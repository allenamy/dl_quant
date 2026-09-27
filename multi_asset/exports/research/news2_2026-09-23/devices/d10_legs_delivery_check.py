#!/usr/bin/env python3
"""d10_legs_delivery_check.py <out dir> <reference legs.npz> <king oof sha> <out.json> -- the checks before an October legs.npz is
handed to dlarch (lead 2026-09-27, after pod2's root overlay filled for ~1 min at 07:17-07:20Z during the October build):
  L1 the driver log's last line is `LEGS_OCT DONE <sha>` and the log has no Traceback / ENOSPC / "No space" / "FAILED"
  L2 legs.npz re-read byte by byte: its sha equals the DONE line; the zip opens and every member passes its CRC
  L3 NC_LEGS_RECEIPT.json: sha256 == file sha, inputs.king_oof == the October King OOF sha, features == f1cd3fa2, fund_state == f07e4ebd
  L4 same keys, shapes and dtypes as the reference legs (line D legs_d10 104af853); ready / not_ready counts and reasons side by side
     (the King changed, so values may differ; the axis and the layout may not)
Prints one anchored line `LEGS_DELIVERY PASS|FAIL <reasons>`; writes the receipt through durable_write.
"""
import hashlib, json, os, re, sys, zipfile

import numpy as np

for _c in (os.path.dirname(os.path.realpath(__file__)),
           os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), "common"),
           os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))), "common")):
    if os.path.exists(os.path.join(_c, "durable_write.py")):
        sys.path.insert(0, _c)
        break
else:
    raise ImportError("common/durable_write.py not found next to or above this device; deploy it with the device")
import durable_write as DW  # every file this device writes goes through it (news2 class fix 2026-09-27)

FEATURES_SHA = "f1cd3fa2b48e96ddf202a5098e08b9cc0ebcffda3bfc42c347743b9a5cd7d5fd"
FUND_STATE_PREFIX = "f07e4ebd"


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 24), b""):
            h.update(b)
    return h.hexdigest()


def main():
    out_dir, ref, koof_sha, outp = sys.argv[1:5]
    fails, rec = [], {"device": os.path.basename(__file__), "self_sha256": sha(os.path.realpath(__file__)), "out_dir": out_dir}
    log = open(os.path.join(out_dir, "legs_oct.log")).read()
    lines = [l for l in log.splitlines() if l.strip()]
    m = re.fullmatch(r"LEGS_OCT DONE ([0-9a-f]{64})", lines[-1] if lines else "")
    bad_words = [w for w in ("Traceback", "ENOSPC", "No space", "FAILED", "Errno 28") if w in log]
    rec["L1"] = {"last_line": lines[-1] if lines else None, "bad_words": bad_words}
    if not m or bad_words:
        fails.append("L1 log")
    p = os.path.join(out_dir, "legs.npz")
    got = sha(p)
    crc_bad = None
    try:
        with zipfile.ZipFile(p) as z:
            crc_bad = z.testzip()
    except zipfile.BadZipFile as e:
        crc_bad = f"BadZipFile {e}"
    rec["L2"] = {"sha256": got, "done_line_sha": m.group(1) if m else None, "crc_first_bad": crc_bad}
    if not m or got != m.group(1) or crc_bad is not None:
        fails.append("L2 bytes")
    rp = os.path.join(out_dir, "NC_LEGS_RECEIPT.json")
    r = json.load(open(rp)) if os.path.exists(rp) else {}
    inp = r.get("inputs", {})
    rec["L3"] = {"receipt": rp, "receipt_sha256": sha(rp) if os.path.exists(rp) else None, "sha256": r.get("sha256"),
                 "king_oof": inp.get("king_oof"), "features": inp.get("features"), "fund_state": inp.get("fund_state")}
    if not (r.get("sha256") == got and inp.get("king_oof") == koof_sha and inp.get("features") == FEATURES_SHA
            and str(inp.get("fund_state", "")).startswith(FUND_STATE_PREFIX)):
        fails.append("L3 receipt")
    A, B = np.load(p, allow_pickle=True), np.load(ref, allow_pickle=True)
    layout = {k: {"new": [list(A[k].shape), str(A[k].dtype)], "ref": [list(B[k].shape), str(B[k].dtype)]}
              for k in sorted(set(A.files) | set(B.files)) if k in A.files and k in B.files}
    rec["L4"] = {"keys_only_new": sorted(set(A.files) - set(B.files)), "keys_only_ref": sorted(set(B.files) - set(A.files)),
                 "layout_mismatch": {k: v for k, v in layout.items() if v["new"] != v["ref"]},
                 "counts_new": {k: r.get(k) for k in ("ready", "not_ready", "not_ready_reasons", "leg_returns", "first_ready")},
                 "ref_file_sha256": sha(ref)}
    if rec["L4"]["keys_only_new"] or rec["L4"]["keys_only_ref"] or rec["L4"]["layout_mismatch"]:
        fails.append("L4 layout")
    rec["verdict"] = "PASS" if not fails else "FAIL"
    rec["fails"] = fails
    s = DW.write_json(outp, rec, indent=1, allow_nan=True, default=str)
    print(f"LEGS_DELIVERY {rec['verdict']} {fails} legs_sha256={got} receipt_sha256={s}")


if __name__ == "__main__":
    main()
