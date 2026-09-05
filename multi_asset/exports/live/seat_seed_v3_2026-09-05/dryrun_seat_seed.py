#!/usr/bin/env python3
"""Dry run for PREREG_deploy_seat_seed_v3_2026-09-05: build the seeded state file in STAGING (never the live path),
verify alignment bitwise, and print the producer-rule seat before/after. Read-only on the live tree."""
import json, os, sys, hashlib, numpy as np
from datetime import datetime, timezone
W = "/Users/haosiyu/wide_shadow"; OUT = os.path.dirname(os.path.abspath(__file__))
LOOK = 900
def utc(t): return datetime.fromtimestamp(int(t), tz=timezone.utc).strftime("%Y-%m-%d %H:%MZ")
def sha(b): return hashlib.sha256(b).hexdigest()[:12]
st_path = f"{W}/state/leg_returns_live.json"
raw = open(st_path, "rb").read(); st = json.loads(raw)
print("live state file sha", sha(raw), "rows", {k: len(v) for k, v in st.items()})
new = np.load(f"{W}/shadow_bundle/leg_returns.npz"); old = np.load(f"{W}/shadow_bundle.aug20260816_backup/leg_returns.npz")
print("v3 bundle leg_returns.npz sha", sha(open(f"{W}/shadow_bundle/leg_returns.npz", "rb").read()), "ts", utc(new["ts"][0]), "->", utc(new["ts"][-1]), "n", len(new["ts"]))
fund = np.array(st["fund"]); rev = np.array(st["rev24"]); king = np.array(st["king"]); n = len(fund)
# 1) alignment: bundle-era prefix of the state file == OLD bundle tail (bitwise, all three legs)
ob = len(old["fund"]) - n if n <= len(old["fund"]) else None
best = None
for off in range(0, len(old["fund"]) - 50):
    m = min(n, len(old["fund"]) - off); eq = int(np.sum(fund[:m] == old["fund"][off:off + m]))
    if best is None or eq > best[1]: best = (off, eq, m)
off_old, eq_old, m_old = best
pref = 0
while pref < m_old and fund[pref] == old["fund"][off_old + pref] and rev[pref] == old["rev24"][off_old + pref] and king[pref] == old["king"][off_old + pref]: pref += 1
print(f"bundle-era prefix (all 3 legs bitwise == OLD bundle): {pref} rows = anchors {utc(old['ts'][off_old])} .. {utc(old['ts'][off_old + pref - 1])}; live rows after: {n - pref}")
assert pref >= 800 and pref + (n - pref) == n
# anchors of every state row: prefix rows have bundle ts; live rows are consecutive 4h anchors after the prefix end (checked below)
# live rows: one LR row is appended per scored anchor (producer L439-443: LR append then the 'score' log row), so the
# live rows map one-to-one, in order, onto the score-log anchors after the prefix end (NOT necessarily consecutive 4h steps).
prefix_end = int(old["ts"][off_old + pref - 1])
log = f"{W}/shadow_log.jsonl"; scored = []
for l in open(log):
    try:
        r = json.loads(l)
        if r.get("e") == "score" and r.get("anchor_ts"): scored.append(int(r["anchor_ts"]))
    except Exception: pass
tail = [a for a in scored if a > prefix_end]
assert tail == sorted(tail) and len(tail) == len(set(tail)), "score log anchors not strictly increasing"
gaps = [(utc(a), utc(b)) for a, b in zip(tail, tail[1:]) if b - a != 14400]
print(f"score-log anchors after prefix end: {len(tail)} (state live rows {n - pref}); first {utc(tail[0])} last {utc(tail[-1])}; non-4h gaps {len(gaps)}: {gaps[:6]}")
assert len(tail) == n - pref, "live rows do not match the producer's score log one-to-one"
anchor = np.array([int(old["ts"][off_old + i]) for i in range(pref)] + tail)
# 2) map every state row to the NEW bundle by ts
ts_new = {int(t): i for i, t in enumerate(new["ts"])}
idx_new = np.array([ts_new.get(int(a), -1) for a in anchor])
cov = idx_new >= 0
print(f"rows covered by the v3 bundle: {int(cov.sum())} of {n} (last covered anchor {utc(anchor[cov][-1])}); uncovered live rows: {int((~cov).sum())} = {utc(anchor[~cov][0])} .. {utc(anchor[-1])}")
# bitwise checks on the bundle-era prefix vs NEW bundle: fund/rev24 identical, king all different
pf = idx_new[:pref]
print("prefix vs v3: fund bitwise-equal", int(np.sum(fund[:pref] == new["fund"][pf])), "/", pref, "; rev24", int(np.sum(rev[:pref] == new["rev24"][pf])), "/", pref, "; king equal", int(np.sum(king[:pref] == new["king"][pf])), "/", pref)
assert np.all(fund[:pref] == new["fund"][pf]) and np.all(rev[:pref] == new["rev24"][pf])
# 3) seat per producer rule (3-leg msharpe on last LOOK rows) + combo mask king/(king+fund)
def seat(k, r, f):
    R = np.stack([np.array(k[-LOOK:]), np.array(r[-LOOK:]), np.array(f[-LOOK:])]); shp = R.mean(1) / (R.std(1) + 1e-9); shp = np.maximum(shp, 0.0)
    w3 = shp / shp.sum() if shp.sum() > 0 else np.array([1 / 3] * 3)
    return w3, (w3[0] / (w3[0] + w3[2]) if (w3[0] + w3[2]) > 0 else float("nan")), R.mean(1), R.std(1)
