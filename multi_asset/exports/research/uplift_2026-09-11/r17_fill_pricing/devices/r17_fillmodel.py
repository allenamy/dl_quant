#!/usr/bin/env python3
"""r17_fillmodel.py — STEP 1 of PREREG_r17 (§2): the fill model from the LIVE ledger, read-only.

Unit = (rebalance_id, symbol) group of orders.jsonl rows. I = |intended_full| of the maker attempt-1 row;
F = sum |filled_notional| over maker + topup_taker rows; f = min(F/I, 1). Features: direction class from
(prev_w, target_w); liquidity tier from v4-lineage qvk (j1_slice x0910; rolling.npz only past 09-10 00Z after
an overlap check); participation p = I / qv4h. Tables T1 (class x tier) and T2 (class x tier x p-tercile),
notional-weighted f_w = sum F / sum I (the quantity the replay uses) and unweighted. Calibration (in-sample +
odd/even UTC-day holdout), one L2 fractional-logistic check, adverse-selection conditional, dust rule, era split.

READ-ONLY on ~/dl_quant_live and ~/wide_shadow. ENV WHITELIST = EXPLICITLY EMPTY (asserted). PREREG sha asserted.
"""
import os, sys, json, time, hashlib, math, calendar
from collections import defaultdict, Counter

_FORBIDDEN = ["LEGS", "PHI", "CAL", "MEMBERS_TOPN", "COSTB_JSON", "PANEL_IN", "V2", "OUT_TAG", "W3FIX", "FTRIM", "UMASK_SCOPE",
              "SLOW_NPY", "FPRED", "FSEED", "LOOK", "WRULE", "TRADE_TOPN", "UMASK_NPZ", "SHADOW_OFFSET_MIN", "RNSM", "FTPOS", "LTRIM_TH", "CDAMP"]
_present = sorted(k for k in _FORBIDDEN if k in os.environ); assert _present == [], f"E-0826-D: caliber flags present: {_present}"
ENV_WHITELIST = []
import numpy as np
def _no_env(*a, **k): raise AssertionError("r17_fillmodel ENV WHITELIST is EMPTY: this device reads no environment variable")
os.environ.get = _no_env

ROOT = "/Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/uplift_2026-09-11"
R = ROOT + "/r17_fill_pricing"
PREREG = R + "/PREREG_r17_fill_pricing_2026-09-12.md"; PREREG_SHA = "a7533b922c68e6dc575b1eadd3d19f62d4d271393ec5d58621c31aa65f5ae272"
AMEND1 = R + "/PREREG_AMENDMENT_1_r17_2026-09-12.md"; AMEND1_SHA = "70c8142ac4595fb4e83659daaa83cd3a68ba1284f103fd77ba3a14ba3f3269bd"
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 22), b""): h.update(c)
    return h.hexdigest()
assert sha(PREREG) == PREREG_SHA, sha(PREREG)
assert sha(AMEND1) == AMEND1_SHA, sha(AMEND1)
SELF_SHA = sha(os.path.abspath(__file__))
LIVE = "/Users/haosiyu/dl_quant_live/state/live/pilot_log"
XINFO = "/Users/haosiyu/dl_quant_live/state/live/exchange_info_cache.json"
CACHE = "/Users/haosiyu/wide_shadow/state/rolling.npz"
SHADOW_CFG = "/Users/haosiyu/wide_shadow/shadow_bundle/config.json"
SLICE = ROOT + "/judge1_r6/j1_slice.npz"
G_USDT = 232000.0; NMIN = 30; NB = 2000; BOOT_SEED = 20260905
T_ERA_B = 1787716800; T_ERA_C = calendar.timegm((2026, 9, 3, 0, 0, 0)); T_SLICE_END = calendar.timegm((2026, 9, 10, 0, 0, 0))
READ_UTC = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
RC = dict(self_sha256=SELF_SHA, prereg_sha256=PREREG_SHA, amendment1_sha256=AMEND1_SHA, env_whitelist=ENV_WHITELIST, env_whitelist_declared="EXPLICITLY EMPTY SET (asserted at runtime)",
          read_utc=READ_UTC, inputs={}, gates={}, notes=[])

