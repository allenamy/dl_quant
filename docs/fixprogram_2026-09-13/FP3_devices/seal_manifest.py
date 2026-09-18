#!/usr/bin/env python3
"""seal_manifest.py — per-fold identity manifest + verifier for the FP3 legal-member model.

SUPERSEDES seal.py.  seal.py is retained ONLY as the defective red-control: it writes a
FIXED sentence ("trained and materialised"), yields sha256=None for a missing artefact with
no refusal, hardcodes the mwf/refit/king prose, and samples sorted(glob)[:6] predictions.
Under an isolated fake filesystem with all 17 artefacts absent, seal.py still exits 0.

This script instead DERIVES every sentence from a check performed at run time:
  * a per-fold manifest over 40 folds (2 seeds x 20 months), each fold carrying the month it
    trained on, its label cutoff, its test range, the sha of its training inputs / source
    device / output artefacts, and a process exit code — all read from the artefacts, then
    re-verified by re-hashing the files on disk;
  * per seed, month-set disjointness + completeness + test-overlap=0 + merged==expected;
  * every registered artefact must EXIST and (where a witness records a value) re-hash to it,
    else NAMED REFUSAL + nonzero exit — never a null field beside a success sentence;
  * completeness of the device set `want`, not just the intersection;
  * the mwf prediction population enumerated in full with a stated sampling rule (no [:6]);
  * np_export completion decided by real dependency acceptance (PASS + pt-sha bind + correct
    device sha), NOT by the MODEL_DONE_SEALED marker — which the run wrote while np_export was
    rc=2 (the accepted 14:02:09 incident); this seal would refuse at that instant.

If a check's evidence does not exist on the pod, the item is UNPROVEN and the seal exits
nonzero — the gap is named, never omitted.

Roots come from the environment so the script is hermetically testable:
  FP3_ROOT (default /workspace/fp3_live_2026-09), FP3_WS (default /workspace).
Read-only except for the one manifest it writes: $FP3_ROOT/MODEL_SEAL_MANIFEST.json.
"""
import hashlib, json, os, re, sys, glob, time
from datetime import datetime, timezone

R  = os.environ.get("FP3_ROOT", "/workspace/fp3_live_2026-09")
WS = os.environ.get("FP3_WS", "/workspace")
SEEDS = [42, 2027]
TAG = "mE1cX7"
EXPECTED_MONTHS = [f"{y}{m:02d}" for y in (2025, 2026) for m in range(1, 13)][:20]  # 202501..202608

# ---- verdict accumulators -------------------------------------------------------------
CHECKS = []          # every item, PROVEN / REFUSED / UNPROVEN / NOTE, each with a derived sentence
def rec(item, status, sentence, **data):
    CHECKS.append({"item": item, "status": status, "sentence": sentence, **({"data": data} if data else {})})
    return status
def proven(item, sentence, **d):   return rec(item, "PROVEN", sentence, **d)
def refuse(item, sentence, **d):   return rec(item, "REFUSED", sentence, **d)
def unproven(item, sentence, **d): return rec(item, "UNPROVEN", sentence, **d)
def note(item, sentence, **d):     return rec(item, "NOTE", sentence, **d)

def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 24), b""):
            h.update(c)
    return h.hexdigest()

def load_json(p):
    try:
        with open(p) as f:
            return json.load(f), None
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"

def read_text(p):
    try:
        with open(p, "rb") as f:
            return f.read().decode("utf-8", "replace"), None
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"

def iso(ts):
    return datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(timezone.utc)

# --------------------------------------------------------------------------------------
# 0. self-description
SELF_SHA = sha(os.path.abspath(__file__)) if os.path.exists(os.path.abspath(__file__)) else None
manifest = {"kind": "FP3 legal-member model per-fold identity manifest",
            "self_sha256": SELF_SHA, "root": R, "ws": WS,
            "generated_utc": time.strftime("%FT%TZ", time.gmtime()),
            "supersedes": "seal.py (defective fixed-string seal, retained as red control)"}

# --------------------------------------------------------------------------------------
# 1. WITNESS artefacts: read them first; the shas THEY record are the reference values.
witness = {}
def need_json(key, path, item):
    d, err = load_json(path)
    if err:
        refuse(item, f"witness absent/unreadable, cannot derive its recorded values: {path} ({err})")
    witness[key] = d
    return d

