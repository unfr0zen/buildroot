#!/bin/sh
set -eu
"$BR2_EXTERNAL_DIAMOND3_PATH/board/common/post_build.sh" "$1"
python3 "$BR2_EXTERNAL_DIAMOND3_PATH/scripts/mkconsole.py" "$BUILD_DIR/linux-7.3.1/lib/fonts/font_8x16.c" "$1" J49
ln -sf wl127x-nvs.bin "$1/lib/firmware/ti-connectivity/wl1271-nvs.bin"

cat "$BINARIES_DIR/zImage" "$BINARIES_DIR/omap3-j49.dtb" > "$BINARIES_DIR/zImage.j49"
"$HOST_DIR/bin/mkimage" -A arm -O linux -T kernel -C none -a 0x80008000 -e 0x80008000 -n Linux-7.3.1-J49 -d "$BINARIES_DIR/zImage.j49" "$BINARIES_DIR/uImage"
