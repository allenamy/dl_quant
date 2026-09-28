import unittest
import numpy as np
from recent_cash_resume import semantic_prefix

class Gate(unittest.TestCase):
    def fixture(self):
        a={'A':np.array([0,14400]),'nav5_t0':np.array(0),
           'nav5_sim':np.ones(97)*100.,'nav5_main':np.ones(97)*100.,
           'nav1':np.array([100.,100.]),'navm1':np.array([100.,100.])}
        b={k:v.copy() for k,v in a.items()}
        b['A']=np.array([0,14400,28800]);return a,b
    def test_positive(self):
        a,b=self.fixture();self.assertEqual(semantic_prefix(a,b)['endpoint_samples_changed'],[])
    def test_one_ulp_terminal(self):
        a,b=self.fixture();b['nav5_sim'][-1]=np.nextafter(100.,np.inf)
        self.assertEqual(len(semantic_prefix(a,b)['endpoint_samples_changed']),1)
    def test_interior_one_ulp_refused(self):
        a,b=self.fixture();b['nav5_sim'][2]=np.nextafter(100.,np.inf)
        with self.assertRaises(ValueError):semantic_prefix(a,b)
    def test_economic_field_one_ulp_refused(self):
        a,b=self.fixture();b['nav1'][-1]=np.nextafter(100.,np.inf)
        with self.assertRaises(ValueError):semantic_prefix(a,b)
    def test_two_ulp_refused(self):
        a,b=self.fixture();b['nav5_sim'][-1]=np.nextafter(np.nextafter(100.,np.inf),np.inf)
        with self.assertRaises(ValueError):semantic_prefix(a,b)
    def test_axis_boundary_refused(self):
        a,b=self.fixture();b['A'][2]+=14400;b['nav5_sim'][-1]=np.nextafter(100.,np.inf)
        with self.assertRaises(ValueError):semantic_prefix(a,b)
    def test_nonfinite_refused(self):
        a,b=self.fixture();b['nav5_sim'][-1]=np.nan
        with self.assertRaises(ValueError):semantic_prefix(a,b)

if __name__=='__main__':unittest.main()