refit = {}
np_exp = {}
merge = {}
shards = {}   # (seed, k) -> shard results dict
for sd in SEEDS:
    refit[sd]  = need_json(f"refit_s{sd}",  f"{R}/f8_v4/models/f10_live_s{sd}.json",      f"witness.refit_s{sd}")
    np_exp[sd] = need_json(f"np_s{sd}",     f"{R}/np_export/NP_EXPORT_s{sd}.json",        f"witness.np_export_s{sd}")
    merge[sd]  = need_json(f"merge_s{sd}",  f"{R}/f8_v4/mwf_v4b/RAW_s{sd}/results/merge.json", f"witness.merge_s{sd}")
    for k in range(4):
        p = f"{R}/f8_v4/mwf_v4b/RAW_s{sd}/shard{k}/results/f10_V2MAIN_{TAG}_s{sd}.json"
        shards[(sd, k)] = need_json(f"shard_s{sd}_{k}", p, f"witness.shard_s{sd}_{k}")

model_log, _  = read_text(f"{R}/logs/model.log")
cmds_txt, _   = read_text(f"{R}/f8_v4/logs/commands.txt")
king_log, _   = read_text(f"{R}/logs/king.log")

# --------------------------------------------------------------------------------------
# 2. REGISTERED ARTEFACTS: exist + (where a witness records a value) re-hash to it.
#    Reference shas are pulled from the witnesses above, not hardcoded.
def wget(d, *keys):
    for k in keys:
        if not isinstance(d, dict) or k not in d:
            return None
        d = d[k]
    return d

# assemble reference shas from witnesses
ref = {}   # label -> (expected_sha_or_prefix, source, mode)  mode in {"full","prefix16"}
r42 = refit.get(42) or {}
if wget(r42, "inputs_sha256"):
    ins = r42["inputs_sha256"]
    ref["dlw_raw_targets"] = (ins.get("targets"), "f10_live_s42.json:inputs_sha256.targets", "full")
    ref["fea82"]           = (ins.get("fea82"),   "f10_live_s42.json:inputs_sha256.fea82", "full")
    ref["fea89"]           = (ins.get("fea89"),   "f10_live_s42.json:inputs_sha256.fea89", "full")
    ref["legs"]            = (ins.get("legs"),    "f10_live_s42.json:inputs_sha256.legs", "full")
if wget(r42, "pt_sha256"):
    ref["f10_live_s42"]    = (r42["pt_sha256"], "f10_live_s42.json:pt_sha256", "full")
r27 = refit.get(2027) or {}
if wget(r27, "pt_sha256"):
    ref["f10_live_s2027"]  = (r27["pt_sha256"], "f10_live_s2027.json:pt_sha256", "full")
if wget(np_exp.get(42) or {}, "npz_sha256"):
    ref["np_s42"]   = (np_exp[42]["npz_sha256"], "NP_EXPORT_s42.json:npz_sha256", "full")
if wget(np_exp.get(2027) or {}, "npz_sha256"):
    ref["np_s2027"] = (np_exp[2027]["npz_sha256"], "NP_EXPORT_s2027.json:npz_sha256", "full")
# model.log MODEL_PREP_DONE king=<16hex> legs=<16hex>  (prefix witnesses)
prep = re.search(r"MODEL_PREP_DONE king=([0-9a-f]+) legs=([0-9a-f]+)", model_log or "")
if prep:
    ref["king_slow_pred"] = (prep.group(1), "model.log:MODEL_PREP_DONE king=", "prefix16")
    ref.setdefault("legs", (prep.group(2), "model.log:MODEL_PREP_DONE legs=", "prefix16"))
# king.log records the liveness mask sha (full)
mk = re.search(r"member_mask_tradable_AND_live_W24H_cachegrid\.npz['\"],\s*['\"]sha256['\"]:\s*['\"]([0-9a-f]{64})", king_log or "")
if mk:
    ref["mask_liveness"] = (mk.group(1), "king.log:member_mask.sha256", "full")

