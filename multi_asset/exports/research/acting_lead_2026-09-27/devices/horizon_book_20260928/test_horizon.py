import unittest
import numpy as np
from horizon import targets, training_rows
from residual_model import fit_predict

class HorizonTests(unittest.TestCase):
    def test_path_compound_decay(self):
        y=np.zeros((15,2));y[:3,0]=[.1,-.1,.2]
        slow=targets(y)
        self.assertAlmostEqual(slow[0,0],(.1+.9*(-.11)+.81*.198)/sum(.9**np.arange(12)))
        self.assertEqual(slow[0,1],0.)
        self.assertTrue(np.isnan(slow[4]).all())

    def test_outside_window_does_not_change(self):
        y=np.full((40,3),.01);base=targets(y);y[12:]=-.5
        np.testing.assert_array_equal(base[0],targets(y)[0])

    def test_unknown_refused_not_zero(self):
        y=np.zeros((15,2));y[7,0]=np.nan
        self.assertTrue(np.isnan(targets(y)[0,0]));self.assertEqual(targets(y)[0,1],0.)
        y[7,0]=np.inf;self.assertTrue(np.isnan(targets(y)[0,0]))
        y[7,0]=-1;self.assertTrue(np.isnan(targets(y)[0,0]))

    def test_training_stride_and_label_endpoint(self):
        a=np.arange(120)*14400;pa=np.repeat(np.arange(120),3)
        rows=training_rows(a,pa,np.ones(len(pa),bool),a[100])
        anchors=np.unique(pa[rows]);np.testing.assert_array_equal(anchors,[0,12,24])
        self.assertTrue((np.diff(a[anchors])>=12*14400).all())
        self.assertLessEqual(a[anchors[-1]]+12*14400,a[100]-60*14400)

    def test_exact_axes_and_population(self):
        a=np.arange(100)*14400;pa=np.repeat(np.arange(100),2);valid=np.ones(200,bool);valid[24]=False
        r=training_rows(a,pa,valid,a[-1]);self.assertNotIn(24,r)
        with self.assertRaises(ValueError):training_rows(a+.5,pa,valid,a[-1])
        with self.assertRaises(ValueError):training_rows(a[::-1],pa,valid,a[-1])

    def test_test_labels_cannot_change_fit(self):
        a=np.arange(180)*14400;pa=np.repeat(np.arange(180),2)
        rng=np.random.default_rng(42);y=rng.normal(0,.01,(180,2));x=rng.normal(size=(360,6))
        z=targets(y).ravel();rows=training_rows(a,pa,np.isfinite(z),a[120]);test=np.flatnonzero(pa>=120)
        pred,model=fit_predict(x,z,rows,test)
        y[120:]=.9;z2=targets(y).ravel();r2=training_rows(a,pa,np.isfinite(z2),a[120]);p2,m2=fit_predict(x,z2,r2,test)
        np.testing.assert_array_equal(rows,r2);np.testing.assert_array_equal(pred,p2)
        for k in model:np.testing.assert_array_equal(model[k],m2[k])

if __name__=='__main__':unittest.main()
