# Nest Buildroot

Linux 7.3.1 and Buildroot 2026.08.1 for Diamond3 and J49, with systemd,
Bash, SSH, USB serial/Ethernet, Wi-Fi and a framebuffer console. UBIFS uses
the NAND space remaining after boot artifacts. No OTA.

Requires Docker on macOS, the sibling `../qemu` checkout, and stock device
firmware. Upstream Buildroot is a Git submodule.

```sh
git submodule update --init --depth 1
make firmware FIRMWARE_DIR=/path/to/stock/lib/firmware/brcm
make docker
make qemu-ui UBOOT='/path/to/u-boot-6.5-14-signed.hab'
```

Diamond3 images: `output/images/`. UI: http://127.0.0.1:8075.

Diamond3 includes ioquake3 and the public Quake III Arena demo. Run
`quake3-demo` to follow an automatic bot match, or `quake3 +map q3dm1`
for a clockwise-rotated KMS/OpenGL ES session.

```sh
make j49-firmware NVS=/path/to/stock/wl12xx-nvs.bin
make j49
make j49-qemu-ui NAND=/path/to/stock-j49.raw FRESH=1
```

J49 images: `output/j49/images/`. UI: http://127.0.0.1:8076.
J49 requires a stock NAND dump with 2048-byte pages and 64-byte OOBs.

UART and USB serial provide root access. USB Ethernet uses `192.168.77.1/24`
with DHCP. SSH host keys are generated on first boot and stored in UBIFS.
Wi-Fi credentials belong in `/etc/wpa_supplicant.conf`.

For native Linux builds, install Buildroot host dependencies and run
`make diamond3-defconfig && make`; then `make BOARD=j49 j49-defconfig`
and `make BOARD=j49`. Docker builds reuse the Diamond3 glibc toolchain for J49.

To package a physical Diamond3 test image after building:

```sh
make diamond3-image UBOOT='/path/to/u-boot-6.5-14-signed.hab' \
  BOOT_NAND='/path/to/diamond3-nand-backup.bin'
```

`output/images/diamond3-buildroot.bin` is a 512 MiB logical NAND image for
`unfr0zen restore`, with a `.sha256` sidecar. It uses the hardware DTB and
preserves the reference backup's complete 4 MiB boot partition, including DBBT.
The reference must contain both copies of the supplied signed U-Boot.
Restore preserves or regenerates ROM boot-control data and preserves the chip's
bad-block table. This is not an OOB/ECC image for a raw programmer.
Physical peripherals and HAB authentication require device validation.
Use an unfr0zen build that recognizes Homebrew USB `1d6b:0104` at restore
completion. UART and USB serial expose the Linux console.
