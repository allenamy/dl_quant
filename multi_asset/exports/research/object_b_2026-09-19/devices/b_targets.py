#!/usr/bin/env python3
"""Object B targets + descriptive receipts from a P3 run (PREREG §1, §2, §4 windows; AMENDMENT 3 A3.3 dead-name exposure). No returns, no prices.
Inputs: work/<tag>/P3.json (records) + P3.vec.npz. Outputs: work/<tag>/TARGETS_<tag>.npz and receipts/TARGETS_<tag>.json.

Per reading R in {scaled (main), lit (as coded), scaled_l333_only (sensitivity)} and anchor A:
  kind[A] = 2 combo (the combo target file) | 1 king (the producer's king file: preflight failed or known crash) | 0 hold (producer skipped: no new file)
  weights[A] = the file's weights (empty on hold). The executor's on_unavailable = hold carries the previous book (the simulator's rule, not done here).
B_CORE start (PREREG §4) = first anchor whose seat window (the last 900 king leg-return entries, msharpe_look = 900) consists only of entries scored from
anchors where the king leg was served (fold admissible, finite predictions). Each LR entry appended at anchor A scores the previous anchor A − 4h
(producer step 6), so its source anchor is the previous record's anchor.
Dead-name exposure (named limitation, AMENDMENT 3 A3.3): share of gross (Σ|w|) of the target on names that are dead (tradability_v1 last traded bar
< data_end − 3 d) with A > last traded bar; per UTC year, on written targets and on hold-carried effective targets."""
import os, sys, json, time, collections
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import b_lib as BL
import b_driver as BD

tag = sys.argv[1]; W = f"{BD.R}/work/{tag}"
D = json.load(open(f"{W}/P3.json")); recs = D["records"]; Z = np.load(f"{W}/P3.vec.npz"); V = {k: Z[k] for k in Z.files}
assert len(recs) == len(V["anchor"]) and all(int(r["anchor"]) == int(a) for r, a in zip(recs, V["anchor"]))
G = BD.Globals(load_cache=False); LE = G.LE
yr = lambda A: str(time.gmtime(int(A)).tm_year)


def vec(name, k):
    a, b = V[name + "_off"][k], V[name + "_off"][k + 1]; return V[name + "_idx"][a:b].astype(np.int64), V[name + "_val"][a:b]


READ = {"scaled": "traded_scaled", "lit": "traded_lit", "scaled_l333_only": "traded_scaled_l333_only"}
out = {"anchor": V["anchor"]}; stats = {}
for R_, key in READ.items():
    kinds = []; idxs = []; vals = []; offs = [0]
    cnt = collections.defaultdict(collections.Counter); expo = collections.defaultdict(lambda: collections.defaultdict(float))
    eff = None
    for k, r in enumerate(recs):
        A = int(r["anchor"]); t = r.get(key) or ("hold(producer_skip)" if not r.get("wrote") else None)
        if t == "combo": kd = 2; i_, v_ = vec("combo", k)
        elif t == "king": kd = 1; i_, v_ = vec("king_file", k)
        else: kd = 0; i_, v_ = np.zeros(0, np.int64), np.zeros(0)
        kinds.append(kd); idxs.append(i_); vals.append(v_); offs.append(offs[-1] + len(i_))
        cnt[yr(A)][{0: "hold", 1: "king", 2: "combo"}[kd]] += 1
        if (r.get("combo") or {}).get("known_crash"): cnt[yr(A)]["known_crash"] += 1
        if kd: eff = (i_, v_)
        dead_now = LE.dead & (A > LE.last)
        for lab, iv in (("written", (i_, v_) if kd else None), ("effective", eff)):
            if iv is None or not len(iv[0]): continue
            g = float(np.abs(iv[1]).sum()); gd = float(np.abs(iv[1][dead_now[iv[0]]]).sum())
            expo[yr(A)][lab + "_gross"] += g; expo[yr(A)][lab + "_dead_gross"] += gd; expo[yr(A)][lab + "_dead_anchor_cells"] += int(dead_now[iv[0]].sum())
    out[f"{R_}_kind"] = np.array(kinds, np.int8); out[f"{R_}_off"] = np.array(offs, np.int64)
    out[f"{R_}_idx"] = np.concatenate(idxs).astype(np.int16) if offs[-1] else np.zeros(0, np.int16); out[f"{R_}_val"] = np.concatenate(vals) if offs[-1] else np.zeros(0)
    stats[R_] = {"counts_by_year": {y: dict(c) for y, c in sorted(cnt.items())},
                 "dead_name_exposure_by_year": {y: {"written_share": (e["written_dead_gross"] / e["written_gross"]) if e["written_gross"] else None,
                                                    "effective_share": (e["effective_dead_gross"] / e["effective_gross"]) if e["effective_gross"] else None,
                                                    "written_name_anchor_cells": int(e["written_dead_anchor_cells"])} for y, e in sorted(expo.items())}}
