#!/usr/bin/env python3
"""m2_make_config_hook.py — run configuration for the NAMED-DEVIATION overlay route (m2_hook.py), derived from a FROZEN certified config
(for OLD: RUN_CONFIG_main_A0_2026-09-19.json). Targets are the BASE targets, unchanged (the hedge is added by the hook, not by the file).
Changes (asserted, flattened key paths): config / status / created_utc / paths.pod_root / m2_hook (added) and, per kept run, tag / arm / role.
  mode 'overlay' : the scaled runs (main + three cost cells), arm 'OBJB_<A>' → 'OBJB_<A>M2H', table = the formula hedge table
  mode 'control' : the scaled MAIN run only, arm → 'OBJB_<A>M2H0', table = zeros (must reproduce the certified base paths bitwise)
usage: python m2_make_config_hook.py <base_config> <mode> <hook_device> <table_npz> <out_config> <diff_receipt> <pod_root>
"""
import json, sys, time, hashlib, copy


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


def flat(o, p=""):
    out = {}
    if isinstance(o, dict):
        for k, v in o.items(): out.update(flat(v, f"{p}.{k}" if p else k))
    elif isinstance(o, list):
        for i, v in enumerate(o): out.update(flat(v, f"{p}[{i}]"))
    else:
        out[p] = o
    return out


base_p, mode, hook_p, table_p, out_p, diff_p, pod_root = sys.argv[1:8]
assert mode in ("overlay", "control")
sfx = "M2H" if mode == "overlay" else "M2H0"
B = json.load(open(base_p)); C = copy.deepcopy(B)
C["config"] = B["config"] + f"__{sfx}_btc_overlay_hook_2026-09-23"
C["status"] = ("FROZEN before any M2 number — NAMED DEVIATION route (executor-level overlay, m2_hook.py) of prereg "
               "docs/PREREG_old_vs_new_models_same_engine_2026-09-23.md Stage 2 (8530d2b7f / 1217d786)")
C["created_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
C["paths"]["pod_root"] = pod_root
kept, dropped = [], []
for r in B["runs"]:
    if r.get("book") != "scaled" or (mode == "control" and r.get("cost_cell")):
        dropped.append(r["tag"]); continue
    r2 = copy.deepcopy(r); a0 = r["arm"]
    r2["arm"] = a0 + sfx; r2["tag"] = r["tag"].replace(a0 + "|", a0 + sfx + "|", 1)
    r2["role"] = ("M2 overlay via executor hook: " if mode == "overlay" else "zero-hedge hook control: ") + r["role"]
    kept.append(r2)
C["runs"] = kept
arm = kept[0]["arm"]
C["m2_hook"] = {"device": hook_p, "device_sha256": sha(hook_p), "mode": mode, "tables": {arm: {"npz": table_p, "sha256": sha(table_p)}},
                "prereg": {"path": "docs/PREREG_old_vs_new_models_same_engine_2026-09-23.md", "commit": "8530d2b7f",
                           "sha256": "1217d786b29cf8bcb37f4aa86f2e9862bb278f7c1a91cc9ac58ed9376b9a31b4"},
                "base_config": {"path": base_p, "sha256": sha(base_p)}, "dropped_runs": dropped}
json.dump(C, open(out_p, "w"), indent=1)
FB, FC = flat(B), flat(C)
non_run_same = all(FB[k] == FC[k] for k in FB if not k.startswith(("runs[", "config", "status", "created_utc", "paths.pod_root")))
bmap = {r["tag"]: r for r in B["runs"]}; run_check = []
for r2 in C["runs"]:
    r0 = bmap[r2["tag"].replace(sfx + "|", "|", 1)]; f0, f2 = flat(r0), flat(r2)
    d = sorted(k for k in set(f0) | set(f2) if f0.get(k, "<absent>") != f2.get(k, "<absent>"))
    run_check.append({"tag": r2["tag"], "differing_keys": d, "ok": set(d) <= {"tag", "arm", "role"}})
verdict = "PASS" if non_run_same and all(x["ok"] for x in run_check) else "RED"
json.dump({"device": "m2_make_config_hook.py", "self_sha256": sha(sys.argv[0]), "mode": mode, "base_config": {"path": base_p, "sha256": sha(base_p)},
           "config": {"path": out_p, "sha256": sha(out_p)}, "per_run": run_check, "dropped_runs": dropped,
           "every_non_run_key_equal_except_labels_and_pod_root": non_run_same, "added_top_level": ["m2_hook"], "VERDICT": verdict}, open(diff_p, "w"), indent=1)
print("M2H_CONFIG", mode, verdict, out_p, sha(out_p))
sys.exit(0 if verdict == "PASS" else 1)
