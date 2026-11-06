#!/bin/sh
set -eu
cd "$1"
sha256sum uImage omap3-j49.dtb rootfs.ubifs rootfs.ubi > SHA256SUMS
