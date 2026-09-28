import io
import unittest
import numpy as np
import actual_blend_cash as A

def blob(anchor=100,idx=(0,1),val=(.1,-.1)):
    b=io.BytesIO();np.savez(b,anchor=anchor,idx=idx,val=val);return b.getvalue()

class Tests(unittest.TestCase):
    def test_state(self):self.assertEqual(A.read_state(blob(),100,['X','Y']),{'X':.1,'Y':-.1})
    def test_state_wrong_anchor(self):
        with self.assertRaises(ValueError):A.read_state(blob(),101,['X','Y'])
    def test_duplicate_index(self):
        with self.assertRaises(ValueError):A.read_state(blob(idx=(0,0)),100,['X','Y'])
    def test_bad_index(self):
        with self.assertRaises(ValueError):A.read_state(blob(idx=(0,2)),100,['X','Y'])
    def test_nonfinite(self):
        with self.assertRaises(ValueError):A.read_state(blob(val=(.1,np.nan)),100,['X','Y'])
    def test_float_index(self):
        with self.assertRaises(ValueError):A.read_state(blob(idx=(0.,1.)),100,['X','Y'])
    def test_combination(self):
        r=A.allocate({'X':1,'Y':-1},{'X':0,'Y':0},{'X':.55,'Y':-.55},100,1.1,[],[],[],{'X':50,'Y':-50})
        self.assertAlmostEqual(r['components']['X']['kc'],50)
        self.assertEqual(r['components']['X']['fc'],0)
    def test_raw_mismatch_refused(self):
        with self.assertRaises(ValueError):A.allocate({'X':1,'Y':-1},{},{'X':.5,'Y':-.55},100,1,[],[],[],{'X':50,'Y':-50})
    def test_common_not_independent_scale(self):
        # Combined raw .55 + .90 = 1.45: KC must not be normalized to its own budget.
        r=A.allocate({'X':1,'Y':-1},{'X':2,'Y':-2},{'X':1.45,'Y':-1.45},100,2.9,[],[],[],{'X':50,'Y':-50})
        self.assertAlmostEqual(r['components']['X']['kc'],50*.55/1.45)
        self.assertAlmostEqual(r['components']['X']['fc'],50*.90/1.45)
    def test_named_clamp(self):
        r=A.allocate({'X':1,'Y':-1},{},{'X':.55,'Y':-.55},100,1.1,[],[],['X'],{'X':40,'Y':-50})
        self.assertAlmostEqual(r['components']['X']['clamp'],-10)
    def test_unlisted_difference(self):
        with self.assertRaises(ValueError):A.allocate({'X':1,'Y':-1},{},{'X':.55,'Y':-.55},100,1.1,[],[],[],{'X':40,'Y':-50})
    def test_forced_removed(self):
        r=A.allocate({'X':1,'Y':-1,'Z':1},{},{'X':.55,'Y':-.55,'Z':.55},100,1.65,['Z'],['Z'],[],{'X':50,'Y':-50,'Z':0})
        self.assertEqual(sum(r['components']['Z'].values()),0)
    def test_cancelled_components_need_price(self):
        r=A.value_components({'kc':10,'fc':-10,'export':0,'clamp':0},None,10)
        self.assertEqual(r['verdict'],'COMPONENT_UNPRICED')
        self.assertIsNone(r['values'])
    def test_zero_components_no_price(self):
        self.assertEqual(A.value_components(dict.fromkeys(A.PARTS,0),None,None)['values'],dict.fromkeys(A.PARTS,0))
    def test_component_value(self):
        r=A.value_components({'kc':10,'fc':20,'export':0,'clamp':-5},10,11)
        self.assertAlmostEqual(sum(r['values'].values()),2.5)

if __name__=='__main__':unittest.main()
