#!/bin/sh
set -eu
sed -i '/^root:/s@:[^:]*$@:/bin/bash@' "$1/etc/passwd"
[ ! -L "$1/etc/dropbear" ] || rm -f "$1/etc/dropbear"
mkdir -p "$1/etc/dropbear" "$1/etc/systemd/system/multi-user.target.wants"
# Host keys and machine identity belong to the device's first boot.
rm -f "$1/etc/dropbear/"*host_key "$1/etc/machine-id"
touch "$1/etc/machine-id"
for unit in nest-hardware nest-usb nest-usb-dhcp nest-wheel nest-backplate nest-ssh-keys; do
 ln -sf "../$unit.service" "$1/etc/systemd/system/multi-user.target.wants/$unit.service"
done
mkdir -p "$1/etc/systemd/system/getty.target.wants"
ln -sf ../nest-usb-shell.service "$1/etc/systemd/system/getty.target.wants/nest-usb-shell.service"
ln -sf /usr/lib/systemd/system/getty@.service "$1/etc/systemd/system/getty.target.wants/getty@tty1.service"
rm -f "$1/etc/avahi/services/sftp-ssh.service"

mkdir -p "$1/etc/systemd/system/sysinit.target.wants"
ln -sf ../nest-console-font.service "$1/etc/systemd/system/sysinit.target.wants/nest-console-font.service"

ln -sf ../nest-console.service "$1/etc/systemd/system/getty.target.wants/nest-console.service"
