import unittest
import numpy as np
from stage import price_contributions, joint_measurable, verify_combo, period_readout
from selection import selection_steps


class Controls(unittest.TestCase):
    def test_unknown_held_outside_members_is_not_zero(self):
        w=np.array([[[.5,0,.5]]]); y=np.array([[.02,.01,np.nan]])
        self.assertFalse(joint_measurable([w], y)[0])

    def test_zero_exposure_unknown_allowed(self):
        w=np.array([[[.5,-.5,0]]]); y=np.array([[.02,.01,np.nan]])
        self.assertTrue(joint_measurable([w], y)[0])
        np.testing.assert_allclose(price_contributions(w,y)[0],[[50.]])

    def test_population_union_all_stages_and_arms(self):
        y=np.array([[.02,np.nan]])
        a=np.array([[[1.,0.]],[[0.,1.]]]); b=np.array([[[1.,0.]],[[1.,0.]]])
        self.assertFalse(joint_measurable([a,b],y)[0])

    def test_nonfinite_weights_rejected(self):
        with self.assertRaises(ValueError):joint_measurable([np.array([[[np.nan]]])],np.ones((1,1)))

    def test_cash_unknown_kept_nan(self):
        natural,unit,g=price_contributions(np.array([[[1.,1.]]]),np.array([[.02,np.nan]]))
        self.assertTrue(np.isnan(natural[0,0]));self.assertTrue(np.isnan(unit[0,0]))

    def test_gross_normalization(self):
        n,u,g=price_contributions(np.array([[[.25,-.25]]]),np.array([[.02,.01]]))
        np.testing.assert_allclose(n,[[25.]]);np.testing.assert_allclose(u,[[50.]])

    def test_combo_drift_refused(self):
        k=np.array([[.5,-.5]]);f=np.array([[.2,-.2]]);r=.55*k+.45*f
        verify_combo(k,f,r);r[0,0]+=.00001
        with self.assertRaises(ValueError):verify_combo(k,f,r)

    def test_hold_not_cash(self):
        r=period_readout(np.array([True,True]),np.array([True,False]),np.array([True,True]),
                         np.array([[1.,999.]]),np.array([[2.,999.]]))
        self.assertEqual(r['measured_published'],1);self.assertEqual(r['mean_delta'],[1.])

    def test_same_population_for_every_stage(self):
        r=period_readout(np.ones(2,bool),np.ones(2,bool),np.array([True,False]),
                        np.array([[1.,10.],[2.,100.]]),np.array([[2.,20.],[4.,200.]]))
        self.assertEqual(r['mean_delta'],[1.,2.]);self.assertEqual(r['unmeasured_published'],1)

    def test_combo_uses_pre_serialization_leg(self):
        k=np.array([[.5,-.5]]);f=np.array([[1e-10,-.2]]);r=.55*k+.45*f
        verify_combo(k,f,r)
        with self.assertRaises(ValueError):verify_combo(k,np.where(abs(f)>1e-9,f,0),r)

    def test_selection_not_recenter_confused(self):
        w=np.array([.5,-.3,-.2]);sel=np.array([True,True,False]);s=selection_steps(w,sel)
        np.testing.assert_allclose(s[1],[.5,-.3,0]);np.testing.assert_allclose(s[2],[.4,-.4,0])
        np.testing.assert_allclose(s[3],[.5,-.5,0]);self.assertAlmostEqual(sum(np.diff(s@np.array([.01,.02,.1]))),float((s[-1]-s[0])@np.array([.01,.02,.1])))

    def test_selection_nonfinite_refused(self):
        with self.assertRaises(ValueError):selection_steps(np.array([np.nan,1]),np.ones(2,bool))


if __name__=='__main__':unittest.main()
