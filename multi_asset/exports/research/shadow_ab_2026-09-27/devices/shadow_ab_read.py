"""shadow_ab_read.py — reading device of the forward shadow A/B. Applies docs/DECISION_RULE_forward_shadow_ab_2026-09-27.md (lead,
7f47461e6) mechanically; adds no threshold. Committed before any shadow reading exists.

modes
  health      : identity control, ledger chain, coverage, VOID days, anchors per day. Prints NO arm mean and NO difference variance
                (rule §2: nobody looks at arm means before the end).
  dispersion  : the single week-2 look (rule §2): per arm, the measured SD of the daily difference -> 12-week MDE
                (z 2.39 + 0.84) ; EXTEND_TO_26W if any arm's MDE > 10 bps/day. Prints NO means.
  final       : rule §3 verdicts per arm.
Daily series: UTC day of the anchor; d_day = sum over the day's anchors of (net_arm - net_live) in bps of NAV. A day is VOID for an arm
if any of its 6 anchors is missing / VOID / has no net, or if the day's unknown share (unpriced + funding-unknown |w|, over the day's
total |w| = 2.0 per anchor) exceeds 5 % for the arm or for LIVE_REPLAY. The first 3 days from START_ANCHOR are warm-up (excluded).
usage: shadow_ab_read.py <ledger.jsonl> <START_ANCHOR> health|dispersion|final <out.json>"""
import sys, json, hashlib, collections, time
import numpy as np
LEDGER, START, MODE, OUT = sys.argv[1], int(sys.argv[2]), sys.argv[3], sys.argv[4]
ARMS = ("NOKING", "KHALF", "FUNDONLY"); H4 = 14400; DAY = 86400
Z, ZPOW, B, SEED, BLOCK = 2.39, 0.84, 10000, 20260927, 7
VOID_SHARE = 0.05; WARM_DAYS = 3; MDE_EXTEND = 10.0; W12 = 84


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


lines = open(LEDGER).read().splitlines()
prev = None; chain_ok = True
for l in lines:
    d = json.loads(l)
    if d.get("prev_line_sha256") != prev: chain_ok = False
    prev = hashlib.sha256(l.encode()).hexdigest()
recs = [json.loads(l) for l in lines]
recs = [r for r in recs if r["anchor"] >= START]
warm_end = START + WARM_DAYS * DAY                                     # rule §2: the first 3 days after START are warm-up
warm_end = -(-warm_end // DAY) * DAY                                   # count only complete UTC days from there on
by_day = collections.defaultdict(dict)
for r in recs: by_day[(r["anchor"] // DAY) * DAY][r["anchor"]] = r


def unknown_share(a):
    return (a.get("unpriced_abs_w", 0.0) + a.get("funding_unknown_abs_w", 0.0)) / 2.0


def day_value(day, arm):
    rs = by_day[day]
    if len(rs) != 6: return None, f"{len(rs)} anchors"
    tot, unk_a, unk_l = 0.0, 0.0, 0.0
    for A, r in sorted(rs.items()):
        if r.get("VOID") or not r.get("identity"): return None, "identity VOID anchor"
        a, l = r["arms"].get(arm, {}), r["arms"].get("LIVE_REPLAY", {})
        if a.get("net") is None or l.get("net") is None: return None, "no net (missing book / previous book)"
        tot += a["net"] - l["net"]; unk_a += unknown_share(a); unk_l += unknown_share(l)
    if unk_a / 6 > VOID_SHARE or unk_l / 6 > VOID_SHARE: return None, f"unknown share {max(unk_a, unk_l) / 6:.3f} > 5%"
    return 1e4 * tot, None


days = sorted(d for d in by_day if d >= warm_end)
series, voids = {}, {}
for arm in ARMS:
    v, why = [], collections.Counter()
    for d in days:
        x, reason = day_value(d, arm)
        if x is None: why[reason] += 1
        else: v.append((d, x))
    series[arm] = v; voids[arm] = dict(why)
rec = {"device": "shadow_ab_read.py", "self_sha256": sha(__file__), "mode": MODE, "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
       "rule": "docs/DECISION_RULE_forward_shadow_ab_2026-09-27.md (7f47461e6)", "ledger_sha256": sha(LEDGER), "ledger_lines": len(lines),
       "chain_ok": chain_ok, "start_anchor": START, "warm_up_ends": warm_end, "days_after_warm_up": len(days)}
rec["health"] = {"identity_fail_anchors": [r["anchor"] for r in recs if not r.get("identity")],
                 "anchors_per_day_hist": dict(collections.Counter(len(by_day[d]) for d in days)),
                 "valid_days_per_arm": {a: len(series[a]) for a in ARMS}, "void_days_per_arm": voids,
                 "void_share_per_arm": {a: (sum(voids[a].values()) / len(days)) if days else None for a in ARMS}}


def mbb_se(x):
    x = np.asarray(x); n = len(x); b = min(BLOCK, n); k = int(np.ceil(n / b)); rng = np.random.default_rng(SEED)
    st = rng.integers(0, n - b + 1, size=(B, k)); idx = (st[:, :, None] + np.arange(b)[None, None, :]).reshape(B, k * b)[:, :n]
    return float(x[idx].mean(1).std(ddof=1))


if MODE == "dispersion":
    out = {}
    for arm in ARMS:
        x = np.array([v for _, v in series[arm]])
        if len(x) < 5: out[arm] = {"n_days": len(x), "status": "too few days"}; continue
        sd = float(x.std(ddof=1)); mde = (Z + ZPOW) * sd / np.sqrt(W12)
        mde_mbb = (Z + ZPOW) * mbb_se(x) * np.sqrt(len(x) / W12)
        out[arm] = {"n_days": len(x), "sd_daily_bps": sd, "MDE_12w_bps_per_day": mde, "MDE_12w_mbb_reported_only": mde_mbb}
    rec["dispersion"] = out
    rec["EXTEND_TO_26W"] = bool(any(v.get("MDE_12w_bps_per_day", 0) > MDE_EXTEND for v in out.values()))
elif MODE == "final":
    out = {}
    for arm in ARMS:
        x = np.array([v for _, v in series[arm]])
        if len(x) < 14: out[arm] = {"VERDICT": "UNDECIDED (fewer than 14 valid days)", "n_days": len(x)}; continue
        m, se = float(x.mean()), mbb_se(x); h = len(x) // 2
        m1, m2 = float(x[:h].mean()), float(x[h:].mean()); t = m / se if se > 0 else float("nan")
        if t >= Z and m1 > 0 and m2 > 0: v = "BETTER"
        elif t <= -Z and m1 < 0 and m2 < 0: v = "WORSE"
        else: v = "NO_DIFFERENCE_RESOLVED"
        out[arm] = {"VERDICT": v, "mean_bps_per_day": m, "SE_mbb7": se, "t": t, "first_half": m1, "second_half": m2, "n_days": len(x),
                    "MDE_measured": (Z + ZPOW) * se,
                    "note": "BETTER only supports proposing a switch to the user; the pre-2026 backtest non-inferiority check (rule §3) is still required"}
    rec["final"] = out
open(OUT + ".tmp", "w").write(json.dumps(rec, indent=1)); import os; os.replace(OUT + ".tmp", OUT)
print("SHADOW_AB_READ", MODE, "chain_ok", chain_ok, "days", len(days), json.dumps(rec["health"]["valid_days_per_arm"]),
      json.dumps({k: {kk: vv for kk, vv in v.items() if kk in ("MDE_12w_bps_per_day", "VERDICT")} for k, v in rec.get("dispersion", rec.get("final", {})).items()}))
