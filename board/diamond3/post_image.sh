#!/bin/sh
set -eu
cp "$BR2_EXTERNAL_DIAMOND3_PATH/board/diamond3/boot.cmd" "$1/boot.cmd"
cd "$1"
sha256sum uInitrd uImage imx6sx-diamond3.dtb rootfs.ubifs rootfs.ubi > SHA256SUMS
