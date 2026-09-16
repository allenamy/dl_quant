"""Bounded new-clock/source-interface controls; do not repeat money-core tests."""
import copy,unittest
import numpy as np
import current_dispatch as d

class DispatchTests(unittest.TestCase):
    def setUp(self):
        self.t=np.array([1735689600,1735704000],dtype=np.int64)
        self.sy=np.array(['A','B','C','D'])
        self.a={'anchor_ts':self.t,'symbols':self.sy}
        for off in (3300,3600):
            self.a['observation_ts_'+str(off)]=self.t+off
            self.a['price_'+str(off)]=np.ones((2,4),dtype=np.float64)
            self.a['quote_volume_'+str(off)]=np.ones((2,4),dtype=np.float64)
            self.a['trade_count_'+str(off)]=np.ones((2,4),dtype=np.float64)
        self.cal={'symbols':{}}

    def test_two_modes_exact_clock_and_population(self):
        anchors=np.arange(self.t[0],self.t[0]+7*14400,14400,dtype=np.int64)
        halt=d.expected_clocks(anchors,np.array([],dtype=np.int64),[],'ECONOMIC_HALT')
        no=d.expected_clocks(anchors,np.array([],dtype=np.int64),[],'NO_ECONOMIC_HALT')
        self.assertEqual([x for x in halt if x[0]!='RISK_ATTEMPT'],no)
        self.assertEqual(sum(x[0]=='RISK_ATTEMPT' for x in halt),6)
        self.assertEqual([x[1] for x in no if x[0]=='READBACK'],((anchors[:-1]+3300)*1000).tolist())
        old=[(k,t-1800000 if k=='READBACK' else t,i) for k,t,i in no]
        self.assertNotEqual(old,no)

    def test_original_status_and_announced_permission(self):
        self.a['quote_volume_3600'][0,1]=0
        self.a['price_3600'][0,2]=np.nan
        t=int(self.t[0]+3600)*1000
        self.cal['symbols']['D']={'new_order_restrictions':[{'announced_at_ms':t,'effective_ms':t,'end_ms':t+1}]}
        ob=d.OriginalRiskFacts(self.a,self.t,self.sy,self.cal).observations(t)
        self.assertEqual([ob[s]['status'] for s in self.sy],['ACTIVE','ZERO_ACTIVITY','MISSING','ACTIVE'])
        self.assertFalse(ob['D']['submission_allowed'])
        self.cal['symbols']['D']['new_order_restrictions'][0]['announced_at_ms']=t+1
        self.assertTrue(d.OriginalRiskFacts(self.a,self.t,self.sy,self.cal).observations(t)['D']['submission_allowed'])

    def test_exact_clock_refuses_bool_shift_and_nearest(self):
        f=d.OriginalRiskFacts(self.a,self.t,self.sy,self.cal);t=int(self.t[0]+3600)*1000
        for bad in (True,t+1,t+300000,t+28800000):
            with self.assertRaises(ValueError): f.observations(bad)
        a=copy.deepcopy(self.a);a['observation_ts_3300'][0]+=300
        with self.assertRaises(ValueError):d.OriginalRiskFacts(a,self.t,self.sy,self.cal)

    def test_axis_and_market_views(self):
        a=copy.deepcopy(self.a);a['price_3600']=a['price_3600'].astype(np.float32)
        with self.assertRaises(ValueError):d.OriginalRiskFacts(a,self.t,self.sy,self.cal)
        with self.assertRaises(ValueError):d.OriginalRiskFacts(self.a,self.t,self.sy[::-1],self.cal)

    def test_current_only_role_identity(self):
        self.assertEqual(d.scenario_identity('halt_current_main'),('current_main__main','ECONOMIC_HALT'))
        for bad in ('scenario_002','halt_f10_s2027','nohalt_current_main__main'):
            with self.assertRaises(ValueError):d.scenario_identity(bad)

    def test_real_market_clock_slice(self):
        p=d.HERE.parent/'current_economic_risk_20260915/market_actual1/risk_observations.npz'
        with np.load(p,allow_pickle=False) as z:
            a={k:z[k] if k=='symbols' else z[k][:2] for k in z.files}
        f=d.OriginalRiskFacts(a,a['anchor_ts'],a['symbols'],{'symbols':{}})
        for off in (3300,3600):
            self.assertEqual(f.index(int(a['observation_ts_'+str(off)][1])*1000,off),1)

if __name__=='__main__':unittest.main()
