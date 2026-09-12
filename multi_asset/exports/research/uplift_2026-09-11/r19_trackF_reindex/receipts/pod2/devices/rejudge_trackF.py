#!/usr/bin/env python3
"""r19 STEP 3 (T1) — re-judge every trackF result that consumed the regime labels (PREREG_r19 §2 C1-C4, §3, §4).
BEFORE = archived arms (trackF/dev_v4F/probe_artifacts) + archived labels (trackF/regime_labels.npz).
AFTER  = label-consuming arms re-run on the corrected labels (r19 dev_v4F19/probe_artifacts) + corrected labels
         (r19 regime_labels_fixed.npz); label-independent arms are the archived ones (their re-run is the negative control).
boot / gseries / levels / contrast are VERBATIM copies of trackF/judgeF.py (sha 15bdf51d...); the judge2 contrast
k-sequence and the composition / ceiling / diag2 logic are ported line-for-line so that BEFORE reproduces the
published RESULT_trackF_regime_conditional_2026-09-11.md numbers. Reads NO environment variable. CPU only."""
import numpy as np, json, time, calendar, hashlib, os, sys
CALPFX=('CAL','JUDGE','UPLIFT','PANEL','LOOK','WRULE','LEGS','PHI','FSEED','W3FIX','FTRIM','UMASK','SLOW','FPRED','MEMBERS_TOPN','COSTB','SLEEVE','KMOD','SEAT','RNSM','LTRIM','CDAMP','FUNDSCALE','FEMAT','TRADE_TOPN','REF_SKIP')
CALFLAGS=sorted(k for k in os.environ if k.startswith(CALPFX)); assert CALFLAGS==[], CALFLAGS
ENV_WL=[]; assert all(k not in os.environ for k in ENV_WL)
R19="/workspace/uplift_2026-09-11/r19_trackF_reindex"; TF="/workspace/uplift_2026-09-11/trackF"
PA=f"{TF}/dev_v4F/probe_artifacts/w10_ablation_series__%s.npz"; PB=f"{R19}/dev_v4F19/probe_artifacts/w10_ablation_series__%s.npz"
PREREG_SHA="6ef841333dd6260af7f1c9ae8a35c76cd505d2c09fd85e33a1d1f82560a4cefa"
def sha(p):
    h=hashlib.sha256()
    with open(os.path.realpath(p),'rb') as f:
        for b in iter(lambda: f.read(1<<22), b''): h.update(b)
    return h.hexdigest()
assert sha(f"{R19}/PREREG_r19_trackF_2026-09-12.md")==PREREG_SHA, "PREREG changed after freeze"
assert sha(f"{TF}/regime_labels.npz")=="18ee9e1ae6fd2f74577c6a871851cc543d399fe36f3e8c7d815546804152482b"
# ---------------- verbatim from judgeF.py ----------------
def T(*a): return calendar.timegm(a + (0,)*(6-len(a)))
FROZEN=(T(2025,3,1), T(2026,8,10,20)+1)
WIN={"2022":(T(2022,1,1),T(2023,1,1)),"2023":(T(2023,1,1),T(2024,1,1)),"2024":(T(2024,1,1),T(2025,1,1)),
     "2025":(T(2025,1,1),T(2026,1,1)),"2026->08-10":(T(2026,1,1),T(2026,8,10,20)+1),
     "frozen":FROZEN,"2024-01->2026-08-10":(T(2024,1,1),T(2026,8,10,20)+1),
     "holdout 2025-01->2026-08-10":(T(2025,1,1),T(2026,8,10,20)+1)}
