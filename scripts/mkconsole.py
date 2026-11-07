#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Generate a twelve-line thermostat banner and a Linux console Braille font."""
import math
from pathlib import Path
import re
import struct
import sys

source = re.sub(r'/\*.*?\*/', '', Path(sys.argv[1]).read_text(), flags=re.S)
font = bytes(int(value, 16) for value in re.findall(r'0x([0-9a-fA-F]{2})\b', source))
assert len(font) == 4096
for mask in range(256):
    rows = [0] * 16
    for bit, x, y in [(0, 1, 1), (1, 1, 5), (2, 1, 9), (3, 5, 1),
                      (4, 5, 5), (5, 5, 9), (6, 1, 13), (7, 5, 13)]:
        if mask & (1 << bit):
            for dy in range(2):
                rows[y + dy] |= (0x80 >> x) | (0x80 >> (x + 1))
    font += bytes(rows)
font = struct.pack('<8I', 0x864ab572, 0, 32, 1, 512, 16, 16, 8) + font
for glyph in range(512):
    char = bytes([glyph]).decode('cp437') if glyph < 256 else chr(0x2800 + glyph - 256)
    font += char.encode() + b'\xff'
root = Path(sys.argv[2])
fontpath = root / 'usr/share/consolefonts/thermostat.psf'
fontpath.parent.mkdir(parents=True, exist_ok=True)
fontpath.write_bytes(font)

pixels = {}
for y in range(48):
    for x in range(48):
        radius = math.hypot(x - 23.5, y - 23.5)
        if 20.0 < radius <= 23.7:
            pixels[x, y] = 255 if 21.2 < radius < 23 else 244
# Seven-segment temperature readout: 72 degrees.
for x, segments in [(12, 'abc'), (25, 'abged')]:
    strokes = {'a': (x, 19, 8, 2), 'b': (x + 6, 20, 2, 7),
               'c': (x + 6, 26, 2, 7), 'd': (x, 32, 8, 2),
               'e': (x, 26, 2, 7), 'g': (x, 25, 8, 2)}
    for segment in segments:
        sx, sy, width, height = strokes[segment]
        for dy in range(height):
            for dx in range(width):
                pixels[sx + dx, sy + dy] = 208
for y in range(18, 24):
    for x in range(35, 41):
        if 1.2 < math.hypot(x - 37.5, y - 20.5) < 2.7:
            pixels[x, y] = 208
labels = {1: (sys.argv[3].upper() if len(sys.argv) > 3 else 'DIAMOND3', 51), 2: ('unfr0zen', 255), 4: ('Linux 7.3.1', 45),
          5: ('Bash + Starship', 114), 7: ('USB 192.168.77.1', 45),
          8: ('SSH root@192.168.77.1', 255), 10: ('UART / ACM / ECM', 244)}
if len(sys.argv) > 3 and sys.argv[3].lower() == 'onyx':
    labels[5] = ('Bash', 114)
    labels[7] = ('USB .77.1', 45)
    labels[8] = ('SSH', 255)
    labels[10] = ('ACM / ECM', 244)
if len(sys.argv) > 3 and sys.argv[3].lower() == 'j49':
    labels[5] = ('Starship', 114)
    labels[7] = ('192.168.77.1', 45)
    labels[8] = ('SSH :22', 255)
    labels[10] = ('ACM / ECM', 244)
lines = []
for row in range(12):
    line = ''
    for column in range(24):
        mask = 0
        colors = []
        for bit, dx, dy in [(0, 0, 0), (1, 0, 1), (2, 0, 2), (3, 1, 0),
                            (4, 1, 1), (5, 1, 2), (6, 0, 3), (7, 1, 3)]:
            color = pixels.get((column * 2 + dx, row * 4 + dy))
            if color is not None:
                mask |= 1 << bit
                colors.append(color)
        if row == 3 and 10 <= column < 14:
            line += '\x1b[38;5;255m' + 'nest'[column - 10]
        elif mask:
            color = 208 if 208 in colors else max(colors)
            line += f'\x1b[38;5;{color}m' + chr(0x2800 + mask)
        else:
            line += ' '
    if row in labels:
        text, color = labels[row]
        line += f'   \x1b[38;5;{color}m{text}'
    lines.append(line + '\x1b[0m')
(root / 'etc/issue').write_text('\n'.join(lines) + '\n\n')
