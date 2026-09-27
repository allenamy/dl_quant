#!/usr/bin/env python3
"""t7_g2_split.py — ZERO-RETURN diagnostic ordered by the lead's RULING_G2_red_2026-09-27.md (9a3efb684) §1: split every G2 miss of the frozen
t7_s1_guards.py into its causes; counts only. Committed before it is run. Reuses the frozen cell rules (t7_s1_common.py, sha asserted), the G4 union
list the frozen guards wrote (S1_G4_LIST.json, sha recorded) and the G2 cell/denominator definition copied verbatim from t7_s1_guards.py L88-91.

For every G2 cell that is NOT valid, non-exclusive flags (all that fail):
  coin_no_bar           no KRW coin bar with volume > 0 in [N-4h, N-1h]
  coin_no_index         bar present, no Binance index bar at o
  coin_perp_missing     no Binance perp kline at o (data gap: kline absent)
  coin_perp_zero_trades perp kline at o with count == 0          (§11.11 no-trade hour)
  coin_g5_o_day         coin market's G5 day containing o (the denominator only excludes the G5 day containing N-1h)
  btc_no_bar / btc_no_index / btc_perp_missing / btc_perp_zero_trades / btc_g5_day      (def A BTC leg)
  usdt_no_bar / usdt_g5_day                                                            (def B USDT leg)
Exclusive attribution under the ruling §2(b), applied strictly as written: a miss is RULE_EXCLUDED iff every failing flag is in
  {coin_perp_zero_trades, btc_perp_zero_trades, btc_g5_day};  otherwise it stays a miss. The ambiguous flags (coin_perp_missing, btc_perp_missing,
  coin_g5_o_day) are counted and listed, never excluded here (the lead applies the ruling).
Reported per venue x year x def: cells, valid, frozen hit rate, flag counts, RULE_EXCLUDED, hit rate under (b), and the pure-cause counts.
Output /Users/haosiyu/cc_tmp/krw_pull/s1/T7_G2_SPLIT.json (sha from the written bytes)."""
import os, sys, json, time, calendar, collections, hashlib
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import t7_s1_common as C
DEV = os.path.dirname(os.path.abspath(__file__))
def fsha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()
COMMON_SHA = fsha(os.path.join(DEV, "t7_s1_common.py")); assert COMMON_SHA.startswith("d25214665291aa84"), COMMON_SHA   # == S1_GUARDS.json common_sha256
OUT = C.ROOT + "/s1"
GJ = json.load(open(OUT + "/S1_GUARDS.json")); assert GJ["common_sha256"] == COMMON_SHA
G4 = json.load(open(OUT + "/S1_G4_LIST.json")); g4set = {tuple(x) for x in G4["union"]}
PLAN = C.plan(); first_day = {(v, m["market"]): m["first_day_epoch"] for v in ("upbit", "bithumb") for m in PLAN["krw"][v]}
G5 = C.load_g5()
N0, N1 = calendar.timegm((2021, 12, 1, 4, 0, 0)), calendar.timegm((2026, 8, 30, 20, 0, 0))
N = np.arange(N0, N1 + 1, 14400, dtype=np.int64); yrs = np.array([time.gmtime(int(t)).tm_year for t in N]); months = np.array([C.month_of(t) for t in N])
assert [int(N[0]), int(N[-1]), int(N.size)] == GJ["grid"], ("grid differs from the frozen guards run", GJ["grid"])
IBTC = C.load_index("BTCUSDT"); PBTC = C.load_perp("BTCUSDT")
FLAGS = ("coin_no_bar", "coin_no_index", "coin_perp_missing", "coin_perp_zero_trades", "coin_g5_o_day", "btc_no_bar", "btc_no_index", "btc_perp_missing",
         "btc_perp_zero_trades", "btc_g5_day", "usdt_no_bar", "usdt_g5_day")
