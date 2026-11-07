// SPDX-License-Identifier: GPL-2.0-only
#include <fcntl.h>
#include <mtd/ubi-user.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/ioctl.h>
#include <sys/mount.h>
#include <unistd.h>

static long long number(const char *path)
{
 long long value;
 FILE *f = fopen(path, "r");
 if (!f) { perror(path); exit(1); }
 if (fscanf(f, "%lld", &value) != 1) exit(1);
 fclose(f);
 return value;
}
static void mounted(const char *source, const char *target, const char *type)
{
 if (mount(source, target, type, 0, NULL)) { perror(target); exit(1); }
}
int main(void)
{
 mounted("devtmpfs", "/dev", "devtmpfs");
 int console = open("/dev/console", O_RDWR);
 if (console >= 0) {
  for (int i = 0; i < 3; i++) dup2(console, i);
  if (console > 2) close(console);
 }
 mounted("sysfs", "/sys", "sysfs");
 if (access("/sys/class/ubi/ubi0", F_OK)) {
  struct ubi_attach_req attach = { .ubi_num = UBI_DEV_NUM_AUTO, .mtd_num = 1 };
  int fd = open("/dev/ubi_ctrl", O_RDWR);
  if (fd < 0 || ioctl(fd, UBI_IOCATT, &attach)) { perror("attach ubipart"); return 1; }
  close(fd);
 }
 long long free_lebs = number("/sys/class/ubi/ubi0/avail_eraseblocks");
 if (free_lebs) {
  struct ubi_rsvol_req req = {
   .vol_id = 2,
   .bytes = (free_lebs + number("/sys/class/ubi/ubi0_2/reserved_ebs")) *
             number("/sys/class/ubi/ubi0_2/usable_eb_size"),
  };
  int fd = open("/dev/ubi0", O_RDWR);
  if (fd < 0 || ioctl(fd, UBI_IOCRSVOL, &req)) { perror("grow rootfs"); return 1; }
  close(fd);
 }
 mounted("ubi0:root0", "/newroot", "ubifs");
 if (mount("/dev", "/newroot/dev", NULL, MS_MOVE, NULL) ||
     umount("/sys") || chdir("/newroot") ||
     mount(".", "/", NULL, MS_MOVE, NULL) || chroot(".") || chdir("/")) {
  perror("switch root"); return 1;
 }
 execl("/sbin/init", "init", (char *)NULL);
 perror("init");
 return 1;
}
