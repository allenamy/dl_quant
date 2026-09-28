import unittest
import numpy as np
from blend_support import amihud_at, ranked, blend, leg_return, support


class Contracts(unittest.TestCase):
    def test_future_and_boundary(self):
        r=np.full((400,12),.001);q=np.tile(np.arange(12)+1.,(400,1))
        a=amihud_at(r,q,300);r[301:]=99;q[301:]=25
        np.testing.assert_array_equal(a,amihud_at(r,q,300))
        q[300,0]=20
        self.assertNotEqual(a[0],amihud_at(r,q,300)[0])

    def test_left_open_and_coverage(self):
        r=np.ones((400,12));q=np.ones_like(r)
        a=amihud_at(r,q,300);r[12]=-99
        np.testing.assert_array_equal(a,amihud_at(r,q,300))
        r[13:28,0]=np.nan
        self.assertTrue(np.isnan(amihud_at(r,q,300)[0]))

    def test_volume_before_aggregation(self):
        r=np.ones((288,12))*.001;q=np.tile(np.r_[np.zeros(144),np.ones(144)*4][:,None],(1,12))
        x=amihud_at(r,q,287)
        np.testing.assert_allclose(x,.288/(144*np.expm1(4))*1e6)
        self.assertFalse(np.isclose(x[0],.288/(288*np.expm1(2))*1e6))

    def test_rank_population_and_unknown(self):
        x=np.arange(15,dtype=float);mask=np.arange(15)<10
        a=ranked(x,mask);self.assertTrue(np.isnan(a[10:]).all())
        x[10:]=-100
        np.testing.assert_array_equal(a,ranked(x,mask))
        mask[0]=False;self.assertTrue(np.isnan(ranked(x,mask)).all())
        self.assertTrue(np.isnan(blend(np.array([1.,2.]),np.array([np.nan,4.]))[0]))

    def test_leg_return_finite_population(self):
        self.assertEqual(leg_return(np.array([1.,-1.]),np.array([.01,-.01])),100.)
        self.assertEqual(leg_return(np.array([1.,-1.]),np.array([np.nan,np.nan])),0.)

    def test_support_keeps_missing_and_hold(self):
        t=np.array([[.5,-.5,0.],[0.,0.,1.]])
        g=np.array([[0,3,-1],[0,3,-1]])
        x=support(t,np.array([True,False]),g)
        self.assertEqual(x['published_anchors'],1)
        self.assertEqual(x['gross_sum_by_q1_q4_unknown'],[.5,0.,0.,.5,0.])
        y=support(t,np.ones(2,bool),g)
        self.assertEqual(y['gross_sum_by_q1_q4_unknown'][-1],1.)


if __name__=='__main__':unittest.main()
