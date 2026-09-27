#!/usr/bin/env python3
"""feas_counts.py — ZERO-RETURN feasibility counts for token-unlock events (docs/FEAS_token_unlock_2026-09-27.md). Reads the DefiLlama public dataset
emissionsIndex.json (downloaded 2026-09-27 ~11:02Z from https://defillama-datasets.llama.fi/emissionsIndex, sha asserted) and the NC LIVE universe U_NC.npz
(t7nc_universe.py, sha 19b9dc35). No price or return is read (the dataset's live tokenPrice field is used only for the ticker symbol).
Counts per UTC year 2023-2026: unique (perp, timestamp) cliff unlocks of category insiders/privateSale whose perp is in LIVE at the anchor containing the
timestamp (timestamps outside the U_NC axis are not counted), by size vs maxSupply; names; timestamp hour-of-day; unmapped protocols.
usage: python3 feas_counts.py <emissionsIndex.json> <U_NC.npz> <out.json>"""
import sys, json, time, hashlib, collections
import numpy as np
EIDX, UNC, OUT = sys.argv[1:4]
def fsha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()
assert fsha(EIDX).startswith("4815100c35c797f2"), fsha(EIDX); assert fsha(UNC).startswith("19b9dc35ab86b232")
d = json.load(open(EIDX))["data"]
U = np.load(UNC); ue = U["E_ts"].astype(np.int64); us = [str(s) for s in U["symbols"]]; UU = U["U"]; col = {s: i for i, s in enumerate(us)}
def perp(sym):
    for c in (sym + "USDT", "1000" + sym + "USDT", "1000000" + sym + "USDT", "1M" + sym + "USDT"):
        if c in col: return c
agg = collections.defaultdict(float); maxs = {}; mapped = set(); unmapped = []
for p in d:
    sym = (p.get("tokenPrice") or [{}])[0].get("symbol"); ps = perp(sym.upper()) if sym else None
    if not ps:
        if p.get("events"): unmapped.append([p["name"], sym])
        continue
    mapped.add(p["name"]); maxs[ps] = p.get("maxSupply") or 0
    for e in p.get("events") or []:
        if e.get("unlockType") == "cliff" and e.get("category") in ("insiders", "privateSale"):
            agg[(ps, int(e["timestamp"]))] += sum(x for x in (e.get("noOfTokens") or []) if x)
rep = {"device": "feas_counts.py", "self_sha256": fsha(__file__), "emissionsIndex_sha256": fsha(EIDX), "U_NC_sha256": fsha(UNC), "zero_returns": True,
       "protocols": len(d), "protocols_with_events": sum(1 for p in d if p.get("events")), "protocols_mapped_to_a_perp": len(mapped),
       "protocols_with_events_unmapped": len(unmapped), "unmapped_first20": unmapped[:20], "per_year": {}, "hour_of_day_top": None}
hours = collections.Counter(); per = collections.defaultdict(collections.Counter); names = collections.defaultdict(set); pn = collections.defaultdict(collections.Counter)
for (ps, t), tok in agg.items():
    if t < ue[0] or t > ue[-1] + 14400: continue
    i = int(np.searchsorted(ue, t, side="right") - 1)      # anchor containing t
    if not UU[i, col[ps]]: continue
    y = time.gmtime(t).tm_year; f = tok / maxs[ps] if maxs[ps] else float("nan"); hours[time.gmtime(t).tm_hour] += 1
    per[y]["unique_events_in_LIVE"] += 1
    for th, lab in ((0.005, "ge0.5pct_maxsupply"), (0.01, "ge1pct_maxsupply"), (0.02, "ge2pct_maxsupply")):
        if f >= th: per[y][lab] += 1
    if f != f: per[y]["no_maxsupply"] += 1
    if f >= 0.01: names[y].add(ps); pn[y][ps] += 1
for y in sorted(per):
    rep["per_year"][y] = {**per[y], "names_ge1pct": len(names[y]), "max_events_per_name_ge1pct": max(pn[y].values()) if pn[y] else 0}
rep["hour_of_day_top"] = hours.most_common(5); rep["share_at_00Z"] = round(hours[0] / max(sum(hours.values()), 1), 3)
json.dump(rep, open(OUT, "w"), indent=1); print(json.dumps(rep["per_year"]), rep["hour_of_day_top"], rep["share_at_00Z"])
