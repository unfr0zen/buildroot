#!/bin/sh
set -eu
sed -i '/^ttyGS0::/d' "$1/etc/inittab"
echo 'ttyGS0::respawn:/sbin/getty -L -n -l /bin/sh ttyGS0 115200 vt100' >> "$1/etc/inittab"
firmware="$BR2_EXTERNAL_DIAMOND3_PATH/.work/firmware/brcm"
mkdir -p "$1/lib/firmware/brcm"
for name in brcmfmac43340-sdio.bin brcmfmac43340-sdio.txt; do
 test -f "$firmware/$name" || { echo "Missing private firmware: $firmware/$name" >&2; exit 1; }
 cp "$firmware/$name" "$1/lib/firmware/brcm/$name"
done
python3 "$BR2_EXTERNAL_DIAMOND3_PATH/scripts/mkenv.py" "$BINARIES_DIR"

sed -i '/^tty1::/d' "$1/etc/inittab"
echo 'tty1::respawn:/sbin/getty -L tty1 0 linux' >> "$1/etc/inittab"

initramfs="$BUILD_DIR/diamond3-initramfs"
mkdir -p "$initramfs/dev" "$initramfs/sys" "$initramfs/proc" "$initramfs/newroot"
cp "$BUILD_DIR/diamond3-board-1/diamond3-init" "$initramfs/init"
(cd "$initramfs" && find . | cpio --quiet -o -H newc --owner=0:0) | gzip -9 > "$BINARIES_DIR/initramfs.cpio.gz"
"$HOST_DIR/bin/mkimage" -A arm -O linux -T ramdisk -C gzip -n Diamond3-init -d "$BINARIES_DIR/initramfs.cpio.gz" "$BINARIES_DIR/uInitrd"
