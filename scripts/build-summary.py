#!/usr/bin/env python3
"""Print the final build duration and host artifact location."""
import argparse
from pathlib import Path
import time

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--board', choices=['diamond3', 'j49'], required=True)
parser.add_argument('--images', type=Path, required=True)
parser.add_argument('--started', type=int, required=True)
parser.add_argument('--copied', action='store_true')
args = parser.parse_args()
minutes, seconds = divmod(int(time.time()) - args.started, 60)
print(f'\n=== Build finished in {minutes}m{seconds:02d}s ===')
location = args.images.resolve()
if args.copied:
    print(f'--- Artifacts copied to {location}/ (host) ---')
else:
    print(f'--- Artifacts available in {location}/ ---')
image = location / f'{args.board}-buildroot.bin'
if image.exists():
    print(f'  Flash image: {image}')
