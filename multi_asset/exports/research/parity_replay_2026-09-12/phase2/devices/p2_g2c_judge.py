#!/usr/bin/env python3
"""G2-C judge (AMENDMENT 2 §A2.5, frozen; AMENDMENT 5 labels). Reads the four Phase-1-driver receipts produced on pod2 with the hybrid caches and applies the
frozen thresholds; compares every anchor with the Phase 1 receipts (chain_full c38270ce… and G-P3 snapshot receipts) for context. No threshold is set here
beyond A2.5: king 41/41 weights L-inf <= 1e-6 (chain); combo target_live L-inf <= 1e-6 on 3/3 snapshot-seeded anchors; historical-chain combo residual reported
separately (no label). Writes /workspace/uplift_r2_2026-09-13/P2/receipts/G2C_verdict.json.
usage: env -i PATH=/usr/bin:/bin HOME=/root /workspace/venv/bin/python -B p2_g2c_judge.py PATH,HOME,LC_CTYPE"""
import os, sys, json, time, hashlib, glob
WL = set(sys.argv[1].split(",")) if len(sys.argv) > 1 else set()
assert WL, "env whitelist (argv[1]) must be non-empty"
extra = sorted(set(os.environ) - WL); assert not extra, f"env outside whitelist: {extra}"
P2 = "/workspace/uplift_r2_2026-09-13/P2"; W = f"{P2}/work"; OUT = f"{P2}/receipts/G2C_verdict.json"
def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()
def one(pattern):
    fs = sorted(glob.glob(pattern)); assert len(fs) == 1, (pattern, fs); return fs[0]
prep = json.load(open(f"{P2}/receipts/G2C_prep.json"))
chain_p = one(f"{W}/g2c_chain/receipts/PARITY_G2C_chain_1788624000_1789200000.json")
snap_p = {k: one(f"{W}/g2c_{k}/receipts/PARITY_G2C_snapshot_*_*.json") for k in ("s12", "s16", "s20")}
logs = {"chain": f"{W}/g2c_chain/receipts/G2C_chain.log", **{k: one(f"{W}/g2c_{k}/receipts/G2C_snapshot_*.log") for k in ("s12", "s16", "s20")}}
rc = {}
for k, p in logs.items():
    lines = [l.strip() for l in open(p) if l.strip()]
    rc[k] = lines[-1] if lines and lines[-1].startswith("rc=") else "NO_RC_LINE"
P1 = json.load(open(f"{W}/live_ro/PARITY_phase1_chain_full_1788624000_1789200000.json")); P1a = {int(a["anchor"]): a for a in P1["anchors"]}
C = json.load(open(chain_p)); CA = C["anchors"]
anchors_expected = [1788624000 + 14400 * k for k in range(41)]
king = []; combo_hist = []
for a in CA:
    A = int(a["anchor"]); p1 = P1a.get(A, {})
    king.append({"anchor": A, "g2c_weights_npz_Linf": a["weights_npz_Linf"], "phase1_weights_npz_Linf": p1.get("weights_npz_Linf"), "g2c_target_live_json_Linf": a["target_live_json_Linf"],
                 "lr_entry_max_abs_diff": a.get("lr_entry_max_abs_diff"), "signal_equal_to_live": (a.get("signal_live") or {}) == (a.get("signal_replay") or {})})
    cb = a.get("combo") or {}; p1c = p1.get("combo") or {}
    combo_hist.append({"anchor": A, "rc": cb.get("rc"), "g2c_target_live_Linf": cb.get("target_live_Linf"), "phase1_target_live_Linf": p1c.get("target_live_Linf"),
                       "g2c_target_combo_Linf": cb.get("target_combo_Linf"), "phase1_target_combo_Linf": p1c.get("target_combo_Linf"), "w3m_equal": cb.get("w3m_equal"), "ftrim_n": cb.get("ftrim_n")})
king_ok = ([k["anchor"] for k in king] == anchors_expected and all(k["g2c_weights_npz_Linf"] is not None and k["g2c_weights_npz_Linf"] <= 1e-6 for k in king) and rc["chain"] == "rc=0")
snap = {}
for k, p in snap_p.items():
    d = json.load(open(p)); a = d["anchors"][0]; cb = a.get("combo") or {}
    snap[k] = {"receipt": p, "receipt_sha256": sha(p), "anchor": a["anchor"], "king_weights_npz_Linf": a["weights_npz_Linf"], "content_sha_equal": a.get("content_sha_equal"),
               "combo_rc": cb.get("rc"), "target_live_Linf": cb.get("target_live_Linf"), "target_combo_Linf": cb.get("target_combo_Linf"), "rc_line": rc[k],
               "rolling_sha256": d["rolling_sha256"], "aux_sha256": d["aux_sha256"]}
combo_ok = all(v["combo_rc"] == 0 and v["target_live_Linf"] is not None and v["target_live_Linf"] <= 1e-6 and v["rc_line"] == "rc=0" for v in snap.values())
V = {"device": os.path.abspath(__file__), "self_sha256": sha(os.path.abspath(__file__)), "env": dict(os.environ), "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
     "prep_receipt_sha256": sha(f"{P2}/receipts/G2C_prep.json"), "chain_receipt": chain_p, "chain_receipt_sha256": sha(chain_p), "chain_rc_line": rc["chain"],
     "chain_start_diag": C.get("chain_start_diag"), "phase1_chain_start_diag": P1.get("chain_start_diag"), "chain_rolling_sha256": C.get("rolling_sha256"), "chain_aux_sha256": C.get("aux_sha256"),
     "king_chain": {"n": len(king), "max_Linf": max(k["g2c_weights_npz_Linf"] for k in king) if king else None, "n_le_1e-6": sum(1 for k in king if k["g2c_weights_npz_Linf"] <= 1e-6),
                    "max_lr_entry_abs_diff": max((k["lr_entry_max_abs_diff"] or 0.0) for k in king), "n_signal_equal": sum(1 for k in king if k["signal_equal_to_live"]), "per_anchor": king, "PASS": king_ok},
     "combo_snapshot_seeded": {"anchors": snap, "PASS": combo_ok},
     "combo_historical_chain_residual_REPORTED_NOT_GATED": {"n": len(combo_hist), "n_le_1e-6": sum(1 for c in combo_hist if (c["g2c_target_live_Linf"] is not None and c["g2c_target_live_Linf"] <= 1e-6)),
                                                          "max": max((c["g2c_target_live_Linf"] or 0.0) for c in combo_hist) if combo_hist else None,
                                                          "equal_to_phase1_per_anchor": sum(1 for c in combo_hist if c["g2c_target_live_Linf"] == c["phase1_target_live_Linf"]), "per_anchor": combo_hist}}
V["verdict"] = "PASS" if (king_ok and combo_ok) else "RED"
json.dump(V, open(OUT, "w"), indent=1)
kc = V["king_chain"]; hc = V["combo_historical_chain_residual_REPORTED_NOT_GATED"]
print(f"G2C_VERDICT {V['verdict']} king_chain {kc['n_le_1e-6']}/{kc['n']} max_Linf={kc['max_Linf']:.3e} | combo_snapshot " + " ".join(f"{k}:{v['target_live_Linf']}" for k, v in snap.items())
      + f" | hist_chain_combo(reported) n_le_1e-6={hc['n_le_1e-6']}/{hc['n']} max={hc['max']} equal_to_phase1={hc['equal_to_phase1_per_anchor']}", flush=True)