# ------------------------------------------------------------------ inputs
days = sorted(x for x in os.listdir(LIVE) if x.isdigit())
ORD = []; ANCH = {}; n_ord_rows = 0
for dd in days:
    p = f"{LIVE}/{dd}/orders.jsonl"
    if os.path.exists(p):
        for ln in open(p): ORD.append(json.loads(ln)); n_ord_rows += 1
    p = f"{LIVE}/{dd}/anchors.jsonl"
    if os.path.exists(p):
        for ln in open(p):
            r = json.loads(ln); ts = r.get("anchor_ts")
            if ts is None: continue
            mid = r.get("mid_at_anchor_vector")
            if isinstance(mid, str): mid = json.loads(mid)
            ANCH[float(ts)] = dict(mid=mid or {}, target_gross=r.get("target_gross"), realized_gross=r.get("realized_gross"), opening_halted=r.get("opening_halted"))
XI = json.load(open(XINFO)); FLOOR = {s: float(d["min_notional"]) for s, d in XI.items() if isinstance(d, dict) and d.get("min_notional") is not None}
RC["inputs"] = dict(days=[days[0], days[-1]], n_days=len(days), orders_rows=n_ord_rows, anchors_rows=len(ANCH), exchange_info_cache=dict(path=XINFO, sha256=sha(XINFO), n_symbols=len(FLOOR), floor_hist=dict(Counter(FLOOR.values()))),
                    slice=dict(path=SLICE, sha256=sha(SLICE)), cache=dict(path=CACHE, sha256=sha(CACHE), lineage="LIVE-CACHE (rolling.npz), used ONLY for anchors > 2026-09-10 00Z after the overlap check (PREREG §2.3)"),
                    ledger_note="orders.jsonl anchor_ts is a WALL-CLOCK FLOAT; canonical anchor E = round(anchor_ts/14400)*14400 (asserted |anchor_ts-E| < 3600)")
# qvk (v4 lineage) from the r6 slice
Z = np.load(SLICE, allow_pickle=True); STS = Z["ts"].astype(np.int64); SSYM = [str(s) for s in Z["symbols"]]; SQVK = np.asarray(Z["qvk"], np.float64)
sidx = {s: i for i, s in enumerate(SSYM)}; srow = {int(t): i for i, t in enumerate(STS)}
# rolling cache (channel 3 = log1p quote volume, shadow_loop_v3.bars_to_channels L246)
zc = np.load(CACHE, allow_pickle=True); CTS = zc["ts"].astype(np.int64); LQV = np.asarray(zc["data"][:, :, 3], np.float64); del zc
cfg = json.load(open(SHADOW_CFG)); PSYM = [str(s) for s in cfg["symbols_panel"]]; assert PSYM == SSYM, "cache symbols != slice symbols"
assert (np.diff(CTS) == 300).all()
QVe = np.where(np.isfinite(LQV), np.expm1(np.clip(LQV, 0, 30)), np.nan); crow = {int(t): i for i, t in enumerate(CTS)}
def qv4h_cache(E, j):
    """sum of 48 five-minute quote volumes over bars closing in (E-4h, E]; NaN if < 40 finite."""
    i1 = crow.get(int(E))
    if i1 is None: return np.nan
    i0 = i1 - 47
    if i0 < 0: return np.nan
    v = QVe[i0:i1 + 1, j]; fin = np.isfinite(v)
    return float(v[fin].sum()) if fin.sum() >= 40 else np.nan
def qv4h_slice(E, j):
    r = srow.get(int(E))
    if r is None: return np.nan
    q = SQVK[r, j]
    return float(np.expm1(min(max(q, 0.0), 30.0)) * 48) if np.isfinite(q) else np.nan
# overlap check (PREREG §2.3): log-difference and tier agreement on slice anchors covered by the cache
def tier_of(q): return 2 if not np.isfinite(q) else (0 if q >= 5e6 else (1 if q >= 1e6 else 2))
dl = []; agree = 0; tot = 0
for E in STS:
    if int(E) not in crow or crow[int(E)] < 47: continue
    for j in range(len(SSYM)):
        a = qv4h_slice(E, j); b = qv4h_cache(E, j)
        if np.isfinite(a) and np.isfinite(b) and a > 0 and b > 0:
            dl.append(math.log(b) - math.log(a)); tot += 1; agree += (tier_of(a) == tier_of(b))
dl = np.array(dl)
RC["gates"]["qv4h_overlap"] = dict(n=int(tot), median_abs_dlog=float(np.median(np.abs(dl))), p90_abs_dlog=float(np.percentile(np.abs(dl), 90)), mean_dlog=float(dl.mean()), tier_agree=float(agree / max(tot, 1)),
                                   PASS=bool(np.median(np.abs(dl)) < 0.02 and agree / max(tot, 1) >= 0.98))
