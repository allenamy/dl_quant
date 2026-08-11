import os
src = open('probe1b_v2.py').read().split('def analyse(')[0].replace(
    "SP = os.path.dirname(os.path.abspath(__file__))", "SP = os.getcwd()")
exec(src)
import random, statistics

pos = positions(SH); ts = sorted(pos)
def cum_disp(BETA):
    tot = 0.0
    for k in range(len(ts)-1):
        a, b = ts[k], ts[k+1]
        if (b-a)/3600.0 > 6: continue
        pa, pb = px('BTCUSDT', a), px('BTCUSDT', b)
        if not pa or not pb: continue
        rbtc = pb/pa - 1.0
        vals = [(s, float(p.get('venue_position_notional') or 0)) for s, p in pos[a].items()]
        vals = [(s, v) for s, v in vals if v and s in BETA]
        g = sum(abs(v) for _, v in vals)
        if g <= 100: continue
        bbar = sum(abs(v)*BETA[s] for s, v in vals)/g
        tot += sum(v*(BETA[s]-bbar) for s, v in vals) * rbtc
    return tot

real = cum_disp(B_JUN)
syms = sorted(B_JUN); vals = [B_JUN[s] for s in syms]
random.seed(0)
null = []
for _ in range(2000):
    sh = vals[:]; random.shuffle(sh)
    null.append(cum_disp(dict(zip(syms, sh))))
null.sort()
ge = sum(1 for x in null if abs(x) >= abs(real))
print('REAL cumulative dispersion PnL      $%+.2f' % real)
print('placebo (betas shuffled across names, B=2000):')
print('  null mean $%+.2f  sd $%.2f  p2.5 $%+.2f  p97.5 $%+.2f'
      % (statistics.mean(null), statistics.stdev(null), null[50], null[1949]))
print('  p(|null| >= |real|) = %.4f' % (ge/len(null)))
print('  => the result %s attributable to WHICH names carry which beta'
      % ('IS' if ge/len(null) < 0.05 else 'is NOT clearly'))