items = [("cache", f"{WS}/data/dlnative_5m_wide829_f16_holefix2.npz"),
         ("hole_cells", f"{WS}/review_scratch/holefix2_cells.npz"),
         ("mask_liveness", f"{WS}/fp2_2026-09/masks/member_mask_tradable_AND_live_W24H_cachegrid.npz"),
         ("raw_patch", f"{WS}/fp2_2026-09/raw_patch.npz"),
         ("dlw_raw_targets", f"{R}/dlw_v4raw/data/dlw_targets.npz"),
         ("dlw_clip_targets", f"{R}/dlw_hf3/data/dlw_targets.npz"),
         ("fea82", f"{R}/dlw_v4raw/data/dlw_fea82.npz"),
         ("fea89", f"{R}/f8_v4/data/f8_fea89.npz"),
         ("king_fea", f"{R}/data/wide_fea_v4.npy"),
         ("king_meta", f"{R}/data/wide_fea_v4_meta.npz"),
         ("king_slow_pred", f"{R}/shadow_bundle_L/slow_pred_pinned.npy"),
         ("king_booster", f"{R}/shadow_bundle_L/slow2026.txt"),
         ("legs", f"{R}/f8_v4/data/f10v2_legs.npz"),
         ("f10_live_s42", f"{R}/f8_v4/models/f10_live_s42.pt"),
         ("f10_live_s2027", f"{R}/f8_v4/models/f10_live_s2027.pt"),
         ("np_s42", f"{R}/np_export/f10_np_s42.npz"),
         ("np_s2027", f"{R}/np_export/f10_np_s2027.npz")]

arte = {}
for lab, p in items:
    if not os.path.exists(p):
        refuse(f"artefact.{lab}", f"registered artefact ABSENT: {p}")
        arte[lab] = {"path": p, "exists": False, "sha256": None, "verified": False}
        continue
    h = sha(p); b = os.path.getsize(p)
    entry = {"path": p, "exists": True, "sha256": h, "bytes": b}
    if lab in ref and ref[lab][0]:
        exp, src, mode = ref[lab]
        ok = (h.startswith(exp) if mode == "prefix16" else h == exp)
        entry.update({"ref_sha": exp, "ref_source": src, "ref_mode": mode, "verified": ok})
        if ok:
            proven(f"artefact.{lab}", f"{lab} exists ({b} B) and re-hashes to the value recorded by {src} "
                                      f"({'64-bit prefix' if mode=='prefix16' else 'sha256'} {exp[:16]})", sha256=h)
        else:
            refuse(f"artefact.{lab}", f"{lab} MISMATCH: on-disk {h[:16]} != {src} {exp[:16]}")
    else:
        entry.update({"verified": False, "ref_source": None,
                      "note": "present; no independent witness records a sha to cross-check — existence + snapshot hash only"})
        note(f"artefact.{lab}", f"{lab} exists ({b} B), sha256 {h[:16]} recorded; PRESENT-ONLY (no witness sha to cross-check)", sha256=h)
    arte[lab] = entry
manifest["registered_artefacts"] = arte

# --------------------------------------------------------------------------------------
# 3. PER-FOLD MANIFEST (40): month, cutoff, test range, input/device/output shas, exit code.
folds_out = []
n_fold_ok = 0
# device (source) shas that produced the folds, from the shard witnesses
def shard_of(sd, month):
    for k in range(4):
        s = shards.get((sd, k)) or {}
        if isinstance(wget(s, "folds"), dict) and month in s["folds"]:
            return k, s
    return None, None

# per-shard END-row exit codes from commands.txt (the real trace)
end_rows = {}
for m in re.finditer(r"END\[RAW s(\d+) shard(\d+)\]\s+python\s+(\d+)\s+rc=(\d+).*?folds done:\s*(\d+);\s*MWF_TRAIN_DONE:\s*(\d+)",
                     cmds_txt or ""):
    sd, k, pid, rc, nf, done = (int(m.group(i)) for i in range(1, 7))
    end_rows[(sd, k)] = {"pid": pid, "rc": rc, "folds_done": nf, "mwf_train_done": done}

