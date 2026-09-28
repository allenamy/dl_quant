import unittest
import numpy as np
from trace_chain import compile_trace, price_metric

SOURCE = '''def chain(zc):
    w = np.where(sel, zc, 0.0)
    w = np.where(sel, w - (w[sel].mean() if sel.any() else 0), w)
    g = np.abs(w).sum()
    if g < 1e-9: return None
    w = w / g
    capw = P["cap_mult"] / max(int(sel.sum()), 1)
    w = np.clip(w, -capw, capw)
    g2 = np.abs(w).sum()
    if g2 > 1e-9: w = w / g2
    tgt = np.zeros(NW); tgt[pm] = w
    smv = H + P["alpha"] * (tgt - H)
    trade = smv - H
    smv = np.where(np.abs(trade) < P["band"], H, smv)
    _keep_liq = np.zeros(NW, bool); _keep_liq[pm[sel]] = True
    keep = (LIVE_MASK.copy() if LIVE_MASK is not None else np.ones(NW, bool))
    if LIVE_MASK is not None:
        _mm = np.zeros(NW, bool); _mm[pm] = True
        keep &= _mm
    keep &= _keep_liq
    leave = (~keep) & (np.abs(smv) > 1e-12)
    smv = np.where(leave, 0.0, smv)
    return smv
'''

class TraceTest(unittest.TestCase):
    def test_observers_preserve_original_output_and_states(self):
        ns, traces = compile_trace(SOURCE)
        plain = {'np':np}; exec(SOURCE,plain)
        kwargs=dict(P={'cap_mult':1.2,'alpha':.1,'band':.002},NW=5,pm=np.array([0,1,3]),sel=np.array([True,True,False]),LIVE_MASK=np.array([True,True,True,True,False]),H=np.array([.01,-.02,.004,0,.003]))
        ns.update(kwargs);plain.update(kwargs)
        z=np.array([.4,-.2,.1]); result=ns['chain'](z)
        np.testing.assert_array_equal(result,plain['chain'](z))
        self.assertEqual([x[0] for x in traces],['demean','normalize','cap_normalize','ema','band','eligible'])
        self.assertFalse(np.shares_memory(traces[-1][1],result))
        old=result.copy(); traces[-1][1][0]=999
        np.testing.assert_array_equal(result,old)
    def test_structure_drift_refused(self):
        with self.assertRaises(ValueError): compile_trace(SOURCE.replace('w = w / g','w = w / (g + 1)',1))
    def test_nonzero_unknown_never_zero(self):
        self.assertIsNone(price_metric(np.array([.5,-.5]),np.array([.01,np.nan])))
        self.assertAlmostEqual(price_metric(np.array([1.,0.]),np.array([.01,np.nan])),100.)
    def test_zero_portfolio_unmeasurable(self):
        self.assertIsNone(price_metric(np.zeros(2),np.array([.01,.02])))

if __name__=='__main__':unittest.main()
