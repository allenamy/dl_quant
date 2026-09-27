"""Known-answer lifecycle controls; no pod2 or research-data access."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('waiter', Path(__file__).with_name('ksr_readout_waiter.py'))
waiter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(waiter)
START = '2026-09-27T12:54:55Z KSR_START pgid=3479615 mode=run'


class WaiterTest(unittest.TestCase):
    def status(self, tail='', alive=True):
        return waiter.classify(START + '\n' + tail, START, alive)

    def test_alive_without_terminal_is_running(self):
        self.assertEqual(self.status(), 'RUNNING')

    def test_gone_without_terminal_is_explicit_failure(self):
        self.assertEqual(self.status(alive=False), 'GONE_WITHOUT_MARKER')

    def test_exact_done_allows_reader_even_after_driver_exit(self):
        self.assertEqual(self.status('2026-09-28T02:00:00Z KSR_DONE series=36 (+ baseline)\n', False), 'DONE')

    def test_stop_or_traceback_overrides_done(self):
        for failure in ['2026-09-28T02:00:01Z STOP: broken', 'Traceback (most recent call last):']:
            self.assertEqual(self.status('2026-09-28T02:00:00Z KSR_DONE series=36\n' + failure), 'FAILED')

    def test_embedded_or_wrong_count_done_does_not_unlock(self):
        for line in ['x says KSR_DONE series=36', '2026-09-28T02:00:00Z KSR_DONE series=360',
                     '2026-09-28T02:00:00Z KSR_DONE series=35']:
            self.assertEqual(self.status(line, False), 'GONE_WITHOUT_MARKER')

    def test_stale_done_before_start_does_not_unlock(self):
        self.assertEqual(waiter.classify('2026-09-27T00:00:00Z KSR_DONE series=36\n' + START, START, False), 'GONE_WITHOUT_MARKER')

    def test_replaced_log_or_new_run_refused(self):
        for text in ['', START + '\n2026-09-27T23:00:00Z KSR_START pgid=999 mode=run']:
            with self.assertRaises(ValueError):
                waiter.classify(text, START, True)

    def test_manifest_detects_mutation_after_binding(self):
        with tempfile.TemporaryDirectory() as root:
            p = Path(root) / 'input'; p.write_bytes(b'original')
            expected = {str(p): waiter.sha(p)}
            waiter.check_hashes(expected)
            p.write_bytes(b'mutated')
            with self.assertRaisesRegex(ValueError, 'sha mismatch'):
                waiter.check_hashes(expected)


if __name__ == '__main__':
    unittest.main(verbosity=2)