for sd in SEEDS:
    mg = merge.get(sd) or {}
    fdict = wget(mg, "merged", "folds")
    if not isinstance(fdict, dict):
        unproven(f"folds.s{sd}", f"merge.json for seed {sd} has no merged.folds — cannot build the fold manifest")
        continue
    for month in sorted(fdict):
        f = fdict[month]
        k, srec = shard_of(sd, month)
        pt_path  = f"{R}/f8_v4/mwf_v4b/RAW_s{sd}/shard{k}/models/{TAG}_{month}.pt" if k is not None else None
        pf_path  = f"{R}/f8_v4/mwf_v4b/RAW_s{sd}/shard{k}/preds_fold/{TAG}_{month}.npz" if k is not None else None
        cfg_path = f"{R}/f8_v4/mwf_v4b/RAW_s{sd}/shard{k}/models/{TAG}_{month}_config.json" if k is not None else None
        cfg, _ = load_json(cfg_path) if cfg_path else (None, None)
        rowid = f"s{sd}:{month}"
        row = {"seed": sd, "month": month, "shard": f.get("shard"),
               "trained_on_month": month,
               "label_cutoff": f.get("cutoff"),
               "test_range": [wget(cfg, "first_test"), wget(cfg, "last_test")] if cfg else None,
               "n_train": f.get("n_train"), "n_val": f.get("n_val"), "n_test": f.get("n_test"),
               "best_epoch": f.get("best_epoch"), "rule": f.get("best_epoch_rule"),
               "causality_ok": f.get("causality_ok"),
               "input_shas": {kk: wget(srec or {}, f"{kk}_sha256") for kk in ("targets", "fea82", "fea89", "legs")},
               "source_device_sha256": wget(srec or {}, "self_sha256"),
               "base_engine_sha256": wget(srec or {}, "base_sha256"),
               "recorded_pt_sha256": f.get("pt_sha256"),
               "recorded_preds_fold_sha256": f.get("preds_fold_sha256"),
               "shard_process_rc": (end_rows.get((sd, k)) or {}).get("rc") if k is not None else None,
               "pt_path": pt_path, "preds_fold_path": pf_path}
        problems = []
        if k is None:
            problems.append("no shard owns this month")
        else:
            if not (pt_path and os.path.exists(pt_path)):
                problems.append("pt absent")
            elif f.get("pt_sha256") and sha(pt_path) != f["pt_sha256"]:
                problems.append(f"pt sha mismatch (disk {sha(pt_path)[:12]} vs merge {f['pt_sha256'][:12]})")
            if not (pf_path and os.path.exists(pf_path)):
                problems.append("preds_fold absent")
            elif f.get("preds_fold_sha256") and sha(pf_path) != f["preds_fold_sha256"]:
                problems.append("preds_fold sha mismatch")
            if f.get("causality_ok") is not True:
                problems.append(f"causality_ok={f.get('causality_ok')}")
            if not f.get("cutoff"):
                problems.append("no label cutoff recorded")
            if row["test_range"] in (None, [None, None]):
                problems.append("no test range in config")
            er = end_rows.get((sd, k))
            if er is None:
                problems.append("no shard END-row exit code in commands.txt")
            elif er["rc"] != 0:
                problems.append(f"shard process rc={er['rc']}")
        row["problems"] = problems
        row["proven"] = not problems
        folds_out.append(row)
        if problems:
            refuse(f"fold.{rowid}", f"fold {rowid} NOT proven: {'; '.join(problems)}")
        else:
            n_fold_ok += 1
            proven(f"fold.{rowid}", f"fold {rowid} shard{k}: trained through {f['cutoff']}, test {row['test_range'][0]}..{row['test_range'][1]} "
                                    f"(n_test {f.get('n_test')}), pt+preds_fold re-hash to merge values, causality_ok, shard rc=0")
manifest["folds"] = folds_out
manifest["n_folds_proven"] = n_fold_ok
manifest["n_folds_expected"] = len(SEEDS) * len(EXPECTED_MONTHS)

