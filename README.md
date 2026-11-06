# Diamond3 Buildroot

Buildroot 2026.08.1, Linux 7.3.1, musl, BusyBox, eudev, iproute2, iw,
wpa_supplicant, Dropbear, Bash, Starship 1.27.0, procps, htop, GNU grep,
util-linux, MTD/UBI tools, evtest, libgpiod tools, i2c-tools, USB tools,
nano and less. No OTA service or update slots.

On macOS with Docker running:

```sh
make docker
```

On Linux with Buildroot host dependencies installed:

```sh
make diamond3-defconfig
make
```

The upstream tree is the `buildroot/` Git submodule pinned to tag
`2026.08.1`. `make prepare` initializes it. Board wiring and rootfs overlay
live in
`board/diamond3/`, kernel configuration in `linux/`, and external packages
in `package/`. `configs/diamond3_defconfig` selects the complete system.
Docker builds use the named volume `diamond3-buildroot-output`; finished
artifacts are copied to `output/images/`. `make menuconfig` and
`make linux-menuconfig` configure native Linux builds. To configure Docker
builds, run `scripts/build.sh menuconfig` or `scripts/build.sh linux-menuconfig`.
`make docker` preserves the active configuration; use
`scripts/build.sh diamond3-defconfig all` to restore the checked-in defaults.

Wi-Fi requires the device firmware and board NVRAM from a stock filesystem:

```sh
make firmware FIRMWARE_DIR=/path/to/stock/lib/firmware/brcm
```

Only `brcmfmac43340-sdio.bin` and `brcmfmac43340-sdio.txt` are imported into
ignored `.work/firmware/`. Firmware, ROM dumps, signed U-Boot and NAND images
are not tracked. The post-build step requires these Wi-Fi files.

Run the sibling QEMU machine through the unchanged signed U-Boot:

```sh
make qemu-ui UBOOT='/absolute/path/to/u-boot-6.5-14-signed.hab'
```

`scripts/qemu.py --uboot FILE --fresh` creates a fresh isolated emulated NAND.
The generated UBI image includes redundant U-Boot environments that
automatically load the legacy kernel, initramfs and DTB from UBI volumes.
The web UI is served at `http://127.0.0.1:8075`. `make qemu` runs only the
serial console; `make smoke` verifies a root shell on a fresh emulated NAND.
The default QEMU binary is
`../qemu/qemu-src/build/qemu-system-arm` and can be overridden with `--qemu`.

| NAND region | Offset | Size |
|---|---:|---:|
| Existing U-Boot/FCB/DBBT reservation | 0 | 4 MiB |
| UBI (`env0`, `env1`, `kernel`, `dtb`, `initramfs`, `rootfs`) | 0x400000 | 508 MiB |

The root volume fills the space left after boot artifacts, UBI metadata and
bad-block reserves. The two environment copies are bootloader metadata,
not rootfs update slots. A small static initramfs extends the root volume
before mounting UBIFS:
the signed bootloader initially attaches the stock 500 MiB partition.

`rootfs.ubifs` uses 2048-byte minimum I/O and 126976-byte LEBs.
`rootfs.ubi` uses 128 KiB eraseblocks, a VID header at 2048 bytes,
and a dynamic `rootfs` volume with autoresize. UBI reserves its own
metadata and bad-block allowance from the remaining NAND space.

The emulator image is logical data pages without OOB/ECC. It is not a
physical NAND flashing image: real hardware requires preserving its FCB,
DBBT, signed bootloader copies and bad-block map. No physical-device
flashing target is provided.

Userspace uses Linux 7.1 headers with the Linux 7.3.1 runtime kernel.

UART1 exposes a root login with an empty password. USB configfs creates a
composite CDC ACM/ECM gadget. `/dev/ttyGS0` runs a Bash root shell.
The USB Ethernet interface is `192.168.77.1/24`; its DHCP server offers
`192.168.77.10` through `.20` without replacing the host's default route
or DNS. Dropbear accepts the empty root password for local development. Wi-Fi credentials are supplied separately through
`/etc/wpa_supplicant.conf`; the image contains no network credentials.

The board package initializes the HX8369 panel through GPIO-driven 9-bit
SPI and exposes LCDIF through DRM/fbdev. It includes a wheel daemon using
the two VF610 ADC Hall channels and a uinput `REL_DIAL` device; the front
button uses gpio-keys. Board wiring and panel command tables derive from
the local stock Diamond3 device tree and the GPL display implementation
in the sibling recovery U-Boot sources. Physical display timing, analog
wheel calibration, USB enumeration and Wi-Fi require device validation.

QEMU's default ROM stub loads signed U-Boot without validating HAB.
Its optional `boot-rom` property requires a complete 98304-byte dump.
The partial 97280-byte dump starts at address 0x400 and omits reset
vectors. The complete `diamond3-rom-00000000-00018000.bin` includes them
and can be run with `make rom ROM=/absolute/path/to/full-rom.bin`.
Real HAB authentication needs the device's fuse state and ROM hardware
dependencies modelled.

The framebuffer console rotates 90 degrees clockwise. A twelve-line
Braille thermostat banner uses a bundled 512-glyph console font. Bash
initializes Starship with a plain-character, colored prompt; aliases live
in `/etc/profile.d/30-aliases.sh`. `dmesg` uses util-linux color output.

The piezo uses PWM1 and its active-low amplifier GPIO through the kernel
`pwm-beeper` input driver. `diamond3-tone 2400 200` plays a 2400 Hz tone
for 200 milliseconds; omitting arguments uses 2000 Hz for 200 ms.
The QEMU runner sets the PWM model clock to 66 MHz to match this kernel.

With the UI running, `python3 scripts/check-usb.py` verifies an ACM root
shell and an ECM DHCP exchange through `.work/nand.usb.sock`. This is a
virtual USB host; it does not create a macOS USB Ethernet interface.
