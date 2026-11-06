#!/usr/bin/env python3
"""Exercise BlueZ on an isolated, logged-in Diamond3 QEMU console."""
import argparse
import json
import re
import time
import urllib.request

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--ui", required=True)
args = parser.parse_args()


def request(path, value=None):
    data = None if value is None else json.dumps(value).encode()
    with urllib.request.urlopen(
        urllib.request.Request(args.ui + path, data=data,
                               headers={"Content-Type": "application/json"}),
        timeout=5,
    ) as response:
        return json.load(response)


def command(text, timeout=40):
    offset = request("/console/read?since=0")["end"]
    marker = "__BLE_CHECK_DONE__"
    text += f"; printf '\\n{marker}:%s\\n' \"$?\""
    with urllib.request.urlopen(urllib.request.Request(
        args.ui + "/console/send", data=text.encode()
    ), timeout=5):
        pass
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        output = request(f"/console/read?since={offset}")["text"]
        output = re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", output).replace("\r", "")
        if re.search(rf"\n{marker}:\d+\n", output):
            assert f"\n{marker}:0\n" in output, output
            return output
        time.sleep(0.1)
    raise AssertionError(output)


def prop(name, value):
    result = request("/qmp", {"execute": "qom-set", "arguments": {
        "path": "/chardevs/diamond3-ble", "property": name, "value": value,
    }})
    assert "return" in result, result


peer = "/org/bluez/hci0/dev_02_00_00_00_00_01"
command("systemctl stop nest-ble-hci-test.service 2>/dev/null; true")
prop("hci-test-firmware", True)
prop("peer-present", True)
try:
    command("modprobe hci_uart && systemd-run --collect --unit=nest-ble-hci-test "
            "/usr/bin/btattach -B /dev/ttyble0 -P h4 -S 57600 -N")
    command("for n in 1 2 3 4 5 6 7 8 9 10; do "
            "busctl get-property org.bluez /org/bluez/hci0 org.bluez.Adapter1 "
            "Address >/dev/null 2>&1 && break; sleep 1; done; "
            "bluetoothctl power on; bluetoothctl --timeout 4 scan on")
    output = command(f"busctl get-property org.bluez {peer} org.bluez.Device1 Name")
    assert '"QEMU BLE test peer"' in output, output
    command("bluetoothctl --timeout 8 connect 02:00:00:00:00:01")
    output = command(f"busctl get-property org.bluez {peer} "
                     "org.bluez.Device1 ServicesResolved")
    assert "b true" in output, output
    output = command(f"busctl call org.bluez {peer}/service0006/char0007 "
                     "org.bluez.GattCharacteristic1 ReadValue 'a{sv}' 0")
    assert "ay 4 81 69 77 85" in output, output
    command("bluetoothctl disconnect 02:00:00:00:00:01")
    output = command(f"busctl get-property org.bluez {peer} org.bluez.Device1 Connected")
    assert "b false" in output, output
    print("PASS: BlueZ discovery, connection, GATT manufacturer read and disconnect")
finally:
    command("systemctl stop nest-ble-hci-test.service")
    prop("peer-present", False)
    prop("hci-test-firmware", False)