USE_CACHE_AFTER = RC["gates"]["qv4h_overlap"]["PASS"]
def qv4h_at(E, sym):
    j = sidx.get(sym)
    if j is None: return np.nan, "nosym"
    if int(E) <= T_SLICE_END: return qv4h_slice(E, j), "slice"
    return (qv4h_cache(E, j), "cache") if USE_CACHE_AFTER else (np.nan, "dropped")

# ------------------------------------------------------------------ groups (PREREG §2.1)
G = defaultdict(list)
for r in ORD: G[(r["rebalance_id"], r["symbol"])].append(r)
def cls(pw, tw):
    if abs(tw) < 1e-15 and abs(pw) > 0: return "ZERO_TARGET"
    if pw * tw < 0: return "FLIP"
    if abs(pw) > 0 and abs(tw) < abs(pw): return "DERISK"
    return "ADD"
CNT = Counter(); rows = []; dust = []; halt = []
anchor_ts_sorted = sorted(ANCH)
def next_anchor(a):
    lo, hi = a + 3 * 3600, a + 5 * 3600
    c = [t for t in anchor_ts_sorted if lo < t < hi]
    return min(c) if c else None
for (rid, sym), rs in G.items():
    a1 = [r for r in rs if r["order_type"] == "maker" and r["attempt_idx"] == 1]
    if not a1: CNT["no_a1_%s" % rs[0]["order_type"]] += 1; continue
    ints = [abs(r.get("intended_full") if r.get("intended_full") is not None else (r["intended_notional"] or 0.0)) for r in a1]
    if len(a1) > 1:
        if max(ints) > 0 and (max(ints) - min(ints)) / max(ints) > 1e-6: CNT["a1_intent_mismatch"] += 1; continue
        CNT["a1_multi_retry"] += 1
    m = a1[0]; I = ints[0]; tr = m["terminal_reason"]; a = float(m["anchor_ts"]); E = int(round(a / 14400.0)) * 14400
    if abs(a - E) >= 3600: CNT["offgrid_groups"] += 1; continue   # AMENDMENT 1: off-grid (manual/rebuild) anchor runs are excluded and counted
    pw = m["prev_w"] or 0.0; tw = m["target_w"] or 0.0; c = cls(pw, tw); sgn = 1.0 if (tw - pw) >= 0 else -1.0
    qv, src = qv4h_at(E, sym); CNT["qv_" + src] += 1
    base = dict(rid=rid, sym=sym, a=a, E=E, cls=c, I=I, tier=tier_of(qv), qv4h=qv, p=(I / qv if (np.isfinite(qv) and qv > 0) else np.nan),
                aod=(E % 86400) // 14400, side=("buy" if sgn > 0 else "sell"), arm=m.get("placement_arm"), dw=abs(tw - pw), floor=FLOOR.get(sym, 5.0), mid=m.get("mid_at_anchor"),
                era=("A" if E < T_ERA_B else ("B" if E < T_ERA_C else "C")), tr=tr)
    if tr == "skipped_min_notional": dust.append(base); CNT["dust"] += 1; continue
    if tr == "blocked_by_halt": halt.append(base); CNT["halt"] += 1; continue
    if tr == "skipped_no_mid": CNT["skipped_no_mid"] += 1; continue
    if I <= 0: CNT["zero_intent"] += 1; continue
    legs = [r for r in rs if r["order_type"] in ("maker", "topup_taker")]
    unk = sum(1 for r in legs if r.get("filled_notional") is None); CNT["fill_unknown_rows"] += unk
    Fs = sum((r.get("filled_notional") or 0.0) for r in legs); F = abs(Fs)
    if F > 0 and np.sign(Fs) != sgn: CNT["fill_sign_opposite"] += 1; continue
    if F > 1.02 * I: CNT["fill_gt_intent_1.02"] += 1
    Fm = sum(abs(r.get("filled_notional") or 0.0) for r in legs if r["order_type"] == "maker"); Ft = sum(abs(r.get("filled_notional") or 0.0) for r in legs if r["order_type"] == "topup_taker")
    f = min(F / I, 1.0)
    nx = next_anchor(a); adv = np.nan
    if nx is not None and base["mid"] and ANCH[nx]["mid"].get(sym):
        adv = sgn * (float(ANCH[nx]["mid"][sym]) / float(base["mid"]) - 1.0) * 1e4
    rows.append(dict(base, F=F, f=f, Fm=Fm, Ft=Ft, adv=adv, day=time.strftime("%Y%m%d", time.gmtime(E)), unk=unk))
