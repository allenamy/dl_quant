#!/usr/bin/env python3
"""d10_stage5_engine.py -- line D stage 5: the D10-swap combo (stage 4) through dlarch's chain steps 2-5 (adapter spec, adapter with
read-back, X-axis RUN_CONFIG derived from the NEWS2_s42X base, team engine gate, bt_launch) and dlarch_cell_retain against
DLARCH_REF_NC_s42X -- so the cell is on the same axis, judge (news_stats 7141ba42), control and engine as F10_FULL / R1.4 (dlarch's
route, 2026-09-26 20:0xZ). Every step's function is IMPORTED from dlarch_chain_run.py (engine_gate, mem_gate, run, constants);
nothing is re-implemented except the combo source (a directory argument instead of news2_combo.py) and this cell's arm name.
Nothing is written under /dev/shm (root under /workspace); /dev/shm free is measured before the engine and must be >= 5 GiB (lead).
usage: env -i PATH=/usr/bin:/bin HOME=/root /workspace/venv/bin/python -B d10_stage5_engine.py <combo_dir> <root> [--engine | --identity]
  --identity: the stage-4 IDENTITY combo (== combo_s42 bitwise) through steps 1-4 only; every array of the resulting TARGETS npz must
              equal dlarch's REF_NC_s42X targets bitwise (the npz carries arrays only, no arm label) -- proves this driver's adapter
              path is the one the control cell went through. Red => the D10 cell is not started.
Executor (protocol s10-f): news2, this process under setsid on pod2; supervisor: news2's waiter on <root>/logs/stage5.log.
"""
import hashlib, importlib.util, json, os, shutil, sys, time

CR_PATH = "/workspace/dlarch_2026-09-24/dlarch_chain_run.py"
spec = importlib.util.spec_from_file_location("dlarch_chain_run", CR_PATH); CR = importlib.util.module_from_spec(spec)
sys.path.insert(0, os.path.dirname(CR_PATH)); spec.loader.exec_module(CR)
ARM = "NEWS2_D10KFSWAP_s42"          # one source of truth for the arm name (dlarch's lesson: copies drift)
SHM_MIN_GIB = 5.0                    # lead 2026-09-26: never leave /dev/shm below 5 GiB (others' engine gates need 4)
REF_CELL = "/workspace/dlarch_2026-09-24/chain/ref_nc_s42X/runs/DLARCH_REF_NC_s42X_scaled_rule_raw_UAFE"
REF_TAG = "DLARCH_REF_NC_s42X_scaled_rule_raw_UAFE"
REF_TARGETS = "/workspace/dlarch_2026-09-24/chain/ref_nc_s42X/targets/TARGETS_DLARCH_REF_NC_s42X.npz"


def sha(p): return CR.sha(p)


