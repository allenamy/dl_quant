#!/usr/bin/env python3
"""Known-answer controls only. Never opens Pod research files or candidate arrays."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

FILE = Path(__file__).with_name('ksr_terminal_audit.py')
DEV = None
if FILE.exists():
    spec = importlib.util.spec_from_file_location('ksr_terminal_audit', FILE)
    DEV = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(DEV)

W0 = 1696118400
AXIS = W0 + np.arange(12, dtype=np.int64) * 14400


def cell(r=0.0, price=0.0, carry=0.0, fee=0.0, unknown=0.0):
    z = {'anchors': AXIS.copy()}
    for key, value in [('r', r), ('pnl', price), ('car', carry), ('cst', fee), ('unk', unknown)]:
        z[key + '_per_path'] = np.broadcast_to(value, (32, 12)).copy().astype(float)
    z['g_per_path'] = z['r_per_path'] * 1e4 / 2
    return z


class TerminalAuditTest(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(DEV, 'postprocessor not implemented yet')

    def test_identity_all_terms_zero(self):
        z = cell(r=0.001, price=6, carry=0.5, fee=0.2)
        d = DEV.decompose_seed({k: z for k in DEV.ROLES}, np.ones(12, bool))
        for term in d['terms'].values():
            for value in term.values():
                np.testing.assert_array_equal(value, np.zeros((32, 2)))

    def test_known_interaction_is_four_term_baseline_adjusted(self):
        # One nonzero anchor per day removes within-day compounding from this control.
        one = np.tile([1, 0, 0, 0, 0, 0], 2)[None, :]
        paths = np.arange(1, 33)[:, None]
        z = {k: cell(r=one * paths * v * 1e-4, price=one * paths * v / 2)
             for k, v in [('BASE', 10), ('FULL', 17), ('SEAT', 12), ('COMP', 13)]}
        d = DEV.decompose_seed(z, np.ones(12, bool))
        expected = np.repeat(2 * paths, 2, axis=1)
        np.testing.assert_allclose(d['terms']['INTERACTION']['dbar_compounded_bps'], expected, atol=1e-11)
        np.testing.assert_allclose(d['terms']['INTERACTION']['pnl_NAV_bps'], expected, atol=1e-12)
        for metric in d['terms']['FULL']:
            got = d['terms']['FULL'][metric] - d['terms']['SEAT'][metric] - d['terms']['COMP'][metric]
            np.testing.assert_array_equal(d['terms']['INTERACTION'][metric], got)

    def test_compound_each_path_before_average_and_no_extra_gross(self):
        r = np.arange(32)[:, None] * np.ones((1, 12)) * 0.0001
        z = {k: cell() for k in DEV.ROLES}; z['FULL'] = cell(r=r)
        d = DEV.decompose_seed(z, np.ones(12, bool))
        expected = ((1 + r[:, 0]) ** 6 - 1) * 1e4
        np.testing.assert_allclose(d['terms']['FULL']['dbar_compounded_bps'][:, 0], expected, atol=1e-11)
        self.assertGreater(abs(expected.mean() - ((1 + r[:, 0].mean()) ** 6 - 1) * 1e4), 0.01)
        np.testing.assert_allclose(d['terms']['FULL']['g_NAV_bps'][:, 0], r[:, 0] * 6 * 1e4)

    def test_channel_units_paid_funding_and_compounding_gap_are_explicit(self):
        z = {k: cell() for k in DEV.ROLES}; z['FULL'] = cell(r=0.0001, price=3, carry=1, fee=0.5, unknown=0.1)
        d = DEV.decompose_seed(z, np.ones(12, bool))['terms']['FULL']
        np.testing.assert_allclose(d['car_NAV_bps'], np.full((32, 2), 12.0))
        np.testing.assert_allclose(d['g_minus_price_net_NAV_bps'], d['g_NAV_bps'] - d['pnl_NAV_bps'] + d['car_NAV_bps'] + d['cst_NAV_bps'] + d['unk_NAV_bps'])
        np.testing.assert_allclose(d['compounding_minus_g_bps'], d['dbar_compounded_bps'] - d['g_NAV_bps'])

    def test_only_full_days_with_same_indices(self):
        m = np.ones(12, bool); m[0] = False
        z = {k: cell() for k in DEV.ROLES}; z['FULL'] = cell(r=0.001)
        d = DEV.decompose_seed(z, m)
        np.testing.assert_array_equal(d['days'], [W0 + 86400])
        self.assertEqual(d['terms']['FULL']['dbar_compounded_bps'].shape, (32, 1))
        with self.assertRaisesRegex(DEV.Unavailable, 'full UTC'):
            DEV.decompose_seed(z, np.arange(12) < 5)

    def test_wrong_axis_missing_path_and_nonfinite_refused(self):
        for problem in ('axis', 'paths', 'nan', 'duplicate'):
            z = {k: cell() for k in DEV.ROLES}
            if problem == 'axis': z['COMP']['anchors'] += 14400
            if problem == 'paths': z['FULL']['r_per_path'] = np.zeros((31, 12))
            if problem == 'nan': z['SEAT']['r_per_path'][0, 0] = np.nan
            if problem == 'duplicate': z['BASE']['anchors'][1] = z['BASE']['anchors'][0]
            with self.subTest(problem=problem), self.assertRaises(DEV.Unavailable):
                DEV.decompose_seed(z, np.ones(12, bool))

    def test_unrequested_member_cannot_enter_decomposition(self):
        z = {k: cell() for k in DEV.ROLES}; z['FULL_m1'] = cell(r=0.5)
        with self.assertRaisesRegex(DEV.Unavailable, 'exactly'):
            DEV.decompose_seed(z, np.ones(12, bool))

    def test_exact_first_difference_not_later_and_hyb_not_visited(self):
        a = W0 + np.arange(-2, 4, dtype=np.int64) * 14400
        x = np.zeros((len(a), 3)); y = x.copy(); y[2:, 0] = 0.001
        r = DEV.check_s1_lr(a, a.copy(), x, y)
        self.assertEqual(r['king_first_differing_anchor'], W0)
        self.assertEqual(r['LR_first_differing_anchor'], W0)
        for problem in ('late', 'early', 'equal', 'other_leg_only', 'missing_anchor', 'wrong_axis', 'nan', 'empty', 'no_history'):
            aa = a.copy(); bb = a.copy(); xx = x.copy(); yy = y.copy()
            if problem == 'late': yy[2, 0] = 0
            if problem == 'early': yy[1, 0] = 1
            if problem == 'equal': yy[:] = 0
            if problem == 'other_leg_only': yy[:] = 0; yy[2:, 1] = 1
            if problem == 'missing_anchor': aa += 1; bb += 1
            if problem == 'wrong_axis': bb += 14400
            if problem == 'nan': yy[-1, 0] = np.nan
            if problem == 'empty': aa=aa[:0]; bb=bb[:0]; xx=xx[:0]; yy=yy[:0]
            if problem == 'no_history': aa=aa[2:]; bb=bb[2:]; xx=xx[2:]; yy=yy[2:]
            with self.subTest(problem=problem), self.assertRaises(DEV.Unavailable):
                DEV.check_s1_lr(aa, bb, xx, yy)

    def test_pre2026_names_have_distinct_frozen_start(self):
        a = np.arange(DEV.ts(2022, 6, 30), DEV.ts(2026, 1, 2), 14400, dtype=np.int64)
        seg = DEV.segment_masks(a)
        self.assertEqual(a[seg['PRE2026_ALL_AVAILABLE']][0], DEV.ts(2022, 6, 30))
        self.assertEqual(a[seg['PRE2026_G4_COMMON']][0], DEV.ts(2023, 6, 30) + 14400)
        self.assertEqual(a[seg['PRE2026_G4_COMMON']][-1], DEV.ts(2026, 1, 1) - 14400)

    def test_source_declared_lr_warmup_and_unclosed_tail(self):
        # nc_legs leaves LR before first ready and the final, unclosed row as NaN.
        # A blanket isfinite gate rejects a valid source object; ignoring arbitrary
        # NaNs would instead admit a missing observation inside the used history.
        a = W0 + np.arange(-3, 4, dtype=np.int64) * 14400
        ready = np.array([False, False, True, True, True, True, True])
        base = np.zeros((7, 3)); base[:2] = np.nan; base[-1] = np.nan
        changed = base.copy(); changed[3:-1, 0] = 1
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); (root/'gate4').mkdir(); (root/'legs').mkdir()
            old = root/'legs/KSR_S0_m0.npz'; new = root/'legs/KSR_S1_m0.npz'
            gate = root/'gate4/KSR_S1_m0.json'
            def run(x, y, r0, r1):
                np.savez(old, E_ts=a, LR=x, ready=r0)
                np.savez(new, E_ts=a, LR=y, ready=r1)
                rec = dict(PASS=True, self_sha256=DEV.GATE4_SHA, mode='legs', first_window_anchor=W0,
                           S0_legs=str(old), S0_legs_sha256=DEV.sha(old), spliced_legs=str(new), spliced_legs_sha256=DEV.sha(new),
                           arrays={'LR': dict(axis0_is_anchor=True, pre_window_bitwise_equal=True,
                                              first_differing_anchor=W0, n_anchors_differing=3)})
                gate.write_text(json.dumps(rec))
                result, _ = DEV.check_gate4_and_axes({'gate4': str(root/'gate4')}, {'S1': {'m0': 'KSR_S1_m0'}},
                                                    {str(gate): DEV.sha(gate)}, [], [])
                return result['S1_first_difference']['m0']
            ok = run(base, changed, ready, ready)
            self.assertEqual(ok['king_first_differing_anchor'], W0)
            self.assertEqual(ok['structural_missing']['prefix_rows'], 2)
            self.assertEqual(ok['structural_missing']['unclosed_tail_rows'], 1)
            for problem in ('interior_nan', 'prefix_inf', 'one_sided_missing', 'readiness_diff',
                            'readiness_hole', 'nonbool_ready', 'prefix_value', 'tail_value', 'no_finite_pre'):
                x=base.copy(); y=changed.copy(); r0=ready.copy(); r1=ready.copy()
                if problem == 'interior_nan': x[4]=np.nan; y[4]=np.nan
                if problem == 'prefix_inf': x[0]=np.inf; y[0]=np.inf
                if problem == 'one_sided_missing': y[1]=0
                if problem == 'readiness_diff': r1[1]=True
                if problem == 'readiness_hole': r0[4]=False; r1[4]=False
                if problem == 'nonbool_ready': r0=r0.astype(int); r1=r1.astype(int)
                if problem == 'prefix_value': x[0]=0; y[0]=0
                if problem == 'tail_value': x[-1]=0; y[-1]=0
                if problem == 'no_finite_pre': x[2]=np.nan; y[2]=np.nan; r0[2]=False; r1[2]=False
                with self.subTest(problem=problem), self.assertRaises(DEV.Unavailable):
                    run(x,y,r0,r1)

    def test_done_identity_required(self):
        good = dict(status='DONE', pgid=3505287, upstream_pgid=3479615,
                    upstream_start_ticks=508358906, waiter_sha256=DEV.WAITER_SHA,
                    config_sha256=DEV.CONFIG_SHA)
        DEV.validate_done_identity(good)
        for key in good:
            bad = dict(good); bad[key] = 'wrong'
            with self.subTest(key=key), self.assertRaises(DEV.Unavailable):
                DEV.validate_done_identity(bad)

    def test_no_done_never_opens_npz(self):
        with tempfile.TemporaryDirectory() as root, patch.object(DEV.np, 'load', side_effect=AssertionError('candidate opened')):
            with self.assertRaisesRegex(DEV.Unavailable, 'no DONE'):
                DEV.completion_inputs(root)

    def test_frozen_statistics_parity(self):
        research = FILE.parents[2]
        paths = {
            'news_stats': research / 'news_2026-09-23/devices/news_stats.py',
            'bt_tables': research / 'baseline_tables_2026-09-19/devices/bt_tables.py',
            'bt_driver_lib': research / 'baseline_tables_2026-09-19/devices/bt_driver_lib.py',
        }
        modules = {}
        for name, path in paths.items():
            spec = importlib.util.spec_from_file_location('control_' + name, path)
            module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module); modules[name] = module
        ns = modules['news_stats']; ns.BT = modules['bt_tables']; ns.DL = modules['bt_driver_lib']
        self.assertEqual(DEV.sha(paths['news_stats']), '7141ba42ab227b9f35b48acce62d5e2a2494f364fdf6a83189974cb2af67e03c')
        rng = np.random.default_rng(1937)
        z = {k: cell(r=rng.normal(0, 0.002, (32, 12))) for k in DEV.ROLES}
        mask = np.ones(12, bool); mask[0] = False
        result = DEV.decompose_seed(z, mask)
        for role in ('FULL', 'SEAT', 'COMP'):
            paths = lambda k: [{'A': AXIS, 'r': z[k]['r_per_path'][j]} for j in range(32)]
            _, expected = ns.dbar(paths(role), paths('BASE'), mask, result['days'])
            np.testing.assert_allclose(result['terms'][role]['dbar_compounded_bps'], expected * 1e4, atol=1e-11)

    def test_all_eight_actual_lr_checked_and_hyb_exempt(self):
        edges = [DEV.ts(y, m) for y, m in [(2023, 10), (2024, 1), (2024, 10), (2025, 1), (2025, 10), (2026, 1), (2026, 7)]]
        a = np.array([W0 - 14400] + edges, dtype=np.int64)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); (root/'gate4').mkdir(); (root/'legs').mkdir()
            pins = {}; cmap = {'S1': {}, 'HYB': {'SEAT_ONLY': 'not_a_real_file'}}
            for k in range(8):
                old, new, gate = root/'legs'/f'KSR_S0_m{k}.npz', root/'legs'/f'KSR_S1_m{k}.npz', root/'gate4'/f'KSR_S1_m{k}.json'
                base = np.zeros((len(a), 3)); candidate = base.copy(); candidate[1:, 0] = k + 1
                np.savez(old, E_ts=a, LR=base); np.savez(new, E_ts=a, LR=candidate)
                r = dict(PASS=True, self_sha256=DEV.GATE4_SHA, mode='legs', first_window_anchor=W0,
                         S0_legs=str(old), S0_legs_sha256=DEV.sha(old), spliced_legs=str(new), spliced_legs_sha256=DEV.sha(new),
                         arrays={'LR': dict(axis0_is_anchor=True, pre_window_bitwise_equal=True,
                                            first_differing_anchor=W0, n_anchors_differing=len(a)-1)})
                gate.write_text(json.dumps(r)); pins[str(gate)] = DEV.sha(gate); cmap['S1'][f'm{k}'] = f'KSR_S1_m{k}'
            series = root/'SER.npz'; target = root/'TARGET.npz'
            np.savez(series, anchors=a); np.savez(target, anchors=a, legs_E_ts=a)
            cfg = {'gate4': str(root/'gate4')}
            facts, got_axis = DEV.check_gate4_and_axes(cfg, cmap, pins, [str(series)], [str(target)])
            self.assertEqual(len(facts['S1_first_difference']), 8)
            self.assertEqual(facts['HYB_LR_contract'], 'NOT_APPLIED_BY_DESIGN')
            np.testing.assert_array_equal(got_axis, a)
            # Equal arrays from the wrong S0 member are still the wrong research object.
            r['S0_legs'] = str(root/'legs'/'KSR_S0_m0.npz'); gate.write_text(json.dumps(r)); pins[str(gate)] = DEV.sha(gate)
            with self.assertRaisesRegex(DEV.Unavailable, 'member paths'):
                DEV.check_gate4_and_axes(cfg, cmap, pins, [str(series)], [str(target)])
            r['S0_legs'] = str(old)
            # Corrupt only m7, preserving old PASS and exact-first-difference metadata.
            candidate[1, 0] = 0; np.savez(new, E_ts=a, LR=candidate)
            r['spliced_legs_sha256'] = DEV.sha(new); gate.write_text(json.dumps(r)); pins[str(gate)] = DEV.sha(gate)
            pins.pop(str(new))
            with self.assertRaisesRegex(DEV.Unavailable, 'first difference'):
                DEV.check_gate4_and_axes(cfg, cmap, pins, [str(series)], [str(target)])

    def test_synthetic_output_preserves_two_seeds_and_pre_window_days(self):
        research = FILE.parents[2]
        modules = {}
        for name, directory in [('news_stats', 'news_2026-09-23'), ('bt_tables', 'baseline_tables_2026-09-19')]:
            path = research / directory / 'devices' / (name + '.py')
            spec = importlib.util.spec_from_file_location('e2e_' + name, path)
            module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module); modules[name] = module
        ns = modules['news_stats']; ns.BT = modules['bt_tables']
        starts = [DEV.ts(2022, 6, 30), DEV.ts(2023, 6, 30), DEV.ts(2023, 7), DEV.ts(2023, 10),
                  DEV.ts(2024, 10), DEV.ts(2025, 10), DEV.ts(2026, 1), DEV.ts(2026, 7)]
        a = np.concatenate([d + np.arange(6) * 14400 for d in starts])
        cmap = {'S0': {'m0': 'BASE'}, 'S1': {'m0': 'FULL'}, 'HYB': {'SEAT_ONLY': 'SEAT', 'COMP_ONLY': 'COMP'}}
        with tempfile.TemporaryDirectory() as directory, patch.object(DEV, 'import_frozen_stats', return_value=ns):
            root = Path(directory)
            for seed, multiplier in [('42', 1), ('2027', 2)]:
                for role, level in [('BASE', 10), ('FULL', 17), ('SEAT', 12), ('COMP', 13)]:
                    r = np.zeros((32, len(a))); r[:, ::6] = level * multiplier * 1e-4
                    z = {'anchors': a, 'r_per_path': r, 'g_per_path': r * 1e4 / 2}
                    z.update({c + '_per_path': np.zeros_like(r) for c in ('pnl', 'car', 'cst', 'unk')})
                    np.savez(root / f'SER_{role}_s{seed}.npz', **z)
            book = root/'book.json'; book.write_text(json.dumps({'self_sha256': DEV.READER_SHA, 'status': 'BOOK_HALF_OF_THE_VERDICT', 'GM': 2}))
            out = DEV.build_description({'series': str(root)}, cmap, book, a)
            segment = out['segments']['H1_merged']
            self.assertEqual(segment['n_full_UTC_days'], 3)
            for seed, multiplier in [('42', 1), ('2027', 2)]:
                self.assertAlmostEqual(segment['by_seed'][seed]['FULL']['dbar_compounded_bps']['mean_bps_per_day'], 7 * multiplier)
                self.assertAlmostEqual(segment['by_seed'][seed]['INTERACTION']['dbar_compounded_bps']['mean_bps_per_day'], 2 * multiplier)
            self.assertAlmostEqual(segment['mean_of_two_seeds_same_path']['INTERACTION']['dbar_compounded_bps']['mean_bps_per_day'], 3)
            self.assertEqual(out['segments']['PRE2026_ALL_AVAILABLE']['n_full_UTC_days'], 6)
            self.assertEqual(out['segments']['PRE2026_G4_COMMON']['n_full_UTC_days'], 4)
            DEV.write_json(root/'result.json', out)
            self.assertEqual(json.loads((root/'result.json').read_text()), out)


if __name__ == '__main__':
    unittest.main(verbosity=2)
