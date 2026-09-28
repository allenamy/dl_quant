import copy
import unittest
import numpy as np
from prediction_bridge import align_prefix, complete_daily

def fixture():
 a={'anchors':np.arange(8)*14400,'count':np.full(8,2),'off':np.arange(9)*2,'m':np.tile([0,1],8),'symbols':np.array(['A','B']), 'raw_y':np.arange(16,dtype=float),'rank_y':np.tile([-.5,.5],8)}
 b={k:v.copy() for k,v in a.items()}
 for k in ('anchors','count'):b[k]=b[k][:6]
 b['off']=b['off'][:7]
 for k in ('m','raw_y','rank_y'):b[k]=b[k][:12]
 return a,b

class Bridge(unittest.TestCase):
 def test_exact_prefix_and_equal_unknown(self):
  a,b=fixture();a['raw_y'][0]=b['raw_y'][0]=np.nan
  self.assertEqual(align_prefix(a,b),(6,12))
 def test_same_size_member_swap_refused(self):
  a,b=fixture();b['m'][:2]=[1,0]
  with self.assertRaises(ValueError):align_prefix(a,b)
 def test_timestamp_shift_refused(self):
  a,b=fixture();b['anchors'][3]+=1
  with self.assertRaises(ValueError):align_prefix(a,b)
 def test_changed_label_refused(self):
  a,b=fixture();b['raw_y'][1]+=.001
  with self.assertRaises(ValueError):align_prefix(a,b)
 def test_infinity_refused(self):
  a,b=fixture();a['raw_y'][0]=b['raw_y'][0]=np.inf
  with self.assertRaises(ValueError):align_prefix(a,b)
 def test_incomplete_day_not_hidden(self):
  with self.assertRaises(ValueError):complete_daily(np.arange(5)*14400,np.ones((5,2)))
  np.testing.assert_equal(complete_daily(np.arange(6)*14400,np.ones((6,2))),[[1,1]])

if __name__=='__main__':unittest.main()
