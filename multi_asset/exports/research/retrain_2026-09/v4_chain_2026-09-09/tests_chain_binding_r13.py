#!/usr/bin/env python3
"""tests_chain_binding_r13.py — R13-C1: a MEMBER_LIVENESS receipt must be bound to THIS run's candidate, not merely internally consistent.

The independent reviewer (round 13, 7ba79b75 §4) produced a GENUINE PASS receipt from a healthy tiny dataset A, dropped it into candidate root B
whose own run of the same approved gate FAILS (king 2 / DL 2 / bundle 2 failing checks), and both consumers accepted it:
  · `prereq_receipt` returned rc 0, because `v4_gate_common.require` re-hashes the files the RECEIPT names — all of which are A's, all unchanged;
  · `fp2_decision.py` returned rc 0 with SWAP_RECOMMENDED, because it applied the same internal check.
Mutating the ticket's own bytes was correctly refused, so the hash machinery worked — it was verifying the wrong object.

Every cell here asserts the GREEN control first (the run's own genuine receipt passes), then the transplant (refused), then the negative control
(mutated bytes, still refused). Synthetic roots only; no production tree, no network, nothing executed beyond the two consumers.
Run: python3 tests_chain_binding_r13.py   (exit 0 iff ALL PASS)
"""
import hashlib, importlib.util, json, os, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__)); PY = sys.executable
N = [0]; FAILS = []
spec = importlib.util.spec_from_file_location("gc_b", f"{HERE}/v4_gate_common.py"); GC = importlib.util.module_from_spec(spec); spec.loader.exec_module(GC)
LIVENESS_FLOOR = GC.required_inputs("MEMBER_LIVENESS")[0]


def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()


def check(name, cond, detail=""):
    N[0] += 1
    print(("  OK   " if cond else "  FAIL ") + name + (("  — " + str(detail)[:230]) if (detail and not cond) else ""))
    if not cond: FAILS.append(name)


# ─────────────────────────── part 1: prereq_receipt ───────────────────────────
def candidate(t, tag, payload):
    """a candidate root with its own five artefacts (cache/holes/meta/targets/mask); `payload` makes tag A's bytes differ from tag B's"""
    R = os.path.join(t, tag); os.makedirs(f"{R}/v4_gates", exist_ok=True); os.makedirs(f"{R}/data", exist_ok=True)
    f = {}
    for k in ("cache", "hole_cells", "wide_fea_v4_meta", "dlw_v4raw_targets", "member_mask", "bundle_config"):
        p = f"{R}/data/{k}.bin"; open(p, "wb").write(f"{tag} {k} {payload}".encode()); f[k] = p
    return R, f


def liveness_receipt(R, D, f, name="member_liveness.json", end="gates", PASS=True):
    ins = {k: f[k] for k in ("cache", "hole_cells", "wide_fea_v4_meta", "dlw_v4raw_targets", "member_mask")}
    sets = {"wide_fea_v4_meta": {"dead_but_member": 0}, "dlw_v4raw_targets": {"dead_but_member": 0}}
    if end == "export":
        ins["bundle_config"] = f["bundle_config"]; sets["bundle_symbols_live"] = {"dead_at_last_anchor": []}
    rec = {"gate": "MEMBER_LIVENESS", "PASS": PASS, "self_sha256": sha(f"{D}/v4_gate_member_liveness.py"), "dead_but_member_total": 0,
           "window_rows": 288, "row_spacing_s": 300, "refusals": [], "sets": sets,
           "inputs_path": ins, "inputs_sha256": {k: sha(v) for k, v in ins.items()}}
    p = f"{R}/v4_gates/{name}"; json.dump(rec, open(p, "w"), indent=1); return p


def device_dir(t):
    """a device dir whose contract approves the real liveness gate source"""
    D = os.path.join(t, "D"); os.makedirs(D, exist_ok=True)
    for fn in ("v4_gate_common.py", "v4_gate_member_liveness.py"): shutil.copy2(f"{HERE}/{fn}", f"{D}/{fn}")
    c = json.load(open(f"{HERE}/ELIGIBILITY_CONTRACT.json"))
    c["gates"]["MEMBER_LIVENESS"]["approved_source_sha256"] = [sha(f"{D}/v4_gate_member_liveness.py")]
    json.dump(c, open(f"{D}/ELIGIBILITY_CONTRACT.json", "w"))
    return D


