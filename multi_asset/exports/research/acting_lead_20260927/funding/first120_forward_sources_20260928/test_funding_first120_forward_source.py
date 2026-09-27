"""Only stdlib and pure scalar controls; no Torch/NumPy import or network call."""
import ast,pathlib,unittest
import funding_first120_forward_guard as guard
import funding_first120_clock_core as core
ROOT=pathlib.Path(__file__).parent
class SourceAndGateControls(unittest.TestCase):
    def test_no_optimizer_or_expired_entry(self):
        for n in ('funding_first120_forward.py','funding_first120_clock_core.py','funding_first120_forward_guard.py'):
            raw=(ROOT/n).read_text();tree=ast.parse(raw)
            for call in (x for x in ast.walk(tree) if isinstance(x,ast.Call)):
                name=ast.unparse(call.func)
                self.assertNotIn('optim.',name)
            for old in ('funding_network_fixture','funding_f0_byte_diagnostic','funding_cpu_parameter_controls','run_probe'):self.assertNotIn(old,raw)
    def test_budget_gates(self):
        good={'free_bytes':14*guard.G,'uid_rss_bytes':24*guard.G,'gpu_used_mib':0,'gpu_util':0,'compute_pids':[]}
        self.assertEqual(guard.gate_reasons(good),[])
        for k,v,why in [('free_bytes',14*guard.G-1,'HEADROOM'),('uid_rss_bytes',24*guard.G+1,'UID_RSS'),('compute_pids',[99],'GPU_OCCUPIED'),('gpu_util',1,'GPU_OCCUPIED')]:
            self.assertIn(why,guard.gate_reasons(dict(good,**{k:v})))
    def test_stops(self):
        self.assertIsNone(guard.stop_reason(0,0,0,8*guard.G))
        self.assertEqual(guard.stop_reason(guard.SOFT_STOP+1,0,0,8*guard.G),'SOFT_RSS_STOP')
        self.assertEqual(guard.stop_reason(0,guard.GPU_BUDGET+1,0,8*guard.G),'GPU_STOP')
        self.assertEqual(guard.stop_reason(0,0,300,8*guard.G),'WALL_STOP')
        self.assertEqual(guard.stop_reason(0,0,0,8*guard.G-1),'PUBLIC_HEADROOM_STOP')
    def test_declared_tensor_path(self):
        raw=(ROOT/'funding_first120_forward.py').read_text()
        for token in ('(17520,171)','positions_qty','producer_kc_fc','1672531200.','UNRESOLVED_PREVIOUS_ATTEMPT_NOT_RERUN','del objs,obj','(1e-3,1e-4)'):self.assertIn(token,raw)
        raw=(ROOT/'funding_first120_clock_core.py').read_text()
        cash=next(x for x in ast.parse(raw).body if isinstance(x,ast.FunctionDef) and x.name=='cash_path')
        # The only detach is zero initial quantity; no detach inside the recurrent loop.
        loops=[x for x in cash.body if isinstance(x,ast.For)]
        for loop in loops:self.assertNotIn('.detach(',ast.unparse(loop))
        self.assertIn("parts[k][24:]",raw)
    def test_atoms_shape_and_boundary(self):
        p={'first_leg':{'p_rej':.25,'p_full':.5,'p_part':.25,'fbar_part':.5},'completion':{'pi_fill':.5,'maker_share':.5},'fee_rate':{'USDT_era':{'maker':.0002,'taker':.0005}},'timing_offsets_after_decision_s':{'first_leg':[1,2,3,4,5],'later_leg':[6,7,8,9,10],'weights':[.2]*5},'slippage_vs_executor_mid':{'first_leg':-.0002,'later_leg':-.0001}}
        a=core.atoms_from_calibration({'params':p});self.assertEqual(len(a),10);self.assertTrue(all(x[0]>1440 and x[2]<0 for x in a));self.assertAlmostEqual(sum(x[1] for x in a),.734375)
        p['timing_offsets_after_decision_s']['later_leg'][-1]=14400
        with self.assertRaises(ValueError):core.atoms_from_calibration({'params':p})
if __name__=='__main__':unittest.main()
