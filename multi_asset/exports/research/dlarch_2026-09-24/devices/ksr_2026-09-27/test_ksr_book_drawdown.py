#!/usr/bin/env python3
"""Synthetic regression for KSR rule §3; never opens research inputs or engine files.

Execute the reader's actual drawdown and verdict blocks because its CLI imports
a hash-pinned pod2 engine at module scope. The only substituted boundary is ser:
it returns in-memory 32-path returns; maxdd, aggregation and verdict are real.
"""
import os
from pathlib import Path
import unittest

import numpy as np


READER = Path(os.environ.get('KSR_BOOK_READER', Path(__file__).with_name('dlarch_ksr_book.py')))
SOURCE = READER.read_text()
DD_CODE = SOURCE.split('# ---- §3 (a)', 1)[1].split('# ---- §3 (b)', 1)[0]
DD_CODE = DD_CODE[DD_CODE.index('\ndef maxdd'):]
VERDICT_CODE = SOURCE.split('# ---- §2 book verdict (half)', 1)[1].split('# ---- descriptive:', 1)[0]


def measure(losses, baseline=(0.10, 0.10, 0.10), missing=()):
    """Two anchors/year: flat then a known NAV loss. Each loss is its maxDD."""
    returns = {}
    cmap = {arm: {f'm{k}': f'{arm}_m{k}' for k in range(8)} for arm in ('S0', 'S1')}
    for arm, drawdowns in [('S0', baseline), ('S1', losses)]:
        r = np.array([v for loss in drawdowns for v in (0.0, -loss)])
        for cell in cmap[arm].values():
            for seed in ('42', '2027'):
                returns[(cell, seed)] = {'r_per_path': np.tile(r, (32, 1))}
    seg = {f'H1_{year}': (np.arange(6) // 2 == i) & (year not in missing)
           for i, year in enumerate((2023, 2024, 2025))}
    context = {'np': np, 'ser': lambda c, s: returns[(c, s)], 'SEG': seg,
               'H1': (2023, 2024, 2025), 'MEM': list(cmap['S1']),
               'SEEDS': ('42', '2027'), 'cmap': cmap}
    exec(compile(DD_CODE, str(READER), 'exec'), context)
    # Positive book means isolate the veto: it must not be averaged away.
    context.update(rec={}, book={seg: {'D': 1.0, 'MBB95': [0.5, 1.5], 'SE_rule': 0.1}
                                for seg in ('H1_merged', 'H1_2023', 'H1_2024', 'H1_2025')})
    exec(compile(VERDICT_CODE, str(READER), 'exec'), context)
    return context['guard_dd'], context['rec']['BOOK']


class KSRDrawdownTest(unittest.TestCase):
    def test_one_bad_year_cannot_hide_in_three_year_average(self):
        for year, losses in [(2023, (0.14, 0.10, 0.10)),
                             (2024, (0.10, 0.14, 0.10)),
                             (2025, (0.10, 0.10, 0.14))]:
            with self.subTest(year=year):
                guard, book = measure(losses)
                self.assertTrue(guard['FAIL'], 'one H1 year is 4 pp worse')
                self.assertEqual(guard['failed_years'], [str(year)])
                self.assertTrue(book['REJECT'])
                self.assertFalse(book['NON_INFERIOR'])

    def test_good_years_cannot_cancel_bad_year(self):
        guard, book = measure((0.14, 0.0, 0.0))
        self.assertTrue(guard['FAIL'])
        self.assertTrue(book['REJECT'])

    def test_identity_is_zero_and_non_inferior(self):
        guard, book = measure((0.10, 0.10, 0.10))
        self.assertFalse(guard['FAIL'])
        self.assertEqual(guard['S1_minus_S0_pp'], 0.0)
        self.assertFalse(book['REJECT'])
        self.assertTrue(book['NON_INFERIOR'])

    def test_below_limit_in_every_year_passes(self):
        guard, book = measure((0.129, 0.128, 0.127))
        self.assertFalse(guard['FAIL'])
        self.assertTrue(book['NON_INFERIOR'])

    def test_returns_already_nav_no_second_gross_multiplier(self):
        guard, _ = measure((0.12, 0.10, 0.10))
        self.assertAlmostEqual(guard['per_year']['2023']['S1'], 0.12)
        self.assertFalse(guard['FAIL'])

    def test_missing_year_is_unavailable_not_a_partial_verdict(self):
        for year in (2023, 2024, 2025):
            with self.subTest(year=year):
                with self.assertRaisesRegex(SystemExit, f'UNAVAILABLE.*{year}'):
                    measure((0.10, 0.10, 0.10), missing=(year,))


if __name__ == '__main__':
    print(f'reader={READER}', flush=True)
    unittest.main(verbosity=2)
