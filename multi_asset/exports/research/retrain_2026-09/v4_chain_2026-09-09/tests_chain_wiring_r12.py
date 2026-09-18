#!/usr/bin/env python3
"""Behavioural tests for the round-12 chain wiring fixes (independent review R12-C1 / R12-C3).

R12-C1 — the five stages added in round 11 were appended AFTER the stages that consume them: the real `if` order was
  … gates → arms → judge → export → controls → a0rerun → member_rule → per_year → decision
while the FP2 data gates call `fp2_gate_lib.bind_controls`, which refuses a root without `$R/controls/CONTROLS.json`, and the
export acceptance takes the A0 baseline books' identity before the A0 rerun could change their bytes. So a fresh full run could
not reach controls at all, and an export receipt could go stale the moment a0rerun ran.

R12-C3 — preflight bound the contract's `UMASK_NPZ` sha, but the arms stage never passed it: `run_v4_arms.sh` read
`V4_UMASK_NPZ` or fell back to the tree's own `$HC/masks/umask_UPIT_CRYPTO.npz`. The reviewer's argv spy showed the candidate
arms evaluated under the tree default in a clean environment and under a foreign mask when the parent environment carried one,
both at rc 0. `load_month_env` also never cleared that unregistered ambient key.

Everything here is local and offline: the only process the arms wrapper starts is an argv spy that prints and exits, so no
training, model or strategy code can run. Nothing is written outside the scratch directory.
Run: python3 tests_chain_wiring_r12.py   (exit 0 iff ALL PASS)"""
import hashlib, json, os, re, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__)); PY = sys.executable
TMP = tempfile.mkdtemp(prefix="chain_r12_", dir=os.environ.get("TMPDIR") or None)
N = [0]; FAILS = []


def check(name, cond, detail=""):
    N[0] += 1; print(("  OK   " if cond else "  FAIL ") + name + (("  — " + str(detail)[:230]) if detail and not cond else ""))
    if not cond: FAILS.append(name)


def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()


src = open(f"{HERE}/chain_v4_monthly.sh").read()
order = [m.group(1) for m in re.finditer(r'(?m)^if want (\w+); then(?:\s+#.*)?$', src)]   # member_rule/per_year/decision carry a trailing comment
pos = {s: i for i, s in enumerate(order)}

print("[1] R12-C1: the stage blocks now run in dependency order")
check("controls runs BEFORE gates (the FP2 data gates bind_controls against $R/controls/CONTROLS.json)",
      "controls" in pos and "gates" in pos and pos["controls"] < pos["gates"], order)
check("a0rerun runs BEFORE judge and export (both compare against the approved A0 baseline books)",
      pos.get("a0rerun", 99) < pos.get("judge", -1) and pos.get("a0rerun", 99) < pos.get("export", -1), order)
check("a0rerun still runs AFTER arms (it needs build_dev_v4's dev tree and the candidate ARMS_DONE marker)",
      pos.get("arms", 99) < pos.get("a0rerun", -1), order)
check("the decision is still last, after member_rule and per_year",
      pos.get("decision") == max(pos.values()) and pos["member_rule"] < pos["per_year"] < pos["decision"], order)
check("the order is exactly the reviewed dependency graph",
      order == ["preflight", "cache", "data", "controls", "gates", "king", "legs", "mwf", "refit", "np_export",
                "arms", "a0rerun", "judge", "export", "member_rule", "per_year", "decision"], order)

print("\n[2] R12-C1: the ordering is enforced by prerequisites, not by file order (a subset run cannot invert it)")
check("gates declares the controls receipt as a prerequisite when an FP2 data gate is selected",
      re.search(r'prereq_file gates controls .*CONTROLS\.json', src) and re.search(r'prereq_json_eq gates controls_verdict .*VERDICT PASS', src), None)
check("judge and export both declare the A0 rerun receipt as a prerequisite",
      'prereq_receipt judge a0rerun' in src and 'prereq_receipt export a0rerun' in src, None)

