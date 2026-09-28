"""A removed recorder must lose actual layer evidence, not merely a label."""
import hashlib, importlib.util, pathlib, sys, unittest
import torch as T
T.set_num_threads(1)
ROOT=pathlib.Path(__file__).resolve().parent
import funding_first120_clock_core as core
try:
    from trace_step import observed_step
except ModuleNotFoundError:
    # Red baseline is the real uninstrumented numerical implementation.
    def observed_step(fn, expected_sha, *args): return fn(*args), {}

def fixture(hard, scores=None):
    v=lambda x:T.tensor(x,dtype=T.float64)
    return (T,v([-.7,-.2,.3,.6]),v([-2.,0.,0.,2.] if scores is None else scores),
            v([-.5,.3,-.2,.4]),v([.8,0.,.2]),v([0.,-.002,0.,0.]),
            T.arange(4),v([100.,100.,100.,100.]),T.ones(4,dtype=T.bool),
            dict(qv4h_min=1.,cap_mult=2.,alpha=.1,band=.00025),v([0.,0.,0.,0.]),v([0.,0.,0.,0.]),'scaled_diagnostic',hard)

SHA=hashlib.sha256(pathlib.Path(core.__file__).read_bytes()).hexdigest()
class TraceTests(unittest.TestCase):
    def same(self,a,b):
        for x,y in zip(a,b):
            if isinstance(x,T.Tensor):self.assertTrue(T.equal(x,y))
            else:self.assertEqual(x,y)
    def test_real_layers_not_just_an_output_label(self):
        got,trace=observed_step(core.step,SHA,*fixture(True))
        self.assertIn('zf',trace)
        self.assertTrue(T.allclose(trace['zf'],T.tensor([-1/6,1/3,1/3,5/6],dtype=T.float64),rtol=0,atol=1e-15))
        self.assertEqual(len(trace['chains']),2)
        self.assertTrue(T.allclose(trace['chains'][0]['input_z'],T.tensor([-.66,-.10,.20,.56],dtype=T.float64),rtol=0,atol=1e-15))
        self.assertEqual(trace['chains'][0]['blocked'].tolist(),[False,True,False,False])
    def test_tracing_cannot_change_numeric_or_gate_outputs(self):
        for hard in (False,True):
            args=fixture(hard);self.same(observed_step(core.step,SHA,*args)[0],core.step(*args))
    def test_hard_positive_affine_invariance_and_average_ties(self):
        original=core.step(*fixture(True))
        for s in ([-.2,0.,0.,.2],[-20.,0.,0.,20.],[5.,7.,7.,9.]):self.same(original,core.step(*fixture(True,s)))
    def test_soft_scale_standardization_matches_training_contract(self):
        a=core.step(*fixture(False));b=core.step(*fixture(False,[-.2,0.,0.,.2]))
        self.assertLessEqual(float((a[1]-b[1]).abs().max()),1e-6)
    def test_soft_shift_invariance(self):
        self.same(core.step(*fixture(False)),core.step(*fixture(False,[5.,7.,7.,9.])))
    def test_source_drift_refuses_before_observation(self):
        with self.assertRaisesRegex(ValueError,'source drift'):observed_step(core.step,'0'*64,*fixture(True))

if __name__=='__main__':unittest.main()