APY=2190
COLSR=["ts","net","pnl","carry","cost","gross_total","gross_member","gross_sel","nsel","nmember","fires","leg_king","leg_rev24","leg_fund","w3_king","w3_rev24","w3_fund","turnover","net_ex","pnl_ex","carry_ex","cost_ex","netlong"]
C={c:i for i,c in enumerate(COLSR)}
def boot(v, days, rng, lo=2.5, hi=97.5):
    ud,inv=np.unique(days,return_inverse=True); nd=len(ud)
    if nd<3: return (float('nan'),)*3
    S=np.bincount(inv,weights=v,minlength=nd); N=np.bincount(inv,minlength=nd)
    idx=rng.integers(0,nd,size=(2000,nd)); mn=S[idx].sum(1)/N[idx].sum(1)
    return float(np.percentile(mn,lo)), float(np.percentile(mn,hi)), float((mn>0).mean())
def gseries(rec):
    ts=np.round(rec[:,0]).astype(np.int64); return ts, rec[:,C["net_ex"]]/rec[:,C["gross_total"]]
def levels(ts,g):
    o={}
    for w,(lo,hi) in WIN.items():
        m=(ts>=lo)&(ts<hi)
        if not m.any(): continue
        v=g[m]; c=np.concatenate([[0.0],np.cumsum(v)]); dd=float(np.max(np.maximum.accumulate(c)-c))
        o[w]={"n":int(m.sum()),"mean":float(v.mean()),
              "sharpe":float(v.mean()/v.std(ddof=1)*np.sqrt(APY)) if m.sum()>2 and v.std(ddof=1)>0 else float('nan'),
              "se_sharpe":float(np.sqrt(APY/m.sum())),"maxdd":dd,"ann_pct":float(v.mean()*APY/1e4*100)}
    return o
