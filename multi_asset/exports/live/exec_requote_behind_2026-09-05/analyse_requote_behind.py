#!/usr/bin/env python3
"""PREREG_requote_and_behind_live_causal_2026-09-05 (sha 5ed36216…) — read-only judge on the live ledger.
Plan-level intent-to-treat (ITT) all-in cost vs mid_at_anchor, bps per unit intended notional.
Inputs: ~/dl_quant_live/state/live/pilot_log/<day>/{orders,fills}.jsonl (never written)."""
import json, glob, os, sys, math, collections, random
from datetime import datetime, timezone
ROOT = "/Users/haosiyu/dl_quant_live/state/live/pilot_log"
D0, D1 = "20260802", "20260905"
SEED, NBOOT = 20260905, 2000
def day_of(a): return datetime.fromtimestamp(a, tz=timezone.utc).strftime("%Y%m%d")
def is5022(r): return r.get("terminal_reason") == "venue_reject" and "-5022" in (r.get("note") or "")
orders, fills = [], []
for d in sorted(glob.glob(os.path.join(ROOT, "2026*"))):
    day = os.path.basename(d)
    if not (D0 <= day <= D1): continue
    for fn, sink in (("orders.jsonl", orders), ("fills.jsonl", fills)):
        p = os.path.join(d, fn)
        if not os.path.exists(p): continue
        for l in open(p):
            try: r = json.loads(l); r["_day"] = day; sink.append(r)
            except Exception: pass
print(f"orders rows {len(orders)}, fills rows {len(fills)}, days {D0}..{D1}")
# ---------- plans ----------
plans = {}
for r in orders:
    if r.get("order_type") != "maker" or r.get("attempt_idx") != 1: continue
    k = (r["rebalance_id"], r["symbol"])
    p = plans.setdefault(k, dict(day=r["_day"], anchor=r["anchor_ts"], rid=r["rebalance_id"], sym=r["symbol"], side=None,
                                 intended=None, mid=None, refused=False, arm=None, rested1=False, requote_rested=False,
                                 maker_rows=[], skip=None))
    if is5022(r):
        p["refused"] = True; p["intended"] = p["intended"] or r.get("intended_notional"); p["mid"] = p["mid"] or r.get("mid_at_anchor")
        p["side"] = p["side"] or r.get("side"); p["arm"] = p["arm"] or r.get("placement_arm")
    elif r.get("submit_ts") is not None:
        req = (r.get("mid_at_submit") is not None and r.get("mid_at_submit") != r.get("mid_at_anchor"))
        if req: p["requote_rested"] = True
        else: p["rested1"] = True
        p["maker_rows"].append(r)
        p["intended"] = p["intended"] or r.get("intended_notional"); p["mid"] = p["mid"] or r.get("mid_at_anchor")
        p["side"] = p["side"] or r.get("side"); p["arm"] = p["arm"] or r.get("placement_arm")
    elif str(r.get("terminal_reason", "")).startswith("skipped"):
        p["skip"] = r.get("terminal_reason")
topups = collections.defaultdict(list)
for r in orders:
    if r.get("order_type") == "topup_taker" and r.get("filled_notional"):
        topups[(r["rebalance_id"], r["symbol"])].append(r)
# ---------- plan cost ----------
def row_cost(r, side, mid):
    """(notional, price cost bps, fee bps) of one filled row vs the plan's anchor mid."""
    n = abs(r.get("filled_notional") or 0.0); px = r.get("avg_fill_px")
    if n <= 0 or not px or not mid: return 0.0, 0.0, 0.0
    s = 1.0 if side == "buy" else -1.0
    c = s * (px - mid) / mid * 1e4
    fee = (r.get("fee_paid") or 0.0) / n * 1e4
    return n, c, fee
