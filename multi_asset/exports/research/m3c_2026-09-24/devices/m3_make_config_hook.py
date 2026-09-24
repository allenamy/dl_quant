#!/usr/bin/env python3
"""m3_make_config_hook.py — ★★ M3c copy (AMENDMENT_3 §2-1, 80c6c3e4b): labels M3CH / M3CH0, amendments 2 + 3 pinned, and the budget
m3_hook.max_combined_leverage = 2.5 (AMENDMENT_2 §1, user's ruling) written into the config (the hook refuses a config without it). Base
config = news2's RUN_CONFIG_NEWS2_s{42,2027}X_2026-09-23.json (the engine run of the NC targets over 2022-06-30 → 2026-09-18T20Z).
M3b text: ★ M3b copy (docs/AMENDMENT_1_m3_beta_overlay_2026-09-23.md, 912788743): labels M3BH / M3BH0, output root, the
amendment pinned in the m3_hook block; nothing else differs from the M3 config maker (diff receipts/M3B_MAKE_CONFIG_vs_M3.diff).
M3 text: run configuration for M3 (m3_hook.py), derived from a FROZEN base config. DERIVED FROM m2_make_config_hook.py
(diff: receipts/M3_MAKE_CONFIG_vs_M2.diff). Base configs (the ones Stage 1 read the two bases from, both covering 2022-06-30T00Z →
2026-09-18T20Z, 9,252 anchors):
  OLD     = the certified /workspace/baseline_tables_2026-09-19/RUN_CONFIG_main_A0ext_2026-09-20.json (Stage 1's OLD extension run
            OBJB_A0X; bitwise equal to OBJB_A0 on the 9,139 shared anchors)
  NEW_s42 = /workspace/old_vs_new_2026-09-23/RUN_CONFIG_OVN_NEW_s42X_2026-09-23.json (Stage 1; bitwise equal to OVN_NEW_s42 on shared anchors)
Targets are the BASE targets, unchanged (the hedge is added by the hook, not by the file).
Changes (asserted, flattened key paths): config / status / created_utc / paths.pod_root / m3_hook (added) and, per kept run, tag / arm / role.
  Only the scaled MAIN run is kept (no cost cells, no lit reading: the prereg reads R-main only).
  mode 'overlay' : tag '<T>|…' → '<T>M3H|…', arm '<A>' → '<A>M3H', m3_hook.arms = {'<T>M3H': 'overlay'}   (keyed by the TAG prefix <T>,
                   which is what the hook reads; the certified A0ext run has arm 'OBJB_A0' but tag 'OBJB_A0X|…')
  mode 'control' : '<T>M3H0' / '<A>M3H0', m3_hook.arms = {'<T>M3H0': 'control'} (computes and records, never touches the target;
                   must reproduce the base paths bitwise)
usage: python m3_make_config_hook.py <base_config> <mode> <hook_device> <beta_npz> <prereg_md> <amendment1_md> <amendment2_md> <amendment3_md>
         <out_config> <diff_receipt> <pod_root>
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


base_p, mode, hook_p, beta_p, prereg_p, amend_p, amend2_p, amend3_p, out_p, diff_p, pod_root = sys.argv[1:12]
MAX_LEV = 2.5                                                       # AMENDMENT_2 §1 (user: 「按推荐来」 ⇒ 2.5), AMENDMENT_3 §2-1
assert mode in ("overlay", "control")
sfx = "M3CH" if mode == "overlay" else "M3CH0"
B = json.load(open(base_p)); C = copy.deepcopy(B)
C["config"] = B["config"] + f"__{sfx}_btc_overlay_M3c_budget2.5_2026-09-24"
C["status"] = ("FROZEN before any M3c number — M3c = M3b hook + combined-leverage budget 2.5 x NAV on the NC s42 targets, "
               "docs/AMENDMENT_3_m3_beta_overlay_2026-09-24.md §2-1 (80c6c3e4b) / AMENDMENT_2 §3-2 (4530892bc) of prereg "
               "docs/PREREG_m3_beta_overlay_executed_book_2026-09-23.md (24c3f803f)")
C["created_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
C["paths"]["pod_root"] = pod_root
kept, dropped = [], []
for r in B["runs"]:
    if r.get("book") != "scaled" or r.get("cost_cell"):
        dropped.append(r["tag"]); continue
    r2 = copy.deepcopy(r); a0 = r["arm"]; t0, rest = r["tag"].split("|", 1)
    r2["arm"] = a0 + sfx; r2["tag"] = t0 + sfx + "|" + rest          # the tag PREFIX is what the hook keys on (A0ext: arm 'OBJB_A0', tag 'OBJB_A0X|…')
    r2["role"] = ("M3c overlay (M3b + budget 2.5 x NAV) via executor hook: " if mode == "overlay"
                  else "M3c zero-hedge hook control: ") + r["role"]
    kept.append(r2)
assert len(kept) == 1, [r["tag"] for r in kept]
C["runs"] = kept
arm = kept[0]["tag"].split("|")[0]                                     # m3_hook.arms is keyed by the run TAG's prefix (m3_hook.py reads tag.split('|')[0])
C["m3_hook"] = {"device": hook_p, "device_sha256": sha(hook_p), "mode": mode, "beta": {"npz": beta_p, "sha256": sha(beta_p)}, "arms": {arm: mode},
                "prereg": {"path": "docs/PREREG_m3_beta_overlay_executed_book_2026-09-23.md", "commit": "24c3f803f", "sha256": sha(prereg_p)},
                "amendment": {"path": "docs/AMENDMENT_1_m3_beta_overlay_2026-09-23.md", "commit": "912788743", "sha256": sha(amend_p)},
                "amendment_2": {"path": "docs/AMENDMENT_2_m3_beta_overlay_2026-09-23.md", "commit": "4530892bc", "sha256": sha(amend2_p)},
                "amendment_3": {"path": "docs/AMENDMENT_3_m3_beta_overlay_2026-09-24.md", "commit": "80c6c3e4b", "sha256": sha(amend3_p)},
                "variant": "M3c", "max_combined_leverage": MAX_LEV,
                "derived_from": "m2_make_config_hook.py (M2 route H)", "base_config": {"path": base_p, "sha256": sha(base_p)}, "dropped_runs": dropped}
json.dump(C, open(out_p, "w"), indent=1)
FB, FC = flat(B), flat(C)
non_run_same = all(FB[k] == FC[k] for k in FB if not k.startswith(("runs[", "config", "status", "created_utc", "paths.pod_root")))
extra_top = sorted(set(C) - set(B))
bmap = {r["tag"]: r for r in B["runs"]}; run_check = []
for r2 in C["runs"]:
    r0 = bmap[r2["tag"].replace(sfx + "|", "|", 1)]; f0, f2 = flat(r0), flat(r2)      # the tag, arm and role MUST all change (else the hook is inert)
    d = sorted(k for k in set(f0) | set(f2) if f0.get(k, "<absent>") != f2.get(k, "<absent>"))
    run_check.append({"tag": r2["tag"], "differing_keys": d, "ok": set(d) == {"tag", "arm", "role"} and r2["tag"].split("|")[0] in C["m3_hook"]["arms"]
                      and r2["tag"] != r0["tag"]})
verdict = "PASS" if non_run_same and extra_top == ["m3_hook"] and all(x["ok"] for x in run_check) else "RED"
json.dump({"device": "m3_make_config_hook.py", "self_sha256": sha(sys.argv[0]), "mode": mode, "base_config": {"path": base_p, "sha256": sha(base_p)},
           "config": {"path": out_p, "sha256": sha(out_p)}, "per_run": run_check, "dropped_runs": dropped,
           "every_non_run_key_equal_except_labels_and_pod_root": non_run_same, "added_top_level": extra_top, "VERDICT": verdict}, open(diff_p, "w"), indent=1)
print("M3H_CONFIG", mode, verdict, out_p, sha(out_p))
sys.exit(0 if verdict == "PASS" else 1)