def contrast(tsA,gA,tsB,gB,k,alpha_lo=2.5,alpha_hi=97.5,win=FROZEN):
    ia={int(t):i for i,t in enumerate(tsA)}; ib={int(t):i for i,t in enumerate(tsB)}
    common=np.array(sorted(set(ia)&set(ib)))
    m=(common>=win[0])&(common<win[1]); cc=common[m]
    d=np.array([gB[ib[int(t)]]-gA[ia[int(t)]] for t in cc])
    rng=np.random.default_rng([20260905,k])
    lo,hi,p=boot(d, cc//86400, rng, alpha_lo, alpha_hi)
    return {"n":int(len(cc)),"delta":float(d.mean()),"ci_lo":lo,"ci_hi":hi,"p_gt0":p}
# ---------------- arms ----------------
# BEFORE (archive) = the round-2 archive files the published judges read: trackF/{arms,tf,tf2}.npz (repo copies shipped to r19/archive_npz;
# sha 4023f628... / 0dc9815d... / 27b0c472...). Where pod2 still holds the per-run probe_artifacts npz, the archive rec is ASSERTED bitwise equal.
ARCH_NPZ={p:np.load(f"{R19}/archive_npz/{p}",allow_pickle=True) for p in ("arms.npz","tf.npz","tf2.npz")}
assert sha(f"{R19}/archive_npz/arms.npz")=="4023f62829f403f3c04015a14d81a54d60351ffb1c145241a15710987ff341a5"
assert sha(f"{R19}/archive_npz/tf.npz")=="0dc9815d42dedaf3b9136ec9a6554267afb9790f1db5776575f5eb2a5867975b"
assert sha(f"{R19}/archive_npz/tf2.npz")=="27b0c4721c0f636c2b9f45a60fe0191d92ecdd70218f262986dc860cdedf2d1d"
ARCHIVE_XCHECK={}
def load_archive(tag):
    hits=[(p,Z) for p,Z in ARCH_NPZ.items() if f"{tag}__rec" in Z.files]; assert len(hits)==1, (tag,[p for p,_ in hits])
    rec=hits[0][1][f"{tag}__rec"]; src=f"{R19}/archive_npz/{hits[0][0]}::{tag}__rec"
    if os.path.exists(PA%tag):
        eq=bool(np.array_equal(rec, np.load(PA%tag,allow_pickle=True)["d30_n2_c42_rec"], equal_nan=True)); ARCHIVE_XCHECK[tag]=eq; assert eq, ("archive npz != pod2 probe artifact", tag)
    return rec, src
def load_r19(tag):
    p=PB%tag; return np.load(p,allow_pickle=True)["d30_n2_c42_rec"], p
ARCH_S42={"A0":"PARITY_A0_dyn_s42","KFnoDL":"AR_KF_p0","FUND":"AR_FUND","KING":"AR_KING","REV":"AR_REV","ALL3DL":"AR_ALL3_p45","ALL3":"AR_ALL3_p0",
          "DLslot":"AR_F10","noFTRIM":"AR_KF_noftrim","R1":"TF_R1","R1b":"TF_R1b","R2":"TF_R2","R3":"TF_R3","F1":"TF_F1","F1R":"TF_F1R","R5":"TF_R5","R6":"TF_R6"}
ARCH_S27={"A0":"S27_A0","R1":"S27_R1","F1":"S27_F1","R5":"S27_R5","R6":"S27_R6"}
LABEL_CONSUMING={"R1","R1b","R2","R3","F1R","R5","R6"}
FORM_ORDER=["A0","KFnoDL","FUND","KING","REV","ALL3DL","ALL3","DLslot","noFTRIM","R1","R1b","R2","R3","F1","F1R","R5","R6"]
def arms(which):
    out={"s42":{},"s2027":{}}
    for sd,M in (("s42",ARCH_S42),("s2027",ARCH_S27)):
        for nm,tag in M.items():
            out[sd][nm]=load_r19(tag) if (which=="after" and nm in LABEL_CONSUMING) else load_archive(tag)
    return out
ARMS={"before":arms("before"),"after":arms("after")}
print("archive npz vs pod2 probe_artifacts bitwise cross-check:", ARCHIVE_XCHECK)
class _Legs:  # legs arrays from the archived PARITY_A0 (arms.npz keys PARITY_A0_dyn_s42__legs_*)
    files=[k for k in ARCH_NPZ["arms.npz"].files if "__legs_" in k]
    def __getitem__(self,k): return ARCH_NPZ["arms.npz"][k]
LEGS=_Legs()
# ---------------- labels ----------------
def load_lab(p):
    L=np.load(p); return {int(t):int(l) for t,l in zip(L["ts"].astype(np.int64),L["lab"])}
LABS={"before":load_lab(f"{TF}/regime_labels.npz"),"after":load_lab(f"{R19}/regime_labels_fixed.npz")}
NAMES={-1:"WARM",0:"LL",1:"LH",2:"HL",3:"HH"}; CELLS=[0,1,2,3,-1]; CELLIDX={0:0,1:1,2:2,3:3,-1:4,"ALL":5}
def sh(v): return float(v.mean()/v.std(ddof=1)*np.sqrt(APY)) if len(v)>2 and v.std(ddof=1)>0 else float('nan')
OUT={"prereg_sha256":PREREG_SHA,"self_sha256":hashlib.sha256(open(__file__,'rb').read()).hexdigest(),"env_whitelist":ENV_WL,
     "arms":{w:{s:{nm:(sha(p) if os.path.exists(p) else p) for nm,(r,p) in d.items()} for s,d in ARMS[w].items()} for w in ARMS},
     "archive_npz_vs_pod2_probe_bitwise":ARCHIVE_XCHECK,
     "labels_sha256":{"before":sha(f"{TF}/regime_labels.npz"),"after":sha(f"{R19}/regime_labels_fixed.npz")}}
tsA0,gA0=gseries(ARMS["before"]["s42"]["A0"][0]); WARM_LO=int(tsA0[900]); WA_HI=T(2026,8,30,20)
OUT["W_ALPHA"]={"lo_utc":time.strftime("%F %HZ",time.gmtime(WARM_LO)),"hi_utc":"2026-08-30 20Z","n_A0":int(((tsA0>=WARM_LO)&(tsA0<=WA_HI)).sum())}

# ======== (A) judgeF: frozen-window contrasts vs A0, CI95 and Bonferroni K=6 (99.17%), k = judgeF CANDS[2:] order ========
JF_ORDER=[("R1",1),("R1b",2),("R2",3),("R3",4),("F1",5),("F1R",6)]
OUT["A_judgeF_frozen"]={}
print("\n=== (A) judgeF frozen-window contrast (cand - A0), s42; CI95 / CI99.17 (Bonf K=6) ===")
print(f"{'cand':6s}{'':8s}{'n':>6s}{'delta':>9s}{'CI95':>22s}{'CI99.17':>22s}{'P>0':>7s}")
for w in ("before","after"):
    tsA,gA=gseries(ARMS[w]["s42"]["A0"][0]); OUT["A_judgeF_frozen"][w]={}
    for nm,k in JF_ORDER:
        ts,g=gseries(ARMS[w]["s42"][nm][0]); c=contrast(tsA,gA,ts,g,k); c2=contrast(tsA,gA,ts,g,k,0.4167,99.5833)
        OUT["A_judgeF_frozen"][w][nm]={**c,"ci_bonf_lo":c2["ci_lo"],"ci_bonf_hi":c2["ci_hi"],"G1_pass_gt_0p23":bool(c["delta"]>0.23),"G2_pass_bonf_lo_gt0":bool(c2["ci_lo"]>0)}
        print(f"{nm:6s}{w:8s}{c['n']:6d}{c['delta']:+9.3f}   [{c['ci_lo']:+7.3f},{c['ci_hi']:+7.3f}]   [{c2['ci_lo']:+7.3f},{c2['ci_hi']:+7.3f}]{c['p_gt0']:7.3f}")

# ======== (B) judge2: levels per span, per-year means, contrasts (frozen/FULL/HOLDOUT) both seeds, running k ========
SPANS={"FULL":(0,T(2026,8,10,20)+1),"2023on":(T(2023,1,1),T(2026,8,10,20)+1),"2024on":(T(2024,1,1),T(2026,8,10,20)+1),
       "HOLDOUT":(T(2025,1,1),T(2026,8,10,20)+1),"frozen":FROZEN}
J2_S42=["A0","R1","R3","F1","F1R","R5","R6"]; J2_S27=["A0","R1","F1","R5","R6"]
OUT["B_judge2"]={}
for w in ("before","after"):
    OUT["B_judge2"][w]={"levels":{},"by_year":{},"contrasts":{}}
    for sd,names in (("s42",J2_S42),("s2027",J2_S27)):
        for nm in names:
            ts,g=gseries(ARMS[w][sd][nm][0]); lv={}
            for s,(lo,hi) in SPANS.items():
                m=(ts>=lo)&(ts<hi); v=g[m]; lv[s]={"n":int(m.sum()),"mean":float(v.mean()),"sharpe":sh(v),"se_sharpe":float(np.sqrt(APY/m.sum()))}
            yr=np.array([time.gmtime(int(t)).tm_year for t in ts]); by={}
            for y in range(2022,2027):
                m=yr==y
                if y==2026: m=m&(ts<=T(2026,8,10,20))
                by[str(y)]=float(g[m].mean())
            OUT["B_judge2"][w]["levels"][f"{sd}:{nm}"]=lv; OUT["B_judge2"][w]["by_year"][f"{sd}:{nm}"]=by
    k=0
    for nm in ("R1","R3","F1","F1R","R5","R6"):
        for sd,names in (("s42",J2_S42),("s2027",J2_S27)):
            if nm not in names: continue
            k+=1
            tsA,gA=gseries(ARMS[w][sd]["A0"][0]); ts,g=gseries(ARMS[w][sd][nm][0]); row={}
            for wn,win in (("frozen",FROZEN),("FULL",(0,T(2026,8,10,20)+1)),("HOLDOUT",(T(2025,1,1),T(2026,8,10,20)+1))):
                row[wn]={**contrast(tsA,gA,ts,g,k,win=win),"k":k}
            OUT["B_judge2"][w]["contrasts"][f"{sd}:{nm}"]=row
print("\n=== (B) judge2 contrasts vs A0 (delta [CI95]) : frozen | FULL | HOLDOUT ===")
for key in OUT["B_judge2"]["before"]["contrasts"]:
    line=f"{key:10s}"
    for w in ("before","after"):
        r=OUT["B_judge2"][w]["contrasts"][key]
        line+=f" | {w:6s} "+" ".join(f"{wn[:3]} {r[wn]['delta']:+.3f}[{r[wn]['ci_lo']:+.3f},{r[wn]['ci_hi']:+.3f}]" for wn in ("frozen","FULL","HOLDOUT"))
    print(line)
print("\n=== (B) FULL-history Sharpe (SE) and per-year mean g ===")
for key in OUT["B_judge2"]["before"]["levels"]:
    b=OUT["B_judge2"]["before"]["levels"][key]["FULL"]; a=OUT["B_judge2"]["after"]["levels"][key]["FULL"]
    yb=OUT["B_judge2"]["before"]["by_year"][key]; ya=OUT["B_judge2"]["after"]["by_year"][key]
    print(f"{key:10s} FULL Sh {b['sharpe']:5.2f}->{a['sharpe']:5.2f} (SE {b['se_sharpe']:.2f}) frozen Sh {OUT['B_judge2']['before']['levels'][key]['frozen']['sharpe']:5.2f}->{OUT['B_judge2']['after']['levels'][key]['frozen']['sharpe']:5.2f} | 2023 {yb['2023']:+.3f}->{ya['2023']:+.3f} 2024 {yb['2024']:+.3f}->{ya['2024']:+.3f} 2025 {yb['2025']:+.3f}->{ya['2025']:+.3f} 2026 {yb['2026']:+.3f}->{ya['2026']:+.3f}")

# ======== (C) conditional table per regime cell: W_ALPHA (primary) and trackF-original caliber (all labeled anchors, own axis) ========
def cond_table(w, sd, nm, caliber):
    rec,_=ARMS[w][sd][nm]; ts,g=gseries(rec); lab=np.array([LABS[w].get(int(t),-1) for t in ts])
    if caliber=="W_ALPHA": m0=(ts>=WARM_LO)&(ts<=WA_HI)
    else: m0=np.ones(len(ts),bool)
    fi=FORM_ORDER.index(nm); si=0 if sd=="s42" else 1; out={}
    for cell in CELLS+["ALL"]:
        m=m0&((lab>=0) if cell=="ALL" else (lab==cell))
        if m.sum()<3: out[NAMES.get(cell,"ALL")]={"n":int(m.sum())}; continue
        v=g[m]; k=100*fi+10*si+CELLIDX[cell]; rng=np.random.default_rng([20260905,k])
        lo,hi,p=boot(v,ts[m]//86400,rng)
        out[NAMES.get(cell,"ALL")]={"n":int(m.sum()),"mean":float(v.mean()),"ci_lo":lo,"ci_hi":hi,"p_gt0":p,"sharpe":sh(v),"se_sharpe":float(np.sqrt(APY/m.sum())),"k":k}
    return out
OUT["C_conditional"]={}
for cal in ("W_ALPHA","TF_ORIG"):
    OUT["C_conditional"][cal]={}
    for w in ("before","after"):
        OUT["C_conditional"][cal][w]={}
        for sd,names in (("s42",FORM_ORDER),("s2027",["A0","R1","F1","R5","R6"])):
            for nm in names: OUT["C_conditional"][cal][w][f"{sd}:{nm}"]=cond_table(w,sd,nm,cal)
    print(f"\n=== (C) conditional table [{cal}]: mean g (Sharpe) [CI95] per cell, before -> after ===")
    for key in OUT["C_conditional"][cal]["before"]:
        b=OUT["C_conditional"][cal]["before"][key]; a=OUT["C_conditional"][cal]["after"][key]; line=f"{key:12s}"
        for cell in ("LL","LH","HL","HH"):
            if "mean" in b[cell] and "mean" in a[cell]:
                flag="*" if (np.sign(b[cell]["mean"])!=np.sign(a[cell]["mean"]) and (a[cell]["ci_lo"]>0 or a[cell]["ci_hi"]<0)) else " "
                line+=f" {cell} n{b[cell]['n']:4d}->{a[cell]['n']:4d} {b[cell]['mean']:+.3f}->{a[cell]['mean']:+.3f}[{a[cell]['ci_lo']:+.2f},{a[cell]['ci_hi']:+.2f}]{flag}"
        print(line)

# ======== (D) composition: A0 cell shares FULL vs FROZEN, regime-mix expectation (composition.py port) ========
OUT["D_composition"]={}
for w in ("before","after"):
    OUT["D_composition"][w]={}
    for nm in ("A0","F1"):
        ts,g=gseries(ARMS[w]["s42"][nm][0]); lb=np.array([LABS[w].get(int(t),-1) for t in ts])
        full=ts<=T(2026,8,10,20); froz=(ts>=FROZEN[0])&(ts<FROZEN[1]); post=(lb>=0)&full; d={}
        for l in (0,1,2,3):
            m=(lb==l)&full; v=g[m]
            d[NAMES[l]]={"share_full":float(m.sum()/post.sum()),"share_frozen":float(((lb==l)&froz).sum()/froz.sum()),"mean":float(v.mean()),"sharpe":sh(v),"n":int(m.sum())}
        ws_full=np.array([((lb==l)&post).sum() for l in (0,1,2,3)],float); ws_full/=ws_full.sum()
        ws_fro=np.array([((lb==l)&froz).sum() for l in (0,1,2,3)],float); ws_fro/=ws_fro.sum()
        mu=np.array([g[(lb==l)&full].mean() for l in (0,1,2,3)]); sd_=np.array([g[(lb==l)&full].std(ddof=1) for l in (0,1,2,3)])
        for tag,wt in (("mix_full",ws_full),("mix_frozen",ws_fro)):
            m_=float((wt*mu).sum()); v_=float((wt*(sd_**2+mu**2)).sum()-m_**2); d[tag]={"mean":m_,"sharpe":float(m_/np.sqrt(v_)*np.sqrt(APY))}
        d["realised"]={"FULL":{"mean":float(g[full].mean()),"sharpe":sh(g[full])},"FROZEN":{"mean":float(g[froz].mean()),"sharpe":sh(g[froz])}}
        OUT["D_composition"][w][nm]=d
print("\n=== (D) composition (A0): cell share FULL / FROZEN, before -> after ===")
for l in ("LL","LH","HL","HH"):
    b=OUT["D_composition"]["before"]["A0"][l]; a=OUT["D_composition"]["after"]["A0"][l]
    print(f"{l} share FULL {b['share_full']:.3f}->{a['share_full']:.3f}  FROZEN {b['share_frozen']:.3f}->{a['share_frozen']:.3f}  mean {b['mean']:+.3f}->{a['mean']:+.3f}  Sh {b['sharpe']:+.2f}->{a['sharpe']:+.2f}")
for tag in ("mix_full","mix_frozen"):
    b=OUT["D_composition"]["before"]["A0"][tag]; a=OUT["D_composition"]["after"]["A0"][tag]; print(f"A0 expectation {tag}: mean {b['mean']:.3f}->{a['mean']:.3f} Sharpe {b['sharpe']:.2f}->{a['sharpe']:.2f}")

# ======== (E) ceiling.py port: ORACLE per-cell pick and walk-forward switch over the 14 forms ========
OUT["E_ceiling"]={}
for w in ("before","after"):
    FORMS={k:ARMS[w]["s42"][k][0] for k in ("A0","KFnoDL","FUND","REV","ALL3DL","ALL3","DLslot","noFTRIM","R1","R3","F1","F1R","R5","R6")}
    TS=None
    for k,r in FORMS.items():
        ts,g=gseries(r); TS=set(ts.tolist()) if TS is None else TS&set(ts.tolist())
    TS=np.array(sorted(TS)); G={}
    for k,r in FORMS.items():
        ts,g=gseries(r); ix={int(t):i for i,t in enumerate(ts)}; G[k]=np.array([g[ix[int(t)]] for t in TS])
    lb=np.array([LABS[w].get(int(t),-1) for t in TS]); mfull=TS<=T(2026,8,10,20)
    pick={}; cells={}
    for l in (-1,0,1,2,3):
        m=(lb==l)&mfull
        if m.sum()<30: continue
        best=max(FORMS,key=lambda k: G[k][m].mean()); pick[l]=best; cells[NAMES[l]]={"n":int(m.sum()),"best":best,"best_mean":float(G[best][m].mean()),"A0_mean":float(G["A0"][m].mean())}
    orc=np.array([G[pick.get(int(l),"A0")][i] for i,l in enumerate(lb)])
    MIN=200; run={k:{l:[0.0,0] for l in (-1,0,1,2,3)} for k in FORMS}; sel=[]
    for i in range(len(TS)):
        l=int(lb[i]); n=run["A0"][l][1]
        best=max(FORMS,key=lambda k: run[k][l][0]/run[k][l][1]) if n>=MIN else "A0"; sel.append(best)
        for k in FORMS: run[k][l][0]+=G[k][i]; run[k][l][1]+=1
    sel=np.array(sel); wf=np.array([G[sel[i]][i] for i in range(len(TS))]); m=mfull
    mm=m&(TS>=FROZEN[0])&(TS<FROZEN[1]); mh=m&(TS>=T(2025,1,1))
    OUT["E_ceiling"][w]={"n_common":int(len(TS)),"oracle_pick":cells,
        "ORACLE":{"mean":float(orc[m].mean()),"sharpe":sh(orc[m]),"se":float(np.sqrt(APY/m.sum()))},
        "A0":{"mean":float(G["A0"][m].mean()),"sharpe":sh(G["A0"][m])},"F1":{"mean":float(G["F1"][m].mean()),"sharpe":sh(G["F1"][m])},
        "WF":{"mean":float(wf[m].mean()),"sharpe":sh(wf[m]),"switches":int((sel[1:]!=sel[:-1]).sum()),"frozen_sharpe":sh(wf[mm]),"holdout_sharpe":sh(wf[mh]),
              "A0_frozen_sharpe":sh(G["A0"][mm]),"A0_holdout_sharpe":sh(G["A0"][mh]),"usage":{k:int((sel[m]==k).sum()) for k in FORMS if (sel[m]==k).any()}}}
    e=OUT["E_ceiling"][w]; print(f"\n=== (E) ceiling [{w}] n={e['n_common']}: ORACLE {e['ORACLE']['mean']:.3f}/Sh {e['ORACLE']['sharpe']:.2f} | A0 {e['A0']['mean']:.3f}/{e['A0']['sharpe']:.2f} | F1 {e['F1']['mean']:.3f}/{e['F1']['sharpe']:.2f} | WF {e['WF']['mean']:.3f}/{e['WF']['sharpe']:.2f} switches {e['WF']['switches']} frozen {e['WF']['frozen_sharpe']:.2f} holdout {e['WF']['holdout_sharpe']:.2f} (A0 {e['WF']['A0_holdout_sharpe']:.2f})")
    print("   picks:",{c:(v['best'],round(v['best_mean'],3)) for c,v in cells.items()})

# ======== (F) diag2 port: leg TARGET-LAYER unit-gross price return per cell (legs from archived A0; labels change) ========
lts=LEGS["PARITY_A0_dyn_s42__legs_ts"].astype(np.int64) if "PARITY_A0_dyn_s42__legs_ts" in LEGS.files else LEGS["legs_ts"].astype(np.int64)
legs={k:(LEGS["PARITY_A0_dyn_s42__legs_"+k] if "PARITY_A0_dyn_s42__legs_"+k in LEGS.files else LEGS["legs_"+k]) for k in ("king","rev24","fund")}
yr=np.array([time.gmtime(int(t)).tm_year for t in lts]); OUT["F_legs_by_cell"]={}
for w in ("before","after"):
    lb=np.array([LABS[w].get(int(t),-1) for t in lts]); d={}
    for era,msk in (("ALL",np.ones(len(lts),bool)),("2022-2023",yr<2024),("2024-2026",yr>=2024),("2024",yr==2024),("2025+",yr>=2025)):
        d[era]={}
        for l in (0,1,2,3):
            m=(lb==l)&msk
            d[era][NAMES[l]]={"n":int(m.sum()),**{k:{"mean":float(legs[k][m].mean()),"sharpe":sh(legs[k][m])} for k in legs}} if m.sum()>=30 else {"n":int(m.sum())}
    OUT["F_legs_by_cell"][w]=d
print("\n=== (F) leg layer per cell (fund / rev24 / king mean (Sharpe)), before -> after ===")
for era in ("2022-2023","2024","2025+"):
    for l in ("LL","LH","HL","HH"):
        b=OUT["F_legs_by_cell"]["before"][era][l]; a=OUT["F_legs_by_cell"]["after"][era][l]
        if "fund" in b and "fund" in a:
            print(f"{era:9s} {l} n{b['n']:4d}->{a['n']:4d} fund {b['fund']['mean']:+.3f}({b['fund']['sharpe']:+.2f})->{a['fund']['mean']:+.3f}({a['fund']['sharpe']:+.2f}) rev24 {b['rev24']['mean']:+.3f}({b['rev24']['sharpe']:+.2f})->{a['rev24']['mean']:+.3f}({a['rev24']['sharpe']:+.2f}) king {b['king']['mean']:+.3f}({b['king']['sharpe']:+.2f})->{a['king']['mean']:+.3f}({a['king']['sharpe']:+.2f})")

# ======== (G) §7 unprofitable cells: does ANY form have mean g > 0 with CI95 excluding 0, per cell (W_ALPHA, s42) ========
OUT["G_unprofitable"]={}
for w in ("before","after"):
    d={}
    for cell in ("LL","LH","HL","HH"):
        rows=[(k,v[cell]) for k,v in OUT["C_conditional"]["W_ALPHA"][w].items() if k.startswith("s42:") and "mean" in v[cell]]
        best=max(rows,key=lambda kv: kv[1]["mean"]); sig=[k for k,v in rows if v["ci_lo"]>0]
        d[cell]={"best_form":best[0],"best_mean":best[1]["mean"],"best_ci":[best[1]["ci_lo"],best[1]["ci_hi"]],"forms_with_ci_lo_gt0":sig,"n_A0":OUT["C_conditional"]["W_ALPHA"][w]["s42:A0"][cell]["n"]}
    OUT["G_unprofitable"][w]=d
    print(f"\n=== (G) [{w}] cells with no significantly profitable form (W_ALPHA, s42) ===")
    for cell,v in d.items(): print(f"  {cell} nA0={v['n_A0']:4d} best {v['best_form']:12s} {v['best_mean']:+.3f} [{v['best_ci'][0]:+.3f},{v['best_ci'][1]:+.3f}]  forms with CI95>0: {v['forms_with_ci_lo_gt0']}")

# ======== (H) regime x year composition of cells (label_and_arsenal port) ========
OUT["H_regime_years"]={}
for w in ("before","after"):
    lb=np.array([LABS[w].get(int(t),-1) for t in tsA0]); yr0=np.array([time.gmtime(int(t)).tm_year for t in tsA0])
    OUT["H_regime_years"][w]={NAMES[L]:{str(y):int(((lb==L)&(yr0==y)).sum()) for y in range(2022,2027)} for L in (-1,0,1,2,3)}
print("\n=== (H) cell x year (A0 axis) before | after ===")
for L in ("LL","LH","HL","HH"): print(f"  {L} {OUT['H_regime_years']['before'][L]} | {OUT['H_regime_years']['after'][L]}")

json.dump(OUT, open(f"{R19}/receipts/RESULT_r19_trackF_rejudge.json","w"), indent=1)
print("\nREJUDGE_DONE", time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()))