w3_0, m0, mu0, sd0 = seat(king, rev, fund)
print(f"CURRENT: w3 {np.round(w3_0, 4).tolist()} masked king {m0:.4f}; king mean {mu0[0]:.3f} sd {sd0[0]:.2f} shp {mu0[0]/(sd0[0]+1e-9):.4f}")
# option A: replace king only on the bundle-era prefix
kA = king.copy(); kA[:pref] = new["king"][pf]
w3_A, mA, muA, sdA = seat(kA, rev, fund)
print(f"OPTION A (prefix only, {pref} rows): w3 {np.round(w3_A, 4).tolist()} masked king {mA:.4f}; king mean {muA[0]:.3f} shp {muA[0]/(sdA[0]+1e-9):.4f}")
# option B' (device rule): replace king on every row the v3 bundle covers; keep uncovered live rows
kB = king.copy(); kB[cov] = new["king"][idx_new[cov]]
w3_B, mB, muB, sdB = seat(kB, rev, fund)
print(f"OPTION B' (device rule, {int(cov.sum())} rows): w3 {np.round(w3_B, 4).tolist()} masked king {mB:.4f}; king mean {muB[0]:.3f} shp {muB[0]/(sdB[0]+1e-9):.4f}")
# reference: last 900 rows of the v3 bundle alone
w3_R, mR, muR, sdR = seat(new["king"], new["rev24"], new["fund"])
print(f"REFERENCE (v3 bundle last 900 rows alone): w3 {np.round(w3_R, 4).tolist()} masked king {mR:.4f}")
# 4) staged file (option B'), same structure/length/float formatting as the producer's atomic_json
staged = {leg: list(map(float, {"king": kB, "rev24": rev, "fund": fund}[leg])) for leg in ("king", "rev24", "fund")}
assert {k: len(v) for k, v in staged.items()} == {k: len(v) for k, v in st.items()}
assert staged["fund"] == st["fund"] and staged["rev24"] == st["rev24"]
n_changed = int(np.sum(np.array(staged["king"]) != king)); print("king rows changed:", n_changed, "unchanged:", n - n_changed)
sp = f"{OUT}/leg_returns_live.seeded_v3.json"; json.dump(staged, open(sp, "w")); print("staged file", sp, "sha", sha(open(sp, "rb").read()))
json.dump({"live_sha": sha(raw), "n_rows": n, "prefix_rows": int(pref), "covered_rows": int(cov.sum()), "uncovered_live_rows": int((~cov).sum()),
           "prefix_anchors": [utc(anchor[0]), utc(anchor[pref - 1])], "uncovered_anchors": [utc(anchor[~cov][0]), utc(anchor[-1])],
           "seat_current": {"w3": w3_0.tolist(), "masked": float(m0)}, "seat_A": {"w3": w3_A.tolist(), "masked": float(mA)},
           "seat_B_device_rule": {"w3": w3_B.tolist(), "masked": float(mB)}, "seat_ref_bundle_only": {"w3": w3_R.tolist(), "masked": float(mR)},
           "staged_sha": sha(open(sp, "rb").read()), "v3_leg_returns_sha": sha(open(f"{W}/shadow_bundle/leg_returns.npz", "rb").read())},
          open(f"{OUT}/dryrun_receipt.json", "w"), indent=1)
print("DRYRUN_OK")
