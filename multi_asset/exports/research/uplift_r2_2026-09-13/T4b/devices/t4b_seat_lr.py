#!/usr/bin/env python3
"""t4b_seat_lr.py — pod2, CPU (nice, <=16 threads), READ-ONLY. Seat-seeding inputs for PREREG_T4b.
The 09-05 seat seeding (docs/PREREG_deploy_seat_seed_v3_2026-09-05.md) wrote the v3 bundle's king leg-return rows
(`shadow_bundle_v3/leg_returns.npz`, sha 6061af10…) into the producer's seat history. Those rows were computed by
pod_export_bundle_v3.py L97-111 from slow_pred_pinned.npy (v0-scored). This device recomputes the king leg-return series with
that exact formula from T4's K0 file (== slow_pred_pinned bitwise) — GATE SL: must equal the bundle's king column bitwise —
and from T4's K1 file (same boosters, column 80 = v1) as the counterfactual input. It computes no seat weight and no P&L.
Output: kings_lr.npz {ts, king_K0, king_K1} + receipt.
Launch: nice -n 19 taskset -c 0-15 env -i PATH=... HOME=/root OMP_NUM_THREADS=16 MKL_NUM_THREADS=16 OPENBLAS_NUM_THREADS=16 /workspace/venv/bin/python devices/t4b_seat_lr.py <whitelist>
"""
import os, sys, json, time, hashlib
WHITE = set(x for x in sys.argv[1].split(",") if x) if len(sys.argv) > 1 else None
assert WHITE, "whitelist argv[1]"
assert sorted(k for k in os.environ if k not in WHITE) == [], ("ENV WHITELIST VIOLATION", sorted(os.environ))
import numpy as np
from scipy.stats import rankdata
T4B = "/workspace/uplift_r2_2026-09-13/T4b"; T4 = "/workspace/uplift_r2_2026-09-13/T4"
def sha(p):
    h = hashlib.sha256()
    with open(os.path.realpath(p), "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()
t0 = time.time()
META = "/workspace/data/wide_fea_v2ext_meta.npz"; BLR = "/workspace/shadow_bundle_v3/leg_returns.npz"
K0P = T4 + "/kings/K0_v3axis.npy"; K1P = T4 + "/kings/K1_v3axis.npy"
EXP = {META: "4b1b6047107d25573244a84df69d45bc987ada89b6731e826c867a230e247082", BLR: "6061af108e45fee5ea0257b37f35e9efd0783d494934cad398e003fd47de7c13",
       K0P: "158cd4ac8f8f30f7f41a5a6cba0bd19a450ce756727e4aeae3d4e4b0b67d0054", K1P: "c98f79d4d28289151276d874d35a4e6368b0e3387aa24a941ad5ab674535c5ab"}
INPUTS = {p: sha(p) for p in EXP}
for p, h in EXP.items(): assert INPUTS[p] == h, ("INPUT SHA", p, INPUTS[p])
MT = np.load(META, allow_pickle=True); E_ts = MT["E_ts"].astype(np.int64); members = MT["members"]; y4 = MT["y4"]; nA = len(E_ts)
B = np.load(BLR); bts = B["ts"].astype(np.int64)
assert np.array_equal(bts, E_ts), "bundle leg_returns ts != meta E_ts (every anchor had an export-panel row)"
def xz(v):   # pod_export_bundle_v3.py L88-92 verbatim
    ok = np.isfinite(v); out = np.full(len(v), np.nan)
    n = ok.sum()
    if n >= 10: out[ok] = rankdata(v[ok]) / max(n - 1, 1) - 0.5
    return out
def king_lr(PRED):   # L97-110 (king leg only; the export panel only gates row existence, all rows exist per the assert above)
    out = []
    for i in range(nA):
        m = members[i]; ok = np.isfinite(y4[i, m])
        z = np.nan_to_num(xz(PRED[i, m]))
        z = np.where(ok, z, 0.0); z -= z[ok].mean() if ok.sum() else 0
        g = np.abs(z).sum()
        out.append(float((z / g * np.nan_to_num(y4[i, m], nan=0.0)).sum() * 1e4) if g > 1e-9 else 0.0)
    return np.array(out)
L0 = king_lr(np.load(K0P)); L1 = king_lr(np.load(K1P))
bk = B["king"].astype(np.float64)
GATE_SL = dict(bitwise=bool(np.array_equal(L0, bk)), n=int(nA), n_unequal=int((L0 != bk).sum()), maxabs=float(np.abs(L0 - bk).max()))
GATE_SL["PASS"] = GATE_SL["bitwise"]
op = T4B + "/private_inputs/kings_lr.npz"; np.savez_compressed(op, ts=E_ts, king_K0=L0, king_K1=L1)
RC = dict(self_sha256=sha(os.path.abspath(__file__)), inputs=INPUTS, gate_SL=GATE_SL, output=op, output_sha256=sha(op), rows_where_K1_differs=int((L1 != L0).sum()),
          env=dict(whitelist=sorted(WHITE), actual={k: os.environ[k] for k in sorted(os.environ)}), built_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), wall_s=round(time.time() - t0, 1))
json.dump(RC, open(T4B + "/receipts/RECEIPT_T4b_seat_lr.json", "w"), indent=1, default=str)
print(json.dumps({k: v for k, v in RC.items() if k != "env"}, indent=1, default=str))
assert GATE_SL["PASS"], "GATE SL FAIL"
