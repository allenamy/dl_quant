import unittest,numpy as np
from continuous import run_arm
from substitute import exact_control
class ContinuousTests(unittest.TestCase):
    def step(self,**kw):
        return dict(accepted=True,kc=kw['kc_prev']*.5+kw['seats'][0],fc=kw['fc_prev']*.5,raw=kw['kc_prev']*.5+kw['seats'][0])
    def test_no_hidden_reanchoring(self):
        r=run_arm(self.step,np.array([1,2,3]),0,{'kc':np.array([8.]),'fc':np.array([0.])},lambda i:{'seats':np.array([0.])},set(),None)
        self.assertEqual([float(x['kc'][0]) for x in r],[4.,2.,1.])
    def test_hold_does_not_zero_or_update(self):
        r=run_arm(self.step,np.array([1,2,3]),0,{'kc':np.array([8.]),'fc':np.array([0.])},lambda i:{'seats':np.array([0.])},{2},None)
        self.assertEqual([float(x['kc'][0]) for x in r],[4.,4.,2.])
    def test_missing_seat_refuses(self):
        with self.assertRaises(ValueError):run_arm(self.step,np.array([1]),0,{'kc':np.array([8.]),'fc':np.array([0.])},lambda i:{},set(),{})
    def test_control_cannot_ignore_raw(self):
        with self.assertRaises(ValueError):exact_control({'accepted':True,'kc':np.zeros(1),'fc':np.zeros(1),'raw':np.ones(1)},dict(kc=np.zeros((1,1)),fc=np.zeros((1,1)),raw=np.zeros((1,1))),0)
if __name__=='__main__':unittest.main()
