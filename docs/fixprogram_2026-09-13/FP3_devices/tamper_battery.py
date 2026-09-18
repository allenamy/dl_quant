#!/usr/bin/env python3
"""Hermetic tamper red-battery for seal_manifest.py.

Self-contained: it SYNTHESISES a complete, internally self-consistent fixture (merge records,
shard results, refit + np_export witnesses, per-fold .pt/.npz stand-ins, the 17 registered
artefacts, the 9 devices, and the logs) in a temporary directory it creates and OWNS, points the
seal at it via FP3_ROOT / FP3_WS, and cleans it up at the end. Stdlib only — no pod, no numpy, no
prior state; a clean checkout runs it with `python3 tamper_battery.py` next to seal_manifest.py.

It first proves the untampered fixture SEALS (baseline GREEN — otherwise the refusals below would
be vacuous), then applies each tamper and requires: exit != 0, verdict NOT SEALED, and the
SPECIFIC expected refusal present. The artefact stand-ins are arbitrary bytes whose sha256 is
computed and then written into the witnesses, so every cross-check is self-consistent without any
real model files. This proves the REFUSALS fire; proving the real pod artefacts seal cleanly is a
separate, pod-dependent, point-in-time measurement (seal_manifest_realrun_*.txt), not this.
"""
import json, os, sys, shutil, tempfile, subprocess, hashlib

TAG = "mE1cX7"
SEEDS = [42, 2027]
MONTHS = [f"{y}{m:02d}" for y in (2025, 2026) for m in range(1, 13)][:20]  # 202501..202608
SEAL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "seal_manifest.py")


