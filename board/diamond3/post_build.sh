#!/bin/sh
set -eu
"$BR2_EXTERNAL_DIAMOND3_PATH/board/common/post_build.sh" "$1"
firmware="$BR2_EXTERNAL_DIAMOND3_PATH/.work/firmware/brcm"
mkdir -p "$1/lib/firmware/brcm"
for name in brcmfmac43340-sdio.bin brcmfmac43340-sdio.txt; do
 test -f "$firmware/$name" || { echo "Missing private firmware: $firmware/$name" >&2; exit 1; }
 cp "$firmware/$name" "$1/lib/firmware/brcm/$name"
done
python3 "$BR2_EXTERNAL_DIAMOND3_PATH/scripts/mkenv.py" "$BINARIES_DIR"


initramfs="$BUILD_DIR/diamond3-initramfs"
mkdir -p "$initramfs/dev" "$initramfs/sys" "$initramfs/proc" "$initramfs/newroot"
cp "$BUILD_DIR/diamond3-board-1/diamond3-init" "$initramfs/init"
(cd "$initramfs" && find . | cpio --quiet -o -H newc --owner=0:0) | gzip -9 > "$BINARIES_DIR/initramfs.cpio.gz"
"$HOST_DIR/bin/mkimage" -A arm -O linux -T ramdisk -C gzip -n Diamond3-init -d "$BINARIES_DIR/initramfs.cpio.gz" "$BINARIES_DIR/uInitrd"
python3 "$BR2_EXTERNAL_DIAMOND3_PATH/scripts/mkconsole.py" "$BUILD_DIR/linux-7.3.1/lib/fonts/font_8x16.c" "$1"
