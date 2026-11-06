#!/bin/sh
set -eu
sed -i '/^root:/s@:[^:]*$@:/bin/bash@' "$1/etc/passwd"
sed -i '/^ttyGS0::/d; /^tty1::/d' "$1/etc/inittab"
echo 'ttyGS0::respawn:/sbin/getty -L -n -l /usr/sbin/console-shell ttyGS0 115200 xterm-256color' >> "$1/etc/inittab"
echo 'tty1::respawn:/sbin/getty -L tty1 0 linux' >> "$1/etc/inittab"