RC["counts"] = dict(CNT); RC["counts"].update(groups_total=len(G), sent=len(rows), dust=len(dust), halt=len(halt))
sent_I = sum(r["I"] for r in rows); dust_I = sum(r["I"] for r in dust); halt_I = sum(r["I"] for r in halt)
RC["intent_notional_usdt"] = dict(sent=sent_I, dust=dust_I, halt=halt_I, dust_share_of_all=dust_I / (sent_I + dust_I + halt_I), halt_share_of_all=halt_I / (sent_I + dust_I + halt_I))
RC["dust_rule"] = dict(floor_source="exchange_info_cache.json MIN_NOTIONAL.notional (executor.filters.f[*].min_notional)", floors=dict(Counter(FLOOR.values())),
                       dust_groups=len(dust), dust_by_class=dict(Counter(d["cls"] for d in dust)), dust_I_median=float(np.median([d["I"] for d in dust])) if dust else None,
                       dust_I_max=float(max(d["I"] for d in dust)) if dust else None, sent_I_min=float(min(r["I"] for r in rows)),
                       dust_dw_median=float(np.median([d["dw"] for d in dust])) if dust else None, sent_dw_p01_p10=[float(np.percentile([r["dw"] for r in rows], q)) for q in (1, 10)],
                       note="live sends go down to |dw| ~ 5 USDT / gross; no_trade_band_w=0.002 in book.json is NOT binding on the ledger")

# ------------------------------------------------------------------ live steady-state gross ratio (GATE F-ii reference)
rat = [(t, ANCH[t]["realized_gross"] / ANCH[t]["target_gross"]) for t in anchor_ts_sorted if ANCH[t]["target_gross"] and ANCH[t]["realized_gross"] and t >= calendar.timegm((2026, 8, 3, 0, 0, 0))]
rv = np.array([x[1] for x in rat])
RC["live_gross_ratio"] = dict(n=int(len(rv)), median_all=float(np.median(rv)), median_excl_lt_0p8=float(np.median(rv[rv >= 0.8])), n_lt_0p8=int((rv < 0.8).sum()), p10=float(np.percentile(rv, 10)), p90=float(np.percentile(rv, 90)),
                              definition="anchors.jsonl realized_gross/target_gross, anchors >= 2026-08-03 00Z; realized = venue gross at anchor start (held), target = sizing gross")

# ------------------------------------------------------------------ tables (PREREG §2.5)
CLS = ["ADD", "DERISK", "FLIP", "ZERO_TARGET"]; TIERS = [0, 1, 2]
P = np.array([r["p"] for r in rows]); fin = np.isfinite(P)
PCUT = [float(np.percentile(P[fin], 100 / 3)), float(np.percentile(P[fin], 200 / 3))]
def pter(p): return 2 if not np.isfinite(p) else (0 if p <= PCUT[0] else (1 if p <= PCUT[1] else 2))
for r in rows: r["pt"] = pter(r["p"])
for d in dust: d["pt"] = pter(d["p"])
def cell_stats(rs):
    if not rs: return dict(n=0)
    I = np.array([r["I"] for r in rs]); F = np.array([r["F"] for r in rs]); f = np.array([r["f"] for r in rs])
    return dict(n=int(len(rs)), sum_I=float(I.sum()), f_w=float(min(F.sum() / I.sum(), 1.0)), f_u=float(f.mean()), P_f0=float((f <= 1e-9).mean()), P_fpartial=float(((f > 1e-9) & (f < 1 - 1e-9)).mean()), P_f1=float((f >= 1 - 1e-9).mean()),
                maker_share_of_fill=float(sum(r["Fm"] for r in rs) / max(F.sum(), 1e-9)), taker_share_of_fill=float(sum(r["Ft"] for r in rs) / max(F.sum(), 1e-9)))
T1 = {c: {t: cell_stats([r for r in rows if r["cls"] == c and r["tier"] == t]) for t in TIERS} for c in CLS}
T2 = {c: {t: {q: cell_stats([r for r in rows if r["cls"] == c and r["tier"] == t and r["pt"] == q]) for q in (0, 1, 2)} for t in TIERS} for c in CLS}
TC = {c: cell_stats([r for r in rows if r["cls"] == c]) for c in CLS}
TALL = cell_stats(rows)
def fhat(c, t, q):
    """PREREG §2.5 lookup with fallback: T2 (n>=30) -> T1 (n>=30) -> class marginal."""
    x = T2[c][t][q]
    if x["n"] >= NMIN: return x["f_w"], "T2"
    x = T1[c][t]
    if x["n"] >= NMIN: return x["f_w"], "T1"
    return TC[c]["f_w"], "class"
