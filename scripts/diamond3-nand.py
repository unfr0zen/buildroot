#!/usr/bin/env python3
"""Package a Diamond3 logical NAND image for unfr0zen restore."""
import argparse
import hashlib
from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parents[1]
NAND_SIZE = 0x20000000
BLOCK_SIZE = 0x20000


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--uboot", type=Path, required=True)
    parser.add_argument("--images", type=Path, default=ROOT / "output/images")
    parser.add_argument("--output", type=Path,
                        default=ROOT / "output/images/diamond3-buildroot.bin")
    args = parser.parse_args()
    boot = args.uboot.read_bytes()
    if len(boot) < 0x420 or boot[0x400:0x404] != bytes.fromhex("d1002040"):
        parser.error("U-Boot must contain an i.MX IVT at offset 0x400")
    boot_data, own = struct.unpack_from("<II", boot, 0x410)
    data_offset = 0x400 + boot_data - own
    if data_offset < 0 or data_offset + 12 > len(boot):
        parser.error("U-Boot boot-data pointer is outside the image")
    boot_size = struct.unpack_from("<I", boot, data_offset + 4)[0]
    if boot_size != len(boot) or len(boot) > 0x180000:
        parser.error("U-Boot length must match its signed boot-data size")
    ubi = (args.images / "rootfs.ubi").read_bytes()
    if not ubi.startswith(b"UBI#") or len(ubi) % BLOCK_SIZE:
        parser.error("rootfs.ubi must be an erase-block-aligned UBI image")
    if len(ubi) > NAND_SIZE - 0x400000 - 4 * BLOCK_SIZE:
        parser.error("UBI image overlaps the flash bad-block table reservation")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("wb") as image:
        for _ in range(NAND_SIZE // 1048576):
            image.write(b"\xff" * 1048576)
        for offset, contents in [(0x100000, boot), (0x280000, boot),
                                 (0x400000, ubi)]:
            image.seek(offset)
            image.write(contents)
    sha = hashlib.sha256()
    with args.output.open("rb") as image:
        for chunk in iter(lambda: image.read(1048576), b""):
            sha.update(chunk)
    digest = sha.hexdigest()
    checksum = args.output.with_suffix(args.output.suffix + ".sha256")
    checksum.write_text(f"{digest}  {args.output.name}\n")
    print(f"{args.output}: {NAND_SIZE} bytes, SHA-256 {digest}")


if __name__ == "__main__":
    main()
