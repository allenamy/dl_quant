"""Track F step 2b: arsenal on a COMMON anchor set, with per-cell n, and the P&L decomposition
that tests the dispersion mechanism (alpha scales with dispersion, carry+cost do not)."""
import numpy as np, time, json
R = "/workspace/uplift_2026-09-11/trackF"
L = np.load(f"{R}/regime_labels.npz"); ts_r = L["ts"]; LAB = L["lab"]
Z = np.load(f"{R}/regime_vars.npz", allow_pickle=True); RC = [str(c) for c in Z["cols"]]; V = Z["V"]; K = {c: i for i, c in enumerate(RC)}
NAMES = {-1: "WARM", 0: "LL", 1: "LH", 2: "HL", 3: "HH"}
COLSR = ["ts","net","pnl","carry","cost","gross_total","gross_member","gross_sel","nsel","nmember","fires","leg_king","leg_rev24","leg_fund","w3_king","w3_rev24","w3_fund","turnover","net_ex","pnl_ex","carry_ex","cost_ex","netlong"]
C = {c: i for i, c in enumerate(COLSR)}
ARMS = ["PARITY_A0_dyn_s42","AR_KF_p0","AR_FUND","AR_KING","AR_REV","AR_ALL3_p45","AR_ALL3_p0","AR_F10","AR_KF_noftrim"]
LBL = {"PARITY_A0_dyn_s42":"A0 in-service","AR_KF_p0":"king+fund noDL","AR_FUND":"fund only","AR_KING":"king only",
       "AR_REV":"rev24 only","AR_ALL3_p45":"3legs+DL","AR_ALL3_p0":"3legs noDL","AR_F10":"DL-slot book","AR_KF_noftrim":"A0 no-FTRIM"}
D = {}
for a in ARMS:
    A = np.load(f"{R}/dev_v4F/probe_artifacts/w10_ablation_series__{a}.npz", allow_pickle=True)
    Rr = A["d30_n2_c42_rec"]; D[a] = (np.round(Rr[:,0]).astype(np.int64), Rr)
common = set(D[ARMS[0]][0].tolist())
for a in ARMS[1:]: common &= set(D[a][0].tolist())
common = np.array(sorted(common)); print("common anchors across all 9 forms:", len(common),
      time.strftime("%F",time.gmtime(common[0])), "->", time.strftime("%F",time.gmtime(common[-1])))
lmap = {int(t): LAB[i] for i,t in enumerate(ts_r)}
lc = np.array([lmap.get(int(t),-1) for t in common]); yc = np.array([time.gmtime(int(t)).tm_year for t in common])
def sh(v): return (v.mean()/v.std(ddof=1)*np.sqrt(2190)) if len(v)>2 and v.std(ddof=1)>0 else np.nan
print("\ncommon-set cell sizes:", {NAMES[l]: int((lc==l).sum()) for l in (-1,0,1,2,3)})
print("common-set year sizes:", {int(y): int((yc==y).sum()) for y in range(2022,2027)})
print("\n=== ARSENAL on the COMMON anchor set: mean g (Sharpe) by regime cell ===")
print(f"{'form':17s}" + "".join(f"{NAMES[l]+' n='+str(int((lc==l).sum())):>19s}" for l in (0,1,2,3)) + f"{'ALL':>19s}")
out={}
for a in ARMS:
    ts,Rr = D[a]; idx = {int(t):i for i,t in enumerate(ts)}
    sel = np.array([idx[int(t)] for t in common]); g = Rr[sel,C["net_ex"]]/Rr[sel,C["gross_total"]]
    line=f"{LBL[a]:17s}"; cells={}
    for l in (0,1,2,3):
        v=g[lc==l]; cells[NAMES[l]]={"n":int(len(v)),"mean":float(v.mean()),"sharpe":float(sh(v)),"se_mean":float(v.std(ddof=1)/np.sqrt(len(v)))}
        line+=f"{v.mean():11.3f}({sh(v):5.2f})"
    v=g[lc>=0]; cells["ALL"]={"n":int(len(v)),"mean":float(v.mean()),"sharpe":float(sh(v))}
    line+=f"{v.mean():11.3f}({sh(v):5.2f})"
    out[a]={"label":LBL[a],"cells":cells}
    print(line)
# 1-D splits
print("\n=== 1-D splits (common set) ===")
for nm,mask in (("disp24 LOW", (lc==0)|(lc==2)), ("disp24 HIGH",(lc==1)|(lc==3)), ("sigfund LOW",(lc==0)|(lc==1)), ("sigfund HIGH",(lc==2)|(lc==3))):
    line=f"{nm:13s} n={int(mask.sum()):5d} "
    for a in ("PARITY_A0_dyn_s42","AR_FUND","AR_KING","AR_F10"):
        ts,Rr=D[a]; idx={int(t):i for i,t in enumerate(ts)}; sel=np.array([idx[int(t)] for t in common])
        g=Rr[sel,C["net_ex"]]/Rr[sel,C["gross_total"]]; v=g[mask]
        line+=f"{LBL[a]}: {v.mean():6.3f}({sh(v):5.2f})  "
    print(line)
# decomposition of A0 per cell: pnl_ex / carry_ex / cost_ex per unit gross
print("\n=== A0 decomposition per unit gross (bps/anchor): pnl - carry - cost = net ===")
ts,Rr=D["PARITY_A0_dyn_s42"]; idx={int(t):i for i,t in enumerate(ts)}; sel=np.array([idx[int(t)] for t in common]); S=Rr[sel]
gt=S[:,C["gross_total"]]
for l in (0,1,2,3):
    m=lc==l
    print(f"{NAMES[l]:4s} n={int(m.sum()):5d} pnl {np.mean(S[m,C['pnl_ex']]/gt[m]):7.3f}  carry {np.mean(S[m,C['carry_ex']]/gt[m]):7.3f}  "
          f"cost {np.mean(S[m,C['cost_ex']]/gt[m]):7.3f}  net {np.mean(S[m,C['net_ex']]/gt[m]):7.3f}  "
          f"| w3_king {np.mean(S[m,C['w3_king']]):5.3f} w3_fund {np.mean(S[m,C['w3_fund']]):5.3f} turn {np.mean(S[m,C['turnover']]):6.4f}")
# per-year x cell for A0
print("\n=== A0 mean g by (year, cell) ===")
g=S[:,C["net_ex"]]/gt
print(f"{'year':6s}" + "".join(f"{NAMES[l]:>18s}" for l in (0,1,2,3)))
for y in range(2022,2027):
    line=f"{y:<6d}"
    for l in (0,1,2,3):
        m=(yc==y)&(lc==l)
        line += f"{g[m].mean():10.3f}[{int(m.sum()):4d}]" if m.sum()>2 else f"{'--':>18s}"
    print(line)
json.dump(out, open(f"{R}/RESULT_arsenal_common.json","w"), indent=1)
