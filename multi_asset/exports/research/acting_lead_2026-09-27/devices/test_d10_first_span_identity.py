"""Small input-only controls. No executor imports or simulations."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np

P = Path(__file__).with_name('d10_first_span_identity.py')
spec = importlib.util.spec_from_file_location('identity', P)
M = importlib.util.module_from_spec(spec)
spec.loader.exec_module(M)


class IdentityControls(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.a = 1785542400 + np.arange(120, dtype=np.int64) * 14400
        self.lo = int(self.a[0]) * 1000; self.hi = (int(self.a[-1]) + 14400) * 1000
        self.ledger = self.root / 'new_ms.npz'
        self.write_ledger([self.lo, self.lo + 100, self.lo + 900, self.hi, self.hi + 1])
        self.target = self.root / 'new_targets.npz'; self.target.write_bytes(b'new independently generated targets')
        self.consumer = self.root / 'new_ms_consumer.py'; self.consumer.write_text('# synthetic source identity only\n')
        self.identity = {'schema': 'd10-first-span-input-identity/1', 'assets': {
            'ms_ledger': {'path': str(self.ledger), 'resolved': str(self.ledger.resolve()), 'sha256': M.sha(self.ledger)},
            'targets': {'path': str(self.root / 'old_missing_targets.npz'), 'exists': False, 'sha256': None}}}
        self.manifest = self.root / 'identity.json'; self.manifest.write_text(json.dumps(self.identity))
        self.cfg = {'schema': 'd10-first-120-contract/1', 'identity_manifest_sha256': M.sha(self.manifest),
                    'anchors': self.a.tolist(), 'end_ms': self.hi,
                    'feature_known_offset_ms': 999, 'decision_offset_ms': 1440000,
                    'cash_interval': '(start,end]', 'funding_before_same_time_fill': True,
                    'funding': {'path': str(self.ledger), 'sha256': M.sha(self.ledger),
                                'field': 'ft_ms', 'dtype': '<i8', 'unit': 'millisecond',
                                'clock': 'economic_settlement', 'coalesce_seconds': False},
                    'consumer': {'kind': 'exact_ms_active_view', 'path': str(self.consumer), 'sha256': M.sha(self.consumer)},
                    'targets': {'path': str(self.target), 'sha256': M.sha(self.target), 'new_independent': True}}

    def write_ledger(self, times, field='ft_ms', dtype=np.int64, rates=None):
        np.savez(self.ledger, off=np.array([0, len(times)], np.int64),
                 symbols=np.array(['S']), rate=np.asarray(rates if rates is not None else [0.01] * len(times)),
                 **{field: np.asarray(times, dtype=dtype)})

    def run_input(self):
        return M.check_and_load(self.cfg, self.manifest, self.cfg['identity_manifest_sha256'])

    def rebind_ledger(self):
        self.cfg['funding']['sha256'] = self.identity['assets']['ms_ledger']['sha256'] = M.sha(self.ledger)
        self.manifest.write_text(json.dumps(self.identity)); self.cfg['identity_manifest_sha256'] = M.sha(self.manifest)

    def test_same_second_ms_rows_and_exact_end_are_retained(self):
        events, r = self.run_input()
        self.assertEqual(events['ft_ms'].tolist(), [self.lo + 100, self.lo + 900, self.hi])
        self.assertEqual(r['status'], 'INPUT_CONTRACT_PASS_CASH_UNVALIDATED')
        self.assertFalse(r['execution_ready'])
        self.assertEqual(r['loaded_funding']['path'], str(self.ledger))

    def test_wrong_end_or_anchor_count_refused(self):
        self.cfg['end_ms'] += 1
        with self.assertRaises(M.Unavailable): self.run_input()
        self.cfg['end_ms'] = self.hi; self.cfg['anchors'].pop()
        with self.assertRaises(M.Unavailable): self.run_input()

    def test_declared_clock_unit_and_field_mismatch_refused(self):
        for key, wrong in [('field', 'ft'), ('unit', 'second'), ('clock', 'producer_asof'), ('coalesce_seconds', True)]:
            original = self.cfg['funding'][key]; self.cfg['funding'][key] = wrong
            with self.assertRaises(M.Unavailable): self.run_input()
            self.cfg['funding'][key] = original

    def test_actual_schema_ft_and_float_ms_refused_even_if_rebound(self):
        self.write_ledger([self.lo + 100], field='ft'); self.rebind_ledger()
        with self.assertRaises(M.Unavailable): self.run_input()
        self.write_ledger([self.lo + 100], dtype=np.float64); self.rebind_ledger()
        with self.assertRaises(M.Unavailable): self.run_input()

    def test_wrong_actual_path_or_changed_file_refused(self):
        copy = self.root / 'another_ms.npz'; copy.write_bytes(self.ledger.read_bytes())
        self.cfg['funding']['path'] = str(copy)
        with self.assertRaises(M.Unavailable): self.run_input()
        self.cfg['funding']['path'] = str(self.ledger); self.ledger.write_bytes(b'changed')
        with self.assertRaises(M.Unavailable): self.run_input()

    def test_missing_or_old_borrowed_targets_refused(self):
        self.target.unlink()
        with self.assertRaises(M.Unavailable): self.run_input()
        self.target.write_bytes(b'new independently generated targets')
        self.cfg['targets']['path'] = self.identity['assets']['targets']['path']
        with self.assertRaises(M.Unavailable): self.run_input()

    def test_duplicate_exact_ms_or_nonfinite_rates_refused(self):
        self.write_ledger([self.lo + 100, self.lo + 100]); self.rebind_ledger()
        with self.assertRaises(M.Unavailable): self.run_input()
        self.write_ledger([self.lo + 100], rates=[float('nan')]); self.rebind_ledger()
        with self.assertRaises(M.Unavailable): self.run_input()

    def test_same_exact_ms_different_symbols_preserved(self):
        np.savez(self.ledger, off=np.array([0, 1, 2], np.int64), symbols=np.array(['S', 'T']),
                 rate=np.array([0.01, -0.02]), ft_ms=np.array([self.lo + 100] * 2, np.int64))
        self.rebind_ledger(); events, _ = self.run_input()
        self.assertEqual(events['symbol_index'].tolist(), [0, 1])
        self.assertEqual(events['rate'].tolist(), [0.01, -0.02])

    def test_seconds_mislabeled_as_ms_refused(self):
        self.write_ledger([int(self.a[0]) + 1]); self.rebind_ledger()
        with self.assertRaises(M.Unavailable): self.run_input()

    def test_manifest_or_consumer_source_changed_refused(self):
        self.consumer.write_text('# changed\n')
        with self.assertRaises(M.Unavailable): self.run_input()
        with self.assertRaises(M.Unavailable): M.check_and_load(self.cfg, self.manifest, '0' * 64)


if __name__ == '__main__': unittest.main(verbosity=2)