P = []
for k, p in plans.items():
    if p["intended"] is None or p["mid"] is None or p["side"] is None: continue
    if p["skip"] and not (p["refused"] or p["maker_rows"]): continue
    I = abs(p["intended"])
    if I <= 0: continue
    tot_cost = 0.0; tot_fill = 0.0; parts = collections.defaultdict(float); nparts = collections.defaultdict(float)
    for r in p["maker_rows"]:
        n, c, f = row_cost(r, p["side"], p["mid"]); lab = "requote" if (r.get("mid_at_submit") != r.get("mid_at_anchor")) else "maker"
        tot_cost += n * (c + f); tot_fill += n; parts[lab] += n * (c + f); nparts[lab] += n
    for r in topups.get(k, []):
        n, c, f = row_cost(r, p["side"], p["mid"]); lab = "topup_" + str(r.get("topup_source"))
        tot_cost += n * (c + f); tot_fill += n; parts[lab] += n * (c + f); nparts[lab] += n
    fill_share = min(tot_fill / I, 1.5)
    branch = None
    if p["refused"]:
        if p["requote_rested"]:
            branch = "requote_filled" if nparts["requote"] >= 0.5 * I else ("requote_partial" if nparts["requote"] > 0 else "requote_unfilled")
        else:
            branch = "twice_refused"
    P.append(dict(k=k, day=p["day"], rid=p["rid"], sym=p["sym"], I=I, cost=tot_cost / I, fill=fill_share, refused=p["refused"],
                  branch=branch, arm=p["arm"], maker_fill=(nparts["maker"] + nparts["requote"]) / I,
                  parts={a: parts[a] / I for a in parts}, nparts={a: nparts[a] / I for a in nparts}))
print(f"plans {len(P)}; refused {sum(1 for x in P if x['refused'])}")
# ---------- helpers ----------
def wmean(xs, key="cost"):
    W = sum(x["I"] for x in xs); return (sum(x["I"] * x[key] for x in xs) / W) if W else float("nan"), W
def boot(fn, days, n=NBOOT, seed=SEED):
    rng = random.Random(seed); vals = []
    days = sorted(days)
    for _ in range(n):
        smp = [days[rng.randrange(len(days))] for _ in days]
        v = fn(smp)
        if v is not None and not (isinstance(v, float) and math.isnan(v)): vals.append(v)
    vals.sort()
    if not vals: return (float("nan"), float("nan"))
    return vals[int(0.025 * len(vals))], vals[int(0.975 * len(vals)) - 1]
def by_day(xs):
    d = collections.defaultdict(list)
    for x in xs: d[x["day"]].append(x)
    return d
def fmt(v, lo, hi): return f"{v:+.2f} [{lo:+.2f},{hi:+.2f}]"
# ---------- Q1: requote DiD ----------
def did_windows(pre_lo, pre_hi, post_lo, post_hi, label):
    pre = [x for x in P if pre_lo <= x["day"] <= pre_hi]; post = [x for x in P if post_lo <= x["day"] <= post_hi]
    def eff(pre_days, post_days, sample_pre=None, sample_post=None):
        dp = by_day(pre); dq = by_day(post)
        A = [x for d in (sample_pre or sorted(dp)) for x in dp[d]]; B = [x for d in (sample_post or sorted(dq)) for x in dq[d]]
        ra = [x for x in A if x["refused"]]; na = [x for x in A if not x["refused"]]
        rb = [x for x in B if x["refused"]]; nb = [x for x in B if not x["refused"]]
        if not ra or not na or not rb or not nb: return None
        return (wmean(rb)[0] - wmean(nb)[0]) - (wmean(ra)[0] - wmean(na)[0])
    v = eff(None, None)
    dpre, dpost = sorted(by_day(pre)), sorted(by_day(post))
    rng = random.Random(SEED); vals = []
    for _ in range(NBOOT):
        sp = [dpre[rng.randrange(len(dpre))] for _ in dpre]; sq = [dpost[rng.randrange(len(dpost))] for _ in dpost]
        e = eff(None, None, sp, sq)
        if e is not None: vals.append(e)
    vals.sort(); lo, hi = vals[int(0.025 * len(vals))], vals[int(0.975 * len(vals)) - 1]
    ra = [x for x in pre if x["refused"]]; na = [x for x in pre if not x["refused"]]; rb = [x for x in post if x["refused"]]; nb = [x for x in post if not x["refused"]]
    print(f"\n=== Q1 requote DiD · {label}: pre {pre_lo}..{pre_hi} (no requote) vs post {post_lo}..{post_hi} (requote) ===")
    print(f"  refused plans ITT cost (bps/unit intended): pre {wmean(ra)[0]:+.2f} (n={len(ra)}, notional {wmean(ra)[1]:.0f}) | post {wmean(rb)[0]:+.2f} (n={len(rb)}, notional {wmean(rb)[1]:.0f})")
    print(f"  non-refused plans:                           pre {wmean(na)[0]:+.2f} (n={len(na)}) | post {wmean(nb)[0]:+.2f} (n={len(nb)})")
    print(f"  refused fill share: pre {wmean(ra,'fill')[0]:.3f} post {wmean(rb,'fill')[0]:.3f}; maker-leg fill share of refused: pre {wmean(ra,'maker_fill')[0]:.3f} post {wmean(rb,'maker_fill')[0]:.3f}")
    print(f"  ★ DiD effect (post−pre, refused−nonrefused) = {fmt(v, lo, hi)} bps per unit intended notional (negative = requote cheaper)")
    days_post = len(set(x["day"] for x in rb)); per_day = wmean(rb)[1] / max(days_post, 1)
    print(f"  units: refused intended notional {per_day:.0f} USDT/day (post) ⇒ effect ≈ {v * 1e-4 * per_day:+.2f} USDT/day [{lo*1e-4*per_day:+.2f},{hi*1e-4*per_day:+.2f}]")
    return v, lo, hi
