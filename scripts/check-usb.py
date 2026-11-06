#!/usr/bin/env python3
"""Check ACM root-shell access and an ECM DHCP handshake through QEMU USB."""

import socket, select, time, struct, argparse, json, urllib.request
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument(
    "socket",
    nargs="?",
    default=str(Path(__file__).resolve().parents[1] / ".work/nand.usb.sock"),
)
parser.add_argument("--speed", choices=["hs", "fs"], default="hs")
parser.add_argument("--ui", help="UI URL for testing the cable switch")
parser.add_argument(
    "--discovery-hostname", help="Also check NetBIOS and mDNS hostname replies"
)
args = parser.parse_args()
s = socket.socket(socket.AF_UNIX)
s.connect(args.socket)
buffer = b""


def line(prefix, timeout=5):
    global buffer
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if b"\n" in buffer:
            value, buffer = buffer.split(b"\n", 1)
            if value.startswith(prefix):
                return value.decode()
        elif select.select([s], [], [], 0.1)[0]:
            chunk = s.recv(65536)
            if not chunk:
                raise RuntimeError("bridge closed")
            buffer += chunk
    raise TimeoutError(prefix)


def cmd(value):
    s.sendall((value + "\n").encode())


def token(ep, direction, data):
    for _ in range(1000):
        cmd(f"TOKEN{direction} {ep} {data}")
        answer = line(f"TOKEN {ep} {direction} ".encode())
        if " ACK" in answer:
            return (
                bytes.fromhex(answer.split(" ACK", 1)[1].strip())
                if direction == "IN"
                else int(answer.split(" ACK", 1)[1].strip())
            )
        if "ERROR" in answer or "STALL" in answer:
            raise RuntimeError(answer)
        time.sleep(0.01)
    raise TimeoutError(answer)


def control(bm, request, value=0, index=0, length=0, data=b""):
    if data:
        length = len(data)
    setup = struct.pack("<BBHHH", bm, request, value, index, length)
    cmd("SETUP " + setup.hex())
    line(b"SETUPACK")
    if bm & 128:
        result = b""
        while len(result) < length:
            packet = token(0, "IN", str(length - len(result)))
            result += packet
            if len(packet) < 64 or len(packet) % 64:
                break
        token(0, "OUT", "")
        return result
    if data:
        token(0, "OUT", data.hex())
    token(0, "IN", "0")
    return b""


line(b"CONNECT")
cmd("SPEED " + args.speed)
cmd("RESET")
line(b"RESETDONE")
time.sleep(0.02)
print("device", control(128, 6, 0x100, length=18).hex())
control(0, 5, 1)
config = control(128, 6, 0x200, length=255)
print("config", config.hex())
interfaces = []
packet_sizes = {}
pos = 0
while pos < len(config):
    size, kind = config[pos : pos + 2]
    assert size >= 2
    d = config[pos : pos + size]
    if kind == 4:
        interface = {"num": d[2], "alt": d[3], "cls": d[5], "sub": d[6], "eps": []}
        interfaces.append(interface)
    elif kind == 5:
        interface["eps"].append((d[2], d[3] & 3))
        packet_sizes[d[2]] = struct.unpack("<H", d[4:6])[0]
    pos += size
print(interfaces)
assert all(
    size == (64 if args.speed == "fs" else 512)
    for i in interfaces
    for ep, kind in i["eps"]
    if kind == 2
    for size in [packet_sizes[ep]]
)
control(0, 9, 1)
acm = next(i for i in interfaces if i["cls"] == 2 and i["sub"] == 2)
acmdata = next(i for i in interfaces if i["num"] == acm["num"] + 1)
ecm = next(i for i in interfaces if i["cls"] == 2 and i["sub"] == 6)
ecmdata = next(i for i in interfaces if i["num"] == ecm["num"] + 1 and i["alt"] == 1)
control(1, 11, 1, ecmdata["num"])
control(0x21, 0x22, 3, acm["num"])
coding = struct.pack("<IBBB", 115200, 0, 0, 8)
control(0x21, 0x20, index=acm["num"], data=coding)
assert control(0xA1, 0x21, index=acm["num"], length=7) == coding
print("ACM line coding OK")


def endpoints(i):
    return next(ep & 127 for ep, typ in i["eps"] if typ == 2 and not ep & 128), next(
        ep & 127 for ep, typ in i["eps"] if typ == 2 and ep & 128
    )


aout, ain = endpoints(acmdata)
eout, ein = endpoints(ecmdata)


def write(ep, payload):
    while payload:
        done = token(ep, "OUT", payload.hex())
        if not done:
            time.sleep(0.01)
        payload = payload[done:]


