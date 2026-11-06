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
    parser.add_argument("--uboot", type=Path,
                        default=ROOT / "output/images/u-boot-sdp-5.2d43-nand.bin")
    parser.add_argument("--boot-reference", type=Path, required=True,
                        help="logical NAND backup providing the complete boot partition")
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
    if boot_size > len(boot) or len(boot) > 0x180000:
        parser.error("U-Boot image must contain its boot-data span and fit the NAND reservation")
    if args.boot_reference.stat().st_size != NAND_SIZE:
        parser.error("boot reference must be a 512 MiB logical NAND backup")
    if args.output.resolve() == args.boot_reference.resolve():
        parser.error("output must not overwrite the reference backup")
    with args.boot_reference.open("rb") as reference:
        boot_partition = reference.read(0x400000)
    boot_partition = bytearray(boot_partition)
    for offset in [0x100000, 0x280000]:
        if boot_partition[offset + 0x400:offset + 0x404] != bytes.fromhex("d1002040"):
            parser.error("reference backup has no U-Boot IVT at the expected offsets")
        data, own = struct.unpack_from("<II", boot_partition, offset + 0x410)
        data_offset = offset + 0x400 + data - own
        if data_offset < offset or data_offset + 12 > offset + 0x180000:
            parser.error("reference U-Boot boot-data pointer is outside its reservation")
        capacity = struct.unpack_from("<I", boot_partition, data_offset + 4)[0]
        if capacity < len(boot):
            parser.error("reference bootloader span is too small for the public signed image")
        boot_partition[offset:offset + 0x180000] = b"\xff" * 0x180000
        boot_partition[offset:offset + len(boot)] = boot
    if not any(boot_partition[offset + 4:offset + 12] == b"DBBT\x00\x00\x00\x01"
               for offset in range(0x80000, 0x100000, BLOCK_SIZE)):
        parser.error("reference boot partition has no valid DBBT header")
    ubi = (args.images / "rootfs.ubi").read_bytes()
    if not ubi.startswith(b"UBI#") or len(ubi) % BLOCK_SIZE:
        parser.error("rootfs.ubi must be an erase-block-aligned UBI image")
    if len(ubi) > NAND_SIZE - 0x400000 - 4 * BLOCK_SIZE:
        parser.error("UBI image overlaps the flash bad-block table reservation")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("wb") as image:
        for _ in range(NAND_SIZE // 1048576):
            image.write(b"\xff" * 1048576)
        for offset, contents in [(0, boot_partition), (0x400000, ubi)]:
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