print("\n[3] R12-C3: the approved evaluation mask reaches the CANDIDATE arms, not only the baseline rerun")
wd = os.path.join(TMP, "wiring"); dev = os.path.join(wd, "device"); os.makedirs(dev, exist_ok=True)
shutil.copyfile(f"{HERE}/run_v4_arms.sh", f"{dev}/run_v4_arms.sh")
open(f"{dev}/run_arm.sh", "w").write('#!/bin/bash\nprintf "SPY_ARG=%s\\n" "$@"\nexit 0\n')   # argv spy: prints and exits, never a real arm
h = os.path.join(wd, "health"); kd = os.path.join(wd, "king")
for sub in ("dev_v4/logs", "dev_v4/f8_2026-08-22/preds", "masks", "calib"): os.makedirs(os.path.join(h, sub), exist_ok=True)
os.makedirs(kd, exist_ok=True); open(f"{kd}/SLOW_v4.npy", "wb").write(b"spy only")
for s_ in (42, 2027): open(f"{h}/dev_v4/f8_2026-08-22/preds/f10_v4RAW_s{s_}.npy", "wb").write(b"spy only")
for nm in ("approved_mask.npz", "foreign_mask.npz"): open(os.path.join(wd, nm), "wb").write(nm.encode())
open(f"{h}/masks/umask_UPIT_CRYPTO.npz", "wb").write(b"tree default")   # the old silent fallback


def arms(env_extra):
    log = f"{h}/dev_v4/logs/V4_A1_dyn_s42.out"
    if os.path.exists(log): os.remove(log)
    env = dict(os.environ, V4_HC=h, V4_KING_DIR=kd, V4_PY=PY); env.pop("V4_UMASK_NPZ", None); env.update(env_extra)
    r = subprocess.run(["bash", f"{dev}/run_v4_arms.sh", "A1", "42 2027"], capture_output=True, text=True, env=env)
    masks = sorted({x.split("UMASK_NPZ=")[1].split()[0] for x in (open(log).read().splitlines() if os.path.exists(log) else []) if "UMASK_NPZ=" in x})
    return r.returncode, masks, (r.stdout + r.stderr)


rc, masks, out = arms({"V4_UMASK_NPZ": os.path.join(wd, "approved_mask.npz")})
check("green baseline: the driver passes the contract mask ⇒ every arm is evaluated under exactly that file",
      rc == 0 and masks == [os.path.join(wd, "approved_mask.npz")], (rc, masks, out[-150:]))
rc, masks, out = arms({})
check("the driver passes NOTHING ⇒ ARMS_FAIL rc 3 naming R12-C3 (was: the tree's own default mask, rc 0)",
      rc == 3 and "ARMS_FAIL" in out and "R12-C3" in out and not masks, (rc, masks, out[-150:]))
rc, masks, out = arms({"V4_UMASK_NPZ": os.path.join(wd, "missing_mask.npz")})
check("a declared mask that does not exist ⇒ ARMS_FAIL rc 3 (a path is not evidence the file is there)",
      rc == 3 and "does not exist" in out, (rc, out[-150:]))

