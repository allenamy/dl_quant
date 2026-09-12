"""r14 MECHANISM FACTS — what the book actually is on the dead prefix, and the turnover-unit arithmetic.
ENV WHITELIST (E-0826-D) = EMPTY SET, asserted in-file."""
import os, sys, json, hashlib, calendar, time
_FORBID = ("LEGS","CAL","WRULE","LOOK","PHI","UMASK_NPZ","UMASK_SCOPE","FSEED","FPRED","COSTB_JSON",
           "MEMBERS_TOPN","FTRIM","SLOW_NPY","W3FIX","FEMAT_NPZ","OUT_TAG","TRADE_TOPN","TILT","TILT_TAU",
           "TILT_K","KMOD","KMOD_F10","KMOD_L","KMOD_AGREE","KTAIL","SEATF10","SEATNET","FUNDSCALE",
           "REF_SKIP","SLEEVE","CDAMP","LTRIM_TH","FTRIM_TH","RNSM","FTPOS","PANEL","PANEL_IN",
           "EXPORT_PANEL","EMA_STATE_JSON","JUDGE_HC","JUDGE_REQUIRE_W")
_v=[k for k in _FORBID if k in os.environ]; assert not _v, _v
ENV_SEEN=sorted(os.environ.keys()); ENV_WHITELIST=[]; assert ENV_WHITELIST==[]
import numpy as np
def sha(p):
    h=hashlib.sha256()
    with open(p,"rb") as f:
        for b in iter(lambda: f.read(1<<22), b""): h.update(b)
    return h.hexdigest()
def T(*a): return calendar.timegm(a+(0,)*(6-len(a)))
ROOT="/Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/uplift_2026-09-11"; OUT=ROOT+"/r14_cleanbase"
assert sha(OUT+"/PREREG_r14_clean_baseline_2026-09-12.md")=="89ba6e7d87d79866d78f7a95400ee13b21b7d0d511dfc82f6ce7b509ca956fe7"
A0P=ROOT+"/r10_screen/CMUM_CARRY/pin/A0_PWR230k_s42.npz"
R={"step":"R14_FACTS","self_sha256":sha(os.path.abspath(__file__)),"env_whitelist":ENV_WHITELIST,
   "env_seen_at_runtime":ENV_SEEN,"numpy":np.__version__,
   "inputs":{"A0_PWR230k_s42":{"path":A0P,"sha256":sha(A0P)},
             "r14_clean_series":{"path":OUT+"/series/r14_clean_series.npz","sha256":sha(OUT+"/series/r14_clean_series.npz")}},
   "utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime())}
z=np.load(A0P,allow_pickle=True); cols=[str(c) for c in z["cols"]]; ix={c:i for i,c in enumerate(cols)}
rec=np.asarray(z["rec"],float); ts_all=np.round(rec[:,ix["ts"]]).astype(np.int64)
A=np.arange(len(ts_all))[900:]; A=A[ts_all[A]<=T(2026,8,30,20)]
s=np.load(OUT+"/series/r14_clean_series.npz",allow_pickle=True); KD=s["king_dead"]; BD=s["both_dead"]; CL=s["clean"]
w3k=rec[:,ix["w3_king"]][A]; w3f=rec[:,ix["w3_fund"]][A]; w3r=rec[:,ix["w3_rev24"]][A]
gt=rec[:,ix["gross_total"]][A]; tr=rec[:,ix["turnover"]][A]
R["seat_weights"]={
 "on_KING_DEAD":{"w3_king_mean":float(w3k[KD].mean()),"w3_king_max":float(w3k[KD].max()),
                 "w3_rev24_mean":float(w3r[KD].mean()),"w3_fund_mean":float(w3f[KD].mean()),
                 "n_anchors_w3king_gt_1e-12":int((w3k[KD]>1e-12).sum())},
 "on_CLEAN":{"w3_king_mean":float(w3k[CL].mean()),"w3_rev24_mean":float(w3r[CL].mean()),
             "w3_fund_mean":float(w3f[CL].mean()),"n_anchors_w3king_eq_0":int((w3k[CL]==0.0).sum())},
 "mechanism":"LEGS=101 masks rev24 to 0 (measured: w3_rev24 == 0.0 on every W_ALPHA anchor). On the dead "
             "prefix the king leg's trailing 900-anchor returns are identically 0, so its msharpe is 0 and the "
             "seat normally hands the whole weight to fund (2148/3300 anchors, w3_king == 0). On the other "
             "1152/3300 the FUND leg's trailing msharpe is also <= 0, so w3_at falls back to [1/3,1/3,1/3], "
             "which after the LEGS=101 mask and renormalisation is [0.5, 0, 0.5] -- the seat LABELS king at "
             "0.5 while its z-vector is identically zero. Either way z = w3_fund * z_fund, a pure multiple of "
             "the fund score, and the subsequent w/=L1(w) removes the scalar: the TRADED book is the fund-only "
             "book on all 3300 dead anchors. w3_king > 0 there is a seat label, not an exposure."}
R["gross_total"]={"mean_FULL":float(gt.mean()),"mean_CLEAN":float(gt[CL].mean()),"mean_KINGDEAD":float(gt[KD].mean())}
R["turnover_unit_arithmetic"]={
 "RAW_mean_FULL":float(tr.mean()),"MATCHED_mean_FULL":float((tr/gt).mean()),
 "ratio_from_unrounded":float((tr/gt).mean()/tr.mean()),
 "ratio_quoted_in_brief":1.78189,
 "brief_ratio_uses_rounded_raw_0.03032":float((tr/gt).mean()/0.03032),
 "one_over_mean_gross_total":float(1.0/gt.mean()),
 "RAW_mean_CLEAN":float(tr[CL].mean()),"MATCHED_mean_CLEAN":float((tr/gt)[CL].mean()),
 "ratio_CLEAN":float((tr/gt)[CL].mean()/tr[CL].mean()),
 "note":"the matched value is E[t_i/g_i] (mean of per-anchor ratios), NOT E[t]/E[g]; the Jensen gap is why "
        "raw/mean_gross_total != matched"}
R["turnover_unit_arithmetic"]["raw_over_mean_gross_total"]=float(tr.mean()/gt.mean())
print(json.dumps(R["seat_weights"],indent=1)); print(json.dumps(R["gross_total"],indent=1))
print(json.dumps(R["turnover_unit_arithmetic"],indent=1))
json.dump(R,open(OUT+"/receipts/RECEIPT_r14_facts.json","w"),indent=1)
print("FACTS_DONE")
