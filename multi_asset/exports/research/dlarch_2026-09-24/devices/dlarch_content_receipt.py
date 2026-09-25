#!/usr/bin/env python3
"""dlarch_content_receipt.py -- a reference token that survives a re-run.

WHY (lead ruling 2026-09-25): a sha handed to another agent as a reference key must be a CONTENT sha.
`TRAIN_RECEIPT.json`'s file sha is not: it records wall-clock fields, so re-running a fold changes it
even when every prediction is bit-identical. Measured on (T0, s42, 202506): `scores.npz` sha,
`model.pt` sha, `train_loss`, `alpha`, `a_final`, `scored_pairs` all IDENTICAL, while
`elapsed_seconds` went 135.33 -> 133.93 and `curve[*].seconds` changed -- which moved the fold
receipt's sha (2a47f56d -> 524eafd0) and hence the train receipt's (21f94f90 -> 178f2cbe). I had
already given the old value to fresh as a reference key, so it went stale.

WHY A SIDECAR AND NOT A CHANGE TO THE TRAINER: the trainer's own sha is inside its `sources` block, so
editing it would (a) make resume hard-fail on any seed already part-trained, (b) make every completed
seed's receipt mismatch on a re-merge, and (c) require re-running the G1 bitwise-identity gate. A
sidecar costs none of that and can also be written for seeds that are ALREADY delivered, so coverage is
better than "from the next seed onward".

WHAT GOES IN `content` (hashed): only quantities that a re-run reproduces -- the OOF sha, per-fold
scores/model shas, scored_pairs, test_anchors, param_count, a_init/a_final, and the loss curve with
its `seconds` field removed. Input/source shas are kept by BASENAME -> sha, because the absolute path
is an environment fact, not content.
WHAT GOES IN `env` (NOT hashed): timings, gpu name, absolute paths, the receipt file shas.

usage: dlarch_content_receipt.py <env-whitelist> <seed dir> [<seed dir> ...]
"""
import hashlib
import json
import os
import sys
import time

TIMING_KEYS = {"elapsed_seconds", "seconds", "utc_start", "utc_end", "logged_utc", "run_utc"}
ENV_KEYS = {"gpu", "elapsed_seconds"}


def sha_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


# The OOF's expected schema. fresh (2026-09-25) pointed out that `F10_OOF.npz`'s file sha is a
# CONTAINER sha, not array identity: this project already has two counterexamples -- .npz file sha !=
# array identity, and an npz carrying a per-run `model_sha256` whose container sha moved every run while
# the prediction matrix was bit-identical. He checked my delivered file (keys E_ts/P/symbols only, no
# timing/host/path/nested-sha), so the container sha happens to be safe TODAY -- but it depends on the
# schema never gaining a field like `written_utc`, and that failure would be SILENT.
# So the content key is built from ARRAY BYTES, and a schema change is made LOUD.
OOF_EXPECTED_KEYS = ("E_ts", "P", "symbols")


def oof_arrays(path):
    """Per-array byte shas + a combined key. Independent of the container's schema."""
    import numpy as np
    with np.load(path, allow_pickle=False) as z:
        keys = tuple(sorted(z.files))
        per = {k: {"shape": list(z[k].shape), "dtype": str(z[k].dtype),
                   "bytes_sha256": hashlib.sha256(np.ascontiguousarray(z[k]).tobytes()).hexdigest()}
               for k in keys}
    combined = hashlib.sha256(
        "".join(f"{k}:{per[k]['dtype']}:{per[k]['shape']}:{per[k]['bytes_sha256']}" for k in keys).encode()
    ).hexdigest()
    unexpected = [k for k in keys if k not in OOF_EXPECTED_KEYS]
    missing = [k for k in OOF_EXPECTED_KEYS if k not in keys]
    return {"keys": list(keys), "per_array": per, "arrays_sha256": combined,
            "schema_matches_expected": not unexpected and not missing,
            "unexpected_keys": unexpected, "missing_keys": missing,
            "note": ("arrays_sha256 is built from array BYTES, so it does not depend on the container "
                     "schema; schema_matches_expected must stay true -- if a field is ever added to the "
                     "OOF, the container sha would move silently while predictions are unchanged")}


def strip_timing(o):
    """Recursively drop timing fields, so the curve keeps train_loss/alpha but not per-epoch seconds."""
    if isinstance(o, dict):
        return {k: strip_timing(v) for k, v in o.items() if k not in TIMING_KEYS}
    if isinstance(o, list):
        return [strip_timing(v) for v in o]
    return o


# Version of the `content` field list. content_sha256 covers those fields, so ADDING a field moves the
# hash even though nothing about the artifacts changed -- the same silent-drift hazard this device was
# built to close, one level up. Bumping this makes the cause visible: a reader comparing two
# content_sha256 values must first compare the versions.
#   v1 (2026-09-25 09:2xZ): no oof_arrays; the prediction key was the OOF CONTAINER sha
#   v2 (2026-09-25 09:4xZ): + oof_arrays (per-array byte shas + arrays_sha256) and a loud schema guard,
#                           after fresh pointed out that a container sha depends on the schema holding
CONTENT_SCHEMA_VERSION = 2


