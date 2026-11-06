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

Generated NAND images target QEMU. Physical flashing and HAB authentication
require device validation; preserve the original signed bootloader and bad-block map.
