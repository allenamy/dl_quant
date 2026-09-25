#!/usr/bin/env python3
"""Add revision-1 arms to the ladder driver: LEGAL_res, MEM_res, three _ncfill, all_new_nclegal.

Pre-registration revision 1: docs/PREREG_gap_carrier_ladder_2026-09-25.md @ dd57ac30f
(file sha256 893abd37cfa87a0d07457bbdd62a5ccab804579605e1bac73244af1bdcf1ac03), lead's rulings verbatim.

  LEGAL_res         book_legal <- NEW's align_universe & funding_state[legal]   (lead's new arm)
  MEM_res           members    <- NEW's dlw_targets[members]                     (lead's new arm)
  KZ_res_ncfill     lead's path 2 sensitivity: NEW's KZ, but where NEW has no score keep NC's value
  KZWL_res_ncfill   same rule on KZ and WL
  F10_res_ncfill    same rule on F10's P
  all_new_nclegal   leave-one-out: everything NEW EXCEPT legal, which stays NC. Gives the book-layer
                    EXACT answer to "how much of the gap needs NEW trading cells NC calls untradable",
                    in dbar units -- not a price-return proxy. Its reading rule is lead's to write; the
                    seven-arm thresholds are deliberately NOT applied to it.

The fill rule is per cell and literal: NEW value non-finite => use NC's. Fill counts go in the receipt
per array, because "0 cells filled" is itself the claim for WL and has to be checkable.
"""
p = "/dev/shm/pnoise_2026-09-24/devices/pnoise_ladder_combo.py"
s = open(p).read()
n0 = len(s)

# --- take(): optional NC fill on non-finite NEW cells -------------------------------------------
s = s.replace(
    '''    def take(nc_arr, new_arr, rows):
        """NEW's array on NC's axis; anchors NEW lacks keep NC's values (counted)."""
        out = np.asarray(nc_arr, np.float64).copy()
        ok = rows >= 0
        out[ok] = np.asarray(new_arr, np.float64)[rows[ok]]
        return out, int((~ok).sum())''',
    '''    def take(nc_arr, new_arr, rows, ncfill=False):
        """NEW's array on NC's axis; anchors NEW lacks keep NC's values (counted).

        ncfill implements lead's path-2 rule literally, per CELL: where NEW's value is non-finite,
        keep NC's. The number of cells filled is returned so that "0 filled" is checkable, not assumed.
        """
        out = np.asarray(nc_arr, np.float64).copy()
        ok = rows >= 0
        newv = np.asarray(new_arr, np.float64)[rows[ok]]
        n_filled = 0
        if ncfill:
            nonfin = ~np.isfinite(newv)
            n_filled = int(nonfin.sum())
            newv = np.where(nonfin, out[ok], newv)
        out[ok] = newv
        return out, int((~ok).sum()), n_filled''',
    1)

s = s.replace(
    '''    swapped, kept_nc, NEW_LEGAL = [], {}, [False]
    def sub(name, new_arr, rows):
        v, n_kept = take(base[name], new_arr, rows)
        base[name] = v; swapped.append(name); kept_nc[name] = n_kept''',
    '''    swapped, kept_nc, NEW_LEGAL, nc_filled = [], {}, [False], {}
    def sub(name, new_arr, rows, ncfill=False):
        v, n_kept, n_fill = take(base[name], new_arr, rows, ncfill)
        base[name] = v; swapped.append(name + ("(ncfill)" if ncfill else "")); kept_nc[name] = n_kept
        if ncfill:
            nc_filled[name] = n_fill''',
    1)

# ready is taken through take() too -> unpack three values
s = s.replace(
    '''        rd, nk = take(base["ready"].astype(np.float64), nwl["ready"].astype(np.float64), rows_new)
        base["ready"] = rd > 0.5; swapped.append("ready"); kept_nc["ready"] = nk
    elif ARM == "KZWL_res":''',
    '''        rd, nk, _ = take(base["ready"].astype(np.float64), nwl["ready"].astype(np.float64), rows_new)
        base["ready"] = rd > 0.5; swapped.append("ready"); kept_nc["ready"] = nk
    elif ARM == "KZWL_res":''',
    1)
s = s.replace(
    '''        rd, nk = take(base["ready"].astype(np.float64), nwl["ready"].astype(np.float64), rows_new)
        base["ready"] = rd > 0.5; swapped.append("ready"); kept_nc["ready"] = nk
    else:''',
    '''        rd, nk, _ = take(base["ready"].astype(np.float64), nwl["ready"].astype(np.float64), rows_new)
        base["ready"] = rd > 0.5; swapped.append("ready"); kept_nc["ready"] = nk
    else:''',
    1)