def content_of(seed_dir):
    tr_path = os.path.join(seed_dir, "TRAIN_RECEIPT.json")
    tr = json.load(open(tr_path))
    oof = os.path.join(seed_dir, "F10_OOF.npz")
    content = {"content_schema_version": CONTENT_SCHEMA_VERSION,
               "arm": tr.get("arm"), "seed": tr.get("seed"), "status": tr.get("status"),
               "folds": tr.get("folds"), "expected_folds": tr.get("expected_folds"),
               # container sha (kept: it is what the trainer recorded and it is stable in practice)
               "oof_sha256": tr.get("pred_sha256"),
               # ARRAY-level identity: the primary key, independent of the container schema
               "oof_arrays": oof_arrays(oof) if os.path.exists(oof) else None,
               "inputs_by_basename": {os.path.basename(k): v for k, v in (tr.get("inputs") or {}).items()},
               "sources_by_basename": {os.path.basename(k): v for k, v in (tr.get("sources") or {}).items()},
               "per_fold": {}}
    for tag in sorted(tr.get("folds") or []):
        fr = os.path.join(seed_dir, tag, "FOLD_RECEIPT.json")
        if not os.path.exists(fr):
            content["per_fold"][tag] = {"MISSING_FOLD_RECEIPT": True}
            continue
        r = json.load(open(fr))
        content["per_fold"][tag] = {
            k: r.get(k) for k in ("score_sha256", "model_sha256", "scored_pairs", "test_anchors",
                                  "score_label_missing_pairs", "param_count", "a_init", "a_final",
                                  "anchors_skipped_in_spans", "fixed_epoch_index", "schedule_T_max",
                                  "updates_end_at_index")}
        content["per_fold"][tag]["curve_without_timings"] = strip_timing(r.get("curve"))
        content["per_fold"][tag]["seat_census"] = r.get("seat_census")
    env = {"seed_dir": seed_dir, "train_receipt_path": tr_path,
           "train_receipt_file_sha256": sha_file(tr_path),
           "oof_file_sha256_recomputed": sha_file(oof) if os.path.exists(oof) else None,
           "gpu_and_timings_excluded_from_content": True,
           "utc_written": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    blob = json.dumps(content, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return content, env, hashlib.sha256(blob.encode()).hexdigest()


def main():
    wl = set(sys.argv[1].split(","))
    extra = sorted(set(os.environ) - wl)
    assert not extra, f"env outside whitelist: {extra}"
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import dlarch_safe_io as sio
    rows = []
    for d in sys.argv[2:]:
        content, env, csha = content_of(d)
        rec = {"device": "dlarch_content_receipt.py",
               "self_sha256": sha_file(os.path.abspath(__file__)),
               "content_sha256": csha,
               "REFERENCE_KEY": ("PRIMARY: content_sha256 (whole seed). For predictions alone use "
                                 "content.oof_arrays.arrays_sha256 -- it hashes ARRAY BYTES and so does "
                                 "not depend on the OOF container schema. content.oof_sha256 is the "
                                 "container sha: fine today (keys are exactly E_ts/P/symbols) but it "
                                 "would move silently if a field were ever added to the OOF, so use it "
                                 "only as corroboration. NEVER use the TRAIN_RECEIPT file sha as a "
                                 "reference key -- it moves when only timings change."),
               "KEY_STABILITY": ("oof_arrays.arrays_sha256 is the MOST stable key: it moves only if the "
                                 "arrays move. content_sha256 also moves if this device's content field "
                                 "list changes, which is why content_schema_version exists -- compare "
                                 "versions before concluding that content differs."),
               "content_schema_version": CONTENT_SCHEMA_VERSION,
               "schema_guard": (None if content.get("oof_arrays") is None
                                else {"matches_expected": content["oof_arrays"]["schema_matches_expected"],
                                      "expected": list(OOF_EXPECTED_KEYS),
                                      "actual": content["oof_arrays"]["keys"]}),
               "content": content, "env": env}
        oa = content.get("oof_arrays")
        assert oa is None or oa["schema_matches_expected"], (
            f"{d}: OOF schema changed -- expected {OOF_EXPECTED_KEYS}, got {oa['keys']}; "
            "the container sha would move silently while predictions are unchanged, so this is loud on purpose")
        out = os.path.join(d, "CONTENT_RECEIPT.json")
        written = sio.write_json(out, rec)
        rows.append((content.get("seed"), len(content.get("folds") or []), csha, content.get("oof_sha256"), out, written))
        print(f"seed {content.get('seed'):>5}  folds {len(content.get('folds') or []):>2}  "
              f"content_sha256 {csha}")
        print(f"        oof_arrays_sha256 {oa['arrays_sha256'] if oa else None}   (PRIMARY for predictions)")
        print(f"        oof_container_sha {content.get('oof_sha256')}   (corroboration only)")
        print(f"        written {out} (file sha {written[:16]})")
    print(f"DLARCH_CONTENT_RECEIPT seeds={len(rows)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
