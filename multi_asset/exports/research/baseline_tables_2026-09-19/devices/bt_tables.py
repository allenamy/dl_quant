#!/usr/bin/env python3
"""bt_tables.py — TABLE DEVICE for docs/PREREG_baseline_tables_certified_2026-09-19.md (67769510b) §3.1–§3.6 and §4. Pure numpy functions
(importable, no I/O at import) + a CLI that runs ONLY the reconciliation steps ① and ② on the OLD stream-R object P2-CMB (the lead's scope).

Definitions (prereg §4; written here before any number from this device):
  window return        r_w = NAV(A+4h)/NAV(A) − 1 on the MAIN reading (UA-FREEZE-EXCLUDE removes UNKNOWN cells; LEGACY / v2: = the simulator NAV).
  g                    1e4·r_w / gm (bps per anchor per unit TARGET gross; gm = 2.0 ⇒ NAV return = 2·g·1e-4), the judge's net_ex / gross_total at the
                       executed-book layer; components price / funding (paid > 0) / fee / unknown-excluded, each 1e4·x/(gm·NAV_start); g = price −
                       funding − fee − unknown (asserted per window, 1e-9).
  daily returns        UTC day d: Π_{windows with A in d}(1 + r_w) − 1 (the 4h NAV compounded by UTC day; §4).
  CAGR                 (Π_d(1 + r_d))^(365/n_days) − 1 (compound; n_days = number of UTC days in the cell); a NAV ≤ 0 ⇒ −100 %.
  daily Sharpe         mean(r_d)/std(r_d, ddof=1)·√365; undefined (None) when n_days < 2 or std = 0.
  maxDD                min over the sampled NAV of NAV/cummax − 1 with the cell's starting NAV as the first point; two samplings, always labelled:
                       '4h' = window boundaries, '5m' = every 5-minute boundary of the simulator's event path (per path; for the MEAN path the 5-minute
                       mean returns compounded). Never called intraday worst risk.
  worst 30 days        min over every 30 consecutive UTC days of Π(1 + r_d) − 1 (None if fewer than 30 days).
  CVaR 5 %             mean of the worst ceil(0.05·n_days) daily returns.
  mean path            the 32 fill paths' per-window MEAN return compounded (the conditional expectation under fill randomness, §4; not a forecast
                       interval); path distribution = per-path metrics' median and 5 % / 95 % percentiles (numpy linear), description only.
  bootstrap            moving-block bootstrap on calendar UTC days (non-circular: block starts uniform on 0..n−b, ceil(n/b) blocks concatenated and
                       truncated to n); main block 5 days, sensitivity 1 and 10; B = 10,000; rng = numpy.random.default_rng([20260919, 99]) (the
                       §3.5 generator; used for every bootstrap in this device — §3.2 does not name another). The same day indices are applied to
                       every series of a comparison; nonlinear statistics are recomputed per draw.
  §3.2 cells           G0 frozen labels (bt_g0_extend.py output; LAB_EXCL primary): 7 variables × {low, mid, high} = 21 cells; per cell the §3.1
                       metrics + anchors + days + mean-g CI (5 / 1 / 10-day blocks) + Bonferroni K = 21 interval (percentiles 0.119 / 99.881 of the
                       5-day draws, same draws); a cell with < 2 days is 'describe only' (no CI, no mark).
  §3.4 cost cells      fee × 1.25 (USDT maker / taker rates); slippage × 1.5 (the pooled signed slippage values, as written); fill rate × 0.9 (every
                       fill probability: first-leg full and partial shares × 0.9 with the removed mass moved to 'zero', and the completion probability
                       π × 0.9). Applied one at a time by COST_CELLS → calibration override (bt_driver consumes it); Δ vs the base cell.
  §3.5 pairing         ΔSR = SR(a) − SR(b), ΔR = CAGR(a) − CAGR(b) on the aligned daily returns of the two mean paths; Δg = linear mean of per-anchor
                       paired differences; CI95 = 2.5 / 97.5 percentiles of the draws; one-sided centred p: p_up = (1 + #{Δ* − Δ̂ ≥ Δ̂})/(B + 1),
                       p_down = (1 + #{Δ* − Δ̂ ≤ Δ̂})/(B + 1); label (A) better iff p_up < 0.05, (B) worse iff p_down < 0.05, else (C) — reading only,
                       'CI contains 0' is never written as equivalent or non-inferior; zero-variance draws counted, > 1 % ⇒ UNAVAILABLE.
  §3.6 reconciliation  fixed order ①→②→③; step k's Δ = metric(after step k) − metric(before step k) on the same window; interactions fall into the
                       later step by construction (Σ steps = total, telescoping, asserted). Point Δ on the mean paths; CI for ΔCAGR / ΔSharpe / Δg from
                       the paired bootstrap above; ΔmaxDD: point + per-fill-path 5 / 50 / 95 % (paired by seed when both sides have paths).
usage (CLI, steps ① and ② only):
  python bt_tables.py recon <v2_s42.npz> <v2_s2027.npz> <run_dir_old_s42> <run_dir_old_s2027> <run_dir_raw_s42> <run_dir_raw_s2027> <out.json>
"""
import json, math, os, sys, time, hashlib

