import unittest
import signal_trace_cash as C
class CashTrace(unittest.TestCase):
 def p(self,**kw):return dict(dict.fromkeys(C.KEYS,0.),**kw)
 def test_values(self):self.assertEqual(C.value(self.p(king=10,fund=-20),2,3)['fund'],-10)
 def test_net_zero_missing_is_unknown(self):self.assertIsNone(C.value(self.p(king=10,fund=-10),None,3))
 def test_allzero_no_mark(self):self.assertEqual(sum(C.value(self.p(),None,None).values()),0)
 def test_nonfinite_mark(self):self.assertIsNone(C.value(self.p(king=1),2,float('inf')))
 def test_nonfinite_part(self):
  with self.assertRaises(ValueError):C.value(self.p(f10=float('nan')),2,3)
 def test_missing_part(self):
  with self.assertRaises(ValueError):C.value({'king':1},2,3)
if __name__=='__main__':unittest.main()
