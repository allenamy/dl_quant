import unittest
import numpy as np
from probe import checked_fetch,run_screen

class Controls(unittest.TestCase):
    def setUp(self):
        self.ts=np.arange(2018)*300;self.cd=np.ones((2018,2,7),np.float16);self.rr=np.ones((2018,2),np.float32)
    def fn(self,st,a,p,cd):return (st.cts.copy(),st.cd.copy(),cd.copy(),np.where(st.fetch_mask)[0])
    def screen(self,a=2015*300,fetch=None):
        return run_screen(self.ts,self.cd,self.rr,np.ones(2,bool),np.ones(2,bool) if fetch is None else fetch,a,{},self.fn)
    def test_future_rows_excluded(self):
        before=self.screen();self.cd[2016:]=100;self.rr[2016:]=-100;after=self.screen()
        for a,b in zip(before,after):np.testing.assert_array_equal(a,b)
    def test_fetch_exclusion(self):self.assertEqual(self.screen(fetch=np.array([False,True]))[-1].tolist(),[1])
    def test_unknown_fetch_refused(self):
        with self.assertRaises(ValueError):checked_fetch(['C'],['A','B'])
    def test_duplicate_refused(self):
        with self.assertRaises(ValueError):checked_fetch(['A','A'],['A','B'])
    def test_missing_anchor_refused(self):
        with self.assertRaises(ValueError):self.screen(2015*300+1)
    def test_nongrid_refused(self):
        self.ts[0]+=1
        with self.assertRaises(ValueError):self.screen()
    def test_shape_refused(self):
        with self.assertRaises(ValueError):self.screen(fetch=np.ones(3,bool))
    def test_prehistory_refused(self):
        with self.assertRaises(ValueError):self.screen(0)

if __name__=='__main__':unittest.main()
