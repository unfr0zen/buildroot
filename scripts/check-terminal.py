#!/usr/bin/env python3
"""Exercise nest-terminal with real PTYs; run on Linux with a native binary."""

import fcntl
import os
import pty
import select
import signal
import struct
import subprocess
import sys
import termios
import time

master, slave = pty.openpty()
original = termios.tcgetattr(slave)
fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", 24, 80, 0, 0))
child = """import fcntl, os, signal, struct, termios, tty

def size(*args):
 rows, columns, _, _ = struct.unpack('HHHH', fcntl.ioctl(0, termios.TIOCGWINSZ, bytes(8)))
 print('SIZE:%d:%d' % (rows, columns), flush=True)

tty.setraw(0)
signal.signal(signal.SIGWINCH, size)
size()
while True:
 data = os.read(0, 128)
 if data == b'q': break
 print('INPUT:' + data.hex(), flush=True)
raise SystemExit(13)
"""
process = subprocess.Popen(
    [sys.argv[1], sys.executable, "-u", "-c", child],
    stdin=slave,
    stdout=slave,
    stderr=slave,
    env={**os.environ, "TERM": "xterm-256color"},
)
buffer = b""


def expect(value):
    global buffer
    end = time.monotonic() + 5
    while value not in buffer and time.monotonic() < end:
        if select.select([master], [], [], 0.1)[0]:
            buffer += os.read(master, 65536)
    assert value in buffer, (value, buffer)
    buffer = buffer.split(value, 1)[1]


try:
    expect(b"SIZE:24:80")
    os.write(master, b"\x1b[8;37;")
    time.sleep(0.01)
    os.write(master, b"119t")
    expect(b"SIZE:37:119")
    os.write(master, b"\x1b[A")
    expect(b"INPUT:1b5b41")
    os.write(master, b"\x1b")
    expect(b"INPUT:1b")
    fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", 45, 132, 0, 0))
    os.kill(process.pid, signal.SIGWINCH)
    expect(b"SIZE:45:132")
    os.write(master, b"q")
    assert process.wait(timeout=5) == 13
    assert termios.tcgetattr(slave) == original
    print(
        "window reports, SIGWINCH, escape keys, exit status and termios restoration OK"
    )
finally:
    if process.poll() is None:
        process.terminate()
        process.wait(timeout=5)
    os.close(master)
    os.close(slave)
