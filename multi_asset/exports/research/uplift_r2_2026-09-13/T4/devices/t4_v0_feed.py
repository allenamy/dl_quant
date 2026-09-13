#!/usr/bin/env python3
"""t4_v0_feed.py — Mac, read-only (PREREG_T4 §6 "v0 feed"). For the 450 symbols_live names and the 41 chained anchors:
rows = in-service bundle funding_ledger_seed.json rows strictly BEFORE the first row of the production ledger tail, then the
production ledger tail itself (snapshot aux.json) — so from the tail's first row on, v0 sees exactly the rows production applied.
v0  : acc0 = raw rate of the first row; acc += a*(rate - acc), a = 1 - 0.5**(max(ft - last, 1)/(3*86400))   (shadow_loop_v3.py L345-349 without 8/iv)
v1r : the same recursion on rate*(8/iv) with the row's recorded iv (reconstruction check against the served column 80, GATE V1R)
value at anchor A = state after all rows with ft <= A. Also: start-up residual weight 0.5**((last_ft<=A - first_ft)/3d), and the
seed-vs-production overlap audit (rows present in both with different rate; rows in one source only, inside the tail's span).
Output: T4/private/v0_feed.npz + receipts/RECEIPT_T4_v0_feed.json.
Launch: env -i PATH=/usr/bin:/bin HOME=/Users/haosiyu /usr/bin/python3 -B devices/t4_v0_feed.py <whitelist>"""
import os, sys, json, time, hashlib
WHITE = set(x for x in sys.argv[1].split(",") if x) if len(sys.argv) > 1 else None
assert WHITE, "whitelist argv[1]"
assert sorted(k for k in os.environ if k not in WHITE) == [], ("ENV WHITELIST VIOLATION", sorted(os.environ))
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); T4 = os.path.dirname(HERE)
def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()
PREREG_SHA = "0f94b754c9ca4c6e65c3f2a63146dab7036f37862abd2210cbbfcef661aab4dd"; assert sha(T4 + "/PREREG_T4_king_feature_skew_2026-09-13.md") == PREREG_SHA
SNAP = T4 + "/private/snapshot_1789272000"; AUX = SNAP + "/state/aux.json"
SEED = "/Users/haosiyu/wide_shadow/shadow_bundle/funding_ledger_seed.json"; CFG = "/Users/haosiyu/wide_shadow/shadow_bundle/config.json"
INPUTS = {AUX: sha(AUX), SEED: sha(SEED), CFG: sha(CFG)}
assert INPUTS[AUX] == "4dc0aafec4e2f5682de14c756397f14a80a4c0c4e96870cc4d9fad7c632e84a7" and INPUTS[SEED] == "85f1a1dbb2629f0f1164eb96d5b7c7a9c2f2e4484213042ce28abff3caa96740", INPUTS
cfg = json.load(open(CFG)); syms = cfg["symbols_panel"]; live = cfg["symbols_live"]; jof = {s: j for j, s in enumerate(syms)}
aux = json.load(open(AUX)); LED = aux["ledger_tail"]; seed = json.load(open(SEED))
ANCH = list(range(1788624000, 1789200000 + 1, 14400)); assert len(ANCH) == 41
HL = 3 * 86400.0
V0 = np.full((len(ANCH), 829), np.nan); V1R = np.full((len(ANCH), 829), np.nan); RES = np.full((len(ANCH), 829), np.nan); LASTFT = np.full((len(ANCH), 829), np.nan)
audit = dict(names=0, names_no_prod_rows=0, seed_rows_used=0, prod_rows_used=0, overlap_rows=0, overlap_rate_mismatch=0, overlap_rate_maxabs=0.0,
             seed_only_rows_inside_tail_span=0, prod_only_rows_inside_seed_span=0, names_seed_ends_before_tail_starts=[])
for s in live:
    j = jof.get(s)
    if j is None: continue
    prod = [(int(r[0]), float(r[1]), float(r[2]) if (len(r) > 2 and r[2]) else 8.0) for r in LED.get(s, [])]
    sd = [(int(r[0]), float(r[1]), float(r[2]) if (len(r) > 2 and r[2] == r[2] and r[2]) else 8.0) for r in seed.get(s, [])]
    audit["names"] += 1
    if not prod: audit["names_no_prod_rows"] += 1; continue
    p0 = prod[0][0]; pset = {t: (r, i) for t, r, i in prod}; sset = {t: (r, i) for t, r, i in sd}
    if sd and sd[-1][0] < p0: audit["names_seed_ends_before_tail_starts"].append(s)
    for t, (r, i) in sset.items():
        if t >= p0:
            if t in pset:
                audit["overlap_rows"] += 1; dr = abs(r - pset[t][0])
                if dr > 0: audit["overlap_rate_mismatch"] += 1; audit["overlap_rate_maxabs"] = max(audit["overlap_rate_maxabs"], dr)
            elif t <= prod[-1][0]: audit["seed_only_rows_inside_tail_span"] += 1
    if sd:
        for t in pset:
            if sd[0][0] <= t <= sd[-1][0] and t not in sset: audit["prod_only_rows_inside_seed_span"] += 1
    rows = [x for x in sd if x[0] < p0] + prod
    audit["seed_rows_used"] += sum(1 for x in sd if x[0] < p0); audit["prod_rows_used"] += len(prod)
    assert all(rows[k][0] < rows[k + 1][0] for k in range(len(rows) - 1)), ("rows not strictly increasing", s)
    acc0 = acc1 = None; last = None; first = rows[0][0]; k = 0
    for ai, A in enumerate(ANCH):
        while k < len(rows) and rows[k][0] <= A:
            t, r, iv = rows[k]; rn = r * (8.0 / iv)
            if acc0 is None: acc0 = r; acc1 = rn
            else:
                a = 1 - 0.5 ** (max(t - last, 1) / HL); acc0 = acc0 + a * (r - acc0); acc1 = acc1 + a * (rn - acc1)
            last = t; k += 1
        if acc0 is not None:
            V0[ai, j] = acc0; V1R[ai, j] = acc1; RES[ai, j] = 0.5 ** ((last - first) / HL); LASTFT[ai, j] = last
fin = np.isfinite(RES)
OUT = T4 + "/private/v0_feed.npz"
np.savez_compressed(OUT, anchors=np.array(ANCH, np.int64), V0=V0, V1R=V1R, startup_residual_weight=RES, last_ft=LASTFT, symbols=np.array(syms))
audit["n_names_seed_ends_before_tail_starts"] = len(audit["names_seed_ends_before_tail_starts"])
RC = dict(self_sha256=sha(os.path.abspath(__file__)), prereg_sha256=PREREG_SHA, inputs=INPUTS, output=OUT, output_sha256=sha(OUT), audit=audit,
          startup_residual_weight=dict(max_over_cells=float(RES[fin].max()), p99=float(np.percentile(RES[fin], 99)), n_cells_gt_1e_3=int((RES[fin] > 1e-3).sum()), at_first_anchor_max=float(np.nanmax(RES[0]))),
          finite_cells_per_anchor=[int(np.isfinite(V0[a]).sum()) for a in range(len(ANCH))],
          env=dict(whitelist=sorted(WHITE), actual={k: os.environ[k] for k in sorted(os.environ)}), built_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
json.dump(RC, open(T4 + "/receipts/RECEIPT_T4_v0_feed.json", "w"), indent=1, default=str)
print(json.dumps({k: v for k, v in RC.items() if k != "env"}, indent=1, default=str)[:4000])
