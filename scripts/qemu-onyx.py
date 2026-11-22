#!/usr/bin/env python3
"""Boot the Onyx image through the public signed loader in an open-fuse emulator."""
import argparse
import os
from pathlib import Path
import re
import select
import shutil
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--qemu', type=Path, default=ROOT / 'qemu/qemu-src/build/qemu-system-arm')
parser.add_argument('--nand', type=Path)
parser.add_argument('--fresh', action='store_true')
parser.add_argument('--ui', action='store_true')
parser.add_argument('--port', type=int, default=8075)
parser.add_argument('--rom', type=Path, help='execute a complete 96 KiB i.MX6UL ROM dump')
parser.add_argument('--smoke', action='store_true')
args = parser.parse_args()
if args.ui and args.smoke:
    parser.error('--ui and --smoke cannot be combined')
args.nand = (args.nand or ROOT / ('.work/onyx-smoke.bin' if args.smoke else
                                 '.work/onyx-nand.bin')).resolve()
args.nand.parent.mkdir(parents=True, exist_ok=True)
if args.fresh or not args.nand.exists():
    shutil.copyfile(ROOT / 'output/onyx/images/onyx-buildroot.bin', args.nand)
command = [sys.executable, str(ROOT / 'qemu/boards/onyx/launch.py'),
           '--qemu', str(args.qemu.resolve()), '--nand', str(args.nand),
           '--open-security', '--nic', 'user,model=bcm43341,restrict=on']
if args.rom:
    command += ['--boot-rom', str(args.rom.resolve()), '--sdp-image',
                str(ROOT / 'output/onyx/images/u-boot-sdp-5.8d44-onyx-0NUR.hab'),
                '--sdp-fit', str(ROOT / 'output/onyx/images/kernel_fdt.itb')]
if args.ui:
    command += ['--ui', '--ui-port', str(args.port)]
if not args.smoke:
    os.execv(sys.executable, command)
child = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, start_new_session=True)
try:
    deadline = time.monotonic() + 180
    tail = b''
    logged_in = checked = False
    while time.monotonic() < deadline:
        if child.poll() is not None:
            raise SystemExit(f'QEMU exited before boot verification: {child.returncode}')
        if not select.select([child.stdout], [], [], 1)[0]:
            continue
        chunk = child.stdout.read1(65536)
        sys.stdout.buffer.write(chunk)
        sys.stdout.buffer.flush()
        tail = (tail + chunk)[-32768:]
        clean = re.sub(rb'\x1b\[[0-?]*[ -/]*[@-~]', b'', tail)
        if not logged_in and b'onyx login:' in tail:
            child.stdin.write(b'root\n'); child.stdin.flush()
            logged_in = True
        if logged_in and not checked and b'root@onyx' in clean:
            script = (ROOT / 'tests/onyx-hardware.sh').read_bytes()
            child.stdin.write(b"sh <<'END_TEST' && echo ONYX_SMOKE_OK "
                              b"|| echo ONYX_SMOKE_FAILED\n" + script +
                              b"END_TEST\n")
            child.stdin.flush()
            checked = True
            tail = b''
        if checked and b'\nONYX_SMOKE_FAILED' in tail:
            raise SystemExit('Onyx hardware smoke test failed')
        if checked and b'\nONYX_SMOKE_OK' in tail:
            break
    else:
        raise SystemExit('Onyx root-shell smoke test timed out')
finally:
    if child.poll() is None:
        os.killpg(child.pid, signal.SIGTERM)
    try:
        child.wait(timeout=5)
    except subprocess.TimeoutExpired:
        os.killpg(child.pid, signal.SIGKILL)
        child.wait()
