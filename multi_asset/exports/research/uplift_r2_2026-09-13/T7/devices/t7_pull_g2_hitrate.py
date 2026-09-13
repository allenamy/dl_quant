#!/usr/bin/env python3
"""t7_pull_g2_hitrate.py — G2 hit rate on the full history (draft PREREG §2.4 G2; S1 end pinned by the lead at 2026-08-30T20Z; granularity HOURLY). No returns.
FROZEN RULES:
- Anchors N: every 4h from 2021-12-01T04:00Z to 2026-08-30T20:00Z inclusive.
- Bar rule (draft §2.2): o = latest KRW 60m bar open in [N-4h, N-1h]; Binance index 1h bar with open o must exist.
  def A additionally needs the venue's KRW-BTC bar at o and the BTCUSDT index bar at o; def B needs a KRW-USDT bar u in [o-3h, o].
- View U (the draft G2 cell set): mapped pair x anchor with N >= KRW first trading day + 1 d and N inside the symbol's index availability
  [first index bar + 4h, last index bar + 1h] taken from the AFTER-fill series (identical denominators before/after); def B also needs N >= KRW-USDT first day + 1 d.
  def A excludes the KRW-BTC/BTCUSDT pair (identity by construction); def B includes it.
- View E (S1 universe): View U restricted to replay rec anchors (A0 C0) and to the symbol being C0-eligible at N.
- Index versions: BEFORE = monthly zips only (derived/binance); AFTER = monthly plus filled daily zips (derived/binance_filled).
- G4 (adopted by the lead as a pre-declared data-quality exclusion): drop pair x calendar-month cells for months containing identity-guard flagged days
  (diverge or scale-suspect) that lie inside the pair's [elig_first, elig_last]; reported both without and with G4.
- PASS (draft G2): hit rate >= 0.99 for each venue x calendar year x definition in View U. Invalid cells counted by first failing reason.
- The eligibility npz is read from the research repo only after a dataless-flag and bytes-read == st_size guard (iCloud eviction hazard).
Output <root>/checks/G2_HITRATE.json."""
import os, sys, io, json, time, calendar, stat, hashlib, collections, argparse
import numpy as np
ap = argparse.ArgumentParser(); ap.add_argument("--root", required=True); ap.add_argument("--elig", required=True)
ap.add_argument("--test-before-only", action="store_true", help="logic/runtime test before the fill: AFTER is replaced by the monthly series and the output goes to G2_HITRATE_TEST.json")
A = ap.parse_args(); ROOT = A.root
FILLED_DIR = "binance" if A.test_before_only else "binance_filled"
SF_DATALESS = getattr(stat, "SF_DATALESS", 0x40000000)
def guarded_bytes(p):
    st = os.stat(p)
    if st.st_flags & SF_DATALESS: raise SystemExit("REFUSE %s: dataless" % p)
    b = open(p, "rb").read()
    if len(b) != st.st_size: raise SystemExit("REFUSE %s: read %d != st_size %d" % (p, len(b), st.st_size))
    return b
PLAN = json.load(open(ROOT + "/plan/PULL_PLAN_FROZEN.json")); IG = json.load(open(ROOT + "/checks/IDENTITY_GUARD_T7_pull.json"))
eb = guarded_bytes(A.elig); Z = np.load(io.BytesIO(eb), allow_pickle=True)
ELIG_SHA = hashlib.sha256(eb).hexdigest()
SYM = [str(s) for s in Z["symbols"]]; col = {s: i for i, s in enumerate(SYM)}; E_ts = Z["E_ts"].astype(np.int64); EL = Z["elig_C0"]; REC = set(Z["rec_ts_C0"].astype(np.int64).tolist())
erow = {int(t): i for i, t in enumerate(E_ts)}
N0, N1 = calendar.timegm((2021, 12, 1, 4, 0, 0)), calendar.timegm((2026, 8, 30, 20, 0, 0))
N = np.arange(N0, N1 + 1, 14400, dtype=np.int64); yrs = np.array([time.gmtime(int(t)).tm_year for t in N]); mon = np.array([time.strftime("%Y-%m", time.gmtime(int(t))) for t in N])
in_rec = np.array([int(t) in REC for t in N]); ridx = np.array([erow.get(int(t), -1) for t in N])
def load(p):
    if not os.path.exists(p): return None
    z = np.load(p); return np.sort(z["open_s"].astype(np.int64))
first_day = {(v, m["market"]): m["first_day_epoch"] for v in ("upbit", "bithumb") for m in PLAN["krw"][v]}
# G4 exclusion months (computed from the frozen identity-guard receipt)
elig_win = {(p["venue"], p["symbol"]): (calendar.timegm(time.strptime(p["elig_first_utc"][:10], "%Y-%m-%d")), calendar.timegm(time.strptime(p["elig_last_utc"][:10], "%Y-%m-%d"))) for p in PLAN["pairs"]}
G4 = {}
for q in IG["pairs"]:
    if q["status"] in ("PASS", "NO_DATA", "NO_OVERLAP"): continue
    lo, hi = elig_win[(q["venue"], q["symbol"])]; months = set()
    for rng in (q.get("diverge_ranges") or []) + (q.get("scale_suspect_ranges") or []):
        a = calendar.timegm(time.strptime(rng[0], "%Y-%m-%d")); b = calendar.timegm(time.strptime(rng[1], "%Y-%m-%d"))
        for d in range(a, b + 1, 86400):
            if lo <= d <= hi: months.add(time.strftime("%Y-%m", time.gmtime(d)))
    if months: G4[(q["venue"], q["symbol"], q["market"])] = sorted(months)
