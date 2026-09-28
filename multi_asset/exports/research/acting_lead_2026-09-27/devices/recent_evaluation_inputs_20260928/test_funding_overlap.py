import unittest
from funding_overlap import event_map,no_duplicates

class FundingInputTests(unittest.TestCase):
    def test_key_row_match(self):
        self.assertEqual(event_map({'BTCUSDT|100':[100,.01,1.]}),{('BTCUSDT',100):.01})
    def test_row_identity_refused(self):
        with self.assertRaises(ValueError):event_map({'BTCUSDT|100':[101,.01,1.]})
    def test_duplicate_refused(self):
        with self.assertRaises(ValueError):no_duplicates([('a',1),('a',1)])
    def test_unknown_rate_refused(self):
        for x in (None,True,float('nan'),float('inf')):
            with self.assertRaises(ValueError):event_map({'BTCUSDT|100':[100,x,1.]})
    def test_unknown_interval_preserved(self):
        self.assertEqual(event_map({'BTCUSDT|100':[100,.01,None]}),{('BTCUSDT',100):.01})
