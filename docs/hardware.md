# Hardware interfaces

Board descriptions follow the stock Diamond3 DVT device tree and Nest's
J49 GPL board files (`board-diamond.c`, `board-j49-evt-mux.c`,
`board-diamond-gpio.h`). Wired controllers are enabled; unused controllers
remain disabled to avoid pin conflicts.

| Interface | Diamond3 | J49 |
|---|---|---|
| Console UART | UART1 `/dev/ttymxc0` | UART1 `/dev/ttyS0` |
| Auxiliary UART | UART2 `/dev/ttymxc1` | UART2 `/dev/ttyS1`, stock pads unrouted |
| Backplate UART | UART6 `/dev/ttysensormcu0` | UART3 `/dev/ttysensormcu0` |
| BLE UART | UART5 `/dev/ttyble0`, DA14580 | None |
| I2C | I2C2 `/dev/i2c-1`, I2C4 `/dev/i2c-3` | I2C1–3 `/dev/i2c-0`–`2` |
| I2C clients | LM3695 `0x63`, PFUZE200 `0x08` | TPS65921 `0x48`–`0x4b`, ADBS-A320 `0x57`, LM3530 `0x36` |
| LCD SPI | ECSPI1, kernel panel driver | McSPI1, kernel panel driver |
| Radio SPI | ECSPI3 `/dev/spidev2.0` | McSPI2 `/dev/spidev1.0` |
| Radio alias | `/dev/spidev_em35x` | `/dev/spidev_em35x` |
| Wheel | ADC1 Hall channels 1/2, uinput `REL_DIAL` | ADBS-A320, uinput `REL_DIAL` |
| Front button | GPIO2_18, gpio-keys | TPS65921 power button |
| Piezo | PWM1, GPIO1_5 active low | GPT11 PWM, GPIO58 active low |
| Display | HX8369, LCDIF DRM | Tianma TM025ZDZ01, OMAP DSS DRM |
| 3D graphics | GC400T, Etnaviv and Mesa | AM3703 has no 3D GPU |

SPI LCD devices belong to their panel drivers and do not expose a spidev
node. The radio device uses an explicit spidev driver override.

## Readings and controls

`nest-status` reports battery voltage, CPU temperature, available backplate
sensors, ADC channels, GPIO controls, and UART/I2C/SPI inventory. `sensors`
reads hwmon devices. `nest-tone 2400 200` plays a 2400 Hz tone for 200 ms;
the QEMU browser's sound button enables host playback.

Battery voltage is `/sys/class/power_supply/nest-battery/voltage_now` in µV.
Diamond3 uses ADC2 channel 0, a gated 100 kΩ/301 kΩ divider and a 100 µs
settling delay. J49 uses three times MADC channel 0's millivolt reading,
as the stock application does. No percentage curve is assumed.

All ADC channels are available through IIO. Diamond3's voltage samples use
a 3.3 V reference. Its battery ADC reads zero while the divider is disabled;
read the power-supply property to perform a gated measurement. J49's
`twl4030_madc_hwmon` platform device also preserves stock attribute names
and millivolt units, including attributes named `battery_temp` and
`battery_charger_current`; these names do not imply °C or mA.

CPU temperatures use `/sys/class/thermal/thermal_zone*/temp` in m°C.
OMAP36xx's kernel driver marks its sensor unreliable and adds its configured
20 °C hotspot offset. QEMU's `die-temperature-millicelsius` device property
controls the synthetic sensor sample; synthetic i.MX calibration does not
supply real HAB fuses.

`nest-backplate` reads checksum-validated MCU frames without issuing HVAC
switching commands. Ambient temperature is centi-°C, humidity is permille
RH, light channels are raw visible/IR ADC values, and PIR reports motion.
`/run/nest/backplate.state` contains numeric readings and sample timestamps;
`/run/nest/backplate-messages/` retains the latest payload for each message
type. Missing, invalid or stale samples are unavailable. UART baud discovery
and the handshake require physical-device validation.

GPIO exporter nodes expose stock-style `<signal>/value` files with raw
physical pin values. Inputs are read-only; outputs initialize deasserted.

| Board node | Signals (SoC GPIO) |
|---|---|
| Diamond3 `sensor-mcu-gpios` | `detect#` 5_13, reset 5_14 |
| Diamond3 `ble0-da14580-gpios` | reset 5_16 |
| Diamond3 `em35x-gpios` | reset 2_0, wake 2_5, irq 2_4 |
| J49 `diamond-backplate` | `detect#` 65, reset 104 |
| J49 `diamond-zigbee` | `interrupt` 182, `reset#` 61 |
| J49 `diamond-battery` | disconnect 161 |
| J49 `board-inputs` | LCD ID 105, wheel motion 108 |

Kernel-owned LCD, wheel, Wi-Fi, button and beeper pins stay owned by those
drivers. The generic GPIO character devices expose remaining unclaimed
lines through libgpiod.

## Bluetooth

Diamond3 includes BlueZ (`bluetoothctl`, `btmon`, `btattach`), UART H4 and
USB Bluetooth kernel drivers. The stock DA14580 startup uses `da-loader`
at 57600 baud and loads `nl_ble_app_firmware.bin`. The stock `ble-ping` tool sends a GTL frame (type `0x05`, message
`0xc801`); installing BlueZ does not convert that protocol. No automatic H4 attachment is attempted against
unknown firmware. Onboard BlueZ operation requires HCI-capable firmware or
a validated protocol bridge. QEMU models the DA14580 UART boot ROM and base GTL commands. Its optional
HCI test personality supports BlueZ with a virtual GATT peer; it does not
execute Nest firmware or provide HCI firmware for physical devices. See
[QEMU BLE UART](../qemu/docs/qemu-da14580.md).

Physical panel, radio, analog calibration and sound require device testing.

## Services

Systemd manages USB gadget setup, USB DHCP, the wheel daemon, backplate
telemetry and SSH host-key creation through `nest-*.service` units.
`nest-netbios.service` answers NetBIOS hostname queries; Avahi advertises
`diamond3.local` or `j49.local` and SSH. The journal stays in RAM with a
2 MiB limit. PID 1 services the watchdog. Device identity and SSH keys
persist on UBIFS across reboots. The Jitterentropy daemon seeds the kernel
random pool before SSH key creation. J49 limits udev to one worker and
disables watermark boosting to fit its 64 MiB RAM.

To configure Wi-Fi, write `/etc/wpa_supplicant.conf` and enable the upstream
`wpa_supplicant@wlan0.service` unit (`systemctl enable --now
wpa_supplicant@wlan0`). Systemd-networkd requests
DHCP after association. No Wi-Fi credentials are included in the image.

The display service loads panel and backlight drivers before `sysinit.target`.
The font service prints the banner as soon as the framebuffer is available.
Coldplug runs alongside other services; USB waits for its UDC rather than the
whole udev queue. Diamond3 uses four udev workers; J49 uses one.
`nest-console.service` opens the UART directly, configured by
`/etc/default/nest-console`. Login consoles lower console printk verbosity;
boot messages remain enabled, and subsequent messages remain in `dmesg` and
the journal. `dmesg -n 7` restores live kernel console messages.

Diamond3 QEMU uses `rootfs-qemu.ubi` and `imx6sx-diamond3-qemu.dtb`,
which declare the emulated GPU DMA coherent. `rootfs.ubi` contains the
physical-device DTB with its hardware DMA cache policy.
