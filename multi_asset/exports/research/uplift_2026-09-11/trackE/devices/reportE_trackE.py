"""TRACK E report: tables from judge_trackE outputs + leg-turnover cost + deciding-question blocks."""
import numpy as np, json, os, sys, time, calendar
U="/workspace/uplift_2026-09-11"; AD=f"{U}/artifacts"
sys.path.insert(0,U)
import importlib.util
spec=importlib.util.spec_from_file_location("jt", f"{U}/judge_trackE.py")
# judge_trackE runs on import (argv driven) -> re-implement the few helpers here instead
COLS=["ts","net","pnl","carry","cost","gross_total","gross_member","gross_sel","nsel","nmember","fires","leg_king","leg_rev24","leg_fund","w3_king","w3_rev24","w3_fund","turnover","net_ex","pnl_ex","carry_ex","cost_ex","netlong"]
C={c:i for i,c in enumerate(COLS)}
def T(*a): return calendar.timegm(a+(0,)*(6-len(a)))
FROZEN=(T(2025,3,1),T(2026,8,10,20)+1)
def path(tag):
    p=f"{AD}/w10_ablation_series_{tag}.npz"
    if not os.path.exists(p): p=f"/workspace/review_scratch/health_check/dev_v4/probe_artifacts/w10_ablation_series_{tag}.npz"
    return p
def rec(tag):
    A=np.load(path(tag),allow_pickle=True); R=A["d30_n2_c42_rec"]
    return np.round(R[:,0]).astype(np.int64), R
def legturn(tag):
    """leg-weight turnover: sum|dw3| per anchor on the frozen window, and its cost at 3.52 bps/unit intent
       (w3 is a share of a unit-gross book, so a change of |dw| in leg weight moves at most |dw| of gross)."""
    ts,R=rec(tag); m=(ts>=FROZEN[0])&(ts<FROZEN[1])
    W=R[m][:,[C["w3_king"],C["w3_rev24"],C["w3_fund"]]]
    d=np.abs(np.diff(W,axis=0)).sum(1)
    return float(d.mean()), float(d.mean()*3.52), float(R[m,C["turnover"]].mean())
if __name__=="__main__":
    tags=sys.argv[1:]
    print("%-24s %9s %9s %9s %9s" % ("tag","legturn","cost_bps","nameturn","w3king"))
    for t in tags:
        try:
            lt,ct,nt=legturn(t); ts,R=rec(t); m=(ts>=FROZEN[0])&(ts<FROZEN[1])
            print("%-24s %9.5f %9.4f %9.5f %9.4f" % (t,lt,ct,nt,R[m,C["w3_king"]].mean()))
        except Exception as e: print(t,"ERR",e)
