#!/bin/sh
set -eu
"$BR2_EXTERNAL_DIAMOND3_PATH/board/common/post_build.sh" "$1"
python3 "$BR2_EXTERNAL_DIAMOND3_PATH/scripts/mkenv.py" "$BINARIES_DIR"


initramfs="$BUILD_DIR/diamond3-initramfs"
mkdir -p "$initramfs/dev" "$initramfs/sys" "$initramfs/proc" "$initramfs/newroot"
cp "$BUILD_DIR/diamond3-board-1/diamond3-init" "$initramfs/init"
(cd "$initramfs" && find . | cpio --quiet -o -H newc --owner=0:0) | gzip -9 > "$BINARIES_DIR/initramfs.cpio.gz"
"$HOST_DIR/bin/mkimage" -A arm -O linux -T ramdisk -C gzip -n Diamond3-init -d "$BINARIES_DIR/initramfs.cpio.gz" "$BINARIES_DIR/uInitrd"
python3 "$BR2_EXTERNAL_DIAMOND3_PATH/scripts/mkconsole.py" "$BUILD_DIR/linux-7.3.1/lib/fonts/font_8x16.c" "$1"
