// SPDX-License-Identifier: GPL-2.0-only
#include <fcntl.h>
#include <glob.h>
#include <linux/uinput.h>
#include <math.h>
#include <stdio.h>
#include <string.h>
#include <sys/ioctl.h>
#include <unistd.h>

static int sample(const char *base, int channel, double *result)
{
 char path[512];
 int value;
 snprintf(path, sizeof(path), "%s/in_voltage%d_raw", base, channel);
 FILE *f = fopen(path, "r");
 if (!f) return -1;
 int ok = fscanf(f, "%d", &value);
 fclose(f);
 if (ok != 1) return -1;
 *result = value;
 return 0;
}
int main(void)
{
 glob_t paths;
 char adc[512] = "";
 if (glob("/sys/bus/iio/devices/iio:device*", 0, NULL, &paths)) return 1;
 for (size_t i = 0; i < paths.gl_pathc; i++) {
  char path[512], name[64];
  snprintf(path, sizeof(path), "%s/name", paths.gl_pathv[i]);
  FILE *f = fopen(path, "r");
  if (!f) continue;
  int ok = fscanf(f, "%63s", name); fclose(f);
  if (ok == 1 && strstr(name, "2280000.adc")) { snprintf(adc, sizeof(adc), "%s", paths.gl_pathv[i]); break; }
 }
 globfree(&paths);
 if (!adc[0]) return 1;
 int fd = open("/dev/uinput", O_WRONLY);
 if (fd < 0) return 1;
 struct uinput_setup setup = { .id = { .bustype = BUS_HOST }, .name = "Diamond3 wheel" };
 if (ioctl(fd, UI_SET_EVBIT, EV_REL) || ioctl(fd, UI_SET_RELBIT, REL_DIAL) ||
     ioctl(fd, UI_DEV_SETUP, &setup) || ioctl(fd, UI_DEV_CREATE)) return 1;
 double previous = 0, accumulated = 0;
 int initialized = 0;
 for (;;) {
  double x, y;
  if (sample(adc, 1, &x) || sample(adc, 2, &y)) return 1;
  x -= 1965; y -= 2038;
  if (hypot(x, y) > 100) {
   double angle = atan2(y, x);
   if (initialized) {
    double delta = remainder(angle - previous, 2 * M_PI);
    accumulated += delta;
    int steps = accumulated / (M_PI / 12);
    if (steps) {
     struct input_event events[2] = {{ .type = EV_REL, .code = REL_DIAL, .value = steps }, { .type = EV_SYN, .code = SYN_REPORT }};
     if (write(fd, events, sizeof(events)) != sizeof(events)) return 1;
     accumulated -= steps * (M_PI / 12);
    }
   }
   previous = angle; initialized = 1;
  }
  usleep(5000);
 }
}
