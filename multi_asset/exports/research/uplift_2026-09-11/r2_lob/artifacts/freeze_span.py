"""Freeze the LOBFULL anchor set from the 34 tranche-1 arms so every later arm is judged on the SAME span."""
import numpy as np, glob, os, json, datetime as dt
COLS=["ts","net","pnl","carry","cost","gross_total","gross_member","gross_sel","nsel","nmember","fires","leg_king","leg_rev24","leg_fund","w3_king","w3_rev24","w3_fund","turnover","net_ex","pnl_ex","carry_ex","cost_ex","netlong"]
C={c:i for i,c in enumerate(COLS)}
live=None
fs=[f for f in sorted(glob.glob("/workspace/uplift_2026-09-11/r2/arms/*.npz")) if os.path.basename(f).startswith("R2_")]
assert len(fs)==34,len(fs)
for f in fs:
    R=np.load(f,allow_pickle=True)["rec"]
    ts=np.round(R[:,0].astype(float)).astype(np.int64)
    a=set(int(x) for x in ts[(R[:,C["gross_total"]]>1e-12)&(R[:,C["w3_fund"]]>0.999)])
    live=a if live is None else (live&a)
L=np.array(sorted(live),dtype=np.int64)
np.save("/workspace/uplift_2026-09-11/r2/LOBTS_frozen.npy",L)
print("frozen span n=%d  %s -> %s  (from %d tranche-1 arms)"%(len(L),dt.datetime.utcfromtimestamp(int(L[0])),dt.datetime.utcfromtimestamp(int(L[-1])),len(fs)))
