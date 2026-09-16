#!/usr/bin/env python3
"""R16R-M1 (independent review, second round, 2026-09-16): the King B-REPRO gate's exit code must come from the
verdict THE DEVICE ITSELF PRODUCES by running its whole main() — never from a dict a test hands it.

The first-round test evaluated the return expression on a hand-built {"GATE_B_REPRO": "PASS"} — the DL gate's key.
The King device writes "GATE_B_REPRO_KING", so a real PASS exited 3 and the test never saw it: a control that
feeds the exit expression a key the device never writes is vacuous (GEN-4). Here main() runs end to end; only the
EXPENSIVE, EXTERNAL things are stubbed, each stub named:
  - `lightgbm` module  → SyntheticBooster / SyntheticRegressor (deterministic function of X; no training, no GPU)
  - META / FEA / PINS / STORED / BOOST paths → small synthetic files under a temp dir; EXPECT cleared
Nothing about historical King numbers or training performance is claimed. Three arms, pre-registered:
  PASS     saved booster reproduces STORED, refits reproduce                 → GATE_B_REPRO_KING=PASS,    exit 0
  PARTIAL  FM_GK_REFIT=0 (refits not run)                                    → "PARTIAL (2026 only)",   exit 3
  INVALID  saved booster disagrees with STORED by 1.0 (> tolerance 1e-5)     → INVALID,                 exit 3
"""
import importlib.util, json, os, sys, tempfile, types, subprocess
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); DEV = os.path.join(HERE, "fm_gate_b_repro_king.py")
FAILS, N = [], [0]
def check(name, ok, detail=None):
    N[0] += 1
    if not ok: FAILS.append(name)
    print(("  OK   " if ok else "  FAIL ") + name + (("  — " + str(detail)[:200]) if detail is not None else ""), flush=True)
try:
    import scipy  # noqa: F401
except ImportError:
    print("  UNAVAIL scipy not importable here — the device needs rankdata; full-main arms not run, not faked"); sys.exit(3)

NA, NW, NM = 8, 829, 60                     # 8 anchors (2 per year 2023..2026), 829 symbols, 60 members each
def fixture(d, offset=0.0):
    E_ts = np.array([int(__import__("calendar").timegm((y, m, 15, 0, 0, 0)) ) for y in (2023, 2024, 2025, 2026) for m in (3, 9)], np.int64)
    members = np.empty(NA, object)
    for i in range(NA): members[i] = np.arange(NM)
    rng = np.random.default_rng(7)
    y4 = np.full((NA, NW), np.nan, np.float32); y4[:, :NM] = rng.normal(size=(NA, NM)).astype(np.float32)
    names = [f"f{k}" for k in range(5)] + ["ret5_sum_48_x"]          # one dropped by keep, five kept
    NC = len(names); keep = [k for k, nm in enumerate(names) if not nm.startswith(("ret5_sum_48", "ret5_sum_288"))]
    FEA = rng.normal(size=(NA, NW, NC)).astype(np.float32)
    np.savez(os.path.join(d, "meta.npz"), E_ts=E_ts, members=members, y4=y4, names=np.array(names))
    np.save(os.path.join(d, "fea.npy"), FEA)
    json.dump({"keep_names": [names[k] for k in keep]}, open(os.path.join(d, "pins.json"), "w"))
    # STORED = what a booster that returns row-sum/100 would scatter (this is the "truth" the gate compares against)
    P = np.full((NA, NW), np.nan, np.float32)
    for i in range(NA):
        P[i, :NM] = FEA[i, :NM][:, keep].sum(axis=1) / 100.0
    np.save(os.path.join(d, "stored.npy"), P)
    open(os.path.join(d, "boost.txt"), "w").write("synthetic\n")
    return offset

class SyntheticBooster:
    """Stub of lightgbm.Booster: predict = row-sum/100 (+ offset in the INVALID arm). No model is read."""
    offset = 0.0
    def __init__(self, model_file=None): self.model_file = model_file
    def predict(self, X): return X.sum(axis=1) / 100.0 + SyntheticBooster.offset
class SyntheticRegressor:
    def __init__(self, **kw): self.kw = kw
    def fit(self, X, y): return self
    def predict(self, X): return X.sum(axis=1) / 100.0

