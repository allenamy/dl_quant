#!/usr/bin/env python3
"""m2_make_config.py — derives the M2 run configuration from a FROZEN certified run configuration (for OLD: RUN_CONFIG_main_A0_2026-09-19.json,
sha 7b6dca2c…) and writes a DIFF receipt that must show ONLY target paths / shas, run tags and labels, and the output root.

Changes (nothing else; asserted on the flattened key paths of the two JSONs):
  config / status / created_utc / m2 (added block)                       labels
  paths.pod_root                                                         output root (pod2 /workspace is at its disk quota on 2026-09-23 06:04Z;
                                                                         outputs go to /dev/shm/<root>, copied out afterwards)
  runs: the base config's scaled runs (main + the three cost cells) are kept in order with
        runs[*].tag  'OBJB_<A>|…' → 'OBJB_<A>M2|…', runs[*].arm 'OBJB_<A>' → 'OBJB_<A>M2' (the driver keys books by (arm, book))
        runs[*].targets.sources[*].{npz, npz_sha256, receipt, receipt_sha256} → the M2 target file and its receipt
        runs[*].role → prefixed 'M2 overlay: '
  the 'lit' run is not carried (Stage 2 uses the main setting and the cost cells) — listed in the receipt as a dropped run, not a changed one
  with --with-base-control: the base config's scaled main run is appended UNCHANGED (tag, arm, targets identical) as a reproduction control
Every simulator setting (window, nav0, seeds, gross, chase, decision / stop offsets, per-name stop, §4-2 rule, tradability, UA policy,
calibration, pins, launch limits) is copied byte-for-byte in value.
usage: python m2_make_config.py <base_config> <m2_targets_npz> <m2_npz_sha> <m2_receipt> <m2_receipt_sha> <out_config> <diff_receipt> <pod_root> [--with-base-control]
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


base_p, npz, npz_sha, rc, rc_sha, out_p, diff_p, pod_root = sys.argv[1:9]
with_ctrl = "--with-base-control" in sys.argv
assert sha(npz) == npz_sha and sha(rc) == rc_sha, "M2 target / receipt sha mismatch"
B = json.load(open(base_p)); C = copy.deepcopy(B)
C["config"] = B["config"] + "__M2_btc_overlay_2026-09-23"
C["status"] = "FROZEN before any M2 number (prereg docs/PREREG_old_vs_new_models_same_engine_2026-09-23.md Stage 2, 8530d2b7f / 1217d786)"
C["created_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
C["paths"]["pod_root"] = pod_root
kept, dropped = [], []
for r in B["runs"]:
    if r.get("book") != "scaled":
        dropped.append(r["tag"]); continue
    r2 = copy.deepcopy(r)
    a0 = r["arm"]; r2["arm"] = a0 + "M2"; r2["tag"] = r["tag"].replace(a0 + "|", a0 + "M2|", 1)
    assert len(r2["targets"]["sources"]) == 1, "one source expected"
    r2["targets"]["sources"][0].update(npz=npz, npz_sha256=npz_sha, receipt=rc, receipt_sha256=rc_sha)
    r2["role"] = "M2 overlay: " + r["role"]
    kept.append(r2)
C["runs"] = kept + ([copy.deepcopy(next(r for r in B["runs"] if r.get("book") == "scaled" and not r.get("cost_cell")))] if with_ctrl else [])
C["m2"] = {"prereg": {"path": "docs/PREREG_old_vs_new_models_same_engine_2026-09-23.md", "commit": "8530d2b7f", "sha256": "1217d786b29cf8bcb37f4aa86f2e9862bb278f7c1a91cc9ac58ed9376b9a31b4"},
           "base_config": {"path": base_p, "sha256": sha(base_p)}, "targets": {"npz": npz, "npz_sha256": npz_sha, "receipt": rc, "receipt_sha256": rc_sha},
           "dropped_runs": dropped, "base_control_appended": with_ctrl}
json.dump(C, open(out_p, "w"), indent=1)
# ---- diff receipt ----
FB, FC = flat(B), flat(C)
allowed_prefix = ("config", "status", "created_utc", "paths.pod_root", "m2.")
diffs = []
for k in sorted(set(FB) | set(FC)):
    if FB.get(k, "<absent>") != FC.get(k, "<absent>"): diffs.append((k, FB.get(k, "<absent>"), FC.get(k, "<absent>")))
bad = []
for k, a, b in diffs:
    if k.startswith(allowed_prefix) or k in ("config", "status", "created_utc"): continue
    if k.startswith("runs["):
        tail = k.split("]", 1)[1]
        if tail in (".tag", ".arm", ".role") or tail.startswith(".targets.sources[0].") and tail.split(".")[-1] in ("npz", "npz_sha256", "receipt", "receipt_sha256"): continue
        # runs removed / appended shift indices: compare run-by-run below instead
        continue
    bad.append(k)
# run-by-run: every kept run equals its base run except the allowed fields
run_check = []
bmap = {r["tag"]: r for r in B["runs"]}
for r2 in C["runs"]:
    src_tag = r2["tag"].replace("M2|", "|", 1)
    r0 = bmap[src_tag]; f0, f2 = flat(r0), flat(r2)
    d = sorted(k for k in set(f0) | set(f2) if f0.get(k, "<absent>") != f2.get(k, "<absent>"))
    ok = all(k in ("tag", "arm", "role") or (k.startswith("targets.sources[0].") and k.split(".")[-1] in ("npz", "npz_sha256", "receipt", "receipt_sha256")) for k in d)
    run_check.append({"tag": r2["tag"], "from": src_tag, "differing_keys": d, "ok": ok})
non_run_same = all(FB[k] == FC[k] for k in FB if not k.startswith(("runs[", "config", "status", "created_utc", "paths.pod_root")))
verdict = "PASS" if (not bad and all(x["ok"] for x in run_check) and non_run_same) else "RED"
json.dump({"device": "m2_make_config.py", "self_sha256": sha(sys.argv[0]), "base_config": {"path": base_p, "sha256": sha(base_p)},
           "m2_config": {"path": out_p, "sha256": sha(out_p)}, "top_level_diffs_outside_runs": [d for d in diffs if not d[0].startswith("runs[")],
           "dropped_runs": dropped, "per_run": run_check, "every_non_run_key_equal_except_labels_and_pod_root": non_run_same, "bad_keys": bad, "VERDICT": verdict},
          open(diff_p, "w"), indent=1, default=str)
print("M2_CONFIG", verdict, out_p, sha(out_p), "diff", sha(diff_p))
sys.exit(0 if verdict == "PASS" else 1)
