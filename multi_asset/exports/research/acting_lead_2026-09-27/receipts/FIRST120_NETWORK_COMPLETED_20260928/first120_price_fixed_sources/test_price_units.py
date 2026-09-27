import math
import unittest
import numpy as np
from price_units import decode_log_prices


class ReferencePanel:
    def __init__(self, lp, g0, syms, first, cref, ref):
        self.lp, self.g0, self.syms = lp, g0, list(syms)
        self.first, self.cref, self.ref = first, cref, ref

    def px(self, symbol, ts):
        j = self.syms.index(symbol)
        if self.first[j] < 0 or ts < self.first[j]:
            return None
        return float(self.ref[j] * math.exp(self.lp[(ts-self.g0)//300,j]-self.cref[j]))


class PriceUnitControls(unittest.TestCase):
    def fixture(self):
        raw = np.array([[-1., 0.], [-.9, .1], [-.8, .2]], dtype=np.float64)
        ts = np.array([600,900,1200], dtype=np.int64)
        syms = np.array(['BTCUSDT','NEWUSDT'])
        meta = {'grid':np.arange(300,1800,300), 'symbols':syms.copy(),
                'first_fin':np.array([300,900]), 'cref_raw':np.array([-1.,0.]),
                'ref_px':np.array([100.,2.]), 'unavail_grid_row':np.array([],dtype=int),
                'unavail_col':np.array([],dtype=int)}
        return raw,ts,syms,meta

    def call(self, data=None):
        return decode_log_prices(np, *(data or self.fixture()), ReferencePanel)

    def test_negative_log_is_not_negative_price(self):
        price, rec = self.call()
        self.assertEqual(price[0,0],100.)
        self.assertAlmostEqual(price[1,0],100.*math.exp(.1),delta=1e-12)
        self.assertEqual(rec['encoding'],'absolute_price_from_cumulative_log_v1')

    def test_before_listing_stays_unknown(self):
        price,_=self.call()
        self.assertTrue(np.isnan(price[0,1]))
        self.assertEqual(price[1,1],2.*math.exp(.1))

    def test_zero_log_uses_reference(self):
        d=self.fixture();d[3]['first_fin'][1]=300
        self.assertEqual(self.call(d)[0][0,1],2.)

    def test_symbol_permutation_refused(self):
        d=self.fixture();d[3]['symbols']=d[3]['symbols'][::-1]
        with self.assertRaisesRegex(ValueError,'symbol'):self.call(d)

    def test_fractional_clock_refused(self):
        d=list(self.fixture());d[1]=d[1].astype(float)+.5
        with self.assertRaisesRegex(ValueError,'integer'):self.call(d)

    def test_off_grid_refused(self):
        d=self.fixture();d[1][1]+=1
        with self.assertRaisesRegex(ValueError,'grid'):self.call(d)

    def test_invalid_reference_refused(self):
        for value in [0.,-1.,float('nan'),float('inf')]:
            d=self.fixture();d[3]['ref_px'][0]=value
            with self.assertRaisesRegex(ValueError,'reference'):self.call(d)

    def test_unavailable_bar_needs_explicit_policy(self):
        d=self.fixture();d[3]['unavail_grid_row']=np.array([1]);d[3]['unavail_col']=np.array([0])
        with self.assertRaisesRegex(ValueError,'unavailable'):self.call(d)

    def test_nonfinite_log_refused(self):
        d=self.fixture();d[0][0,0]=float('nan')
        with self.assertRaisesRegex(ValueError,'log'):self.call(d)

    def test_post_listing_unknown_refused(self):
        class BadPanel(ReferencePanel):
            def px(self,s,t):return None
        with self.assertRaisesRegex(ValueError,'unexpected unknown'):
            decode_log_prices(np,*self.fixture(),BadPanel)


if __name__=='__main__':unittest.main()
