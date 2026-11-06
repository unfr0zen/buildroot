#!/usr/bin/env python3
"""Check backplate framing and sensor units using a native Linux PTY."""

import binascii
import os
from pathlib import Path
import pty
import struct
import subprocess
import sys
import time

master, slave = pty.openpty()
serial = Path("/dev/ttysensormcu0")
assert not serial.exists(), "Run in an isolated container without a sensor UART"
serial.symlink_to(os.ttyname(slave))
process = subprocess.Popen([sys.argv[1]])
state = Path("/run/nest/backplate.state")


def frame(kind, data):
    packet = struct.pack("<HH", kind, len(data)) + data
    return b"\xd5\xaa\x96" + packet + struct.pack("<H", binascii.crc_hqx(packet, 0))


def readings():
    return dict(line.split("=", 1) for line in state.read_text().splitlines())


def expect(key, value):
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        if state.exists() and readings().get(key) == str(value):
            return
        time.sleep(0.05)
    raise AssertionError((key, value, readings() if state.exists() else "no state"))


try:
    time.sleep(0.3)
    sample = frame(2, struct.pack("<hH", 2150, 450))
    os.write(master, b"noise" + sample[:4])
    time.sleep(0.05)
    os.write(master, sample[4:])
    expect("temperature_centi_c", 2150)
    expect("humidity_permille", 450)
    invalid = bytearray(frame(2, struct.pack("<hH", 9999, 999)))
    invalid[-1] ^= 1
    os.write(master, invalid)
    time.sleep(0.1)
    expect("temperature_centi_c", 2150)
    os.write(master, frame(10, struct.pack("<HH", 200, 60)))
    expect("light_visible_raw", 200)
    expect("light_infrared_raw", 60)
    os.write(master, frame(5, struct.pack("<HH", 1, 0)))
    expect("motion", 1)
    os.write(master, frame(2, struct.pack("<HH", 0x8000, 0xFFFF)))
    expect("temperature_centi_c", -2147483648)
    expect("humidity_permille", -1)
    print("PASS: split frames, CRC rejection, sensor units and unavailable readings")
finally:
    process.terminate()
    process.wait(timeout=5)
    serial.unlink()
    os.close(master)
    os.close(slave)
