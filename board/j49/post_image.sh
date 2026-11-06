#!/bin/sh
set -eu
python3 "$BR2_EXTERNAL_DIAMOND3_PATH/scripts/j49-nand.py" --images "$1" --output "$1/j49-buildroot.bin"
cd "$1"
sha256sum MLO u-boot-j49.bin u-boot-j49.img uImage omap3-j49.dtb rootfs.ubifs rootfs.ubi j49-buildroot.bin > SHA256SUMS
sha256sum j49-buildroot.bin > j49-buildroot.bin.sha256