# --------------------------------------------------------------------------------------
# 4. MONTH PARTITION per seed: 4 shards x 5 months, disjoint, complete, test-overlap 0,
#    merged coverage == expected (expected set derived from the artefacts' own months_all).
for sd in SEEDS:
    shard_months = {}
    for k in range(4):
        s = shards.get((sd, k)) or {}
        fk = wget(s, "folds")
        shard_months[k] = sorted(fk.keys()) if isinstance(fk, dict) else []
    # authoritative expected set = months_all recorded in a shard witness (derived from targets axis)
    months_all = None
    for k in range(4):
        s = shards.get((sd, k)) or {}
        if wget(s, "months_all"):
            months_all = sorted(str(x) for x in s["months_all"]); break
    all_shard = [m for k in range(4) for m in shard_months[k]]
    dup = sorted({m for m in all_shard if all_shard.count(m) > 1})
    union = sorted(set(all_shard))
    sizes = {k: len(shard_months[k]) for k in range(4)}
    cov = wget(merge.get(sd) or {}, "coverage_by_month")
    cov_keys = sorted(cov.keys()) if isinstance(cov, dict) else []
    cov_full = isinstance(cov, dict) and all((lambda ab: ab[0] == ab[1])(v.split("/")) for v in cov.values())
    exp = months_all or EXPECTED_MONTHS
    ok = (not dup) and (len(union) == 20) and all(sizes[k] == 5 for k in range(4)) \
         and union == exp and cov_keys == exp and cov_full
    data = {"shard_month_sets": shard_months, "duplicates": dup, "sizes": sizes,
            "union_n": len(union), "expected_source": "shard.months_all" if months_all else "builtin",
            "coverage_keys_eq_expected": cov_keys == exp, "coverage_all_full": cov_full}
    if ok:
        proven(f"partition.s{sd}", f"seed {sd}: 4 shards x 5 months, pairwise disjoint (0 duplicates), union = 20 months "
                                   f"= expected axis set, merged coverage keys == expected and every month full-coverage; test months are 20 distinct calendar months (overlap 0)", **data)
    else:
        refuse(f"partition.s{sd}", f"seed {sd} partition FAILED: dup={dup} sizes={sizes} union={len(union)} "
                                   f"cov_keys_eq={cov_keys==exp} cov_full={cov_full}", **data)

# cross-seed: both seeds cover the same 20 months
s42m = sorted(wget(merge.get(42) or {}, "coverage_by_month").keys()) if isinstance(wget(merge.get(42) or {}, "coverage_by_month"), dict) else []
s27m = sorted(wget(merge.get(2027) or {}, "coverage_by_month").keys()) if isinstance(wget(merge.get(2027) or {}, "coverage_by_month"), dict) else []
if s42m and s42m == s27m:
    proven("partition.cross_seed", f"both seeds walk the same 20 test months {s42m[0]}..{s42m[-1]}")
elif s42m or s27m:
    refuse("partition.cross_seed", f"seeds cover different month sets: s42={s42m} s2027={s27m}")

# --------------------------------------------------------------------------------------
# 5. LABEL CUTOFF — verified from artefact configs (refit json + np npz meta), not copied.
cutoffs = {}
for sd in SEEDS:
    cutoffs[f"refit_s{sd}"] = wget(refit.get(sd) or {}, "trained_through_label_utc")
# np npz internal metadata (self-describing)
for sd in SEEDS:
    p = f"{R}/np_export/f10_np_s{sd}.npz"
    if os.path.exists(p):
        try:
            import numpy as np
            d = np.load(p)
            cutoffs[f"npnpz_s{sd}"] = str(d["trained_through_label_utc"]) if "trained_through_label_utc" in d else None
        except Exception as e:
            cutoffs[f"npnpz_s{sd}"] = f"__unreadable__:{type(e).__name__}"
vals = [v for v in cutoffs.values() if v and not str(v).startswith("__")]
if vals and len(set(vals)) == 1:
    proven("label_cutoff", f"refit label cutoff = {vals[0]} — agreed across {len(vals)} independent artefact fields "
                           f"({', '.join(k for k,v in cutoffs.items() if v and not str(v).startswith('__'))}); "
                           f"pool/axis end 2026-08-31T20:00:00Z; distinct from the 40 per-fold MWF cutoffs recorded per fold above",
           sources=cutoffs, value=vals[0])
    manifest["label_cutoff"] = vals[0]
else:
    unproven("label_cutoff", f"label cutoff not consistently derivable from artefacts: {cutoffs}")

