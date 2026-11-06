#!/bin/sh
set -eu
cp "$BR2_EXTERNAL_DIAMOND3_PATH/board/diamond3/boot.cmd" "$1/boot.cmd"
cp "$1/imx6sx-diamond3.dtb" "$1/imx6sx-diamond3-qemu.dtb"
"$HOST_DIR/bin/fdtput" "$1/imx6sx-diamond3-qemu.dtb" /soc/gpu@1800000 dma-coherent
sed -e "s|BINARIES_DIR|$1|g" \
 -e "s|BR2_ROOTFS_UBIFS_PATH|$1/rootfs.ubifs|g" \
 -e 's|imx6sx-diamond3.dtb|imx6sx-diamond3-qemu.dtb|g' \
 "$BR2_EXTERNAL_DIAMOND3_PATH/board/diamond3/ubinize.cfg" > "$1/ubinize-qemu.cfg"
"$HOST_DIR/sbin/ubinize" -o "$1/rootfs-qemu.ubi" -m 2048 -p 131072 -s 2048 "$1/ubinize-qemu.cfg"
cd "$1"
sha256sum uInitrd uImage imx6sx-diamond3.dtb rootfs.ubifs rootfs.ubi imx6sx-diamond3-qemu.dtb rootfs-qemu.ubi > SHA256SUMS
