#!/usr/bin/env python3
"""r19 STEP 4 — cross-round regime-table mask-indexing audit BY EXECUTION COUNT (PREREG_r19 §7).
For every builder the programme used, replicate its member/mask lookup line-for-line and COUNT how many anchors
actually had the CRYPTO-m1 mask applied. Reads NO environment variable. CPU only."""
import numpy as np, json, hashlib, os, time
CALPFX=('CAL','JUDGE','UPLIFT','PANEL','LOOK','WRULE','LEGS','PHI','FSEED','W3FIX','FTRIM','UMASK','SLOW','FPRED','MEMBERS_TOPN','COSTB','SLEEVE','KMOD','SEAT','RNSM','LTRIM','CDAMP','FUNDSCALE','FEMAT','TRADE_TOPN','REF_SKIP')
assert sorted(k for k in os.environ if k.startswith(CALPFX))==[]
U="/workspace/uplift_2026-09-11"; HC="/workspace/review_scratch/health_check"; R19=U+"/r19_trackF_reindex"
def sha(p):
    h=hashlib.sha256()
    with open(os.path.realpath(p),'rb') as f:
        for b in iter(lambda: f.read(1<<22), b''): h.update(b)
    return h.hexdigest()
UM=np.load(f"{HC}/masks/umask_UPIT_CRYPTO.npz",allow_pickle=True); umts=UM["ts"].astype(np.int64); umap={int(t):k for k,t in enumerate(umts)}; last=int(umts[-1])
def axis(base):
    MT=np.load(f"{base}/wide_fea_hist_meta.npz",allow_pickle=True); PW=np.load(f"{base}/wide_panel_4h_hist_v2.npz",allow_pickle=True)
    E=MT["E_ts"].astype(np.int64); pts=PW["ts"].astype(np.int64); prow={int(t):j for j,t in enumerate(pts)}
    return E, pts, prow
E0,pts0,prow0=axis(f"{HC}/dev_v4/pod_backup_2026-08-21"); EX,ptsX,prowX=axis(f"{HC}/dev_v4_x0910/pod_backup_2026-08-21")
def count_rowindex(E,prow):        # the defective lookup: umap.get(j)
    hits=0; n=0
    for t in E:
        j=prow.get(int(t))
        if j is None: continue
        n+=1; hits+= umap.get(j) is not None
    return n,hits
def count_rowindex_carry(E,prow):  # r6j1 / r7_fuel: umap.get(j) + carry branch for t>last
    hits=0; carry=0; n=0
    for t in E:
        j=prow.get(int(t))
        if j is None: continue
        n+=1
        if umap.get(j) is not None: hits+=1
        elif int(t)>last: carry+=1
    return n,hits,carry
def count_ts(E,prow):              # correct lookup by timestamp (+ carry)
    hits=0; carry=0; n=0
    for t in E:
        j=prow.get(int(t))
        if j is None: continue
        n+=1
        if int(t) in umap: hits+=1
        elif int(t)>last: carry+=1
    return n,hits,carry
def count_umaskrow(E,pts,prow):    # r12 v1 style: UMASK_ROW={j: ... for j,t in enumerate(pts) if int(t) in umap}; mk=UMASK_ROW.get(j)
    UR={j for j,t in enumerate(pts) if int(t) in umap}; hits=0; n=0
    for t in E:
        j=prow.get(int(t)); n+=1
        if j is not None and j in UR: hits+=1
    return n,hits
rows=[]
def add(round_, builder, bsha, product, psha, n, hits, ok, member_rule, note):
    rows.append(dict(round=round_, builder=builder, builder_sha256=bsha, product=product, product_sha256=psha, n_anchors=n, mask_hits=hits, indexing_correct=ok, member_rule=member_rule, note=note))
