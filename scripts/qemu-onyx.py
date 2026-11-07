#!/usr/bin/env python3
"""Boot the Onyx image through the public signed loader in an open-fuse emulator."""
import argparse
from pathlib import Path
import re
import select
import shutil
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
machine = 'onyx,secure-boot=off'
if args.rom:
    machine += ',boot-rom=' + str(args.rom.resolve())
if args.ui:
    command = [sys.executable, str(ROOT / 'qemu/boards/onyx/launch.py'),
               '--qemu', str(args.qemu.resolve()), '--nand', str(args.nand),
               '--ui', '--ui-port', str(args.port), '--open-security']
    if args.rom:
        command += ['--boot-rom', str(args.rom.resolve()), '--sdp-image',
                    str(ROOT / 'output/onyx/images/u-boot-sdp-5.8d44-onyx-0NUR.hab'),
                    '--sdp-fit', str(ROOT / 'output/onyx/images/kernel_fdt.itb')]
    raise SystemExit(subprocess.call(command))
command = [str(args.qemu), '-M', machine, '-drive',
           f'if=none,id=nand,format=raw,file={args.nand}',
           '-display', 'none', '-monitor', 'none', '-serial', 'stdio',
           '-nic', 'none', '-action', 'watchdog=none']
if args.rom and not args.smoke:
    raise SystemExit(subprocess.call([
        sys.executable, str(ROOT / 'qemu/boards/onyx/launch.py'),
        '--qemu', str(args.qemu.resolve()), '--nand', str(args.nand),
        '--open-security', '--boot-rom', str(args.rom.resolve()),
        '--sdp-image', str(ROOT / 'output/onyx/images/u-boot-sdp-5.8d44-onyx-0NUR.hab'),
        '--sdp-fit', str(ROOT / 'output/onyx/images/kernel_fdt.itb')]))
if not args.smoke:
    raise SystemExit(subprocess.call(command))
helper = None
if args.rom:
    usb_socket = args.nand.with_suffix('.usb.sock')
    usb_socket.unlink(missing_ok=True)
    command += ['-chardev', f'socket,id=onyxusb,path={usb_socket},server=on,wait=off',
                '-global', 'fsl-imx6ul.usb0-hostchar=onyxusb']
child = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT)
try:
    if args.rom:
        helper = subprocess.Popen([
            sys.executable, str(ROOT / 'qemu/boards/onyx/sdp.py'),
            '--socket', str(usb_socket), '--image',
            str(ROOT / 'output/onyx/images/u-boot-sdp-5.8d44-onyx-0NUR.hab'),
            '--fit', str(ROOT / 'output/onyx/images/kernel_fdt.itb')])
    deadline = time.monotonic() + 180
    tail = b''
    logged_in = checked = False
    while time.monotonic() < deadline:
        if helper and helper.poll() not in (None, 0):
            raise SystemExit('Onyx ROM SDP upload failed')
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
            child.stdin.write(b'id; uname -r; df -h /; echo ONYX_SMOKE_OK\n')
            child.stdin.flush()
            checked = True
            tail = b''
        if checked and b'uid=0(root)' in tail and b'ubi0:root0' in tail and b'\r\nONYX_SMOKE_OK' in tail:
            break
    else:
        raise SystemExit('Onyx root-shell smoke test timed out')
finally:
    if helper:
        if helper.poll() is None:
            helper.terminate()
        helper.wait(timeout=5)
    child.terminate()
    try:
        child.wait(timeout=5)
    except subprocess.TimeoutExpired:
        child.kill(); child.wait()