RULE = {"coin_perp_zero_trades", "btc_perp_zero_trades", "btc_g5_day"}
agg = collections.defaultdict(lambda: collections.Counter()); t0 = time.time()
for v in ("upbit", "bithumb"):
    KB = C.derive_krw(v, "KRW-BTC"); KU = C.derive_krw(v, "KRW-USDT"); ufirst = first_day[(v, "KRW-USDT")]
    g5btc = G5.get((v, "KRW-BTC"), set()); g5usdt = G5.get((v, "KRW-USDT"), set())
    for p in [q for q in PLAN["pairs"] if q["venue"] == v]:
        s, mk = p["symbol"], p["market"]; K = C.derive_krw(v, mk); I = C.load_index(s); Pp = C.load_perp(s)
        if I is None or Pp is None: continue
        g5c = G5.get((v, mk), set())
        pA, pB, _, _, dg = C.venue_leg(v=v, N=N, months=months, krw=K, first_day=first_day[(v, mk)], idx=I, perp=Pp, g5days=g5c, g4set=g4set, sym=s,
                                       kbtc=KB, ibtc=IBTC, pbtc=PBTC, g5btc=g5btc, kusdt=KU, g5usdt=g5usdt, mult=p["mult"])
        # G2 cells: verbatim from t7_s1_guards.py
        win = (N >= first_day[(v, mk)] + 86400) & (N >= I["open_s"][0] + 14400) & (N <= I["open_s"][-1] + 3600) & (N >= Pp["open_s"][0] + 14400) & (N <= Pp["open_s"][-1] + 3600)
        excl = dg["g4bad"] | np.isin(C.day_keys(v, N - 3600), list(g5c))
        cA = win & ~excl & (s != "BTCUSDT"); cB = win & ~excl & (N >= ufirst + 86400)
        # flags (recomputed with the same helpers as venue_leg)
        o = dg["o"]; has = dg["has_bar"]
        pc = C.at(Pp["open_s"], o); pmiss = has & dg["idx_ok"] & (pc < 0); pzero = has & dg["idx_ok"] & (pc >= 0) & (Pp["count"][np.maximum(pc, 0)] == 0)
        dk = C.day_keys(v, o); cg5 = has & np.isin(dk, list(g5c)) if g5c else np.zeros(N.size, bool)
        bk = C.at(KB["open_s"], o); bi = C.at(IBTC["open_s"], o); bp = C.at(PBTC["open_s"], o)
        bnb = has & (bk < 0); bni = has & (bi < 0); bpm = has & (bp < 0); bpz = has & (bp >= 0) & (PBTC["count"][np.maximum(bp, 0)] == 0)
        bg5 = has & np.isin(dk, list(g5btc)) if g5btc else np.zeros(N.size, bool)
        iu = C.latest_in(KU["open_s"], o - 3 * 3600, o); unb = has & (iu < 0)
        du = C.day_keys(v, np.where(iu >= 0, KU["open_s"][np.maximum(iu, 0)], -1)); ug5 = has & (iu >= 0) & np.isin(du, list(g5usdt)) if g5usdt else np.zeros(N.size, bool)
        common = {"coin_no_bar": ~has, "coin_no_index": has & ~dg["idx_ok"], "coin_perp_missing": pmiss, "coin_perp_zero_trades": pzero, "coin_g5_o_day": cg5}
        legs = {"A": {"btc_no_bar": bnb, "btc_no_index": bni, "btc_perp_missing": bpm, "btc_perp_zero_trades": bpz, "btc_g5_day": bg5},
                "B": {"usdt_no_bar": unb, "usdt_g5_day": ug5}}
        for dfn, cells, valid in (("A", cA, dg["vA"]), ("B", cB, dg["vB"])):
            F = {**common, **legs[dfn]}; miss = cells & ~valid
            anyflag = np.zeros(N.size, bool)
            for f in F.values(): anyflag |= f
            nonrule = np.zeros(N.size, bool)
            for k, f in F.items():
                if k not in RULE: nonrule |= f
            rule_only = miss & anyflag & ~nonrule
            for y in np.unique(yrs[cells]):
                cy = cells & (yrs == y); a = agg[(v, int(y), dfn)]; my = miss & (yrs == y)
                a["cells"] += int(cy.sum()); a["valid"] += int((cy & valid).sum()); a["miss"] += int(my.sum())
                for k, f in F.items(): a["flag_" + k] += int((my & f).sum())
                a["RULE_EXCLUDED"] += int((rule_only & (yrs == y)).sum()); a["miss_no_flag"] += int((my & ~anyflag).sum())
                for k, f in F.items():
                    others = np.zeros(N.size, bool)
                    for k2, f2 in F.items():
                        if k2 != k: others |= f2
                    a["pure_" + k] += int((my & f & ~others).sum())
rows = []
for (v, y, dfn), a in sorted(agg.items()):
    c, val, rx = a["cells"], a["valid"], a["RULE_EXCLUDED"]
    rows.append({"venue": v, "year": y, "def": dfn, "cells": c, "valid": val, "hit_frozen": round(val / max(c, 1), 6), "RULE_EXCLUDED": rx,
                 "hit_under_b": round(val / max(c - rx, 1), 6), "in_eval_years": y in (2023, 2024, 2025, 2026),
                 **{k: a[k] for k in sorted(a) if k.startswith(("flag_", "pure_")) or k in ("miss", "miss_no_flag")}})
rec = {"device": "t7_g2_split.py", "self_sha256": fsha(os.path.abspath(__file__)), "common_sha256": COMMON_SHA, "guards_receipt_sha256": fsha(OUT + "/S1_GUARDS.json"),
       "g4_list_sha256": fsha(OUT + "/S1_G4_LIST.json"), "ruling": "RULING_G2_red_2026-09-27.md 9a3efb684", "zero_returns": True,
       "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "rule_set_b": sorted(RULE), "rows": rows, "elapsed_s": round(time.time() - t0, 1)}
# consistency with the frozen guards run: cells / valid per venue x year x def must equal S1_GUARDS.json G2 rows
fz = {(r["venue"], r["year"], r["def"]): (r["cells"], r["hit_rate"]) for r in GJ["G2"]["rows"]}
rec["matches_frozen_G2"] = all(fz.get((r["venue"], r["year"], r["def"]), (None,))[0] == r["cells"] and abs(fz[(r["venue"], r["year"], r["def"])][1] - r["hit_frozen"]) < 1e-5 for r in rows) and len(fz) == len(rows)
blob = json.dumps(rec, indent=1).encode(); p = OUT + "/T7_G2_SPLIT.json"
with open(p + ".tmp", "wb") as f: f.write(blob); f.flush(); os.fsync(f.fileno())
os.replace(p + ".tmp", p); assert fsha(p) == hashlib.sha256(blob).hexdigest()
print("T7_G2_SPLIT DONE", hashlib.sha256(blob).hexdigest()[:16], "matches_frozen_G2", rec["matches_frozen_G2"], flush=True)
for r in rows:
    if r["in_eval_years"]: print(r["venue"], r["year"], r["def"], "hit_frozen", r["hit_frozen"], "RULE_EXCLUDED", r["RULE_EXCLUDED"], "hit_under_b", r["hit_under_b"], flush=True)