print("\n[4] R12-C3: an ambient V4_UMASK_NPZ cannot survive the contract loader")
env_file = os.path.join(TMP, "loader.env")
base = open(f"{HERE}/v4_month_2026-09_fp2.env").read()
base = re.sub(r'(?m)^R=.*$', f"R={TMP}", base); base = re.sub(r'(?m)^PY=.*$', f"PY={PY}", base)
# R12-C5 (2026-09-18): the September contract now DECLARES UMASK_NPZ itself. These cases append their own, and load_month_env refuses a
# duplicate key, so the declared line is removed first — the case still exercises exactly what it did before.
base = re.sub(r'(?m)^UMASK_NPZ=.*\n', '', base)
open(env_file, "w").write(base + f"UMASK_NPZ={os.path.join(wd, 'approved_mask.npz')}\n")
cmd = 'source "$1"; load_month_env "$2" >/dev/null; printf "%s|%s" "${UMASK_NPZ:-<unset>}" "${V4_UMASK_NPZ:-<unset>}"'
env = dict(os.environ, PY=PY, L="/dev/null", CHAIN_DEVICE_DIR=HERE, V4_UMASK_NPZ=os.path.join(wd, "foreign_mask.npz"))
r = subprocess.run(["bash", "-c", cmd, "probe", f"{HERE}/chain_lib.sh", env_file], capture_output=True, text=True, env=env)
got = (r.stdout.strip().splitlines() or [""])[-1].split("|")
check("a foreign ambient V4_UMASK_NPZ is cleared and re-derived from the contract's UMASK_NPZ",
      len(got) == 2 and got[0].endswith("approved_mask.npz") and got[1] == got[0], (r.returncode, r.stdout[-160:]))
open(env_file + ".nomask", "w").write(base)
r = subprocess.run(["bash", "-c", cmd, "probe", f"{HERE}/chain_lib.sh", env_file + ".nomask"], capture_output=True, text=True, env=env)
got = (r.stdout.strip().splitlines() or [""])[-1].split("|")
check("a contract that declares NO mask leaves V4_UMASK_NPZ unset, so each consumer refuses instead of defaulting",
      len(got) == 2 and got[1] == "<unset>", (r.returncode, r.stdout[-160:]))

print("\n[4b] R12-C1 end to end: on a FRESH root the gates stage stops ON the controls dependency, by name")
fr = os.path.join(TMP, "freshroot"); root = os.path.join(fr, "root"); os.makedirs(os.path.join(root, "v4_gates"), exist_ok=True)
os.makedirs(os.path.join(root, "masks"), exist_ok=True); open(os.path.join(root, "masks", "member_mask_tradable_W24H_cachegrid.npz"), "wb").write(b"stub")
fenv = os.path.join(fr, "env.env")
_b = re.sub(r'(?m)^R=.*$', f"R={root}", re.sub(r'(?m)^PY=.*$', f"PY={PY}", open(f"{HERE}/v4_month_2026-09_fp2.env").read()))
_b = re.sub(r'(?m)^UMASK_NPZ=.*\n', '', _b)                                   # same reason as [4]: this case appends its own
open(fenv, "w").write(_b + f"UMASK_NPZ={os.path.join(wd, 'approved_mask.npz')}\n")


def stage(name, env_file):
    r = subprocess.run(["bash", f"{HERE}/chain_v4_monthly.sh", env_file], capture_output=True, text=True,
                       cwd=HERE, env=dict(os.environ, PY=PY, V4_STAGES=name, L="/dev/null"))
    fails = [x for x in (r.stdout + r.stderr).splitlines() if "FAIL_" in x]
    return r.returncode, (fails[-1].strip() if fails else "")


import time as _t
_pf = {"gate": "PREFLIGHT", "PASS": True, "root": root, "utc": _t.strftime("%Y-%m-%dT%H:%M:%SZ", _t.gmtime()),
       "month_env_sha256": hashlib.sha256(open(fenv, "rb").read()).hexdigest()}
json.dump(_pf, open(os.path.join(root, "v4_gates", "preflight.json"), "w"))
for sub in ("f8_v4/gates", "f8_v4/data", "dlw_v4raw/data", "dlw_hf3/data"): os.makedirs(os.path.join(root, sub), exist_ok=True)
for rel in ("dlw_v4raw/data/dlw_targets.npz", "dlw_hf3/data/dlw_targets.npz", "f8_v4/data/f8_fea89.npz"): open(os.path.join(root, rel), "wb").write(b"stub")
for T, tp in (("RAW", "dlw_v4raw/data/dlw_targets.npz"), ("CLIP", "dlw_hf3/data/dlw_targets.npz")):
    json.dump({"targets_sha256": sha(os.path.join(root, tp)), "fea89_sha256": sha(os.path.join(root, "f8_v4/data/f8_fea89.npz"))},
              open(os.path.join(root, f"f8_v4/gates/F10_GATE_{T}.json"), "w"))
