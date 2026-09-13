#!/usr/bin/env python3
"""t6_extract.py -- T6 step 2a (pod2, read-only on inputs). Build the member g-matrices from the FROZEN family (commit c0ed46c8).
For every member of FAMILY_T6.json: load the canonical record, judged key (d30_n2_c42_rec else rec), align to the W_FULL grid, g = net_ex/gross_total,
and GATE-X: sha256(g float64 bytes) must equal the frozen g_sha256_wfull. Writes receipts/T6_SERIES_s{42,2027}.npz + RECEIPT_T6_extract.json.
No statistic is computed here.
Usage: python3 t6_extract.py <env_whitelist_csv> <FAMILY_T6.json> <out_dir>
"""
import os, sys, json, time, hashlib, calendar
WHITE = set(x for x in sys.argv[1].split(",") if x); assert WHITE, "non-empty env whitelist required"
EXTRA = sorted(k for k in os.environ if k not in WHITE); assert EXTRA == [], ("ENV WHITELIST VIOLATION", EXTRA)
FJ, OUTD = sys.argv[2], sys.argv[3]
import numpy as np
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()
FROZEN_FAMILY_SHA = "7ad53ccec6da11db6e7d9a9beac183d025085087c55ffd3ae6e90a46b2eb32c7"   # FAMILY_T6.json in commit c0ed46c8
assert sha(FJ) == FROZEN_FAMILY_SHA, ("FAMILY_T6.json is not the frozen version", sha(FJ))
F = json.load(open(FJ))
ARCH = "/workspace/uplift_2026-09-11/r8_inbook/arms/R8_A0_dyn_s42.npz"
Z = np.load(ARCH); C = [str(c) for c in Z["cols"]]; TS = Z["rec"][:, C.index("ts")].astype(np.int64)
UB = calendar.timegm((2026, 8, 30, 20, 0, 0)); WF = TS[TS <= UB]; assert len(WF) == 10038
t0 = time.time(); rec = dict(device="t6_extract.py", self_sha256=sha(os.path.abspath(__file__)), family_sha256=sha(FJ), env_whitelist=sorted(WHITE),
                             env_actual={k: os.environ[k] for k in sorted(os.environ)}, python=sys.version.split()[0], numpy=np.__version__, host=os.uname().nodename, seeds={})
for seed in ("42", "2027"):
    ms = [m for m in F["members"] if m["seed"] == seed]
    G = np.empty((len(WF), len(ms)), dtype=np.float64); chk = []
    for j, m in enumerate(ms):
        p = m["canonical_path"]; assert sha(p) == m["canonical_file_sha256"], ("file sha drift", p)
        Zr = np.load(p); Cr = [str(c) for c in Zr["cols"]]; R = Zr[m["rec_key"]]
        ts = R[:, Cr.index("ts")]; ok = np.isfinite(ts); tsi = ts[ok].astype(np.int64)
        pos = {int(t): i for i, t in enumerate(tsi)}; idx = np.array([pos[int(t)] for t in WF])
        g = R[ok, Cr.index("net_ex")][idx] / R[ok, Cr.index("gross_total")][idx]
        hs = hashlib.sha256(np.ascontiguousarray(g, dtype=np.float64).tobytes()).hexdigest()
        chk.append(dict(member_id=m["member_id"], stem=m["canonical_stem"], equal=hs == m["g_sha256_wfull"], finite=bool(np.isfinite(g).all())))
        G[:, j] = g
    gate = all(c["equal"] and c["finite"] for c in chk)
    out = os.path.join(OUTD, "T6_SERIES_s%s.npz" % seed)
    np.savez(out, G=G, ts=WF, member_id=np.array([m["member_id"] for m in ms]), stem=np.array([m["canonical_stem"] for m in ms]),
             role=np.array([m["role"] for m in ms]), round=np.array([m["canonical_round"] for m in ms]),
             F1=np.array([m["in_F1"] for m in ms]), F2=np.array([m["in_F2"] for m in ms]), F3=np.array([m["in_F3"] for m in ms]),
             F4=np.array([m["in_F4"] for m in ms]), F5=np.array([m["in_F5"] for m in ms]), model_inputs=np.array([m["model_inputs"] for m in ms]),
             family_sha256=np.array(FROZEN_FAMILY_SHA))
    rec["seeds"][seed] = dict(n_members=len(ms), gate_X_pass=gate, n_equal=sum(c["equal"] for c in chk), out=out, out_sha256=sha(out), checks=chk)
rec["wall_s"] = round(time.time() - t0, 1)
json.dump(rec, open(os.path.join(OUTD, "RECEIPT_T6_extract.json"), "w"), indent=1)
print("SUMMARY t6_extract s42 n=%d gateX=%s s2027 n=%d gateX=%s self_sha256=%s wall=%.1fs" % (rec["seeds"]["42"]["n_members"], rec["seeds"]["42"]["gate_X_pass"],
      rec["seeds"]["2027"]["n_members"], rec["seeds"]["2027"]["gate_X_pass"], rec["self_sha256"][:16], rec["wall_s"]))
