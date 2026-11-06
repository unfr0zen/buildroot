#!/usr/bin/env python3
"""Boot an isolated logical NAND through the user's unchanged signed U-Boot."""
import argparse
import os
import re
from pathlib import Path
import select
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--uboot', type=Path, required=True)
p.add_argument('--qemu', type=Path, default=ROOT.parent / 'qemu/qemu-src/build/qemu-system-arm')
p.add_argument('--ui', action='store_true')
p.add_argument('--port', type=int, default=8075)
p.add_argument('--nand', type=Path, default=ROOT / '.work/nand.bin')
p.add_argument('--fresh', action='store_true')
p.add_argument('--smoke', action='store_true', help='exit after confirming the root shell')
a = p.parse_args()
images = ROOT / 'output/images'
nand = a.nand.resolve()
nand.parent.mkdir(exist_ok=True)
if a.fresh or not nand.exists():
    pieces = [(0x100000, a.uboot, 0x180000), (0x280000, a.uboot, 0x180000),
              (0x400000, images / 'rootfs.ubi', 0x1fc00000)]
    for _, source, limit in pieces:
        if source.stat().st_size > limit:
            raise SystemExit(f'{source} exceeds its NAND reservation')
    with nand.open('wb') as f:
        for _ in range(512):
            f.write(b'\xff' * 1048576)
        for offset, source, _ in pieces:
            f.seek(offset)
            f.write(source.read_bytes())
usb_socket = nand.with_suffix('.usb.sock')
usb_socket.unlink(missing_ok=True)
command = [str(a.qemu), '-M', 'diamond3,usb0-hostchar=usbhost', '-drive', f'file={nand},if=none,id=nand,format=raw',
           '-display', 'none', '-monitor', 'none', '-serial', 'stdio', '-nic', 'user,model=bcm43341',
           '-global', 'driver=imx.pwm,property=clock-frequency,value=66000000',
           '-chardev', f'socket,id=usbhost,path={usb_socket},server=on,wait=off']
if a.ui:
    if a.smoke:
        raise SystemExit('--ui and --smoke cannot be combined')
    sockets = [ROOT / '.work' / name for name in ['console.sock', 'board.sock', 'qmp.sock']]
    for path in sockets:
        path.unlink(missing_ok=True)
    command[command.index('stdio')] = 'chardev:con'
    command += ['-chardev', f'socket,id=con,path={sockets[0]},server=on,wait=off',
                '-chardev', f'socket,id=boardui,path={sockets[1]},server=on,wait=off',
                '-global', 'driver=flintstone.board,property=chardev,value=boardui',
                '-qmp', f'unix:{sockets[2]},server=on,wait=off']
    child = subprocess.Popen(command)
    ui = subprocess.Popen([sys.executable, str(ROOT.parent / 'qemu/ui/ui.py'),
        '--board', str(sockets[1]), '--console', str(sockets[0]), '--qmp', str(sockets[2]),
        '--screen-file', str(ROOT / '.work/screen.ppm'), '--port', str(a.port),
        '--name', 'Diamond3 Buildroot', '--echo-console', '--parent', str(os.getpid()),
        '--pins', 'button=HU-BUTTON,poweroff=POWEROFF,wifi_reset=WIFI-RESET,hall_enable=HALL-ENABLE'])
    print(f'QEMU UI: http://127.0.0.1:{a.port}', flush=True)
    try:
        child.wait()
    finally:
        ui.terminate()
        if child.poll() is None:
            child.terminate()
        child.wait()
        ui.wait()
    raise SystemExit(child.returncode)
child = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
tail = b''
booted = False
checked = False
deadline = time.monotonic() + 180
try:
    while child.poll() is None:
        if a.smoke and time.monotonic() > deadline:
            raise SystemExit("root-shell smoke test timed out")
        ready, _, _ = select.select([child.stdout] + ([] if a.smoke else [sys.stdin.buffer]), [], [], 1)
        if child.stdout in ready:
            data = child.stdout.read1(65536)
            if not data:
                break
            sys.stdout.buffer.write(data)
            sys.stdout.buffer.flush()
            tail = (tail + data)[-8192:]
            if b'Starting kernel' in tail:
                booted = True
            if a.smoke and b'diamond3 login:' in tail:
                child.stdin.write(b'root\n')
                child.stdin.flush()
                tail = b''
            clean = re.sub(rb'\x1b\[[0-?]*[ -/]*[@-~]', b'', tail)
            if a.smoke and not checked and booted and b'root@diamond3' in clean:
                checked = True
                child.stdin.write(b'id; uname -r; df -h /; echo DIAMOND3_SMOKE_OK\n')
                child.stdin.flush()
                tail = b''
            if a.smoke and b'uid=0(root)' in tail and b'7.3.1' in tail and b'\r\nDIAMOND3_SMOKE_OK\r\n' in tail and b'ubi0:rootfs' in tail:
                break
        if not a.smoke and sys.stdin.buffer in ready:
            data = sys.stdin.buffer.read1(4096)
            if not data:
                break
            child.stdin.write(data)
            child.stdin.flush()
finally:
    child.terminate()
    child.wait(timeout=10)
