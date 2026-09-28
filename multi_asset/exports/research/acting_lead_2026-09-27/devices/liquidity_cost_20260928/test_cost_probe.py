import unittest
from cost_probe import finite, project, reference, measure, quartiles


class CostProbeTest(unittest.TestCase):
    def test_blind_projection(self):
        self.assertEqual(project({'symbol':'X','chase_arm':'A','requote_p':.2}, {'symbol'}), {'symbol':'X'})

    def test_nonfinite_unknown(self):
        self.assertIsNone(finite(float('nan')))
        self.assertIsNone(finite(float('inf')))
        self.assertIsNone(finite(None))
        self.assertIsNone(finite(True))

    def test_conflicting_reference(self):
        self.assertEqual(reference([{'mid_at_anchor':10}, {'mid_at_anchor':11}])[1], 'reference_conflict')
        self.assertEqual(reference([{'mid_at_anchor':10}, {'mid_at_anchor':10}]), (10.0, None))

    def test_missing_not_zero(self):
        self.assertEqual(reference([{'mid_at_anchor':None}])[1], 'reference_unknown')

    def test_cost_side(self):
        self.assertAlmostEqual(measure(101,100,'buy'),.01)
        self.assertAlmostEqual(measure(101,100,'sell'),-.01)
        with self.assertRaises(ValueError):measure(101,100,'unknown')

    def test_quartile_full_population_and_ties(self):
        self.assertEqual(quartiles([1,2,3,4,5,6,7,8]).tolist(), [0,0,1,1,2,2,3,3])
        self.assertEqual(quartiles([1,1,1,1]).tolist(), [2,2,2,2])

    def test_quartile_missing_refused(self):
        with self.assertRaises(ValueError):quartiles([1,float('nan')])


if __name__=='__main__':unittest.main()
