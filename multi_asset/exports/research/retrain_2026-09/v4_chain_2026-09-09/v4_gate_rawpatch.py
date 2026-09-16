"""RAW_PATCH_COVERAGE gate (FX-TRAIN TRN-02, 2026-09-13; AUDIT_TRAIN 7e1ecf9a TRN-02; docs/fixprogram_2026-09-13/FX_TRAIN/FACT_TABLE_TRN.md §TRN-02).
Standalone receipt of the coverage rules in v4_rawpatch_lib.py (G1-G9) for one (cache, raw patch, manifest) triple. The same rules run inside
pod_dlw_targets_raw.py, which refuses to build patched targets unless they PASS; this program exists so a roll/extension stage (or a reviewer) can bind a
receipt to the exact files. Receipt through v4_gate_common.finalize (gate RAW_PATCH_COVERAGE; inputs cache / raw_patch / raw_patch_manifest): rc 0 iff PASS, else 3.
env (all REQUIRED, no defaults): CACHE, RAW_PATCH, RAW_PATCH_MANIFEST, RAWPATCH_OUT. A missing key or file is a PASS=false receipt naming it (rc 3)."""
import json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from v4_gate_common import finalize, sha256_file
_OUT = os.environ.get("RAWPATCH_OUT")
if not _OUT:
    print("RAWPATCH_REFUSED missing RAWPATCH_OUT (no receipt path: nothing written)", flush=True); sys.exit(3)
_KEYS = ("CACHE", "RAW_PATCH", "RAW_PATCH_MANIFEST")
E = {k: os.environ.get(k, "") for k in _KEYS}
INPUTS = {"cache": E["CACHE"] or None, "raw_patch": E["RAW_PATCH"] or None, "raw_patch_manifest": E["RAW_PATCH_MANIFEST"] or None}
_ref = {}
if [k for k in _KEYS if not E[k]]: _ref["missing_env"] = [k for k in _KEYS if not E[k]]
if {k: v for k, v in INPUTS.items() if not v or not os.path.isfile(v)}: _ref["missing_files"] = {k: v for k, v in INPUTS.items() if not v or not os.path.isfile(v)}
if _ref:
    print("RAWPATCH_REFUSED", json.dumps(_ref), flush=True); finalize("RAW_PATCH_COVERAGE", {"PASS": False, "REFUSED": _ref}, _OUT, INPUTS)
import numpy as np
import v4_rawpatch_lib as L
t0 = time.time()
Z = np.load(E["CACHE"], allow_pickle=True); CTS = Z["ts"].astype(np.int64); syms = [str(s) for s in Z["symbols"]]; ch0 = Z["data"][:, :, 0]
rep = L.verify_files(ch0, CTS, syms, E["RAW_PATCH"], E["CACHE"], cache_sha256=sha256_file(E["CACHE"]), manifest_path=E["RAW_PATCH_MANIFEST"])
rep["wall_s"] = round(time.time() - t0, 1); rep["built_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
for k, v in rep.get("checks", {}).items():
    print(("  OK   " if v.get("ok") else "  FAIL ") + k + " " + json.dumps({kk: vv for kk, vv in v.items() if kk != "ok"}, default=str)[:300], flush=True)
print("RAW_PATCH_COVERAGE", "PASS" if rep["PASS"] else "FAIL", json.dumps(rep.get("summary", {})), flush=True)
finalize("RAW_PATCH_COVERAGE", rep, _OUT, INPUTS)
