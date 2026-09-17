#!/usr/bin/env python3
"""fp2_per_year_table.py — FP2-8 §4 / AMENDMENT 4 (2026-09-17): the per-year table of the live form (A0) and the candidate (A1) from the SAME arm records the
judge reads (probe_artifacts/w10_ablation_series_V4_<ARM>_<seat>_s<seed>.npz, book variant d30_n2_c42 = per-name stop), RAW accounting, both arms under the
same evaluation umask. Formulas are r18_judge.py's, verbatim in meaning:
  g = net_ex / gross_total (bps per anchor per unit gross, net of fees and carry); pnl/carry/cost likewise per unit gross; tau_raw = turnover
  windows: W_FULL = ts <= UB; W_ALPHA = W_FULL minus the first 900 anchors (LOOK warm-up); KING_LIVE = W_ALPHA & ts >= 2024-01-01; YEAR = UTC year
  Sharpe (a) anchor: mean/std(ddof=1)*sqrt(2190)   (b) daily: UTC-day compounded returns at L=1, mean/std*sqrt(365)   (None when std == 0 or n <= 30)
  CI95: UTC-day block bootstrap, NB=2000 draws, default_rng([20260905, k]) (paired for Δ on the same anchors)
  maxDD: NAV_t = Π(1 + L·g·1e-4) over UTC days at L = LEV (default 2.0 = the live gross), min(NAV/cummax − 1) within the window
Three-state: every requested arm×seat×seed file must load and pass the config assertions, else that cell is UNAVAILABLE (recorded) and rc 3.
env: ARMS_DIR OUT_JSON OUT_MD [UMASK_NPZ] [ARMS=A0,A1] [SEATS=dyn,fix] [SEEDS=42,2027] [LEV=2.0] [UB=2026-08-30T20:00:00Z]"""
import calendar, hashlib, json, os, sys, time
import numpy as np
NB = 2000
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()
def load(p, seat, seed=None):
    Z = np.load(p, allow_pickle=True); C = [str(c) for c in Z["cols"]]; rec = np.asarray(Z["d30_n2_c42_rec"], float); cfg = json.loads(str(Z["config_json"]))
    why = []
    for k, v in (("CAL", "log"), ("PHI", 0.45), ("LEGS", "101"), ("WRULE", "msharpe"), ("UMASK_SCOPE", "m1"), ("LOOK", 900), ("FTRIM", "zero"), ("MEMBERS_TOPN", 829)):
        if cfg.get(k) != v: why.append(f"cfg {k}={cfg.get(k)!r} != {v!r}")
    if seat == "dyn" and cfg.get("W3FIX") is not None: why.append(f"dyn seat with W3FIX={cfg.get('W3FIX')!r}")
    if seat == "fix" and cfg.get("W3FIX") != "0.21,0,0.79": why.append(f"fix seat W3FIX={cfg.get('W3FIX')!r} != '0.21,0,0.79'")
    col = lambda k: rec[:, C.index(k)]
    ts = col("ts").astype(np.int64); gt = col("gross_total")
    d = dict(ts=ts, gt=gt, g=col("net_ex") / gt, pnl=col("pnl_ex") / gt, car=col("carry_ex") / gt, cst=col("cost_ex") / gt, tau_raw=col("turnover"), nl=col("netlong"),
             cfg={k: cfg.get(k) for k in ("UMASK_NPZ", "COSTB_JSON", "SLOW_NPY", "FPRED", "FSEED", "W3FIX", "FEMAT_NPZ")}, sha=sha(p), path=p, why=why)
    if not np.allclose(d["pnl"] - d["car"] - d["cst"], d["g"], atol=1e-9): why.append("pnl - carry - cost != g")
    if (np.diff(ts) <= 0).any(): why.append("ts not increasing")
    for k in ("g", "pnl", "car", "cst", "tau_raw", "nl"):      # R05 (review round 2): an Inf/NaN return cell must make the arm UNAVAILABLE, never flow into a mean/CI
        nb = int((~np.isfinite(d[k])).sum())
        if nb: why.append(f"{k} not finite on {nb} rows")
    if seed is not None and str(cfg.get("FSEED")) != str(seed): why.append(f"cfg FSEED={cfg.get('FSEED')!r} != file-name seed {seed!r}")   # R08: the seed is a fact of the record, not of the file name
    d["W"] = np.asarray(Z["d30_n2_c42_W"], np.float32) if "d30_n2_c42_W" in Z.files else None; d["symbols"] = [str(s) for s in Z["symbols"]] if "symbols" in Z.files else None
    return d