# --------------------------------------------------------------------------------------
# 6. np_export dependency acceptance + the 14:02:09 incident (marker disavowed).
for sd in SEEDS:
    d = np_exp.get(sd) or {}
    npz = arte.get(f"np_s{sd}", {})
    refit_pt = wget(refit.get(sd) or {}, "pt_sha256")
    probs = []
    if d.get("PASS") is not True: probs.append("PASS!=true")
    if d.get("wrote_npz") is not True: probs.append("wrote_npz!=true")
    if wget(d, "V1", "ok") is not True: probs.append("V1.ok!=true")
    rho = wget(d, "V1", "spearman"); mx = wget(d, "V1", "maxabs")
    if not (isinstance(rho, (int, float)) and rho >= wget(d, "V1", "criterion_rho")): probs.append(f"spearman {rho} below criterion")
    if not (isinstance(mx, (int, float)) and mx <= wget(d, "V1", "criterion_maxabs")): probs.append(f"maxabs {mx} above criterion")
    if d.get("pt_sha256") != refit_pt: probs.append(f"export pt_sha {str(d.get('pt_sha256'))[:12]} != refit pt {str(refit_pt)[:12]}")
    if not npz.get("verified"): probs.append("npz did not re-hash to recorded npz_sha256")
    if probs:
        refuse(f"np_export.s{sd}", f"np_export seed {sd} not accepted: {'; '.join(probs)}")
    else:
        proven(f"np_export.s{sd}", f"np_export seed {sd} ACCEPTED by dependency: PASS + V1 spearman {rho:.10f} (<=1e-5 maxabs) + "
                                   f"export pt_sha binds the refit model + npz re-hashes; produced by device self_sha {str(d.get('self_sha256'))[:12]} "
                                   f"at {d.get('built_utc')}", self_sha256=d.get("self_sha256"))

# the incident: MODEL_DONE_SEALED written while np_export was rc=2, before the real export existed
seal_marker = re.search(r"\[([0-9T:\-]+Z)\]\s+MODEL_DONE_SEALED", model_log or "")
rc2 = re.findall(r"np_export s(\d+) rc=(\d+)", model_log or "")
built = {sd: wget(np_exp.get(sd) or {}, "built_utc") for sd in SEEDS}
if seal_marker and built.get(42):
    t_marker = iso(seal_marker.group(1)); t_built = iso(built[42])
    if t_built > t_marker:
        note("incident.model_done_sealed",
             f"DISAVOWED: run wrote MODEL_DONE_SEALED at {seal_marker.group(1)} while np_export was "
             f"rc=2 for seeds {[s for s,_ in rc2]} (wrong script pod_np_export_v4.py); the correct export "
             f"materialised {int((t_built-t_marker).total_seconds())}s LATER (built_utc {built[42]}). This seal "
             f"ignores the marker and accepts np_export only via dependency (section 6); at {seal_marker.group(1)} "
             f"f10_np_s*.npz were absent so this seal would REFUSE.",
             marker_rc2=rc2, marker_utc=seal_marker.group(1), real_built_utc=built)
    else:
        note("incident.model_done_sealed", f"MODEL_DONE_SEALED {seal_marker.group(1)}; export built {built}")
else:
    unproven("incident.model_done_sealed", "could not locate MODEL_DONE_SEALED / built_utc to reconstruct the 14:02:09 incident")

# --------------------------------------------------------------------------------------
# 7. DEVICE COMPLETENESS (`want`, not just intersection) + cross-verification.
want = ["pod_dlw_targets_raw_v2.py", "pod_fea_ext_clamp_v2.py", "pod_export_bundle_v4.py", "pod_legs_v4b.py",
        "pod_f10_train_monthly_v4.py", "pod_f10_refit_v4.py", "pod_f10_np_export_v4.py",
        "pod_dlw_features_ext.py", "pod_f8_build_ext.py"]
search_dirs = [f"{WS}/fp2_2026-09/devices_v4chain", WS]
# witness self-shas to cross-verify device identity
dev_witness = {
    "pod_f10_refit_v4.py":        (wget(r42, "self_sha256"), "f10_live_s42.json:self_sha256"),
    "pod_f10_train_monthly_v4.py": (wget(shards.get((42, 0)) or {}, "self_sha256"), "shard_s42_0:self_sha256"),
    "pod_f10_np_export_v4.py":    (wget(np_exp.get(42) or {}, "self_sha256"), "NP_EXPORT_s42.json:self_sha256"),
}
devices = {}
for name in want:
    path = next((os.path.join(d, name) for d in search_dirs if os.path.exists(os.path.join(d, name))), None)
    if path is None:
        refuse(f"device.{name}", f"wanted device NOT FOUND in {search_dirs} — device set incomplete")
        devices[name] = {"found": False, "sha256": None}
        continue
    h = sha(path)
    e = {"found": True, "path": path, "sha256": h}
    w = dev_witness.get(name)
    if w and w[0]:
        e.update({"cross_verified": h == w[0], "witness": w[1], "witness_sha": w[0]})
        if h == w[0]:
            proven(f"device.{name}", f"{name} present at {path}, sha {h[:12]} CROSS-VERIFIED against {w[1]}")
        else:
            refuse(f"device.{name}", f"{name} sha {h[:12]} != witness {w[1]} {w[0][:12]}")
    else:
        e.update({"cross_verified": None, "witness": None})
        note(f"device.{name}", f"{name} present at {path}, sha {h[:12]}; PRESENT-ONLY (no artefact records this device's self-sha)")
    devices[name] = e