for r in rows: r["fhat"], r["src"] = fhat(r["cls"], r["tier"], r["pt"])
RC["p_cuts"] = PCUT; RC["T1"] = T1; RC["T2"] = T2; RC["T_class"] = TC; RC["T_all"] = TALL
RC["fhat_source_share"] = dict(Counter(r["src"] for r in rows))
# by era, by anchor-of-day, side, placement arm (marginal checks)
RC["T1_by_era"] = {e: {c: {t: cell_stats([r for r in rows if r["era"] == e and r["cls"] == c and r["tier"] == t]) for t in TIERS} for c in CLS} for e in ("A", "B", "C")}
RC["class_by_era"] = {e: {c: cell_stats([r for r in rows if r["era"] == e and r["cls"] == c]) for c in CLS} for e in ("A", "B", "C")}
RC["by_anchor_of_day"] = {int(a): cell_stats([r for r in rows if r["aod"] == a]) for a in range(6)}
RC["by_side"] = {s: cell_stats([r for r in rows if r["side"] == s]) for s in ("buy", "sell")}
RC["by_placement_arm"] = {str(a): cell_stats([r for r in rows if r["arm"] == a]) for a in ("join", "behind", None)}
# secondary table with halt as f=0 (report only)
def cell_stats_with_halt(rs, hs):
    I = np.array([r["I"] for r in rs] + [h["I"] for h in hs]); F = np.array([r["F"] for r in rs] + [0.0] * len(hs))
    return dict(n=int(len(I)), f_w=float(F.sum() / I.sum()) if I.sum() > 0 else None, n_halt=len(hs))
RC["T_class_incl_halt"] = {c: cell_stats_with_halt([r for r in rows if r["cls"] == c], [h for h in halt if h["cls"] == c]) for c in CLS}

# ------------------------------------------------------------------ calibration (PREREG §2.5)
def calib(rs, pred_key):
    pr = np.array([r[pred_key] for r in rs]); I = np.array([r["I"] for r in rs]); F = np.array([r["F"] for r in rs])
    q = np.quantile(pr, np.linspace(0, 1, 11)); q[-1] += 1e-9; out = []
    for k in range(10):
        m = (pr >= q[k]) & (pr < q[k + 1])
        if m.sum() == 0: continue
        out.append(dict(decile=k, n=int(m.sum()), pred_w=float((pr[m] * I[m]).sum() / I[m].sum()), real_w=float(F[m].sum() / I[m].sum())))
    x = np.array([o["pred_w"] for o in out]); y = np.array([o["real_w"] for o in out]); w = np.array([o["n"] for o in out], float)
    xm = (x * w).sum() / w.sum(); ym = (y * w).sum() / w.sum(); slope = float(((x - xm) * (y - ym) * w).sum() / max(((x - xm) ** 2 * w).sum(), 1e-12))
    return dict(deciles=out, slope=slope, mae=float(np.abs(x - y).mean()), overall_pred=float((pr * I).sum() / I.sum()), overall_real=float(F.sum() / I.sum()))
RC["calibration_insample"] = calib(rows, "fhat")
# odd/even UTC-day holdout: fit tables on one fold, predict the other
udays = sorted(set(r["day"] for r in rows)); fold = {d: (i % 2) for i, d in enumerate(udays)}
def fit_tables(rs):
    t1 = {c: {t: cell_stats([r for r in rs if r["cls"] == c and r["tier"] == t]) for t in TIERS} for c in CLS}
    t2 = {c: {t: {q: cell_stats([r for r in rs if r["cls"] == c and r["tier"] == t and r["pt"] == q]) for q in (0, 1, 2)} for t in TIERS} for c in CLS}
    tc = {c: cell_stats([r for r in rs if r["cls"] == c]) for c in CLS}
    def fh(c, t, q):
        x = t2[c][t][q]
        if x["n"] >= NMIN: return x["f_w"]
        x = t1[c][t]
        if x["n"] >= NMIN: return x["f_w"]
        x = tc[c]
        return x["f_w"] if x["n"] > 0 else TALL["f_w"]
    return fh
