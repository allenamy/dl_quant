import sys, unittest
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'linkage_20260928'))
from flow_ridge import fit_ridge, predict, month_masks
try:
    from tail_risk import tail_labels, fit_multi, probability_metrics
    IMPLEMENTED=True
except ImportError:
    IMPLEMENTED=False

class TailRisk(unittest.TestCase):
    def test_implementation_present(self):self.assertTrue(IMPLEMENTED,'tail-risk screen helpers absent')
    @unittest.skipUnless(IMPLEMENTED,'not implemented')
    def test_disjoint_five_percent_and_missing(self):
        y=np.r_[np.arange(100.),np.nan];p=tail_labels(y)
        self.assertEqual(p.shape,(101,2));np.testing.assert_equal(p[:100].sum(0),[5,5]);self.assertTrue(np.isnan(p[-1]).all());self.assertFalse((p.sum(1)>1).any())
        self.assertTrue((p[:5,1]==1).all());self.assertTrue((p[95:100,0]==1).all())
    @unittest.skipUnless(IMPLEMENTED,'not implemented')
    def test_ties_are_fixed_axis_and_inf_refused(self):
        p=tail_labels(np.zeros(100));self.assertTrue((p[:5,1]==1).all());self.assertTrue((p[-5:,0]==1).all())
        for y in (np.arange(49.),np.r_[np.arange(99.),np.inf]):
            with self.assertRaises(ValueError):tail_labels(y)
    @unittest.skipUnless(IMPLEMENTED,'not implemented')
    def test_multioutput_equal_two_scalar_ridges(self):
        r=np.random.default_rng(42);x=r.normal(size=(200,5));y=r.normal(size=(200,2));w=r.uniform(size=200);m=fit_multi(x,y,w)
        for j in range(2):np.testing.assert_allclose(predict(m,x)[:,j],predict(fit_ridge(x,y[:,j],w),x),atol=2e-13,rtol=0)
    @unittest.skipUnless(IMPLEMENTED,'not implemented')
    def test_future_mutation_does_not_change_training_fit(self):
        r=np.random.default_rng(42);at=np.arange(600)*14400;start=int(at[550]);tr,te=month_masks(at,start,start+30*86400);x=r.normal(size=(600,4));y=r.normal(size=(600,2));a=fit_multi(x[tr],y[tr],np.ones(tr.sum()));x[~tr]+=1000;y[~tr]-=1000;b=fit_multi(x[tr],y[tr],np.ones(tr.sum()))
        for k in a:np.testing.assert_array_equal(a[k],b[k])
    @unittest.skipUnless(IMPLEMENTED,'not implemented')
    def test_volatility_only_does_not_imply_tail_direction(self):
        y=tail_labels(np.arange(100.));p=np.zeros((100,2));p[:5]=[.8,.8];p[-5:]=[.8,.8];v=probability_metrics(p,y);self.assertEqual(v[4],.5)
    @unittest.skipUnless(IMPLEMENTED,'not implemented')
    def test_direction_sign_and_probabilities(self):
        y=tail_labels(np.arange(100.));v=probability_metrics(y,y);np.testing.assert_allclose(v,[0,0,1,1,1]);self.assertEqual(probability_metrics(y[:,::-1],y)[4],0)
    @unittest.skipUnless(IMPLEMENTED,'not implemented')
    def test_invalid_training_is_refused(self):
        x=np.ones((10,3));y=np.ones((10,2))
        for a,b,w in [(x,y[:-1],np.ones(10)),(x,y,np.zeros(10)),(x*np.nan,y,np.ones(10)),(x,y,np.ones(10)*-1)]:
            with self.assertRaises(ValueError):fit_multi(a,b,w)

if __name__=='__main__':unittest.main()