def prereq(D, R, receipt, binds):
    """drive chain_lib.sh's prereq_receipt exactly as the driver does"""
    args = " ".join(f'"{k}={v}"' for k, v in binds.items())
    log = os.path.join(os.path.dirname(receipt), "prereq.log")            # `say` writes the success line to $L, not to stdout
    sc = (f'set -o pipefail; D={D}; R={R}; PY={PY}; L={log}; V4_MONTH_ENV=""; . {HERE}/chain_lib.sh; '
          f'prereq_receipt probe liveness "{receipt}" MEMBER_LIVENESS {args}')
    r = subprocess.run(["bash", "-c", sc], capture_output=True, text=True)
    said = open(log).read() if os.path.exists(log) else ""
    return r.returncode, (r.stdout + r.stderr + said)


print("[1] prereq_receipt: a genuine PASS from ANOTHER candidate must not open this run")
with tempfile.TemporaryDirectory() as t:
    D = device_dir(t)
    RA, fA = candidate(t, "A", "healthy")           # the reviewer's tiny healthy dataset
    RB, fB = candidate(t, "B", "stale-bars")        # the candidate whose own run fails
    own = liveness_receipt(RB, D, fB)
    bindB = {k: fB[k] for k in ("cache", "hole_cells", "wide_fea_v4_meta", "dlw_v4raw_targets", "member_mask")}
    rc, out = prereq(D, RB, own, bindB)
    check("[1.0] GREEN: B's own genuine receipt, bound to B's artefacts ⇒ rc 0", rc == 0 and "bound to this run's artefacts" in out, (rc, out[-200:]))

    transplant = liveness_receipt(RA, D, fA, name="from_A.json")          # genuine, PASS, approved source, every recorded input on disk
    rc, out = prereq(D, RB, transplant, {})
    check("[1.1] the transplant passes WITHOUT a binding — this is exactly what the reviewer reproduced (require only re-hashes what the receipt names)",
          rc == 0, (rc, out[-200:]))
    rc, out = prereq(D, RB, transplant, bindB)
    check("[1.2] RED: the same transplanted receipt, bound to B's artefacts ⇒ rc 3 naming the other candidate's artefact",
          rc == 3 and "another candidate's artefact" in out, (rc, out[-220:]))

    # negative control: the binding must not be satisfiable by a same-path file whose bytes moved
    own2 = liveness_receipt(RB, D, fB, name="own2.json")
    open(fB["dlw_v4raw_targets"], "wb").write(b"B dlw_v4raw_targets rebuilt")
    rc, out = prereq(D, RB, own2, bindB)
    check("[1.3] NEGATIVE CONTROL: B's own receipt after B's targets were rebuilt ⇒ refused (sha differs), not silently accepted",
          rc == 3, (rc, out[-200:]))

print("\n[2] prereq_receipt: each bound key is checked on its own")
with tempfile.TemporaryDirectory() as t:
    D = device_dir(t); RB, fB = candidate(t, "B", "x"); RA, fA = candidate(t, "A", "y")
    mixed = {k: fB[k] for k in ("cache", "hole_cells", "wide_fea_v4_meta", "dlw_v4raw_targets", "member_mask")}
    rec = liveness_receipt(RB, D, fB, name="mixed.json")
    j = json.load(open(rec)); j["inputs_path"]["wide_fea_v4_meta"] = fA["wide_fea_v4_meta"]
    j["inputs_sha256"]["wide_fea_v4_meta"] = sha(fA["wide_fea_v4_meta"]); json.dump(j, open(rec, "w"))
    rc, out = prereq(D, RB, rec, mixed)
    check("[2.0] ONE key from the other candidate (the king meta) ⇒ refused and the key is named", rc == 3 and "wide_fea_v4_meta" in out, (rc, out[-200:]))
    rec2 = liveness_receipt(RB, D, fB, name="nokey.json")
    j = json.load(open(rec2)); j["inputs_path"].pop("member_mask"); j["inputs_sha256"].pop("member_mask"); json.dump(j, open(rec2, "w"))
    rc, out = prereq(D, RB, rec2, mixed)
    check("[2.1] a receipt that never recorded member_mask cannot be bound to this run's mask ⇒ refused", rc == 3 and "records no input" in out, (rc, out[-200:]))

