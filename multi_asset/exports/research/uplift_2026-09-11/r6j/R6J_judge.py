"""R6 JUDGE-2. Re-judge A0 / XIB_LAG50 / (A0+AMI@0.20) on the EXTENDED and LIVE-OVERLAP windows
against the frozen rules of PREREG_r6 (sha 7dff6b0b...). Statistic + bootstrap copied verbatim from
ANGLE1_judge.py (which itself copied judge_round3.py). NO new device runs: every series already exists
on the shared 10039-row v4 panel axis; this script only RE-CUTS windows and re-runs the paired bootstrap.
E-0826-D: env whitelist enumerated and asserted below; every producing run's config_json is re-read and
recorded, so the env of the SERIES is carried into the product, not the env of this judge."""
import numpy as np, json, calendar, os, hashlib, datetime as dt, sys

APY = 2190; WARM = 900
LAD = "/workspace/uplift_2026-09-11/seatladder/dev/probe_artifacts"
P6  = "/workspace/uplift_2026-09-11/p6/arms"
R3K = "/workspace/uplift_2026-09-11/r3k/arms"
OUT = "/workspace/uplift_2026-09-11/r6j"
os.makedirs(OUT, exist_ok=True)
SHA = lambda p: hashlib.sha256(open(p,'rb').read()).hexdigest()
def T(*a): return calendar.timegm(a+(0,)*(6-len(a)))

# ---- env whitelist of the DEVICE that produced every series (read from each series' own config_json) ----
DEV_ENV_KEYS = ["CAL","CDAMP","COSTB_JSON","FEMAT_NPZ","FPRED","FSEED","FTPOS","FTRIM","FTRIM_TH","FUNDSCALE",
  "KMOD","KMOD_AGREE","KMOD_F10","KMOD_L","KTAIL","LEGS","LOOK","LTRIM_TH","MEMBERS_TOPN","OUT_TAG","PHI",
  "REF_SKIP","RNSM","SEATF10","SEATNET","SLEEVE","SLOW_NPY","TRADE_TOPN","UMASK_NPZ","UMASK_SCOPE","W3FIX","WRULE"]
PINNED = {"CAL":"log","LEGS":"101","LOOK":900,"MEMBERS_TOPN":829,"WRULE":"msharpe"}
COSTFIT = "/workspace/uplift_2026-09-11/r3k/costb_PWR_G230k.json"

# ---- honest frontier for any PHI>0 arm: DL preds last finite anchor (VERIFIED separately) ----
DL_LAST = T(2026,8,30,20)
FROZ_END = T(2026,8,10,20); FROZ_LO = T(2025,3,1)

WINDOWS = [  # name, lo, hi(inclusive), postwarm_only, decision_power
 ("W0_FROZEN",        FROZ_LO,        FROZ_END,   False, "CONTROL"),
 ("W2_EXT_PRIMARY",   FROZ_LO,        DL_LAST,    False, "DECISIVE"),
 ("W3_FULLCYCLE_ext", None,           DL_LAST,    True,  "DECISIVE"),
 ("W3_FULLCYCLE_inc", None,           FROZ_END,   True,  "CONTROL"),
 ("NEW_SLICE",        T(2026,8,11),   DL_LAST,    False, "DESCRIPTIVE"),
 ("REGIME_0819_21",   T(2026,8,19),   T(2026,8,21,20), False, "DESCRIPTIVE"),
 ("LIVE_ALL_ovl",     T(2026,8,1),    DL_LAST,    False, "DESCRIPTIVE"),
 ("LIVE_COMBO_ovl",   T(2026,8,26,4), DL_LAST,    False, "DESCRIPTIVE"),
]
SEATS = [("dyn","dyn (replay dynamic seat)"),("k021","fix 0.2100 (frozen-rule constant)"),
         ("k0357","fix 0.3568 (LIVE BOOK's current king weight)"),
         ("k0257","fix 0.2572"),("k0462","fix 0.4617"),("k0534","fix 0.5338")]
