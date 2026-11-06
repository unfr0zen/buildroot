#!/usr/bin/env python3
"""Create a J49 raw NAND using source-built x-loader and U-Boot."""

import argparse
import j49_ecc as ecc
from pathlib import Path

root = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--images", type=Path, default=root / "output/j49/images")
p.add_argument("--output", type=Path, default=root / "output/j49/images/j49-buildroot.bin")
a = p.parse_args()
mask = (1 << 52) - 1
table = []
for byte in range(256):
    value = byte << 44
    for _ in range(8):
        value = ((value << 1) & mask) ^ (ecc.BCH4_G if value & (1 << 51) else 0)
    table.append(value)


def parity(data):
    value = 0
    for byte in data:
        value = ((value << 8) & mask) ^ table[((value >> 44) ^ byte) & 255]
    return value


assert parity(bytes(range(256)) * 2) == ecc.bch4_parity(bytes(range(256)) * 2)
ecc.bch4_parity = parity
images = a.images
kernel = (images / "uImage").read_bytes()
ubi = (images / "rootfs.ubi").read_bytes()
assert len(kernel) <= 0x800000 and len(ubi) <= 0xF400000
a.output.parent.mkdir(parents=True, exist_ok=True)
with a.output.open("wb") as target:
    remaining = 0x10000000 // 2048 * 2112
    while remaining:
        count = min(remaining, 1048576)
        target.write(b"\xff" * count)
        remaining -= count
with a.output.open("r+b") as target:
    mlo = (images / "MLO").read_bytes()
    uboot = (images / "u-boot-j49.img").read_bytes()
    assert len(mlo) <= 0x20000 and len(uboot) <= 0x180000
    for offset in [0, 0x20000]:
        ecc.write_data(target, offset, mlo.ljust((len(mlo) + 2047) // 2048 * 2048, b"\xff"))
    for offset in [0x40000, 0x1C0000]:
        ecc.write_data(target, offset, uboot.ljust((len(uboot) + 2047) // 2048 * 2048, b"\xff"))
    env = {"stdin": "serial", "stdout": "serial", "stderr": "serial",
           "baudrate": "115200", "bootdelay": "1"}
    env["bootargs"] = (
        "console=tty0 consoleblank=0 console=ttyS0,115200 earlycon=uart8250,mmio32,0x4806a000 loglevel=7 systemd.show_status=error ubi.mtd=2,2048 root=ubi0:rootfs rootfstype=ubifs rw clk_ignore_unused fbcon=rotate:0"
    )
    env["bootcmd"] = "nboot.i 0x81000000 0 0x400000; bootm 0x81000000"
    for generation, offset in [(1, 0x340000), (0, 0x3A0000)]:
        ecc.save_env(target, offset, generation, env)
    ecc.write_data(
        target, 0x400000, kernel.ljust((len(kernel) + 2047) // 2048 * 2048, b"\xff")
    )
    polynomial = bytes.fromhex("2813cc3996ac7f")
    for offset in range(0, len(ubi), 2048):
        data = ubi[offset : offset + 2048].ljust(2048, b"\xff")
        oob = bytearray(b"\xff" * 64)
        for sector in range(4):
            raw = parity(data[sector * 512 : (sector + 1) * 512])
            modern = (raw << 4).to_bytes(7, "big")
            modern = bytes(x ^ y for x, y in zip(modern, polynomial))
            oob[2 + sector * 8 : 9 + sector * 8] = modern
            oob[36 + sector * 7 : 43 + sector * 7] = raw.to_bytes(7, "big")
        target.seek((0xC00000 + offset) // 2048 * 2112)
        target.write(data + oob)
print(a.output)