prompt = b""
for _ in range(1000):
    prompt += token(ain, "IN", "4096")
    if b"root@" in prompt and b">" in prompt:
        break
else:
    raise RuntimeError("no ACM shell prompt")
write(aout, b"id; echo USB_ACM_OK\r")
console = b""
for _ in range(100):
    time.sleep(0.05)
    console += token(ain, "IN", "4096")
    if b"uid=0(root)" in console and b"USB_ACM_OK" in console:
        break
print("ACM", console.decode(errors="replace"))
assert b"uid=0(root)" in console
mac = bytes.fromhex("020000770002")
xid = 0x12345678


def checksum(data):
    words = struct.unpack("!%dH" % (len(data) // 2), data)
    total = sum(words)
    while total >> 16:
        total = (total & 65535) + (total >> 16)
    return (~total) & 65535


def dhcp(kind, requested=None):
    bootp = struct.pack(
        "!BBBBIHH4s4s4s4s16s64s128s",
        1,
        1,
        6,
        0,
        xid,
        0,
        0x8000,
        b"\0" * 4,
        b"\0" * 4,
        b"\0" * 4,
        b"\0" * 4,
        mac + b"\0" * 10,
        b"\0" * 64,
        b"\0" * 128,
    )
    opts = b"\x63\x82\x53\x63\x35\x01" + bytes([kind]) + b"\x37\x03\x01\x03\x06"
    if requested:
        opts += b"\x32\x04" + requested + b"\x36\x04" + socket.inet_aton("192.168.77.1")
    payload = bootp + opts + b"\xff"
    udp = struct.pack("!HHHH", 68, 67, len(payload) + 8, 0) + payload
    ip = struct.pack(
        "!BBHHHBBH4s4s", 0x45, 0, len(udp) + 20, 1, 0, 64, 17, 0, b"\0" * 4, b"\xff" * 4
    )
    ip = ip[:10] + struct.pack("!H", checksum(ip)) + ip[12:]
    return b"\xff" * 6 + mac + b"\x08\x00" + ip + udp


def read_frame(ep):
    frame = b""
    while True:
        packet = token(ep, "IN", "4096")
        frame += packet
        if len(packet) < packet_sizes[ep | 128]:
            return frame


def reply(kind):
    for _ in range(30):
        frame = read_frame(ein)
        if len(frame) < 282 or frame[12:14] != b"\x08\x00":
            continue
        header = 14 + (frame[14] & 15) * 4
        packet = frame[header + 8 :]
        if len(packet) < 240 or struct.unpack("!I", packet[4:8])[0] != xid:
            continue
        pos = 240
        options = {}
        while pos < len(packet):
            opt = packet[pos]
            pos += 1
            if opt == 255:
                break
            if opt == 0:
                continue
            size = packet[pos]
            pos += 1
            options[opt] = packet[pos : pos + size]
            pos += size
        if options.get(53) == bytes([kind]):
            return packet[16:20]
    raise RuntimeError("no DHCP reply")


acm_notify = next(ep & 127 for ep, kind in acm["eps"] if kind == 3)
notice = token(acm_notify, "IN", "64")
assert notice[:2] == bytes([0xA1, 0x20]) and len(notice) == 10
ecm_notify = next(ep & 127 for ep, kind in ecm["eps"] if kind == 3)
notice = token(ecm_notify, "IN", "64")
assert notice[:2] == bytes([0xA1, 0]) and len(notice) == 8
for _ in range(6):
    notice = token(ecm_notify, "IN", "64")
    if notice[:2] == bytes([0xA1, 0x2A]):
        assert len(notice) == 16
        break
    assert notice[:2] == bytes([0xA1, 0]) and len(notice) == 8
else:
    raise AssertionError("no ECM speed notification")
print("ACM/ECM interrupt notifications OK")
control(0x21, 0x43, 0x0F, ecm["num"])
control(2, 3, 0, eout)
try:
    token(eout, "OUT", "")
except RuntimeError as error:
    assert "STALL" in str(error)
else:
    raise AssertionError("halted endpoint accepted OUT")
control(2, 1, 0, eout)
print("endpoint halt/clear OK")
write(eout, dhcp(1))
offered = reply(2)
print("DHCPOFFER", socket.inet_ntoa(offered))
write(eout, dhcp(3, offered))
leased = reply(5)
print("DHCPACK", socket.inet_ntoa(leased))
assert leased == offered
device_mac = bytes.fromhex("020000770001")
host_ip = leased
device_ip = socket.inet_aton("192.168.77.1")
arp = struct.pack("!HHBBH", 1, 0x800, 6, 4, 1) + mac + host_ip + bytes(6) + device_ip
write(eout, bytes.fromhex("ffffffffffff") + mac + b"\x08\x06" + arp)
for _ in range(30):
    frame = read_frame(ein)
    if frame[12:14] == b"\x08\x06" and frame[20:22] == b"\x00\x02":
        break
else:
    raise AssertionError("no ARP reply")
payload = bytes(range(256)) * 4
icmp = struct.pack("!BBHHH", 8, 0, 0, 0x1234, 1) + payload
icmp = icmp[:2] + struct.pack("!H", checksum(icmp)) + icmp[4:]
ip = struct.pack(
    "!BBHHHBBH4s4s", 0x45, 0, len(icmp) + 20, 2, 0, 64, 1, 0, host_ip, device_ip
)
ip = ip[:10] + struct.pack("!H", checksum(ip)) + ip[12:]
write(eout, device_mac + mac + b"\x08\x00" + ip + icmp)
for _ in range(30):
    frame = read_frame(ein)
    if frame[12:14] == b"\x08\x00" and frame[23] == 1:
        packet = frame[14 + (frame[14] & 15) * 4 :]
        if packet[0] == 0 and packet[4:8] == icmp[4:8]:
            assert packet[8:] == payload and checksum(packet) == 0, (
                len(frame),
                len(packet),
                frame[16:18].hex(),
                packet[:32].hex(),
                packet[-32:].hex(),
            )
            break
else:
    raise AssertionError("no ICMP echo reply")
print("1024-byte ICMP payload round-trip OK")

if args.discovery_hostname:

    def udp_query(port, payload):
        udp = struct.pack("!HHHH", 49152, port, len(payload) + 8, 0) + payload
        ip = struct.pack(
            "!BBHHHBBH4s4s", 0x45, 0, len(udp) + 20, 3, 0, 64, 17, 0, host_ip, device_ip
        )
        ip = ip[:10] + struct.pack("!H", checksum(ip)) + ip[12:]
        write(eout, device_mac + mac + b"\x08\x00" + ip + udp)
        for _ in range(30):
            frame = read_frame(ein)
            if len(frame) < 42 or frame[12:14] != b"\x08\x00" or frame[23] != 17:
                continue
            offset = 14 + (frame[14] & 15) * 4
            source, destination = struct.unpack("!HH", frame[offset : offset + 4])
            data = frame[offset + 8 :]
            if source == port and destination == 49152 and data[:2] == payload[:2]:
                return data
        raise AssertionError(f"No hostname response on UDP {port}")

    name = args.discovery_hostname.upper().encode().ljust(15, b" ") + b"\0"
    encoded = bytes(v for n in name for v in (65 + (n >> 4), 65 + (n & 15)))
    query = struct.pack("!HHHHHH", 0x4E42, 0x110, 1, 0, 0, 0)
    query += b"\x20" + encoded + b"\0" + struct.pack("!HH", 32, 1)
    response = udp_query(137, query)
    assert response[6:8] == b"\0\x01" and response[-4:] == device_ip, response.hex()
    labels = args.discovery_hostname + ".local"
    dns_name = (
        b"".join(bytes([len(part)]) + part.encode() for part in labels.split("."))
        + b"\0"
    )
    query = struct.pack("!HHHHHH", 0x4D44, 0, 1, 0, 0, 0)
    query += dns_name + struct.pack("!HH", 1, 1)
    response = udp_query(5353, query)
    assert response[2] & 0x80 and device_ip in response, response.hex()
    print("NetBIOS and mDNS hostname resolution OK")
cmd("RESET")
line(b"RESETDONE")
assert len(control(128, 6, 0x100, length=18)) == 18
try:
    control(128, 255, length=1)
except RuntimeError as error:
    assert "STALL" in str(error)
else:
    raise AssertionError("invalid request did not stall")
assert len(control(128, 6, 0x100, length=18)) == 18
print("reset and control stall recovery OK")
if args.ui:

    def cable(connected):
        request = urllib.request.Request(
            args.ui.rstrip("/") + "/usb",
            data=json.dumps({"connected": connected}).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request) as response:
            return json.load(response)

    state = cable(False)
    assert not state["vbus"]
    line(b"DISCONNECT")
    time.sleep(0.1)
    state = cable(True)
    assert state["vbus"]
    line(b"CONNECT")
    # USB hosts debounce attachment before reset and allow reset recovery.
    time.sleep(0.1)
    cmd("RESET")
    line(b"RESETDONE")
    time.sleep(0.02)
    assert len(control(128, 6, 0x100, length=18)) == 18
    print("cable reconnect OK")
s.close()
