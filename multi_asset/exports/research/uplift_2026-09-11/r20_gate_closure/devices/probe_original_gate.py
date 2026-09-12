"""r20 STEP 1 — reproduce the independent reviewer's six export-gate probes against the ORIGINAL gate.

Reviewer device: codex worktree .../codex_uplift_review_2026-09-12/contracts/probe_export_gate.py (its fixtures lived in a
tempfile.TemporaryDirectory and are gone; RECEIPT_export_gate_probes.json keeps the outcomes). This script re-implements the
SAME method: the E5/E6/E7 block of the original gate source is executed VERBATIM (string-sliced between the two markers the
reviewer used) on isolated synthetic books, and the real v4_gate_common.require() is run against an ISOLATED copy of the frozen
contract with the original gate's sha approved. Nothing here touches the frozen contract, the live tree, or any real receipt.

Outputs RECEIPT_probe_original_gate.json: per probe, our observed E5_E6/E7/require outcome next to the reviewer's recorded one.
ENV (whitelist, all optional): R20_OUT (receipt dir), R20_SCRATCH (fixture dir). Exit 0 iff every probe reproduces.
"""
import os, sys, json, ast, calendar, hashlib, importlib.util, shutil, time
from pathlib import Path
import numpy as np

REPO = Path("/Users/haosiyu/Desktop/quant_research")
GATE = REPO / "multi_asset/exports/research/uplift_2026-09-11/infra2/v4e_gate_export.py"
CHAIN = REPO / "multi_asset/exports/research/retrain_2026-09/v4_chain_2026-09-09"
REVIEW = REPO / ".claude/worktrees/codex-independent-20260907/multi_asset/exports/research/codex_uplift_review_2026-09-12/contracts"
OUT = Path(os.environ.get("R20_OUT", REPO / "multi_asset/exports/research/uplift_2026-09-11/r20_gate_closure/receipts"))
SCRATCH = Path(os.environ.get("R20_SCRATCH", Path.home() / "cc_tmp/r20_probe_original"))
ENV_WHITELIST = {k: os.environ.get(k) for k in ("R20_OUT", "R20_SCRATCH")}

sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
src = GATE.read_text(); gate_sha = hashlib.sha256(src.encode()).hexdigest()
assert gate_sha == "f814c728938482b876cbcaa31f200832d207a0f89387d58ed3e2d0d45448e214", gate_sha
common_sha = sha(CHAIN / "v4_gate_common.py"); contract_sha = sha(CHAIN / "ELIGIBILITY_CONTRACT.json")
assert common_sha == "7b6d49a3de74df8840b8bdf5e6a20226505a5a8a6abf25d57f822d522cba2eb2", common_sha
assert contract_sha == "3299dc97ab0c90d51ac77297b605e5072bafd4cfaac954ab8655699c498f271b", contract_sha

# constants lifted from the gate source by AST (the reviewer's method: never retyped)
constants = {}
for node in ast.parse(src).body:
    if isinstance(node, ast.Assign):
        for t in node.targets:
            if isinstance(t, ast.Name) and t.id in ("COLS", "PINNED_BOOK_ENV", "DEVICE_SHA256"):
                constants[t.id] = ast.literal_eval(node.value)
code = src.split("# ---------- E5/E6/E7 book contract ----------")[1].split('R["PASS"]')[0]
COLS = constants["COLS"]; f0 = calendar.timegm((2025, 3, 1, 0, 0, 0)); n = 3168; f1 = f0 + n * 14400

if SCRATCH.exists(): shutil.rmtree(SCRATCH)
books = SCRATCH / "dev_v4/probe_artifacts"; books.mkdir(parents=True)
femat = SCRATCH / "femat.npy"; np.save(femat, np.zeros((n, 1)))
sig = SCRATCH / "signal.json"
results = {}


def run(name, patch=None, signal=None, mutate_arrays=False):
    """Verbatim reviewer fixture: 4 books, unit gross_total, W ones; optional cfg patch / signal receipt / array mutation."""
    sig.write_text(json.dumps({"PASS": True, "gate": "NOT_A_SIGNAL_GATE"} if signal is None else signal))
    for seat in ("dyn", "fix"):
        for seed in ("42", "2027"):
            cfg = {**constants["PINNED_BOOK_ENV"], "FSEED": seed, "W3FIX": "0.21,0,0.79" if seat == "fix" else None,
                   "HEALTH": {"device_sha256": constants["DEVICE_SHA256"]}, "FEMAT_NPZ": str(femat), "COST_B": [[2, 5, .8]] * 3}
            if patch: cfg.update(patch)
            r = np.zeros((n, len(COLS))); r[:, 0] = f0 + np.arange(n) * 14400; r[:, COLS.index("gross_total")] = 1
            w = np.ones((n, 1))
            if mutate_arrays: w[:] = 0; r[:, COLS.index("net_ex")] = float("inf")
            np.savez(books / f"w10_ablation_series_V4_TEST_{seat}_s{seed}.npz", d30_n2_c42_rec=r, d30_n2_c42_W=w,
                     cols=COLS, symbols=["BTCUSDT"], config_json=json.dumps(cfg))
    rec = {"checks": {}}
    def chk(key, ok, detail): rec["checks"][key] = {"ok": bool(ok), **detail}
    ns = {**constants, "np": np, "os": os, "json": json, "ARM": "TEST", "HC": str(SCRATCH), "FROZEN": (f0, f1), "N_FROZEN": n,
          "C": {c: i for i, c in enumerate(COLS)}, "E": {"SIGNAL_RECEIPT": str(sig)}, "sha256_file": sha, "chk": chk}
    exec(compile(code, str(GATE), "exec"), ns)
    results[name] = {k: v["ok"] for k, v in rec["checks"].items()}
    results[name]["_detail_first_book"] = {k: v for k, v in rec["checks"]["E5_E6_books"]["book_dyn_s42"].items() if k in ("cfg_diffs", "W_finite", "gross_finite_pos", "ok")}
    results[name]["_E7_detail"] = {k: rec["checks"]["E7_signal_provenance"].get(k) for k in ("signal_receipt_PASS", "signal_gate")}


