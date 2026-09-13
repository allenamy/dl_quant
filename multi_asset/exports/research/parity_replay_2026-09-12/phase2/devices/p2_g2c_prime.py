#!/usr/bin/env python3
"""G2-C′ injection plumbing parity (AMENDMENT 2 §A2.5 G2-C′, frozen before this device existed). On each snapshot-seeded anchor A of G2-C:
 (i)  KING: run_anchor(A) from the Phase 1 snapshot state twice — (a) with the real booster wrapped by a recorder, (b) with the ACTUAL Phase 2 OOFBooster
      (p2_driver.py) whose lookup array holds, for (A, members), exactly the predictions recorded in (a) — and require weights npz idx/val, the float64 H vector
      and the target_live weights to be BITWISE equal.
 (ii) F10: take the production-mode G2-C run of the same anchor (real 171 pipeline + real F10 model, outputs under g2c_sNN/replay_home), recompute its f10/scol
      by executing the device's own source block (from `F82 = np.load(...dlw_fea82...)` to `f10 = (h @ ...).squeeze(-1)`) on that run's mini/data files; then
      rerun the byte-identical combo stage in a fresh replay home with the same inputs but with the ACTUAL Phase 2 injection (p2_driver.write_f10_injection +
      write_identity_model) carrying those f10 scores; require state_H_{f10,kc,fc}_{A}.npz and target_live_combo / target_combo / target_blend weights to be
      BITWISE equal to the production-mode run.
Writes only under /workspace/uplift_r2_2026-09-13/P2/work/g2cp_* and receipts/G2Cprime_injection_plumbing.json.
usage (one process per anchor tree, HOME = that tree's fake home; same CPU set as the G2-C runs):
  env -i PATH=/usr/bin:/bin HOME=<P2>/work/g2c_sNN/home taskset -c 0-7 nice -n 10 /workspace/venv/bin/python -B p2_g2c_prime.py PATH,HOME,LC_CTYPE sNN"""
import os, sys, json, time, hashlib, shutil, subprocess, importlib, copy, ast
WL = set(sys.argv[1].split(",")) if len(sys.argv) > 2 else set()
assert WL, "env whitelist (argv[1]) must be non-empty"
extra = sorted(set(os.environ) - WL); assert not extra, f"env outside whitelist: {extra}"
TAG = sys.argv[2]; assert TAG in ("s12", "s16", "s20")
# thread env deliberately NOT pinned: the harness block and the stage must run under the same BLAS/OpenMP defaults as the G2-C production-mode run (taskset -c 0-7, no OMP vars)
import numpy as np
P2 = "/workspace/uplift_r2_2026-09-13/P2"; W = f"{P2}/work"
SPEC = {"s12": (1789214400, 1789200000), "s16": (1789228800, 1789214400), "s20": (1789243200, 1789228800)}
A, APREV = SPEC[TAG]
SRC_TREE = f"{W}/g2c_{TAG}"; TREE = f"{W}/g2cp_{TAG}"; OUT = f"{P2}/receipts/G2Cprime_injection_plumbing_{TAG}.json"
def under(p): assert os.path.realpath(p).startswith(P2 + "/"), p; return p
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 24), b""): h.update(ch)
    return h.hexdigest()
T0 = time.time()
assert os.environ["HOME"] == f"{SRC_TREE}/home", os.environ["HOME"]
PINS = {"replay_driver.py": "f2ced820daa45e0fec0879b6eaeba58905109b60dc0ac09a6e5b0d7cd1bee4ec", "shadow_loop_v3_replay.py": "4d3bc157f03e3462a69e64f817b3fd4cd51be4c03d72650304b7d0c1a0089d42",
        "combo_stage_replay.py": "f5ba9a8234ef0c01ee1aa5bdb0ebd87e8e7093c10b164e37f4fc10f97bc7f77b"}
DRIVER_PIN = "dc4e6c8571bcc3bb6c1744fcda5f768ef9f0e3af17111574a15d188623082c54"
assert sha(f"{P2}/devices/p2_driver.py") == DRIVER_PIN
if os.path.exists(TREE): shutil.rmtree(under(TREE))
os.makedirs(under(f"{TREE}/dev"), exist_ok=True); os.makedirs(f"{TREE}/receipts", exist_ok=True)
for f, s in PINS.items():
    assert sha(f"{SRC_TREE}/dev/{f}") == s, f; shutil.copy2(f"{SRC_TREE}/dev/{f}", f"{TREE}/dev/{f}")
R = {"device": os.path.abspath(__file__), "self_sha256": sha(os.path.abspath(__file__)), "env": dict(os.environ), "anchor": A, "tag": TAG, "pins": PINS, "p2_driver_sha256": DRIVER_PIN,
     "python": sys.version.split()[0], "numpy": np.__version__}

