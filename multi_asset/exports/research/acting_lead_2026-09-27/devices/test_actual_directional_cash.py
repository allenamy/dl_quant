import unittest
import actual_directional_cash as D


def trade(ts, qty, price=10):
    return dict(ts=ts, qty=qty, quote=qty*price, fee=.01, asset='USDT')


class Direction(unittest.TestCase):
    def test_long(self):
        self.assertEqual(D.classify(2, [trade(1,-1)], 10), 'LONG_ONLY')
    def test_short(self):
        self.assertEqual(D.classify(-2, [trade(1,1)], 10), 'SHORT_ONLY')
    def test_flip(self):
        self.assertEqual(D.classify(2, [trade(1,-3)], 10), 'CONFIRMED_FLIP')
    def test_flat(self):
        self.assertEqual(D.classify(0, [], 0), 'FLAT')
    def test_close_is_not_flip(self):
        self.assertEqual(D.classify(-.3, [trade(1,.1), trade(2,.2)], 10), 'SHORT_ONLY')
    def test_same_time_ambiguity(self):
        x=[trade(1,2),trade(1,-2)]
        self.assertEqual(D.classify(1,x,10),'INTRATIMESTAMP_AMBIGUOUS')
        self.assertEqual(D.classify(1,x[::-1],10),'INTRATIMESTAMP_AMBIGUOUS')
    def test_same_time_nonambiguous(self):
        self.assertEqual(D.classify(3,[trade(1,-1),trade(1,2)],10),'LONG_ONLY')
    def test_different_time_confirms(self):
        self.assertEqual(D.classify(1,[trade(1,-2),trade(2,2)],10),'CONFIRMED_FLIP')
    def test_zero_start_ambiguous(self):
        self.assertEqual(D.classify(0,[trade(1,-1),trade(1,1)],10),'INTRATIMESTAMP_AMBIGUOUS')
    def test_nonfinite_refused(self):
        for bad in (float('nan'),float('inf'),True):
            with self.assertRaises(ValueError): D.classify(bad,[],10)
    def test_cash_closed_roundtrip(self):
        a={'qty':0,'notional':0}; b={'qty':0,'notional':0}
        r=D.component('X',a,b,[trade(1,2,10),trade(2,-2,12)],[])
        self.assertEqual(r['price_trade_cash_usdt'],4)
        self.assertEqual(r['category'],'LONG_ONLY')
    def test_quantity_missing_refused(self):
        with self.assertRaises(ValueError):
            D.component('X',{'qty':1,'notional':10},{'qty':2,'notional':20},[],[])
    def test_income_only_unknown_position(self):
        z={'qty':0,'notional':0}
        r=D.component('X',z,z,[],[dict(asset='BNB',income=-.02)])
        self.assertEqual(r['category'],'NO_OBSERVED_POSITION')
        self.assertEqual(r['recorded_funding_native'],{'BNB':-.02})
    def test_short_cash_sign(self):
        r=D.component('X',{'qty':-2,'notional':-20},{'qty':-2,'notional':-24},[],[])
        self.assertEqual(r['price_trade_cash_usdt'],-4)
        self.assertEqual(r['category'],'SHORT_ONLY')


if __name__=='__main__': unittest.main()
