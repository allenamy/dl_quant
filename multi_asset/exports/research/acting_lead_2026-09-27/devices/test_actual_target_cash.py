import unittest
import actual_target_cash as A

class Test(unittest.TestCase):
    def test_exact_target(self):
        r=A.decompose({'qty':2,'notional':20},{'qty':2,'notional':24},[],20,False)
        self.assertEqual((r['benchmark'],r['alignment'],r['trading']),(4,0,0))
    def test_under_target(self):
        r=A.decompose({'qty':1,'notional':10},{'qty':1,'notional':12},[],20,False)
        self.assertEqual((r['benchmark'],r['alignment'],r['trading']),(4,-2,0))
    def test_short(self):
        r=A.decompose({'qty':-2,'notional':-20},{'qty':-2,'notional':-24},[],-20,False)
        self.assertEqual(r['benchmark'],-4)
    def test_trade(self):
        r=A.decompose({'qty':1,'notional':10},{'qty':2,'notional':24},[{'qty':1,'quote':11}],10,False)
        self.assertEqual((r['actual'],r['benchmark'],r['alignment'],r['trading']),(3,2,0,1))
    def test_missing_end_price(self):
        r=A.decompose({'qty':1,'notional':10},{'qty':0,'notional':0},[{'qty':-1,'quote':-11}],10,False)
        self.assertEqual(r['verdict'],'UNPRICED')
        self.assertIsNone(r['benchmark'])
        self.assertEqual(r['actual'],1)
    def test_missing_start_price(self):
        r=A.decompose({'qty':0,'notional':0},{'qty':1,'notional':12},[{'qty':1,'quote':11}],10,False)
        self.assertEqual(r['verdict'],'UNPRICED')
    def test_halt_ignores_unsubmitted_target(self):
        r=A.decompose({'qty':0,'notional':0},{'qty':1,'notional':12},[{'qty':1,'quote':11}],10,True)
        self.assertEqual((r['benchmark'],r['alignment'],r['trading']),(0,0,1))
    def test_zero_position_zero_target(self):
        r=A.decompose({'qty':0,'notional':0},{'qty':0,'notional':0},[],0,False)
        self.assertEqual(r['benchmark'],0)
    def test_halt_holds_actual(self):
        r=A.decompose({'qty':1,'notional':10},{'qty':1,'notional':12},[],50,True)
        self.assertEqual((r['benchmark'],r['alignment']),(2,0))
    def test_conflicting_target(self):
        with self.assertRaises(ValueError):A.known_target([{'symbol':'X','target_w':.1},{'symbol':'X','target_w':.2}],100,10,20)
    def test_future_target(self):
        with self.assertRaises(ValueError):A.known_target([{'symbol':'X','target_w':.1}],100,21,20)
    def test_nonfinite_target(self):
        with self.assertRaises(ValueError):A.known_target([{'symbol':'X','target_w':float('nan')}],100,10,20)
    def test_plan_scale(self):
        self.assertEqual(A.known_target([{'symbol':'X','target_w':.1}],100,10,20),{'X':10})
    def test_quantity_mismatch(self):
        with self.assertRaises(ValueError):A.decompose({'qty':1,'notional':10},{'qty':2,'notional':24},[],10,False)

if __name__=='__main__':unittest.main()
