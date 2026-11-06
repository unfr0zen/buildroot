# Nest Buildroot

A boilerplate for anyone building custom Linux images for Nest hardware:
Diamond3 and J49. Linux 7.3.1, Buildroot 2026.08.1, systemd, Bash, SSH,
USB serial/Ethernet, Wi-Fi and a framebuffer console. UBIFS uses the NAND
space remaining after boot artifacts. No OTA.

```sh
git submodule update --init --depth 1
make
make qemu-ui
```

Diamond3 builds download Nest's public signed `u-boot-sdp-5.2d43.hab`,
verify its SHA-256, and generate a NAND wrapper without modifying signed bytes.
Bootloader binaries and device backups are not stored in Git.
Images: `output/images/`. QEMU is a pinned Git submodule. Emulator targets
initialize and build it automatically when needed, then print the UI URL.
`make qemu-build` rebuilds it explicitly.

`output/images/diamond3-buildroot.bin` is a 512 MiB logical NAND image for
`unfr0zen restore`, with a `.sha256` sidecar. Both U-Boot copies use the
downloaded public image; DBBT records are generated during packaging.
Recovery preserves or regenerates the FCB and preserves the chip's bad-block
table. This is not an OOB/ECC image for a raw programmer.
The public loader requires physical-device validation.

```sh
make BOARD=j49
make j49-qemu-ui
```

J49 builds x-loader and U-Boot from pinned Nest GPL sources; no signed or
prebuilt bootloader is required. `j49-buildroot.bin` includes both stages.
J49 images: `output/j49/images/`.

UART and USB serial provide root access. USB Ethernet uses `192.168.77.1/24`
with DHCP. SSH host keys are generated on first boot and stored in UBIFS.
Wi-Fi firmware and J49 NVS download automatically through `linux-firmware`.
Diamond3 radio parameters are included in the board overlay.
Wi-Fi credentials belong in `/etc/wpa_supplicant.conf`.

Linux builds natively using standard Buildroot host dependencies.
On macOS, `make` automatically uses Docker.
