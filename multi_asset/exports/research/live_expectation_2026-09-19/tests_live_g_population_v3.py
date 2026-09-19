#!/usr/bin/env python3
"""live_g_population_v3 的行为测试(合成封存副本; 不读生产账本, 不联网)。含复审 R5B-06 / R5B-07 的反例。"""
import copy, json, math, os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import live_g_population_v3 as G

res = []
def check(name, cond, detail=""):
    res.append(bool(cond)); print(("[PASS] " if cond else "[FAIL] ") + name + (f" — {detail}" if detail else ""))

T0 = 1789000000.0
def win(t0, t1, net):
    return {"from": G.U(t0), "to": G.U(t1), "terms": {"mtm_and_trade_cash": net, "flows": {}, "N": [10000.0, 10000.0], "p": [1.0, 1.0], "b": [0.0, 0.0]}}
def seal_of(wins_spec, anchors, snaps):
    ts = sorted({t for a, b, _ in wins_spec for t in (a, b)})
    return {"windows_4h": [win(a, b, n) for a, b, n in wins_spec],
            "daily_nav_rows": [{"file": "f", "line": i, "row": {"nav_ts": t, "mode": "LIVE"}} for i, t in enumerate(ts)],
            "position_readback_rows": [{"file": "f", "line": i, "row": {"read_ts": t, "symbol": s, "venue_position_notional": v}} for i, (t, s, v) in enumerate(snaps)],
            "anchor_rows": [{"file": "f", "line": i, "row": {"anchor_ts": a, "target_gross": g}} for i, (a, g) in enumerate(anchors)]}

# (a) R5B-06 counterexample: one 8h window, two 4h target segments 100 / 200, net 1 + 2 = 3 ⇒ 3 / 300 = 100 bps (v2 logic: 3/(100·2) = 150)
S = seal_of([(T0, T0 + 28800, 3.0)], [(T0 - 60, 100.0), (T0 + 14400, 200.0)], [(T0, "X", 100.0), (T0 + 28800, "X", 200.0)])
rows = G.build_rows(S); st = G.stats(rows, "D_I")
v = st.get("ratio_of_sums_bps_per_4h", {}).get("net")
check("8h window split at the in-window anchor ⇒ 100 bps (not 150)", st["verdict"] == "OK" and abs(v - 100.0) < 1e-9 and rows[0]["n_segments"] == 2, f"{v} bps, segments {rows[0]['n_segments']}")
_tol = G.ANCHOR_TOL_S; G.ANCHOR_TOL_S = 1e9                      # device mutation: no in-window cuts ⇒ first target held for the whole window (v2 logic)
try:
    try:
        rows_m = G.build_rows(S); vm = G.stats(rows_m, "D_I").get("ratio_of_sums_bps_per_4h", {}).get("net")
    except G.Refused as e:
        vm = f"refused: {e}"
finally:
    G.ANCHOR_TOL_S = _tol
check("device mutation (no segmentation) does NOT give 100 bps — so the test above can fail", vm != 100.0, f"mutated result {vm}")

# (b) R5B-07: target_gross 0 on a losing window ⇒ I main metric refused, population not shrunk
S = seal_of([(T0, T0 + 14400, -39.68), (T0 + 14400, T0 + 28800, 5.0)], [(T0 - 60, 0.0), (T0 + 14340, 100.0)], [(T0, "X", 0.0), (T0 + 14400, "X", 50.0), (T0 + 28800, "X", 60.0)])
rows = G.build_rows(S); st = G.stats(rows, "D_I")
check("zero target_gross ⇒ REFUSED_INVALID_DENOMINATOR with the full population counted", st["verdict"] == "REFUSED_INVALID_DENOMINATOR" and st["n_windows"] == 2 and st["n_invalid"] == 1, str(st))
stN = G.stats(rows, "D_N"); check("N unaffected by the bad target (valid NAV) ⇒ OK over both windows", stN["verdict"] == "OK" and stN["n_windows"] == 2)

