import numpy as np, time
A=np.load('arms.npz'); L=np.load('labels.npz')
lmap={int(t):int(l) for t,l in zip(L['ts'],L['lab'])}
NAMES={0:'LL',1:'LH',2:'HL',3:'HH'}
ts=A['PARITY_A0_dyn_s42__legs_ts'].astype(np.int64)
legs={k:A['PARITY_A0_dyn_s42__legs_'+k] for k in ('king','rev24','fund')}
lb=np.array([lmap.get(int(t),-1) for t in ts]); yr=np.array([time.gmtime(int(t)).tm_year for t in ts])
print("leg TARGET-LAYER unit-gross price return, bps/anchor (NOT the book layer; no carry, no cost)")
print("leg availability: king is identically 0 before 2024 (zero OOS coverage)")
def sh(v): return v.mean()/v.std(ddof=1)*np.sqrt(2190) if len(v)>2 and v.std(ddof=1)>0 else np.nan
print(f"\n{'cell':5s}"+"".join(f"{k:>22s}" for k in legs))
for l in (0,1,2,3):
    m=lb==l; line=f"{NAMES[l]:5s}"
    for k in legs:
        v=legs[k][m]; line+=f"{v.mean():12.3f}({sh(v):5.2f})n{int(m.sum())}"[:22].rjust(22)
    print(line)
print(f"\nsplit by era (king live only 2024+):")
for era,msk in (("2022-2023", yr<2024), ("2024-2026", yr>=2024), ("2024-2024", yr==2024), ("2025+", yr>=2025)):
    print(f" -- {era} --")
    for l in (0,1,2,3):
        m=(lb==l)&msk
        if m.sum()<30: print(f"   {NAMES[l]:4s} n={int(m.sum()):5d}  (too few)"); continue
        line=f"   {NAMES[l]:4s} n={int(m.sum()):5d} "
        for k in legs:
            v=legs[k][m]; line+=f" {k}:{v.mean():7.3f}({sh(v):5.2f})"
        print(line)
print("\nfund leg by year x cell:")
print(f"{'yr':5s}"+"".join(f"{NAMES[l]:>16s}" for l in (0,1,2,3)))
for y in range(2022,2027):
    line=f"{y:<5d}"
    for l in (0,1,2,3):
        m=(yr==y)&(lb==l)
        line+= f"{legs['fund'][m].mean():9.3f}[{int(m.sum()):4d}]" if m.sum()>30 else f"{'--':>16s}"
    print(line)
print("\nking leg by year x cell:")
for y in range(2024,2027):
    line=f"{y:<5d}"
    for l in (0,1,2,3):
        m=(yr==y)&(lb==l)
        line+= f"{legs['king'][m].mean():9.3f}[{int(m.sum()):4d}]" if m.sum()>30 else f"{'--':>16s}"
    print(line)