_DRAW = {}
def draws(nd):
    if nd not in _DRAW: _DRAW[nd] = np.stack([np.random.default_rng([20260905, k]).integers(0, nd, nd) for k in range(NB)])
    return _DRAW[nd]
def boot(d, mask, DAY):
    idx = np.nonzero(mask)[0]
    if len(idx) == 0: return None
    dd = {}
    for k in idx: dd.setdefault(DAY[k], []).append(k)
    keys = sorted(dd); tot = np.array([d[dd[k]].sum() for k in keys]); cnt = np.array([len(dd[k]) for k in keys], float); nd = len(keys)
    r = draws(nd); ms = tot[r].sum(1) / cnt[r].sum(1)
    return dict(ci95=[float(np.percentile(ms, 2.5)), float(np.percentile(ms, 97.5))], se=float(ms.std(ddof=1)), n_days=nd)
def shp(x): return (float(x.mean() / x.std(ddof=1) * np.sqrt(2190)) if len(x) > 30 and x.std(ddof=1) > 0 else None)
def dayret(g, mask, L, DAYS):
    idx = np.nonzero(mask)[0]; ud, inv = np.unique(DAYS[idx], return_inverse=True); out = np.ones(len(ud)); np.multiply.at(out, inv, 1.0 + L * g[idx] * 1e-4); return ud, out - 1.0
def maxdd_daily(g, mask, L, DAYS):
    if not mask.any(): return None
    _, rd = dayret(g, mask, L, DAYS); nav = np.concatenate([[1.0], np.cumprod(1.0 + rd)]); return float((nav / np.maximum.accumulate(nav) - 1.0).min())
def maxdd_anchor(g, mask, L):
    """F09 (independent review 2026-09-17): the drawdown the design promised — NAV compounded PER ANCHOR at leverage L, min(NAV/cummax − 1).
    Day-end sampling hides intra-day losses (1 → 1.1 → 1 within one day shows 0% daily, −9.09% per anchor)."""
    if not mask.any(): return None
    nav = np.concatenate([[1.0], np.cumprod(1.0 + L * g[mask] * 1e-4)]); return float((nav / np.maximum.accumulate(nav) - 1.0).min())
def sharpe_daily(g, mask, DAYS):
    if mask.sum() <= 30: return None
    _, rd = dayret(g, mask, 1.0, DAYS); return float(rd.mean() / rd.std(ddof=1) * np.sqrt(365)) if len(rd) > 30 and rd.std(ddof=1) > 0 else None
def level(x, mask, DAY, DAYS, LEV):
    n = int(mask.sum())
    if n == 0: return dict(n=0)
    g = x["g"][mask]; b = boot(x["g"], mask, DAY)
    return dict(n=n, g=float(g.mean()), ci95=b["ci95"], se_boot=b["se"], n_days=b["n_days"], sharpe_anchor=shp(g), sharpe_daily=sharpe_daily(x["g"], mask, DAYS), maxdd_L=maxdd_anchor(x["g"], mask, LEV), maxdd_L_dayend=maxdd_daily(x["g"], mask, LEV, DAYS),
                pnl=float(x["pnl"][mask].mean()), carry=float(x["car"][mask].mean()), cost=float(x["cst"][mask].mean()), tau_raw=float(x["tau_raw"][mask].mean()), gross_total=float(x["gt"][mask].mean()), netlong=float(x["nl"][mask].mean()))