# ─────────────────────────── part 2: fp2_decision.py ───────────────────────────
print("\n[3] fp2_decision.py: the decision must refuse a liveness receipt from another candidate")
sys.path.insert(0, HERE)
import fp2_decision_fixture as FX                                            # the suite's own root fixture (R13: it now builds liveness receipts)


def decide(X, **kw):
    py = X.per_year({"42": {"W_ALPHA": (0.06, 0.20), "KING_LIVE": (0.06, 0.20)}, "2027": {"W_ALPHA": (0.06, 0.20), "KING_LIVE": (0.06, 0.20)}})
    return X.run(py, X.export(), **kw)


X = FX.Root()
rc, out, j = decide(X)
check("[3.0] GREEN: the fixture's own liveness receipts ⇒ the decision runs and binds them (no liveness item in UNAVAILABLE)",
      rc == 0 and not [u for u in j["UNAVAILABLE"] if "liveness" in u.lower()], (rc, j["UNAVAILABLE"][:3]))
check("[3.1] GREEN: both semantic bindings are recorded, not assumed",
      all(j["binding"]["semantic"].get(k, {}).get("same_path") and j["binding"]["semantic"][k]["same_sha"]
          for k in j["binding"]["semantic"] if k.startswith("liveness_")), sorted(k for k in j["binding"].get("semantic", {}) if k.startswith("liveness_")))

# the transplant: a genuine receipt whose inputs are ANOTHER candidate's files
other = {}
for k in ("cache", "kmeta", "dlt", "mmask", "bundle_config"):
    p = f"{X.R}/data/other_{k}.bin"; open(p, "wb").write(f"other {k}".encode()); other[k] = p
lv_other = X.liveness("gates", path=f"{X.R}/v4_gates/lv_other.json", cache=other["cache"], kmeta=other["kmeta"], dlt=other["dlt"], mmask=other["mmask"])
rc, out, j = decide(X, lv=lv_other)
check("[3.2] RED: the gates-end receipt produced from another candidate's artefacts ⇒ the decision refuses it by semantic binding",
      any("liveness_gates" in u for u in j["UNAVAILABLE"]) and j["RECOMMENDATION"] != "SWAP_RECOMMENDED",
      (j["RECOMMENDATION"], [u for u in j["UNAVAILABLE"] if "liveness" in u][:3]))

lvx_other = X.liveness("export", path=f"{X.R}/v4_gates/lvx_other.json", bundle_cfg=other["bundle_config"])
rc, out, j = decide(X, lvx=lvx_other)
check("[3.3] RED: the export-end receipt that checked ANOTHER bundle's config ⇒ refused (the shipped live list was never this candidate's)",
      any("liveness_export.bundle_config" in u for u in j["UNAVAILABLE"]) and j["RECOMMENDATION"] != "SWAP_RECOMMENDED",
      (j["RECOMMENDATION"], [u for u in j["UNAVAILABLE"] if "bundle_config" in u][:2]))

lv_bad = X.liveness("gates", path=f"{X.R}/v4_gates/lv_dead.json", dead=7)
rc, out, j = decide(X, lv=lv_bad)
check("[3.4] NEGATIVE CONTROL: a bound receipt that carries dead members is still refused on its own verdict",
      any("dead-but-member" in u for u in j["UNAVAILABLE"]) and j["RECOMMENDATION"] != "SWAP_RECOMMENDED", j["UNAVAILABLE"][:2])

print(f"\n{'ALL PASS' if not FAILS else 'FAILURES: ' + str(FAILS)}  ({N[0]} checks)")
sys.exit(0 if not FAILS else 1)
