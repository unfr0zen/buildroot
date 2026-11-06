// SPDX-License-Identifier: GPL-2.0-only
#define _DEFAULT_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <poll.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/file.h>
#include <sys/stat.h>
#include <termios.h>
#include <time.h>
#include <unistd.h>

static int serial_fd;
static int temperature = INT_MIN, humidity = -1, visible = -1, infrared = -1,
           motion;
static long temp_at, light_at, motion_at, packet_at;
static uint16_t le16(const unsigned char *p) { return p[0] | p[1] << 8; }
static long seconds(void) {
    struct timespec now;
    clock_gettime(CLOCK_BOOTTIME, &now);
    return now.tv_sec;
}
static uint16_t checksum(const unsigned char *data, size_t size) {
    uint16_t crc = 0;
    while (size--) {
        crc ^= (uint16_t)*data++ << 8;
        for (int i = 0; i < 8; i++)
            crc = crc & 0x8000 ? (crc << 1) ^ 0x1021 : crc << 1;
    }
    return crc;
}
static void send_frame(unsigned type, const unsigned char *data,
                       unsigned size) {
    unsigned char frame[263] = {0xd5,      0xaa, 0x96,     type,
                                type >> 8, size, size >> 8};
    memcpy(frame + 7, data, size);
    uint16_t crc = checksum(frame + 3, size + 4);
    frame[size + 7] = crc;
    frame[size + 8] = crc >> 8;
    size += 9;
    unsigned done = 0;
    while (done < size) {
        ssize_t count = write(serial_fd, frame + done, size - done);
        if (count > 0) {
            done += count;
            continue;
        }
        if (count < 0 && errno == EINTR)
            continue;
        if (count < 0 && errno == EAGAIN) {
            struct pollfd fd = {.fd = serial_fd, .events = POLLOUT};
            if (poll(&fd, 1, 1000) > 0)
                continue;
        }
        break;
    }
}
static void save_state(void) {
    FILE *file = fopen("/run/nest/backplate.state.tmp", "w");
    if (!file)
        return;
    fprintf(file,
            "packet_at=%ld\ntemp_at=%ld\nlight_at=%ld\nmotion_at=%"
            "ld\ntemperature_centi_c=%d\nhumidity_permille=%d\nlight_visible_"
            "raw=%d\nlight_infrared_raw=%d\nmotion=%d\n",
            packet_at, temp_at, light_at, motion_at, temperature, humidity,
            visible, infrared, motion);
    if (!fclose(file))
        rename("/run/nest/backplate.state.tmp", "/run/nest/backplate.state");
}
static void packet(unsigned type, const unsigned char *data, unsigned size) {
    packet_at = seconds();
    char path[96];
    snprintf(path, sizeof(path), "/run/nest/backplate-messages/%04x.hex", type);
    FILE *file = fopen(path, "w");
    if (file) {
        for (unsigned i = 0; i < size; i++)
            fprintf(file, "%02x", data[i]);
        fputc('\n', file);
        fclose(file);
    }
    if (type == 2 && size >= 4) {
        int value = (int16_t)le16(data);
        temperature = value >= -4000 && value <= 12500 ? value : INT_MIN;
        value = le16(data + 2);
        humidity = value <= 1000 ? value : -1;
        temp_at = packet_at;
    } else if (type == 10 && size >= 4) {
        visible = le16(data);
        infrared = le16(data + 2);
        if (visible == 65535)
            visible = -1;
        if (infrared == 65535)
            infrared = -1;
        light_at = packet_at;
    } else if (type == 5 && size >= 4) {
        motion = le16(data) || le16(data + 2);
        motion_at = packet_at;
    } else if (type == 4 && size == 13) {
        send_frame(0x8f, data, size);
    }
    static const unsigned char requests[][2] = {
        {0x10, 0x98}, {0x18, 0x99}, {0x19, 0x9d}, {0x1d, 0x9b},
        {0x1b, 0x9c}, {0x1c, 0x9f}, {0x1f, 0x9e}, {0x1e, 0x85},
    };
    for (unsigned i = 0; i < sizeof(requests) / sizeof(requests[0]); i++)
        if (type == requests[i][0])
            send_frame(requests[i][1], data, 0);
    save_state();
}
static int detached(void) {
    static const char *const paths[] = {
        "/sys/devices/platform/sensor-mcu-gpios/detect#/value",
        "/sys/devices/platform/diamond-backplate/detect#/value",
    };
    for (unsigned i = 0; i < sizeof(paths) / sizeof(paths[0]); i++) {
        FILE *file = fopen(paths[i], "r");
        if (file) {
            int value = fgetc(file);
            fclose(file);
            return value == '1';
        }
    }
    return 0;
}