rc, last = stage("gates", fenv)
check("fresh root, data prerequisites satisfied, no controls receipt ⇒ FAIL_gates_prereq_controls rc 3 (was: gates ran and the FP2 gate died inside bind_controls, with controls scheduled AFTER it)",
      rc == 3 and last.endswith("FAIL_gates_prereq_controls"), (rc, last))
json.dump({"VERDICT": "FAIL"}, open(os.path.join(root, "controls", "CONTROLS.json"), "w")) if os.makedirs(os.path.join(root, "controls"), exist_ok=True) is None else None
rc, last = stage("gates", fenv)
check("a controls receipt that is NOT PASS is refused by name too (VERDICT is checked, not the file's existence)",
      rc == 3 and last.endswith("FAIL_gates_prereq_controls_verdict"), (rc, last))

print("\n[5] R12-C2: the decision device consumes and re-verifies both liveness ends")
dec = open(f"{HERE}/fp2_decision.py").read()
check("LIVENESS_JSON and LIVENESS_EXPORT_JSON are required inputs (absent ⇒ UNAVAILABLE), under R/v4_gates",
      dec.count("LIVENESS_JSON") >= 3 and dec.count("LIVENESS_EXPORT_JSON") >= 3, None)
check("both are re-verified through v4_gate_common.require with recorded_extras, and the export end must carry bundle_symbols_live",
      'expected_gate="MEMBER_LIVENESS"' in dec and "recorded_extras=True" in dec and "bundle_symbols_live" in dec, None)
check("the driver's decision stage passes both receipts", "LIVENESS_JSON=$R/v4_gates/member_liveness.json" in src and "LIVENESS_EXPORT_JSON=$R/v4_gates/member_liveness_export.json" in src, None)

print("\n[6] R15-C1: the env-leak CLASS is closed in run_gate (the sibling of R12-C3, without adding a new name)")
lib = open(f"{HERE}/chain_lib.sh").read()
check("run_gate derives an ambient strip from the gate's OWN declaration (gate_env_keys → `--env-keys`), not a hand-maintained name list",
      "gate_env_keys" in lib and "--env-keys" in lib and "ambient strip" in lib, None)
check("a declared key is kept only if it is an explicit run_gate arg OR a governed contract key (V4_MONTH_KEYS ∪ optionals); anything else is unset before the gate runs",
      re.search(r'case " \$V4_MONTH_KEYS \$V4_MONTH_OPTIONAL_KEYS " in \*" \$_k "\*\) continue', lib) is not None
      and re.search(r'for _k in \$_strip; do unset "\$_k"; done', lib) is not None, None)
gk = subprocess.run([PY, f"{HERE}/v4_gate_member_liveness.py", "--env-keys"], capture_output=True, text=True)
declared = set(gk.stdout.split())
governed = set(re.search(r'V4_MONTH_KEYS="([^"]*)"', lib).group(1).split()) | set(re.search(r'V4_MONTH_OPTIONAL_KEYS="([^"]*)"', lib).group(1).split())
check("EXPORT_ANCHOR_TS is a DECLARED gate read but NOT a governed contract key ⇒ run_gate strips an ambient one (R12-C3 had to add the name V4_UMASK_NPZ by hand; this class needs no new name, and V4_UMASK_NPZ is not even a liveness-gate read)",
      gk.returncode == 0 and "EXPORT_ANCHOR_TS" in declared and "EXPORT_ANCHOR_TS" not in governed and "V4_UMASK_NPZ" not in declared, (sorted(declared), "EXPORT_ANCHOR_TS" in governed))

print(f"\n{'ALL PASS' if not FAILS else 'FAILURES: ' + str(FAILS)}  ({N[0]} checks)")
sys.exit(0 if not FAILS else 1)