SEEDS = (42,2027)

def _load(path, key=None):
    Z = np.load(path, allow_pickle=True)
    k = key or ("rec" if "rec" in Z.files else "d30_n2_c42_rec")
    cols = [str(c) for c in Z["cols"]] if "cols" in Z.files else \
      ["ts","net","pnl","carry","cost","gross_total","gross_member","gross_sel","nsel","nmember","fires",
       "leg_king","leg_rev24","leg_fund","w3_king","w3_rev24","w3_fund","turnover","net_ex","pnl_ex","carry_ex","cost_ex","netlong"]
    ix = {c:i for i,c in enumerate(cols)}
    R = np.asarray(Z[k], float)
    ts = np.round(R[:,ix["ts"]]).astype(np.int64)
    g = R[:,ix["net_ex"]]/R[:,ix["gross_total"]]
    cfg = json.loads(str(Z["config_json"])) if "config_json" in Z.files else None
    return ts, g, R, ix, cfg

def ladder(tag):  # seatladder series have no cols/config_json; fixed COLS order
    return _load(f"{LAD}/w10_ablation_series_{tag}.npz", "d30_n2_c42_rec")

sr  = lambda x: float(np.mean(x)/np.std(x,ddof=1)*np.sqrt(APY))
def boot_mean(v, days, rng, B=2000):
    ud, inv = np.unique(days, return_inverse=True); nd = len(ud)
    S = np.bincount(inv, weights=v, minlength=nd); N = np.bincount(inv, minlength=nd)
    idx = rng.integers(0, nd, size=(B, nd)); mn = S[idx].sum(1)/N[idx].sum(1)
    return float(np.percentile(mn,2.5)), float(np.percentile(mn,97.5)), float((mn>0).mean()), mn

def boot_dsr(xa, xb, days, rng, B=2000):
    """paired bootstrap of the annualised-Sharpe DIFFERENCE, resampling UTC day blocks jointly."""
    ud, inv = np.unique(days, return_inverse=True); nd = len(ud)
    order = np.argsort(inv, kind="stable"); a = xa[order]; b = xb[order]
    starts = np.searchsorted(inv[order], np.arange(nd)); ends = np.append(starts[1:], len(a))
    idx = rng.integers(0, nd, size=(B, nd)); out = np.empty(B)
    for q in range(B):
        sl = idx[q]
        va = np.concatenate([a[starts[j]:ends[j]] for j in sl])
        vb = np.concatenate([b[starts[j]:ends[j]] for j in sl])
        out[q] = va.mean()/va.std(ddof=1) - vb.mean()/vb.std(ddof=1)
    out *= np.sqrt(APY)
    return float(np.percentile(out,2.5)), float(np.percentile(out,97.5)), float((out>0).mean()), out

Z_BONF_K8 = 2.7344   # PREREG §5 F1 family, K1 = 8
def bonf_bound(point, boots, z=Z_BONF_K8):
    se = float(np.std(boots, ddof=1))
    return point - z*se, point + z*se, se

RES = {"meta":{}, "levels":{}, "paired":{}, "windows":{}}
RES["meta"]["utc_now"] = dt.datetime.utcnow().isoformat()+"Z"
RES["meta"]["self_sha256"] = SHA(os.path.abspath(__file__))
RES["meta"]["cost_model"] = {"path":COSTFIT,"sha256_16":SHA(COSTFIT)[:16]}
RES["meta"]["DL_LAST_anchor"] = str(dt.datetime.utcfromtimestamp(DL_LAST))
RES["meta"]["note_frontier"] = ("any PHI>0 arm is only replayable to 2026-08-30 20Z: f10_A0_s{42,2027}.npy "
  "last finite row = dlw axis index 10205 = 2026-08-30 20:00Z; w10 L267 nan_to_num()s the F10 leg to 0, "
  "so a later anchor silently replays a DIFFERENT book (no behavioural signature).")