import numpy as np

H4 = 14400; DAY = 86400; GM = 2.0
B_DEFAULT = 10000; RNG_SEED = (20260919, 99); BLOCK_MAIN = 5; BLOCK_SENS = (1, 10); K_BONF = 21
COST_CELLS = {"fee_x1.25": "fee_rate.*.maker/taker × 1.25", "slip_x1.5": "slippage_vs_executor_mid.* × 1.5 (signed, as written)",
              "fill_x0.9": "first_leg p_full, p_part × 0.9 (mass → p_zero); completion.pi_fill × 0.9"}


# ───────────────────────── series ─────────────────────────
def series_from_path(Z, gm=GM):
    """one simulator path file (bt_launch PATH_*.npz) → the main-reading series"""
    nav0 = Z["nav0"]; den = gm * nav0
    s = dict(A=Z["A"].astype(np.int64), r=Z["navm1"] / Z["navm0"] - 1.0,
             pnl=1e4 * Z["price_trade"] / den, car=-1e4 * Z["funding"] / den, cst=1e4 * Z["fee"] / den,
             unk=1e4 * Z["unk_excluded"] * (Z["unk_price"] + Z["unk_funding"]) / den, tau=Z["turnover"] / den,
             dstop=Z["n_flatten_events"].astype(float), nstop=Z["n_stop_events"].astype(float), halt=(Z["status"] == 1).astype(float),
             hold=(Z["status"] == 2).astype(float), dust=Z["end_dust_usdt"] / den, unk_notional=Z["unk_notional"] / den,
             t5=int(Z["nav5_t0"]) + 300 * np.arange(len(Z["nav5_main"]), dtype=np.int64), nav5=Z["nav5_main"] / Z["nav5_main"][0])
    s["g"] = 1e4 * s["r"] / gm
    return s


def series_from_v2(Z, gm=GM):
    """stream R's v2 simulator ledger (SIM_*.npz; no 5-minute path, no UNKNOWN column)"""
    den = gm * Z["nav0"]
    s = dict(A=Z["A"].astype(np.int64), r=Z["nav1"] / Z["nav0"] - 1.0, pnl=1e4 * Z["price_trade"] / den, car=-1e4 * Z["funding"] / den,
             cst=1e4 * Z["fee"] / den, unk=np.zeros(len(Z["A"])), tau=Z["turnover"] / den, dstop=Z["n_flatten_events"].astype(float),
             nstop=Z["n_stop_events"].astype(float), halt=(Z["status"] == 1).astype(float), hold=(Z["status"] == 2).astype(float),
             dust=np.full(len(Z["A"]), np.nan), unk_notional=np.zeros(len(Z["A"])), t5=None, nav5=None)
    s["g"] = 1e4 * s["r"] / gm
    return s


