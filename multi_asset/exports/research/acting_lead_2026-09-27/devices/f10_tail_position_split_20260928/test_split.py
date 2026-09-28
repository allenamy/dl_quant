import unittest
import numpy as np
try:
    from split import split_weights
except ImportError:
    def split_weights(old, new, y):
        raise NotImplementedError('tail position decomposition absent')

class Split(unittest.TestCase):
    def test_long_reduction(self):
        np.testing.assert_allclose(split_weights([.4], [.2], [.1]), [[0], [-200], [0], [0]])
    def test_short_increase(self):
        np.testing.assert_allclose(split_weights([-.1], [-.3], [.1]), [[0], [0], [-200], [0]])
    def test_crossing_long_to_short(self):
        np.testing.assert_allclose(split_weights([.4], [-.2], [.1]), [[0], [-400], [-200], [0]])
    def test_crossing_short_to_long(self):
        np.testing.assert_allclose(split_weights([-.4], [.2], [.1]), [[200], [0], [0], [400]])
    def test_down_prices_sign_and_identity(self):
        a=np.array([.1,-.2,.3,-.4]); b=np.array([.3,-.1,-.4,.2]); y=np.array([-.1,.2,-.3,.4])
        np.testing.assert_allclose(split_weights(a,b,y).sum(0),(b-a)*y*1e4)
    def test_invalid(self):
        for a,b,y in [([],[],[]),([.1],[.2,.3],[1]),([float('nan')],[0],[1]),([0],[0],[float('inf')])]:
            with self.assertRaises(ValueError): split_weights(a,b,y)

if __name__=='__main__': unittest.main()