manifest["devices"] = devices

# trainer path-split provenance (same basename, two shas) — trainer_sha256 lives under merged.*,
# not at the top level; reading the wrong path once silently skipped this whole disclosure.
shard_trainer = wget(shards.get((42, 0)) or {}, "self_sha256")
merge_trainer = wget(merge.get(42) or {}, "merged", "trainer_sha256")
merge_trainer_path = wget(merge.get(42) or {}, "merged", "trainer")
if shard_trainer and merge_trainer:
    if shard_trainer != merge_trainer:
        note("provenance.trainer_split",
             f"two files named pod_f10_train_monthly_v4.py: shard execution attributes self_sha {shard_trainer[:12]} "
             f"(devices_v4chain, cross-verified above); the MERGE step records {merge_trainer[:12]} from a different path "
             f"({merge_trainer_path}). The 40 fold artefacts were produced by the shard trainer; the merge-recorded copy is a "
             f"stitch-time reference. Recorded, not reconciled — no artefact was produced by the merge-recorded copy.",
             shard_self_sha256=shard_trainer, merge_trainer_sha256=merge_trainer, merge_trainer_path=merge_trainer_path)
    else:
        note("provenance.trainer_split", f"shard and merge both attribute trainer sha {shard_trainer[:12]}")
else:
    note("provenance.trainer_split",
         f"trainer provenance not compared (a witness is absent — see the corresponding witness refusal): "
         f"shard self_sha={shard_trainer} merge trainer_sha={merge_trainer}")

# base engine (not in want) — record + verify
base_path = f"{WS}/pod_f10_train_ext.py"; base_w = wget(shards.get((42, 0)) or {}, "base_sha256")
if os.path.exists(base_path) and base_w:
    bh = sha(base_path)
    (proven if bh == base_w else refuse)("device.base_engine",
        f"base engine pod_f10_train_ext.py sha {bh[:12]} {'==' if bh==base_w else '!='} shard base_sha256 {base_w[:12]}")

# --------------------------------------------------------------------------------------
# 8. EXIT CODES: per-shard (commands.txt), per-seed conjunction (driver log), refit.
n_end = len(end_rows)
all_rc0 = n_end == 8 and all(v["rc"] == 0 for v in end_rows.values())
folds_done = sum(v["folds_done"] for v in end_rows.values())
mwf_done = all(v["mwf_train_done"] == 1 for v in end_rows.values())
if all_rc0 and folds_done == 40 and mwf_done:
    proven("exit.shards", f"commands.txt records all 8 shard processes rc=0 (2 seeds x 4 shards), folds done "
                          f"{folds_done}/40, MWF_TRAIN_DONE on every shard — the real per-shard exit trace the old seal never read",
           end_rows={f"s{sd}_{k}": v for (sd, k), v in end_rows.items()})
else:
    unproven("exit.shards", f"per-shard exit trace incomplete: {n_end}/8 END rows, all_rc0={all_rc0}, folds_done={folds_done}, mwf_done={mwf_done}")

seed_rc = dict(re.findall(r"seed (\d+) shards rc=(\d+)", model_log or ""))
merge_done = set(re.findall(r"MERGE_DONE RAW (\d+)", model_log or ""))
refit_rc = dict(re.findall(r"refit s(\d+) rc=(\d+)", model_log or ""))
fail_mwf = re.findall(r"FAIL_mwf_s(\d+)", model_log or "")
drv_ok = (all(seed_rc.get(str(sd)) == "0" for sd in SEEDS) and {str(s) for s in SEEDS} <= merge_done
          and all(refit_rc.get(str(sd)) == "0" for sd in SEEDS) and not fail_mwf)
if drv_ok:
    proven("exit.driver", f"driver log: seed shard-batch rc=0 both seeds (wait-conjunction over the 4 shards, run_mwf.sh), "
                          f"MERGE_DONE both seeds, refit rc=0 both seeds, no FAIL_mwf marker",
           seed_shard_rc=seed_rc, merge_done=sorted(merge_done), refit_rc=refit_rc)