def series_mean(paths, gm=GM):
    """the MEAN path over fill paths (list of series_from_path, seed order): per-window mean of r and of every component; 5-minute mean returns"""
    A = paths[0]["A"]
    for p in paths: assert np.array_equal(p["A"], A)
    s = dict(A=A)
    for k in ("r", "pnl", "car", "cst", "unk", "tau", "dstop", "nstop", "halt", "hold", "dust", "unk_notional", "g"):
        s[k] = np.stack([p[k] for p in paths]).mean(0)
    t5 = paths[0]["t5"]
    for p in paths: assert np.array_equal(p["t5"], t5)
    r5 = np.stack([p["nav5"][1:] / p["nav5"][:-1] - 1.0 for p in paths]).mean(0)
    s["t5"] = t5; s["nav5"] = np.concatenate([[1.0], np.cumprod(1.0 + r5)])
    return s


def g_identity_err(s):
    return float(np.max(np.abs(s["g"] - (s["pnl"] - s["car"] - s["cst"] - s["unk"])))) if len(s["g"]) else 0.0


# ───────────────────────── statistics ─────────────────────────
def daily(A, r):
    d = (np.asarray(A, np.int64) // DAY) * DAY
    ud, inv = np.unique(d, return_inverse=True); out = np.ones(len(ud)); np.multiply.at(out, inv, 1.0 + np.asarray(r, float))
    return ud, out - 1.0


def cagr(rd):
    rd = np.asarray(rd, float); n = len(rd)
    if n == 0: return None
    nav = np.cumprod(1.0 + rd)
    if np.any(nav <= 0): return -1.0
    return float(nav[-1] ** (365.0 / n) - 1.0)


def sharpe(rd):
    rd = np.asarray(rd, float)
    if len(rd) < 2: return None
    sd = rd.std(ddof=1)
    return float(rd.mean() / sd * math.sqrt(365.0)) if sd > 0 else None


def maxdd_nav(nav):
    nav = np.asarray(nav, float)
    if len(nav) == 0: return None
    return float((nav / np.maximum.accumulate(nav) - 1.0).min())


def maxdd_4h(r):
    return maxdd_nav(np.concatenate([[1.0], np.cumprod(1.0 + np.asarray(r, float))]))


def nav5_cell(s, mask):
    """the 5-minute NAV over the selected windows: each window's own 5-minute relative path appended (start point included once)"""
    if s.get("nav5") is None: return None
    A = s["A"][mask]
    if len(A) == 0: return None
    i0 = ((A - s["t5"][0]) // 300).astype(np.int64); i1 = i0 + H4 // 300
    if i1.max() >= len(s["nav5"]) or i0.min() < 0: return None
    level = 1.0; out = [1.0]
    for a, b in zip(i0, i1):
        seg = s["nav5"][a:b + 1] / s["nav5"][a]
        out.extend((level * seg[1:]).tolist()); level = level * seg[-1]
    return np.array(out)


def maxdd_5m(s, mask):
    n5 = nav5_cell(s, mask)
    return maxdd_nav(n5) if n5 is not None else None


def worst_30d(rd):
    rd = np.asarray(rd, float)
    if len(rd) < 30: return None
    L = np.concatenate([[0.0], np.cumsum(np.log1p(rd))])
    return float(np.expm1((L[30:] - L[:-30]).min()))


def cvar5(rd):
    rd = np.sort(np.asarray(rd, float))
    if len(rd) == 0: return None
    k = int(math.ceil(0.05 * len(rd)))
    return float(rd[:k].mean())


def pct(x, q):
    x = np.asarray([v for v in x if v is not None and np.isfinite(v)], float)
    return float(np.percentile(x, q)) if len(x) else None


# ───────────────────────── cells (§3.1 / §3.2 / §3.3) ─────────────────────────
def cell_metrics(s, mask, gm=GM):
    """the per-cell metric set of §3.1 (and §3.2 / §3.3 on the same series)"""
    mask = np.asarray(mask, bool); n = int(mask.sum())
    if n == 0: return {"n_anchors": 0}
    A = s["A"][mask]; r = s["r"][mask]; ud, rd = daily(A, r)
    o = {"n_anchors": n, "n_days": int(len(ud)), "first_anchor": int(A[0]), "last_anchor": int(A[-1]),
         "nav_return": float(np.prod(1.0 + r) - 1.0), "cagr": cagr(rd), "sharpe_daily": sharpe(rd),
         "maxdd_4h": maxdd_4h(r), "maxdd_5m": maxdd_5m(s, mask), "worst_30d": worst_30d(rd), "cvar5_daily": cvar5(rd),
         "g": float(s["g"][mask].mean()), "price": float(s["pnl"][mask].mean()), "funding_paid": float(s["car"][mask].mean()),
         "fee": float(s["cst"][mask].mean()), "unknown_excluded": float(s["unk"][mask].mean()), "turnover_over_gross": float(s["tau"][mask].mean()),
         "day_stop_flattens": float(s["dstop"][mask].sum()), "per_name_stops": float(s["nstop"][mask].sum()), "halt_anchors": float(s["halt"][mask].sum()),
         "hold_anchors": float(s["hold"][mask].sum()), "dust_over_gross_mean": (float(np.nanmean(s["dust"][mask])) if np.isfinite(s["dust"][mask]).any() else None),
         "unknown_notional_over_gross_mean": float(s["unk_notional"][mask].mean())}
    return o


def path_distribution(paths, mask, keys=("cagr", "sharpe_daily", "maxdd_4h", "maxdd_5m", "worst_30d", "cvar5_daily", "g", "nav_return")):
    per = [cell_metrics(p, mask) for p in paths]
    return {k: {"median": pct([m.get(k) for m in per], 50), "p05": pct([m.get(k) for m in per], 5), "p95": pct([m.get(k) for m in per], 95),
                "n_paths": len(per)} for k in keys}


def year_cells(A, full_recipe_start=None):
    """§3.1 periods (UTC): 2022H2 (partial recipe) · 2023 · 2024 (inside / outside the full-recipe window) · 2025 · 2026H1 · 2026-07-01 → end
    (describe only). Every anchor before full_recipe_start is labelled PARTIAL_RECIPE; a year crossing it is split."""
    A = np.asarray(A, np.int64); y = np.array([time.gmtime(int(t)).tm_year for t in A]); mo = np.array([time.gmtime(int(t)).tm_mon for t in A])
    frs = int(full_recipe_start) if full_recipe_start is not None else None
    base = {"2022H2": (y == 2022) & (mo >= 7) | ((y == 2022) & (mo == 6)), "2023": y == 2023, "2024": y == 2024, "2025": y == 2025,
            "2026H1": (y == 2026) & (mo <= 6), "2026-07-01→end": (y == 2026) & (mo >= 7)}
    out = {}
    for nm, m in base.items():
        if frs is None:
            out[nm] = {"mask": m, "partial_recipe": None, "describe_only": nm == "2026-07-01→end"}; continue
        pre = m & (A < frs); post = m & (A >= frs)
        if pre.any() and post.any():
            out[nm + " (PARTIAL_RECIPE, before full-recipe start)"] = {"mask": pre, "partial_recipe": True, "describe_only": nm == "2026-07-01→end"}
            out[nm + " (full recipe)"] = {"mask": post, "partial_recipe": False, "describe_only": nm == "2026-07-01→end"}
        elif pre.any():
            out[nm + " (PARTIAL_RECIPE)"] = {"mask": pre, "partial_recipe": True, "describe_only": nm == "2026-07-01→end"}
        else:
            out[nm] = {"mask": post, "partial_recipe": False, "describe_only": nm == "2026-07-01→end"}
    return out


# ───────────────────────── bootstrap ─────────────────────────
def mbb_indices(n, block, B=B_DEFAULT, seed=RNG_SEED):
    """moving-block bootstrap day indices, (B, n): non-circular, starts uniform on 0..n−block, ceil(n/block) blocks, truncated to n"""
    block = int(min(block, n)); k = int(math.ceil(n / block))
    rng = np.random.default_rng(list(seed))
    st = rng.integers(0, n - block + 1, size=(B, k))
    return (st[:, :, None] + np.arange(block)[None, None, :]).reshape(B, k * block)[:, :n]


def day_sums(A, x, days):
    """per-day sum and count of an anchor-level series on a fixed day axis"""
    d = (np.asarray(A, np.int64) // DAY) * DAY; pos = np.searchsorted(days, d); assert np.all(days[pos] == d)
    s = np.bincount(pos, weights=np.asarray(x, float), minlength=len(days)); c = np.bincount(pos, minlength=len(days)).astype(float)
    return s, c


def mean_ci(A, x, mask, days, block=BLOCK_MAIN, B=B_DEFAULT, seed=RNG_SEED, idx=None):
    """mean of an anchor-level series over a cell, CI from the MBB on the full day axis (days outside the cell contribute 0 / 0)"""
    mask = np.asarray(mask, bool); s, c = day_sums(A[mask], x[mask], days)
    if idx is None: idx = mbb_indices(len(days), block, B, seed)
    with np.errstate(all="ignore"): ms = s[idx].sum(1) / c[idx].sum(1)
    ms = ms[np.isfinite(ms)]
    return {"mean": float(x[mask].mean()), "ci95": [float(np.percentile(ms, 2.5)), float(np.percentile(ms, 97.5))],
            "ci_bonf": [float(np.percentile(ms, 100 * 0.025 / K_BONF)), float(np.percentile(ms, 100 * (1 - 0.025 / K_BONF)))], "n_draws_defined": int(len(ms))}, ms


def paired(sa, sb, block=BLOCK_MAIN, B=B_DEFAULT, seed=RNG_SEED, mask=None):
    """§3.5 / §3.6 paired estimator of a − b on the same windows: ΔSR, ΔCAGR (nonlinear, recomputed per draw) and Δg (linear)"""
    assert np.array_equal(sa["A"], sb["A"]), "series must share the window axis"
    m = np.ones(len(sa["A"]), bool) if mask is None else np.asarray(mask, bool)
    A = sa["A"][m]; da, ra = daily(A, sa["r"][m]); db, rb = daily(A, sb["r"][m]); assert np.array_equal(da, db)
    n = len(da); idx = mbb_indices(n, block, B, seed)
    est = {"d_sharpe": (sharpe(ra) or np.nan) - (sharpe(rb) or np.nan), "d_cagr": cagr(ra) - cagr(rb), "d_g": float((sa["g"][m] - sb["g"][m]).mean())}
    RA = ra[idx]; RB = rb[idx]
    def sr(R):
        sd = R.std(1, ddof=1); mu = R.mean(1); out = np.where(sd > 0, mu / np.where(sd > 0, sd, 1.0) * math.sqrt(365.0), np.nan); return out, int((sd <= 0).sum())
    sra, za = sr(RA); srb, zb = sr(RB)
    def cg(R):
        L = np.cumprod(1.0 + R, axis=1); fin = L[:, -1]; bad = (L <= 0).any(1)
        return np.where(bad, -1.0, np.abs(fin) ** (365.0 / n) - 1.0)
    dsr = sra - srb; dcg = cg(RA) - cg(RB)
    sg, cg_ = day_sums(A, sa["g"][m] - sb["g"][m], da); dgb = sg[idx].sum(1) / cg_[idx].sum(1)
    out = {"n_days": n, "block_days": block, "B": B, "rng": list(seed), "undefined_sharpe_draws": za + zb}
    for k, draws in (("d_sharpe", dsr), ("d_cagr", dcg), ("d_g", dgb)):
        x = draws[np.isfinite(draws)]; e = est[k]
        pu = (1 + int(np.sum(x - e >= e))) / (len(x) + 1); pd = (1 + int(np.sum(x - e <= e))) / (len(x) + 1)
        und = 1.0 - len(x) / B
        out[k] = {"estimate": float(e), "ci95": [float(np.percentile(x, 2.5)), float(np.percentile(x, 97.5))], "p_up": pu, "p_down": pd,
                  "label": ("UNAVAILABLE" if und > 0.01 else ("(A) better" if pu < 0.05 else ("(B) worse" if pd < 0.05 else "(C) undecidable"))),
                  "undefined_share": und}
    return out


# ───────────────────────── §3.2 regimes ─────────────────────────
LEVELS = ("low", "mid", "high")


def regime_cells(A, lab_ts, LAB, vars_):
    """21 masks from the G0 frozen labels (−1 = unlabelled): {var: {level: mask}}"""
    pos = {int(t): i for i, t in enumerate(np.asarray(lab_ts, np.int64))}
    ix = np.array([pos.get(int(a), -1) for a in A]); assert (ix >= 0).all(), "every window anchor needs a label row"
    L = np.asarray(LAB)[ix]
    return {v: {LEVELS[l]: L[:, j] == l for l in range(3)} for j, v in enumerate(vars_)}


def regime_table(s, cells, B=B_DEFAULT, seed=RNG_SEED):
    A = s["A"]; days = np.unique((A // DAY) * DAY); out = {}
    idx = {b: mbb_indices(len(days), b, B, seed) for b in (BLOCK_MAIN,) + BLOCK_SENS}
    for v, lv in cells.items():
        out[v] = {}
        for nm, m in lv.items():
            o = cell_metrics(s, m)
            if o["n_anchors"] == 0: out[v][nm] = o; continue
            if o["n_days"] < 2:
                o["ci"] = "single-day cell: describe only"; out[v][nm] = o; continue
            ci = {}
            for b in (BLOCK_MAIN,) + BLOCK_SENS:
                c, _ = mean_ci(A, s["g"], m, days, block=b, idx=idx[b]); ci[f"block_{b}d"] = c
            o["g_ci"] = ci
            main = ci[f"block_{BLOCK_MAIN}d"]
            o["mark"] = "††" if (main["ci_bonf"][0] > 0 or main["ci_bonf"][1] < 0) else ("†" if (main["ci95"][0] > 0 or main["ci95"][1] < 0) else "")
            out[v][nm] = o
    return out


# ───────────────────────── §3.6 reconciliation ─────────────────────────
def recon_step(name, before_mean, after_mean, before_paths=None, after_paths=None, block=BLOCK_MAIN, B=B_DEFAULT, seed=RNG_SEED):
    """Δ = after − before on the same windows (interaction terms land in the later step by construction)"""
    m = np.ones(len(before_mean["A"]), bool)
    mb = cell_metrics(before_mean, m); ma = cell_metrics(after_mean, m)
    o = {"step": name, "before": {k: mb[k] for k in ("cagr", "sharpe_daily", "maxdd_4h", "maxdd_5m", "g", "nav_return")},
         "after": {k: ma[k] for k in ("cagr", "sharpe_daily", "maxdd_4h", "maxdd_5m", "g", "nav_return")}}
    o["delta_point"] = {k: (ma[k] - mb[k]) if (ma[k] is not None and mb[k] is not None) else None for k in o["before"]}
    o["paired_bootstrap"] = {"main_5d": paired(after_mean, before_mean, block, B, seed)}
    for b in BLOCK_SENS: o["paired_bootstrap"][f"sens_{b}d"] = paired(after_mean, before_mean, b, B, seed)
    if after_paths:
        pa = [cell_metrics(p, m) for p in after_paths]
        if before_paths:
            assert len(before_paths) == len(after_paths)
            pb = [cell_metrics(p, m) for p in before_paths]; pairing = "paired by fill seed"
        else:
            pb = [mb] * len(pa); pairing = "each after-path vs the single before path"
        o["per_fill_path_delta"] = {"pairing": pairing}
        for k in ("cagr", "sharpe_daily", "maxdd_4h", "maxdd_5m", "g"):
            d = [(x[k] - y[k]) if (x.get(k) is not None and y.get(k) is not None) else None for x, y in zip(pa, pb)]
            o["per_fill_path_delta"][k] = {"median": pct(d, 50), "p05": pct(d, 5), "p95": pct(d, 95), "n": len([v for v in d if v is not None])}
    return o


def telescoping_ok(steps, first_before, last_after, keys=("cagr", "sharpe_daily", "maxdd_4h", "g")):
    tot = {k: last_after[k] - first_before[k] for k in keys}
    s = {k: sum(st["delta_point"][k] for st in steps) for k in keys}
    return {k: abs(tot[k] - s[k]) for k in keys}


# ───────────────────────── CLI: steps ① and ② only ─────────────────────────
def load_run_dir(d, R=32):
    files = sorted(f for f in os.listdir(d) if f.startswith("PATH_") and f.endswith(".npz"))
    assert len(files) == R, f"{d}: {len(files)} path files, expected {R}"
    return [series_from_path(np.load(os.path.join(d, f))) for f in files], files


def _sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


def main_recon(argv):
    v2 = {"s42": argv[0], "s2027": argv[1]}; old = {"s42": argv[2], "s2027": argv[3]}; raw = {"s42": argv[4], "s2027": argv[5]}; outp = argv[6]
    rec = {"device": "bt_tables.py", "self_sha256": _sha(os.path.abspath(__file__)), "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "object": "P2-CMB (stream R's S2 production-path target book, S2_A0pred = in-service recipe arm) — NOT the certified production path (object B)",
           "prereg": "docs/PREREG_baseline_tables_certified_2026-09-19.md §3.6 steps ① and ② only (③ waits for object B)", "steps": {}, "inputs": {}}
    for seed in ("s42", "s2027"):
        Z2 = np.load(v2[seed]); s_v2 = series_from_v2(Z2); rec["inputs"][f"v2_{seed}"] = {"path": v2[seed], "sha256": _sha(v2[seed])}
        po, fo = load_run_dir(old[seed]); pr, fr = load_run_dir(raw[seed])
        rec["inputs"][f"v31_old_{seed}"] = {"dir": old[seed], "files": fo}; rec["inputs"][f"v31_raw_{seed}"] = {"dir": raw[seed], "files": fr}
        mo = series_mean(po); mr = series_mean(pr)
        for nm, s in (("v2", s_v2), ("v31_old_mean", mo), ("v31_raw_mean", mr)):
            assert np.array_equal(s["A"], s_v2["A"]), nm
        idn = {"v31_old_paths_max_g_identity_err": max(g_identity_err(p) for p in po), "v31_raw_paths_max_g_identity_err": max(g_identity_err(p) for p in pr)}
        s1 = recon_step("① simulator v2 → v3.1 (old stream-R prices, UNAVAILABLE as v2: LEGACY-ZERO-RETURN)", s_v2, mo, None, po)
        s2 = recon_step("② v3.1 old prices → v3.1 restored raw prices (UNAVAILABLE rule UA-FREEZE-EXCLUDE)", mo, mr, po, pr)
        tel = telescoping_ok([s1, s2], s1["before"], s2["after"])
        rec["steps"][seed] = {"step1": s1, "step2": s2, "telescoping_abs_err": tel, "identity": idn,
                              "v31_old_mean_full": cell_metrics(mo, np.ones(len(mo["A"]), bool)), "v31_raw_mean_full": cell_metrics(mr, np.ones(len(mr["A"]), bool)),
                              "v2_full": cell_metrics(s_v2, np.ones(len(s_v2["A"]), bool)),
                              "path_distribution_old": path_distribution(po, np.ones(len(mo["A"]), bool)),
                              "path_distribution_raw": path_distribution(pr, np.ones(len(mr["A"]), bool))}
    json.dump(rec, open(outp + ".tmp", "w"), indent=1, default=float); os.replace(outp + ".tmp", outp)
    print("BT_TABLES recon written", outp, _sha(outp))


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "recon":
        main_recon(sys.argv[2:])
    else:
        print(__doc__)