agg = collections.defaultdict(lambda: collections.Counter())
for v in ("upbit", "bithumb"):
    KB = load(ROOT + "/derived/%s/KRW-BTC_60m.npz" % v); KU = load(ROOT + "/derived/%s/KRW-USDT_60m.npz" % v)
    ufirst = first_day[(v, "KRW-USDT")]
    for ver, ddir in (("BEFORE", "binance"), ("AFTER", FILLED_DIR)):
        IB = load(ROOT + "/derived/%s/BTCUSDT.npz" % ddir)
        for p in [q for q in PLAN["pairs"] if q["venue"] == v]:
            s, m = p["symbol"], p["market"]; K = load(ROOT + "/derived/%s/%s_60m.npz" % (v, m)); I = load(ROOT + "/derived/%s/%s.npz" % (ddir, s)); IA = load(ROOT + "/derived/%s/%s.npz" % (FILLED_DIR, s))
            if K is None or IA is None: agg[(v, "NO_DATA", ver)]["pairs"] += 1; continue
            base = (N >= first_day[(v, m)] + 86400) & (N >= IA[0] + 14400) & (N <= IA[-1] + 3600)
            o = np.full(len(N), -1, np.int64)
            for k in (4, 3, 2, 1):   # later k overwrite earlier => the latest bar wins
                has = np.isin(N - k * 3600, K); o = np.where(has, N - k * 3600, o)
            ov = o >= 0; idx = ov & (np.isin(o, I) if I is not None else False)
            bk = np.isin(o, KB); bi = np.isin(o, IB); fresh = o == N - 3600
            us = np.zeros(len(N), bool)
            for j in range(4): us |= np.isin(o - j * 3600, KU)
            vA = ov & idx & bk & bi; vB = ov & idx & us
            cellsA = base & (s != "BTCUSDT"); cellsB = base & (N >= ufirst + 86400)
            vE = np.zeros(len(N), bool)
            if s in col:
                rv = in_rec & (ridx >= 0); vE[rv] = EL[ridx[rv], col[s]]
            g4 = np.isin(mon, G4.get((v, s, m), []))
            for view, vm in (("U", np.ones(len(N), bool)), ("E", vE)):
                for g4f, gm in (("noG4", np.ones(len(N), bool)), ("G4", ~g4)):
                    for dfn, cells, valid in (("A", cellsA, vA), ("B", cellsB, vB)):
                        c = cells & vm & gm
                        for y in np.unique(yrs[c]):
                            cy = c & (yrs == y); key = (v, int(y), dfn, view, ver, g4f); a = agg[key]
                            a["cells"] += int(cy.sum()); a["valid"] += int((cy & valid).sum()); a["fresh_valid"] += int((cy & valid & fresh).sum())
                            a["NO_KRW_BAR"] += int((cy & ~ov).sum()); a["NO_INDEX_BAR"] += int((cy & ov & ~idx).sum())
                            if dfn == "A": a["NO_BTC_BAR"] += int((cy & ov & idx & ~(bk & bi)).sum())
                            else: a["NO_USDT_BAR"] += int((cy & ov & idx & ~us).sum())
                    if view == "U" and g4f == "G4" and ver == "AFTER":
                        agg[(v, "G4_EXCLUDED_CELLS", s)]["cellsA"] += int((cellsA & g4).sum()); agg[(v, "G4_EXCLUDED_CELLS", s)]["cellsB"] += int((cellsB & g4).sum())
rows = []
for key, a in sorted(agg.items(), key=lambda kv: str(kv[0])):
    if len(key) == 6:
        v, y, dfn, view, ver, g4f = key
        rows.append({"venue": v, "year": y, "def": dfn, "view": view, "index": ver, "g4": g4f, **a, "hit_rate": round(a["valid"] / a["cells"], 6) if a["cells"] else None,
                     "fresh_frac_of_valid": round(a["fresh_valid"] / a["valid"], 6) if a["valid"] else None})
passes = [r for r in rows if r["view"] == "U" and r["index"] == "AFTER"]
out = {"device": os.path.basename(__file__), "device_sha256": hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest(), "run_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
       "elig_npz_sha256": ELIG_SHA, "anchors": [time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime(int(N0))), time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime(int(N1))), int(len(N))],
       "G4_exclusion_months": [{"venue": k[0], "symbol": k[1], "market": k[2], "months": mm} for k, mm in sorted(G4.items())],
       "G4_excluded_cells_viewU": {"%s %s" % (k[0], k[2]): dict(a) for k, a in agg.items() if len(k) == 3 and k[1] == "G4_EXCLUDED_CELLS"},
       "no_data_pairs": {"%s %s" % (k[0], k[2]): dict(a) for k, a in agg.items() if len(k) == 3 and k[1] == "NO_DATA"},
       "pass_rule": "View U, index AFTER: hit_rate >= 0.99 per venue x year x def", "pass_table": [{"venue": r["venue"], "year": r["year"], "def": r["def"], "g4": r["g4"], "hit_rate": r["hit_rate"], "PASS": (r["hit_rate"] or 0) >= 0.99} for r in passes],
       "rows": rows}
json.dump(out, open(ROOT + "/checks/" + ("G2_HITRATE_TEST.json" if A.test_before_only else "G2_HITRATE.json"), "w"), indent=1)
for r in rows:
    if r["view"] in ("U", "E") and r["g4"] == "noG4":
        print(r["venue"], r["year"], r["def"], r["view"], r["index"], "cells", r["cells"], "hit", r["hit_rate"], "fresh", r["fresh_frac_of_valid"], {k: r[k] for k in ("NO_KRW_BAR", "NO_INDEX_BAR", "NO_BTC_BAR", "NO_USDT_BAR") if k in r})
print("G4 months:", out["G4_exclusion_months"])