for k in (0, 1):
    fh = fit_tables([r for r in rows if fold[r["day"]] == k])
    for r in rows:
        if fold[r["day"]] != k: r["fhat_oof"] = fh(r["cls"], r["tier"], r["pt"])
RC["calibration_holdout_oddeven_days"] = calib(rows, "fhat_oof"); RC["calibration_holdout_oddeven_days"]["n_days_fold0"] = sum(1 for d in udays if fold[d] == 0); RC["calibration_holdout_oddeven_days"]["n_days_fold1"] = sum(1 for d in udays if fold[d] == 1)
RC["gates"]["F_i_holdout_slope_in_0.8_1.2"] = dict(slope=RC["calibration_holdout_oddeven_days"]["slope"], PASS=bool(0.8 <= RC["calibration_holdout_oddeven_days"]["slope"] <= 1.2))

# ------------------------------------------------------------------ one L2 fractional logistic (check only; PREREG §2.5)
def design(rs):
    X = []
    for r in rs:
        x = [1.0] + [1.0 if r["cls"] == c else 0.0 for c in CLS[1:]] + [1.0 if r["tier"] == t else 0.0 for t in (1, 2)] + [math.log(r["p"]) if (np.isfinite(r["p"]) and r["p"] > 0) else math.log(PCUT[1])] + [1.0 if r["aod"] == a else 0.0 for a in range(1, 6)] + [1.0 if r["side"] == "buy" else 0.0]
        X.append(x)
    return np.array(X)
NAMES = ["intercept"] + ["cls_" + c for c in CLS[1:]] + ["tier1", "tier2", "log_p"] + ["aod%d" % a for a in range(1, 6)] + ["buy"]
X = design(rows); y = np.array([r["f"] for r in rows]); w = np.array([r["I"] for r in rows]); w = w / w.mean()
lam = 1.0; beta = np.zeros(X.shape[1]); pen = np.full(X.shape[1], lam); pen[0] = 0.0
for it in range(50):
    eta = X @ beta; mu = 1 / (1 + np.exp(-eta)); W = w * mu * (1 - mu) + 1e-12
    z = eta + (y - mu) / (mu * (1 - mu) + 1e-12)
    A = X.T @ (W[:, None] * X) + np.diag(pen); b = X.T @ (W * z)
    nb = np.linalg.solve(A, b)
    if np.max(np.abs(nb - beta)) < 1e-8: beta = nb; break
    beta = nb
mu = 1 / (1 + np.exp(-(X @ beta)))
RC["logistic_check"] = dict(coef=dict(zip(NAMES, [float(b) for b in beta])), iters=it + 1, l2=lam, weighted_mean_pred=float((mu * w).sum() / w.sum()), weighted_mean_real=float((y * w).sum() / w.sum()),
                            corr_with_T2_fhat=float(np.corrcoef(mu, np.array([r["fhat"] for r in rows]))[0, 1]),
                            cell_pred_vs_T2={c: {t: dict(logit=float(np.mean(mu[[i for i, r in enumerate(rows) if r["cls"] == c and r["tier"] == t]])) if any(r["cls"] == c and r["tier"] == t for r in rows) else None, T1=T1[c][t].get("f_w")) for t in TIERS} for c in CLS})

# ------------------------------------------------------------------ adverse selection (PREREG §2.5)
def boot_mean(x, daysx, k):
    rng = np.random.default_rng([BOOT_SEED, k]); ud = sorted(set(daysx)); idx = {d: np.where(np.array(daysx) == d)[0] for d in ud}
    o = np.empty(NB)
    for b in range(NB):
        pdraw = rng.integers(0, len(ud), len(ud)); o[b] = x[np.concatenate([idx[ud[q]] for q in pdraw])].mean()
    return [float(np.percentile(o, 2.5)), float(np.percentile(o, 97.5))]
ADV = {}; k = 0
for grp, sel in (("f_eq_1", lambda r: r["f"] >= 1 - 1e-9), ("f_partial", lambda r: 1e-9 < r["f"] < 1 - 1e-9), ("f_eq_0", lambda r: r["f"] <= 1e-9), ("all_sent", lambda r: True)):
    rs = [r for r in rows if sel(r) and np.isfinite(r["adv"])]
    if len(rs) < 10: ADV[grp] = dict(n=len(rs)); continue
    x = np.array([r["adv"] for r in rs]); I = np.array([r["I"] for r in rs]); k += 1
    ADV[grp] = dict(n=len(rs), mean_bps=float(x.mean()), mean_intent_weighted_bps=float((x * I).sum() / I.sum()), ci95_days=boot_mean(x, [r["day"] for r in rs], k),
                    by_class={c: dict(n=len([r for r in rs if r["cls"] == c]), mean_bps=float(np.mean([r["adv"] for r in rs if r["cls"] == c]))) for c in CLS if any(r["cls"] == c for r in rs)})
