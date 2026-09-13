#!/usr/bin/env python3
"""t4b_seat_override.py — Mac, read-only on production (PREREG_T4b §6 seat arm). Builds the seat-history file for arm seatK1.
Start = the producer's own seat history at snapshot 1789200000 (09-12 08Z close). Row -> anchor mapping follows the 09-05 dry run
(multi_asset/exports/live/seat_seed_v3_2026-09-05/dryrun_seat_seed.py): the oldest rows are bitwise equal, on fund and rev24, to the
August bundle tail; the remaining rows map one-to-one, in order, onto the producer's score-log anchors after that prefix.
Seeded rows = rows whose anchor is covered by the v3 bundle (<= 2026-08-30 20Z). GATE SA: on every seeded row the stored king value
equals the v3 bundle's king value at that anchor AND equals T4b's recomputed v0 series (kings_lr.npz king_K0) bitwise.
Override: those rows' king values <- king_K1 (same boosters, column 80 = v1); fund and rev24 untouched; same JSON structure.
Computes no seat weight. Output: private/seat_override/leg_returns_live.seatK1.json + receipt."""
import os, sys, json, time, hashlib
WHITE = set(x for x in sys.argv[1].split(",") if x) if len(sys.argv) > 1 else None
assert WHITE, "whitelist argv[1]"
assert sorted(k for k in os.environ if k not in WHITE) == [], ("ENV WHITELIST VIOLATION", sorted(os.environ))
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); T4B = os.path.dirname(HERE); PRIV = T4B + "/private"
def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()
_fr = open(T4B + "/receipts/PREREG_FREEZE_sha.txt").readline().split(); PREREG_SHA = _fr[2]; assert sha(T4B + "/PREREG_T4b_v2main_feature_skew_2026-09-13.md") == PREREG_SHA
W = "/Users/haosiyu/wide_shadow"; PS = PRIV + "/producer_snapshot_1789200000"; SNAP = PRIV + "/snapshot_live"
for _l in open(PS + "/SHA256SUMS.txt"):
    _h, _f = _l.split(None, 1); assert sha(PS + "/" + _f.strip()) == _h, ("PRODUCER SNAPSHOT COPY CHANGED", _f)
OLD = f"{W}/shadow_bundle.aug20260816_backup/leg_returns.npz"; NEW = f"{W}/shadow_bundle/leg_returns.npz"; KLR = PRIV + "/pod2_inputs/kings_lr.npz"
INPUTS = {p: sha(p) for p in (PS + "/leg_returns_live.json", OLD, NEW, KLR, SNAP + "/shadow_log.jsonl")}
assert INPUTS[NEW] == "6061af108e45fee5ea0257b37f35e9efd0783d494934cad398e003fd47de7c13" and INPUTS[KLR] == "2b67a5180ad892f9bd101f9e568856ff9ab72dc92f0cfe14a23afdbb6394d8a5", INPUTS
st = json.load(open(PS + "/leg_returns_live.json")); fund = np.array(st["fund"]); rev = np.array(st["rev24"]); king = np.array(st["king"]); n = len(king)
old = np.load(OLD); new = np.load(NEW); K = np.load(KLR)
best = None
for off in range(0, len(old["fund"]) - 50):
    m = min(n, len(old["fund"]) - off); eq = int(np.sum(fund[:m] == old["fund"][off:off + m]))
    if best is None or eq > best[1]: best = (off, eq, m)
off_old = best[0]; pref = 0
while pref < best[2] and fund[pref] == old["fund"][off_old + pref] and rev[pref] == old["rev24"][off_old + pref]: pref += 1
prefix_end = int(old["ts"][off_old + pref - 1]); last_anchor = int(json.load(open(PS + "/aux.json"))["last_anchor"])
scored = []
for l in open(SNAP + "/shadow_log.jsonl"):
    try:
        r = json.loads(l)
        if r.get("e") == "score" and r.get("anchor_ts"): scored.append(int(r["anchor_ts"]))
    except Exception: pass
tail = [a for a in scored if prefix_end < a < last_anchor]
assert tail == sorted(tail) and len(tail) == len(set(tail)) and len(tail) == n - pref, (len(tail), n - pref)
anchor = np.array([int(old["ts"][off_old + i]) for i in range(pref)] + tail, np.int64)
nts = {int(t): i for i, t in enumerate(new["ts"])}; kts = {int(t): i for i, t in enumerate(K["ts"])}
cov = np.array([int(a) in nts for a in anchor]); seeded = np.where(cov)[0]
v_new = np.array([new["king"][nts[int(anchor[i])]] for i in seeded]); v_k0 = np.array([K["king_K0"][kts[int(anchor[i])]] for i in seeded]); v_k1 = np.array([K["king_K1"][kts[int(anchor[i])]] for i in seeded])
GATE_SA = dict(rows=int(n), prefix_rows=int(pref), score_rows=int(len(tail)), seeded_rows=int(len(seeded)), seeded_first=time.strftime("%Y-%m-%d %HZ", time.gmtime(int(anchor[seeded[0]]))),
               seeded_last=time.strftime("%Y-%m-%d %HZ", time.gmtime(int(anchor[seeded[-1]]))), stored_eq_bundle=int(np.sum(king[seeded] == v_new)), stored_eq_K0=int(np.sum(king[seeded] == v_k0)))
GATE_SA["PASS"] = bool(GATE_SA["stored_eq_bundle"] == len(seeded) and GATE_SA["stored_eq_K0"] == len(seeded) and len(seeded) > 0)
assert GATE_SA["PASS"], GATE_SA
king2 = king.copy(); king2[seeded] = v_k1
out = {"king": list(map(float, king2)), "rev24": st["rev24"], "fund": st["fund"]}
assert out["rev24"] == st["rev24"] and out["fund"] == st["fund"] and len(out["king"]) == n
os.makedirs(PRIV + "/seat_override", exist_ok=True); op = PRIV + "/seat_override/leg_returns_live.seatK1.json"; json.dump(out, open(op, "w"))
RC = dict(self_sha256=sha(os.path.abspath(__file__)), prereg_sha256=PREREG_SHA, inputs=INPUTS, gate_SA=GATE_SA, rows_changed=int(np.sum(np.array(out["king"]) != king)),
          output=op, output_sha256=sha(op), env=dict(whitelist=sorted(WHITE), actual={k: os.environ[k] for k in sorted(os.environ)}), built_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
json.dump(RC, open(T4B + "/receipts/RECEIPT_T4b_seat_override.json", "w"), indent=1, default=str); print(json.dumps({k: v for k, v in RC.items() if k != "env"}, indent=1, default=str))