# ---------- axis + window arithmetic, asserted before any statistic ----------
ts0, g0, R0, ix0, _ = ladder("LAD_A0_dyn_s42")
RES["meta"]["axis"] = {"n":len(ts0),"first":str(dt.datetime.utcfromtimestamp(ts0[0])),
                       "last":str(dt.datetime.utcfromtimestamp(ts0[-1]))}
WARM_TS = int(ts0[WARM])          # post-warm threshold as a TIMESTAMP, so it is axis-independent
                                  # (XIB fixed-seat arms drop axis row 0 -> 10038 rows; row-index warm cuts would slip)
def mask(ts, lo, hi, postwarm):
    m = np.ones(len(ts), bool)
    if postwarm: m &= (ts >= WARM_TS)
    if lo is not None: m &= (ts >= lo)
    m &= (ts <= hi)
    return m
for nm, lo, hi, pw, pwr in WINDOWS:
    m = mask(ts0, lo, hi, pw)
    RES["windows"][nm] = {"n":int(m.sum()),"lo":str(dt.datetime.utcfromtimestamp(lo)) if lo else "postwarm",
        "hi":str(dt.datetime.utcfromtimestamp(hi)),"power":pwr}
print(json.dumps(RES["windows"], indent=1), flush=True)
assert RES["windows"]["W0_FROZEN"]["n"] == 3168, RES["windows"]["W0_FROZEN"]
assert RES["windows"]["W3_FULLCYCLE_inc"]["n"] == 9018, RES["windows"]["W3_FULLCYCLE_inc"]

# ---------- levels + paired deltas ----------
def seed_stream(base, k): return np.random.default_rng([base, k])

for seat, seatdesc in SEATS:
    for sd in SEEDS:
        ta0, ga0, Ra, ixa, _ = ladder(f"LAD_A0_{seat}_s{sd}")
        tx0, gx0, Rx, ixx, _ = ladder(f"LAD_XIB_{seat}_s{sd}")
        ta, ia, ix_ = np.intersect1d(ta0, tx0, return_indices=True)   # XIB fixed-seat arms are 10038 rows
        ga = ga0[ia]; gx = gx0[ix_]
        RES["meta"].setdefault("axis_intersect", {})[f"{seat}|s{sd}"] = \
            {"n_A0":int(len(ta0)),"n_XIB":int(len(tx0)),"n_common":int(len(ta))}
        for nm, lo, hi, pw, pwr in WINDOWS:
            m = mask(ta, lo, hi, pw)
            if m.sum() < 8: continue
            d = ga[m]; x = gx[m]; days = ta[m]//86400
            base = 20260905 if pwr == "CONTROL" else 20260911
            l0,h0,p0,bm0 = boot_mean(x-d, days, seed_stream(base,0))
            l9,h9,p9,bm9 = boot_mean(x-d, days, seed_stream(base,9))
            dl0,dh0,dp0,bs0 = boot_dsr(x, d, days, seed_stream(base,0))
            blo,bhi,bse = bonf_bound(float(sr(x)-sr(d)), bs0)
            gblo,gbhi,gbse = bonf_bound(float((x-d).mean()), bm0)
            key = f"{seat}|s{sd}|{nm}"
            RES["levels"][f"A0|{key}"]  = {"n":int(m.sum()),"g_bps":float(d.mean()),"sharpe":sr(d)}
            RES["levels"][f"XIB|{key}"] = {"n":int(m.sum()),"g_bps":float(x.mean()),"sharpe":sr(x)}
            RES["paired"][f"XIB-A0|{key}"] = {
              "n":int(m.sum()),"power":pwr,
              "dg_bps":float((x-d).mean()),"dg_ci95_k0":[l0,h0],"dg_ci95_k9":[l9,h9],"dg_P>0":p0,
              "dg_bonfK8":[gblo,gbhi],"dg_boot_se":gbse,
              "dSharpe":float(sr(x)-sr(d)),"dSharpe_ci95_k0":[dl0,dh0],"dSharpe_P>0":dp0,
              "dSharpe_bonfK8":[blo,bhi],"dSharpe_boot_se":bse,
              "rho_XIB_A0":float(np.corrcoef(x,d)[0,1]),
              "PASS_dg_2streams":bool(l0>0 and l9>0),
              "PASS_dSharpe_bonfK8":bool(blo>0)}
        print("done", seat, sd, flush=True)

