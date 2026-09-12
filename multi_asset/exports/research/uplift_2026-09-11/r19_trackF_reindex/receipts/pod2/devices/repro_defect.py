#!/usr/bin/env python3
"""r19 STEP 1 — reproduce the trackF mask-index defect and its correction (PREREG_r19 §0/§1/§5).
(a) run the ORIGINAL build_regime.py body verbatim, instrumented to count mask hits; assert the
    archived regime_vars.npz (sha 27e604f7...) is reproduced bitwise and hits == 0;
(b) run the same body with the single-line fix  k = umap.get(j)  ->  k = umap.get(int(t)); count hits;
(c) per-field change statistics; (d) labels (label_and_arsenal.py function verbatim) before/after,
    change count and transition matrix; (e) archive equivalence local labels.npz == pod2 regime_labels.npz;
(f) cross-instrument: corrected sig_fund vs r7f1 R6M_sig; (g) generate build_regime_fixed.py by exact
    string replacement (2 hunks: the index, the output path), save the unified diff, RUN it and assert its
    output equals (b) bitwise.  Reads NO environment variable; caliber flags must be absent. CPU only."""
import numpy as np, json, hashlib, os, sys, time, difflib, subprocess
CALPFX=('CAL','JUDGE','UPLIFT','PANEL','LOOK','WRULE','LEGS','PHI','FSEED','W3FIX','FTRIM','UMASK','SLOW','FPRED','MEMBERS_TOPN','COSTB','SLEEVE','KMOD','SEAT','RNSM','LTRIM','CDAMP','FUNDSCALE','FEMAT','TRADE_TOPN','REF_SKIP')
CALFLAGS=sorted(k for k in os.environ if k.startswith(CALPFX)); assert CALFLAGS==[], ('caliber env flags present', CALFLAGS)
ENV_WL=[]; assert all(k not in os.environ for k in ENV_WL)
R19="/workspace/uplift_2026-09-11/r19_trackF_reindex"; TF="/workspace/uplift_2026-09-11/trackF"
B="/workspace/review_scratch/health_check/dev_v4/pod_backup_2026-08-21"
UMP="/workspace/review_scratch/health_check/masks/umask_UPIT_CRYPTO.npz"
def sha(p):
    h=hashlib.sha256()
    with open(os.path.realpath(p),'rb') as f:
        for b in iter(lambda: f.read(1<<22), b''): h.update(b)
    return h.hexdigest()
EXPECT={f"{B}/wide_fea_hist_meta.npz":"0e3c09ac86c727ac1a7893889918e3b367463fd059a154f5e320eed47f5725c3",
        f"{B}/wide_panel_4h_hist_v2.npz":"5e67c0559daa904d8f0526b6e268e93dcb45aab89d82646cf79a794445481116",
        UMP:"47d87b5165b695a7d9b340134a189dd6a2165c837bab35808b699ffac3f7f1b5",
        f"{TF}/build_regime.py":"db80e66fb0620333b0b224a14b2184e27be345027941092078abf56fba9299b4",
        f"{TF}/regime_vars.npz":"27e604f7444d02f6e6caf7b5fcd1ec5f178f1d2438219976ce6b053e72a801c4",
        f"{TF}/label_and_arsenal.py":"75daa23803539c5bbbfd12647e2d909388414f9d4078613fa60c6129188917f0",
        f"{TF}/regime_labels.npz":"18ee9e1ae6fd2f74577c6a871851cc543d399fe36f3e8c7d815546804152482b",
        f"{R19}/labels_local_copy.npz":"8184d6f1137d6ba7a0870aefe2b2174684cf96bd90fd79c46685d17bf2f01f2e"}
INSHA={p: sha(p) for p in EXPECT}
for p,s in EXPECT.items(): assert INSHA[p]==s, (p, INSHA[p], s)
print("input shas OK (8/8)", flush=True)

# ---------------- the builder body, verbatim from build_regime.py, with `fix` switching L29 only ----------------
MT=np.load(f"{B}/wide_fea_hist_meta.npz", allow_pickle=True)
E_ts=MT["E_ts"].astype(np.int64); members=MT["members"]
PW=np.load(f"{B}/wide_panel_4h_hist_v2.npz", allow_pickle=True)
pw_row={int(t): j for j,t in enumerate(PW["ts"].astype(np.int64))}
SYM=[str(s) for s in PW["symbols"]]
UM=np.load(UMP, allow_pickle=True)
assert [str(x) for x in UM["symbols"]]==SYM, "umask symbols mismatch"
umap={int(t): k for k,t in enumerate(UM["ts"].astype(np.int64))}
UMM=np.asarray(UM["mask"])
FN=PW["f_fund_now"]; IV=PW["f_fund_iv"]; R24=PW["f_rev_24h"]
V7=PW["f_vol_7d"]; M7=PW["f_mom_7d"]; RG=PW["f_range_24h"]
_IVf=np.where(np.isfinite(IV)&(IV>0), IV, 8.0)
RN8=FN*(8.0/_IVf)
ibtc=SYM.index("BTCUSDT")
COLS=["ts","nmem","sig_fund","fund_mean","fund_med","frac_neg","disp24","mean24",
      "breadth_up","vol7_med","absmom7_med","range24_med","btc_r24","btc_m7","btc_v7","young30"]