# unfilled-notional-weighted vs filled-notional-weighted (the r14 framing)
rs = [r for r in rows if np.isfinite(r["adv"])]
x = np.array([r["adv"] for r in rs]); I = np.array([r["I"] for r in rs]); F = np.array([r["F"] for r in rs]); U = np.maximum(I - F, 0.0)
ADV["filled_notional_weighted"] = float((x * F).sum() / F.sum()); ADV["unfilled_notional_weighted"] = float((x * U).sum() / U.sum())
ADV["direction_reproduced_unfilled_gt_filled"] = bool(ADV["unfilled_notional_weighted"] > ADV["filled_notional_weighted"])
ADV["definition"] = "adv = sgn(intent) * (mid_at_anchor[next anchor] / mid_at_anchor[this row] - 1) * 1e4; + = price moved in the intended direction (missing the fill forgoes it); live config quote: filled +3.66 vs unfilled +5.48"
RC["adverse_selection"] = ADV

# ------------------------------------------------------------------ the table the replay consumes (PREREG §2.5/§2.6)
EMP = {}
for c in CLS:
    for t in TIERS:
        for q in (0, 1, 2):
            rs = [r for r in rows if r["cls"] == c and r["tier"] == t and r["pt"] == q]
            src = "T2" if len(rs) >= NMIN else None
            if src is None:
                rs = [r for r in rows if r["cls"] == c and r["tier"] == t]; src = "T1" if len(rs) >= NMIN else None
            if src is None: rs = [r for r in rows if r["cls"] == c]; src = "class"
            f = np.array([r["f"] for r in rs]); I = np.array([r["I"] for r in rs]); o = np.argsort(f); f = f[o]; I = I[o]
            cw = np.cumsum(I) / I.sum()
            EMP["%s|%d|%d" % (c, t, q)] = dict(src=src, n=int(len(f)), f_w=float(min((f * I).sum() / I.sum(), 1.0)), f_sorted=[round(float(v), 6) for v in f], cw=[round(float(v), 8) for v in cw])
TABLE = dict(prereg_sha256=PREREG_SHA, fillmodel_self_sha256=SELF_SHA, built_utc=READ_UTC, classes=CLS, tiers=TIERS, p_cuts=PCUT, G_USDT=G_USDT, NMIN=NMIN,
             fhat={"%s|%d|%d" % (c, t, q): dict(fhat=fhat(c, t, q)[0], src=fhat(c, t, q)[1], n_T2=T2[c][t][q]["n"], n_T1=T1[c][t]["n"]) for c in CLS for t in TIERS for q in (0, 1, 2)},
             emp=EMP, floors=FLOOR, floor_default=5.0, class_rule="ZERO_TARGET: |tgt|<1e-15 & |prev|>0; FLIP: prev*tgt<0; DERISK: same sign & |tgt|<|prev|; ADD: else (incl prev==0)",
             tier_rule="qv4h=expm1(clip(qvk,0,30))*48; >=5e6->0, >=1e6->1, else 2; NaN->2", participation_rule="p=|intent|*G_USDT/qv4h; NaN -> tercile 2; cuts on live sent population")
TP = R + "/receipts/r17_fill_table.json"; json.dump(TABLE, open(TP, "w"), indent=0)
RC["table"] = dict(path=TP, sha256=sha(TP))
# per-group rows for reproducibility (compact)
np.savez_compressed(R + "/receipts/r17_fill_groups.npz", rid=np.array([r["rid"] for r in rows]), sym=np.array([r["sym"] for r in rows]), E=np.array([r["E"] for r in rows], np.int64), cls=np.array([r["cls"] for r in rows]),
                    I=np.array([r["I"] for r in rows]), F=np.array([r["F"] for r in rows]), f=np.array([r["f"] for r in rows]), tier=np.array([r["tier"] for r in rows], np.int8), p=np.array([r["p"] for r in rows]), pt=np.array([r["pt"] for r in rows], np.int8),
                    adv=np.array([r["adv"] for r in rows]), fhat=np.array([r["fhat"] for r in rows]), era=np.array([r["era"] for r in rows]), aod=np.array([r["aod"] for r in rows], np.int8), side=np.array([r["side"] for r in rows]), arm=np.array([str(r["arm"]) for r in rows]))
