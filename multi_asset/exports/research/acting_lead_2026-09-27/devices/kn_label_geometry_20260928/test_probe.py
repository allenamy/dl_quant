import unittest
import numpy as np
from probe import measure, validate_members

class Controls(unittest.TestCase):
    def test_zero_and_common_fee_leave_rank(self):
        y=np.arange(100,dtype=float)
        for f in (np.zeros(100),np.ones(100)*.03):
            r,d=measure(y,y-f,f)
            self.assertAlmostEqual(r['spearman'],1)
            self.assertTrue(np.all(d==0))
            self.assertEqual(r['top_retention'],1)
            self.assertEqual(r['bottom_retention'],1)
    def test_fee_can_reverse_ranks(self):
        y=np.arange(100,dtype=float);f=2*y
        r,d=measure(y,y-f,f)
        self.assertAlmostEqual(r['spearman'],-1)
        self.assertEqual(r['top_retention'],0)
        self.assertGreater(np.mean(d),.5)
    def test_nonfinite_never_filled(self):
        for x in (float('nan'),float('inf')):
            y=np.arange(100,dtype=float);y[0]=x
            with self.assertRaises(ValueError):measure(y,y,np.zeros(100))
    def test_duplicate_members_refused(self):
        for a in ([0,0],[0,100],[-1,0]):
            with self.assertRaises(ValueError):validate_members(np.array(a),100)
    def test_ties_do_not_invent_extreme_order(self):
        y=np.zeros(100)
        r,d=measure(y,y,y)
        self.assertIsNone(r['spearman'])
        self.assertIsNone(r['top_retention'])
        self.assertTrue(np.all(d==0))

if __name__=='__main__':unittest.main()
