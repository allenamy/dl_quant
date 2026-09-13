#!/usr/bin/env python3
"""G2-S chunk-seam gate comparator (AMENDMENT 2 §A2.4, frozen). Chains (run by p2_run.py, same driver dc4e6c85…):
  X = seamX: PIT / SLOW_v4 / v4RAW_s42 / withhold, start 2024-02-01 00:00Z, recorded from S_Y
  Y = seamY: identical arm, start S_Y = S_X + 300 anchors
  both end at E = S_Y + 1830 + 300 anchors.
Gate: for every anchor A in [S_Y + 1830, E]: king H, kc, fc state vectors L-inf <= 1e-9 AND identical w3, traded_file, combo rc and combo_live_status.why.
Also reports the L-inf curve for all common anchors and the first anchor from which L-inf <= 1e-9 (all three vectors) and the categorical fields stay equal to E.
Writes /workspace/uplift_r2_2026-09-13/P2/receipts/G2S_seam_gate.json.
usage: env -i PATH=/usr/bin:/bin HOME=/root /workspace/venv/bin/python -B p2_g2s_seam.py PATH,HOME,LC_CTYPE"""
import os, sys, json, time, hashlib, calendar
WL = set(sys.argv[1].split(",")) if len(sys.argv) > 1 else set()
assert WL, "env whitelist (argv[1]) must be non-empty"
extra = sorted(set(os.environ) - WL); assert not extra, f"env outside whitelist: {extra}"
import numpy as np
P2 = "/workspace/uplift_r2_2026-09-13/P2"; OUT = f"{P2}/receipts/G2S_seam_gate.json"
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 24), b""): h.update(ch)
    return h.hexdigest()
def iso(t): return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(t)))
H4 = 14400; W = 1830
SX = calendar.timegm((2024, 2, 1, 0, 0, 0)); SY = SX + 300 * H4; GATE_FROM = SY + W * H4; E = SY + (W + 300) * H4
def load(tag):
    j = f"{P2}/receipts/RUN_{tag}.json"; v = f"{P2}/receipts/RUN_{tag}.vec.npz"
    d = json.load(open(j)); zf = np.load(v); z = {k: zf[k] for k in zf.files}   # decompress each member ONCE (attempt 1 re-read members inside the loop and was OOM-killed)
    assert d.get("fatal") is None, (tag, d.get("fatal"))
    recs = {int(r["anchor"]): r for r in d["records"]}
    vec = {}
    for k, A in enumerate(z["anchor"].astype(np.int64)):
        vec[int(A)] = {nm: (z[f"{nm}_idx"][z[f"{nm}_off"][k]:z[f"{nm}_off"][k + 1]], z[f"{nm}_val"][z[f"{nm}_off"][k]:z[f"{nm}_off"][k + 1]]) for nm in ("king", "kc", "fc")}
    return d, recs, vec, {"json": j, "json_sha256": sha(j), "vec": v, "vec_sha256": sha(v)}
dX, rX, vX, fX = load("seamX"); dY, rY, vY, fY = load("seamY")
for d_, s_ in ((dX, SX), (dY, SY)):
    assert d_["arm"]["start"] == iso(s_) and d_["arm"]["end"] == iso(E), (d_["arm"]["start"], d_["arm"]["end"])
    assert d_["driver_sha256"] == "dc4e6c8571bcc3bb6c1744fcda5f768ef9f0e3af17111574a15d188623082c54"
common = sorted(set(rX) & set(rY)); assert common[0] == SY and common[-1] == E, (iso(common[0]), iso(common[-1]))
def dense(p):
    v = np.zeros(829); v[p[0].astype(np.int64)] = p[1]; return v
def cat(r):
    s = (r.get("signal") or {}); st = (r.get("combo_live_status") or {})
    return {"w3": s.get("w3"), "traded_file": r.get("traded_file"), "combo_rc": r.get("combo_rc"), "why": st.get("why"), "members": s.get("members"), "sel": s.get("sel")}
curve = []
for A in common:
    li = {nm: float(np.abs(dense(vX[A][nm]) - dense(vY[A][nm])).max()) for nm in ("king", "kc", "fc")}
    ce = cat(rX[A]) == cat(rY[A])
    curve.append({"anchor": A, "utc": iso(A), **{f"Linf_{k}": v for k, v in li.items()}, "categorical_equal": ce})
ok_row = [c["Linf_king"] <= 1e-9 and c["Linf_kc"] <= 1e-9 and c["Linf_fc"] <= 1e-9 and c["categorical_equal"] for c in curve]
first_stable = None
for k in range(len(curve) - 1, -1, -1):
    if not ok_row[k]: first_stable = curve[k + 1]["anchor"] if k + 1 < len(curve) else None; break
else:
    first_stable = curve[0]["anchor"]
gate_rows = [c for c, o in zip(curve, ok_row) if c["anchor"] >= GATE_FROM]
gate_ok = len(gate_rows) == 301 and all(o for c, o in zip(curve, ok_row) if c["anchor"] >= GATE_FROM)
R = {"device": os.path.abspath(__file__), "self_sha256": sha(os.path.abspath(__file__)), "env": dict(os.environ), "inputs": {"X": fX, "Y": fY},
     "S_X": iso(SX), "S_Y": iso(SY), "W_anchors": W, "gate_from": iso(GATE_FROM), "end": iso(E), "n_common": len(common), "n_gate_rows": len(gate_rows),
     "gate_max_Linf": {k: max(c[f"Linf_{k}"] for c in gate_rows) for k in ("king", "kc", "fc")} if gate_rows else None,
     "gate_categorical_all_equal": all(c["categorical_equal"] for c in gate_rows),
     "first_anchor_from_which_all_equal_within_1e-9_to_end": iso(first_stable) if first_stable else None,
     "measured_warmup_anchors_after_S_Y": ((first_stable - SY) // H4) if first_stable else None,
     "curve_every_30": curve[::30], "curve_tail_10": curve[-10:], "verdict": "PASS" if gate_ok else "RED"}
json.dump(R, open(OUT, "w"), indent=1)
print(f"G2S_VERDICT {R['verdict']} gate_rows={len(gate_rows)} max_Linf={R['gate_max_Linf']} categorical_equal={R['gate_categorical_all_equal']} "
      f"first_stable={R['first_anchor_from_which_all_equal_within_1e-9_to_end']} measured_warmup_after_S_Y={R['measured_warmup_anchors_after_S_Y']}", flush=True)