RC["groups_npz_sha256"] = sha(R + "/receipts/r17_fill_groups.npz")
json.dump(RC, open(R + "/receipts/RECEIPT_r17_fillmodel_2026-09-12.json", "w"), indent=1, default=float)
# ------------------------------------------------------------------ print
print("READ", READ_UTC, "days", days[0], days[-1], "orders rows", n_ord_rows, "groups", len(G))
print("COUNTS", json.dumps(RC["counts"]))
print("INTENT USDT sent %.0f dust %.0f (%.1f%%) halt %.0f (%.1f%%)" % (sent_I, dust_I, 100 * RC["intent_notional_usdt"]["dust_share_of_all"], halt_I, 100 * RC["intent_notional_usdt"]["halt_share_of_all"]))
print("QV4H overlap", json.dumps(RC["gates"]["qv4h_overlap"]))
print("LIVE gross ratio", json.dumps(RC["live_gross_ratio"]))
print("P cuts", PCUT, "fhat src share", RC["fhat_source_share"])
print("\nT1 class x tier  (n | f_w | f_u | P0/Ppart/P1 | maker share)")
for c in CLS:
    for t in TIERS:
        x = T1[c][t]
        if x["n"]: print("  %-11s tier%d n=%5d f_w=%.4f f_u=%.4f  P0=%.3f Ppart=%.3f P1=%.3f  mk=%.3f" % (c, t, x["n"], x["f_w"], x["f_u"], x["P_f0"], x["P_fpartial"], x["P_f1"], x["maker_share_of_fill"]))
        else: print("  %-11s tier%d n=0" % (c, t))
print("class marginal", {c: (TC[c]["n"], round(TC[c]["f_w"], 4)) for c in CLS}, "ALL", TALL["n"], round(TALL["f_w"], 4))
print("class incl halt", {c: (v["n"], round(v["f_w"], 4) if v["f_w"] else None, v["n_halt"]) for c, v in RC["T_class_incl_halt"].items()})
print("\nT2 (class|tier|ptercile: n f_w src)")
for kk, v in TABLE["fhat"].items(): print("  %-18s n_T2=%5d n_T1=%5d fhat=%.4f (%s)" % (kk, v["n_T2"], v["n_T1"], v["fhat"], v["src"]))
print("\nby era (class f_w n):", {e: {c: (v["n"], round(v["f_w"], 3)) if v["n"] else None for c, v in RC["class_by_era"][e].items()} for e in ("A", "B", "C")})
print("by anchor-of-day:", {a: (v["n"], round(v["f_w"], 3)) for a, v in RC["by_anchor_of_day"].items()})
print("by side:", {s: (v["n"], round(v["f_w"], 3)) for s, v in RC["by_side"].items()}, "by arm:", {a: (v["n"], round(v["f_w"], 3)) if v["n"] else None for a, v in RC["by_placement_arm"].items()})
print("\nCALIB insample slope %.3f mae %.4f | holdout slope %.3f mae %.4f  GATE F-i %s" % (RC["calibration_insample"]["slope"], RC["calibration_insample"]["mae"], RC["calibration_holdout_oddeven_days"]["slope"], RC["calibration_holdout_oddeven_days"]["mae"], RC["gates"]["F_i_holdout_slope_in_0.8_1.2"]["PASS"]))
for o in RC["calibration_holdout_oddeven_days"]["deciles"]: print("   d%d n=%5d pred %.3f real %.3f" % (o["decile"], o["n"], o["pred_w"], o["real_w"]))
print("LOGIT", json.dumps({k2: round(v, 3) for k2, v in RC["logistic_check"]["coef"].items()}), "corr with T2", round(RC["logistic_check"]["corr_with_T2_fhat"], 3))
print("\nADVERSE SELECTION", json.dumps({k2: (v if not isinstance(v, dict) else {kk: vv for kk, vv in v.items() if kk != "by_class"}) for k2, v in ADV.items()}, default=float))
for grp in ("f_eq_1", "f_partial", "f_eq_0"):
    if "by_class" in ADV[grp]: print("  ", grp, {c: (v["n"], round(v["mean_bps"], 2)) for c, v in ADV[grp]["by_class"].items()})
print("\nTABLE", TP, RC["table"]["sha256"])
print("DONE_r17_fillmodel")
