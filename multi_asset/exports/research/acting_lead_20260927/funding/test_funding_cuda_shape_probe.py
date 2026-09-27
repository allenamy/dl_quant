"""Resource-controller tests only. Never imports Torch or launches a worker."""
import ast
import importlib.util
import pathlib
import unittest
from unittest import mock

P=pathlib.Path(__file__).with_name('funding_cuda_shape_probe.py')
spec=importlib.util.spec_from_file_location('shape_probe',P)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class GuardTests(unittest.TestCase):
    def base(self):
        return {'free_bytes':11*m.G,'uid_rss_bytes':27*m.G,'gpu_used_mib':2,'gpu_util':0,'compute_pids':[]}
    def test_exact_gate(self):self.assertEqual(m.gate_reasons(self.base()),[])
    def test_headroom_one_byte_short(self):
        s=self.base();s['free_bytes']-=1;self.assertIn('HEADROOM',m.gate_reasons(s))
    def test_uid_one_byte_over(self):
        s=self.base();s['uid_rss_bytes']+=1;self.assertIn('UID_RSS',m.gate_reasons(s))
    def test_gpu_process_even_if_small(self):
        s=self.base();s['compute_pids']=[321];self.assertIn('GPU_OCCUPIED',m.gate_reasons(s))
    def test_worker_soft_stop(self):
        self.assertEqual(m.stop_reason(m.SOFT_STOP+1,0,0,9*m.G),'SOFT_RSS_STOP')
    def test_gpu_wall_and_shared_pressure(self):
        self.assertEqual(m.stop_reason(0,m.GPU_BUDGET+1,0,9*m.G),'GPU_STOP')
        self.assertEqual(m.stop_reason(0,0,60,9*m.G),'WALL_STOP')
        self.assertEqual(m.stop_reason(0,0,0,8*m.G-1),'PUBLIC_HEADROOM_STOP')
    def test_only_owned_compute_pid(self):
        self.assertEqual(m.owned_gpu_bytes('12, 100\n13, 200\n',12),100*2**20)
    def test_bad_nvidia_output_fails(self):
        with self.assertRaises(ValueError):m.owned_gpu_bytes('12, [N/A]',12)
    def test_termination_is_only_private_child_group(self):
        child=mock.Mock(pid=123);child.poll.return_value=None
        with mock.patch.object(m.os,'getpgid',return_value=123), mock.patch.object(m.os,'killpg') as kill:
            m.terminate_owned(child)
            kill.assert_called_once_with(123,m.signal.SIGTERM)
    def test_changed_group_refuses_kill(self):
        child=mock.Mock(pid=123);child.poll.return_value=None
        with mock.patch.object(m.os,'getpgid',return_value=999), mock.patch.object(m.os,'killpg') as kill:
            with self.assertRaises(RuntimeError):m.terminate_owned(child)
            kill.assert_not_called()
    def test_shape_bytes(self):
        self.assertEqual(m.SHAPE,(120,829,171))
        self.assertEqual(m.input_bytes(),68044320)
        self.assertEqual(m.DECLARED_RSS,3*m.G)
        self.assertEqual(m.SOFT_STOP,5*m.G//2)
    def test_no_optimizer_no_old_entry_and_fixed_worker_inputs(self):
        tree=ast.parse(P.read_text());worker=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='worker')
        src=ast.get_source_segment(P.read_text(),worker)
        self.assertNotIn('optim.',src);self.assertNotIn('.step(',src);self.assertNotIn('torch.load',src)
        self.assertNotIn('np.load',src);self.assertNotIn('network_fixture',P.read_text())
        self.assertNotIn('exec(',src)

if __name__=='__main__':unittest.main()
