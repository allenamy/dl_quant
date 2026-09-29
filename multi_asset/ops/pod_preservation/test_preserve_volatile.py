"""Offline small-file checks; no Pod, venue, or production calls."""
import importlib.util
import os
from pathlib import Path
import tarfile
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('preserve', Path(__file__).with_name('preserve_volatile.py'))
pv = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pv)


class ArchiveChecks(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.src, self.out = root/'source', root/'out'
        self.src.mkdir(); self.out.mkdir()
        (self.src/'model').write_bytes(b'fixed-model-bytes'*100)
        (self.src/'absolute_link').symlink_to('/workspace/frozen/artifact')
        os.link(self.src/'model', self.src/'model_hardlink')
        (self.src/'nested').mkdir()
        (self.src/'nested'/'config').write_text('{"seed":42}\n')
        pv.pack(self.src, 'shm', self.out, set())

    def tearDown(self):
        self.tmp.cleanup()

    def test_contents_links_and_independent_archive_digest(self):
        r = pv.verify('shm', self.out)
        self.assertEqual(r['status'], 'PASS')
        self.assertEqual(r['entries_verified'], 6)
        self.assertEqual(r['sha256'], pv.sha(self.out/'shm.tar'))

    def test_corrupted_member_refused(self):
        with tarfile.open(self.out/'shm.tar') as tf:
            pos = tf.getmember('shm/model').offset_data
        with (self.out/'shm.tar').open('r+b') as f:
            f.seek(pos); f.write(b'!')
        with self.assertRaisesRegex(RuntimeError, 'content mismatch'):
            pv.verify('shm', self.out)

    def test_changed_original_refused(self):
        (self.src/'model').write_text('changed source')
        with self.assertRaisesRegex(RuntimeError, 'Source changed'):
            pv.verify('shm', self.out)

    def test_missing_original_refused(self):
        (self.src/'model').unlink()
        with self.assertRaisesRegex(RuntimeError, 'Source changed'):
            pv.verify('shm', self.out)

    def test_restore_verification_does_not_need_volatile_original(self):
        (self.src/'model').unlink()
        r = pv.verify('shm', self.out, check_source=False)
        self.assertEqual(r['status'], 'PASS')

    def test_truncation_refused(self):
        with (self.out/'shm.tar').open('r+b') as f:
            f.truncate(2048)
        with self.assertRaises((RuntimeError, tarfile.TarError)):
            pv.verify('shm', self.out)

    def test_repeat_verification_preserves_frozen_receipt(self):
        pv.verify('shm', self.out)
        path = self.out/'shm_verification.json'
        before = path.read_bytes()
        pv.verify('shm', self.out, check_source=False, write_receipt=False)
        self.assertEqual(before, path.read_bytes())


if __name__ == '__main__':
    unittest.main()