int main(int argc, char **argv) {
    const char *device = argc > 1 ? argv[1] : "/dev/ttysensormcu0";
    static const speed_t speeds[] = {B115200, B460800, B921600, B230400,
                                     B57600,  B38400,  B9600};
    unsigned speed = 0;
    serial_fd = open(device, O_RDWR | O_NOCTTY | O_NONBLOCK);
    if (serial_fd < 0) {
        perror(device);
        return 1;
    }
    if (flock(serial_fd, LOCK_EX | LOCK_NB)) {
        perror("backplate already open");
        return 1;
    }
    struct termios tty;
    if (tcgetattr(serial_fd, &tty)) {
        perror("tcgetattr");
        return 1;
    }
    cfmakeraw(&tty);
    tty.c_cflag |= CLOCAL | CREAD;
    tty.c_cflag &= ~CRTSCTS;
    mkdir("/run/nest", 0755);
    mkdir("/run/nest/backplate-messages", 0755);
    unsigned char input[2048];
    size_t used = 0;
    long baud_at = -10, tick_at = -10;
    for (;;) {
        long now = seconds();
        if (detached()) {
            if (packet_at) {
                packet_at = temp_at = light_at = motion_at = 0;
                temperature = INT_MIN;
                humidity = visible = infrared = -1;
                save_state();
            }
            used = 0;
            tcflush(serial_fd, TCIFLUSH);
            poll(NULL, 0, 500);
            continue;
        }
        if ((!packet_at || now - packet_at > 15) && now - baud_at >= 3) {
            speed_t baud =
                speeds[speed++ % (sizeof(speeds) / sizeof(speeds[0]))];
            cfsetispeed(&tty, baud);
            cfsetospeed(&tty, baud);
            tcsetattr(serial_fd, TCSANOW, &tty);
            tcflush(serial_fd, TCIFLUSH);
            used = 0;
            baud_at = now;
            tcsendbreak(serial_fd, 0);
            send_frame(0xff, input, 0);
            send_frame(0x90, input, 0);
        }
        if (packet_at && now - tick_at >= 2) {
            unsigned char tick[4] = {now, now >> 8, now >> 16, now >> 24};
            send_frame(0x83, tick, 4);
            tick_at = now;
        }
        struct pollfd fd = {.fd = serial_fd, .events = POLLIN};
        int ready = poll(&fd, 1, 500);
        if (ready < 0 && errno == EINTR)
            continue;
        if (ready < 0 || fd.revents & (POLLHUP | POLLERR))
            break;
        if (!(fd.revents & POLLIN))
            continue;
        ssize_t count = read(serial_fd, input + used, sizeof(input) - used);
        if (count < 0 && (errno == EINTR || errno == EAGAIN))
            continue;
        if (count <= 0)
            break;
        used += count;
        while (used >= 7) {
            if (input[0] != 0xd5 || input[1] != 0xaa || input[2] != 0x96 ||
                le16(input + 5) > 254) {
                memmove(input, input + 1, --used);
                continue;
            }
            unsigned size = le16(input + 5);
            if (used < size + 9)
                break;
            if (checksum(input + 3, size + 4) == le16(input + size + 7)) {
                packet(le16(input + 3), input + 7, size);
                used -= size + 9;
                memmove(input, input + size + 9, used);
            } else {
                memmove(input, input + 1, --used);
            }
        }
    }
    perror("backplate serial");
    return 1;
}
