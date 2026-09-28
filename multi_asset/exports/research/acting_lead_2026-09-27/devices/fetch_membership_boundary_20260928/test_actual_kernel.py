import os,unittest
from pathlib import Path
import numpy as np
from probe import module,compile_block,run_screen

class RealKernelControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        p=Path(os.environ['PROBE_SOURCES'])
        cls.source=(p/'shadow_loop_v3.py').read_text()
        cls.nc=module(p/'nc_contract.py','test_nc');cls.tr=module(p/'tradability.py','test_tr')
    def setUp(self):
        self.ts=np.arange(2018)*300;self.cd=np.ones((2018,2,7),np.float16)
        self.cd[:,:,0]=np.where(np.arange(2018)[:,None]%2==0,.001,-.001);self.cd[:,0,3]=10;self.cd[:,1,3]=5
        self.rr=self.cd[:,:,0].astype(np.float32);self.params={'cov_min':.9,'vol_min':1e-5,'NTOP':1}
    def screen(self,fetch,source=None):
        fn=compile_block(source or self.source,self.nc,self.tr)
        return run_screen(self.ts,self.cd,self.rr,np.ones(2,bool),np.array(fetch,bool),2015*300,self.params,fn)
    def test_actual_gate_reranks(self):
        self.assertEqual(self.screen([True,True])['m'].tolist(),[0])
        self.assertEqual(self.screen([False,True])['m'].tolist(),[1])
    def test_removing_fetch_gate_detected(self):
        changed=self.source.replace('cand_now = legal_now & st.crypto & st.fetch_mask','cand_now = legal_now & st.crypto')
        self.assertNotEqual(changed,self.source)
        self.assertEqual(self.screen([False,True],changed)['m'].tolist(),[0])
        self.assertNotEqual(self.screen([False,True],changed)['m'].tolist(),self.screen([False,True])['m'].tolist())
    def test_future_poison_same_members_and_metrics(self):
        old=self.screen([True,True]);self.cd[2016:]=99;self.rr[2016:]=-99
        new=self.screen([True,True])
        for k in old:np.testing.assert_array_equal(old[k],new[k])
    def test_no_fetch_not_zero_fallback(self):self.assertEqual(self.screen([False,False])['m'].size,0)

if __name__=='__main__':unittest.main()
