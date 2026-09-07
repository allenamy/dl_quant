import numpy as np, json, time, calendar, hashlib
PA="/workspace/review_scratch/allweather_trackB/replay/dev_alt/probe_artifacts"
GA="/workspace/review_scratch/dl_monthly_gate/replay/dev_alt/probe_artifacts"
COLS=["ts","net","pnl","carry","cost","gross_total","gross_member","gross_sel","nsel","nmember","fires","leg_king","leg_rev24","leg_fund","w3_king","w3_rev24","w3_fund","turnover","net_ex","pnl_ex","carry_ex","cost_ex","netlong"]
ARM="d30_n2_c42"; NB=2000; SEED=20260905
CUT=calendar.timegm((2026,8,10,20,0,0)); T2503=calendar.timegm((2025,3,1,0,0,0)); T26=calendar.timegm((2026,1,1,0,0,0))
A={"R0_s42":f"{GA}/w10_ablation_series_G_mE1_R0.npz",
   "CONST42":f"{PA}/w10_ablation_series_G_mE1c_R0_spl42.npz",
   "FLOOR5_s42":f"{PA}/w10_ablation_series_G_mE1cF5_R0_spl42.npz",
   "FIX7_s42":f"{PA}/w10_ablation_series_G_mE1cX7_R0_spl42.npz",
   "R0_s2027":f"{PA}/w10_ablation_series_G_mE1s2027_R0_spl27.npz",
   "CONSTspl27":f"{PA}/w10_ablation_series_G_mE1c_R0_spl27.npz",
   "FLOOR5_s2027":f"{PA}/w10_ablation_series_G_mE1cF5s27_R0_spl27.npz",
   "FIX7_s2027":f"{PA}/w10_ablation_series_G_mE1cX7s27_R0_spl27.npz"}
D={};MT={}
for k,p in A.items():
    z=np.load(p,allow_pickle=True); cfg=json.loads(str(z["config_json"])); assert [str(c) for c in z["cols"]]==COLS,k
    for kk,v in {"LEGS":"101","CAL":"log","LOOK":900,"WRULE":"msharpe","MEMBERS_TOPN":829,"TRADE_TOPN":0,"FTRIM":"zero","UMASK_SCOPE":"m1","W3FIX":None}.items():
        assert cfg.get(kk)==v,(k,kk,cfg.get(kk),v)
    assert abs(cfg["PHI"]-0.45)<1e-12 and cfg.get("PHIDYN",0)==0,k
    Rr=z[f"{ARM}_rec"]; D[k]={c:Rr[:,i] for i,c in enumerate(COLS)}
    MT[k]={"sha16":hashlib.sha256(open(p,"rb").read()).hexdigest()[:16],"FPRED":cfg["FPRED"],"FSEED":cfg["FSEED"],"n":int(len(Rr))}
ks=list(D); ts={k:D[k]["ts"].astype(np.int64) for k in ks}
common=ts[ks[0]]
for k in ks[1:]: common=np.intersect1d(common,ts[k])
print("n_common",len(common),"| per-arm n:",{k:MT[k]["n"] for k in ks})
G={}
for k in ks:
    ix=np.searchsorted(ts[k],common); assert np.array_equal(ts[k][ix],common)
    G[k]=(D[k]["net_ex"][ix]/D[k]["gross_total"][ix]).astype(float)
GT=(D["R0_s42"]["gross_total"][np.searchsorted(ts["R0_s42"],common)]).astype(float)
days=common//86400
W={"FROZEN":(common>=T2503)&(common<=CUT),"2026<=cut":(common>=T26)&(common<=CUT)}
rng=np.random.default_rng(SEED)
def boot(x,m):
    v=x[m];d=days[m];ud,inv=np.unique(d,return_inverse=True);nd=len(ud)
    s=np.bincount(inv,weights=v,minlength=nd);c=np.bincount(inv,minlength=nd)
    idx=rng.integers(0,nd,size=(NB,nd));mn=s[idx].sum(1)/c[idx].sum(1)
    return float(v.mean()),float(np.percentile(mn,2.5)),float(np.percentile(mn,97.5)),float((mn>0).mean()),int(m.sum())
P=[("FLOOR5_s42","R0_s42"),("FLOOR5_s42","CONST42"),("FIX7_s42","R0_s42"),("FIX7_s42","CONST42"),
   ("FLOOR5_s2027","R0_s2027"),("FIX7_s2027","R0_s2027"),("FLOOR5_s2027","CONSTspl27"),("FIX7_s2027","CONSTspl27"),
   ("R0_s42","CONST42"),("R0_s2027","CONSTspl27")]
for wn,m in W.items():
    print(f"\n=== {wn} (n={int(m.sum())}) per-gross bps/anchor ===")
    for x,r in P:
        mu,lo,hi,pp,n=boot(G[x]-G[r],m)
        print(f"  {x:14s} - {r:12s}  {mu:+.4f} [{lo:+.4f},{hi:+.4f}] P{pp:.3f}")
print("\nFROZEN gross_total mean =",float(GT[W["FROZEN"]].mean()))
print("arm meta:"); [print(" ",k,MT[k]) for k in ks]
