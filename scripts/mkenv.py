#!/usr/bin/env python3
"""Create redundant 64 KiB U-Boot environments for the Diamond3 UBI backend."""
import struct
import sys
import zlib
from pathlib import Path
board = Path(__file__).resolve().parents[1] / 'board/diamond3'
commands = [line.strip() for line in (board / 'boot.cmd').read_text().splitlines() if line.strip()]
values = {
    'bootcmd': '; '.join(commands),
    'bootdelay': '1',
    'mtdids': 'nand0=mx6_nand',
    'mtdparts': 'mtdparts=mx6_nand:4m(u-boot),-(ubipart)',
    'stdin': 'serial', 'stdout': 'serial', 'stderr': 'serial',
}
payload = b''.join(f'{key}={value}'.encode() + b'\0' for key, value in values.items()) + b'\0'
payload = payload.ljust(65536 - 5, b'\xff')
for name, generation in [('env0', 1), ('env1', 0)]:
    (Path(sys.argv[1]) / f'{name}.bin').write_bytes(struct.pack('<IB', zlib.crc32(payload), generation) + payload)