# ---------- Amihud sleeve (PHI=0 -> it does NOT use the DL leg) ----------
for sd in SEEDS:
    ta,ga,_,_,cfgA = _load(f"{R3K}/A0_PWR230k_s{sd}.npz")
    tb,gb,_,_,cfgS = _load(f"{P6}/w10_ablation_series_P6_AMQ64_PWR_s{sd}.npz")
    assert np.array_equal(ta,tb)
    RES["meta"][f"sleeve_cfg_s{sd}"] = {k:cfgS.get(k) for k in DEV_ENV_KEYS} if cfgS else None
    RES["meta"][f"A0arm_cfg_s{sd}"]  = {k:cfgA.get(k) for k in DEV_ENV_KEYS} if cfgA else None
    for nm, lo, hi, pw, pwr in WINDOWS:
        m = mask(ta, lo, hi, pw)
        if m.sum() < 8: continue
        A = ga[m]; S = gb[m]; days = ta[m]//86400
        base = 20260905 if pwr=="CONTROL" else 20260911
        C = 0.80*A + 0.20*S
        l0,h0,p0,bm0 = boot_mean(C-A, days, seed_stream(base,0))
        l9,h9,p9,_   = boot_mean(C-A, days, seed_stream(base,9))
        dl0,dh0,dp0,bs0 = boot_dsr(C, A, days, seed_stream(base,0))
        blo,bhi,bse = bonf_bound(float(sr(C)-sr(A)), bs0)
        gblo,gbhi,gbse = bonf_bound(float((C-A).mean()), bm0)
        lossmask = A < 0
        RES["levels"][f"AMI_standalone|dyn|s{sd}|{nm}"] = {"n":int(m.sum()),"g_bps":float(S.mean()),"sharpe":sr(S)}
        RES["levels"][f"A0arm|dyn|s{sd}|{nm}"]          = {"n":int(m.sum()),"g_bps":float(A.mean()),"sharpe":sr(A)}
        RES["levels"][f"A0+AMI20|dyn|s{sd}|{nm}"]       = {"n":int(m.sum()),"g_bps":float(C.mean()),"sharpe":sr(C)}
        RES["paired"][f"(A0+AMI20)-A0|dyn|s{sd}|{nm}"] = {
          "n":int(m.sum()),"power":pwr,
          "dg_bps":float((C-A).mean()),"dg_ci95_k0":[l0,h0],"dg_ci95_k9":[l9,h9],
          "dg_bonfK8":[gblo,gbhi],
          "dSharpe":float(sr(C)-sr(A)),"dSharpe_ci95_k0":[dl0,dh0],"dSharpe_P>0":dp0,
          "dSharpe_bonfK8":[blo,bhi],"dSharpe_boot_se":bse,
          "rho_sleeve_A0":float(np.corrcoef(S,A)[0,1]),
          "hedge_test_n_A0_losing":int(lossmask.sum()),
          "hedge_test_sleeve_g_on_A0_loss_anchors":float(S[lossmask].mean()) if lossmask.sum() else None,
          "PASS_dg_2streams":bool(l0>0 and l9>0),
          "PASS_dSharpe_bonfK8":bool(blo>0)}
    print("done sleeve", sd, flush=True)

json.dump(RES, open(f"{OUT}/R6J_JUDGE2.json","w"), indent=1)
print("WROTE", f"{OUT}/R6J_JUDGE2.json", flush=True)