def build(fix):
    rows=[]; first_seen={}; hits=0; n_anchor_with_panel_row=0
    for i,t in enumerate(E_ts):
        j=pw_row.get(int(t))
        if j is None: continue
        n_anchor_with_panel_row+=1
        m=members[i]
        k=umap.get(int(t)) if fix else umap.get(j)          # <-- the only difference between the two runs
        if k is not None: m=m[UMM[k][m]]; hits+=1
        if len(m)<50: continue
        for s in m:
            if s not in first_seen: first_seen[s]=t
        young=float(np.mean([(t-first_seen[s])<30*86400 for s in m]))
        f=RN8[j,m]; f=f[np.isfinite(f)]
        r=R24[j,m]; r=r[np.isfinite(r)]
        v=V7[j,m]; v=v[np.isfinite(v)]
        mm=M7[j,m]; mm=mm[np.isfinite(mm)]
        rg=RG[j,m]; rg=rg[np.isfinite(rg)]
        nn=lambda a,fn: (float(fn(a)) if len(a)>50 else np.nan)
        rows.append((int(t), len(m),
                     nn(f, lambda a: 1e4*np.std(a)), nn(f, lambda a: 1e4*np.mean(a)),
                     nn(f, lambda a: 1e4*np.median(a)), nn(f, lambda a: np.mean(a<0)),
                     nn(r, np.std), nn(r, np.mean), nn(r, lambda a: np.mean(a>0)),
                     nn(v, np.median), nn(mm, lambda a: np.median(np.abs(a))), nn(rg, np.median),
                     float(R24[j,ibtc]), float(M7[j,ibtc]), float(V7[j,ibtc]), young))
    return np.array(rows, dtype=np.float64), hits, n_anchor_with_panel_row

t0=time.time()
A_orig, hits_orig, npr = build(fix=False)
A_fix,  hits_fix,  _   = build(fix=True)
print(f"built both in {time.time()-t0:.1f}s; anchors with panel row {npr}; rows orig {len(A_orig)} fix {len(A_fix)}", flush=True)
Z=np.load(f"{TF}/regime_vars.npz", allow_pickle=True)
arch_cols=[str(c) for c in Z["cols"]]; arch_V=Z["V"]
bitwise=bool(arch_cols==COLS and arch_V.shape==A_orig.shape and np.array_equal(arch_V, A_orig, equal_nan=True))
print(f"ARCHIVE REPRODUCED BITWISE BY ORIGINAL CODE: {bitwise}   original_mask_hits={hits_orig}   corrected_mask_hits={hits_fix}", flush=True)
assert bitwise, "STOP: archived table not reproduced by the original code"
assert hits_orig==0, ("STOP: original code applied the mask on", hits_orig)
assert hits_fix==10039, ("STOP: corrected hits != 10039", hits_fix)
assert np.array_equal(A_orig[:,0], A_fix[:,0]), "row axis differs between original and corrected"

# ---------------- per-field change statistics ----------------
fields={}
for c in range(1,len(COLS)):
    a=A_orig[:,c]; b=A_fix[:,c]; both=np.isfinite(a)&np.isfinite(b)
    changed=int(np.sum(~((a==b)|(np.isnan(a)&np.isnan(b)))))
    corr=float(np.corrcoef(a[both],b[both])[0,1]) if both.sum()>2 and np.std(a[both])>0 and np.std(b[both])>0 else float('nan')
    fields[COLS[c]]={"n":int(len(a)),"changed":changed,"maxabs":float(np.max(np.abs(a[both]-b[both]))) if both.any() else 0.0,
                     "mean_original":float(np.nanmean(a)),"mean_corrected":float(np.nanmean(b)),"correlation":corr,
                     "n_finite_original":int(np.isfinite(a).sum()),"n_finite_corrected":int(np.isfinite(b).sum())}