run("positive_shape_control", signal={"PASS": True, "gate": "SIGNAL"})
run("bare_PASS_wrong_signal_gate")
run("signal_FAIL_negative_control", signal={"PASS": False})
run("different_cost_and_ftrim_accepted", patch={"COST_B": [[0, 0, 1]] * 3, "FTRIM_TH": -0.1})
run("bad_fixed_PIN_negative_control", patch={"PHI": 0.99})
run("zero_W_and_infinite_pnl_accepted", mutate_arrays=True)

# --- require() with an ISOLATED contract that approves the original gate sha (the frozen file is never written) ---
spec = importlib.util.spec_from_file_location("isolated_common", CHAIN / "v4_gate_common.py")
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
contract = json.loads((CHAIN / "ELIGIBILITY_CONTRACT.json").read_text())
contract["gates"]["BUNDLE_export"]["approved_source_sha256"] = [gate_sha]
cp = SCRATCH / "contract_isolated.json"; cp.write_text(json.dumps(contract)); mod.CONTRACT_PATH = str(cp)
inputs = {}
for key in mod.REQUIRED_INPUTS["BUNDLE_export"]:
    f = SCRATCH / (key + ".txt"); f.write_text("frozen upstream " + key); inputs[key] = str(f)
rp = SCRATCH / "receipt.json"
rp.write_text(json.dumps({"PASS": True, "gate": "BUNDLE_export", "self_sha256": gate_sha, "inputs_sha256": {k: mod.sha256_file(v) for k, v in inputs.items()}}))
kw = {"inputs": inputs, "expected_gate": "BUNDLE_export", "expected_self_sha": gate_sha}
bundle = SCRATCH / "exported_bundle"; bundle.mkdir(); pred = bundle / "slow_pred_pinned.npy"
np.save(pred, np.ones(5)); before = mod.require(str(rp), **kw)
np.save(pred, np.full(5, float("nan"))); after = mod.require(str(rp), **kw)
Path(inputs["wide_fea_v4"]).write_text("changed registered input"); control = mod.require(str(rp), **kw)
results["unbound_shipped_bundle"] = {"require_before": before[0], "require_after_exported_prediction_mutated": after[0],
                                     "require_after_registered_input_mutated": control[0], "reason_control": control[1],
                                     "registered_names": list(inputs)}

# --- compare with the reviewer's recorded outcomes ---
rev = json.load(open(REVIEW / "RECEIPT_export_gate_probes.json"))
assert rev["gate_sha256"] == gate_sha
expected = {  # (E5_E6 ok, E7 ok) as recorded by the reviewer; require probe separately
    "positive_shape_control": (True, True), "bare_PASS_wrong_signal_gate": (True, True), "signal_FAIL_negative_control": (True, False),
    "different_cost_and_ftrim_accepted": (True, True), "bad_fixed_PIN_negative_control": (False, True), "zero_W_and_infinite_pnl_accepted": (True, True)}
table = []; all_ok = True
for k, (e56, e7) in expected.items():
    r56 = rev["cases"][k]["E5_E6_books"]["ok"]; r7 = rev["cases"][k]["E7_signal_provenance"]["ok"]
    o56 = results[k]["E5_E6_books"]; o7 = results[k]["E7_signal_provenance"]
    rep = (r56, r7) == (o56, o7) == (e56, e7); all_ok &= rep
    table.append({"probe": k, "reviewer_E5_E6": r56, "reviewer_E7": r7, "ours_E5_E6": o56, "ours_E7": o7, "reproduced": rep})
u = rev["cases"]["unbound_shipped_bundle"]
rep_u = (u["before"][0], u["after_exported_prediction_mutation"][0], u["registered_input_mutation_negative_control"][0]) == (before[0], after[0], control[0]) == (True, True, False)
all_ok &= rep_u
table.append({"probe": "unbound_shipped_bundle", "reviewer": [u["before"][0], u["after_exported_prediction_mutation"][0], u["registered_input_mutation_negative_control"][0]],
              "ours": [before[0], after[0], control[0]], "reproduced": rep_u, "meaning": "[require before, after pred mutated, after registered input mutated]"})

OUT.mkdir(parents=True, exist_ok=True)
receipt = {"device": "probe_original_gate.py", "self_sha256": sha(__file__), "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "env_whitelist": ENV_WHITELIST, "python": sys.version.split()[0], "numpy": np.__version__,
           "sources": {"v4e_gate_export.py": gate_sha, "v4_gate_common.py": common_sha, "ELIGIBILITY_CONTRACT.json (frozen, read only)": contract_sha,
                       "reviewer_receipt": sha(REVIEW / "RECEIPT_export_gate_probes.json"), "reviewer_probe_script": sha(REVIEW / "probe_export_gate.py")},
           "method": "E5/E6/E7 block of the original gate exec'd verbatim on isolated synthetic books; real v4_gate_common.require against an isolated contract copy approving the original sha",
           "ALL_REPRODUCED": bool(all_ok), "table": table, "raw": results}
(OUT / "RECEIPT_probe_original_gate.json").write_text(json.dumps(receipt, indent=1, default=str))
print(json.dumps(table, indent=1)); print("ALL_REPRODUCED", all_ok)
sys.exit(0 if all_ok else 3)
