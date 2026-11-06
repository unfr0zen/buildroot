// SPDX-License-Identifier: GPL-2.0-only
#define _DEFAULT_SOURCE
#include <errno.h>
#include <poll.h>
#include <pty.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/wait.h>
#include <termios.h>
#include <time.h>
#include <unistd.h>

static volatile sig_atomic_t stopped, resized;
static void signal_event(int signal)
{
    if (signal == SIGWINCH)
        resized = 1;
    else
        stopped = signal;
}
static int send_all(int fd, const void *data, size_t size)
{
    const char *bytes = data;
    while (size) {
        ssize_t done = write(fd, bytes, size);
        if (done < 0 && errno == EINTR)
            continue;
        if (done <= 0)
            return -1;
        bytes += done;
        size -= done;
    }
    return 0;
}
static long milliseconds(void)
{
    struct timespec now;
    clock_gettime(CLOCK_MONOTONIC, &now);
    return now.tv_sec * 1000L + now.tv_nsec / 1000000;
}
int main(int argc, char **argv)
{
    struct termios original, raw;
    struct winsize window = {.ws_row = 24, .ws_col = 80};
    const char *term = getenv("TERM");
    int master, status = 0;
    pid_t child;
    if (argc < 2)
        return 2;
    if (!isatty(0) || !isatty(1) || (term && !strcmp(term, "linux"))) {
        execvp(argv[1], argv + 1);
        perror(argv[1]);
        return 127;
    }
    if (tcgetattr(0, &original)) {
        perror("tcgetattr");
        return 1;
    }
    ioctl(0, TIOCGWINSZ, &window);
    if (!window.ws_row || !window.ws_col) {
        window.ws_row = 24;
        window.ws_col = 80;
    }
    child = forkpty(&master, NULL, &original, &window);
    if (child < 0) {
        perror("forkpty");
        return 1;
    }
    if (!child) {
        if (!term || !strcmp(term, "vt100") || !strcmp(term, "dumb"))
            setenv("TERM", "xterm-256color", 1);
        execvp(argv[1], argv + 1);
        perror(argv[1]);
        _exit(127);
    }
    raw = original;
    cfmakeraw(&raw);
    if (tcsetattr(0, TCSANOW, &raw)) {
        kill(child, SIGTERM);
        return 1;
    }
    struct sigaction action = {.sa_handler = signal_event};
    sigemptyset(&action.sa_mask);
    sigaction(SIGWINCH, &action, NULL);
    sigaction(SIGTERM, &action, NULL);
    sigaction(SIGHUP, &action, NULL);
    char sequence[64];
    size_t pending = 0;
    long query_at = 0, pending_at = 0;
    while (!stopped) {
        if (waitpid(child, &status, WNOHANG) == child)
            break;
        long now = milliseconds();
        if (now >= query_at) {
            if (send_all(1, "\033[18t", 5))
                break;
            query_at = now + 1000;
        }
        if (resized) {
            struct winsize actual;
            resized = 0;
            if (!ioctl(0, TIOCGWINSZ, &actual) && actual.ws_row &&
                actual.ws_col) {
                window = actual;
                ioctl(master, TIOCSWINSZ, &window);
            }
        }
        if (pending && now - pending_at > 100) {
            if (send_all(master, sequence, pending))
                break;
            pending = 0;
        }
        struct pollfd fds[2] = {{.fd = 0, .events = POLLIN},
                                {.fd = master, .events = POLLIN}};
        int ready = poll(fds, 2, 50);
        if (ready < 0 && errno == EINTR)
            continue;
        if (ready < 0)
            break;
        if (fds[0].revents & POLLIN) {
            char data[4096];
            ssize_t count = read(0, data, sizeof(data));
            if (count <= 0)
                break;
            for (ssize_t i = 0; i < count; i++) {
                unsigned char byte = data[i];
                if (!pending && byte != 27) {
                    if (send_all(master, &byte, 1))
                        stopped = SIGHUP;
                    continue;
                }
                if (!pending)
                    pending_at = now;
                sequence[pending++] = byte;
                /* Only consume CSI 8;rows;columns t window-size reports. */
                int prefix = (pending == 1 && byte == 27) ||
                             (pending == 2 && byte == '[') ||
                             (pending == 3 && byte == '8') ||
                             (pending == 4 && byte == ';') ||
                             (pending > 4 &&
                              ((byte >= '0' && byte <= '9') || byte == ';'));
                if (pending > 4 && byte == 't') {
                    unsigned rows, columns;
                    int end = 0;
                    sequence[pending] = 0;
                    if (sscanf(sequence, "\033[8;%u;%ut%n", &rows, &columns,
                               &end) == 2 &&
                        end == (int)pending && rows && columns &&
                        rows <= 65535 && columns <= 65535) {
                        window.ws_row = rows;
                        window.ws_col = columns;
                        ioctl(master, TIOCSWINSZ, &window);
                        ioctl(0, TIOCSWINSZ, &window);
                        pending = 0;
                        continue;
                    }
                }
                if (!prefix || pending >= sizeof(sequence) - 1) {
                    if (send_all(master, sequence, pending))
                        stopped = SIGHUP;
                    pending = 0;
                }
            }
        }
        if (fds[1].revents & POLLIN) {
            char data[4096];
            ssize_t count = read(master, data, sizeof(data));
            if (count <= 0 || send_all(1, data, count))
                break;
        }
        if (fds[1].revents & (POLLHUP | POLLERR))
            break;
    }
    if (waitpid(child, &status, WNOHANG) == 0) {
        kill(child, stopped ? stopped : SIGHUP);
        waitpid(child, &status, 0);
    }
    tcsetattr(0, TCSANOW, &original);
    close(master);
    return WIFEXITED(status) ? WEXITSTATUS(status) : 128 + WTERMSIG(status);
}
