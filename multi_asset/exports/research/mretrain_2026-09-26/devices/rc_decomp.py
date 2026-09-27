"""rc_decomp.py — root-cause support for the King-in-2026 question (lead 2026-09-27 01:4xZ; dlarch leads the synthesis, fresh2 = King
owner). DESCRIPTIVE ONLY: no gate, no threshold, no verdict. Three parts, each on committed family artefacts:
  A. RED_m0 − A0_m0 (both F10 seeds, then averaged) by channel: price (pnl), funding PAID (car = −funding cash flow, + = paid: the
     engine identity is nav1 − nav0 = price_trade + funding − fee, bt_tables car = −1e4·funding/den), fee (cst), UA-excluded (unk),
     and the residual g − (pnl − car − cst) — all native bt_tables caliber bps/anchor/gross, summed per UTC full day and
     converted to NAV bps/day (× GM); segments pre2026 (frozen NS.SEG) / 2026 / years / 2026 months. Total row reconciles to the
     frozen news_stats.dbar of r (the red reading) — printed side by side, the difference is the compounding/navm0 term.
  B. seat path: King seat share s = WL_king / (WL_king + WL_fund) (combo_target zeroes the F10 seat) of A0 vs RED legs, monthly;
     the daily RED − A0 g difference bucketed by the seat change Δs = s_RED − s_A0 (bucket shares of the total) and by A0 King
     share tercile; King / fund leg returns LR (legs caliber) monthly.
  C. King single-model score-layer IC ("looked at alone"): per anchor Spearman of A0_m0 P (== in-service a10b8725 scores) vs the
     training label y4s over finite cells (>= 30), monthly mean; plus the top-minus-bottom decile mean label spread (bps / 4h).
     The shuffled RED P is run through the same code as a zero control.
usage: python rc_decomp.py <legs_RED.npz or -> <out.json>"""
import os, sys, json, hashlib, time, calendar
import numpy as np
from scipy.stats import spearmanr
R = "/dev/shm/mretrain_2026-09-26"; ENG = "/dev/shm/news_2026-09-23/engine"; sys.path.insert(0, ENG)
import news_stats as NS, bt_tables as BT, bt_driver_lib as DL
NS.BT, NS.DL = BT, DL
NEWT = "/workspace/codex_research/QNT-2026-0907/combo_20260923/corrected_combo_v1d/data/dlw_targets.npz"
LEGS_RED, OUT = sys.argv[1], sys.argv[2]
DAY = 86400; SEEDS = ("42", "2027")
iso = lambda t: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(t)))
ym = lambda t: time.strftime("%Y-%m", time.gmtime(int(t)))


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


rec = {"device": "rc_decomp.py", "self_sha256": sha(os.path.abspath(__file__)), "utc": iso(time.time()), "status": "DESCRIPTIVE_NO_GATE", "inputs": {}}
GM = float(BT.GM) if hasattr(BT, "GM") else float(DL.GM); rec["GM"] = GM
ser = {}
for lbl in ("A0_m0", "RED_m0"):
    for s in SEEDS:
        p = f"{R}/series/SER_{lbl}_s{s}.npz"; rec["inputs"][p] = sha(p); ser[(lbl, s)] = np.load(p)
