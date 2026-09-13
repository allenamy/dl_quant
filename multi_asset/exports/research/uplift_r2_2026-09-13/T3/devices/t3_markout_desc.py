#!/usr/bin/python3
"""T3 §4 descriptive markout (no decision role after PROGRAM AMENDMENT 1) + gate G3.
PREREG_T3_markout_curve_2026-09-13.md sha c7be8500... Price source P1 = r11 marks_multilag.json (aggTrades, first trade at or
after fill_ts + D within 60 s; sha 26ca67c9...). Second column = next-anchor venue mid (anchors.jsonl mid_at_anchor_vector).
MO_F(D) = s*(P_D/F - 1)*1e4 (negative = adverse to us); MO_M(D) = s*(P_D/M_sub - 1)*1e4, M_sub = parent order mid_at_submit.
Read-only. ENV WHITELIST = EMPTY SET (asserted; os.environ.get / os.getenv raise after import)."""
import bisect, hashlib, json, math, os, sys, time
from collections import defaultdict, Counter
T3 = "/Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/uplift_r2_2026-09-13/T3"
PREREG = f"{T3}/PREREG_T3_markout_curve_2026-09-13.md"; PREREG_SHA = "c7be850055160d7eeafe10fb859470f442d3f0552333ba290d9496357be8f8f6"
LOG = f"{T3}/private/ledger_snap_20260913T0455Z"
MARKS = "/Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/uplift_2026-09-11/r11_costtruth/out/full/marks_multilag.json"
MARKS_SHA = "26ca67c969ec1e3f968c1506c61d0eb246b935317046519f401a38e86d5f58ac"
LAGS = ["60", "300", "900", "3600", "14400"]
NB = 2000; SEED = 20260905
_FORBID = ("CAL", "JUDGE", "PANEL", "W10_", "POD_", "DLW_", "KING_", "SEAT_", "UMASK", "LEGS", "FTRIM", "R12_", "R21_", "PHI", "CEM_Q", "LIVE_MODE")
_hit = sorted(k for k in os.environ if any(k.startswith(p) for p in _FORBID))
assert not _hit, f"E-0826-D: forbidden env present {_hit}"
import numpy as np
def _no_env(*a, **k): raise RuntimeError("E-0826-D: this device reads no environment variable")
os.environ.get = _no_env; os.getenv = _no_env
def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""): h.update(c)
    return h.hexdigest()
assert sha256(PREREG) == PREREG_SHA; assert sha256(MARKS) == MARKS_SHA
SELF_SHA = sha256(os.path.abspath(__file__))
def read_jsonl(p):
    out = []
    with open(p) as f: lines = f.readlines()
    for i, ln in enumerate(lines):
        ln = ln.strip()
        if not ln: continue
        try: out.append(json.loads(ln))
        except json.JSONDecodeError:
            if i == len(lines) - 1: continue
            raise
    return out
days = sorted(d for d in os.listdir(LOG) if d.isdigit() and len(d) == 8)
fills_raw = []
for d in days:
    p = f"{LOG}/{d}/fills.jsonl"
    if os.path.exists(p): fills_raw.extend(read_jsonl(p))
seen_last = {}
for i, f in enumerate(fills_raw):
    if f.get("trade_id") is not None: seen_last[f["trade_id"]] = i
fills = [f for i, f in enumerate(fills_raw) if f.get("trade_id") is None or seen_last.get(f["trade_id"]) == i]
orders_by = defaultdict(list)
for d in days:
    p = f"{LOG}/{d}/orders.jsonl"
    if os.path.exists(p):
        for r in read_jsonl(p): orders_by[(r["rebalance_id"], r["symbol"])].append(r)
anch = []
for d in days:
    p = f"{LOG}/{d}/anchors.jsonl"
    if os.path.exists(p):
        for r in read_jsonl(p):
            mv = r.get("mid_at_anchor_vector")
            if isinstance(mv, str): mv = json.loads(mv)
            anch.append((r["anchor_ts"], mv or {}))
anch.sort(key=lambda x: x[0]); ats = [a for a, _ in anch]
marks = json.load(open(MARKS))

