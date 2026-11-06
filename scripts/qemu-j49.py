#!/usr/bin/env python3
"""Run the J49 image through source-built x-loader and U-Boot."""

import argparse
import os
import re
import select
import time
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--fresh", action="store_true")
p.add_argument("--ui", action="store_true")
p.add_argument("--smoke", action="store_true")
p.add_argument("--nand", type=Path, default=root / ".work/j49-nand.raw")
p.add_argument("--port", type=int, default=8076)
p.add_argument("--qemu", type=Path,
               default=root / "qemu/qemu-src/build/qemu-system-arm",
               help="override the bundled emulator binary")
a = p.parse_args()
emulator = root / "qemu"
if not (emulator / "ui/backplate.py").is_file():
    p.error("QEMU submodule is missing; run make qemu-prepare")
if a.ui and a.smoke:
    p.error("--ui and --smoke cannot be combined")
nand = a.nand.resolve()
if a.fresh or not nand.exists():
    subprocess.run(
        [
            sys.executable,
            str(root / "scripts/j49-nand.py"),
            "--output",
            str(nand),
        ],
        check=True,
    )
usb_socket = nand.with_suffix(".usb.sock")
usb_socket.unlink(missing_ok=True)
command = [
    str(a.qemu),
    "-M",
    "j49",
    "-drive",
    f"file={nand},if=none,id=nand,format=raw",
    "-display",
    "none",
    "-monitor",
    "none",
    "-nic",
    "user,model=wl1271",
    "-global",
    "wl1271.fw-version=Rev 6.3.10.0.133",
    "-global",
    "driver=omap3-musb,property=hostchar,value=usbhost",
    "-chardev",
    f"socket,id=usbhost,path={usb_socket},server=on,wait=off",
]
sensor_socket = nand.with_suffix(".sensor.sock")
sensor_socket.unlink(missing_ok=True)
aux_socket = nand.with_suffix(".uart2.sock")
aux_socket.unlink(missing_ok=True)
command += [
    "-chardev",
    f"socket,id=sensor,path={sensor_socket},server=on,wait=off",
    "-chardev",
    f"socket,id=aux,path={aux_socket},server=on,wait=off",
]
backplate_command = [
    sys.executable,
    str(emulator / "ui/backplate.py"),
    "--serial",
    str(sensor_socket),
    "--board",
    "j49",
    "--parent",
    str(os.getpid()),
]
backplate_control = f"tcp:127.0.0.1:{a.port + 20}"
if a.ui:
    backplate_command += ["--control", backplate_control]
ui = None
if a.ui:
    work = nand.parent / (nand.stem + "-ui")
    work.mkdir(exist_ok=True)
    console, board, qmp = [
        work / name for name in ["console.sock", "board.sock", "qmp.sock"]
    ]
    for path in [console, board, qmp]:
        path.unlink(missing_ok=True)
    command += [
        "-serial",
        "chardev:con",
        "-serial",
        "chardev:aux",
        "-serial",
        "chardev:sensor",
        "-chardev",
        f"socket,id=con,path={console},server=on,wait=off",
        "-chardev",
        f"socket,id=boardui,path={board},server=on,wait=off",
        "-global",
        "driver=j49.board,property=chardev,value=boardui",
        "-qmp",
        f"unix:{qmp},server=on,wait=off",
    ]
else:
    command += [
        "-serial",
        "stdio",
        "-serial",
        "chardev:aux",
        "-serial",
        "chardev:sensor",
    ]
child = subprocess.Popen(
    command,
    stdin=subprocess.PIPE if a.smoke else None,
    stdout=subprocess.PIPE if a.smoke else None,
    stderr=subprocess.STDOUT if a.smoke else None,
)
backplate = subprocess.Popen(backplate_command)
if a.ui:
    ui = subprocess.Popen(
        [
            sys.executable,
            str(emulator / "ui/ui.py"),
            "--board",
            str(board),
            "--console",
            str(console),
            "--qmp",
            str(qmp),
            "--screen-file",
            str(work / "screen.ppm"),
            "--port",
            str(a.port),
            "--name",
            "J49 Buildroot",
            "--backplate",
            backplate_control,
            "--echo-console",
            "--parent",
            str(os.getpid()),
            "--pins",
            "button=HU-BUTTON,poweroff=POWEROFF,wifi_enable=WIFI-ENABLE,beeper_en=BEEPER-EN",
        ]
    )
    print(f"J49 UI: http://127.0.0.1:{a.port}", flush=True)
try:
    if a.smoke:
        tail = b""
        checked = False
        passed = False
        deadline = time.monotonic() + 180
        while child.poll() is None and time.monotonic() < deadline:
            if not select.select([child.stdout], [], [], 1)[0]:
                continue
            data = child.stdout.read1(65536)
            if not data:
                break
            sys.stdout.buffer.write(data)
            sys.stdout.buffer.flush()
            tail = (tail + data)[-8192:]
            if b"j49 login:" in tail:
                child.stdin.write(b"root\n")
                child.stdin.flush()
                tail = b""
            clean = re.sub(rb"\x1b\[[0-?]*[ -/]*[@-~]", b"", tail)
            if not checked and b"root@j49" in clean:
                checked = True
                child.stdin.write(b"id; uname -r; df -h /; echo J49_SMOKE_OK\n")
                child.stdin.flush()
                tail = b""
            if (
                b"uid=0(root)" in tail
                and b"7.3.1" in tail
                and b"ubi0:rootfs" in tail
                and b"\r\nJ49_SMOKE_OK\r\n" in tail
            ):
                passed = True
                break
        if not passed:
            raise SystemExit("J49 root-shell smoke test failed")
    else:
        child.wait()
finally:
    backplate.terminate()
    backplate.wait()
    if child.poll() is None:
        child.terminate()
    if ui:
        ui.terminate()
        ui.wait()
    child.wait()
raise SystemExit(0 if a.smoke else child.returncode)