did_windows("20260802", "20260805", "20260806", "20260905", "full")
did_windows("20260802", "20260805", "20260806", "20260821", "pre-swap")
did_windows("20260802", "20260805", "20260826", "20260905", "combo era")
# ---------- Q1b: branch decomposition (post) ----------
post = [x for x in P if x["day"] >= "20260806" and x["refused"]]
print("\n=== Q1b post-period refused plans by branch (ITT cost bps/unit intended; parts = cost contribution per unit intended) ===")
tot_I = sum(x["I"] for x in post)
for b in ("requote_filled", "requote_partial", "requote_unfilled", "twice_refused"):
    xs = [x for x in post if x["branch"] == b]
    if not xs: continue
    m, W = wmean(xs); fs = wmean(xs, "fill")[0]
    parts = collections.defaultdict(float)
    for x in xs:
        for a, v in x["parts"].items(): parts[a] += v * x["I"]
    parts = {a: round(v / W, 2) for a, v in parts.items()}
    print(f"  {b:>16}: n={len(xs):4d} share of refused notional {W/tot_I*100:5.1f}%  ITT cost {m:+.2f}  fill {fs:.3f}  parts {parts}")
pre_ref = [x for x in P if "20260802" <= x["day"] <= "20260805" and x["refused"]]
C_reject = wmean(pre_ref)[0]
C_filled = wmean([x for x in post if x["branch"] == "requote_filled"])[0]
C_unf = wmean([x for x in post if x["branch"] in ("requote_unfilled", "requote_partial")])[0]
rested = [x for x in post if x["branch"] in ("requote_filled", "requote_partial", "requote_unfilled")]
p_fill = wmean(rested, "maker_fill")[0]
pstar = (C_reject - C_unf) / (C_filled - C_unf) if C_filled != C_unf else float("nan")
print(f"  08-05 formula on real branches: C_reject(pre, no requote) {C_reject:+.2f} | C_requote_filled {C_filled:+.2f} | C_requote_unfilled/partial {C_unf:+.2f} ⇒ p* = {pstar:.3f} vs realised maker-leg fill share of rested requotes p = {p_fill:.3f}")
# ---------- Q2: behind vs join ----------
def arm_block(lo, hi, label):
    S = [x for x in P if lo <= x["day"] <= hi and x["arm"] in ("join", "behind")]
    def paired(days=None):
        d = by_day(S); xs = [x for dd in (days or sorted(d)) for x in d[dd]]
        per = collections.defaultdict(lambda: {"join": [], "behind": []})
        for x in xs: per[x["rid"]][x["arm"]].append(x)
        num = den = 0.0
        for rid, g in per.items():
            if g["join"] and g["behind"]:
                mj, wj = wmean(g["join"]); mb, wb = wmean(g["behind"]); w = min(wj, wb)
                num += w * (mb - mj); den += w
        return (num / den) if den else None
    v = paired(); lo_, hi_ = boot(lambda smp: paired(smp), sorted(set(x["day"] for x in S)))
    J = [x for x in S if x["arm"] == "join"]; B = [x for x in S if x["arm"] == "behind"]
    print(f"\n=== Q2 behind vs join · {label} ({lo}..{hi}): plans join {len(J)} behind {len(B)} ===")
    print(f"  ITT cost (bps/unit intended): join {wmean(J)[0]:+.2f} | behind {wmean(B)[0]:+.2f} | ★ paired-within-anchor Δ(behind−join) = {fmt(v, lo_, hi_)}")
    for key, name in (("fill", "realised fill share"), ("maker_fill", "maker-leg fill share")):
        print(f"  {name}: join {wmean(J,key)[0]:.3f} behind {wmean(B,key)[0]:.3f}")
    rj = sum(1 for x in J if x["refused"]) / len(J); rb = sum(1 for x in B if x["refused"]) / len(B)
    print(f"  first-attempt -5022 refusal rate: join {rj*100:.1f}% behind {rb*100:.1f}%")
    for a in ("maker", "requote", "topup_from_partial", "topup_from_reject"):
        pj = sum(x["nparts"].get(a, 0) * x["I"] for x in J) / sum(x["I"] for x in J); pb = sum(x["nparts"].get(a, 0) * x["I"] for x in B) / sum(x["I"] for x in B)
        cj = sum(x["parts"].get(a, 0) * x["I"] for x in J) / sum(x["I"] for x in J); cb = sum(x["parts"].get(a, 0) * x["I"] for x in B) / sum(x["I"] for x in B)
        print(f"  part {a:>18}: notional share join {pj:.3f} behind {pb:.3f} | cost contribution join {cj:+.2f} behind {cb:+.2f}")
    # conditional maker fill price vs ref and markout60 from fills.jsonl
    # ★ fills.jsonl is append-only with SUPERSEDING rows per trade_id (markout import/backfill): keep the LAST row per trade
    fk = {}; _last = {}
    for f in fills:
        if f.get("order_type") != "maker": continue
        _last[f.get("trade_id") or (f["symbol"], f.get("fill_ts"))] = f
    for f in _last.values():
        fk.setdefault((f["rebalance_id"], f["symbol"]), []).append(f)
    def mk(xs):
        n = c = m = mn = 0.0
        for x in xs:
            mid = plans[x["k"]]["mid"]; side = plans[x["k"]]["side"]; s = 1.0 if side == "buy" else -1.0
            for f in fk.get(x["k"], []):
                nt = abs(f.get("fill_notional") or 0); px = f.get("fill_px")
                if nt <= 0 or not px: continue
                n += nt; c += nt * s * (px - mid) / mid * 1e4
                m60 = f.get("mid_at_fill_plus_60s")
                if m60: m += nt * s * (m60 - px) / px * 1e4; mn += nt
        return (c / n if n else float("nan")), (m / mn if mn else float("nan")), (mn / n if n else float("nan")), n
    cj, mj, covj, nj = mk(J); cb, mb, covb, nb = mk(B)
    def mdiff(days):
        d = by_day(S); xs = [x for dd in days for x in d[dd]]
        a = mk([x for x in xs if x["arm"] == "behind"])[1]; b = mk([x for x in xs if x["arm"] == "join"])[1]
        return None if (math.isnan(a) or math.isnan(b)) else a - b
    lo2, hi2 = boot(mdiff, sorted(set(x["day"] for x in S)))
    print(f"  maker fill price vs anchor mid (conditional on fill, bps): join {cj:+.2f} behind {cb:+.2f}")
    print(f"  ★ markout60 (positive = favourable): join {mj:+.2f} (cov {covj:.2f}) behind {mb:+.2f} (cov {covb:.2f}) | Δ(behind−join) = {fmt(mb-mj, lo2, hi2)}")
arm_block("20260812", "20260905", "bandit period")
arm_block("20260826", "20260905", "combo era")
print("\nDONE")
