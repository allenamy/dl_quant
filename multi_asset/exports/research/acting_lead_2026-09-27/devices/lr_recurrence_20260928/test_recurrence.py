"""Pure recurrence controls; never imports a producer entrypoint or calls an API."""
import copy, importlib.util, os, unittest
from pathlib import Path
from types import SimpleNamespace
import numpy as np

P=Path(__file__).with_name('recurrence.py')
spec=importlib.util.spec_from_file_location('recurrence',P) if P.exists() else None
M=importlib.util.module_from_spec(spec) if spec else None
if spec: spec.loader.exec_module(M)
SOURCE=Path(os.environ.get('LR_SOURCE','/dev/shm/lr_recurrence_20260928_inputs/shadow_loop_v3.py'))

class Controls(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(M,'independent recurrence implementation missing')
        self.advance,self.seats=M.production_blocks(SOURCE)
        self.st=SimpleNamespace(last_anchor=0,prev_rec={'anchor_ts':0,'members':[0,1],
          'legz':{k:[-.5,.5] for k in M.LEGS}},LR={k:[0.,1.] for k in M.LEGS})
        self.x=np.zeros((49,2,1),np.float32);self.x[1:,1,0]=1/48
    def go(self,x=None,a=14400):
        self.advance(self.st,a,self.x if x is None else x,{0:0,a:48},48)
    def test_one_return_not_compound(self):
        self.go();self.assertAlmostEqual(self.st.LR['king'][-1],5000.,places=2)
        self.assertEqual(len(self.st.LR['king']),3)
    def test_gap_does_not_append(self):
        self.go(a=28800);self.assertEqual(self.st.LR['king'],[0.,1.])
    def test_prev_identity_mismatch(self):
        self.st.prev_rec['anchor_ts']=-14400;self.go();self.assertEqual(len(self.st.LR['fund']),2)
    def test_missing_46_threshold(self):
        self.x[1:4,1,0]=np.nan;self.go();self.assertEqual(self.st.LR['king'][-1],0.)
    def test_all_missing_not_false_return(self):
        self.x[1:]=np.nan;self.go();self.assertEqual(self.st.LR['fund'][-1],0.)
    def test_seats_nonpositive_uniform(self):
        self.st.LR={k:[-1.,-2.,-3.] for k in M.LEGS}
        np.testing.assert_array_equal(self.seats(self.st,{'msharpe_look':3}),[1/3]*3)
    def test_seats_only_positive(self):
        self.st.LR={'king':[1.,2.,3.],'rev24':[-1.,-2.,-3.],'fund':[-2.,-3.,-4.]}
        np.testing.assert_array_equal(self.seats(self.st,{'msharpe_look':3}),[1.,0.,0.])
    def test_event_not_early_or_twice(self):
        lr={k:[8.,9.] for k in M.LEGS}
        self.assertFalse(M.reseed(self.st,False,149,150,lr));self.assertEqual(self.st.LR['king'],[0.,1.])
        self.assertTrue(M.reseed(self.st,False,150,150,lr));self.st.LR['king'].append(10.)
        self.assertTrue(M.reseed(self.st,True,151,150,lr));self.assertEqual(self.st.LR['king'],[8.,9.,10.])
        self.assertEqual(lr['king'],[8.,9.])
    def test_future_rows_excluded_and_fetch_mask(self):
        ts=np.arange(0,15001,300);r=np.ones((len(ts),2),np.float32)
        x=M.segment(ts,r,[0,1],14400,2,[True,False]);r[-1]=999
        y=M.segment(ts,r,[0,1],14400,2,[True,False])
        np.testing.assert_array_equal(x,y);self.assertTrue(np.isnan(x[:,1]).all())
        self.assertEqual(x.shape,(49,2,1));self.assertEqual(float(x[1:,0].sum()),48.)
    def test_missing_bar_refused(self):
        ts=np.delete(np.arange(0,14701,300),10)
        with self.assertRaisesRegex(ValueError,'bar_axis'):M.segment(ts,np.ones((len(ts),2)),[0,1],14400,2,[True,True])
    def test_invalid_seed_refused(self):
        for bad in ({}, {'king':[1.], 'rev24':[2.], 'fund':[np.inf]}):
            with self.assertRaises(ValueError):M.validate_lr(bad)
    def test_effectful_source_rejected(self):
        with self.assertRaisesRegex(ValueError,'source_identity'):M.production_blocks(SOURCE,expected_sha='0'*64)

if __name__=='__main__':unittest.main()
