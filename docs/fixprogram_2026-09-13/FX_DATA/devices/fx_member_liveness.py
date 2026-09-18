#!/usr/bin/env python3
"""FP3 F (2026-09-18): how many TRAINING member cells belong to names with NO LIVE BAR in the previous 24 h (all 288 five-minute rows hole-filled or NaN)?
Liveness by bars (the venue trades or not), not by funding records (the research funding panel has coverage gaps that would misclassify traded names).
Inputs: the 5m cache, its hole-fill cell list, the king meta member sets, the DL targets symbol axis. Output: per-year counts + top names. Read-only.
usage: fx_member_liveness.py <cache.npz> <holefix_cells.npz> <king_meta.npz> <dlw_targets.npz> <out.json>"""
import json, sys, time, hashlib, collections, numpy as np
CP, HP, KP, DP, OUT = sys.argv[1:6]; sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
C = np.load(CP, allow_pickle=True); cts = C["ts"].astype(np.int64); nT, nS = C["data"].shape[:2]; csym = [str(s) for s in C["symbols"]]
H = np.load(HP, allow_pickle=True); filled = np.zeros((nT, nS), bool); filled[H["row"].astype(int), H["col"].astype(int)] = True
notlive = filled | np.isnan(C["data"][:, :, 3].astype(np.float32)); cs = np.cumsum(notlive, axis=0, dtype=np.int32); W = 288
m = np.load(KP, allow_pickle=True); E = m["E_ts"].astype(np.int64); M = m["members"]; syms = [str(s) for s in np.load(DP, allow_pickle=True)["symbols"]]; cidx = np.array([csym.index(s) for s in syms]); pos = {int(t): i for i, t in enumerate(cts)}
by = collections.defaultdict(lambda: [0, 0]); dead = collections.Counter(); runs = collections.defaultdict(list)
for i, t in enumerate(E):
    r = pos.get(int(t))
    if r is None or r < W: continue
    mem = cidx[np.asarray(M[i]).astype(int)]; cnt = cs[r, mem] - cs[r - W, mem]; y = time.strftime("%Y", time.gmtime(int(t))); by[y][0] += len(mem); d = cnt >= W; by[y][1] += int(d.sum())
    for j in mem[d]: dead[csym[j]] += 1; runs[csym[j]].append(int(t))
out = {"device": "fx_member_liveness.py", "self_sha256": sha(__file__), "utc": time.strftime("%FT%TZ", time.gmtime()), "inputs": {CP: sha(CP), HP: sha(HP), KP: sha(KP), DP: sha(DP)}, "rule_measured": "member cell is DEAD-BUT-MEMBER when every 5m row of the previous 24h is hole-filled or NaN",
       "by_year": {y: {"member_cells": v[0], "dead_but_member": v[1], "pct": round(v[1] / v[0] * 100, 3)} for y, v in sorted(by.items())}, "n_names": len(dead), "top_names": dead.most_common(25),
       "spans": {s: [time.strftime("%m-%d %HZ", time.gmtime(min(v))), time.strftime("%m-%d %HZ", time.gmtime(max(v))), len(v)] for s, v in sorted(runs.items(), key=lambda kv: -len(kv[1]))[:25]},
       "proposed_rule": "training/serving member ⇒ at least one live (non-filled, non-NaN) 5m bar in the previous 24h; expected effect ≤ 1% of member cells, concentrated after delistings (2026-08 tokenized-stock perps, 2026-09 ICX/SCRT/STORJ)"}
json.dump(out, open(OUT, "w"), indent=1); print(out["by_year"], "names", out["n_names"])
