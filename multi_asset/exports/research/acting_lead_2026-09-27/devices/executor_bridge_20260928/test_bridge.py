"""Pure research tests; never import an executor entrypoint or call a venue."""
import ast,hashlib,json,math,types,unittest
from pathlib import Path
import numpy as np
HERE=Path(__file__).parent
try:
 import executor_bridge as EB
except ModuleNotFoundError:
 EB=None

def lift(label,kind,env):
 p=HERE/f'{label}_{kind}.py.txt';s=p.read_text();a=ast.parse(s)
 assert all(isinstance(n,ast.FunctionDef) for n in a.body)
 ns=dict(env);exec(compile('from __future__ import annotations\n'+s,str(p),'exec'),ns);return types.SimpleNamespace(**ns)

def old_code():
 lg=lift('old','legs',{'np':np,'math':math});env={'LG':lg,'RESHAPE_REDEMEAN':True,'RESHAPE_RESCALE':True}
 return types.SimpleNamespace(AL=lift('old','anchor',env),EXT=lift('old','external',{}),LG=lg)

class BridgeTests(unittest.TestCase):
 def setUp(self):
  self.X=old_code()
  if EB is not None:EB.install_pure(self.X,HERE)
 def test_small_residual_no_longer_distorts_reshape(self):
  t={'A':-90.,'B':40.,'C':50.};h={'A':1.};original=h.copy()
  c,r=self.X.AL.apply_withhold_and_reshape(t,h,{'A'},180.,floors_usdt={'A':5.,'B':5.,'C':5.})
  self.assertAlmostEqual(sum(t.values()),0.);self.assertEqual(h,original)
  self.assertEqual(r['dust_popped_names'],['A']);self.assertEqual(t['A'],0.)
 def test_equal_floor_is_not_dust(self):
  t={'A':-90.,'B':40.,'C':50.};c,r=self.X.AL.apply_withhold_and_reshape(t,{'A':5.},{'A'},180.,floors_usdt={'A':5.})
  self.assertEqual(c['popped'],[]);self.assertAlmostEqual(sum(t.values()),90.)
 def test_missing_floor_does_not_pop_nonzero(self):
  t={'A':-1.};self.X.AL.withhold_pop(t,{'A':1.},{'A'});self.assertIn('A',t)
 def test_nonfinite_position_is_not_dust(self):
  for h in (float('nan'),float('inf'),float('-inf')):
   t={'A':-90.};self.X.AL.withhold_pop(t,{'A':h},{'A'});self.assertIn('A',t)
 def test_stopped_held_target_is_exactly_flat(self):
  t={'A':-90.,'B':40.,'C':50.};c,r=self.X.AL.apply_withhold_and_reshape(t,{'A':10.},{'A'},180.,floors_usdt={'A':5.},force_flat={'A'})
  self.assertEqual(t['A'],0.);self.assertIn('A',c['flatten_only']);self.assertAlmostEqual(sum(t.values()),0.)
 def test_ordinary_population_equal_old(self):
  old=old_code();a={'A':-90.,'B':40.,'C':50.};b=a.copy()
  old.AL.apply_withhold_and_reshape(a,{},set(),180.);self.X.AL.apply_withhold_and_reshape(b,{},set(),180.)
  self.assertEqual(a,b)
 def test_unknown_floor_not_reported_checked(self):
  r=self.X.EXT.below_min_notional({'A':7.},{},1.)
  self.assertEqual(r.get('unchecked_names'),['A'])
 @unittest.skipIf(EB is None,'bridge not yet implemented')
 def test_source_mutation_refused(self):
  import tempfile,shutil
  with tempfile.TemporaryDirectory() as d:
   for p in HERE.glob('*.py.txt'):shutil.copy(p,d)
   shutil.copy(HERE/'SOURCES.json',d);p=Path(d)/'current_anchor.py.txt';p.write_text(p.read_text()+'\n')
   with self.assertRaisesRegex(ValueError,'source identity'):EB.install_pure(old_code(),Path(d))

if __name__=='__main__':unittest.main()
