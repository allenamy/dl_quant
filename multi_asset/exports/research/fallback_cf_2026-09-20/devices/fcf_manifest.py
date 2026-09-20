#!/usr/bin/env python3
"""fcf_manifest.py — one manifest for the whole F-family run: every device sha, every pinned input sha, every receipt sha, and the
VERBATIM command that produced each artefact. Written last, so a reader can rerun any step without reading this transcript.
Missing files are listed as MISSING with their expected path — never silently skipped (an absent artefact must be visible).
usage: fcf_manifest.py
"""
import hashlib, json, os, time

OUT = "/workspace/fallback_cf_2026-09-20"
D = f"{OUT}/devices"
ENV = "env -i PATH=/usr/bin:/bin HOME=/root LC_CTYPE=C.UTF-8"


def sha(p):
    if not os.path.exists(p): return None
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


def entry(p):
    s = sha(p)
    return {"path": p, "sha256": s} if s else {"path": p, "sha256": None, "state": "MISSING"}


STEPS = [
    {"step": "0. judge devices, byte copies of the certified baseline-tables set",
     "cmd": "for f in bt_launch.py bt_driver_lib.py bt_hist_sim31.py bt_objb_targets.py bt_run_summary.py bt_tables.py; do "
            "cp -p /workspace/baseline_tables_2026-09-19/devices_v3/$f /workspace/fallback_cf_2026-09-20/devices/$f; done; "
            "ln -sfn /workspace/baseline_tables_2026-09-19/devices/exec_copy /workspace/fallback_cf_2026-09-20/devices/exec_copy",
     "artefacts": [f"{D}/{f}" for f in ("bt_launch.py", "bt_driver_lib.py", "bt_hist_sim31.py", "bt_objb_targets.py", "bt_run_summary.py", "bt_tables.py")]},
    {"step": "1. structural-assertion selftest (baseline green, then four mutations, all must go red)",
     "cmd": f"cd {OUT} && /workspace/venv/bin/python -B devices/fcf_targets.py --selftest",
     "artefacts": [f"{OUT}/receipts/FCF_TARGETS_SELFTEST.json"]},
    {"step": "2. build the F0 / F1 / F2 / F4a target files and assert them on the full population",
     "cmd": f"cd {OUT} && /workspace/venv/bin/python -B devices/fcf_targets.py",
     "artefacts": [f"{OUT}/receipts/FCF_TARGETS.json"] + [f"{OUT}/work/TARGETS_{a}_A0_main.npz" for a in ("F0", "F1", "F2", "F4a")]
                  + [f"{OUT}/receipts/TARGETS_{a}_A0_main.json" for a in ("F0", "F1", "F2", "F4a")]},
    {"step": "3. freeze the run config (inherits the certified A0 config; only pod_root and runs differ)",
     "cmd": f"/workspace/venv/bin/python -B {D}/mk_runcfg.py",
     "artefacts": [f"{OUT}/RUN_CONFIG_fallback_cf_F_2026-09-20.json"]},
    {"step": "4. the judge: 4 arms x 32 fill paths, certified simulator v3.1, unchanged",
     "cmd": f"cd {OUT} && nohup setsid {ENV} nice -n 10 /workspace/venv/bin/python -B devices/bt_launch.py PATH,HOME,LC_CTYPE "
            f"RUN_CONFIG_fallback_cf_F_2026-09-20.json > logs/launch_F_full.log 2>&1 &",
     "artefacts": [f"{OUT}/receipts/BT_LAUNCH_full.json"]},
    {"step": "5. THE CONTROL: F0's 32 paths must be bitwise equal to the certified A0 run",
     "cmd": f"cd {OUT} && /workspace/venv/bin/python -B devices/fcf_control_F0.py runs/OBJB_F0_scaled_rule_raw_UAFE OBJB_F0_scaled_rule_raw_UAFE "
            f"/workspace/baseline_tables_2026-09-19/runs/OBJB_A0_scaled_rule_raw_UAFE OBJB_A0_scaled_rule_raw_UAFE 32 "
            f"{OUT}/receipts/FCF_CONTROL_F0.json",
     "artefacts": [f"{OUT}/receipts/FCF_CONTROL_F0.json"]},
    {"step": "6. §4 concentration / staleness / hold-run columns",
     "cmd": f"cd {OUT} && /workspace/venv/bin/python -B devices/fcf_risk_weights.py RUN_CONFIG_fallback_cf_F_2026-09-20.json",
     "artefacts": [f"{OUT}/receipts/FCF_RISK_WEIGHTS.json"]},
    {"step": "7. why the preflight failed, per year (description of the mechanism; decides nothing)",
     "cmd": f"cd {OUT} && /workspace/venv/bin/python -B devices/fcf_preflight_reasons.py",
     "artefacts": [f"{OUT}/receipts/FCF_PREFLIGHT_REASONS.json"]},
    {"step": "8. F4b producer: one line changed, proved before it ran",
     "cmd": f"cd {OUT} && /workspace/venv/bin/python -B devices/fcf_mk_producer_F4b.py",
     "artefacts": [f"{OUT}/receipts/FCF_PRODUCER_F4b.json", f"{D}/shadow_loop_v3_replay_F4b.py"]},
    {"step": "9. F4b counterfactual re-chain (producer only, 10,039 anchors, one core, no GPU, no exchange calls)",
     "cmd": f"cd {OUT} && nohup setsid env -i PATH=/usr/bin:/bin HOME=/root LC_CTYPE=C.UTF-8 OBJB_ROOT=/workspace/object_b_2026-09-19 "
            f"OBJB_ARM=A0 OBJB_DATA=holefix2 nice -n 12 /workspace/venv/bin/python -B devices/fcf_rechain_F4b.py "
            f"PATH,HOME,LC_CTYPE,OBJB_ROOT,OBJB_ARM,OBJB_DATA > logs/rechain_F4b.log 2>&1 &",
     "artefacts": [f"{OUT}/receipts/FCF_RECHAIN_F4b.json", f"{OUT}/work/F4b_KING.npz"]},
    {"step": "10. the re-chain's two-sided structural assertion",
     "cmd": f"cd {OUT} && /workspace/venv/bin/python -B devices/fcf_rechain_assert.py",
     "artefacts": [f"{OUT}/receipts/FCF_RECHAIN_ASSERT.json"]},
    {"step": "11. build the F4b target file",
     "cmd": f"cd {OUT} && /workspace/venv/bin/python -B devices/fcf_targets_F4b.py",
     "artefacts": [f"{OUT}/receipts/TARGETS_F4b_GATE.json", f"{OUT}/work/TARGETS_F4b_A0_main.npz", f"{OUT}/receipts/TARGETS_F4b_A0_main.json"]},
    {"step": "12. main-reading tables and the paired bootstrap",
     "cmd": f"cd {OUT} && /workspace/venv/bin/python -B devices/fcf_tables.py RUN_CONFIG_fallback_cf_F_2026-09-20.json "
            f"{OUT}/receipts/FCF_TABLES.json",
     "artefacts": [f"{OUT}/receipts/FCF_TABLES.json"]},
    {"step": "13. readings P and P2 (the certified post-processors, byte copies, run against the F run dirs)",
     "cmd": f"/workspace/venv/bin/python -B {D}/mk_preading_cfg.py F0 F1 F2 F4a [F4b] && cd {OUT} && "
            f"{ENV} /workspace/venv/bin/python -B devices/bt_p_reading.py PATH,HOME,LC_CTYPE RUN_CONFIG_Preading_F_2026-09-20.json "
            f"receipts/FCF_P_READING.json && {ENV} /workspace/venv/bin/python -B devices/bt_p2_reading.py PATH,HOME,LC_CTYPE "
            f"RUN_CONFIG_P2reading_F_2026-09-20.json receipts/FCF_P2_READING.json",
     "artefacts": [f"{OUT}/receipts/FCF_P_READING.json", f"{OUT}/receipts/FCF_P2_READING.json"]},
    {"step": "14. render the tables to markdown (no number is transcribed by hand)",
     "cmd": f"cd {OUT} && /workspace/venv/bin/python -B devices/fcf_render.py receipts/FCF_TABLES.json receipts/FCF_RISK_WEIGHTS.json "
            f"work/TABLES.md",
     "artefacts": [f"{OUT}/work/TABLES.md"]},
]