def run_arm(tag, refit, offset):
    d = tempfile.mkdtemp(prefix=f"gk_{tag}_"); fixture(d)
    fake = types.ModuleType("lightgbm"); fake.__version__ = "SYNTHETIC-STUB"
    fake.Booster, fake.LGBMRegressor = SyntheticBooster, SyntheticRegressor
    SyntheticBooster.offset = offset
    out = os.path.join(d, "receipt.json")
    os.environ["FM_GK_OUT"] = out; os.environ["FM_GK_REFIT"] = str(refit)
    saved = sys.modules.get("lightgbm"); sys.modules["lightgbm"] = fake
    try:
        spec = importlib.util.spec_from_file_location(f"gk_{tag}", DEV); m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        m.META, m.FEAP, m.PINSP = os.path.join(d, "meta.npz"), os.path.join(d, "fea.npy"), os.path.join(d, "pins.json")
        m.STORED, m.BOOST = os.path.join(d, "stored.npy"), os.path.join(d, "boost.txt")
        m.EXPECT = {}                                             # the pinned /workspace inputs do not exist here
        m.REFIT = refit
        rc = m.main()                                             # ← the WHOLE main, verdict produced by the device
    finally:
        if saved is not None: sys.modules["lightgbm"] = saved
        else: sys.modules.pop("lightgbm", None)
    r = json.load(open(out))
    return rc, r.get("GATE_B_REPRO_KING"), r

print("[arms] full main() with named synthetic stubs")
rc_p, v_p, r_p = run_arm("pass", 1, 0.0)
check("★★★ PASS arm: main() itself writes GATE_B_REPRO_KING=PASS and the process exit is 0",
      v_p == "PASS" and rc_p == 0, (v_p, rc_p, r_p.get("summary")))
rc_q, v_q, r_q = run_arm("partial", 0, 0.0)
check("★★★ PARTIAL arm (FM_GK_REFIT=0): verdict 'PARTIAL (2026 only)' — refits not run is NOT a pass — exit 3",
      str(v_q).startswith("PARTIAL") and rc_q == 3, (v_q, rc_q))
rc_i, v_i, r_i = run_arm("invalid", 1, 1.0)
check("★★★ INVALID arm (saved booster off by 1.0 > 1e-5): verdict INVALID, exit 3",
      v_i == "INVALID" and rc_i == 3, (v_i, rc_i, r_i.get("per_fold", {}).get("K_2026_saved_booster", {}).get("maxabs")))
check("★★ the verdict key the exit reads is the one the device writes (no 'GATE_B_REPRO' key exists in a King receipt)",
      "GATE_B_REPRO" not in r_p and "GATE_B_REPRO_KING" in r_p, sorted(k for k in r_p if k.startswith("GATE")))

print("\n[control] the pre-fix device (git HEAD~1) on the SAME PASS arm")
try:
    old = None
    for _ref in ("HEAD", "HEAD~1", "HEAD~2", "HEAD~3"):           # find the DEFECT SHAPE, not a fixed ancestor
        _c = subprocess.run(["git", "-C", HERE, "show", f"{_ref}:docs/fixprogram_2026-09-13/FX_MODEL/devices/fm_gate_b_repro_king.py"],
                            capture_output=True, text=True)
        if _c.returncode == 0 and 'rc.get("GATE_B_REPRO")' in _c.stdout and 'rc.get("GATE_B_REPRO_KING")' not in _c.stdout:
            old = _c.stdout; print(f"  (control source: {_ref})"); break
    if old is None:
        print("  UNAVAIL no ancestor within HEAD..HEAD~3 reads the DL key in the King device — control not run, not faked")
    else:
        tmp = os.path.join(tempfile.mkdtemp(), "fm_gate_b_repro_king_prefix.py"); open(tmp, "w").write(old)
        DEV_SAVE = DEV; DEV = tmp
        rc_o, v_o, _ = run_arm("prefix", 1, 0.0); DEV = DEV_SAVE
        check("★★★ (PRE-FIX: RED) the pre-fix exit reads the DL key: real PASS verdict, exit 3 — the reviewer's finding, reproduced",
              v_o == "PASS" and rc_o == 3, (v_o, rc_o))
except Exception as e:                                             # noqa: BLE001
    print(f"  UNAVAIL pre-fix source not reachable ({type(e).__name__}); control not run, not faked")
print(f"\n{N[0] - len(FAILS)}/{N[0]} checks passed")
if FAILS: print("FAILED:", *FAILS, sep="\n  "); sys.exit(1)
print("ALL PASS")
