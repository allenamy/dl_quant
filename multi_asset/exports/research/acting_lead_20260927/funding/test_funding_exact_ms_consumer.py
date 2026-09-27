"""Small fixed-inventory controls against the unchanged canonical cash method."""
import ast
import collections
import hashlib
import heapq
import importlib.util
import pathlib
import types
import unittest

HERE = pathlib.Path(__file__).resolve().parent
SOURCE = HERE.parents[1] / 'replay_exec_2026-09-19' / 'exec_sim.py'
CANONICAL_SHA = '29679672e68d4842a62616e40c5fc57143f724b9ebfa6bbde927670624247c24'
A = 1787702400


def canonical_base():
    src = SOURCE.read_bytes()
    assert hashlib.sha256(src).hexdigest() == CANONICAL_SHA
    tree = ast.parse(src)
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'Sim')
    ns = {'L': types.SimpleNamespace(floor_b=lambda t: int(t) // 300 * 300)}
    method = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == 'on_funding')
    exec(compile(ast.Module(body=[method], type_ignores=[]), str(SOURCE), 'exec'), ns)
    return type('CanonicalCashBase', (), {'on_funding': ns['on_funding']})


def load_device():
    p = HERE / 'funding_exact_ms_consumer.py'
    if not p.exists():
        raise AssertionError('Exact-ms consumer is not implemented')
    spec = importlib.util.spec_from_file_location('exact_ms_consumer', p)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Controls(unittest.TestCase):
    def setUp(self):
        self.device = load_device()
        self.Base = canonical_base()

    def run_path(self, events, fills=(), rate_sign=1, initial=10., wrong_order=False):
        cls = type('TestCanonicalCash', (self.device.ExactMsFundingMixin, self.Base), {})
        sim = cls()
        sim.F = self.device.ExactMsFunding(
            {'ft_ms': [t for t, s, r in events], 'symbol_index': [s for t, s, r in events],
             'rate': [r * rate_sign for t, s, r in events], 'symbols': ['S', 'T']},
            A * 1000, (A + 14400) * 1000)
        sim.q = {'S': initial, 'T': 3.}
        sim.K = 0.; sim.k = {}; sim.acc = collections.Counter(); sim.fund_log = []
        sim.px = lambda s, b: 20. if b >= A + 300 else 10.
        queue = [(t, 2, 'fund', None) for t in sim.F.times]
        queue.extend((t, 1 if wrong_order else 3, 'fill', dq) for t, dq in fills)
        queue.sort()
        for t, _, kind, dq in queue:
            if kind == 'fund': sim.on_funding(t)
            else: sim.q['S'] += dq
        return sim

    def test_single_subsecond_event_uses_post_fill_inventory(self):
        sim = self.run_path([(A*1000+900, 0, .001)], [(A+.1, 5.)])
        self.assertAlmostEqual(sim.K, -.15, places=13)
        self.assertNotAlmostEqual(sim.K, -.10, places=13)  # floor-second mutant

    def test_same_second_two_fees_do_not_last_write_or_coalesce_across_fill(self):
        sim = self.run_path([(A*1000+1, 0, .001), (A*1000+900, 0, .003)], [(A+.1, 5.)])
        self.assertEqual(len(sim.fund_log), 2)
        self.assertAlmostEqual(sim.K, -.55, places=13)
        self.assertNotAlmostEqual(sim.K, -.75, places=13)  # last-write twice

    def test_same_ms_multisymbol_and_same_time_funding_precedes_fill(self):
        ev = [(A*1000+100, 0, .001), (A*1000+100, 1, .002)]
        sim = self.run_path(ev, [(A+.1, 5.)])
        self.assertEqual(len(sim.F.times), 1)
        self.assertAlmostEqual(sim.K, -.16, places=13)
        wrong = self.run_path(ev, [(A+.1, 5.)], wrong_order=True)
        self.assertNotAlmostEqual(wrong.K, sim.K, places=13)

    def test_half_open_boundaries_and_price_bar(self):
        ev = [(A*1000, 0, 100.), (A*1000+1, 0, .001),
              ((A+14400)*1000, 0, .002), ((A+14400)*1000+1, 0, 100.)]
        sim = self.run_path(ev)
        self.assertEqual(len(sim.fund_log), 2)
        self.assertAlmostEqual(sim.K, -.5, places=13)

    def test_zero_fee_and_sign_flip(self):
        ev = [(A*1000+1, 0, .001), (A*1000+900, 0, -.002)]
        sim = self.run_path(ev, [(A+.1, 5.)])
        zero = self.run_path(ev, [(A+.1, 5.)], rate_sign=0)
        reverse = self.run_path(ev, [(A+.1, 5.)], rate_sign=-1)
        self.assertEqual(zero.K, 0.)
        self.assertEqual(zero.q, sim.q)
        self.assertEqual(reverse.K, -sim.K)

    def test_pre_fill_zero_gradient_and_reachable_cash_finite_difference(self):
        ev = [(A*1000+1, 0, .001), (A*1000+900, 0, .003)]
        eps = 1e-4
        plus = self.run_path(ev, [(A+.1, 5.+eps)])
        minus = self.run_path(ev, [(A+.1, 5.-eps)])
        self.assertEqual(plus.fund_log[0][-1], minus.fund_log[0][-1])
        fd = (plus.K-minus.K)/(2*eps)
        self.assertAlmostEqual(fd, -.03, places=10)
        self.assertNotAlmostEqual(fd, -.04, places=10)  # charge unreachable first fee

    def test_zero_baseline_inventory_still_has_reachable_derivative(self):
        ev = [(A*1000+900, 0, .003)]
        z = self.run_path(ev, initial=0)
        p = self.run_path(ev, [(A+.1, 1.)], initial=0)
        self.assertEqual(len(z.F.times), 1)
        self.assertAlmostEqual(p.K-z.K, -.03, places=13)

    def test_rate_view_fails_closed_when_inactive_or_wrong_second(self):
        sim = self.run_path([(A*1000+900, 0, .001)])
        with self.assertRaises(RuntimeError): sim.F.rate.get(('S', A))
        with sim.F.active_event(A+.9):
            with self.assertRaises(RuntimeError): sim.F.rate.get(('S', A+1))
        with self.assertRaises(ValueError):
            with sim.F.active_event(A+.8): pass

    def test_duplicate_exact_event_is_rejected(self):
        with self.assertRaises(ValueError):
            self.run_path([(A*1000+1, 0, .001), (A*1000+1, 0, .002)])


if __name__ == '__main__':
    unittest.main(verbosity=2)
