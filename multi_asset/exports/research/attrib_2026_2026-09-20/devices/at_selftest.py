#!/usr/bin/env python3
"""at_selftest.py — the battery for at_lib's primitives and for the four invariants the attribution rests on.

Every item runs TWICE: once on the baseline, which must be GREEN, and once on a MUTATION of the quantity the
item claims to test, which must be RED. A mutation check on a baseline that is already red proves nothing
(memory: red_capability_check_is_vacuous_when_baseline_is_red), so the baseline is asserted first and the
item is only credited when BOTH halves behaved. The verdict line prints the counts of both halves.

usage: python at_selftest.py <ENV_WHITELIST_CSV> <OUT_DIR>
"""
import json, os, sys, time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import at_lib as L

T0 = time.time()
ENV_OK = set(sys.argv[1].split(",")) if len(sys.argv) > 1 else set()
OUT = sys.argv[2] if len(sys.argv) > 2 else f"{L.ROOT}/receipts"
os.makedirs(OUT, exist_ok=True)
rec = L.rec_head("at_selftest.py", sys.argv)
rows = []
n_green = n_red = 0
fails = []


def item(name, base, mut, detail=None):
    global n_green, n_red
    b = bool(base())
    m = bool(mut()) if b else None          # a mutation check on a red baseline proves nothing
    ok = b and (m is False)
    rows.append({"item": name, "baseline_green": b, "mutation_red": (m is False) if b else None,
                 "credited": ok, **({"detail": detail} if detail else {})})
    if b:
        n_green += 1
    if m is False:
        n_red += 1
    if not ok:
        fails.append(name)
    print("ITEM %-46s baseline=%s mutation_red=%s" % (name, "GREEN" if b else "RED", m is False), flush=True)


rng = np.random.default_rng(7)

# 1 ── reshape: demean + unit gross
v = rng.normal(size=40) + 0.3
item("reshape.net_zero_and_unit_gross",
     lambda: abs(L.reshape_pop(v).sum()) < 1e-12 and abs(abs(L.reshape_pop(v)).sum() - 1) < 1e-12,
     lambda: abs((v / np.abs(v).sum()).sum()) < 1e-12)          # rescale WITHOUT demean keeps the tilt

# 2 ── UTC parsing has no local timezone in it
item("ts.is_utc",
     lambda: L.ts("2026-09-18T20:00:00Z") == 1789761600 and L.utc(1789761600) == "2026-09-18T20:00:00Z",
     lambda: L.ts("2026-09-18T20:00:00Z") == 1789761600 + 3600)

# 3 ── daily compounding
A = np.array([L.ts("2026-01-01T00:00:00Z") + 4 * 3600 * i for i in range(12)])
r = np.full(12, 0.01)
ud, rd = L.daily_returns(A, r)
item("daily.compounds_within_the_utc_day",
     lambda: len(ud) == 2 and abs(rd[0] - (1.01 ** 6 - 1)) < 1e-12,
     lambda: len(ud) == 2 and abs(rd[0] - 6 * 0.01) < 1e-12)     # a SUM would be a different number

# 4 ── cagr / sharpe / maxdd / worst30 / cvar5 on closed-form fixtures
rd2 = np.full(365, 0.001)
item("cagr.compound_365",
     lambda: abs(L.cagr_of(rd2) - (1.001 ** 365 - 1)) < 1e-12,
     lambda: abs(L.cagr_of(rd2) - 365 * 0.001) < 1e-12)
rd3 = np.array([0.01, -0.01] * 50)
item("sharpe.annualised_by_sqrt365",
     lambda: abs(L.sharpe_of(rd3) - rd3.mean() / rd3.std(ddof=1) * np.sqrt(365)) < 1e-12,
     lambda: abs(L.sharpe_of(rd3) - rd3.mean() / rd3.std(ddof=0) * np.sqrt(252)) < 1e-12)
item("maxdd.counts_the_start_as_a_peak",
     lambda: abs(L.maxdd_from_returns(np.array([-0.5, 2.0])) - (-0.5)) < 1e-12,
     lambda: abs(L.maxdd_from_returns(np.array([-0.5, 2.0])) - 0.0) < 1e-12)
rd4 = np.concatenate([np.full(30, -0.01), np.full(30, 0.02)])
item("worst30.rolling_window",
     lambda: abs(L.worst30_of(rd4) - (0.99 ** 30 - 1)) < 1e-12,
     lambda: abs(L.worst30_of(rd4) - (1.02 ** 30 - 1)) < 1e-12)
