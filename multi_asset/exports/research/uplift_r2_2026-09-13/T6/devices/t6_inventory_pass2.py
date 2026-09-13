#!/usr/bin/env python3
"""t6_inventory_pass2.py -- T6 step 1b (inventory, NO statistics). Read-only.
For every record file in INVENTORY_pod2.json that is on the v4 accounting caliber (costb_PWR_G230k, umask_UPIT_CRYPTO m1,
MEMBERS_TOPN 829, CAL log) this records STRUCTURAL facts only:
  - judged record key (d30_n2_c42_rec if present else rec -- the r18 judge rule, r18_judge.py load()),
  - W_FULL coverage against the canonical grid (archived A0 ts, ts <= 2026-08-30 20Z, n=10038),
  - count of W_FULL anchors whose g = net_ex/gross_total is non-finite (structural validity, no aggregation),
  - g_sha256 = sha256 of the float64 bytes of g on W_FULL (exact-duplicate detection; no mean/std/Sharpe is computed),
  - the same hash restricted to FROZEN (2025-03-01 00Z .. 2026-08-10 20Z),
  - device shas from config_json.
Plus rec-semantics equality checks (np.array_equal on whole records) for rec-only directories vs the archived A0.
Usage: python3 t6_inventory_pass2.py <env_whitelist_csv> <inventory_json> <out_json>
"""
import os, sys, json, time, hashlib, calendar
WHITE = set(x for x in sys.argv[1].split(",") if x); assert WHITE, "non-empty env whitelist required"
EXTRA = sorted(k for k in os.environ if k not in WHITE); assert EXTRA == [], ("ENV WHITELIST VIOLATION", EXTRA)
INV, OUT = sys.argv[2], sys.argv[3]
import numpy as np
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()
ARCH = "/workspace/uplift_2026-09-11/r8_inbook/arms/R8_A0_dyn_s42.npz"      # archived A0 s42 (file sha 352ac36f..., r18 RESULT header)
ARCH27 = "/workspace/uplift_2026-09-11/r8_inbook/arms/R8_A0_dyn_s2027.npz"  # archived A0 s2027 (aa44e18f...)
UB = calendar.timegm((2026, 8, 30, 20, 0, 0)); F0 = calendar.timegm((2025, 3, 1, 0, 0, 0)); F1 = calendar.timegm((2026, 8, 10, 20, 0, 0))
Z = np.load(ARCH); C = [str(c) for c in Z["cols"]]; A = Z["rec"]
TS = A[:, C.index("ts")].astype(np.int64); WF = TS[TS <= UB]
assert len(WF) == 10038 and WF[0] == calendar.timegm((2022, 1, 31, 0, 0, 0)) and np.all(np.diff(WF) == 14400), (len(WF), WF[0])
FR = WF[(WF >= F0) & (WF <= F1)]; assert len(FR) == 3168, len(FR)
D = json.load(open(INV))
def acal(c):
    return (str(c.get("COSTB_JSON", "")).endswith("costb_PWR_G230k.json") and str(c.get("UMASK_NPZ", "")).endswith("umask_UPIT_CRYPTO.npz")
            and c.get("UMASK_SCOPE") == "m1" and c.get("MEMBERS_TOPN") == 829 and c.get("CAL") == "log")
t0 = time.time(); rows = []
for r in D["rows"]:
    if not r.get("records") or not acal(r.get("cal", {})): continue
    p = r["path"]; keys = r["keys"]
    rk = "d30_n2_c42_rec" if "d30_n2_c42_rec" in keys else ("rec" if "rec" in keys else None)
    o = dict(path=p, file_sha256=r["sha256"], rec_key=rk)
    if rk is None: o["error"] = "no d30_n2_c42_rec/rec key"; rows.append(o); continue
    try:
        Zr = np.load(p); Cr = [str(c) for c in Zr["cols"]]; R = Zr[rk]
        assert R.shape[1] == len(Cr)
        ts = R[:, Cr.index("ts")]; ok_ts = np.isfinite(ts); tsi = ts[ok_ts].astype(np.int64)
        ne = R[ok_ts, Cr.index("net_ex")]; gt = R[ok_ts, Cr.index("gross_total")]
        pos = {int(t): i for i, t in enumerate(tsi)}
        idx = np.array([pos.get(int(t), -1) for t in WF]); miss = int((idx < 0).sum())
        o.update(n_rows=int(R.shape[0]), n_cols=int(R.shape[1]), ts_first=int(tsi.min()), ts_last=int(tsi.max()),
                 ts_first_utc=time.strftime("%Y-%m-%d %HZ", time.gmtime(int(tsi.min()))), ts_last_utc=time.strftime("%Y-%m-%d %HZ", time.gmtime(int(tsi.max()))),
                 wfull_missing=miss, dup_ts=int(len(tsi) - len(pos)))
        if miss == 0:
            with np.errstate(divide="ignore", invalid="ignore"): g = ne[idx] / gt[idx]
            bad = ~np.isfinite(g) | ~(gt[idx] > 0)
            o["wfull_nonfinite_or_nonpos_gross"] = int(bad.sum())
            o["g_sha256_wfull"] = hashlib.sha256(np.ascontiguousarray(g, dtype=np.float64).tobytes()).hexdigest()
            fm = (WF >= F0) & (WF <= F1)
            o["g_sha256_frozen"] = hashlib.sha256(np.ascontiguousarray(g[fm], dtype=np.float64).tobytes()).hexdigest()
        cfg = json.loads(str(Zr["config_json"])) if "config_json" in Zr.files else {}
        o["device"] = {b: {k: v for k, v in d.items() if "sha" in k} for b, d in cfg.items() if isinstance(d, dict)}
        o["has_S0_rec"] = "S0_rec" in keys
    except Exception as e:
        o["error"] = "%s: %s" % (type(e).__name__, str(e)[:200])
    rows.append(o)
