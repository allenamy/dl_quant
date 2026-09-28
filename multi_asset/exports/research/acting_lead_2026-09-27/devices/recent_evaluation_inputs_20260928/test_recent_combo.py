import unittest
import numpy as np
from recent_combo import seeded_function,universe_pin

class Controls(unittest.TestCase):
    def test_seeded_state_is_used(self):
        s='def evolve(w):\n    kc=np.zeros(w);fc=np.zeros(w)\n    for i in range(1):\n        kc=kc+1\n    return kc,fc\n'
        f=seeded_function(s,{'np':np})
        k,c=f(2,np.array([2.,3.]),np.array([4.,5.]));self.assertEqual(k.tolist(),[3.,4.]);self.assertEqual(c.tolist(),[4.,5.])
    def test_changed_source_initialization_refused(self):
        with self.assertRaises(ValueError):seeded_function('def evolve(w):\n    kc=np.ones(w);fc=np.zeros(w)\n',{'np':np})
    def test_explicit_universe_identity(self):
        p=universe_pin(['A','B','C'],['A','C'],np.array([1,0,1],bool));self.assertEqual(p.tolist(),[True,False,True])
    def test_changed_universe_refused(self):
        with self.assertRaises(ValueError):universe_pin(['A','B'],['B'],np.array([1,0],bool))
    def test_unknown_and_duplicate_names_refused(self):
        for names in (['X'],['A','A']):
            with self.assertRaises(ValueError):universe_pin(['A','B'],names,np.array([1,0],bool))

if __name__=='__main__':unittest.main()
