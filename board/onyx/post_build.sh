#!/bin/sh
set -eu
"$BR2_EXTERNAL_DIAMOND3_PATH/board/common/post_build.sh" "$1"
python3 "$BR2_EXTERNAL_DIAMOND3_PATH/scripts/mkenv.py" "$BINARIES_DIR" onyx
initramfs="$BUILD_DIR/onyx-initramfs"
mkdir -p "$initramfs/dev" "$initramfs/sys" "$initramfs/proc" "$initramfs/newroot" "$initramfs/sbin"
cp "$BUILD_DIR/onyx-board-1/onyx-init" "$initramfs/init"
ln -sf ../init "$initramfs/sbin/init"
(cd "$initramfs" && find . | cpio --quiet -o -H newc --owner=0:0) | gzip -9 > "$BINARIES_DIR/initramfs.cpio.gz"
cp "$BR2_EXTERNAL_DIAMOND3_PATH/board/onyx/kernel.its" "$BINARIES_DIR/kernel.its"
(cd "$BINARIES_DIR" && "$HOST_DIR/bin/mkimage" -f kernel.its kernel_fdt.itb)
install -D -m 0644 "$BINARIES_DIR/kernel_fdt.itb" "$1/boot/kernel_fdt.itb"
python3 "$BR2_EXTERNAL_DIAMOND3_PATH/scripts/mkconsole.py" "$BUILD_DIR/linux-7.3.1/lib/fonts/font_8x16.c" "$1" ONYX
# The backplate and wheel need Onyx-specific userspace integration.
rm -f "$1/etc/systemd/system/multi-user.target.wants/nest-wheel.service" \
      "$1/etc/systemd/system/multi-user.target.wants/nest-backplate.service"
