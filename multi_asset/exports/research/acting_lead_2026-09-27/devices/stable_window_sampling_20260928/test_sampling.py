"""Behavioral controls for future experiments; no training or market outcomes."""
import bisect
import collections
import random
import unittest

try:
    from sampling import sample_ids
    IMPLEMENTED = True
except ImportError:
    IMPLEMENTED = False
    # The frozen recipe's inverse-CDF coupling is the real red control.
    def sample_ids(ids, weights, *, seed, stream, draw_ids):
        total = sum(weights)
        c = []
        for w in weights:
            c.append((c[-1] if c else 0) + w / total)
        c[-1] = 1.
        return tuple(ids[bisect.bisect_right(c, random.Random(f'{seed}:{stream}:{d}').random())]
                     for d in draw_ids)


class Sampling(unittest.TestCase):
    def call(self, ids, weights=None, draws=range(256), **kw):
        return sample_ids(ids, weights or [1.] * len(ids), seed=kw.get('seed', 42),
                          stream=kw.get('stream', 'F10/202609'), draw_ids=list(draws))

    def test_adding_window_never_switches_between_two_old_windows(self):
        # Inverse CDF reshuffles old windows when the population grows.
        old = self.call(['a', 'c', 'e', 'g'])
        new = self.call(['a', 'b', 'c', 'e', 'g'])
        unwanted = [(a, b) for a, b in zip(old, new) if b != 'b' and a != b]
        self.assertEqual(unwanted, [])

    @unittest.skipUnless(IMPLEMENTED, 'implementation not yet written')
    def test_reordering_is_exact(self):
        self.assertEqual(self.call(['a', 'b', 'c'], [1., 3., 6.]),
                         self.call(['c', 'a', 'b'], [6., 1., 3.]))

    @unittest.skipUnless(IMPLEMENTED, 'implementation not yet written')
    def test_resume_same_draw_id_is_exact(self):
        whole = self.call(['a', 'b', 'c'], draws=range(96))
        resumed = self.call(['a', 'b', 'c'], draws=range(31)) + self.call(['a', 'b', 'c'], draws=range(31, 96))
        self.assertEqual(whole, resumed)

    @unittest.skipUnless(IMPLEMENTED, 'implementation not yet written')
    def test_common_weight_ratios_preserve_coupling(self):
        old = self.call(['a', 'c', 'e'], [.1, .3, .6])
        new = self.call(['a', 'b', 'c', 'e'], [1., 2., 3., 6.])
        self.assertTrue(all(y == 'b' or x == y for x, y in zip(old, new)))

    @unittest.skipUnless(IMPLEMENTED, 'implementation not yet written')
    def test_removal_preserves_unaffected_draws(self):
        before = self.call(['a', 'b', 'c'], [1., 3., 6.])
        after = self.call(['a', 'c'], [1., 6.])
        self.assertTrue(all(x == 'b' or x == y for x, y in zip(before, after)))

    @unittest.skipUnless(IMPLEMENTED, 'implementation not yet written')
    def test_zero_weight_never_selected(self):
        got = self.call(['a', 'b', 'c'], [0., 1., 0.])
        self.assertEqual(set(got), {'b'})

    @unittest.skipUnless(IMPLEMENTED, 'implementation not yet written')
    def test_weighted_marginal_calibration(self):
        # Fails for uniform/always-first implementations; not an exact-sequence assertion.
        n = 12000
        got = collections.Counter(self.call(['a', 'b', 'c'], [1., 3., 6.], range(n)))
        for name, p in zip(['a', 'b', 'c'], [.1, .3, .6]):
            self.assertLess(abs(got[name] / n - p), .02)

    @unittest.skipUnless(IMPLEMENTED, 'implementation not yet written')
    def test_seed_and_fold_separate_streams(self):
        a = self.call(['a', 'b', 'c'])
        self.assertEqual(a, self.call(['a', 'b', 'c']))
        self.assertNotEqual(a, self.call(['a', 'b', 'c'], seed=2027))
        self.assertNotEqual(a, self.call(['a', 'b', 'c'], stream='F10/202608'))

    @unittest.skipUnless(IMPLEMENTED, 'implementation not yet written')
    def test_invalid_inputs_refused(self):
        cases = [([], []), (['a', 'a'], [1., 1.]), ([''], [1.]), ([None], [1.]),
                 (['a'], []), (['a'], [-1.]), (['a'], [float('nan')]),
                 (['a'], [float('inf')]), (['a'], [True]), (['a'], [0.])]
        for ids, weights in cases:
            with self.subTest(ids=ids, weights=weights), self.assertRaises(ValueError):
                sample_ids(ids, weights, seed=42, stream='fold', draw_ids=[0])
        for seed, stream, draws in [(True, 'fold', [0]), (-1, 'fold', [0]),
                                    (42, '', [0]), (42, 'fold', [0, 0]),
                                    (42, 'fold', [-1]), (42, 'fold', [True])]:
            with self.subTest(seed=seed, stream=stream, draws=draws), self.assertRaises(ValueError):
                sample_ids(['a'], [1.], seed=seed, stream=stream, draw_ids=draws)

    def test_implementation_present(self):
        self.assertTrue(IMPLEMENTED, 'stable window sampler is not implemented')


if __name__ == '__main__':
    unittest.main()