print(f"{'field':12s}{'changed':>8s}{'maxabs':>12s}{'mean_orig':>12s}{'mean_corr':>12s}{'corr':>8s}")
for k,v in fields.items(): print(f"{k:12s}{v['changed']:8d}{v['maxabs']:12.5g}{v['mean_original']:12.5g}{v['mean_corrected']:12.5g}{v['correlation']:8.4f}")

# ---------------- labels: function verbatim from label_and_arsenal.py ----------------
BURN=2190
def expanding_median_label(x):
    lab=np.full(len(x), -1, np.int8)
    for i in range(len(x)):
        if i<BURN: continue
        past=x[:i]; past=past[np.isfinite(past)]
        if len(past)<BURN//2 or not np.isfinite(x[i]): continue
        lab[i]=1 if x[i]>np.median(past) else 0
    return lab
K={c:i for i,c in enumerate(COLS)}
def labels(A):
    LF=expanding_median_label(A[:,K["sig_fund"]]); LD=expanding_median_label(A[:,K["disp24"]])
    LAB=np.full(len(A), -1, np.int8); ok=(LF>=0)&(LD>=0); LAB[ok]=LF[ok]*2+LD[ok]
    return LAB, LF, LD
LAB_o, LF_o, LD_o = labels(A_orig); LAB_f, LF_f, LD_f = labels(A_fix)
ts_r=A_orig[:,0].astype(np.int64)
# archive equivalence: pod2 regime_labels.npz and the local labels.npz (loc_arsenal.py) must both equal the original labels
PL=np.load(f"{TF}/regime_labels.npz"); LL=np.load(f"{R19}/labels_local_copy.npz")
eq_pod=bool(np.array_equal(PL["ts"].astype(np.int64),ts_r) and np.array_equal(PL["lab"],LAB_o) and np.array_equal(PL["lf"],LF_o) and np.array_equal(PL["ld"],LD_o))
eq_loc=bool(np.array_equal(LL["ts"].astype(np.int64),ts_r) and np.array_equal(LL["lab"],LAB_o) and np.array_equal(LL["lf"],LF_o) and np.array_equal(LL["ld"],LD_o))
print(f"pod2 regime_labels.npz == original labels: {eq_pod};  local labels.npz == original labels: {eq_loc}", flush=True)
assert eq_pod and eq_loc
labeled_o=int((LAB_o>=0).sum()); labeled_f=int((LAB_f>=0).sum())
changed_both=int(((LAB_o!=LAB_f)&(LAB_o>=0)&(LAB_f>=0)).sum()); changed_any=int((LAB_o!=LAB_f).sum())
NAMES={-1:"WARM",0:"LL",1:"LH",2:"HL",3:"HH"}
trans={NAMES[a]:{NAMES[b]:int(((LAB_o==a)&(LAB_f==b)).sum()) for b in (-1,0,1,2,3)} for a in (-1,0,1,2,3)}
print(f"LABEL CHANGES: changed(both labeled)={changed_both} / labeled_original={labeled_o} (labeled_corrected={labeled_f}, changed_any={changed_any})")
print("transition matrix (rows = original, cols = corrected):"); print(f"{'':6s}"+"".join(f"{NAMES[b]:>7s}" for b in (-1,0,1,2,3)))
for a in (-1,0,1,2,3): print(f"{NAMES[a]:6s}"+"".join(f"{trans[NAMES[a]][NAMES[b]]:7d}" for b in (-1,0,1,2,3)))
cells_o={NAMES[c]:int((LAB_o==c).sum()) for c in (-1,0,1,2,3)}; cells_f={NAMES[c]:int((LAB_f==c).sum()) for c in (-1,0,1,2,3)}
print("cell sizes original ",cells_o); print("cell sizes corrected",cells_f)
# component-wise: how many flips come from sig_fund vs disp24
print(f"lf changed {int((LF_o!=LF_f).sum())}  ld changed {int((LD_o!=LD_f).sum())}")

# ---------------- cross-instrument: r7f1 R6M_sig (meta members + m1 umask, ddof=0, x0910 axis) ----------------
xi={}
try:
    SV=np.load("/workspace/uplift_2026-09-11/r7f1/out/sigma_variants.npz", allow_pickle=True)
    sc=[str(c) for c in SV["cols"]]; rec=SV["rec"]; sts=rec[:,0].astype(np.int64)
    r6m={int(t):rec[i,sc.index("R6M_sig")] for i,t in enumerate(sts)}
    r6 ={int(t):rec[i,sc.index("R6_sig")]  for i,t in enumerate(sts)}
    com=[i for i,t in enumerate(ts_r) if int(t) in r6m]
    a=A_fix[com,K["sig_fund"]]; b=np.array([r6m[int(ts_r[i])] for i in com])
    a0=A_orig[com,K["sig_fund"]]; b0=np.array([r6[int(ts_r[i])] for i in com])
    fin=np.isfinite(a)&np.isfinite(b); fin0=np.isfinite(a0)&np.isfinite(b0)
    xi={"n_common":len(com),"corrected_vs_R6M_maxabs":float(np.max(np.abs(a[fin]-b[fin]))),"corrected_vs_R6M_n_exact":int(np.sum(a[fin]==b[fin])),
        "original_vs_R6_maxabs":float(np.max(np.abs(a0[fin0]-b0[fin0]))),"original_vs_R6_n_exact":int(np.sum(a0[fin0]==b0[fin0])),
        "sigma_variants_sha256":sha("/workspace/uplift_2026-09-11/r7f1/out/sigma_variants.npz")}
    print("CROSS-INSTRUMENT r7f1:",json.dumps(xi))