# (c) readback conflict
S = seal_of([(T0, T0 + 14400, 1.0)], [(T0 - 60, 100.0)], [(T0, "X", 100.0), (T0, "X", 120.0), (T0 + 14400, "X", 100.0)])
try:
    G.build_rows(S); check("same (read_ts, symbol) with different values ⇒ refused", False)
except G.Refused as e:
    check("same (read_ts, symbol) with different values ⇒ refused", "READBACK_CONFLICT" in str(e), str(e)[:80])

# (d) stale target (> 8h30m old) ⇒ flagged ⇒ I refused
S = seal_of([(T0, T0 + 14400, 1.0)], [(T0 - 9 * 3600, 100.0)], [(T0, "X", 100.0), (T0 + 14400, "X", 100.0)])
rows = G.build_rows(S); st = G.stats(rows, "D_I")
check("target record older than 8h30m ⇒ STALE_TARGET ⇒ I refused", st["verdict"] == "REFUSED_INVALID_DENOMINATOR" and any("STALE_TARGET" in f for f in rows[0]["intent_flags"]))

# (e) unknown snapshot vs true zero
S = seal_of([(T0, T0 + 14400, 1.0)], [(T0 - 60, 100.0)], [(T0, "X", 100.0)])
rows = G.build_rows(S); sh = G.stats_H(rows)
check("missing end snapshot ⇒ H REFUSED_UNKNOWN_SNAPSHOT (unknown is not zero)", sh["verdict"] == "REFUSED_UNKNOWN_SNAPSHOT")
S = seal_of([(T0, T0 + 14400, 0.0), (T0 + 14400, T0 + 28800, 2.0)], [(T0 - 60, 100.0)], [(T0, "X", 0.0), (T0 + 14400, "X", 0.0), (T0 + 28800, "X", 100.0)])
rows = G.build_rows(S); sh = G.stats_H(rows)
check("both ends zero ⇒ true-zero window listed separately, H defined on the rest", sh["verdict"].startswith("OK") and sh["n_windows_true_zero"] == 1 and sh["n_windows_positive"] == 1)

# (f) non-finite input anywhere ⇒ refused
for pos in ("first", "last"):
    S = seal_of([(T0, T0 + 14400, 1.0), (T0 + 14400, T0 + 28800, 1.0)], [(T0 - 60, 100.0)], [(T0, "X", 1.0), (T0 + 14400, "X", 1.0), (T0 + 28800, "X", 1.0)])
    S["windows_4h"][0 if pos == "first" else -1]["terms"]["mtm_and_trade_cash"] = float("nan")
    try:
        G.build_rows(S); check(f"NaN cash term in the {pos} window ⇒ refused", False)
    except G.Refused:
        check(f"NaN cash term in the {pos} window ⇒ refused", True)
S = seal_of([(T0, T0 + 14400, 1.0)], [(T0 - 60, 100.0)], [(T0, "X", float("inf")), (T0 + 14400, "X", 1.0)])
try:
    G.build_rows(S); check("+Inf readback ⇒ refused", False)
except G.Refused:
    check("+Inf readback ⇒ refused", True)

# (g) baseline: a clean 3-window book computes OK on all three denominators
S = seal_of([(T0, T0 + 14400, 1.0), (T0 + 14400, T0 + 28800, -2.0), (T0 + 28800, T0 + 43200, 3.0)], [(T0 - 60, 100.0), (T0 + 14340, 100.0), (T0 + 28740, 100.0)],
            [(T0, "X", 100.0), (T0 + 14400, "X", 100.0), (T0 + 28800, "X", 100.0), (T0 + 43200, "X", 100.0)])
rows = G.build_rows(S)
ok = all(G.stats(rows, k)["verdict"] == "OK" for k in ("D_I", "D_N")) and G.stats_H(rows)["verdict"].startswith("OK")
check("baseline clean book ⇒ I, N, H all OK", ok)
n_fail = res.count(False)
print(f"live_g_population_v3: {'ALL PASS' if not n_fail else 'FAILURES'} {len(res) - n_fail}/{len(res)} checks")
sys.exit(1 if n_fail else 0)