doc = {"device": "fcf_manifest.py", "self_sha256": sha(os.path.abspath(__file__)),
       "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
       "root_pod2": OUT, "root_repo": "multi_asset/exports/research/fallback_cf_2026-09-20",
       "note": "every command is verbatim; the judge, the simulator, the prices, the calibration and the executor tree are the certified "
               "baseline-tables ones and are NOT re-derived here — their pins live in RUN_CONFIG_fallback_cf_F_2026-09-20.json",
       "devices": {os.path.basename(p): entry(p) for p in sorted(
           os.path.join(D, f) for f in os.listdir(D) if f.endswith(".py"))},
       "steps": [dict(s, artefacts=[entry(a) for a in s["artefacts"]]) for s in STEPS]}
cfgp = f"{OUT}/RUN_CONFIG_fallback_cf_F_2026-09-20.json"
if os.path.exists(cfgp):
    C = json.load(open(cfgp))
    doc["inherited_pins"] = {k: {"path": v["path"], "sha256": v["sha256"]} for k, v in C["pins"].items()}
    doc["run_config"] = entry(cfgp)
    doc["arm_targets"] = {r["arm"]: r["targets"]["sources"][0] for r in C["runs"]}
p = f"{OUT}/receipts/FCF_MANIFEST.json"
json.dump(doc, open(p + ".tmp", "w"), indent=1); os.replace(p + ".tmp", p)
miss = [a["path"] for s in doc["steps"] for a in s["artefacts"] if a.get("state") == "MISSING"]
print("FCF_MANIFEST written", p, "sha256", sha(p))
print("artefacts MISSING:", len(miss))
for m in miss: print("   MISSING", m)