except Exception as e:
    xi={"error":repr(e)}; print("cross-instrument unavailable:",e)

# ---------------- generate build_regime_fixed.py (2 hunks), save diff, RUN it, assert equality with A_fix ----------------
src=open(f"{TF}/build_regime.py").read(); s=src
old1='    k = umap.get(j)\n'; new1='    k = umap.get(int(t))\n'
old2='np.savez_compressed("/workspace/uplift_2026-09-11/trackF/regime_vars.npz", cols=np.array(COLS), V=A)'
new2='np.savez_compressed("/workspace/uplift_2026-09-11/r19_trackF_reindex/regime_vars_fixed.npz", cols=np.array(COLS), V=A)'
assert s.count(old1)==1 and s.count(old2)==1
s=s.replace(old1,new1).replace(old2,new2)
s=s.replace('"""Track F step 1:', '"""[r19 FIXED COPY of trackF/build_regime.py sha db80e66f...: L29 index fix + output path; see build_regime_fixed.diff]\nTrack F step 1:',1)
FIX=f"{R19}/devices/build_regime_fixed.py"; open(FIX,"w").write(s)
diff="".join(difflib.unified_diff(src.splitlines(True), s.splitlines(True), fromfile="trackF/build_regime.py", tofile="r19_trackF_reindex/devices/build_regime_fixed.py"))
open(f"{R19}/devices/build_regime_fixed.diff","w").write(diff); print(diff)
rc=subprocess.run([sys.executable, FIX], capture_output=True, text=True); print(rc.stdout[-1500:]); assert rc.returncode==0, rc.stderr[-2000:]
ZF=np.load(f"{R19}/regime_vars_fixed.npz", allow_pickle=True)
eq_script=bool([str(c) for c in ZF["cols"]]==COLS and np.array_equal(ZF["V"], A_fix, equal_nan=True))
print("build_regime_fixed.py output == in-process corrected table (bitwise):", eq_script); assert eq_script
np.savez_compressed(f"{R19}/regime_labels_fixed.npz", ts=ts_r, lab=LAB_f, lf=LF_f, ld=LD_f)
np.savez_compressed(f"{R19}/receipts/regime_labels_original_recomputed.npz", ts=ts_r, lab=LAB_o, lf=LF_o, ld=LD_o)
rcp=dict(utc=time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()), self_sha256=hashlib.sha256(open(__file__,'rb').read()).hexdigest(),
         env_whitelist=ENV_WL, caliber_env_flags=CALFLAGS, python=sys.version.split()[0], numpy=np.__version__,
         input_sha256=INSHA, archive_reproduced_bitwise=bitwise, original_mask_hits=hits_orig, corrected_mask_hits=hits_fix,
         n_anchors_with_panel_row=npr, n_rows=int(len(A_orig)), fields=fields,
         labels=dict(labeled_original=labeled_o, labeled_corrected=labeled_f, changed_both_labeled=changed_both, changed_any=changed_any,
                     lf_changed=int((LF_o!=LF_f).sum()), ld_changed=int((LD_o!=LD_f).sum()), cells_original=cells_o, cells_corrected=cells_f, transition=trans),
         archive_equivalence=dict(pod2_regime_labels_eq=eq_pod, local_labels_npz_eq=eq_loc), cross_instrument_r7f1=xi,
         fixed_script_sha256=sha(FIX), fixed_script_output_eq=eq_script, diff_sha256=sha(f"{R19}/devices/build_regime_fixed.diff"),
         regime_vars_fixed_sha256=sha(f"{R19}/regime_vars_fixed.npz"), regime_labels_fixed_sha256=sha(f"{R19}/regime_labels_fixed.npz"))
json.dump(rcp, open(f"{R19}/receipts/RECEIPT_r19_repro.json","w"), indent=1)
print("REPRO_DONE")
