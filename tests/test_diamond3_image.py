"""Check the restore image's boot metadata without private device files."""
import hashlib
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class Diamond3ImageTests(unittest.TestCase):
    def test_restore_image_has_boot_copies_and_all_dbbt_records(self):
        with tempfile.TemporaryDirectory() as directory:
            images = Path(directory)
            boot = bytearray(0x2000)
            struct.pack_into('<8I', boot, 0x400, 0x402000D1, 0x87800000,
                             0, 0, 0x877FF420, 0x877FF400, 0, 0)
            struct.pack_into('<3I', boot, 0x420, 0x877FF000, len(boot), 0)
            loader = images / 'u-boot.bin'
            loader.write_bytes(boot)
            ubi = b'UBI#'.ljust(0x20000, b'\xff')
            (images / 'rootfs.ubi').write_bytes(ubi)
            output = images / 'diamond3.bin'
            subprocess.run([sys.executable, str(ROOT / 'scripts/diamond3-nand.py'),
                            '--images', str(images), '--uboot', str(loader),
                            '--output', str(output)], check=True, capture_output=True)
            self.assertEqual(output.stat().st_size, 512 * 1024 * 1024)
            with output.open('rb') as image:
                for offset in (0x80000, 0xA0000, 0xC0000, 0xE0000):
                    image.seek(offset)
                    self.assertEqual(struct.unpack('<5I', image.read(20)),
                                     (0, 0x54424244, 0x01000000, 0, 0))
                for offset in (0x100000, 0x280000):
                    image.seek(offset)
                    self.assertEqual(image.read(len(boot)), boot)
                image.seek(0x400000)
                self.assertEqual(image.read(len(ubi)), ubi)
                image.seek(0x1FF80000)
                self.assertEqual(image.read(), b'\xff' * 0x80000)
                sha = hashlib.sha256()
                image.seek(0)
                for chunk in iter(lambda: image.read(1048576), b''):
                    sha.update(chunk)
            self.assertEqual(output.with_suffix('.bin.sha256').read_text(),
                             sha.hexdigest() + '  diamond3.bin\n')


if __name__ == '__main__':
    unittest.main()
