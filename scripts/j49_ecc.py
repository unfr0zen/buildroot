"""J49 legacy BCH4 parity and redundant U-Boot environments."""
import struct
import zlib

PAGE, PAGE_RAW = 2048, 2112
ENV_SIZE = 0x20000
BCH4_G = 0x4523043AB86AB


def bch4_parity(data):
    value = 0
    for byte in data:
        for bit in range(7, -1, -1):
            feedback = bool(value & (1 << 51)) ^ ((byte >> bit) & 1)
            value = (value << 1) & ((1 << 52) - 1)
            if feedback:
                value ^= BCH4_G
    return value


def write_data(file, offset, data):
    assert offset % PAGE == 0 and len(data) % PAGE == 0
    for index in range(len(data) // PAGE):
        file.seek((offset // PAGE + index) * PAGE_RAW)
        raw = bytearray(file.read(PAGE_RAW))
        raw[:PAGE] = data[index * PAGE:(index + 1) * PAGE]
        for sector in range(4):
            block = raw[sector * 512:(sector + 1) * 512]
            at = PAGE + 36 + sector * 7
            raw[at:at + 7] = (b'\xff' * 7 if block == b'\xff' * 512
                              else bch4_parity(block).to_bytes(7, 'big'))
        file.seek((offset // PAGE + index) * PAGE_RAW)
        file.write(raw)


def save_env(file, offset, generation, env):
    body = b'\0'.join(f'{key}={value}'.encode() for key, value in env.items()) + b'\0\0'
    assert len(body) <= ENV_SIZE - 5
    body = body.ljust(ENV_SIZE - 5, b'\0')
    write_data(file, offset, struct.pack('<IB', zlib.crc32(body), generation) + body)
