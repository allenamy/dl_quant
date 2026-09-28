import unittest
import numpy as np
from peer_features import fit_graph, transform, NAMES

class Controls(unittest.TestCase):
    def data(self):
        rng=np.random.default_rng(7);t=np.arange(90)*14400;n=24
        market=rng.normal(0,.01,(90,1));groups=rng.normal(0,.01,(90,4))
        r=market+groups[:,np.arange(n)%4]+rng.normal(0,.002,(90,n));legal=np.ones(r.shape,bool)
        sy=np.array([f'S{i:02d}' for i in range(n)]);return t,r,legal,sy
    def fit(self,t,r,l,sy):return fit_graph(t,r,l,sy,60*14400,min_obs=20,k=5,min_peers=3,min_market=5)
    def vectors(self,n):
        rng=np.random.default_rng(3)
        return dict(r4=rng.normal(0,.01,n),r24=rng.normal(0,.03,n),flow_delta=rng.normal(0,.1,n),qv_anomaly=rng.normal(0,1,n),fund8=rng.normal(0,.001,n),ema8=rng.normal(0,.001,n),active=np.ones(n,bool))
    def test_future_poison_no_effect(self):
        t,r,l,sy=self.data();a=self.fit(t,r,l,sy);r[t>=a['graph_ts']]*=1000;l[t>=a['graph_ts']]=False;b=self.fit(t,r,l,sy)
        for key in ['beta','scale','peers','counts']:np.testing.assert_array_equal(a[key],b[key])
    def test_no_self_and_known_group(self):
        t,r,l,sy=self.data();g=self.fit(t,r,l,sy)
        self.assertTrue(all(i not in g['peers'][i] for i in range(len(sy))))
        self.assertGreater(np.mean([(g['peers'][i]%4==i%4).mean() for i in range(len(sy))]),.9)
    def test_permutation(self):
        t,r,l,sy=self.data();g=self.fit(t,r,l,sy);v=self.vectors(len(sy));a=transform(g,g['graph_ts'],**v)
        ix=np.random.default_rng(2).permutation(len(sy));h=self.fit(t,r[:,ix],l[:,ix],sy[ix]);b=transform(h,h['graph_ts'],**{k:x[ix] for k,x in v.items()})
        np.testing.assert_allclose(a['X'][ix],b['X'],atol=1e-12,rtol=1e-12,equal_nan=True)
    def test_current_peer_missing_is_unknown(self):
        t,r,l,sy=self.data();g=self.fit(t,r,l,sy);v=self.vectors(len(sy));v['active'][g['peers'][0]]=False
        z=transform(g,g['graph_ts'],**v);self.assertTrue(np.isnan(z['X'][0,:7]).all());self.assertEqual(z['peer_count'][0],0)
    def test_stale_day_refused(self):
        t,r,l,sy=self.data();g=self.fit(t,r,l,sy)
        with self.assertRaises(ValueError):transform(g,g['graph_ts']+86400,**self.vectors(len(sy)))
    def test_future_graph_refused(self):
        t,r,l,sy=self.data();g=self.fit(t,r,l,sy)
        with self.assertRaises(ValueError):transform(g,g['graph_ts']-14400,**self.vectors(len(sy)))
    def test_missing_history_not_zero(self):
        t,r,l,sy=self.data();r[:60,0]=np.nan;g=self.fit(t,r,l,sy);z=transform(g,g['graph_ts'],**self.vectors(len(sy)))
        self.assertFalse(g['eligible'][0]);self.assertTrue(np.isnan(z['X'][0]).all())
    def test_constant_history_no_peers(self):
        t,r,l,sy=self.data();g=self.fit(t,np.ones_like(r),l,sy);z=transform(g,g['graph_ts'],**self.vectors(len(sy)))
        self.assertTrue(np.isnan(z['X']).all())
    def test_gap_and_duplicate_refused(self):
        t,r,l,sy=self.data()
        for bad in [np.r_[t[:10],t[9],t[11:]],t.astype(float)+.5]:
            with self.assertRaises(ValueError):self.fit(bad,r,l,sy)
    def test_duplicate_names_refused(self):
        t,r,l,sy=self.data();sy[1]=sy[0]
        with self.assertRaises(ValueError):self.fit(t,r,l,sy)
    def test_infinite_refused(self):
        t,r,l,sy=self.data();r[1,0]=np.inf
        with self.assertRaises(ValueError):self.fit(t,r,l,sy)
    def test_feature_units_and_count(self):
        t,r,l,sy=self.data();g=self.fit(t,r,l,sy);v=self.vectors(len(sy));z=transform(g,g['graph_ts'],**v)
        self.assertEqual(z['X'].shape,(len(sy),8));self.assertEqual(len(NAMES),8)
        np.testing.assert_allclose(z['X'][:,7],v['fund8']-v['ema8'])
        np.testing.assert_allclose(z['X'][:,6],np.maximum(-v['fund8'],0)*z['X'][:,0])

if __name__=='__main__':unittest.main()