# rec-semantics checks: rec-only directories' A0 reproductions vs the archived A0 (whole-record np.array_equal, incl. NaN positions)
def rec_of(p, k=None):
    Zz = np.load(p); k = k or ("d30_n2_c42_rec" if "d30_n2_c42_rec" in Zz.files else "rec"); return Zz[k]
def same(a, b): return bool(a.shape == b.shape and np.array_equal(np.nan_to_num(a, nan=1e300), np.nan_to_num(b, nan=1e300)) and np.array_equal(np.isnan(a), np.isnan(b)))
U = "/workspace/uplift_2026-09-11"
CHECKS = [("r18 C0_s42 d30_n2_c42_rec == archived A0 rec", U + "/r18_foundation/arms/C0_s42.npz", ARCH),
          ("r12 G1_a010_b250_aux0 rec == archived A0 rec", U + "/r12_smoothing/arms/G1_a010_b250_aux0.npz", ARCH),
          ("r16 GP_s42_aux0 rec == archived A0 rec", U + "/r16_asym_band/arms/GP_s42_aux0.npz", ARCH),
          ("r5_oi IB_PARITY rec == archived A0 rec", U + "/r5_oi/out/IB_PARITY.npz", ARCH),
          ("r15 GP_A0_s42 d30_n2_c42_rec == archived A0 rec", U + "/r15_structural/arms/GP_A0_s42.npz", ARCH),
          ("T2 GP_A0_s42 d30_n2_c42_rec == archived A0 rec", "/workspace/uplift_r2_2026-09-13/T2/arms/GP_A0_s42.npz", ARCH),
          ("r8b2 R8_A0_s42 d30_n2_c42_rec cols[:23] == archived A0 rec", U + "/r8b2/dev/probe_artifacts/w10_ablation_series_R8_A0_s42.npz", ARCH),
          ("r15 GP_A0_s2027 d30_n2_c42_rec == archived A0 s2027 rec", U + "/r15_structural/arms/GP_A0_s2027.npz", ARCH27),
          ("r3k A0_PWR230k_s42 rec == archived A0 rec", U + "/r3k/arms/A0_PWR230k_s42.npz", ARCH)]
chk = []
for lab, a, b in CHECKS:
    try:
        ra, rb = rec_of(a), rec_of(b)
        if ra.shape[1] == 24 and rb.shape[1] == 23:
            Za = np.load(a); Ca = [str(c) for c in Za["cols"]]; Cb = [str(c) for c in np.load(b)["cols"]]
            ra = ra[:, [Ca.index(c) for c in Cb]]
        chk.append(dict(label=lab, a=a, b=b, a_sha256=sha(a), b_sha256=sha(b), equal=same(ra, rb), shape_a=list(ra.shape), shape_b=list(rb.shape)))
    except Exception as e:
        chk.append(dict(label=lab, a=a, b=b, error="%s: %s" % (type(e).__name__, str(e)[:200])))
out = dict(device="t6_inventory_pass2.py", self_sha256=sha(os.path.abspath(__file__)), argv=sys.argv, env_whitelist=sorted(WHITE),
           env_actual={k: os.environ[k] for k in sorted(os.environ)}, python=sys.version.split()[0], numpy=np.__version__, host=os.uname().nodename,
           inventory_sha256=sha(INV), archived_A0=dict(path=ARCH, sha256=sha(ARCH), path27=ARCH27, sha256_27=sha(ARCH27)),
           W_FULL=dict(n=int(len(WF)), first=int(WF[0]), last=int(WF[-1])), FROZEN=dict(n=int(len(FR)), first=int(FR[0]), last=int(FR[-1])),
           n_rows=len(rows), n_complete_wfull=sum(1 for o in rows if o.get("wfull_missing") == 0),
           n_complete_and_finite=sum(1 for o in rows if o.get("wfull_missing") == 0 and o.get("wfull_nonfinite_or_nonpos_gross") == 0),
           n_errors=sum(1 for o in rows if "error" in o), rec_semantics_checks=chk, wall_s=round(time.time() - t0, 1), rows=rows)
json.dump(out, open(OUT, "w"), indent=1)
print("SUMMARY t6_inventory_pass2 rows=%d complete_wfull=%d complete_finite=%d errors=%d checks_equal=%s self_sha256=%s wall=%.1fs"
      % (len(rows), out["n_complete_wfull"], out["n_complete_and_finite"], out["n_errors"], [c.get("equal") for c in chk], out["self_sha256"][:16], out["wall_s"]))