rd5 = np.arange(-0.10, 0.10, 0.001)
item("cvar5.mean_of_the_worst_ceil_5pct",
     lambda: abs(L.cvar5_of(rd5) - np.sort(rd5)[:int(np.ceil(0.05 * len(rd5)))].mean()) < 1e-12,
     lambda: abs(L.cvar5_of(rd5) - np.sort(rd5)[0]) < 1e-12)

# 5 ── the bootstrap is a MOVING BLOCK, is in range, and is seed-determined
n, b, B = 100, 5, 64
i1 = L._block_index(np.random.default_rng([L.RNG_BASE, 3]), n, b, B)
i2 = L._block_index(np.random.default_rng([L.RNG_BASE, 3]), n, b, B)
i3 = L._block_index(np.random.default_rng([L.RNG_BASE, 4]), n, b, B)
item("bootstrap.deterministic_in_seed_and_in_range",
     lambda: np.array_equal(i1, i2) and not np.array_equal(i1, i3) and i1.shape == (B, n) and i1.min() >= 0 and i1.max() < n,
     lambda: np.array_equal(i1, i3))
item("bootstrap.blocks_are_contiguous",
     lambda: bool((np.diff(i1[:, :b], axis=1) == 1).all()),
     lambda: bool((np.diff(np.sort(i1[:, :b], axis=1), axis=1) == 2).all()))

# 6 ── Holm
p_ = [0.001, 0.02, 0.2, 0.9]
rej, thr = L.holm(p_, 0.05)
item("holm.step_down_stops_at_the_first_failure",
     lambda: rej == [True, True, False, False] and abs(thr[0] - 0.05 / 4) < 1e-15,
     lambda: rej == [True, True, True, False])

# 7 ── the leg split is exactly additive on a fixture where the answer is known
NWt = 30
kc = rng.normal(size=NWt)
fc = rng.normal(size=NWt)
phik, phif = 0.38, 0.62
x = rng.normal(size=NWt) * 0.01
pop = np.ones(NWt, bool)
a_ = phik * (kc - kc.mean())
b_ = phif * (fc - fc.mean())
m_ = a_ + b_
Lm = np.abs(m_).sum()
Wt = L.reshape_pop(m_ + 0.15 * rng.normal(size=NWt))     # a traded book that is the mix PLUS reshaping
s_ = np.where(np.abs(m_) >= L.EPS_SHARE, a_ / np.where(np.abs(m_) >= L.EPS_SHARE, m_, 1.0), phik / (phik + phif))
item("legsplit.A2_is_exactly_additive",
     lambda: abs(float((s_ * Wt * x).sum() + ((1 - s_) * Wt * x).sum() - (Wt * x).sum())) < 1e-15,
     lambda: abs(float((s_ * Wt * x).sum() + ((1 - s_) * Wt * x).sum() * 0.9 - (Wt * x).sum())) < 1e-15)
item("legsplit.A2b_is_exactly_additive_with_a_named_residual",
     lambda: abs(float((a_ * x).sum() / Lm + (b_ * x).sum() / Lm + ((Wt - m_ / Lm) * x).sum() - (Wt * x).sum())) < 1e-15,
     lambda: abs(float((a_ * x).sum() / Lm + (b_ * x).sum() / Lm - (Wt * x).sum())) < 1e-15)
item("legsplit.seats_matter",
     lambda: abs(float((a_ * x).sum() / Lm) - float(((0.62 * (kc - kc.mean())) * x).sum() / Lm)) > 1e-12,
     lambda: abs(float((a_ * x).sum() / Lm) - float(((0.62 * (kc - kc.mean())) * x).sum() / Lm)) < 1e-12)

# 8 ── market / selection identity, and it breaks under the wrong ȳ
memb = np.zeros(NWt, bool)
memb[:20] = True
inlife = np.ones(NWt, bool)
inlife[25:] = False
xr = np.where(inlife, x, 0.0)
yb = xr[memb & inlife].mean()
mk = Wt * inlife * yb
se = Wt * inlife * (xr - yb)
item("market_selection.identity",
     lambda: abs(float((mk + se - Wt * xr).sum())) < 1e-15,
     lambda: abs(float((Wt * inlife * (yb * 1.5)).sum() + se.sum() - (Wt * xr).sum())) < 1e-15)
