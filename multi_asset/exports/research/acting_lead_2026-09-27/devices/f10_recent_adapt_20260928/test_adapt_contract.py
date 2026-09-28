import unittest, math
from adapt_contract import probabilities, choose, causal_windows

class ContractTests(unittest.TestCase):
    def test_uniform(self):
        self.assertEqual(probabilities([0, 86400], 86400, None), [.5, .5])
    def test_half_life(self):
        p=probabilities([0, 180*86400],180*86400,180)
        self.assertAlmostEqual(p[1]/p[0],2)
    def test_unknown(self):
        for x in [0,-1,float('inf'),float('nan')]:
            with self.assertRaises(ValueError):probabilities([0],1,x)
        for ends,cut in [([],0),([2],1),([float('nan')],1),([0],float('inf'))]:
            with self.assertRaises(ValueError):probabilities(ends,cut,180)
    def test_cdf(self):
        self.assertEqual(choose([.25,.75],[0,.249,.25,.999]),[0,0,1,1])
        for ps,us in [([.5,.6],[.1]),([1],[1]),([1],[float('nan')]),([-.1,1.1],[.1])]:
            with self.assertRaises(ValueError):choose(ps,us)
    def test_budget(self):
        us=[(i+.5)/96 for i in range(96)]
        self.assertEqual(len(choose(probabilities([0,1],1,180),us)),96)
    def test_future(self):
        a=[i*14400 for i in range(400)];ready=[True]*400
        w=causal_windows(a,ready,[60]*400, 350*14400)
        self.assertTrue(w)
        self.assertTrue(all(a[s[-1]]+14400<=350*14400 for s in w))
        # Appending an unobservable future cannot affect the training set.
        self.assertEqual(w,causal_windows(a+[400*14400],ready+[True],[60]*401,350*14400))
    def test_internal_unready(self):
        a=[i*14400 for i in range(400)];ready=[True]*400;ready[100]=False
        w=causal_windows(a,ready,[60]*400,350*14400)
        self.assertTrue(all(100 not in s for s in w))
    def test_axis(self):
        with self.assertRaises(ValueError):causal_windows([0,14400,30000],[True]*3,[60]*3,100000)

if __name__=='__main__':unittest.main()
