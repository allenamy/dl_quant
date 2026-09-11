"""INFRA2 step 1: locate the residual in the FEMAT (sleeve/blend) injection path.
Hypothesis set: (H1) rank engine mismatch argsort-argsort (ORDINAL) vs scipy rankdata (AVERAGE) on ties;
(H2) float32 storage collapsing distinct ranks; (H3) finite-mask/n mismatch; (H4) the >=10 threshold."""
import numpy as np, json
from scipy.stats import rankdata
COLS=["ts","net","pnl","carry","cost","gross_total","gross_member","gross_sel","nsel","nmember","fires","leg_king","leg_rev24","leg_fund","w3_king","w3_rev24","w3_fund","turnover","net_ex","pnl_ex","carry_ex","cost_ex","netlong"]
C={c:i for i,c in enumerate(COLS)}
HC="/workspace/review_scratch/health_check/dev_v4/probe_artifacts"
A0=np.load(HC+"/w10_ablation_series_V4_A0_dyn_s42.npz",allow_pickle=True)
R0=np.asarray(A0["d30_n2_c42_rec"],float)
P=np.load("/workspace/uplift_2026-09-11/attack_trackD_newalpha/out/XIB_PARITY.npz",allow_pickle=True)
R1=np.asarray(P["rec"],float)
t0=np.round(R0[:,0]).astype(np.int64); t1=np.round(R1[:,0]).astype(np.int64)
print("A0 n",len(t0),"PARITY n",len(t1),"axis equal",np.array_equal(t0,t1))
com,i0,i1=np.intersect1d(t0,t1,return_indices=True)
g0=R0[i0,C["net_ex"]]/R0[i0,C["gross_total"]]; g1=R1[i1,C["net_ex"]]/R1[i1,C["gross_total"]]
d=g1-g0
print("n_common %d  mean dg %+.6f  mean|dg| %.6f  max|dg| %.4f  n_exact %d  frac_exact %.6f"%(
  len(com),d.mean(),np.abs(d).mean(),np.abs(d).max(),int((d==0).sum()),float((d==0).mean())))
bad=np.nonzero(d!=0)[0]
print("n_anchors_differing",len(bad))
# per-column exact match
for c in ("net_ex","pnl_ex","carry_ex","cost_ex","gross_total","nsel","turnover","leg_fund"):
    dd=R1[i1,C[c]]-R0[i0,C[c]]
    print("  %-12s n_diff %5d  max|d| %.6g"%(c,int((dd!=0).sum()),np.abs(dd).max()))
# ---- the tie test on the panel
PW=np.load("/workspace/data/wide_panel_4h_v2ext.npz",allow_pickle=True)
pts=PW["ts"].astype(np.int64); FE1=np.asarray(PW["f_fund_ema_v1"],float)
row={int(t):j for j,t in enumerate(pts)}
nrow_tie=0; ntie_cells=0; rows_with_tie=[]
for j in range(FE1.shape[0]):
    v=FE1[j]; ok=np.isfinite(v)
    if ok.sum()<10: continue
    u=np.unique(v[ok])
    if len(u)<ok.sum():
        nrow_tie+=1; ntie_cells+=int(ok.sum()-len(u)); rows_with_tie.append(j)
print("panel rows %d | rows with TIES in f_fund_ema_v1: %d | excess tied cells %d"%(FE1.shape[0],nrow_tie,ntie_cells))
rset=set(rows_with_tie)
# map differing anchors -> panel rows
prow=np.array([row.get(int(t),-1) for t in com])
badrows=prow[bad]
print("differing anchors whose panel row has ties: %d / %d"%(int(sum(1 for r in badrows if r in rset)),len(bad)))
allrows=set(int(r) for r in prow if r>=0)
print("anchors total %d, of which tied-panel-row %d"%(len(prow),len(allrows&rset)))
# ---- float32 collision test
def rz_ord(v,ok):
    return np.argsort(np.argsort(v[ok]))/max(ok.sum()-1,1)-0.5
def rz_avg(v,ok):
    return rankdata(v[ok])/max(ok.sum()-1,1)-0.5
coll=0; ordneq=0; chk=0
for j in range(0,FE1.shape[0],7):
    v=FE1[j]; ok=np.isfinite(v)
    if ok.sum()<10: continue
    chk+=1
    a=rz_avg(v,ok); o=rz_ord(v,ok)
    af=a.astype(np.float32).astype(np.float64)
    if len(np.unique(af))!=len(np.unique(a)): coll+=1
    # does re-ranking the ORDINAL vector reproduce re-ranking the raw?
    if not np.array_equal(rankdata(o),rankdata(v[ok])): ordneq+=1
print("sampled %d rows | float32 rank collisions %d | ORDINAL re-rank != raw re-rank %d"%(chk,coll,ordneq))
