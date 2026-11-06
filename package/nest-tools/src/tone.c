// SPDX-License-Identifier: GPL-2.0-only
#include <fcntl.h>
#include <glob.h>
#include <linux/input.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <unistd.h>

int main(int argc, char **argv)
{
 char *end;
 long hz = argc > 1 ? strtol(argv[1], &end, 10) : 2000;
 if (argc > 1 && *end) return 1;
 long ms = argc > 2 ? strtol(argv[2], &end, 10) : 200;
 if ((argc > 2 && *end) || argc > 3 || hz < 100 || hz > 10000 || ms < 1 || ms > 10000) {
  fprintf(stderr, "Usage: diamond3-tone [100..10000 Hz] [1..10000 ms]\n");
  return 1;
 }
 glob_t paths;
 if (glob("/dev/input/event*", 0, NULL, &paths)) return 1;
 int fd = -1;
 for (size_t i = 0; i < paths.gl_pathc; i++) {
  char name[128] = "";
  fd = open(paths.gl_pathv[i], O_WRONLY);
  if (fd < 0) continue;
  if (ioctl(fd, EVIOCGNAME(sizeof(name)), name) >= 0 && !strcmp(name, "pwm-beeper")) break;
  close(fd); fd = -1;
 }
 globfree(&paths);
 if (fd < 0) { fprintf(stderr, "pwm-beeper input device not found\n"); return 1; }
 struct input_event event = { .type = EV_SND, .code = SND_TONE, .value = hz };
 if (write(fd, &event, sizeof(event)) != sizeof(event)) { perror("tone"); close(fd); return 1; }
 usleep(ms * 1000);
 event.value = 0;
 int result = write(fd, &event, sizeof(event)) == sizeof(event) ? 0 : 1;
 close(fd);
 return result;
}
