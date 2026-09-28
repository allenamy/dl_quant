import unittest
import numpy as np
from residual_model import residual_targets, fit_predict, aligned_labels


class ResidualModelTest(unittest.TestCase):
    def setUp(self):
        r = np.random.default_rng(741)
        self.x = r.normal(size=(160, 7))
        self.y = self.x[:, 2] + r.normal(size=160)

    def test_projection_and_missing_fund_negative_control(self):
        k, f = self.x[:, 0], self.x[:, 1]
        y = self.y + 3*k + 4*f
        z, mask, coeff = residual_targets(y, k, f, minimum=50)
        self.assertTrue(mask.all())
        self.assertLess(abs(np.corrcoef(z,k)[0,1]), 1e-12)
        self.assertLess(abs(np.corrcoef(z,f)[0,1]), 1e-12)
        wrong = y - np.column_stack([np.ones(len(k)),k]) @ np.linalg.lstsq(np.column_stack([np.ones(len(k)),k]),y,rcond=None)[0]
        self.assertGreater(abs(np.corrcoef(wrong,f)[0,1]), .5)

    def test_unknown_not_zero(self):
        k, f = self.x[:,0].copy(), self.x[:,1].copy()
        k[3] = np.nan
        z, mask, _ = residual_targets(self.y,k,f,minimum=50)
        self.assertFalse(mask[3]); self.assertTrue(np.isnan(z[3]))

    def test_insufficient_population(self):
        with self.assertRaises(ValueError):
            residual_targets(self.y[:4],self.x[:4,0],self.x[:4,1],minimum=50)

    def test_test_labels_cannot_enter_fit(self):
        tr, te = np.arange(100), np.arange(100,160)
        p, _ = fit_predict(self.x,self.y,tr,te)
        y2=self.y.copy(); y2[te] = y2[te][::-1]*100
        p2, _ = fit_predict(self.x,y2,tr,te)
        self.assertTrue(np.array_equal(p,p2))

    def test_identical_label_control(self):
        tr,te=np.arange(100),np.arange(100,160)
        p,_=fit_predict(self.x,self.y,tr,te)
        q,_=fit_predict(self.x,self.y.copy(),tr,te)
        self.assertTrue(np.array_equal(p,q))

    def test_bad_fit_population(self):
        with self.assertRaises(ValueError): fit_predict(self.x,self.y,np.arange(100),np.arange(99,160))
        xx=self.x.copy();xx[20,2]=np.nan
        with self.assertRaises(ValueError): fit_predict(xx,self.y,np.arange(100),np.arange(100,160))

    def test_axis_and_symbol_identity(self):
        a=np.arange(5)*14400
        y=np.arange(10).reshape(5,2)
        self.assertTrue(np.array_equal(aligned_labels(a,['A','B'],a,['A','B'],y),y))
        with self.assertRaises(ValueError):aligned_labels(a,['A','B'],a,['B','A'],y)
        with self.assertRaises(ValueError):aligned_labels(a,['A','B'],a[::-1],['A','B'],y)
        with self.assertRaises(ValueError):aligned_labels(a+.5,['A','B'],a,['A','B'],y)

    def test_collinear_ridge_matches_closed_form_in_double_precision(self):
        v=np.linspace(-3,3,4000)
        x=np.repeat(v[:,None],64,axis=1);y=2*v+.01*np.sin(v)
        pred,m=fit_predict(x,y,np.arange(3000),np.arange(3000,4000))
        z=(v[:3000]-m['mu'][0])/m['sd'][0]
        expected=np.dot(z,y[:3000]-y[:3000].mean())/(1+64*np.dot(z,z))
        np.testing.assert_allclose(m['coef'],expected,rtol=1e-9,atol=1e-11)

    def test_missing_label_anchor_stays_unknown(self):
        a=np.arange(5)*14400;y=np.arange(8).reshape(4,2)
        out=aligned_labels(a,['A','B'],a[:4],['A','B'],y)
        self.assertTrue(np.isnan(out[-1]).all())


if __name__=='__main__':unittest.main()
