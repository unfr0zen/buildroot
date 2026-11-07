#!/bin/sh
set -eu
python3 "$BR2_EXTERNAL_DIAMOND3_PATH/scripts/diamond3-nand.py" --board onyx --images "$1" --uboot "$1/u-boot-sdp-5.8d44-onyx-0NUR-nand.bin" --output "$1/onyx-buildroot.bin"
cd "$1"
sha256sum u-boot-sdp-5.8d44-onyx-0NUR.hab u-boot-sdp-5.8d44-onyx-0NUR-nand.bin zImage imx6ul-onyx.dtb kernel_fdt.itb rootfs.ubifs rootfs.ubi onyx-buildroot.bin > SHA256SUMS
