import copy,unittest
import funding_pack_acceptance as m
class TerminalControls(unittest.TestCase):
    def test_terminal_identity_reds(self):
        r={'status':'INPUT_PACK_ONLY_NO_FORWARD_NO_OPTIMIZER','source_sha256':m.WORKER,'cuda_initialized':False}
        t={'status':'COMPLETED','returncode':0,'guard_source_sha256':m.GUARD}
        c={'source_sha256':{'funding_first120_input_pack.py':m.WORKER,'funding_first120_input_pack_guard.py':m.GUARD}}
        self.assertTrue(m.terminal_gate(r,t,c))
        changes=[(0,'source_sha256','bad'),(0,'cuda_initialized',True),(1,'status','FAILED'),(1,'returncode',1),(1,'guard_source_sha256','bad'),(2,'source_sha256',{})]
        for i,k,v in changes:
            a=copy.deepcopy([r,t,c]);a[i][k]=v
            with self.subTest(field=k),self.assertRaises(ValueError):m.terminal_gate(*a)
if __name__=='__main__':unittest.main()
