import unittest
import numpy as np
from recent_windows import raw_return_channel, append_window

class RecentWindowsTests(unittest.TestCase):
    def test_nonboundary_remains_f16(self):
        t=np.array([300,600]);p=np.array([[100.],[100.012345]])
        d=np.full((2,1,7),np.nan,np.float16);d[1,0,0]=(p[1,0]/p[0,0]-1)
        r,bt,bc,br=raw_return_channel(t,p,d,np.ones((2,1),bool))
        self.assertEqual(r[1,0],np.float32(d[1,0,0]));self.assertEqual(len(bt),0)
    def test_bound_restores_raw(self):
        t=np.array([300,600]);p=np.array([[100.],[150.]])
        d=np.full((2,1,7),np.nan,np.float16);d[1,0,0]=.3
        r,bt,bc,br=raw_return_channel(t,p,d,np.ones((2,1),bool))
        self.assertEqual(r[1,0],.5);self.assertEqual(bt.tolist(),[600]);self.assertEqual(bc.tolist(),[0])
    def test_missing_previous_is_not_zero(self):
        t=np.array([300,600,900]);p=np.array([[100.],[np.nan],[150.]])
        d=np.full((3,1,7),np.nan,np.float16)
        r,*_=raw_return_channel(t,p,d,np.isfinite(p));self.assertTrue(np.isnan(r).all())
    def test_contradictory_observation_refuses(self):
        with self.assertRaises(ValueError):raw_return_channel(np.array([300,600]),np.array([[100.],[np.nan]]),np.full((2,1,7),np.nan,np.float16),np.ones((2,1),bool))
    def test_gap_refuses(self):
        with self.assertRaises(ValueError):raw_return_channel(np.array([300,900]),np.ones((2,1)),np.zeros((2,1,7),np.float16),np.ones((2,1),bool))
    def test_prefix_retained_and_future_excluded(self):
        t=np.array([300,600]);c=np.zeros((2,1,7),np.float16);r=np.zeros((2,1),np.float32)
        n=np.array([600,900,1200]);d=np.ones((3,1,7),np.float16);rr=np.ones((3,1),np.float32)
        tt,cc,rrr=append_window(t,c,r,n,d,rr,900)
        self.assertEqual(tt.tolist(),[300,600,900]);self.assertEqual(cc[:2].tobytes(),c.tobytes());self.assertEqual(rrr[:2].tobytes(),r.tobytes())
    def test_missing_seam_refuses(self):
        with self.assertRaises(ValueError):append_window(np.array([300,600]),np.zeros((2,1,7),np.float16),np.zeros((2,1),np.float32),np.array([1200]),np.zeros((1,1,7),np.float16),np.zeros((1,1),np.float32),1200)

if __name__=='__main__':unittest.main()
