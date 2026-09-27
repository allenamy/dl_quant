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

rev 2 (news2 2026-09-27, runbook 1c -- the September extension; with none of the options below it is rev 1 byte for byte in every
array and every receipt key except argv/self_sha256):
  --extra-zips-root R --extra-months M1,M2   also read R/<M>/<SYM>-fundingRate-<M>.zip, only for months the manifest gate VERIFIES
  --extra-api F                              a second API source of the fund_aug shape (d10_pull_api_funding_ms.py); merged after
                                             fund_aug with setdefault (fund_aug wins); overlapping keys with unequal rates are
                                             counted (api_overlap_unequal) and must be 0 for a clean build
  --prefix-ledger P --prefix-sha S           prefix identity: for every row with ft_ms <= max(P.ft_ms) the event set and every rate
                                             must equal P's bitwise; src / zip_iv may change ONLY api-only -> both inside
                                             --extra-months (P2 had no 2026-08 zip, so adding it upgrades those rows; P = e179071d)
  --out-name N                               output file name (default ledger_full_ms.npz; October: ledger_full_ms_2026-09.npz)
With extra sources the fold-to-seconds reconciliation is restricted to rows at or before the old ledger's last second -- the
only window in which the old P2 ledger can be a reference.
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
    ap.add_argument("--extra-zips-root", default=None); ap.add_argument("--extra-months", default=None)
    ap.add_argument("--extra-api", default=None)
    ap.add_argument("--prefix-ledger", default=None); ap.add_argument("--prefix-sha", default=None)
    ap.add_argument("--out-name", default="ledger_full_ms.npz")
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
    EXTRA_MONTHS = [m for m in (a.extra_months or "").split(",") if m]
    if EXTRA_MONTHS:
        assert a.extra_zips_root, "--extra-months needs --extra-zips-root"
        sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
        import d10_manifest_gate as GATE
        for m in EXTRA_MONTHS:
            GATE.require_verified(os.path.join(a.extra_zips_root, m), m, what="d10_build_ledger_ms rev 2")
    EXTRA_API = json.loads(gzip.open(a.extra_api, "rt").read())["rates"] if a.extra_api else {}
    extended = bool(EXTRA_MONTHS or a.extra_api)
    off = [0]
    FT, RT, SR, ZI = [], [], [], []
    st = collections.Counter()
    st_ex = {"zip_same_ms_unequal": [], "conflict": []}

    for j, s in enumerate(SYMS):
        zrows = {}
        extra_zips = [os.path.join(a.extra_zips_root, m, f"{s}-fundingRate-{m}.zip") for m in EXTRA_MONTHS]
        for zp in sorted(glob.glob(f"{FUND_DIR}/{s}/*.zip")) + [z for z in extra_zips if os.path.exists(z)]:
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
        for t_ms, r in EXTRA_API.get(s, []):            # rev 2: fund_aug wins on an overlap; an unequal overlap is counted
            if int(t_ms) in arows and arows[int(t_ms)] != float(r):
                st["api_overlap_unequal"] += 1
            arows.setdefault(int(t_ms), float(r))
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
    outp = os.path.join(a.out, a.out_name)
    new_sha = DW.write_npz(outp, off=off, ft_ms=FT, rate=RT, src=SR, zip_iv=ZI, symbols=np.array(SYMS))
    log("built", len(FT), "rows ->", outp, new_sha[:16])

    # ---------------- positive control: fold to seconds and reconcile with the old ledger ----------------
    # Expected extras DERIVED from the millisecond key (lead's correction: a derived set, never a hardcoded
    # count). Within one second the fold keeps the EARLIEST ms, matching p2_prep_inputs' setdefault order.
    expected_extras = []
    old_max_sec = int(Zo["ft"].max())
    fold_off = [0]
    fFT, fRT, fSR, fZI = [], [], [], []
    for j in range(len(SYMS)):
        a0, b0 = int(off[j]), int(off[j + 1])
        seen = {}
        for k in range(a0, b0):
            sec = int(FT[k]) // 1000                    # FLOOR, as p2_prep_inputs does
            if extended and sec > old_max_sec:          # rev 2: the old ledger is a reference only up to its last second
                continue
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
    if extended:
        ctrl["window_note"] = f"rev 2: fold restricted to rows at or before the old ledger's last second {old_max_sec}"
        ctrl["api_overlap_unequal"] = int(st["api_overlap_unequal"])
        if st["api_overlap_unequal"]:
            ctrl["verdict"] = "NOT_RECONCILED"
    prefix = None
    if a.prefix_ledger:
        assert a.prefix_sha and sha(a.prefix_ledger).startswith(a.prefix_sha), "prefix ledger is not the pinned one"
        P = np.load(a.prefix_ledger, allow_pickle=True)
        pft, poff = P["ft_ms"].astype(np.int64), P["off"].astype(np.int64)
        psyms = [str(x) for x in P["symbols"]]
        pmax = int(pft.max())
        bad, new_rows_after, upgraded, upgraded_by_month = [], 0, 0, collections.Counter()
        extra_ms_ranges = []
        for m in EXTRA_MONTHS:
            y, mo = int(m[:4]), int(m[5:7])
            lo = datetime.datetime(y, mo, 1, tzinfo=datetime.timezone.utc)
            hi = datetime.datetime(y + (mo == 12), mo % 12 + 1, 1, tzinfo=datetime.timezone.utc)
            extra_ms_ranges.append((int(lo.timestamp() * 1000), int(hi.timestamp() * 1000)))
        assert psyms[:len(SYMS)] == SYMS, "prefix ledger symbol axis differs"
        for j in range(len(SYMS)):
            n0, n1, p0, p1 = int(off[j]), int(off[j + 1]), int(poff[j]), int(poff[j + 1])
            nm = FT[n0:n1] <= pmax
            new_rows_after += int((~nm).sum())
            nft, nrt, nsr, nzi = FT[n0:n1][nm], RT[n0:n1][nm], SR[n0:n1][nm], ZI[n0:n1][nm]
            oft, ort, osr = pft[p0:p1], P["rate"][p0:p1].astype(np.float64), P["src"][p0:p1].astype(np.int8)
            ozi = P["zip_iv"][p0:p1].astype(np.float32)
            if not (np.array_equal(nft, oft) and np.array_equal(nrt, ort)):
                bad.append(SYMS[j]); continue
            # the core (the event set and every rate) is identical; src / zip_iv may change ONLY where a newly added archive month
            # now also covers an event the prefix had from the API alone: src 1 -> 3 and zip_iv NaN -> a value
            in_extra = np.zeros(nft.size, bool)
            for lo_, hi_ in extra_ms_ranges:
                in_extra |= (nft >= lo_) & (nft < hi_)
            same_zi = (np.isnan(nzi) & np.isnan(ozi)) | (nzi == ozi)
            ch = (nsr != osr) | ~same_zi
            ok_up = in_extra & (osr == 1) & (nsr == 3) & np.isnan(ozi) & ~np.isnan(nzi)
            if np.any(ch & ~ok_up):
                bad.append(SYMS[j]); continue
            upgraded += int(ch.sum())
            for t in nft[ch]:
                upgraded_by_month[datetime.datetime.fromtimestamp(int(t) / 1000, datetime.timezone.utc).strftime("%Y-%m")] += 1
        prefix = {"path": a.prefix_ledger, "sha256": sha(a.prefix_ledger), "prefix_max_ms": pmax, "prefix_max_utc": iso_ms(pmax),
                  "symbols_differing": bad[:40], "n_symbols_differing": len(bad), "rows_after_prefix": new_rows_after,
                  "src_upgraded_rows_api_to_both": upgraded, "src_upgraded_by_month": dict(upgraded_by_month),
                  "rule": "event set and rates bitwise; src/zip_iv may change only api-only -> both inside --extra-months",
                  "verdict": "PREFIX_BITWISE" if not bad else "PREFIX_DIFFERS"}

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
    if extended or prefix:
        rec["rev2_extension"] = {"extra_months": EXTRA_MONTHS, "extra_api": a.extra_api,
                                 "extra_api_sha256": sha(a.extra_api) if a.extra_api else None, "prefix_identity": prefix}
    outj = os.path.join(a.out, "D10_LEDGER_MS_BUILD.json")
    rsha = DW.write_json(outj, rec, indent=1, allow_nan=True)
    log("control", ctrl["verdict"], "bitwise", ctrl.get("bitwise"), "extras", len(expected_extras))
    log("receipt ->", outj, rsha[:16])
    ok = ctrl["verdict"] == "RECONCILED" and (prefix is None or prefix["verdict"] == "PREFIX_BITWISE")
    if prefix:
        log("prefix", prefix["verdict"], "rows_after_prefix", prefix["rows_after_prefix"])
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