def delta(a, b, mask, DAY):
    n = int(mask.sum())
    if n == 0: return dict(n=0)
    d = a["g"] - b["g"]; bb = boot(d, mask, DAY)
    o = dict(n=n, dg=float(d[mask].mean()), ci95=bb["ci95"], se_boot=bb["se"], n_days=bb["n_days"], dpnl=float((a["pnl"] - b["pnl"])[mask].mean()), dcarry=float((a["car"] - b["car"])[mask].mean()), dcost=float((a["cst"] - b["cst"])[mask].mean()),
             dtau_raw=float((a["tau_raw"] - b["tau_raw"])[mask].mean()), n_anchors_g_differs=int((np.abs(d[mask]) > 1e-12).sum()))
    o["ci95_excl0"] = bool(o["ci95"][0] > 0 or o["ci95"][1] < 0); return o
def mask_stats(x, um):
    if x["W"] is None or um is None: return None
    mts = um["ts"].astype(np.int64); row = {int(t): i for i, t in enumerate(mts)}; M = np.asarray(um["mask"]); rows = [row.get(int(t)) for t in x["ts"]]
    ok = [i for i, r in enumerate(rows) if r is not None]; Wsub = x["W"][ok]; Msub = M[[rows[i] for i in ok]]
    return dict(anchors_with_mask_row=len(ok), anchors_total=int(len(x["ts"])), traded_cells=int((np.abs(Wsub) > 0).sum()), traded_cells_outside_mask=int(((np.abs(Wsub) > 0) & ~Msub).sum()), mask_true_cells=int(Msub.sum()))
