#!/usr/bin/env python3
"""Check a native nbnsd in an isolated Linux container on UDP port 137."""

import socket, struct, subprocess, time, sys

p = subprocess.Popen([sys.argv[1], "-n", "diamond3"])
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.settimeout(0.5)
try:
    time.sleep(0.1)
    name = b"DIAMOND3".ljust(15, b" ") + b"\0"
    encoded = bytes(v for n in name for v in (65 + (n >> 4), 65 + (n & 15)))
    query = (
        struct.pack("!HHHHHH", 0x1234, 0x110, 1, 0, 0, 0)
        + b"\x20"
        + encoded
        + b"\0"
        + struct.pack("!HH", 32, 1)
    )
    for malformed in [
        b"",
        b"\0" * 12,
        query[:25],
        query[:12] + b"\xff" + query[13:],
        query[:13] + b"!" * 32 + query[45:],
    ]:
        s.sendto(malformed, ("127.0.0.1", 137))
    for _ in range(2):
        s.sendto(query, ("127.0.0.1", 137))
        response = s.recv(4096)
        assert (
            response[:2] == b"\x12\x34"
            and response[6:8] == b"\0\x01"
            and response[-4:] == socket.inet_aton("127.0.0.1")
        ), response
    print("PASS: repeated NetBIOS queries and malformed-packet recovery")
finally:
    p.terminate()
    p.wait()
