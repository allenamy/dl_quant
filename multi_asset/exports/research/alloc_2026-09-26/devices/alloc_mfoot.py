#!/usr/bin/env python3
"""alloc_mfoot.py — family M (DECISION_RULE_combination_layer §9) step 1 MECHANISM GATE + the pre-engine POWER PROJECTION the lead asked for.
Committed before it is run. No engine output is read. No MEAN of any book return is computed or written: the projection reports
variances and variance ratios only.

MECHANISM GATE (zero returns). For each seed k in {42, 2027, 7} and each momentum window j in {1, 3, 7} days: on every 2026 anchor
(2026-01-01 .. 2026-09-18T20Z) with a nonzero target, loading = Spearman corr between the target raw weights and mom_j over the names
with nonzero weight and finite mom_j (>= 20 names). med_arm / med_NC = median over anchors of |loading|.
  PASS iff med_arm <= 0.5 * med_NC for EVERY (seed, window) pair (9 of 9); else STOP.  [written before any number]
Also reported: turnover proxy, raw gross, publish / gross-gate counts vs NC (the §2-2 footprint items).

POWER PROJECTION (paper book, variance only). Paper book = the published target (carried through hold anchors), normalised to
sum|w| = 1, times the next 4h simple return of each name from the engine's own RAW 5-minute log-price table (missing -> 0), compounded
over full UTC days. For NC s42 the paper daily series is checked against the certified engine's NC s42 daily series (corr and variance
ratio; NC only). Then for R_M (s42) and M (each seed) vs the same-seed NC paper book, per segment: VR = var(arm)/var(NC), its 30-day MBB
95% interval (B = 10,000, rng (20260923, 1), days resampled jointly) and z = log(VR) / sd_MBB(log VR).
usage: /workspace/venv/bin/python -B alloc_mfoot.py <out.json>
"""
import os, sys, json, hashlib, time, calendar, math
import numpy as np
from scipy.stats import spearmanr
PX = "/workspace/baseline_tables_2026-09-19/work/price_full_raw_x0918r.npy"; PXM = "/workspace/baseline_tables_2026-09-19/work/price_full_raw_x0918r_meta.npz"
MOM = "/workspace/alloc_2026-09-26/work/mom_features.npz"; CELLS = "/workspace/alloc_2026-09-26/cells"
NC = {42: "/dev/shm/news2_2026-09-23/work/combo_s42", 2027: "/dev/shm/news2_2026-09-23/work/combo_s2027", 7: "/workspace/dlarch_2026-09-24/chain/ref_nc_s7X/work/combo_s7"}
NCSER = "/workspace/dlarch_2026-09-24/receipts/RETAIN_REFNC_s42_SELFCTL_2026-09-26.json/SER_DLARCH_REF_NC_s42X_scaled_rule_raw_UAFE.npz"
SEEDS = (42, 2027, 7); KS = (1, 3, 7); MIN_NAMES = 20; B = 10000; RNG = (20260923, 1); BLOCK = 30
def ts(s): return calendar.timegm(time.strptime(s, "%Y-%m-%dT%H:%M:%SZ"))
SEG = {"pre2026": (ts("2023-06-30T04:00:00Z"), ts("2025-12-31T20:00:00Z")), "2026": (ts("2026-01-01T00:00:00Z"), ts("2026-09-18T20:00:00Z"))}


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


def mbb_idx(n):
    block = min(BLOCK, n); k = math.ceil(n / block); rng = np.random.default_rng(list(RNG))
    st = rng.integers(0, n - block + 1, size=(B, k))
    return (st[:, :, None] + np.arange(block)[None, None, :]).reshape(B, k * block)[:, :n]


def load_combo(d):
    z = np.load(f"{d}/scaled_diagnostic.npz"); return {k: z[k] for k in ("E_ts", "raw", "weights", "trade_mask", "reason")}, sha(f"{d}/scaled_diagnostic.npz")