# ───── (i) KING ─────
sys.path.insert(0, f"{TREE}/dev")
rd = importlib.import_module("replay_driver"); dev = rd.dev
assert rd.RH == f"{TREE}/replay_home", rd.RH
sys.path.insert(0, f"{P2}/devices"); import p2_driver as D
cfg, booster, man = dev.load_bundle(); cfg["_booster_sha"] = man.get("slow2026.txt", "")
ledger_full = {s: [list(r) for r in rows] for s, rows in json.load(open(f"{rd.WS}/state/aux.json"))["ledger_tail"].items()}
snapdir = f"{W}/snapshots/{APREV}"
class RecordingBooster:
    def __init__(self, b): self.b = b; self.table = {}
    def predict(self, X):
        f = sys._getframe(1); assert f.f_code.co_name == "run_anchor"
        a_ = int(f.f_locals["anchor"]); m_ = np.asarray(f.f_locals["m"], np.int64); p = self.b.predict(X)
        self.table[a_] = (m_.copy(), np.asarray(p, np.float64).copy()); return p
def clear(a_):
    for d_ in ("weights", "target_live", "target_live_combo", "target_combo", "target_blend", "target_live_king"):
        for f in (f"{rd.RH}/state/{d_}/{a_}.json", f"{rd.RH}/state/{d_}/{a_}.json.sha256", f"{rd.RH}/state/{d_}/{a_}.npz"):
            if os.path.exists(f): os.remove(f)
def king_run(bst):
    clear(A); st = rd.build_state_from_snapshot(snapdir, cfg); assert A == st.last_anchor + 14400
    fx = dev.ReplayFetcher(st.base, ledger_full); dev.run_anchor(st, fx, cfg, bst, A)
    z = np.load(f"{rd.RH}/state/weights/{A}.npz"); tl = json.load(open(f"{rd.RH}/state/target_live/{A}.json"))
    return {"idx": z["idx"].copy(), "val": z["val"].copy(), "members": z["members"].copy(), "H": st.H.copy(), "tl_weights": tl["weights"]}
rec = RecordingBooster(booster); ra = king_run(rec)
m_rec, p_rec = rec.table[A]
class StubG: pass
G = StubG(); G.kt = {"model": "G2Cprime_recorded_real_booster", "label_end": {2026: A - 31 * 86400}}; G.K_row = {A: 0}
KO = np.full((1, 829), np.nan); KO[0, m_rec] = p_rec; G.KOOF = KO
oob = D.OOFBooster(G, "withhold"); rb = king_run(oob)
king = {"members_equal": bool(np.array_equal(ra["members"], rb["members"])), "idx_equal": bool(np.array_equal(ra["idx"], rb["idx"])),
        "val_bitwise_equal": bool(ra["val"].tobytes() == rb["val"].tobytes()), "H_float64_bitwise_equal": bool(ra["H"].tobytes() == rb["H"].tobytes()),
        "target_live_weights_equal": ra["tl_weights"] == rb["tl_weights"], "oob_last": oob.last, "n_members": int(len(m_rec)), "n_pred_finite": int(np.isfinite(p_rec).sum())}
king["PASS"] = all(king[k] for k in ("members_equal", "idx_equal", "val_bitwise_equal", "H_float64_bitwise_equal", "target_live_weights_equal"))
R["king"] = king; print("KING", json.dumps({k: v for k, v in king.items() if k != "oob_last"}), flush=True)

# ───── (ii) F10 ─────
SRH = f"{SRC_TREE}/replay_home"; RHI = under(f"{TREE}/rh_inject")
os.makedirs(f"{RHI}/state/weights", exist_ok=True); os.makedirs(f"{RHI}/state/target_live", exist_ok=True); os.makedirs(f"{RHI}/fea171", exist_ok=True)
for f in (f"state/aux.json", f"state/leg_returns_live.json", f"state/weights/{APREV}.npz", f"state/target_live/{A}.json", f"state/target_live/{A}.json.sha256"):
    shutil.copy2(f"{SRH}/{f}", f"{RHI}/{f}")
os.symlink(os.path.realpath(f"{SRH}/state/rolling.npz"), f"{RHI}/state/rolling.npz"); os.symlink("/workspace/shadow_bundle_v3", f"{RHI}/shadow_bundle")
for f in ("xfer_ref.npz", "xfer_syms.npz", f"state_H_f10_{APREV}.npz", f"state_H_kc_{APREV}.npz", f"state_H_fc_{APREV}.npz"):
    shutil.copy2(f"{SRH}/fea171/{f}", f"{RHI}/fea171/{f}")
