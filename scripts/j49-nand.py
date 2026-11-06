#!/usr/bin/env python3
"""Create a QEMU J49 raw NAND, retaining the supplied bootloader region."""

import argparse
import importlib.util
from pathlib import Path

root = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--stock", type=Path, required=True)
p.add_argument("--output", type=Path, default=root / ".work/j49-nand.raw")
a = p.parse_args()
spec = importlib.util.spec_from_file_location(
    "j49_env", root.parent / "qemu/boards/j49/j49_env.py"
)
ecc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ecc)
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
images = root / "output/j49/images"
kernel = (images / "uImage").read_bytes()
ubi = (images / "rootfs.ubi").read_bytes()
assert len(kernel) <= 0x800000 and len(ubi) <= 0xF400000
assert a.stock.resolve() != a.output.resolve()
a.output.parent.mkdir(parents=True, exist_ok=True)
with a.stock.open("rb") as source, a.output.open("wb") as target:
    boot = source.read(0x400000 // 2048 * 2112)
    assert len(boot) == 0x400000 // 2048 * 2112
    target.write(boot)
    remaining = 0x10000000 // 2048 * 2112 - len(boot)
    while remaining:
        count = min(remaining, 1048576)
        target.write(b"\xff" * count)
        remaining -= count
with a.output.open("r+b") as target:
    active = ecc.active_env(target)
    env = active[2]
    env.pop("silent", None)
    # The release U-Boot blanks the first console argument.
    env["bootargs"] = (
        "console= console=tty0 console=ttyS0,115200 earlycon=uart8250,mmio32,0x4806a000 ubi.mtd=2,2048 root=ubi0:rootfs rootfstype=ubifs rw clk_ignore_unused fbcon=rotate:1"
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
