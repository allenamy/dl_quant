#!/usr/bin/env python3
"""r15_nulls.py — PREREG_r15 §8 turnover-matched nulls for ARM-F and ARM-S, both seeds, on the DERIVED device
(GATE P2/P3 proved its FTPOS=1 / SEATNET=1 paths bitwise equal to the pinned device; asserted here from the receipt).

ARM-F : randomise the rn8 matrix used ONLY in the FTPOS kill test.  RELAB_d = fixed symbol permutation
        default_rng([4242,d]).permutation(829), d=1..3 (informative);  SHIFT_k = rows advanced by k in {101,503,1009}
        (weak for persistent quantities).  Dose = R15_KILL_TH in [-0.0100, 0.0], bisected until the null's marginal
        matched turnover  dtau = mean_WA(turnover/gt)_null - mean_WA(turnover/gt)_A0  is within 1% of ARM-F's.
ARM-S : randomise the 4h-carry matrix used ONLY in the SEATNET subtraction (same families).  Dose = R15_SEATC_SCALE
        in [0, 8], same matching rule.
Max 13 bisection steps; unmatched -> closest step reported and flagged.  Firing counts recorded.
"""
import os, sys, json, time, hashlib, subprocess, calendar
WHITE = set(x for x in sys.argv[1].split(",") if x) if len(sys.argv) > 1 else None
assert WHITE, "launch with a non-empty env whitelist as argv[1]"
BANNED = ('CAL','JUDGE','UPLIFT','PANEL','LOOK','WRULE','LEGS','PHI','FSEED','W3FIX','FTRIM','UMASK','SLOW','FPRED','MEMBERS_TOPN','COSTB','SLEEVE','KMOD','SEAT','RNSM','LTRIM','CDAMP','FUNDSCALE','FEMAT','TRADE_TOPN','REF_SKIP','PYTHON','OMP','MKL','R15','FTPOS','OUT_TAG')
EXTRA = sorted(k for k in os.environ if k not in WHITE); assert EXTRA == [], ("ENV WHITELIST VIOLATION", EXTRA)
BAN = sorted(k for k in os.environ if k.startswith(BANNED)); assert BAN == [], ("CALIBER FLAG PRESENT", BAN)
ENV = dict(env_whitelist=sorted(WHITE), env_actual={k: os.environ[k] for k in sorted(os.environ)}, launch_cmdline=" ".join(sys.argv))
import numpy as np
R = "/workspace/uplift_2026-09-11/r15_structural"; D = R + "/dev"; PY = "/workspace/venv/bin/python"
DER = R + "/devices/w10_sleeve_r15.py"; PREREG_SHA = "097769b087fa0834fb780062bf710134d7e3a67555174de5c26c1668c455f6fc"
def sha(p):
    h = hashlib.sha256()
    with open(os.path.realpath(p), "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()
assert sha(R + "/PREREG_r15_structural_2026-09-12.md") == PREREG_SHA
G = json.load(open(R + "/receipts/RECEIPT_r15_drive_gateP.json"))
assert G["gate"]["P1"]["PASS"] and G["gate"]["P2"]["PASS"] and G["gate"]["P3"]["PASS"], G["gate"]
assert sha(DER) == G["derived_device_sha256"], ("DERIVED DEVICE CHANGED", sha(DER))
BASE = G["base_env"]; A0K = {s: dict(G["runs"]["GP_A0_s" + s]["env"]) for s in ("42", "2027")}
for s in A0K: A0K[s].pop("OUT_TAG")
for p in (R + "/nulls", R + "/sig", D + "/logs"): os.makedirs(p, exist_ok=True)
UB = calendar.timegm((2026, 8, 30, 20, 0, 0))
A0_TS = None
def load_rec(p):
    """Rows are aligned to the ARCHIVED A0's timestamp grid (10039 rows). A null run at an extreme dose can legitimately drop
    an anchor (device L241/L245 `continue` when sel<80 or composite gross<1e-9); such anchors are NaN here and excluded from
    every paired statistic (both sides), and their count is recorded (n_missing)."""
    Z = np.load(p, allow_pickle=True); C = [str(c) for c in Z["cols"]]; rec = Z["d30_n2_c42_rec"] if "d30_n2_c42_rec" in Z else Z["rec"]
    ts = rec[:, 0].astype(np.int64)
    if A0_TS is None:
        WT = ts <= UB; WA = WT.copy(); WA[:900] = False; assert WA.sum() == 9138 and len(ts) == 10039
        col = lambda k: rec[:, C.index(k)].astype(float)
        return dict(ts=ts, WA=WA, g=col("net_ex") / col("gross_total"), tau=col("turnover") / col("gross_total"), w3k=col("w3_king"), rec=rec, cols=C, n_missing=0)
    pos = {int(t): i for i, t in enumerate(ts)}; idx = np.array([pos.get(int(t), -1) for t in A0_TS]); have = idx >= 0
    assert set(ts.tolist()) <= set(A0_TS.tolist()), "null run has anchors outside the A0 grid"
    def col(k):
        v = np.full(len(A0_TS), np.nan); v[have] = rec[idx[have], C.index(k)].astype(float); return v
    WT = A0_TS <= UB; WA = WT.copy(); WA[:900] = False; WA &= have; assert WA.sum() >= 9138 - 50, int(WA.sum())
    return dict(ts=A0_TS, WA=WA, g=col("net_ex") / col("gross_total"), tau=col("turnover") / col("gross_total"), w3k=col("w3_king"), rec=rec, cols=C, n_missing=int(9138 - WA.sum()))
A0 = {}
for s in ("42", "2027"):
    A0[s] = load_rec(G["runs"]["GP_A0_s" + s]["out"])
    if A0_TS is None: A0_TS = A0[s]["ts"]
    assert np.array_equal(A0[s]["ts"], A0_TS)
ARM = {("F", s): load_rec(R + "/arms/F_s%s.npz" % s) for s in ("42", "2027")}
ARM.update({("S", s): load_rec(R + "/arms/S_s%s.npz" % s) for s in ("42", "2027")})
def dtau(x, s): return float((x["tau"] - A0[s]["tau"])[x["WA"]].mean())
def dg(x, s): return float((x["g"] - A0[s]["g"])[x["WA"]].mean())
def fire_S(x, s): return float(np.abs(x["w3k"] - A0[s]["w3k"])[x["WA"]].mean())
TARGET = {k: dict(dtau=dtau(v, k[1]), dg=dg(v, k[1]), fire_S=fire_S(v, k[1])) for k, v in ARM.items()}
# --- null matrices, built exactly as the device builds _RN8 (L86) and the L169 carry quantity
PW = np.load("/workspace/data/wide_panel_4h_v2ext.npz", allow_pickle=True); assert os.path.realpath(D + "/pod_backup_2026-08-21/wide_panel_4h_hist_v2.npz") == "/workspace/data/wide_panel_4h_v2ext.npz"
pts = PW["ts"].astype(np.int64); sym = PW["symbols"]; FN = PW["f_fund_now"]; IV = PW["f_fund_iv"]
IVf = np.where(np.isfinite(IV) & (IV > 0), IV, 8.0); RN8 = np.nan_to_num(FN, nan=0.0) * (8.0 / IVf); C4 = np.nan_to_num(FN, nan=0.0) * (4.0 / IVf)
SIG = {}
for base, nm in ((RN8, "KILL"), (C4, "C4")):
    for d in (1, 2, 3):
        pi = np.random.default_rng([4242, d]).permutation(base.shape[1]); f = R + "/sig/%s_RELAB%d.npz" % (nm, d)
        np.savez(f, symbols=sym, ts=pts, mat=np.asarray(base[:, pi], np.float64), perm=pi); SIG[(nm, "RELAB%d" % d)] = f
    for k in (101, 503, 1009):
        Q = np.zeros_like(base); Q[k:] = base[:-k]; f = R + "/sig/%s_SHIFT%d.npz" % (nm, k)
        np.savez(f, symbols=sym, ts=pts, mat=np.asarray(Q, np.float64)); SIG[(nm, "SHIFT%d" % k)] = f
SIGSHA = {"%s_%s" % k: sha(v) for k, v in SIG.items()}
def run(tag, seed, extra):
    dst = R + "/nulls/%s.npz" % tag
    env = dict(BASE); env.update(A0K[seed]); env.update(extra); env["OUT_TAG"] = tag
    if not os.path.exists(dst):
        with open(D + "/logs/%s.log" % tag, "w") as lf:
            rc = subprocess.call([PY, DER], cwd=D, stdout=lf, stderr=subprocess.STDOUT, env=env)
        src = D + "/probe_artifacts/w10_ablation_series_%s.npz" % tag
        assert rc == 0 and os.path.exists(src), ("RUN FAILED", tag, rc)
        Z = np.load(src, allow_pickle=True)
        kills = Z["d30_n2_c42_R15_kill"].sum(1).astype(np.int32) if "d30_n2_c42_R15_kill" in Z else None
        np.savez_compressed(dst, cols=Z["cols"], rec=Z["d30_n2_c42_rec"], config_json=Z["config_json"], kills=(kills if kills is not None else np.zeros(0, np.int32)))
        os.remove(src)
        try: os.remove(D + "/probe_artifacts/w10_ablation_summary_%s.json" % tag)
        except FileNotFoundError: pass
    Z = np.load(dst, allow_pickle=True); x = load_rec(dst); x["kills"] = Z["kills"]; x["env"] = env; x["out"] = dst
    return x
def chain(job):
    arm, seed, fam = job; tgt = TARGET[(arm, seed)]["dtau"]; sigf = SIG[("KILL" if arm == "F" else "C4", fam)]
    lo, hi = (-0.0100, 0.0) if arm == "F" else (0.0, 8.0)
    trace = []; best = None
    for it in range(13):
        mid = 0.5 * (lo + hi); tag = "N_%s_%s_s%s_it%02d" % (arm, fam, seed, it)
        extra = ({"FTPOS": "1", "R15_INSTR": "1", "R15_KILL_NPZ": sigf, "R15_KILL_TH": "%.10f" % mid} if arm == "F"
                 else {"SEATNET": "1", "R15_SEATC_NPZ": sigf, "R15_SEATC_SCALE": "%.10f" % mid})
        x = run(tag, seed, extra); mt = dtau(x, seed); rel = (mt - tgt) / max(abs(tgt), 1e-12)
        trace.append(dict(it=it, dose=mid, dtau=mt, rel_err=rel, dg=dg(x, seed), tag=tag, n_missing=x["n_missing"]))
        if best is None or abs(rel) < abs(best[1]): best = (mid, rel, x, tag)
        if abs(rel) <= 0.01: break
        if mt < tgt: lo = mid
        else: hi = mid
    dose, rel, x, tag = best
    out = dict(arm=arm, seed=seed, family=fam, sig=sigf, sig_sha256=SIGSHA["%s_%s" % ("KILL" if arm == "F" else "C4", fam)], dose_matched=dose, dtau=dtau(x, seed), dtau_target=tgt,
               dtau_rel_err=rel, MATCHED=bool(abs(rel) <= 0.01), n_steps=len(trace), trace=trace, dg=dg(x, seed), dg_arm=TARGET[(arm, seed)]["dg"],
               tag=tag, out=x["out"], out_sha256=sha(x["out"]), env=x["env"], env_whitelist=sorted(x["env"]),
               tau_matched_mean=float(x["tau"][x["WA"]].mean()), weak_family=fam.startswith("SHIFT"), n_missing_anchors=x["n_missing"], n_paired=int(x["WA"].sum()))
    if arm == "F":
        out["fire_total_WA"] = int(x["kills"][x["WA"]].sum()) if len(x["kills"]) else None
        FI = np.load(R + "/arms/D_FI_s%s.npz" % seed, allow_pickle=True)["d30_n2_c42_R15_kill"].sum(1); out["fire_target_WA"] = int(FI[x["WA"]].sum())
        out["fire_rel_err"] = float(out["fire_total_WA"] / max(out["fire_target_WA"], 1) - 1)
    else:
        out["fire_S_mean_abs_dw3k"] = fire_S(x, seed); out["fire_S_target"] = TARGET[(arm, seed)]["fire_S"]
    return out
JOBS = [(a, s, f) for a in ("F", "S") for s in ("42", "2027") for f in ("RELAB1", "RELAB2", "RELAB3", "SHIFT101", "SHIFT503", "SHIFT1009")]
LOAD0 = open("/proc/loadavg").read().split()[:3]; assert float(LOAD0[0]) <= 6.0, ("LOAD TOO HIGH, WAIT", LOAD0)
from concurrent.futures import ThreadPoolExecutor
t0 = time.time(); NULLS = {}
with ThreadPoolExecutor(max_workers=12) as ex:
    for o in ex.map(chain, JOBS):
        NULLS["%s_s%s_%s" % (o["arm"], o["seed"], o["family"])] = o
        print("NULL %s s%s %-9s dose %.6f dtau %+.6f (tgt %+.6f rel %+.4f) %s steps %2d dg %+.4f (arm %+.4f)%s" % (
            o["arm"], o["seed"], o["family"], o["dose_matched"], o["dtau"], o["dtau_target"], o["dtau_rel_err"], "MATCHED" if o["MATCHED"] else "UNMATCHED", o["n_steps"], o["dg"], o["dg_arm"],
            ("  fire %d/%d" % (o["fire_total_WA"], o["fire_target_WA"]) if o["arm"] == "F" else "  |dw3k| %.4f (arm %.4f)" % (o["fire_S_mean_abs_dw3k"], o["fire_S_target"]))), flush=True)
LOAD1 = open("/proc/loadavg").read().split()[:3]
RC = dict(self_sha256=sha(os.path.abspath(__file__)), prereg_sha256=PREREG_SHA, derived_device_sha256=sha(DER), env=ENV, targets={"%s_s%s" % k: v for k, v in TARGET.items()},
          sig_sha256=SIGSHA, nulls=NULLS, loadavg_before=LOAD0, loadavg_after=LOAD1, wall_s=round(time.time() - t0, 1), built_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
json.dump(RC, open(R + "/receipts/RECEIPT_r15_nulls.json", "w"), indent=1, default=str)
print("DONE_r15_nulls", RC["wall_s"], "s")