def main():
    E = {k: os.environ.get(k, "") for k in ("ARMS_DIR", "OUT_JSON", "OUT_MD", "UMASK_NPZ", "ARMS", "SEATS", "SEEDS", "LEV", "UB", "WA_START")}
    if not (E["ARMS_DIR"] and E["OUT_JSON"] and E["OUT_MD"]): print("REFUSED env ARMS_DIR/OUT_JSON/OUT_MD required", flush=True); return 3
    ARMS = (E["ARMS"] or "A0,A1").split(","); SEATS = (E["SEATS"] or "dyn,fix").split(","); SEEDS = (E["SEEDS"] or "42,2027").split(","); LEV = float(E["LEV"] or 2.0)
    UB = calendar.timegm(time.strptime(E["UB"] or "2026-08-30T20:00:00Z", "%Y-%m-%dT%H:%M:%SZ")); K24 = calendar.timegm((2024, 1, 1, 0, 0, 0))
    rec = {"device": os.path.basename(__file__), "self_sha256": sha(os.path.abspath(__file__)), "utc": time.strftime("%FT%TZ", time.gmtime()), "env": E, "numpy": np.__version__,
           "formulas": {"g": "net_ex/gross_total bps per anchor per unit gross", "sharpe_anchor": "mean/std*sqrt(2190)", "sharpe_daily": "UTC-day compounded L=1, mean/std*sqrt(365)", "ci95": "UTC-day block bootstrap NB=2000 rng([20260905,k])",
                        "maxdd_L": f"NAV=prod(1+L*g*1e-4) PER ANCHOR, L={LEV} (primary; F09)", "maxdd_L_dayend": "same NAV sampled at UTC day ends (secondary)", "W_ALPHA": "ts<=UB minus first 900 anchors", "KING_LIVE": "W_ALPHA & ts>=2024-01-01", "variant": "d30_n2_c42"}, "arms": {}, "delta": {}, "UNAVAILABLE": []}
    um = None
    if E["UMASK_NPZ"]:
        um = np.load(E["UMASK_NPZ"], allow_pickle=True); rec["umask"] = {"path": E["UMASK_NPZ"], "sha256": sha(E["UMASK_NPZ"]), "definition": str(um["definition"]) if "definition" in um.files else None}
    X = {}
    for arm in ARMS:
        for seat in SEATS:
            for s in SEEDS:
                p = os.path.join(E["ARMS_DIR"], f"w10_ablation_series_V4_{arm}_{seat}_s{s}.npz"); key = f"{arm}/{seat}/s{s}"
                if not os.path.isfile(p): rec["UNAVAILABLE"].append({key: "file missing: " + p}); continue
                try: x = load(p, seat, seed=s)
                except Exception as e: rec["UNAVAILABLE"].append({key: f"load error: {e!r}"}); continue   # noqa: BLE001
                if x["why"]: rec["UNAVAILABLE"].append({key: x["why"]}); continue
                X[key] = x
    if not X: rec["VERDICT"] = "UNAVAILABLE"; json.dump(rec, open(E["OUT_JSON"], "w"), indent=1, default=str); open(E["OUT_MD"], "w").write("# FP2 per-year table — UNAVAILABLE (no arm loaded)\n" + json.dumps(rec["UNAVAILABLE"], indent=1)); print("UNAVAILABLE", rec["UNAVAILABLE"]); return 3
    ts0 = next(iter(X.values()))["ts"]
    sym0 = next(iter(X.values()))["symbols"]; um0 = next(iter(X.values()))["cfg"].get("UMASK_NPZ")
    def _fsha(p):
        try: return sha(p) if p and os.path.isfile(p) else None
        except Exception: return None   # noqa: BLE001
    um_sha0 = _fsha(um0); rec["arm_umask"] = {"path": um0, "sha256": um_sha0}
    for k, x in list(X.items()):
        why = []
        if not np.array_equal(x["ts"], ts0): why.append("ts axis differs from the first arm")
        if x["symbols"] is None or sym0 is None or x["symbols"] != sym0: why.append("symbols axis missing or differs")
        if x["cfg"].get("UMASK_NPZ") != um0: why.append(f"UMASK_NPZ differs across arms ({x['cfg'].get('UMASK_NPZ')} vs {um0})")
        if um_sha0 is None: why.append("arm umask file not readable for identity (UMASK_NPZ path)")
        elif _fsha(x["cfg"].get("UMASK_NPZ")) != um_sha0: why.append("umask file sha differs across arms")
        if E["UMASK_NPZ"] and um_sha0 and rec.get("umask") and rec["umask"]["sha256"] != um_sha0: why.append("arm umask sha != contract UMASK_NPZ sha")
        gt = x["gt"]
        if not (np.isfinite(gt).all() and (gt > 0).all()): why.append(f"gross_total not finite-positive on {int((~(np.isfinite(gt) & (gt > 0))).sum())} rows")
        if (np.diff(x["ts"]) != 14400).any(): why.append("ts is not a gap-free 4h grid")
        if um is not None:   # R08: the mask is bound by its ORDERED symbol axis and must cover every anchor — a file hash alone proves neither
            msy = [str(v) for v in um["symbols"]]
            if msy != x["symbols"]: why.append("umask symbols axis != arm symbols axis (order matters)")
            mrow = set(um["ts"].astype(np.int64).tolist()); nomask = int(sum(1 for t in x["ts"] if int(t) not in mrow))
            if nomask: why.append(f"umask has no row for {nomask} of {len(x['ts'])} anchors")
        if why: rec["UNAVAILABLE"].append({k: why}); X[k] = None
    X = {k: v for k, v in X.items() if v is not None}
    if not X: rec["VERDICT"] = "UNAVAILABLE"; json.dump(rec, open(E["OUT_JSON"], "w"), indent=1, default=str); open(E["OUT_MD"], "w").write("# FP2 per-year table — UNAVAILABLE (no arm passed the input gates)\n" + json.dumps(rec["UNAVAILABLE"], indent=1, default=str)); print("UNAVAILABLE", rec["UNAVAILABLE"]); return 3
    ts = ts0; DAY = np.array([time.strftime("%Y%m%d", time.gmtime(int(t))) for t in ts]); DAYS = (ts // 86400) * 86400; YEAR = np.array([time.gmtime(int(t)).tm_year for t in ts])
    WT = ts <= UB; WA = WT.copy(); WA[:900] = False; KL = WA & (ts >= K24); years = sorted(set(YEAR[WA].tolist()))
    WA_START = calendar.timegm(time.strptime(E.get("WA_START") or "2022-06-30T00:00:00Z", "%Y-%m-%dT%H:%M:%SZ"))   # F10: W_ALPHA is pinned to a TIME, not to "row 900 of whatever axis"
    if int(ts[900]) != WA_START:
        rec["VERDICT"] = "UNAVAILABLE"; rec["UNAVAILABLE"].append({"W_ALPHA": f"ts[900]={time.strftime('%FT%TZ', time.gmtime(int(ts[900])))} != pinned start {time.strftime('%FT%TZ', time.gmtime(WA_START))}"})
        json.dump(rec, open(E["OUT_JSON"], "w"), indent=1, default=str); open(E["OUT_MD"], "w").write("# FP2 per-year table — UNAVAILABLE (W_ALPHA start not on the pinned time)\n"); print("UNAVAILABLE W_ALPHA start"); return 3
    rec["coverage"] = {"ts_min": time.strftime("%FT%TZ", time.gmtime(int(ts[0]))), "ts_max": time.strftime("%FT%TZ", time.gmtime(int(ts[-1]))), "UB": time.strftime("%FT%TZ", time.gmtime(UB)), "reaches_UB": bool(int(ts[-1]) >= UB),
                       "WA_START": time.strftime("%FT%TZ", time.gmtime(WA_START)), "n_anchors": int(len(ts)), "n_W_ALPHA": int(WA.sum()), "n_KING_LIVE": int(KL.sum()), "years": [str(y) for y in years]}
    if not rec["coverage"]["reaches_UB"]:   # R06: a table whose data end before the frozen upper bound cannot say anything about the missing tail (e.g. a missing 2026)
        rec["VERDICT"] = "UNAVAILABLE"; rec["UNAVAILABLE"].append({"coverage": f"last anchor {rec['coverage']['ts_max']} < frozen UB {rec['coverage']['UB']}"})
        json.dump(rec, open(E["OUT_JSON"], "w"), indent=1, default=str); open(E["OUT_MD"], "w").write("# FP2 per-year table — UNAVAILABLE (data end before the frozen upper bound)\n" + json.dumps(rec["coverage"], indent=1)); print("UNAVAILABLE coverage", rec["coverage"]); return 3
    rec["windows"] = {"n_anchors": int(len(ts)), "W_FULL": int(WT.sum()), "W_ALPHA": int(WA.sum()), "KING_LIVE": int(KL.sum()), "years": years, "first_anchor_utc": time.strftime("%FT%TZ", time.gmtime(int(ts[0]))), "last_anchor_utc": time.strftime("%FT%TZ", time.gmtime(int(ts[-1])))}
    for k, x in X.items():
        rec["arms"][k] = {"path": x["path"], "sha256": x["sha"], "cfg": x["cfg"], "mask_stats": mask_stats(x, um), "W_ALPHA": level(x, WA, DAY, DAYS, LEV), "KING_LIVE": level(x, KL, DAY, DAYS, LEV),
                          "by_year": {str(y): level(x, WA & (YEAR == y), DAY, DAYS, LEV) for y in years}}
    for seat in SEATS:
        for s in SEEDS:
            a, b = X.get(f"A1/{seat}/s{s}"), X.get(f"A0/{seat}/s{s}")
            if a is None or b is None: rec["UNAVAILABLE"].append({f"delta/{seat}/s{s}": "needs both A1 and A0"}); continue
            rec["delta"][f"A1-A0/{seat}/s{s}"] = {"W_ALPHA": delta(a, b, WA, DAY), "KING_LIVE": delta(a, b, KL, DAY), "by_year": {str(y): delta(a, b, WA & (YEAR == y), DAY) for y in years}}
    rec["VERDICT"] = "PASS" if not rec["UNAVAILABLE"] else "PARTIAL"
    json.dump(rec, open(E["OUT_JSON"], "w"), indent=1, default=str)
    f = lambda v, d=4: ("%+." + str(d) + "f") % v if isinstance(v, (int, float)) and v is not None else "—"
    L = [f"# FP2-8 per-year table (RAW caliber, variant d30_n2_c42, L={LEV}; rendered by fp2_per_year_table.py {rec['self_sha256'][:8]}; VERDICT {rec['VERDICT']})", "",
         f"windows: anchors {rec['windows']['n_anchors']} · W_ALPHA {rec['windows']['W_ALPHA']} · KING_LIVE {rec['windows']['KING_LIVE']} · {rec['windows']['first_anchor_utc']} → {rec['windows']['last_anchor_utc']}" + (f" · umask {rec['umask']['sha256'][:8]}" if um is not None else ""), ""]
    for k in sorted(X):
        r = rec["arms"][k]; L += [f"## {k}  (file {r['sha256'][:8]}; UMASK {os.path.basename(str(r['cfg']['UMASK_NPZ']))}; FPRED {r['cfg']['FPRED']}; SLOW {os.path.basename(str(r['cfg']['SLOW_NPY']))})", "",
                                 "| window | n | g bps/anchor | CI95 | Sharpe(anchor √2190) | Sharpe(daily √365) | maxDD@L 逐锚 | maxDD@L 日末 | pnl / carry / cost | τ raw | netlong |", "|---|---|---|---|---|---|---|---|---|---|---|"]
        for w in ["W_ALPHA", "KING_LIVE"] + [str(y) for y in years]:
            v = r["by_year"].get(w) if w.isdigit() else r[w]
            if not v or v.get("n", 0) == 0: L.append(f"| {w} | 0 | — | — | — | — | — | — | — | — | — |"); continue
            L.append(f"| {w} | {v['n']} | {f(v['g'])} | [{f(v['ci95'][0],3)}, {f(v['ci95'][1],3)}] | {f(v['sharpe_anchor'],3) if v['sharpe_anchor'] is not None else '—'} | {f(v['sharpe_daily'],3) if v['sharpe_daily'] is not None else '—'} | {('%.2f%%' % (100*v['maxdd_L'])) if v['maxdd_L'] is not None else '—'} | {('%.2f%%' % (100*v['maxdd_L_dayend'])) if v.get('maxdd_L_dayend') is not None else '—'} | {f(v['pnl'],3)} / {f(v['carry'],3)} / {f(v['cost'],3)} | {v['tau_raw']:.4f} | {f(v['netlong'],3)} |")
        if r["mask_stats"]: L.append(f"\nmask: traded cells {r['mask_stats']['traded_cells']}, outside umask {r['mask_stats']['traded_cells_outside_mask']} (scope m1: the mask shrinks the member/rank base and does not zero holdings — positions unwinding after a name left the tradable set; P&L share measured in OUTSIDE_MASK_PNL receipt), anchors with mask row {r['mask_stats']['anchors_with_mask_row']}/{r['mask_stats']['anchors_total']}")
        L.append("")
    for k in sorted(rec["delta"]):
        r = rec["delta"][k]; L += [f"## Δ {k} (paired, same anchors)", "", "| window | n | Δg | CI95 | excl 0 | Δpnl / Δcarry / Δcost | Δτ raw | anchors differ |", "|---|---|---|---|---|---|---|---|"]
        for w in ["W_ALPHA", "KING_LIVE"] + [str(y) for y in years]:
            v = r["by_year"].get(w) if w.isdigit() else r[w]
            if not v or v.get("n", 0) == 0: L.append(f"| {w} | 0 | — | — | — | — | — | — |"); continue
            L.append(f"| {w} | {v['n']} | {f(v['dg'])} | [{f(v['ci95'][0],3)}, {f(v['ci95'][1],3)}] | {'yes' if v['ci95_excl0'] else 'no'} | {f(v['dpnl'],3)} / {f(v['dcarry'],3)} / {f(v['dcost'],3)} | {v['dtau_raw']:+.4f} | {v['n_anchors_g_differs']} |")
        L.append("")
    if rec["UNAVAILABLE"]: L += ["## UNAVAILABLE", ""] + [f"- {json.dumps(u, default=str)}" for u in rec["UNAVAILABLE"]] + [""]
    open(E["OUT_MD"], "w").write("\n".join(L)); print(rec["VERDICT"], "arms", sorted(X), "unavailable", len(rec["UNAVAILABLE"]), "->", E["OUT_MD"], flush=True)
    return 0 if rec["VERDICT"] == "PASS" else 3
if __name__ == "__main__":
    sys.exit(main())
