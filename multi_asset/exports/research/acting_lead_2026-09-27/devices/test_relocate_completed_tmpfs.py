import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import relocate_completed_tmpfs as r


class Relocation(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.src = self.root / 'source.bin'; self.src.write_bytes(b'original\x00\xff' * 100)
        self.dst = self.root / 'archive' / 'data.bin'; self.events = []

    def tearDown(self):
        self.tmp.cleanup()

    def run_copy(self):
        return r.relocate(self.src, self.dst, lambda s, v: self.events.append(s))

    def test_bytes_original_name_and_durable_order(self):
        expected = r.sha(self.src)
        self.run_copy()
        self.assertTrue(self.src.is_symlink())
        self.assertEqual(self.src.resolve(), self.dst)
        self.assertEqual(r.sha(self.src), expected)
        self.assertEqual(self.events, ['PREPARED', 'COMMITTED'])

    def test_hardlink_refused(self):
        os.link(self.src, self.root / 'other')
        with self.assertRaisesRegex(ValueError, 'regular file'):
            self.run_copy()
        self.assertFalse(self.src.is_symlink())

    def test_source_symlink_refused(self):
        data = self.root / 'original'; self.src.rename(data); self.src.symlink_to(data)
        with self.assertRaisesRegex(ValueError, 'regular file'):
            self.run_copy()

    def test_changed_source_refused(self):
        actual_sha = r.sha
        def corrupt_after_copy(p):
            if p == self.dst:
                self.src.write_bytes(b'changed')
            return actual_sha(p)
        with patch.object(r, 'sha', corrupt_after_copy):
            with self.assertRaisesRegex(ValueError, 'post-copy identity'):
                self.run_copy()
        self.assertFalse(self.src.is_symlink()); self.assertEqual(self.src.read_bytes(), b'changed')

    def test_wrong_destination_refused(self):
        with patch.object(r, 'sha', return_value='wrong'):
            with self.assertRaisesRegex(ValueError, 'post-copy identity'):
                self.run_copy()
        self.assertFalse(self.src.is_symlink())

    def test_durable_prepare_failure_keeps_original(self):
        def fail(*_):
            raise OSError('journal durability failed')
        with self.assertRaisesRegex(OSError, 'durability'):
            r.relocate(self.src, self.dst, fail)
        self.assertFalse(self.src.is_symlink())
        self.assertEqual(r.sha(self.src), r.sha(self.dst))

    def test_open_source_refused(self):
        with patch.object(r, 'assert_not_open', side_effect=ValueError('active fd')):
            with self.assertRaisesRegex(ValueError, 'active fd'):
                self.run_copy()
        self.assertFalse(self.dst.exists())


if __name__ == '__main__':
    unittest.main()