# --- the six new arms --------------------------------------------------------------------------
NEWARMS = '''    elif ARM == "LEGAL_res":
        NEW_LEGAL[0] = True                                   # lead's new arm: only book_legal moves
    elif ARM == "MEM_res":
        nm_new = list(nwt["members"]); n_sw = 0                # lead's new arm: only members move
        for i in range(len(anchors)):
            if rows_new[i] >= 0:
                members[i] = np.asarray(nm_new[rows_new[i]], np.int64); n_sw += 1
        swapped.append("members"); kept_nc["members"] = int(len(anchors) - n_sw)
    elif ARM == "KZ_res_ncfill":
        sub("KZ", nwl["KZ"], rows_new, ncfill=True)
    elif ARM == "KZWL_res_ncfill":
        sub("KZ", nwl["KZ"], rows_new, ncfill=True)
        sub("WL", nwl["WL"], rows_new, ncfill=True)
    elif ARM == "F10_res_ncfill":
        sub("P", nwf["P"], rows_new, ncfill=True)
    elif ARM == "all_new_nclegal":
        # leave-one-out: identical to all_new EXCEPT book_legal stays NC. NEW_LEGAL is left False.
        for nm in ("KZ", "ZFD", "WL"):
            sub(nm, nwl[nm], rows_new)
        sub("RN8", nwfund["rn8"], rows_new)
        sub("QV", nwt["qvk"], rows_new)
        sub("P", nwf["P"], rows_new)
        nm_new = list(nwt["members"]); n_sw = 0
        for i in range(len(anchors)):
            if rows_new[i] >= 0:
                members[i] = np.asarray(nm_new[rows_new[i]], np.int64); n_sw += 1
        swapped.append("members"); kept_nc["members"] = int(len(anchors) - n_sw)
        rd, nk, _ = take(base["ready"].astype(np.float64), nwl["ready"].astype(np.float64), rows_new)
        base["ready"] = rd > 0.5; swapped.append("ready"); kept_nc["ready"] = nk
        rec["leave_one_out"] = ("everything NEW except book_legal, which stays NC. all_new minus this "
                                "arm isolates how much of the gap needs NEW trading cells NC calls "
                                "untradable -- exact, in dbar units, not a price-return proxy. Its "
                                "reading rule is lead's to write; the seven-arm thresholds are NOT "
                                "applied to it here.")
    else:'''
s = s.replace('    else:\n        rec["verdict"] = "UNAVAILABLE"; rec["why"] = f"unknown arm {ARM}"',
              NEWARMS + '\n        rec["verdict"] = "UNAVAILABLE"; rec["why"] = f"unknown arm {ARM}"', 1)

s = s.replace('    rec["anchors_keeping_nc_values_because_new_lacks_them"] = kept_nc',
              '''    rec["anchors_keeping_nc_values_because_new_lacks_them"] = kept_nc
    if nc_filled:
        rec["cells_filled_with_nc_because_new_had_no_score"] = nc_filled
        rec["fill_rule"] = ("lead's path 2, per cell and literal: NEW value non-finite => use NC's. "
                            "Counts are reported because '0 cells filled' is itself a claim.")''', 1)

s = s.replace(
    '''    if kept_nc:
        print(f"  anchors keeping NC values (NEW lacks them): {kept_nc}")''',
    '''    if kept_nc:
        print(f"  anchors keeping NC values (NEW lacks them): {kept_nc}")
    if nc_filled:
        print(f"  cells filled with NC because NEW had no score: {nc_filled}")''', 1)

s = s.replace('  none      red control     -- nothing substituted',
              '''  none      red control     -- nothing substituted
  LEGAL_res / MEM_res            revision 1 (dd57ac30f): lead's two added arms
  KZ_res_ncfill / KZWL_res_ncfill / F10_res_ncfill   revision 1: lead's path-2 sensitivity (NC fill)
  all_new_nclegal                revision 1: leave-one-out, everything NEW except legal''', 1)

open(p, "w").write(s)
ok = all(k in s for k in ('LEGAL_res', 'MEM_res', 'KZ_res_ncfill', 'KZWL_res_ncfill', 'F10_res_ncfill',
                          'all_new_nclegal', 'ncfill=True', 'cells_filled_with_nc_because_new_had_no_score',
                          'n_filled = int(nonfin.sum())'))
print("patched:", ok, "bytes", n0, "->", len(s))
