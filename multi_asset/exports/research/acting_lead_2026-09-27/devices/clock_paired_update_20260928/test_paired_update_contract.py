import copy, unittest
from paired_update_contract import validate_results

def valid():
 a={'parameter_hash_before':'start','parameter_hash_after':'post','optimizer_updates':1,'loss_before_bits':'loss','gradient_sha256':'grad','optimizer_sha256':'opt','all_finite':True,'hard_max_error':0.0,'hard_masks_equal':True,'hard_reasons_equal':True}
 return {'updates':{k:dict(a) for k in ('A0','A1','F0_A0','F0_A1')},'optimizer_updates':4}
class Contracts(unittest.TestCase):
 def test_positive(self): self.assertEqual(validate_results(valid()),'IMPLEMENTATION_CONTROL_PASS')
 def test_f0_each_byte_field_rejects(self):
  for key in ('loss_before_bits','gradient_sha256','parameter_hash_after','optimizer_sha256'):
   d=valid();d['updates']['F0_A1'][key]='different'
   with self.assertRaisesRegex(ValueError,'F0'):validate_results(d)
 def test_missing_fields(self):
  for key in valid()['updates']['A0']:
   d=valid();del d['updates']['A0'][key]
   with self.assertRaises((ValueError,KeyError)):validate_results(d)
 def test_start_drift(self):
  d=valid();d['updates']['A1']['parameter_hash_before']='other'
  with self.assertRaisesRegex(ValueError,'initial'):validate_results(d)
 def test_no_extra_step(self):
  d=valid();d['updates']['A0']['optimizer_updates']=2
  with self.assertRaisesRegex(ValueError,'step'):validate_results(d)
 def test_nan_and_hard_mismatch(self):
  for key,value in [('hard_max_error',float('nan')),('hard_max_error',1e-8),('hard_masks_equal',False),('hard_reasons_equal',False),('all_finite',False)]:
   d=valid();d['updates']['A0'][key]=value
   with self.assertRaises(ValueError):validate_results(d)
 def test_extra_or_missing_arm(self):
  for key in ('A0','extra'):
   d=valid()
   if key=='A0':del d['updates'][key]
   else:d['updates'][key]=copy.deepcopy(d['updates']['A0'])
   with self.assertRaises(ValueError):validate_results(d)
if __name__=='__main__':unittest.main()
