from __future__ import annotations
import numpy as np, glob, warnings
warnings.filterwarnings("ignore")
from scipy.stats import spearmanr, pearsonr
def dd(p): return p.split("/")[-1][:-4]
def load_month(mon):
    fs=sorted(glob.glob("data/npz_v2arch/*.npz")); days=[f for f in fs if dd(f)[:7]==mon]
    ys=[];tss=[]
    for f in days:
        d=np.load(f,allow_pickle=True); m=d["y_mask_600"].astype(bool)
        ys.append(d["y_600"][m].astype(np.float64)); tss.append(d["timestamps"][m].astype(np.int64))
    return np.concatenate(ys),np.concatenate(tss)
print("=== DIAGNOSE the suspicious result ===")
for mon in ["2025-12","2026-02"]:
    y,ts=load_month(mon); o=np.argsort(ts); y=y[o]; n=len(y); N=30
    Lt=[];Ls=[]
    for i in range(n-N):
        fy=y[i+1:i+1+N]
        if len(fy)>5 and fy.std()>0: Lt.append(np.corrcoef(fy[:-1],fy[1:])[0,1]); Ls.append(np.abs(fy).std())
    Lt=np.array(Lt);Ls=np.array(Ls)
    print(f"\n{mon}:")
    print(f"  L_trend (fwd AR1): mean={Lt.mean():+.3f} std={Lt.std():.3f} | frac>0={np.mean(Lt>0):.3f}  <- if ~1.0 or ~0.0, label is near-constant-sign => dir-acc meaningless")
    print(f"  L_strong (fwd |y| disp): mean={Ls.mean():.5f} std={Ls.std():.5f}")
    # is L_strong just CURRENT vol persistence? corr(current |y| dispersion over PAST N, forward L_strong)
    cur_disp=np.array([ np.abs(y[max(0,i-N):i+1]).std() for i in range(n-N)])
    c=spearmanr(cur_disp,Ls)[0]
    print(f"  spearman(PAST-|y|-disp, FWD-|y|-disp) = {c:+.3f}  <- if HIGH, FWD-STRONG is TRIVIAL vol-persistence (current vol predicts forward vol)")
    # and does forward vol relate to forward PREDICTABILITY (signal-favorability), or just vol magnitude?
    print(f"  NOTE: FWD-STRONG = forward |y| DISPERSION = volatility, NOT signal-favorability. Vol is persistent => trivially predictable, != regime-for-gating.")