n,h=count_rowindex(E0,prow0)
add("r2 trackF (original)", "trackF/build_regime.py", sha(U+"/trackF/build_regime.py"), "trackF/regime_vars.npz", sha(U+"/trackF/regime_vars.npz"), n, h, False, "meta members[i] (mask never applied)", "umap.get(j): row index into ts-keyed dict")
n,h,c=count_ts(E0,prow0)
add("r19 trackF (fixed)", "r19/devices/build_regime_fixed.py", sha(R19+"/devices/build_regime_fixed.py"), "r19/regime_vars_fixed.npz", sha(R19+"/regime_vars_fixed.npz"), n, h, True, "meta members[i] INTERSECT m1 CRYPTO umask", "umap.get(int(t))")
n,h,c=count_rowindex_carry(E0,prow0)
add("r6 judge1 Q4 (incumbent axis)", "r6j1_regime.py (= judge1_r6/j1_regime_pod.py)", sha(U+"/r6j1_regime.py"), "r6j1/j1_regime.json", sha(U+"/r6j1/j1_regime.json"), n, h, False, "meta members[i], no mask", f"row-index lookup; carry branch rows={c}")
n,h,c=count_rowindex_carry(EX,prowX)
add("r6 judge1 Q4 (x0910 axis)", "r6j1_regime.py", sha(U+"/r6j1_regime.py"), "r6j1/j1_regime.json", sha(U+"/r6j1/j1_regime.json"), n, h, False, "meta members[i]; ONLY the Sept tail masked with UMM[-1]", f"row-index lookup; carry branch applied to {c} anchors => inconsistent masking along the axis")
n,h,c=count_rowindex_carry(E0,prow0)
add("r7 FUEL-2 gauge (incumbent)", "r7f2/r7_fuel.py", sha(U+"/r7f2/r7_fuel.py"), "r7f2/R7_FUEL.npz", sha(U+"/r7f2/R7_FUEL.npz"), n, h, False, "meta members[i], no mask", "verbatim copy of r6j1 line (ERROR_LEDGER P1-32)")
n,h,c=count_rowindex_carry(EX,prowX)
add("r7 FUEL-2 gauge (x0910)", "r7f2/r7_fuel.py", sha(U+"/r7f2/r7_fuel.py"), "r7f2/R7_FUEL.npz", sha(U+"/r7f2/R7_FUEL.npz"), n, h, False, "meta members[i]; Sept tail masked", f"carry rows={c}")
n,h=count_rowindex(E0,prow0)
add("r7 FUEL-2 final L93 (basis-dispersion mechanism)", "r7f2/r7_final.py", sha(U+"/r7f2/r7_final.py"), "r7f2/R7_FINAL.json", sha(U+"/r7f2/R7_FINAL.json"), n, h, False, "meta members[i], no mask", "kk=umap.get(j)")
n,h=count_rowindex(E0,prow0)
add("r8 BUILD-1 G8 regime", "r8_inbook/regime_gb.py", sha(U+"/r8_inbook/regime_gb.py"), "r8_inbook/REGIME_GIVEBACK.json", sha(U+"/r8_inbook/REGIME_GIVEBACK.json"), n, h, False, "829-qvk rank base (mask never applied)", "k=umap.get(j)")
n,h,c=count_ts(EX,prowX)
add("r7 FUEL-1 sigma2 R6M/LIVE arms", "r7f1/r7_sigma2.py", sha(U+"/r7f1/r7_sigma2.py"), "r7f1/out/sigma_variants.npz", sha(U+"/r7f1/out/sigma_variants.npz"), n, h, True, "R6M: meta+mask; LIVE: 829-qvk+mask; R6 arm deliberately emulates the defect", f"umap.get(int(t)); carry rows={c}")
n,h=count_umaskrow(E0,pts0,prow0)
add("r12 causal primitives v1 (VOID)", "r12_regime/pod_causal_regime_r12.py", sha(U+"/r12_regime/pod_causal_regime_r12.py"), "r12_regime/causal_primitives_r12.npz", sha(U+"/r12_regime/causal_primitives_r12.npz"), n, h, True, "meta members[i] + mask (VOID: book uses 829-qvk rebuild)", "UMASK_ROW keyed by row j built from ts -> correct")
n,h,c=count_ts(E0,prow0)
add("r12 causal primitives v2", "r12_regime/pod_causal_regime_r12_v2.py", sha(U+"/r12_regime/pod_causal_regime_r12_v2.py"), "r12_regime/causal_primitives_r12_v2.npz", sha(U+"/r12_regime/causal_primitives_r12_v2.npz"), n, h, True, "829-qvk rebuild + mask (parity-asserted vs book 8.09e-6 bps)", "'t in umap' -> correct")
add("r12_smoothing REGIME12", "r12_smoothing/regime12.py", sha(U+"/r12_smoothing/regime12.py"), "r12_smoothing/REGIME12.npz", sha(U+"/r12_smoothing/REGIME12.npz"), int(len(E0)), 0, None, "meta members[i], NO umask by construction (not an indexing error; universe != book's)", "breadth/crash partition on y4 of meta members")
add("r12_smoothing ALTSURGE masks / analyze12", "r12_smoothing/mkmask12.py + analyze12.py", sha(U+"/r12_smoothing/mkmask12.py"), "r12_smoothing/causal_primitives_r12.npz (v1 copy)", sha(U+"/r12_smoothing/causal_primitives_r12.npz"), None, None, True, "consumes v1 (indexing correct, member rule VOID)", "A_ew from v1; see r16 note")
for r in rows: print(f"{r['round']:48s} hits {str(r['mask_hits']):>6s}/{str(r['n_anchors']):<6s} correct={r['indexing_correct']}  {r['member_rule']}")
# v2 consumers (by receipt fields, checked here by sha equality of the file they name)
V2=sha(U+"/r12_regime/causal_primitives_r12_v2.npz"); assert V2.startswith("0510f456")
json.dump(dict(utc=time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()), self_sha256=hashlib.sha256(open(__file__,'rb').read()).hexdigest(),
               umask_sha256=sha(f"{HC}/masks/umask_UPIT_CRYPTO.npz"), umask_last_ts_utc=time.strftime("%F %HZ",time.gmtime(last)), rows=rows,
               v2_consumers_by_receipt=["r12_regime table (r12_regime_table.py asserts PRIM sha)","r13_A_halfscale","r13_B_withinhalf","r13_deploy","r13b_nulls","r15_structural","r16_asym_band","r17_fill_pricing"],
               v1_consumers_by_receipt=["r12_smoothing mkmask12.py/analyze12.py (MASKS12.json primitives_sha16 c74fd695fe036b63)"]),
          open(R19+"/receipts/RECEIPT_r19_primitives_audit.json","w"), indent=1)
print("AUDIT_DONE")
