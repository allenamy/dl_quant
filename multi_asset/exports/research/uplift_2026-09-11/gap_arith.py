# -*- coding: utf-8 -*-
import math, json
ANCH_PER_YR = 6*365.0            # 4h anchors per year
def se_sharpe(n):  return math.sqrt(ANCH_PER_YR/n)

rows=[]
# (label, sharpe, n)
cases=[("A0 full-cycle post-warm s42", 1.4150, 9018),
       ("A0 full-cycle post-warm s2027", 1.4370, 9018),
       ("A0 post-warm + E-0911-D cut (BUILD2 first-hand)", 1.2912, 9138),
       ("frozen window 2025-03..2026-08-10", 2.9357, 3168)]
for lab,s,n in cases:
    se=se_sharpe(n)
    rows.append((lab,s,n,se,s-1.96*se,s+1.96*se))
print("%-48s %8s %6s %7s %18s"%("case","Sharpe","n","SE","CI95"))
for lab,s,n,se,lo,hi in rows:
    print("%-48s %8.4f %6d %7.4f  [%6.3f, %6.3f]"%(lab,s,n,se,lo,hi))

print()
# What does "significantly above 3.0" require?
for lab,s,n in cases[:3]:
    se=se_sharpe(n)
    need = 3.0 + 1.96*se          # point estimate whose CI95 lower bound clears 3.0
    gap_se = (need - s)/se
    nbooks = (need/s)**2          # independent books of THIS quality, s*sqrt(N)
    print("%-48s need point est %.4f | gap %.2f SE | equiv %.2f independent books of its own quality"
          %(lab, need, gap_se, nbooks))

print()
# marginal: how much uncorrelated Sharpe must a SINGLE new sleeve carry, at equal gross?
s=1.4150; se=se_sharpe(9018); need=3.0+1.96*se
extra=math.sqrt(max(need**2-s**2,0.0))
print("single uncorrelated addition, equal risk contribution: Sharpe %.3f required (vs book's %.3f = %.2fx)"%(extra,s,extra/s))
# and what the frozen window was worth
print("regime rent = frozen/full-cycle = %.3fx"%(2.9357/1.4150))
