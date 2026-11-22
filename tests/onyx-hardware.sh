#!/bin/sh
# Runs on a freshly booted QEMU Onyx guest.
set -ex

test "$(id -u)" = 0
grep -q '^ubi0:root0 / ubifs ' /proc/mounts
test "$(cat /sys/class/graphics/fb0/virtual_size)" = 320,320
test "$(i2cget -y 1 0x63 0x14)" = 0xe1
test -c /dev/watchdog0
test -c /dev/ttyGS0
test -d /sys/class/net/usb0
test -r /sys/bus/nvmem/devices/imx-ocotp0/nvmem
temperature=$(cat /sys/class/thermal/thermal_zone0/temp)
test "$temperature" -gt 45000
test "$temperature" -lt 55000
grep -qx 'gpio-keys' /sys/class/input/event*/device/name
grep -qx 'Onyx wheel' /sys/class/input/event*/device/name
grep -qx 'pwm-beeper' /sys/class/input/event*/device/name
nest-tone 2000 20
voltage=$(cat /sys/class/power_supply/nest-battery/voltage_now)
test "$voltage" -ge 3850000
test "$voltage" -le 3950000

# The MCU reports its sensors asynchronously on UART3.
for i in $(seq 1 20); do
    grep -qsE '^temp_at=[1-9]' /run/nest/backplate.state && break
    sleep 1
done
grep -E '^temp_at=[1-9]' /run/nest/backplate.state
ambient=$(sed -n 's/^temperature_centi_c=//p' /run/nest/backplate.state)
test "$ambient" -ge -4000
test "$ambient" -le 12500

# Read NCP_VERSION using Spinel PROP_VALUE_GET over the EM358 SPI port.
radio=/dev/spidev_em35x
transfer() {
    { printf '%b' "$1"; dd if=/dev/zero bs=1 count="$2" 2>/dev/null; } |
        spi-pipe -d "$radio" -b 128 -n 1
}
transfer '\002\173\000\003\000\201\002\002' 120 >/dev/null
for i in $(seq 1 5); do
    transfer '\002\173\000\000\000' 123 >/tmp/ncp-reply
    grep -aq 'OPENTHREAD/' /tmp/ncp-reply && break
    sleep 1
done
grep -ao 'OPENTHREAD/[[:print:]]*' /tmp/ncp-reply
ip link set wlan0 up
iw dev wlan0 scan | grep -F 'SSID: QEMU'
iw dev wlan0 connect QEMU
for i in $(seq 1 20); do
    ip -4 addr show dev wlan0 | grep -q 'inet 10\.0\.2\.' && break
    sleep 1
done
iw dev wlan0 link | grep -F 'SSID: QEMU'
ip -4 addr show dev wlan0 | grep 'inet 10\.0\.2\.'
