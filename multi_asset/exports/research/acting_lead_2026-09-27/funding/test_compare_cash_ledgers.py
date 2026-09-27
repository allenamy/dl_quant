import unittest
from compare_cash_ledgers import classify, groups, compare


class Controls(unittest.TestCase):
    def test_ms_not_collapsed(self):
        got = groups([1000, 1001, 1999, 2000], [1., 2., 3., 4.], 1000, 1999)
        self.assertEqual(got, {1: [(1000, 1.), (1001, 2.), (1999, 3.)]})
        self.assertEqual(classify([(1000, 1.)], got[1]), 'multiple_events_same_second')

    def test_nontrivial_classes(self):
        cases = [( [(1000, .01)], [(1000, .01)], 'one_to_one_exact'),
                 ( [(1000, .01)], [(1001, .01)], 'one_to_one_subsecond_time_changed'),
                 ( [(1000, .01)], [(1001, -.01)], 'one_to_one_rate_changed'),
                 ( [], [(1000, .01)], 'new_only_second'),
                 ( [(1000, .01)], [], 'old_only_second')]
        for old, new, want in cases:
            with self.subTest(want): self.assertEqual(classify(old, new), want)

    def test_duplicate_not_silently_sum(self):
        self.assertEqual(classify([(1000, 3.)], [(1000, 1.), (1000, 2.)]),
                         'multiple_events_same_second')

    def test_common_coverage_and_symbol_identity(self):
        old = {'symbols': ['A'], 'offsets': [0, 2], 'times': [1000, 2000],
               'rates': [.1, .2], 'min_ms': 1000, 'max_ms': 2000}
        new = {'symbols': ['B', 'A'], 'offsets': [0, 1, 4],
               'times': [2000, 1000, 2000, 3000], 'rates': [.2, .1, .2, .3],
               'min_ms': 1000, 'max_ms': 3000}
        r = compare(old, new)
        self.assertEqual(r['counts_second_buckets'], {'one_to_one_exact': 2, 'new_only_second': 1})
        self.assertEqual(r['event_counts'], {'old_events_in_common_coverage': 2,
                                           'new_events_in_common_coverage': 3})


if __name__ == '__main__': unittest.main()