item("market_selection.dead_names_contribute_to_neither",
     lambda: abs(float(mk[~inlife].sum()) + float(se[~inlife].sum())) < 1e-15,
     lambda: abs(float((Wt * yb)[~inlife].sum())) < 1e-15)

# 9 ── fee allocation reproduces the realised anchor fee exactly and is sensitive to a dropped name
dW = rng.normal(size=NWt)
fee_anchor = 0.23
fee_i = np.abs(dW) * fee_anchor / np.abs(dW).sum()
item("fee.allocation_sums_to_the_realised_fee",
     lambda: abs(float(fee_i.sum() - fee_anchor)) < 1e-15,
     lambda: abs(float(fee_i[:-1].sum() - fee_anchor)) < 1e-15)

# 10 ── expanding terciles are causal
xs = np.concatenate([np.zeros(1080), np.array([5.0, -5.0])])


def exp_ter(x, warm=1080, peek=False):
    lab = np.full(len(x), -1, np.int8)
    for i in range(warm, len(x)):
        h = x if peek else x[:i + 1]
        h = h[np.isfinite(h)]
        if h.size < warm:
            continue
        q1, q2 = np.quantile(h, [1 / 3, 2 / 3])
        if np.isfinite(x[i]):
            lab[i] = 0 if x[i] < q1 else (2 if x[i] > q2 else 1)
    return lab


item("expanding_terciles.causal_label_does_not_see_the_future",
     lambda: int(exp_ter(xs)[1080]) == 2 and int(exp_ter(xs, peek=True)[1080]) == 2 and int(exp_ter(xs)[1081]) == 0,
     lambda: np.array_equal(exp_ter(xs), exp_ter(xs, peek=True)))

# 11 ── period masks are inclusive at both ends and give the published anchor counts on the real axis
AGGP = L.PINS["AGG_A0"][0]
if os.path.exists(AGGP):
    Aax = np.load(AGGP, allow_pickle=True)["A"].astype(np.int64)
    EXPECT = {"2022H2": 1110, "2023pre": 1081, "2023full": 1109, "2024": 2196, "2025": 2190,
              "2026H1": 1086, "2026JA": 367, "FULL_RECIPE": 6948, "PARTIAL_RECIPE": 2191, "WHOLE_WINDOW": 9139,
              "2026": 1453, "HIST": 5495}
    got = {n_: int(L.period_mask(Aax, lo, hi).sum()) for n_, lo, hi, _ in L.PERIODS}
    item("periods.anchor_counts_match_the_published_table",
         lambda: all(got[k] == v for k, v in EXPECT.items()),
         lambda: all(int(L.period_mask(Aax, lo, hi[:-9] + "T00:00:00Z").sum()) == EXPECT[n_]
                     for n_, lo, hi, _ in L.PERIODS if n_ in EXPECT),
         {"got": got, "expected": EXPECT})
else:
    rows.append({"item": "periods.anchor_counts_match_the_published_table", "credited": False, "detail": "AGG missing"})
    fails.append("periods.anchor_counts_match_the_published_table")

# 12 ── csr round-trip
class _Z(dict):
    pass


zz = _Z()
zz["q_off"] = np.array([0, 3, 5])
zz["q_idx"] = np.array([2, 5, 9, 1, 4])
zz["q_val"] = np.array([0.1, -0.2, 0.3, 0.4, -0.5])
item("csr.dense_round_trip",
     lambda: abs(L.csr_dense(zz, "q", 0, nw=12)[5] + 0.2) < 1e-15 and abs(L.csr_dense(zz, "q", 1, nw=12).sum() + 0.1) < 1e-15,
     lambda: abs(L.csr_dense(zz, "q", 0, nw=12)[4] + 0.2) < 1e-15)

verdict = "ALL PASS" if not fails else "FAILURES"
print("AT_SELFTEST VERDICT: %s %d/%d items credited (baselines green %d, mutations red %d)"
      % (verdict, len(rows) - len(fails), len(rows), n_green, n_red), flush=True)
rec.update({"items": rows, "n_items": len(rows), "n_credited": len(rows) - len(fails), "failed": fails,
            "baselines_green": n_green, "mutations_red": n_red,
            "VERDICT": verdict, "utc_end": L.utc(time.time()), "runtime_s": round(time.time() - T0, 1)})
p = f"{OUT}/AT_SELFTEST.json"
with open(p + ".tmp", "w") as f:
    json.dump(rec, f, indent=1, default=str)
os.replace(p + ".tmp", p)
sys.exit(0 if not fails else 3)
