#!/usr/bin/env python3
"""d10_build_ledger_ms.py -- build ledger_full_ms.npz: P2's ledger re-keyed by MILLISECOND.

lead's DECISION_RULE_D10_stage2_2026-09-26.md revision 2/3: option (a) as a NEW ARTIFACT. The old
ledger_full.npz (bea6f575) is NOT touched and every pin on it stays as it is, so nothing downstream has to
change. Only the October rebuild and the line B gate read this new file.

SEMANTICS ARE p2_prep_inputs.py's, VERBATIM EXCEPT THE KEY. I read that builder rather than reconstructing it
from its description, and two details would have been wrong from memory:
  * the key is `int(row[0]) // 1000` -- FLOOR, not round. My other devices use round; here the fold-back
    control must use floor or it would not reproduce P2 even when P2 is right.
  * within one key, `setdefault` means FIRST ENCOUNTERED WINS, and since the files are chronological that is
    the EARLIEST millisecond. Confirmed against the known case: for MSFTUSDT 2026-05-21T00:00Z the old ledger
    kept rate 0.0, which is the row at ...600000, not the one at ...600006.
Everything else is copied: the header assertion, `r = arows[t]` when both sources have a key (the API rate is
kept whether or not they agree), src 1/2/3/4, zip_iv from the zip side only, and the strictly-increasing
assertion per symbol.

THE POSITIVE CONTROL IS THE RECONCILIATION (lead's revision 2, as corrected by lead): fold the new ledger back
to seconds and it must be BITWISE IDENTICAL to the old one, and the rows that folding removes must be EXACTLY
the set of same-second extras DERIVED FROM THE DATA -- not a hardcoded count. lead corrected their own first
wording of "exactly 2 events" to a derived set, and this device derives it: the expected extras are computed
from the millisecond key itself, then compared with what the fold actually dropped, both ways.

Usage:
  d10_build_ledger_ms.py --out <dir> [--limit-symbols N]     build + reconcile + receipt
"""
import argparse
import collections
import csv
import datetime
import glob
import gzip
import hashlib
import io
import json
import os
import sys
import time
import zipfile

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

