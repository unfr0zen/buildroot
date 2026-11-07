#!/usr/bin/env python3
"""Download Nest's public signed Diamond3 SDP loader and package it for NAND."""
import argparse
import base64
import hashlib
from pathlib import Path
import struct
import urllib.request

URL = ('https://nest-open-source.googlesource.com/nest-learning-thermostat/5.7/'
       'u-boot/+/refs/heads/master/bin/diamond3/release/u-boot-sdp-5.2d43.hab?format=TEXT')
SHA256 = 'abbde0ce71d8764067ddc982b8ac4f49d27ad3d2587b44d92c55c8a73a5fe826'
NAME = 'u-boot-sdp-5.2d43'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--board', choices=['diamond3', 'onyx'], default='diamond3')
    args = parser.parse_args()
    global URL, SHA256, NAME
    if args.board == 'onyx':
        NAME = 'u-boot-sdp-5.8d44-onyx-0NUR'
        SHA256 = '1c204314ed1e536979e5512217e5baa386796500d6c0aca9460862aabb13b033'
        URL = ('https://nest-open-source.googlesource.com/nest-learning-thermostat/5.7/'
               'u-boot/+/refs/heads/master/bin/onyx/release/' + NAME + '.hab?format=TEXT')
    args.output.mkdir(parents=True, exist_ok=True)
    raw = args.output / (NAME + '.hab')
    if not raw.exists() or hashlib.sha256(raw.read_bytes()).hexdigest() != SHA256:
        with urllib.request.urlopen(URL, timeout=60) as response:
            data = base64.b64decode(response.read(), validate=False)
        if hashlib.sha256(data).hexdigest() != SHA256:
            raise SystemExit('public U-Boot download has an unexpected SHA-256')
        raw.write_bytes(data)
    data = raw.read_bytes()
    if data[:4] != bytes.fromhex('d1002040'):
        raise SystemExit('public U-Boot download has no SDP IVT')
    own = struct.unpack_from('<I', data, 20)[0]
    start, size = struct.unpack_from('<II', data, 32)
    if own - start != 0x400:
        raise SystemExit('unexpected SDP load address')
    # The signed SDP bytes begin at IVT.self; NAND reserves a leading 1 KiB.
    nand = b'\x00' * 0x400 + data
    nand = nand.ljust((max(size, len(nand)) + 2047) // 2048 * 2048, b'\xff')
    target = args.output / (NAME + '-nand.bin')
    target.write_bytes(nand)
    print(f'{raw}: SHA-256 {SHA256}')
    print(target)


if __name__ == '__main__':
    main()