def H(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def wbin(path, tag):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(b"stub:" + tag.encode())
    return H(path)


def wjson(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(obj, f, indent=1)


def wtext(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(text)


def build(root):
    """Construct the whole minimal valid world under <root>/R and <root>/ws; return (R, WS)."""
    R = os.path.join(root, "R")
    WS = os.path.join(root, "ws")
    dv = f"{WS}/fp2_2026-09/devices_v4chain"

    # --- devices (9 wanted) + base engine + scratch trainer -----------------------------------
    dev_train = wbin(f"{dv}/pod_f10_train_monthly_v4.py", "train_monthly")   # == shard self_sha256
    dev_refit = wbin(f"{dv}/pod_f10_refit_v4.py", "refit")                   # == refit self_sha256
    dev_np    = wbin(f"{dv}/pod_f10_np_export_v4.py", "np_export")           # == np self_sha256
    for n in ("pod_dlw_targets_raw_v2", "pod_fea_ext_clamp_v2", "pod_export_bundle_v4", "pod_legs_v4b"):
        wbin(f"{dv}/{n}.py", n)                                              # present-only devices
    wbin(f"{WS}/pod_dlw_features_ext.py", "features_ext")                    # present-only
    wbin(f"{WS}/pod_f8_build_ext.py", "f8_build_ext")                        # present-only
    base_sha = wbin(f"{WS}/pod_f10_train_ext.py", "base_engine")            # == shard base_sha256
    scratch_trainer = wbin(f"{WS}/review_scratch/pod_f10_train_monthly_v4.py", "scratch_trainer")  # merge trainer (unregistered)
    # merge_mwf_v4b.py carrying the V4_TRAINER default the trainer-split note reads
    wtext(f"{dv}/merge_mwf_v4b.py",
          'import os\nTRAINER = os.environ.get("V4_TRAINER", "%s/review_scratch/pod_f10_train_monthly_v4.py")\n' % WS)

    # --- shared data artefacts (their shas feed refit inputs + shard results) -----------------
    targets_sha = wbin(f"{R}/dlw_v4raw/data/dlw_targets.npz", "targets")
    fea82_sha   = wbin(f"{R}/dlw_v4raw/data/dlw_fea82.npz", "fea82")
    fea89_sha   = wbin(f"{R}/f8_v4/data/f8_fea89.npz", "fea89")
    legs_sha    = wbin(f"{R}/f8_v4/data/f10v2_legs.npz", "legs")
    kslow_sha   = wbin(f"{R}/shadow_bundle_L/slow_pred_pinned.npy", "king_slow_pred")
    mask_sha    = wbin(f"{WS}/fp2_2026-09/masks/member_mask_tradable_AND_live_W24H_cachegrid.npz", "mask")
    # present-only registered artefacts
    wbin(f"{WS}/data/dlnative_5m_wide829_f16_holefix2.npz", "cache")
    wbin(f"{WS}/review_scratch/holefix2_cells.npz", "hole_cells")
    wbin(f"{WS}/fp2_2026-09/raw_patch.npz", "raw_patch")
    wbin(f"{R}/dlw_hf3/data/dlw_targets.npz", "clip_targets")
    wbin(f"{R}/data/wide_fea_v4.npy", "king_fea")
    wbin(f"{R}/data/wide_fea_v4_meta.npz", "king_meta")
    wbin(f"{R}/shadow_bundle_L/slow2026.txt", "king_booster")
    wbin(f"{R}/f8_v4/gates/keep", "gate_dir")  # just to create the dir the real tree has

    inputs_sha = {"targets": targets_sha, "fea82": fea82_sha, "fea89": fea89_sha, "legs": legs_sha}

    per_seed = {}
    for sd in SEEDS:
        mwf = f"{R}/f8_v4/mwf_v4b/RAW_s{sd}"
        folds = {}
        shard_months = {k: [] for k in range(4)}
        for i, mth in enumerate(MONTHS):
            k = i % 4
            shard_months[k].append(mth)
            pt_sha = wbin(f"{mwf}/shard{k}/models/{TAG}_{mth}.pt", f"pt-{sd}-{mth}")
            pf_sha = wbin(f"{mwf}/shard{k}/preds_fold/{TAG}_{mth}.npz", f"pf-{sd}-{mth}")
            wjson(f"{mwf}/shard{k}/models/{TAG}_{mth}_config.json",
                  {"fold": int(mth), "first_test": f"{mth[:4]}-{mth[4:]}-01 00:00", "last_test": f"{mth[:4]}-{mth[4:]}-28 20:00"})
            folds[mth] = {"shard": f"shard{k}", "cutoff": f"{mth[:4]}-{mth[4:]}-01 00:00",
                          "n_train": 6000, "n_val": 900, "n_test": 180, "best_epoch": 7,
                          "best_epoch_rule": "fix7", "causality_ok": True,
                          "pt_sha256": pt_sha, "preds_fold_sha256": pf_sha}
        # one stitched .npy per seed + one preds .npy per shard (population counts)
        stitched_sha = wbin(f"{mwf}/preds/f10_V2MAIN_RAW_{TAG}_s{sd}.npy", f"stitch-{sd}")
        for k in range(4):
            wbin(f"{mwf}/shard{k}/preds/f10_V2MAIN_{TAG}_s{sd}.npy", f"shardpred-{sd}-{k}")
        # shard results (self/base/input shas + months_all + 5-fold keys per shard)
        for k in range(4):
            wjson(f"{mwf}/shard{k}/results/f10_V2MAIN_{TAG}_s{sd}.json",
                  {"self_sha256": dev_train, "base_trainer": f"{WS}/pod_f10_train_ext.py", "base_sha256": base_sha,
                   "targets_sha256": targets_sha, "fea82_sha256": fea82_sha, "fea89_sha256": fea89_sha, "legs_sha256": legs_sha,
                   "months_all": list(MONTHS), "folds": {m: {} for m in shard_months[k]}})
        # merge report
        wjson(f"{mwf}/results/merge.json",
              {"merged": {"trainer": f"{WS}/review_scratch/pod_f10_train_monthly_v4.py",
                          "trainer_sha256": scratch_trainer, "stitched_sha256": stitched_sha, "folds": folds},
               "coverage_by_month": {m: "180/180" for m in MONTHS}})
        # refit witness + .pt
        refit_pt = wbin(f"{R}/f8_v4/models/f10_live_s{sd}.pt", f"refitpt-{sd}")
        wjson(f"{R}/f8_v4/models/f10_live_s{sd}.json",
              {"inputs_sha256": dict(inputs_sha), "pt_sha256": refit_pt, "self_sha256": dev_refit,
               "trained_through_label_utc": "2025-12-16T20:00:00Z"})
        # np_export witness + .npz (pt binds the refit model; built AFTER the seal marker)
        np_npz = wbin(f"{R}/np_export/f10_np_s{sd}.npz", f"npnpz-{sd}")
        wjson(f"{R}/np_export/NP_EXPORT_s{sd}.json",
              {"PASS": True, "wrote_npz": True,
               "V1": {"spearman": 1.0, "maxabs": 1e-8, "ok": True, "criterion_rho": 0.99999, "criterion_maxabs": 1e-5},
               "self_sha256": dev_np, "pt_sha256": refit_pt, "npz_sha256": np_npz,
               "built_utc": "2026-09-18T14:02:57Z"})
        per_seed[sd] = {"refit_pt": refit_pt}

    # --- logs ---------------------------------------------------------------------------------
    wtext(f"{R}/logs/model.log",
          "[2026-09-18T11:22:05Z] MODEL_PREP_DONE king=%s legs=%s\n" % (kslow_sha[:16], legs_sha[:16]) +
          "[2026-09-18T13:04:48Z]   seed 42 shards rc=0\n[2026-09-18T13:04:48Z]   seed 42 merge rc=0 MERGE_DONE RAW 42\n" +
          "[2026-09-18T13:45:54Z]   seed 2027 shards rc=0\n[2026-09-18T13:45:54Z]   seed 2027 merge rc=0 MERGE_DONE RAW 2027\n" +
          "[2026-09-18T13:54:25Z]   refit s42 rc=0 REFIT_DONE s42\n[2026-09-18T14:02:08Z]   refit s2027 rc=0 REFIT_DONE s2027\n" +
          "[2026-09-18T14:02:08Z]   np_export s42 rc=2 wrong script\n[2026-09-18T14:02:09Z]   np_export s2027 rc=2 wrong script\n" +
          "[2026-09-18T14:02:09Z] MODEL_DONE_SEALED\n")
    end = ""
    for sd in SEEDS:
        for k in range(4):
            end += f"END[RAW s{sd} shard{k}] python {1000+sd+k} rc=0 2026-09-18T13:00:00Z wall 2000 s; folds done: 5; MWF_TRAIN_DONE: 1\n"
    wtext(f"{R}/f8_v4/logs/commands.txt", end)
    wtext(f"{R}/logs/king.log",
          "member_mask {'path': '.../member_mask_tradable_AND_live_W24H_cachegrid.npz', 'sha256': '%s', 'applied': True}\n" % mask_sha)
    wtext(f"{R}/logs/export.log",
          "fold 2024 IC +0.0575 (base +0.0548 Δ+0.0027)\nfold 2025 IC +0.0616 (base +0.0630 Δ-0.0014)\n"
          "pinned booster 2026 IC +0.0573 (orig +0.0571)\nguard band [2.270, 2.570] PASS\nBUNDLE_DONE files 8\n")
    return R, WS


def run(R, WS):
    r = subprocess.run([sys.executable, SEAL], capture_output=True, text=True,
                       env=dict(os.environ, FP3_ROOT=R, FP3_WS=WS))
    verdict = next((l for l in r.stdout.splitlines() if l.startswith("SEALED") or l.startswith("NOT SEALED")), "?")
    refs = [l.strip() for l in r.stdout.splitlines() if "[REFUSED]" in l or "[UNPROVEN]" in l]
    return r.returncode, verdict, refs, r.stdout


def load(p):
    with open(p) as f:
        return json.load(f)


def dump(p, d):
    with open(p, "w") as f:
        json.dump(d, f, indent=1)


def main():
    root = tempfile.mkdtemp(prefix="seal_tamper_")
    results = []
    try:
        R, WS = build(root)
        merge42 = f"{R}/f8_v4/mwf_v4b/RAW_s42/results/merge.json"
        refit42 = f"{R}/f8_v4/models/f10_live_s42.json"
        npx42 = f"{R}/np_export/NP_EXPORT_s42.json"
        pristine = {p: load(p) for p in (merge42, refit42, npx42)}

        def restore():
            for p, d in pristine.items():
                dump(p, d)

        rc, v, refs, out = run(R, WS)
        baseline_green = (rc == 0 and v.startswith("SEALED"))
        results.append(("BASELINE (untampered synthetic fixture)", rc, v, "GREEN" if baseline_green else "NOT GREEN — tests vacuous", []))
        if not baseline_green:
            # surface why, so a failing baseline is diagnosable rather than silent
            for l in refs[:8]:
                results.append(("  baseline refusal", "", "", "", [l]))

        def test(name, tamper, expect_item):
            restore()
            tamper()
            rc, v, refs, _ = run(R, WS)
            hit = [x for x in refs if expect_item in x]
            ok = (rc != 0) and v.startswith("NOT SEALED") and bool(hit)
            results.append((name, rc, v, "REFUSED as required" if ok else "*** DID NOT REFUSE ***", hit[:1]))

        test("A  delete fold s42:202503 registration (was: 39/40 SEALED)",
             lambda: dump(merge42, {**load(merge42), "merged": {**load(merge42)["merged"],
                       "folds": {m: fo for m, fo in load(merge42)["merged"]["folds"].items() if m != "202503"}}}),
             "fold.s42:202503")
        test("B  delete pt_sha256 of fold s42:202501 (was: tampered model passes)",
             lambda: _pop_fold_field(merge42, "202501", "pt_sha256"), "fold.s42:202501")
        test("C  delete artefact witness refit.inputs_sha256.targets (was: present-only downgrade)",
             lambda: _pop_nested(refit42, ["inputs_sha256", "targets"]), "artefact.dlw_raw_targets")
        test("D  delete device witness refit.self_sha256 (was: present-only downgrade)",
             lambda: _pop(refit42, "self_sha256"), "device.pod_f10_refit_v4.py")
        test("E  delete NP_EXPORT_s42.pt_sha256 (was: None==None bind passes)",
             lambda: _pop(npx42, "pt_sha256"), "np_export.s42")
        test("F  delete NP_EXPORT_s42.V1.criterion_rho (was: None comparison / skip)",
             lambda: _pop_nested(npx42, ["V1", "criterion_rho"]), "np_export.s42")
        restore()
    finally:
        shutil.rmtree(root, ignore_errors=True)

    print("=" * 80)
    print("HERMETIC TAMPER RED-BATTERY for seal_manifest.py")
    print(f"fixture: self-built in a temp dir (now removed); seal = {SEAL}")
    baseline_green = results[0][3] == "GREEN"
    print(f"BASELINE green (untampered synthetic fixture SEALS): {baseline_green}")
    print("=" * 80)
    for name, rc, v, status, hit in results:
        if name.startswith("  baseline refusal"):
            print(f"      {hit[0]}")
            continue
        print(f"\n### {name}\n    exit={rc}  verdict={str(v)[:34]}  => {status}")
        for h in hit:
            print(f"    {h}")
    tests = [r for r in results[1:] if not r[0].startswith("  baseline refusal")]
    ok_all = baseline_green and all(t[3].startswith("REFUSED") for t in tests)
    n_ref = sum(t[3].startswith("REFUSED") for t in tests)
    print("\n" + "=" * 80)
    print(f"RESULT: {'PASS' if ok_all else 'FAIL'} — baseline green={baseline_green}, {n_ref}/{len(tests)} tamper cases refused")
    print("=" * 80)
    sys.exit(0 if ok_all else 1)


def _pop(path, key):
    d = load(path); d.pop(key, None); dump(path, d)


def _pop_nested(path, keys):
    d = load(path); t = d
    for k in keys[:-1]:
        t = t.get(k, {})
    t.pop(keys[-1], None); dump(path, d)


def _pop_fold_field(path, month, field):
    d = load(path); d["merged"]["folds"].get(month, {}).pop(field, None); dump(path, d)


if __name__ == "__main__":
    main()
