#!/usr/bin/env python3
"""t7_s1_build.py — builds the T7 S1 candidate arrays on the Mac, aligned to the A0 meta anchors E_ts (10,182) x 829 panel symbols (frozen PREREG_T7_S1.md §2–§3, §11;
cell rules in t7_s1_common.py). Runs only after t7_s1_guards.py exited 0 (asserted via s1/S1_GUARDS.json STOP == false and its device sha).
Arrays (float32, NaN = invalid), all at anchor N:
  K1 = merged def-A premium; K1_up / K1_bt = venue def-A premium; K1B = merged def-B premium (robustness).
  K2 = K1(N) - K1(N-24h) (merged, both valid); K2_up / K2_bt venue versions; K2B = K1B(N) - K1B(N-24h).
  K3krw = ln(sum over venues of T24_v / Pkrw_USDT_v); K3krw_up / K3krw_bt venue versions (Binance qvk part and the per-anchor median are applied on pod2).
  N-24h values are evaluated at the timestamp N - 86400 with the same rules.
Leakage self-report: (b) leaky construction (bar open == N) cell counts, all of which violate o + 3600 <= N (never saved); (c) maximum (bar open - N) over every valid
  cell used, must be <= -3600.
Output /Users/haosiyu/cc_tmp/krw_pull/s1/T7_S1_CANDIDATES.npz (sha256 from the in-memory bytes) + T7_S1_BUILD_RECEIPT.json."""
import os, sys, io, json, time, calendar, hashlib, stat, collections
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import t7_s1_common as C
DEVICE_SHA = hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest()
COMMON_SHA = hashlib.sha256(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "t7_s1_common.py"), "rb").read()).hexdigest()
OUT = C.ROOT + "/s1"
G = json.load(open(OUT + "/S1_GUARDS.json")); assert G["STOP"] is False and G["common_sha256"] == COMMON_SHA, ("guards not green or common changed", G["STOP"], G["common_sha256"])
G4 = json.load(open(OUT + "/S1_G4_LIST.json")); g4set = {tuple(x) for x in G4["union"]}
ELIG = "/Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/uplift_r2_2026-09-13/T7/receipts/pod2/T7_universe_elig.npz"
st = os.stat(ELIG); assert not (st.st_flags & getattr(stat, "SF_DATALESS", 0x40000000)), "elig npz dataless"
eb = open(ELIG, "rb").read(); assert len(eb) == st.st_size and hashlib.sha256(eb).hexdigest().startswith("a530e123"), "elig npz read/sha"
Z = np.load(io.BytesIO(eb), allow_pickle=True); E = Z["E_ts"].astype(np.int64); SYM = [str(s) for s in Z["symbols"]]; col = {s: i for i, s in enumerate(SYM)}; nA = len(E)
months = np.array([C.month_of(t) for t in E]); months24 = np.array([C.month_of(t) for t in E - 86400])
PLAN = C.plan(); first_day = {(v, m["market"]): m["first_day_epoch"] for v in ("upbit", "bithumb") for m in PLAN["krw"][v]}
G5 = C.load_g5(); IBTC = C.load_index("BTCUSDT"); PBTC = C.load_perp("BTCUSDT")
arr = {k: np.full((nA, len(SYM)), np.nan, dtype=np.float64) for k in ("pA_up", "pA_bt", "pB_up", "pB_bt", "T_up", "T_bt", "X_up", "X_bt", "pA_up24", "pA_bt24", "pB_up24", "pB_bt24", "T_up24", "T_bt24")}
diag = collections.Counter(); maxoff = {"upbit": -10 ** 9, "bithumb": -10 ** 9}; t0 = time.time()
for v, tag in (("upbit", "up"), ("bithumb", "bt")):
    KB = C.derive_krw(v, "KRW-BTC"); KU = C.derive_krw(v, "KRW-USDT")
    for p in [q for q in PLAN["pairs"] if q["venue"] == v]:
        s, mk = p["symbol"], p["market"]
        if s not in col: diag["pair_symbol_not_in_panel"] += 1; continue
        I = C.load_index(s); Pp = C.load_perp(s)
        if I is None or Pp is None: diag["pair_no_index_or_perp"] += 1; continue
        K = C.derive_krw(v, mk); c = col[s]
        common = dict(v=v, krw=K, first_day=first_day[(v, mk)], idx=I, perp=Pp, g5days=G5.get((v, mk), set()), g4set=g4set, sym=s, kbtc=KB, ibtc=IBTC, pbtc=PBTC,
                      g5btc=G5.get((v, "KRW-BTC"), set()), kusdt=KU, g5usdt=G5.get((v, "KRW-USDT"), set()), mult=p["mult"])
        pA, pB, T24, X, dg = C.venue_leg(N=E, months=months, **common)
        pA24, pB24, T2424, _, dg24 = C.venue_leg(N=E - 86400, months=months24, **common)
        _, _, _, _, dgl = C.venue_leg(N=E, months=months, leaky=True, **common)
        for nm, val in (("pA_" + tag, pA), ("pB_" + tag, pB), ("T_" + tag, T24), ("X_" + tag, X), ("pA_%s24" % tag, pA24), ("pB_%s24" % tag, pB24), ("T_%s24" % tag, T2424)):
            fin = np.isfinite(val)
            if np.isfinite(arr[nm][fin, c]).any(): diag["duplicate_symbol_fill_" + nm] += 1
            arr[nm][fin, c] = val[fin]
        used = dg["vA"] | dg["vB"]
        if used.any(): maxoff[v] = max(maxoff[v], int((dg["o"][used] - E[used]).max()))
        used24 = dg24["vA"] | dg24["vB"]
        if used24.any(): maxoff[v] = max(maxoff[v], int((dg24["o"][used24] - (E - 86400)[used24]).max()))
        diag[v + "_leaky_cells"] += int(dgl["has_bar"].sum()); diag[v + "_leaky_cells_violating_G1"] += int((dgl["has_bar"] & ~(dgl["o"] + 3600 <= E)).sum())
