import unittest
import numpy as np
from recent_cash_inputs import extend_log_prices, append_funding, concat_combo

class Controls(unittest.TestCase):
    def test_price_returns_not_level_jump(self):
        p,u,s=extend_log_prices(np.array([3.,4.]),np.array([[100.,200.],[110.,190.]]))
        np.testing.assert_allclose(p[0]-[3,4],np.log([1.1,.95]));self.assertFalse(u.any())
    def test_gap_unknown_and_resume_price(self):
        p,u,s=extend_log_prices(np.array([3.]),np.array([[100.],[np.nan],[121.]]))
        self.assertTrue(u[0,0]);self.assertEqual(p[0,0],3.);self.assertAlmostEqual(p[1,0]-3.,np.log(1.21))
    def test_never_seed_from_future(self):
        with self.assertRaisesRegex(ValueError,'boundary'):extend_log_prices(np.array([3.]),np.array([[np.nan],[121.]]))
    def test_all_missing_remains_unknown(self):
        p,u,s=extend_log_prices(np.array([3.]),np.array([[np.nan],[np.nan]]));self.assertTrue(u.all());self.assertEqual(p[0,0],3.)
    def test_zero_and_inf_refused(self):
        for x in (0.,-1.,np.inf):
            with self.assertRaises(ValueError):extend_log_prices(np.array([3.]),np.array([[100.],[x]]))
    def test_funding_prefix_and_boundary_once(self):
        t,r,c=append_funding(np.array([10,20]),np.array([.1,.2]),[(20,.2),(30,.3)],20,30)
        self.assertEqual(t.tolist(),[10,20,30]);self.assertEqual(r.tolist(),[.1,.2,.3]);self.assertEqual(c['shared'],1)
    def test_funding_conflict(self):
        with self.assertRaisesRegex(ValueError,'conflict'):append_funding(np.array([20]),np.array([.2]),[(20,.3)],20,30)
    def test_funding_new_old_event_refused(self):
        with self.assertRaisesRegex(ValueError,'historical'):append_funding(np.array([20]),np.array([.2]),[(10,.1)],20,30)
    def test_funding_duplicate_refused(self):
        with self.assertRaisesRegex(ValueError,'duplicate'):append_funding(np.array([20]),np.array([.2]),[(30,.1),(30,.1)],20,30)
    def test_funding_future_not_used(self):
        t,r,c=append_funding(np.array([20]),np.array([.2]),[(30,.3),(40,.4)],20,30);self.assertEqual(t.tolist(),[20,30])
    def test_combo_gap_rejected(self):
        x={'symbols':np.array(['A']),'E_ts':np.array([0]),'weights':np.array([[1.]])}
        y={'symbols':np.array(['A']),'E_ts':np.array([28800]),'weights':np.array([[2.]])}
        with self.assertRaises(ValueError):concat_combo(x,y,28800)
    def test_combo_prefix_and_last_unpriced(self):
        x={'symbols':np.array(['A']),'E_ts':np.array([0]),'weights':np.array([[1.]])}
        y={'symbols':np.array(['A']),'E_ts':np.array([14400,28800]),'weights':np.array([[2.],[3.]])}
        z=concat_combo(x,y,28800);self.assertEqual(z['weights'].tolist(),[[1.],[2.]])

if __name__=='__main__':unittest.main()