excluded = Counter()
rows = []
for f in fills:
    ot = f.get("order_type")
    if ot == "protective_flatten":
        excluded["protective_flatten"] += 1; continue
    if ot == "maker" and f.get("venue_maker_flag") is not True:
        excluded["maker_order_type_but_taker_flag"] += 1; continue
    if ot not in ("maker", "topup_taker"):
        excluded[f"other_order_type:{ot}"] += 1; continue
    px = float(f.get("fill_px") or 0.0); nz = abs(float(f.get("fill_notional") or 0.0))
    if not (px > 0 and nz > 0 and f.get("side") in ("buy", "sell")):
        excluded["unusable_px_notional_side"] += 1; continue
    s = 1.0 if f["side"] == "buy" else -1.0
    g = orders_by.get((f["rebalance_id"], f["symbol"]), [])
    par = [o for o in g if o.get("order_type") == ot and o.get("submit_ts") is not None]
    msub = float(par[0]["mid_at_submit"]) if (len(par) == 1 and par[0].get("mid_at_submit")) else None
    rej = any(o.get("order_type") == "maker" and o.get("attempt_idx") == 1 and o.get("terminal_reason") == "venue_reject" and "-5022" in (o.get("note") or "") for o in g)
    status = ("requote" if rej else "first_send") if ot == "maker" else "topup"
    arm = next((o.get("placement_arm") for o in g if o.get("order_type") == "maker" and o.get("attempt_idx") == 1 and o.get("placement_arm") is not None), None)
    m = marks.get(str(f["trade_id"]))
    mo = {}
    if m is not None:
        for L in LAGS:
            rec = m.get(L)
            if rec and rec.get("status") == "ok":
                mo[L] = s * (float(rec["mark_px"]) / px - 1.0) * 1e4
    j = bisect.bisect_left(ats, float(f["fill_ts"]) + 60.0)
    mo_next = None; gap_h = None
    if j < len(ats):
        gap_h = (ats[j] - float(f["fill_ts"])) / 3600.0
        mv = anch[j][1].get(f["symbol"])
        if 3.0 <= gap_h <= 5.0 and mv:
            mo_next = s * (float(mv) / px - 1.0) * 1e4
    ident = None
    if msub and "14400" in mo:
        P = float(m["14400"]["mark_px"]); moM = s * (P / msub - 1.0); e = s * (px / msub - 1.0)
        ident = abs((1 + s * moM) - (1 + s * mo["14400"] / 1e4) * (1 + s * e))
    rows.append(dict(tid=f["trade_id"], ot=ot, s=s, nz=nz, day=int(float(f["fill_ts"]) // 86400), anchor=f.get("anchor_ts"),
                     status=status, arm=arm, mo=mo, mo_next=mo_next, gap_h=gap_h, msub=msub,
                     moM={L: s * (float(m[L]["mark_px"]) / msub - 1.0) * 1e4 for L in mo} if msub else {},
                     e_sub=(s * (px / msub - 1.0) * 1e4) if msub else None, ident=ident,
                     rec60=f.get("mid_at_fill_plus_60s"), rec60_ts=f.get("mark_ts_actual"),
                     p1_60_ts=(float(m["60"]["mark_ts"]) / 1000.0 if (m and m.get("60", {}).get("status") == "ok") else None),
                     px=px))

# ---------------- G3 ----------------
mk_all = [r for r in rows if r["ot"] == "maker"]
cmp_ = [r for r in mk_all if r["p1_60_ts"] is not None and r["rec60"] is not None]
same = sum(1 for r in cmp_ if r["rec60_ts"] is not None and abs(float(r["rec60_ts"]) - r["p1_60_ts"]) <= 0.001)
w = sum(r["nz"] for r in cmp_)
mo_p1 = sum(r["nz"] * r["mo"]["60"] for r in cmp_) / w
mo_rec = sum(r["nz"] * r["s"] * (float(r["rec60"]) / r["px"] - 1.0) * 1e4 for r in cmp_) / w
G3 = {"n_compared": len(cmp_), "n_with_recorded_mark_ts": sum(1 for r in cmp_ if r["rec60_ts"] is not None),
      "same_aggtrade_share": same / max(len(cmp_), 1), "mo60_weighted_P1": round(mo_p1, 4), "mo60_weighted_recorded": round(mo_rec, 4),
      "abs_diff_bps": round(abs(mo_p1 - mo_rec), 4)}
G3["PASS"] = bool(G3["same_aggtrade_share"] >= 0.99 and G3["abs_diff_bps"] <= 0.10)
print("G3", json.dumps(G3))
ident_max = max((r["ident"] for r in rows if r["ident"] is not None), default=0.0)

def balanced(r): return all(L in r["mo"] for L in LAGS)
def family(sel, k):
    sel = [r for r in sel if balanced(r)]
    out = {"n_fills": len(sel), "kseed": k}
    if not sel: return out
    dk = sorted(set(r["day"] for r in sel)); di = {d: i for i, d in enumerate(dk)}
    cols = LAGS + ["next"]
    num = {c: np.zeros(len(dk)) for c in cols}; den = {c: np.zeros(len(dk)) for c in cols}
    numM = {c: np.zeros(len(dk)) for c in LAGS}; denM = {c: np.zeros(len(dk)) for c in LAGS}
    for r in sel:
        i = di[r["day"]]
        for L in LAGS:
            num[L][i] += r["nz"] * r["mo"][L]; den[L][i] += r["nz"]
            if L in r["moM"]: numM[L][i] += r["nz"] * r["moM"][L]; denM[L][i] += r["nz"]
        if r["mo_next"] is not None: num["next"][i] += r["nz"] * r["mo_next"]; den["next"][i] += r["nz"]
    rng = np.random.default_rng([SEED, k]); idx = rng.integers(0, len(dk), size=(NB, len(dk)))
    def summ(nm, dn):
        if dn.sum() <= 0: return None
        b = nm[idx].sum(1) / np.maximum(dn[idx].sum(1), 1e-12)
        return {"mean_bps": round(float(nm.sum() / dn.sum()), 4), "ci95": [round(float(np.percentile(b, 2.5)), 4), round(float(np.percentile(b, 97.5)), 4)],
                "notional_usdt": round(float(dn.sum()), 1)}
    out.update({"n_days": len(dk), "notional_usdt": round(sum(r["nz"] for r in sel), 1),
                "MO_F": {c: summ(num[c], den[c]) for c in cols}, "MO_M_vs_mid_at_submit": {c: summ(numM[c], denM[c]) for c in LAGS},
                "next_anchor_coverage_notional_share": round(float(den["next"].sum() / den["60"].sum()), 4)})
    by_a = defaultdict(lambda: defaultdict(float))
    for r in sel:
        for L in LAGS:
            by_a[r["anchor"]][L + "_n"] += r["nz"] * r["mo"][L]; by_a[r["anchor"]][L + "_d"] += r["nz"]
    out["adverse_anchor_share"] = {L: {"lt0": round(sum(1 for a in by_a.values() if a[L + "_n"] / a[L + "_d"] < 0) / len(by_a), 4),
                                       "le0": round(sum(1 for a in by_a.values() if a[L + "_n"] / a[L + "_d"] <= 0) / len(by_a), 4)} for L in LAGS}
    out["n_anchors"] = len(by_a)
    return out

mk = [r for r in rows if r["ot"] == "maker"]; tk = [r for r in rows if r["ot"] == "topup_taker"]
mkb = [r for r in mk if balanced(r)]
q = np.quantile([r["nz"] for r in mkb], [1 / 3, 2 / 3])
RES = {"101_maker_all": family(mk, 101), "102_maker_buy": family([r for r in mk if r["s"] > 0], 102),
       "103_maker_sell": family([r for r in mk if r["s"] < 0], 103),
       "104_first_send_join": family([r for r in mk if r["status"] == "first_send" and r["arm"] == "join"], 104),
       "105_first_send_behind": family([r for r in mk if r["status"] == "first_send" and r["arm"] == "behind"], 105),
       "106_first_send": family([r for r in mk if r["status"] == "first_send"], 106),
       "107_requote": family([r for r in mk if r["status"] == "requote"], 107),
       "108_topup_taker": family(tk, 108),
       "109_maker_fill_notional_tercile_low": family([r for r in mk if r["nz"] <= q[0]], 109),
       "110_maker_fill_notional_tercile_mid": family([r for r in mk if q[0] < r["nz"] <= q[1]], 110),
       "111_maker_fill_notional_tercile_high": family([r for r in mk if r["nz"] > q[1]], 111)}
counts = {"raw_fill_rows": len(fills_raw), "collapsed": len(fills), "excluded": dict(excluded),
          "maker_collapsed": len(mk), "maker_in_marks": sum(1 for r in mk if r["mo"]), "maker_balanced_panel": len(mkb),
          "maker_not_in_marks": sum(1 for r in mk if not r["mo"]), "topup_collapsed": len(tk), "topup_balanced_panel": sum(1 for r in tk if balanced(r)),
          "tercile_edges_usdt": [float(q[0]), float(q[1])], "identity_maxabs_fraction": ident_max,
          "maker_msub_join_share": round(sum(1 for r in mk if r["msub"]) / len(mk), 4)}
OUT = {"device": os.path.abspath(__file__), "self_sha256": SELF_SHA, "prereg_sha256": PREREG_SHA, "env_whitelist": [],
       "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "inputs": {"ledger_manifest_sha256": sha256(f"{LOG}/MANIFEST_sha256.txt"), "marks_sha256": MARKS_SHA},
       "G3": G3, "counts": counts, "families": RES, "decision_role": "none (PROGRAM AMENDMENT 1 withdrew the 4 h markout rule)"}
json.dump(OUT, open(f"{T3}/receipts/MARKOUT_desc.json", "w"), indent=1)
print(json.dumps(counts, indent=1))
for name, b in RES.items():
    if not b.get("n_fills"): print(name, "empty"); continue
    mf = b["MO_F"]
    print(f"{name:40s} n={b['n_fills']:6d} d={b['n_days']:2d} $={b['notional_usdt']:>10.0f} | " +
          " ".join(f"{L}:{mf[L]['mean_bps']:+7.2f}[{mf[L]['ci95'][0]:+.2f},{mf[L]['ci95'][1]:+.2f}]" for L in LAGS) +
          (f" next:{mf['next']['mean_bps']:+7.2f}[{mf['next']['ci95'][0]:+.2f},{mf['next']['ci95'][1]:+.2f}]" if mf.get("next") else ""))