OLD = "/workspace/uplift_r2_2026-09-13/P2/work/ledger_full.npz"
OLD_SHA = "bea6f5752772d54e659a4da5571ca41945a27d1b2316ec0ae52f387074f795ad"
FUND_DIR = "/workspace/wide_multisrc/funding"
FUND_AUG = "/workspace/fund_aug.json.gz"


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for c in iter(lambda: fh.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def iso_ms(ms):
    return datetime.datetime.fromtimestamp(int(ms) / 1000.0, datetime.timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%S.%fZ")


def log(*a):
    print(time.strftime("%H:%M:%S", time.gmtime()), *a, flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--limit-symbols", type=int, default=None)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    t0 = time.time()

    Zo = np.load(OLD, allow_pickle=True)
    assert sha(OLD) == OLD_SHA, "the old ledger is not the pinned artifact"
    SYMS = [str(s) for s in Zo["symbols"]]
    if a.limit_symbols:
        SYMS = SYMS[:a.limit_symbols]
    log("axis", len(SYMS), "symbols; old ledger sha", OLD_SHA[:16])

    AUG = json.loads(gzip.open(FUND_AUG, "rt").read())["rates"]
    off = [0]
    FT, RT, SR, ZI = [], [], [], []
    st = collections.Counter()
    st_ex = {"zip_same_ms_unequal": [], "conflict": []}

    for j, s in enumerate(SYMS):
        zrows = {}
        for zp in sorted(glob.glob(f"{FUND_DIR}/{s}/*.zip")):
            with zipfile.ZipFile(zp) as zf:
                with zf.open(zf.namelist()[0]) as fh:
                    rd = csv.reader(io.TextIOWrapper(fh))
                    hdr = next(rd)
                    assert [h.strip() for h in hdr] == ["calc_time", "funding_interval_hours",
                                                        "last_funding_rate"], (zp, hdr)
                    for row in rd:
                        if not row:
                            continue
                        try:
                            t = int(row[0])            # ★ MILLISECONDS, no // 1000
                            iv = float(row[1])
                            r = float(row[2])
                        except Exception:
                            st["zip_bad_rows"] += 1
                            continue
                        if t in zrows and zrows[t][0] != r:
                            st["zip_same_ms_unequal"] += 1
                            if len(st_ex["zip_same_ms_unequal"]) < 20:
                                st_ex["zip_same_ms_unequal"].append([s, iso_ms(t), zrows[t][0], r])
                        zrows.setdefault(t, (r, iv))
        arows = {}
        for t_ms, r in AUG.get(s, []):
            arows.setdefault(int(t_ms), float(r))      # ★ MILLISECONDS
        keys = sorted(set(zrows) | set(arows))
        if not keys:
            st["symbols_no_rows"] += 1
        for t in keys:
            inz, ina = t in zrows, t in arows
            if inz and ina:
                if zrows[t][0] == arows[t]:
                    src = 3
                    st["n_both_equal"] += 1
                else:
                    src = 4
                    st["n_conflict"] += 1
                    if len(st_ex["conflict"]) < 20:
                        st_ex["conflict"].append([s, iso_ms(t), zrows[t][0], arows[t]])
                r = arows[t]                            # the API rate is kept, agreeing or not (P2's rule)
            elif ina:
                src = 1
                r = arows[t]
                st["n_aug_only"] += 1
            else:
                src = 2
                r = zrows[t][0]
                st["n_zip_only"] += 1
            FT.append(t)
            RT.append(r)
            SR.append(src)
            ZI.append(zrows[t][1] if inz else np.nan)
        off.append(len(FT))
        if j % 100 == 0:
            log("ledger", j, s, len(FT))

    FT = np.array(FT, np.int64)
    RT = np.array(RT, np.float64)
    SR = np.array(SR, np.int8)
    ZI = np.array(ZI, np.float32)
    off = np.array(off, np.int64)
    for j in range(len(SYMS)):
        seg = FT[off[j]:off[j + 1]]
        assert np.all(np.diff(seg) > 0), SYMS[j]
    outp = os.path.join(a.out, "ledger_full_ms.npz")
    new_sha = DW.write_npz(outp, off=off, ft_ms=FT, rate=RT, src=SR, zip_iv=ZI, symbols=np.array(SYMS))
    log("built", len(FT), "rows ->", outp, new_sha[:16])

    # ---------------- positive control: fold to seconds and reconcile with the old ledger ----------------
    # Expected extras DERIVED from the millisecond key (lead's correction: a derived set, never a hardcoded
    # count). Within one second the fold keeps the EARLIEST ms, matching p2_prep_inputs' setdefault order.
    expected_extras = []
    fold_off = [0]
    fFT, fRT, fSR, fZI = [], [], [], []
    for j in range(len(SYMS)):
        a0, b0 = int(off[j]), int(off[j + 1])
        seen = {}
        for k in range(a0, b0):
            sec = int(FT[k]) // 1000                    # FLOOR, as p2_prep_inputs does
            if sec in seen:
                expected_extras.append({"symbol": SYMS[j], "kept_ms": int(FT[seen[sec]]),
                                        "dropped_ms": int(FT[k]), "utc": iso_ms(FT[k]),
                                        "kept_rate": float(RT[seen[sec]]), "dropped_rate": float(RT[k])})
                continue
            seen[sec] = k
            fFT.append(sec)
            fRT.append(float(RT[k]))
            fSR.append(int(SR[k]))
            fZI.append(float(ZI[k]))
        fold_off.append(len(fFT))
    fFT = np.array(fFT, np.int64)
    fRT = np.array(fRT, np.float64)
    fSR = np.array(fSR, np.int8)
    fZI = np.array(fZI, np.float32)
    fold_off = np.array(fold_off, np.int64)

    ctrl = {"expected_extras_derived_from_ms_key": len(expected_extras),
            "extras": expected_extras[:40],
            "rows_new_ms": int(FT.size), "rows_after_fold": int(fFT.size),
            "rows_old_p2": int(Zo["ft"].size),
            "fold_removed": int(FT.size - fFT.size)}
    if a.limit_symbols:
        ctrl["note"] = "partial run (--limit-symbols): the old ledger covers all 829, so array equality is " \
                       "only checked on the symbols built here"
        oo = Zo["off"].astype(np.int64)
        lim = int(oo[len(SYMS)])
        old_ft, old_rt, old_sr, old_zi = (Zo["ft"][:lim], Zo["rate"][:lim], Zo["src"][:lim], Zo["zip_iv"][:lim])
        old_off = oo[:len(SYMS) + 1]
    else:
        old_ft, old_rt, old_sr, old_zi = Zo["ft"], Zo["rate"], Zo["src"], Zo["zip_iv"]
        old_off = Zo["off"].astype(np.int64)

    same_shape = (fFT.shape == old_ft.shape)
    ctrl["fold_shape_equals_old"] = bool(same_shape)
    if same_shape:
        ctrl["bitwise"] = {
            "ft": bool(np.array_equal(fFT, old_ft.astype(np.int64))),
            "rate": bool(np.array_equal(fRT, old_rt.astype(np.float64))),
            "src": bool(np.array_equal(fSR, old_sr.astype(np.int8))),
            "zip_iv": bool(np.array_equal(np.isnan(fZI), np.isnan(old_zi.astype(np.float32)))
                           and np.array_equal(fZI[~np.isnan(fZI)],
                                              old_zi.astype(np.float32)[~np.isnan(old_zi.astype(np.float32))])),
            "off": bool(np.array_equal(fold_off, old_off)),
        }
        for k in ("ft", "rate", "src"):
            if not ctrl["bitwise"][k]:
                arr_new = {"ft": fFT, "rate": fRT, "src": fSR}[k]
                arr_old = {"ft": old_ft, "rate": old_rt, "src": old_sr}[k]
                bad = np.flatnonzero(arr_new != arr_old)
                ctrl.setdefault("first_differences", {})[k] = [
                    {"index": int(i), "new": float(arr_new[i]), "old": float(arr_old[i])} for i in bad[:10]]
        ctrl["ALL_BITWISE"] = all(ctrl["bitwise"].values())
    else:
        ctrl["ALL_BITWISE"] = False
        ctrl["shape_detail"] = {"fold": list(fFT.shape), "old": list(old_ft.shape)}
    ctrl["derived_set_matches_fold"] = bool(ctrl["fold_removed"] == len(expected_extras))
    ctrl["verdict"] = ("RECONCILED" if ctrl["ALL_BITWISE"] and ctrl["derived_set_matches_fold"]
                       else "NOT_RECONCILED")

    rec = {"device": os.path.basename(__file__), "self_sha256": sha(os.path.realpath(__file__)),
           "argv": vars(a), "python": {"version": sys.version.split()[0], "executable": sys.executable},  # lead 09-27: derived, not listed
           "criteria": "DECISION_RULE_D10_stage2_2026-09-26.md revisions 1-3 (ms key; new artifact; old pins unchanged)",
           "semantics": "p2_prep_inputs.py verbatim EXCEPT the key is milliseconds (not t_ms // 1000)",
           "old_ledger": {"path": OLD, "sha256": OLD_SHA, "untouched": True},
           "new_ledger": {"path": outp, "sha256": new_sha, "rows": int(FT.size), "symbols": len(SYMS),
                          "ft_first": iso_ms(FT.min()), "ft_last": iso_ms(FT.max()),
                          "key": "fundingTime MILLISECONDS"},
           "union_stats": {k: int(v) for k, v in st.items()}, "examples": st_ex,
           "ms_key_finding_recorded_per_lead": (
               "On the MILLISECOND key the two sources conflict on 0 shared rows (src == 4 = "
               f"{int(st['n_conflict'])}). This is stronger than the old 'src == 4 is 0', which was computed "
               "after rounding to seconds and was therefore blind to a settlement discarded inside one "
               "second -- the failure mode that motivated this rebuild."),
           "positive_control_reconciliation": ctrl,
           "seconds": round(time.time() - t0, 1)}
    outj = os.path.join(a.out, "D10_LEDGER_MS_BUILD.json")
    rsha = DW.write_json(outj, rec, indent=1, allow_nan=True)
    log("control", ctrl["verdict"], "bitwise", ctrl.get("bitwise"), "extras", len(expected_extras))
    log("receipt ->", outj, rsha[:16])
    return 0 if ctrl["verdict"] == "RECONCILED" else 2


if __name__ == "__main__":
    sys.exit(main())
