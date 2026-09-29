"""Behavioral controls: replacing exact selection by nearest or flatten-on-HOLD fails."""
import unittest
import numpy as np
from state_handoff import select_seed, evolve

class SeedTests(unittest.TestCase):
 def setUp(self):
  self.x={'E_ts':np.array([0,14400,28800]),'symbols':np.array(['A','B']),
          'kc':np.array([[.1,-.1],[.2,-.2],[.3,-.3]]),'fc':np.array([[.11,-.11],[.21,-.21],[.31,-.31]])}
 def test_exact_prior(self):
  z=select_seed(self.x,['A','B'],14400)
  self.assertIsInstance(z,dict)
  np.testing.assert_array_equal(z['kc'],[.2,-.2])
 def test_no_nearest(self):
  with self.assertRaises(ValueError):select_seed(self.x,['A','B'],14401)
 def test_order_is_identity(self):
  with self.assertRaises(ValueError):select_seed(self.x,['B','A'],14400)
 def test_nonfinite_seed(self):
  self.x['kc'][1,0]=np.nan
  with self.assertRaises(ValueError):select_seed(self.x,['A','B'],14400)
 def test_duplicate_time(self):
  self.x['E_ts'][2]=14400
  with self.assertRaises(ValueError):select_seed(self.x,['A','B'],14400)
 def test_future_values_do_not_enter(self):
  a=select_seed(self.x,['A','B'],14400);self.x['kc'][2]=999;self.x['fc'][2]=-999
  b=select_seed(self.x,['A','B'],14400)
  self.assertIsInstance(a,dict)
  np.testing.assert_array_equal(a['kc'],b['kc']);np.testing.assert_array_equal(a['fc'],b['fc'])

# Deterministic stand-in tests wrapper persistence, never a production-kernel claim.
def controlled_step(*,kc_prev,fc_prev,fail=False,**kw):
 kc=kc_prev+np.array([.1,-.1]);fc=fc_prev+np.array([.2,-.2]);raw=.55*kc+.45*fc
 return dict(kc=kc,fc=fc,raw=raw,accepted=not fail,reason='gross' if fail else 'publish',executor_reshaped=raw)

class PathTests(unittest.TestCase):
 def setUp(self):
  self.seed={'kc':np.array([.1,-.1]),'fc':np.array([.2,-.2])}
  self.frames=[{'anchor':14400,'args':{'fail':False}},{'anchor':28800,'args':{'fail':True}},{'anchor':43200,'args':{}}]
 def test_failed_gate_keeps_new_H(self):
  r=evolve(controlled_step,self.frames,{},self.seed,set())
  self.assertIsInstance(r,list)
  np.testing.assert_allclose(r[1]['kc'],[.3,-.3]);self.assertFalse(r[1]['accepted'])
  np.testing.assert_array_equal(r[1]['published'],r[0]['published'])
  np.testing.assert_allclose(r[2]['kc'],[.4,-.4])
 def test_missing_anchor_no_signal_step(self):
  r=evolve(controlled_step,self.frames,{},self.seed,{28800})
  self.assertIsInstance(r,list)
  np.testing.assert_array_equal(r[1]['kc'],r[0]['kc'])
  np.testing.assert_allclose(r[2]['kc'],[.3,-.3])
 def test_same_seed_identical(self):
  a=evolve(controlled_step,self.frames,{},self.seed,set());b=evolve(controlled_step,self.frames,{},self.seed,set())
  self.assertIsInstance(a,list)
  for x,y in zip(a,b):np.testing.assert_array_equal(x['raw'],y['raw'])
 def test_no_seed_mutation(self):
  before=self.seed['kc'].copy();r=evolve(controlled_step,self.frames,{},self.seed,set())
  self.assertIsInstance(r,list);np.testing.assert_array_equal(self.seed['kc'],before)
 def test_clock_gap_refused(self):
  with self.assertRaises(ValueError):evolve(controlled_step,self.frames[::2],{},self.seed,set())
 def test_unknown_hold_refused(self):
  with self.assertRaises(ValueError):evolve(controlled_step,self.frames,{},self.seed,{14401})

if __name__=='__main__':unittest.main()