print("venue legs done t=%.0fs" % (time.time() - t0), diag, flush=True)
K1 = C.merge([arr["pA_up"], arr["pA_bt"]], [arr["T_up"], arr["T_bt"]]); K1_24 = C.merge([arr["pA_up24"], arr["pA_bt24"]], [arr["T_up24"], arr["T_bt24"]])
K1B = C.merge([arr["pB_up"], arr["pB_bt"]], [arr["T_up"], arr["T_bt"]]); K1B_24 = C.merge([arr["pB_up24"], arr["pB_bt24"]], [arr["T_up24"], arr["T_bt24"]])
with np.errstate(divide="ignore", invalid="ignore"):
    Xs = np.where(np.isfinite(arr["X_up"]) | np.isfinite(arr["X_bt"]), np.nansum(np.stack([arr["X_up"], arr["X_bt"]]), 0), np.nan)
    cand = {"K1": K1, "K1_up": arr["pA_up"], "K1_bt": arr["pA_bt"], "K1B": K1B,
            "K2": K1 - K1_24, "K2_up": arr["pA_up"] - arr["pA_up24"], "K2_bt": arr["pA_bt"] - arr["pA_bt24"], "K2B": K1B - K1B_24,
            "K3krw": np.where(Xs > 0, np.log(Xs), np.nan), "K3krw_up": np.where(arr["X_up"] > 0, np.log(arr["X_up"]), np.nan), "K3krw_bt": np.where(arr["X_bt"] > 0, np.log(arr["X_bt"]), np.nan)}
yrs = np.array([time.gmtime(int(t)).tm_year for t in E])
counts = {k: {int(y): int(np.isfinite(a[yrs == y]).sum()) for y in np.unique(yrs)} for k, a in cand.items()}
assert maxoff["upbit"] <= -3600 and maxoff["bithumb"] <= -3600, ("LEAK (c): bar open after N-1h used", maxoff)
assert diag["upbit_leaky_cells"] == diag["upbit_leaky_cells_violating_G1"] and diag["bithumb_leaky_cells"] == diag["bithumb_leaky_cells_violating_G1"], "LEAK (b) control not all red"
bio = io.BytesIO(); np.savez_compressed(bio, E_ts=E, symbols=np.array(SYM), **{k: v.astype(np.float32) for k, v in cand.items()}); blob = bio.getvalue()
digest = hashlib.sha256(blob).hexdigest(); fp = OUT + "/T7_S1_CANDIDATES.npz"; tmp = fp + ".tmp"
with open(tmp, "wb") as f: f.write(blob); f.flush(); os.fsync(f.fileno())
os.replace(tmp, fp)
rec = {"device": os.path.basename(__file__), "device_sha256": DEVICE_SHA, "common_sha256": COMMON_SHA, "prereg_sha256": "62c6da526ac919304ef464389a0f5024015c37664a9721a11b70f33549f252ac",
       "guards_sha256": hashlib.sha256(open(OUT + "/S1_GUARDS.json", "rb").read()).hexdigest(), "g4_union_n": len(g4set), "candidates_sha256": digest, "candidates_bytes": len(blob),
       "shape": [nA, len(SYM)], "valid_counts_by_year": counts, "leak_c_max_bar_open_minus_N_s": maxoff, "leak_b": {k: v for k, v in diag.items() if "leaky" in k},
       "diag": {k: v for k, v in diag.items() if "leaky" not in k}, "elapsed_s": round(time.time() - t0, 1)}
json.dump(rec, open(OUT + "/T7_S1_BUILD_RECEIPT.json", "w"), indent=1)
print(json.dumps({k: rec[k] for k in ("candidates_sha256", "candidates_bytes", "leak_c_max_bar_open_minus_N_s", "leak_b", "diag")}, indent=1))