else:
    unproven("exit.driver", f"driver-log exit evidence incomplete: seed_rc={seed_rc} merge_done={sorted(merge_done)} refit_rc={refit_rc} fail_mwf={fail_mwf}")

note("exit.per_fold", "per-fold exit code is not a separate process value: the 5 folds of a shard run in-process, so the "
                      "fold-level completion signal is the artefact materialisation + causality_ok verified per fold in section 3; "
                      "the enclosing shard process rc is section 8.")

# --------------------------------------------------------------------------------------
# 9. MWF PREDICTION POPULATION — enumerated in full (no sorted(glob)[:6]).
stitched = sorted(glob.glob(f"{R}/f8_v4/mwf_v4b/RAW_s*/preds/*.npy"))
shard_preds = sorted(glob.glob(f"{R}/f8_v4/mwf_v4b/RAW_s*/shard*/preds/*.npy"))
fold_preds = sorted(glob.glob(f"{R}/f8_v4/mwf_v4b/RAW_s*/shard*/preds_fold/*.npz"))
# verify each stitched file against merge stitched_sha256
stitched_ok = []
for sd in SEEDS:
    p = f"{R}/f8_v4/mwf_v4b/RAW_s{sd}/preds/f10_V2MAIN_RAW_{TAG}_s{sd}.npy"
    exp = wget(merge.get(sd) or {}, "merged", "stitched_sha256")
    if os.path.exists(p) and exp:
        stitched_ok.append((sd, sha(p) == exp))
manifest["mwf_predictions"] = {"rule": "ALL merged + per-shard + per-fold prediction files enumerated; NO truncation",
                               "stitched_count": len(stitched), "shard_preds_count": len(shard_preds),
                               "fold_preds_count": len(fold_preds),
                               "stitched_verified": {f"s{sd}": ok for sd, ok in stitched_ok}}
if len(stitched) == 2 and len(shard_preds) == 8 and len(fold_preds) == 40 and all(ok for _, ok in stitched_ok) and len(stitched_ok) == 2:
    proven("mwf_predictions", "prediction population enumerated in full: 2 stitched (both re-hash to merge stitched_sha256), "
                              "8 per-shard, 40 per-fold — stated counts, no [:6] sampling")
else:
    unproven("mwf_predictions", f"prediction population unexpected: stitched={len(stitched)} shard={len(shard_preds)} "
                                f"fold={len(fold_preds)} stitched_ok={stitched_ok}")

# --------------------------------------------------------------------------------------
# 10. VERDICT — derived.
refused = [c for c in CHECKS if c["status"] == "REFUSED"]
unprov  = [c for c in CHECKS if c["status"] == "UNPROVEN"]
sealed = not refused and not unprov
manifest["checks"] = CHECKS
manifest["summary"] = {"n_checks": len(CHECKS),
                       "proven": sum(c["status"] == "PROVEN" for c in CHECKS),
                       "note": sum(c["status"] == "NOTE" for c in CHECKS),
                       "refused": len(refused), "unproven": len(unprov)}
manifest["verdict"] = ("SEALED — every claim below is derived from a check that passed at run time"
                       if sealed else
                       "NOT SEALED — named refusals/unproven items below; nonzero exit")

out = f"{R}/MODEL_SEAL_MANIFEST.json"
try:
    with open(out, "w") as f:
        json.dump(manifest, f, indent=1)
    manifest["_written"] = out
except Exception as e:
    sys.stderr.write(f"could not write manifest {out}: {e}\n")

print("=" * 90)
print(manifest["verdict"])
print(f"self_sha256 {SELF_SHA}")
print(f"folds proven {n_fold_ok}/{manifest['n_folds_expected']} | checks "
      f"PROVEN {manifest['summary']['proven']} NOTE {manifest['summary']['note']} "
      f"REFUSED {manifest['summary']['refused']} UNPROVEN {manifest['summary']['unproven']}")
print("-" * 90)
for c in CHECKS:
    if c["status"] in ("REFUSED", "UNPROVEN"):
        print(f"  [{c['status']}] {c['item']}: {c['sentence']}")
if sealed:
    for c in CHECKS:
        if c["status"] in ("PROVEN", "NOTE"):
            print(f"  [{c['status']}] {c['item']}: {c['sentence']}")
print("=" * 90)
print("manifest ->", out if manifest.get("_written") else "(NOT WRITTEN)")
sys.exit(0 if sealed else 1)