A = ser[("A0_m0", "42")]["anchors"].astype(np.int64)
for z in ser.values(): assert np.array_equal(z["anchors"].astype(np.int64), A)
ch = lambda z, k: z[k + "_per_path"].mean(0)                               # mean over the 32 execution paths
day = (A // DAY) * DAY
segs = {"pre2026": NS.seg_mask(A, *NS.SEG["pre2026"]), "2026": NS.seg_mask(A, "2026-01-01T00:00:00Z", iso(A[-1]))}
for y in ("2023H2", "2024", "2025"): segs[y] = NS.seg_mask(A, *NS.SEG[y])
for m in sorted({ym(t) for t in A[A >= calendar.timegm((2026, 1, 1, 0, 0, 0))]}):
    segs["2026-" + m[5:]] = np.array([ym(t) == m for t in A]) & segs["2026"]


def per_day(x, m):
    """NAV bps/day of a bps/anchor/gross channel: sum the anchors of each FULL UTC day (6 anchors) × GM, then mean over days"""
    days = NS.full_days(A, m); keep = m & np.isin(day, days)
    s = np.bincount(np.searchsorted(days, day[keep]), weights=x[keep], minlength=len(days)); return float(GM * s.mean()), len(days)


# ---------------- A. channels
A_out = {}
for k, m in segs.items():
    row = {}
    for s in SEEDS + ("avg",):
        ss = SEEDS if s == "avg" else (s,)
        d = {}
        for c in ("pnl", "car", "cst", "unk", "g"):
            d[c] = np.mean([ch(ser[("RED_m0", q)], c) - ch(ser[("A0_m0", q)], c) for q in ss], axis=0)
        d["resid"] = d["g"] - (d["pnl"] - d["car"] - d["cst"])    # g = pnl − car − cst up to navm vs equity (checked: residual ~0)
        row[s] = {c: per_day(v, m)[0] for c, v in d.items()}
        row[s]["n_days"] = per_day(d["g"], m)[1]
        if k in ("pre2026", "2026") and s == "avg":
            days = NS.full_days(A, m)
            P = lambda lbl, q: [{"A": A, "r": ser[(lbl, q)]["r_per_path"][j]} for j in range(32)]
            row[s]["dbar_r_frozen_news_stats"] = float(1e4 * np.mean([NS.dbar(P("RED_m0", q), P("A0_m0", q), m, days)[0].mean() for q in SEEDS]))
        if s == "avg":   # levels too, so the difference can be read against the size of each channel
            row["levels_A0_avg"] = {c: per_day(np.mean([ch(ser[("A0_m0", q)], c) for q in SEEDS], axis=0), m)[0] for c in ("pnl", "car", "cst", "g")}
            row["levels_RED_avg"] = {c: per_day(np.mean([ch(ser[("RED_m0", q)], c) for q in SEEDS], axis=0), m)[0] for c in ("pnl", "car", "cst", "g")}
    A_out[k] = row
rec["A_channels_RED_minus_A0_NAV_bps_per_day"] = A_out

# ---------------- B. seat path
L0p = f"{R}/arms/A0_m0/work/legs.npz"; rec["inputs"][L0p] = sha(L0p); L0 = np.load(L0p)
E = L0["E_ts"].astype(np.int64); ix = np.searchsorted(E, A); assert np.array_equal(E[ix], A)
share = lambda W: W[:, 0] / np.where(W[:, 0] + W[:, 2] > 1e-12, W[:, 0] + W[:, 2], np.nan)
s0 = share(L0["WL"].astype(np.float64))[ix]
B_out = {"note": "King seat share s = WL_king/(WL_king+WL_fund) at each anchor (combo_target zeroes the F10 seat); LR = legs-caliber leg returns (as stored, per anchor)"}
if LEGS_RED != "-":
    rec["inputs"][LEGS_RED] = sha(LEGS_RED); L1 = np.load(LEGS_RED); assert np.array_equal(L1["E_ts"].astype(np.int64), E)
    s1 = share(L1["WL"].astype(np.float64))[ix]
else:
    s1 = None
dg = np.mean([ch(ser[("RED_m0", q)], "g") - ch(ser[("A0_m0", q)], "g") for q in SEEDS], axis=0)
LR0 = L0["LR"].astype(np.float64)[ix]
monthly = {}
for k, m in segs.items():
    r = {"A0_king_share_mean": float(np.nanmean(s0[m])), "A0_LR_king_sum": float(np.nansum(LR0[m, 0])), "A0_LR_fund_sum": float(np.nansum(LR0[m, 2])),
         "A0_LR_F10_sum": float(np.nansum(LR0[m, 1]))}
    if s1 is not None: r["RED_king_share_mean"] = float(np.nanmean(s1[m])); r["RED_LR_king_sum"] = float(np.nansum(L1["LR"].astype(np.float64)[ix][m, 0]))
    monthly[k] = r
B_out["by_segment"] = monthly
for k in ("pre2026", "2026"):
    m = segs[k]; tot = float(dg[m].sum()); bk = {}
    if s1 is not None:
        ds = s1 - s0
        for name, sel in (("seat_down_ge_0.10", ds <= -0.10), ("seat_within_0.10", np.abs(ds) < 0.10), ("seat_up_ge_0.10", ds >= 0.10), ("undefined", ~np.isfinite(ds))):
            sel = sel & m; bk[name] = {"anchors": int(sel.sum()), "sum_dg_bps_anchor_gross": float(dg[sel].sum()), "share_of_total": float(dg[sel].sum() / tot) if tot else None}
    q = np.nanpercentile(s0[m], [33.333, 66.667]); ter = {}
    for name, sel in (("A0_share_low", s0 < q[0]), ("A0_share_mid", (s0 >= q[0]) & (s0 < q[1])), ("A0_share_high", s0 >= q[1])):
        sel = sel & m; ter[name] = {"anchors": int(sel.sum()), "mean_dg": float(dg[sel].mean()), "share_of_total": float(dg[sel].sum() / tot) if tot else None}
    B_out[f"dg_buckets_{k}"] = {"total_sum_dg_bps_anchor_gross": tot, "by_seat_change": bk, "by_A0_king_share_tercile": ter, "tercile_edges": [float(x) for x in q]}
rec["B_seat_path"] = B_out

# ---------------- C. King score-layer IC
T = np.load(NEWT, allow_pickle=True); ya = T["E_ts"].astype(np.int64)
Kp = f"{R}/arms/A0_m0/work/king/KING_OOF.npz"; rec["inputs"][Kp] = sha(Kp); K = np.load(Kp)
assert np.array_equal(T["symbols"], K["symbols"])
KE = K["E_ts"].astype(np.int64); j = np.searchsorted(ya, KE); ok = (j < len(ya)) & (ya[np.minimum(j, len(ya) - 1)] == KE)
Y = np.full(K["P"].shape, np.nan, np.float32); Y[ok] = T["y4s"][j[ok]]
REDP = np.load("/workspace/mretrain_2026-09-26/redcause/king_RED/KING_OOF.npz")["P"] if os.path.exists("/workspace/mretrain_2026-09-26/redcause/king_RED/KING_OOF.npz") else None


def ic_rows(P):
    out = {}
    for i in range(len(KE)):
        g = np.isfinite(P[i]) & np.isfinite(Y[i]); n = int(g.sum())
        if n < 30: continue
        ic = float(spearmanr(P[i, g], Y[i, g]).correlation)
        o = np.argsort(P[i, g]); k10 = max(n // 10, 1); yy = Y[i, g][o]
        out.setdefault(ym(KE[i]), []).append((ic, float(1e4 * (yy[-k10:].mean() - yy[:k10].mean())), n))
    return {m: {"mean_cs_spearman": float(np.mean([x[0] for x in v])), "t_stat": float(np.mean([x[0] for x in v]) / (np.std([x[0] for x in v], ddof=1) / np.sqrt(len(v)))),
                "decile_spread_bps_per_4h": float(np.mean([x[1] for x in v])), "anchors": len(v), "median_names": float(np.median([x[2] for x in v]))} for m, v in sorted(out.items())}


rec["C_king_ic_monthly_A0"] = ic_rows(K["P"])
if REDP is not None: rec["C_king_ic_monthly_RED_zero_control"] = ic_rows(REDP)
yr = {}
for m, v in rec["C_king_ic_monthly_A0"].items():
    y = m[:4]; yr.setdefault(y, []).append((v["mean_cs_spearman"], v["anchors"]))
rec["C_king_ic_by_year_anchor_weighted"] = {y: float(np.average([a for a, _ in v], weights=[b for _, b in v])) for y, v in yr.items()}
json.dump(rec, open(OUT + ".tmp", "w"), indent=1); os.replace(OUT + ".tmp", OUT)
print("RC_DECOMP DONE sha=%s" % sha(OUT), flush=True)
