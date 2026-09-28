import unittest
from funding_continuation import ordered_events

class ContinuationTests(unittest.TestCase):
    def test_exact_boundary_excluded(self):
        self.assertEqual(ordered_events([(100,.1),(200,.2),(300,.3)],100,200),[(200,.2)])
    def test_future_invariance(self):
        self.assertEqual(ordered_events([(200,.2),(300,.3)],100,200),ordered_events([(200,.2),(300,999.)],100,200))
    def test_duplicate_rejected(self):
        with self.assertRaises(ValueError):ordered_events([(200,.1),(200,.1)],100,300)
    def test_order_rejected(self):
        with self.assertRaises(ValueError):ordered_events([(300,.1),(200,.1)],100,300)