def main():
    combo, root = sys.argv[1], sys.argv[2]; do_engine = "--engine" in sys.argv; identity = "--identity" in sys.argv
    assert not (do_engine and identity)
    global ARM
    if identity: ARM = "NEWS2_D10ID_s42"
    L = f"{root}/logs"
    for d in ("configs", "targets", "runs", "logs", "work", "receipts"): os.makedirs(f"{root}/{d}", exist_ok=True)
    rec = {"device": os.path.basename(__file__), "self_sha256": sha(os.path.abspath(__file__)), "chain_run": [CR_PATH, sha(CR_PATH)],
           "arm": ARM, "root": root, "combo_dir": combo, "utc_start": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "steps": {}}
    # ---- 1. stage the combo as <root>/work/combo_s42 with an adapter-shaped TARGET_RECEIPT (policy shas from the files themselves)
    s4 = json.load(open(f"{combo}/STAGE4_RECEIPT.json")); assert s4["mode"] == ("identity" if identity else "d10"), s4["mode"]
    if not identity:
        idr = json.load(open(os.path.join(os.path.dirname(root), "identity", "receipts", "STAGE5_NEWS2_D10ID_s42.json")))
        assert idr.get("IDENTITY_VERDICT") == "BITWISE", "stage-5 adapter identity not BITWISE: refused"
    cdir = f"{root}/work/combo_s42"
    if os.path.lexists(cdir): shutil.rmtree(cdir) if not os.path.islink(cdir) else os.unlink(cdir)
    os.makedirs(cdir)
    pols = {}
    for pol in ("literal", "scaled_diagnostic"):
        shutil.copy2(f"{combo}/{pol}.npz", f"{cdir}/{pol}.npz")
        got = sha(f"{cdir}/{pol}.npz"); assert got == s4["policies"][pol]["sha"], (pol, "copy != stage-4 receipt")
        pols[pol] = {"path": f"{cdir}/{pol}.npz", "sha": got, "reasons": s4["policies"][pol]["reasons"]}
    tr = {"status": "D10_FUNDING_SWAP_TARGETS_NOT_EXECUTION_PNL", "seed": 42, "policies": pols,
          "state_init": "zero at 2023-01-01; hypothetical common start, not live archived state",
          "hold_contract": "trade_mask False = maintain quantities, never King substitution",
          "stage4_receipt": {"path": f"{combo}/STAGE4_RECEIPT.json", "sha256": sha(f"{combo}/STAGE4_RECEIPT.json")},
          "limits": ["models NOT refit: King and F10 are the delivered s42 weights fed D10 funding features",
                     "anchors after 2026-09-01T02:00Z have no rebuilt funding events; outside the frozen reading window",
                     "not a deployable version; a measuring instrument for the funding-feature swap alone"]}
    CR.sio.write_json(f"{cdir}/TARGET_RECEIPT.json", tr)
    rec["steps"]["stage_combo"] = {"target_receipt_sha256": sha(f"{cdir}/TARGET_RECEIPT.json"), "policies": {k: v["sha"] for k, v in pols.items()}}
    # ---- 2. adapter spec (dlarch's derived device, arm passed in)
    rc = CR.run([CR.PV, "-B", f"{CR.DEV}/news2_adapter_specs.py", "PATH,HOME,LC_CTYPE", root, "42", ARM], f"{L}/spec.log")
    assert rc == 0, "adapter spec failed"
    specp = f"{root}/configs/ADAPTER_SPEC_{ARM}.json"; rec["steps"]["adapter_spec"] = {"sha256": sha(specp)}
    # ---- 3. adapter + the three read-back checks of chain_run L380-L407
    tnpz = f"{root}/targets/TARGETS_{ARM}.npz"; tjson = tnpz.replace(".npz", ".json")
    rc = CR.run([CR.PV, "-B", "ovn_adapter.py", "PATH,HOME,LC_CTYPE", specp, tnpz, tjson], f"{L}/adapter.log", cwd=f"{CR.NS}/engine")
    assert rc == 0, "adapter failed"
    R_ = json.load(open(tjson))
    import numpy as np
    with np.load(tnpz, allow_pickle=False) as z:
        for k in z.files: _ = z[k].tobytes()[:1] if z[k].size else b""
    assert R_.get("targets_npz_sha256") == sha(tnpz), "targets receipt and npz disagree"
    rec["steps"]["adapter"] = {"targets_npz_sha256": sha(tnpz), "targets_json_sha256": sha(tjson), "readback_verified": True}
    if identity:
        A, B = np.load(tnpz), np.load(REF_TARGETS)
        cmp_ = {"keys_equal": sorted(A.files) == sorted(B.files)}
        for k in B.files:
            x, y = A[k], B[k]
            cmp_[k] = -1 if (x.shape != y.shape or x.dtype != y.dtype) else int((x.view(np.uint8).reshape(len(x), -1) != y.view(np.uint8).reshape(len(y), -1)).any(1).sum()) if x.size else 0
        rec["identity_vs_ref_targets"] = {"ref": [REF_TARGETS, sha(REF_TARGETS)], "differing_rows": cmp_, "npz_sha_equal": sha(tnpz) == sha(REF_TARGETS)}
        rec["IDENTITY_VERDICT"] = "BITWISE" if cmp_["keys_equal"] and all(v == 0 for k, v in cmp_.items() if k != "keys_equal") else "DIFFERS"
        print("STAGE5_IDENTITY", rec["IDENTITY_VERDICT"], json.dumps(rec["identity_vs_ref_targets"]), flush=True)
    # ---- 4. RUN_CONFIG from the X base, only targets / arm / pod_root changed (chain_run step 4)
    cfg = json.load(open(CR.BASE_CFG)); base_run = [r for r in cfg["runs"] if r["tag"].endswith(CR.BASE_CELL_SUFFIX)]
    assert len(base_run) == 1
    r0 = json.loads(json.dumps(base_run[0])); r0["arm"] = ARM; r0["tag"] = f"{ARM}|scaled|rule|raw|UAFE"; r0["targets"]["arm"] = ARM
    for x in r0["targets"]["sources"]:
        x["npz"] = tnpz; x["npz_sha256"] = sha(tnpz); x["receipt"] = tjson; x["receipt_sha256"] = sha(tjson)
    r0["role"] = "line D funding-only control cell s42 (PLAN_funding_only_control_cell rev 1; reading rule R1.3 frozen c5cfeb5e5)"
    cfg["runs"] = [r0]; cfg["paths"]["pod_root"] = root; cfg["config"] = f"RUN_CONFIG_{ARM}"
    cpath = f"{root}/configs/RUN_CONFIG_{ARM}.json"; CR.sio.write_json(cpath, cfg)
    rec["steps"]["run_config"] = {"path": cpath, "sha256": sha(cpath), "tag": r0["tag"], "base_config": [CR.BASE_CFG, sha(CR.BASE_CFG)]}
    # ---- 5. engine behind the team gate + lead's 5 GiB /dev/shm floor
    if do_engine:
        shm = CR.shm_free_gib(); rec["shm_free_gib_before_gate"] = shm
        assert shm is not None and shm >= SHM_MIN_GIB, f"/dev/shm free {shm} GiB < {SHM_MIN_GIB}: not starting (lead rule)"
        # rev 1 (dlarch's condition I missed on the first cell, 20:18Z): R1.4 cells have priority -- no engine start while any
        # CHAIN/.claim_NESTEP_s* exists. chain_run's engine_gate does not look at claims, so this wait is its own step, recorded.
        import glob as _g
        claims, t_c = [], time.monotonic()
        while True:
            claims = sorted(_g.glob("/workspace/dlarch_2026-09-24/CHAIN/.claim_NESTEP_s*"))
            if not claims: break
            assert time.monotonic() - t_c < 14400, f"R1.4 claims still present after 4 h: {claims}"
            time.sleep(60)
        rec["r14_claims_waited_s"] = int(time.monotonic() - t_c)
        rec["engine_gate"] = CR.engine_gate(cpath)
        rec["mem_gate_before_engine"] = CR.mem_gate(); rec["shm_free_gib_at_start"] = CR.shm_free_gib()
        t0 = time.monotonic()
        rc = CR.run([CR.PV, "-B", "bt_launch.py", "PATH,HOME,LC_CTYPE", cpath, "--resume", ARM], f"{L}/engine.log", cwd=f"{CR.NS}/engine")
        rd = f"{root}/runs/{r0['tag'].replace('|', '_')}"
        npaths = len([f for f in os.listdir(rd) if f.startswith("PATH") and f.endswith(".npz")]) if os.path.isdir(rd) else 0
        rec["steps"]["engine"] = {"rc": rc, "seconds": round(time.monotonic() - t0, 1), "path_npz_found": npaths, "expected": 32, "run_dir": rd}
        assert rc == 0 and npaths == 32, rec["steps"]["engine"]
        rec["mem_gate_after_engine"] = CR.mem_gate()
        # ---- 6. retain against the in-service NC s42X control, same frozen judge (verify only; nothing deleted)
        rout = f"{root}/receipts/RETAIN_{ARM}"
        rc = CR.run([CR.PV, "-B", "/workspace/dlarch_2026-09-24/dlarch_cell_retain.py", "--cell", rd, "--tag", r0["tag"].replace("|", "_"),
                     "--control-cell", REF_CELL, "--control-tag", REF_TAG, "--engine", f"{CR.NS}/engine", "--out", rout,
                     "--env-whitelist", "PATH,HOME,LC_CTYPE"], f"{L}/retain.log")
        rec["steps"]["retain"] = {"rc": rc, "out": rout}
        assert rc == 0, "retain failed"
    rec["utc_end"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    jsha = CR.sio.write_json(f"{root}/receipts/STAGE5_{ARM}.json", rec)
    print(f"STAGE5_DONE engine={'yes' if do_engine else 'no'} targets={rec['steps']['adapter']['targets_npz_sha256'][:16]} json={jsha[:16]}", flush=True)


if __name__ == "__main__":
    main()