def loading_median(raw, mom, rows, j):
    out = []
    for i in rows:
        w = raw[i]; x = mom[i, :, j]; ok = (np.abs(w) > 1e-9) & np.isfinite(x)
        if ok.sum() >= MIN_NAMES: out.append(abs(spearmanr(w[ok], x[ok])[0]))
    return (float(np.median(out)), len(out)) if out else (None, 0)


def paper_daily(C, A, lp, grid):
    """published target carried through holds, sum|w|=1, next-4h simple return; -> (days, daily simple return)"""
    W = C["weights"]; tm = C["trade_mask"]; n = len(A); cur = np.zeros(W.shape[1]); r4 = np.zeros(n)
    i0 = np.searchsorted(grid, A); i1 = np.searchsorted(grid, A + 14400)
    okg = (i1 < len(grid)) & (grid[np.minimum(i0, len(grid) - 1)] == A) & (grid[np.minimum(i1, len(grid) - 1)] == A + 14400)
    for i in range(n):
        if tm[i]:
            g = np.abs(W[i]).sum(); cur = W[i] / g if g > 1e-12 else cur
        if okg[i]:
            ret = np.expm1(np.asarray(lp[i1[i]]) - np.asarray(lp[i0[i]])); r4[i] = float(np.nansum(cur * np.where(np.isfinite(ret), ret, 0.0)))
    d = (A // 86400) * 86400; ud, inv, cnt = np.unique(d, return_inverse=True, return_counts=True)
    out = np.ones(len(ud)); np.multiply.at(out, inv, 1.0 + r4)
    full = cnt == 6
    return ud[full], (out - 1.0)[full]


def vr_stats(x, y):
    idx = mbb_idx(len(x)); vx = x[idx].var(1, ddof=1); vy = y[idx].var(1, ddof=1); lv = np.log(vx / vy)
    vr = float(x.var(ddof=1) / y.var(ddof=1))
    return {"VR": vr, "mbb95": [float(np.exp(np.percentile(lv, 2.5))), float(np.exp(np.percentile(lv, 97.5)))],
            "z_logVR": float(math.log(vr) / lv.std(ddof=1)), "n_days": int(len(x))}


def main():
    out_path = sys.argv[1]
    MZ = np.load(MOM); mom_all = MZ["mom"]; ma = MZ["E_ts"].astype(np.int64)
    m = np.load(PXM); grid = m["grid"].astype(np.int64); lp = np.load(PX, mmap_mode="r")
    rec = {"device": "alloc_mfoot.py", "self_sha256": sha(os.path.abspath(__file__)), "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "no_book_mean_computed": True, "inputs": {"mom_features": sha(MOM), "price_meta": sha(PXM)}, "mechanism": {}, "footprint": {}, "power": {}}
    nc = {s: load_combo(NC[s]) for s in SEEDS}
    arm = {s: load_combo(f"{CELLS}/inservice_momneutral_s{s}/work/combo_s{s}") for s in SEEDS}
    rm = load_combo(f"{CELLS}/inservice_conc20_s42/work/combo_s42")
    rec["inputs"].update({f"NC_s{s}": nc[s][1] for s in SEEDS}); rec["inputs"].update({f"M_s{s}": arm[s][1] for s in SEEDS}); rec["inputs"]["RM_s42"] = rm[1]
    A = nc[42][0]["E_ts"].astype(np.int64); pos = np.searchsorted(ma, A); assert np.array_equal(ma[pos], A); mom = mom_all[pos]
    r26 = np.flatnonzero((A >= SEG["2026"][0]) & (A <= SEG["2026"][1]))
    all_ok = True
    for s in SEEDS:
        C, N = arm[s][0], nc[s][0]; assert np.array_equal(C["E_ts"], N["E_ts"])
        rec["mechanism"][str(s)] = {}
        for j, k in enumerate(KS):
            ma_, na_ = loading_median(C["raw"], mom, r26, j); mn_, nn_ = loading_median(N["raw"], mom, r26, j)
            ok = ma_ is not None and mn_ is not None and ma_ <= 0.5 * mn_
            all_ok &= bool(ok)
            rec["mechanism"][str(s)][f"k{k}"] = {"median_abs_loading_arm": ma_, "median_abs_loading_NC": mn_, "ratio": (ma_ / mn_ if mn_ else None),
                                                 "n_anchors": na_, "PASS": bool(ok)}
            print(f"MECH s{s} k{k}: arm {ma_:.4f} NC {mn_:.4f} ratio {ma_ / mn_:.3f} {'PASS' if ok else 'FAIL'}", flush=True)
        for w, (lo, hi) in SEG.items():
            rows = np.flatnonzero((A >= lo) & (A <= hi))
            def tov(W):
                g = np.abs(W).sum(1, keepdims=True); x = np.where(g > 1e-12, W / np.where(g > 1e-12, g, 1), 0.0); r = rows[rows >= 1]
                return float(np.abs(x[r] - x[r - 1]).sum(1).mean())
            ga = np.array(["gross" in q for q in C["reason"][rows].astype(str)]); gn = np.array(["gross" in q for q in N["reason"][rows].astype(str)])
            rec["footprint"].setdefault(str(s), {})[w] = {"turnover_proxy": {"arm": tov(C["raw"]), "NC": tov(N["raw"])},
                                                          "raw_gross_mean": {"arm": float(np.abs(C["raw"][rows]).sum(1).mean()), "NC": float(np.abs(N["raw"][rows]).sum(1).mean())},
                                                          "publish": {"arm": int(C["trade_mask"][rows].sum()), "NC": int(N["trade_mask"][rows].sum())},
                                                          "gross_gate_rule_frac": float((ga & ~gn).mean())}
    rec["MECHANISM_GATE"] = "PASS" if all_ok else "FAIL"
    # ── power projection (variance only) ──
    pd = {}
    for s in SEEDS: pd[("NC", s)] = paper_daily(nc[s][0], A, lp, grid); pd[("M", s)] = paper_daily(arm[s][0], A, lp, grid)
    pd[("RM", 42)] = paper_daily(rm[0], A, lp, grid)
    Z = np.load(NCSER); EA = Z["anchors"].astype(np.int64); er = Z["r_per_path"].mean(0)
    ed = (EA // 86400) * 86400; eu, einv, ecnt = np.unique(ed, return_inverse=True, return_counts=True); eo = np.ones(len(eu)); np.multiply.at(eo, einv, 1 + er)
    eday = dict(zip(eu[ecnt == 6], (eo - 1)[ecnt == 6]))
    days, pnc = pd[("NC", 42)]
    for w, (lo, hi) in SEG.items():
        sel = np.array([(lo // 86400 * 86400) <= d <= hi and d in eday for d in days])
        x = pnc[sel]; y = np.array([eday[d] for d in days[sel]])
        rec["power"].setdefault("paper_vs_engine_NC_s42", {})[w] = {"corr_daily": float(np.corrcoef(x, y)[0, 1]), "var_ratio_paper_over_engine": float(x.var(ddof=1) / y.var(ddof=1)), "n_days": int(sel.sum())}
    for w, (lo, hi) in SEG.items():
        for lab, s in [("RM", 42)] + [("M", s) for s in SEEDS]:
            d1, a1 = pd[(lab, s)]; d0, b0 = pd[("NC", s)]; assert np.array_equal(d1, d0)
            sel = (d1 >= lo // 86400 * 86400) & (d1 <= hi)
            rec["power"].setdefault(f"{lab}_s{s}", {})[w] = vr_stats(a1[sel], b0[sel])
            v = rec["power"][f"{lab}_s{s}"][w]; print(f"POWER {lab} s{s} {w}: VR {v['VR']:.3f} mbb95 {v['mbb95'][0]:.3f}..{v['mbb95'][1]:.3f} z {v['z_logVR']:+.2f}", flush=True)
    json.dump(rec, open(out_path + ".tmp", "w"), indent=1); os.replace(out_path + ".tmp", out_path)
    assert json.load(open(out_path))["self_sha256"] == rec["self_sha256"]
    print(f"ALLOC_MFOOT MECHANISM_GATE={rec['MECHANISM_GATE']} {sha(out_path)[:16]}", flush=True)


if __name__ == "__main__":
    main()