aux = json.load(open(f"{RHI}/state/aux.json")); pm = np.array(aux["prev_rec"]["members"], np.int64); assert int(aux["prev_rec"]["anchor_ts"]) == A
# production-mode f10 at A by executing the device's own source block on the G2-C run's mini files
src = open(f"{TREE}/dev/combo_stage_replay.py").read()
i0 = src.index('F82 = np.load(f"{MINI}/data/dlw_fea82.npz", allow_pickle=True)'); i1 = src.index('f10 = (h @ M["w2"].T + M["b2"]).squeeze(-1)'); i1 = src.index("\n", i1) + 1
block = src[i0:i1]; ns = {"np": np, "MINI": f"{SRH}/fea171/mini", "HERE": f"{SRH}/fea171", "A": A}
exec(compile(block, "combo_stage_replay.py:F82..f10", "exec"), ns)
f10, scol = ns["f10"], ns["scol"]
pos_in_pm = {int(s): j for j, s in enumerate(pm)}; f10_pm = np.full(len(pm), np.nan)
for v, s_ in zip(f10, scol):
    j = pos_in_pm.get(int(s_))
    if j is not None: f10_pm[j] = v
GF = StubG(); GF.arm = {"serve_policy": "withhold"}; GF.F_row = {A: 0}
GF.ft = {"seed": "G2Cprime", "monthly_label_end": {202609: A - 40 * 86400}, "yearly_label_end": {}, "splice_boundary": 1735689600}
FO = np.full((1, 829), np.nan); FO[0, pm] = f10_pm; GF.FOOF = FO
inj = D.write_f10_injection(GF, A, pm, f"{RHI}/fea171"); idsha = D.write_identity_model(f"{RHI}/fea171"); assert D.selftest_identity_model(f"{RHI}/fea171")
env = {"PATH": "/usr/bin:/bin", "HOME": os.environ["HOME"], "WIDE_SHADOW_HOME": RHI, "COMBO_LIVE": "1", "COMBO_LIVE_DIR": f"{RHI}/state/target_live_combo", "REPLAY_TRUNCATE_CACHE": "1"}
p = subprocess.run([sys.executable, "-B", f"{TREE}/dev/combo_stage_replay.py"], cwd=f"{RHI}/fea171", env=env, capture_output=True, text=True, timeout=900)
f10r = {"injected": inj, "identity_model_sha256": idsha, "stage_rc": p.returncode, "stage_tail": p.stdout.strip().splitlines()[-4:], "stage_err": p.stderr.strip().splitlines()[-4:],
        "n_f10_prod_finite_on_pm": int(np.isfinite(f10_pm).sum())}
def npz_eq(a, b):
    za, zb = np.load(a), np.load(b)
    return bool(int(za["anchor"]) == int(zb["anchor"]) and np.array_equal(za["idx"], zb["idx"]) and za["val"].tobytes() == zb["val"].tobytes())
for t in ("f10", "kc", "fc"):
    f10r[f"state_H_{t}_bitwise_equal"] = npz_eq(f"{SRH}/fea171/state_H_{t}_{A}.npz", f"{RHI}/fea171/state_H_{t}_{A}.npz")
for d_ in ("target_live_combo", "target_combo", "target_blend"):
    a_ = json.load(open(f"{SRH}/state/{d_}/{A}.json")); b_ = json.load(open(f"{RHI}/state/{d_}/{A}.json"))
    f10r[f"{d_}_weights_equal"] = a_["weights"] == b_["weights"]
    if d_ == "target_blend": f10r["rho_f10_vs_king_equal"] = a_.get("rho_f10_vs_king") == b_.get("rho_f10_vs_king"); f10r["n_f10_scored"] = [a_.get("n_f10_scored"), b_.get("n_f10_scored")]
f10r["PASS"] = (p.returncode == 0 and all(f10r[k] for k in ("state_H_f10_bitwise_equal", "state_H_kc_bitwise_equal", "state_H_fc_bitwise_equal", "target_live_combo_weights_equal", "target_combo_weights_equal", "target_blend_weights_equal")))
R["f10"] = f10r; print("F10", json.dumps({k: v for k, v in f10r.items() if k not in ("stage_tail", "injected")}), flush=True)
R["PASS"] = bool(king["PASS"] and f10r["PASS"]); R["runtime_s"] = round(time.time() - T0, 1)
json.dump(R, open(under(OUT), "w"), indent=1, default=str)
print(f"G2Cprime_{TAG} {'PASS' if R['PASS'] else 'RED'} king={king['PASS']} f10={f10r['PASS']}", flush=True)