# served folds + B_CORE start
served = {}; fold_by_year = collections.defaultdict(collections.Counter); f10_by_year = collections.defaultdict(collections.Counter)
for r in recs:
    kg = r.get("king") or {}; served[int(r["anchor"])] = bool(kg.get("fold") is not None and (kg.get("n_finite") or 0) > 0)
    fold_by_year[yr(r["anchor"])][str(kg.get("fold"))] += 1; f10_by_year[yr(r["anchor"])][str((r.get("f10") or {}).get("fold"))] += 1
window = collections.deque(maxlen=900); bcore = None; prev_A = None; prev_len = 0
for r in recs:
    A = int(r["anchor"]); L = int(r.get("lr_len") or 0)
    if L > prev_len and prev_A is not None:
        for _ in range(L - prev_len): window.append(served.get(prev_A, False))
    prev_len = L; prev_A = A
    if bcore is None and len(window) == 900 and all(window): bcore = A
first_served = next((int(r["anchor"]) for r in recs if served[int(r["anchor"])]), None)
f10_first = next((int(r["anchor"]) for r in recs if (r.get("f10") or {}).get("fold") is not None), None)
doc = {"tag": tag, "comparison_type": "(1) historical recipe — object B (targets only; no returns)", "p3_json_sha256": BL.sha(f"{W}/P3.json"),
       "p3_vec_sha256": BL.sha(f"{W}/P3.vec.npz"), "n_anchors": len(recs), "axis": [BL.iso(recs[0]["anchor"]), BL.iso(recs[-1]["anchor"])],
       "readings": stats, "king_fold_served_by_year": {y: dict(c) for y, c in sorted(fold_by_year.items())},
       "f10_fold_served_by_year": {y: dict(c) for y, c in sorted(f10_by_year.items())}, "king_first_served": BL.iso(first_served) if first_served else None,
       "f10_first_served": BL.iso(f10_first) if f10_first else None, "B_CORE_start": BL.iso(bcore) if bcore else None,
       "B_CORE_rule": "first anchor whose last 900 king LR entries all come from king-served anchors (PREREG §4)",
       "PRE_window": ["2022-06-30T00:00:00Z", BL.iso(bcore - BL.H4) if bcore else None, "PARTIAL_RECIPE — seat warm-up / missing legs; not the production strategy"],
       "tradability_sha256": G.shas["tradability"], "self_sha256": BL.sha(os.path.abspath(__file__)), "utc": BL.iso(time.time())}
np.savez_compressed(f"{W}/TARGETS_{tag}.npz", **out)
doc["targets_npz_sha256"] = BL.sha(f"{W}/TARGETS_{tag}.npz")
json.dump(doc, open(f"{BD.R}/receipts/TARGETS_{tag}.json", "w"), indent=1)
print(json.dumps({k: doc[k] for k in ("axis", "king_first_served", "f10_first_served", "B_CORE_start")}), flush=True)
for R_ in stats: print(R_, json.dumps(stats[R_]["counts_by_year"]), json.dumps({y: round(v["written_share"] or 0, 6) for y, v in stats[R_]["dead_name_exposure_by_year"].items()}))
