import pathlib,hashlib,sys,unittest
import numpy as np
import torch
from liquid_utility import utility, mask_from_qv

class Controls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        p=pathlib.Path('/dev/shm/news2_2026-09-23/devices/news2_train_f10.py')
        if hashlib.sha256(p.read_bytes()).hexdigest()!='66bc7c3e69af7aab7062b562674fb3bbe272fd9a28fc3ea9639143f4549420db':raise ValueError('baseline source')
        sys.path.insert(0,str(p.parent));import news2_train_f10
        cls.old=staticmethod(news2_train_f10.utility)
    def data(self):
        torch.manual_seed(42);return torch.randn(19,dtype=torch.float64),torch.randn(19,dtype=torch.float64),torch.randn(19,dtype=torch.float64),torch.tensor([.3,.2,.5],dtype=torch.float64)
    def test_all_selected_is_exact_old_utility(self):
        for device in ('cpu','cuda') if torch.cuda.is_available() else ('cpu',):
            for hard in (False,True):
                args=tuple(v.to(device) for v in self.data());new=utility(*args,.3,torch.ones(19,dtype=torch.bool,device=device),19,hard)
                self.assertTrue(torch.equal(new,self.old(*args,.3,hard)))
    def test_all_selected_gradient_identical(self):
        args=list(self.data());args[0].requires_grad_();new=utility(*args,.3,torch.ones(19,dtype=torch.bool),19);(new*torch.arange(19)).sum().backward();g=args[0].grad.clone();args[0].grad.zero_();(self.old(*args,.3,False)*torch.arange(19)).sum().backward();self.assertTrue(torch.equal(g,args[0].grad))
    def test_unselected_zero_and_selected_neutral(self):
        args=self.data();m=torch.arange(19)<12;x=utility(*args,.3,m,12);self.assertTrue(torch.equal(x[~m],torch.zeros_like(x[~m])));self.assertLess(abs(float(x.sum())),1e-15)
    def test_mask_changes_actual_forward(self):
        args=self.data();m=torch.arange(19)<12;x=utility(*args,.3,m,12);self.assertFalse(torch.equal(x,self.old(*args,.3,False)))
    def test_current_mask_does_not_read_future(self):
        q=np.full((3,19),300000.);m=mask_from_qv(q[0]);q[1:]=0.;self.assertTrue(np.array_equal(mask_from_qv(q[0]),m))
    def test_boundary_and_unknown(self):
        np.testing.assert_array_equal(mask_from_qv(np.array([250000.,249999.,np.nan,1e6])),[True,False,False,True])
    def test_empty_unknown_refused(self):
        for q in (np.zeros(19),np.full(19,np.nan)):
            with self.assertRaises(ValueError):mask_from_qv(q)
    def test_axis_refused(self):
        with self.assertRaises(ValueError):mask_from_qv(np.ones((3,19)))

if __name__=='__main__':unittest.main()
