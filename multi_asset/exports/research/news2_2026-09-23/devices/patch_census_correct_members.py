#!/usr/bin/env python3
"""Two corrections to the census, both of which could have produced a wrong headline.

(1) MEMBER SET. The census used NC's member set for every arm. That is right for an arm that keeps NC's
    members, and WRONG for an arm that substitutes them (all_new, MEM_res, all_new_nclegal): those arms
    run on NEW's member set, and "is NEW's KZ finite where this arm reads it" must be asked about the
    member set the arm actually reads. Measured against NC's members, all_new looked SILENT_ONLY -- i.e.
    it looked as if NEW's own book runs with 43k missing funding-rank cells. That claim needs NEW's own
    member set to be true, so it is not asserted until the census asks the right question.

(2) NCFILL REPAIR. The census reads the SOURCE array (NEW's), so for an _ncfill arm it describes the
    input BEFORE lead's path-2 repair. Left alone, an _ncfill arm shows up as SILENT_ONLY even though the
    repair is exactly what removes the missing cells. The arm's own receipt records the repair
    (cells_filled_with_nc_because_new_had_no_score), so the census now reads it and marks the array
    repaired instead of silently degraded.
"""
p = "/dev/shm/pnoise_2026-09-24/devices/ladder_arm_input_census.py"
s = open(p).read()
n0 = len(s)

s = s.replace(
    '    members = [mm[off[i]:off[i + 1]].astype(np.int64) for i in range(len(anchors))]',
    '''    members_nc = [mm[off[i]:off[i + 1]].astype(np.int64) for i in range(len(anchors))]
    # NEW's member set on NC's anchor axis, for arms that substitute members
    _nm_new = list(Z["targets"]["members"])
    members_new = [(np.asarray(_nm_new[rows[i]], np.int64) if rows[i] >= 0 else members_nc[i])
                   for i in range(len(anchors))]''',
    1)

s = s.replace('    def census(name):',
              '    def census(name, members, member_source, repaired):', 1)

s = s.replace(
    '''        d = {"array": f"{where}[{key}]", "shape": str(A.shape), "per_symbol": bool(per_symbol)}''',
    '''        d = {"array": f"{where}[{key}]", "shape": str(A.shape), "per_symbol": bool(per_symbol),
             "member_set_used": member_source,
             "repaired_by_ncfill": bool(repaired)}''',
    1)

s = s.replace('            d["silent"] = bool(cells > 0)',
              '            d["silent"] = bool(cells > 0 and not repaired)\n'
              '            if repaired:\n'
              '                d["repair_note"] = ("lead\'s path-2 fill replaced these cells with NC values; "\n'
              '                                    "the count above describes the INPUT before repair")', 1)

s = s.replace('            d["silent"] = bool(int(nf[inw].sum()) > 0)',
              '            d["silent"] = bool(int(nf[inw].sum()) > 0 and not repaired)', 1)

s = s.replace(
    '''        arrays = {nm: census(nm) for nm in subs}''',
    '''        swaps_members = any(x == "members" for x in subs)
        mem = members_new if swaps_members else members_nc
        msrc = ("NEW (this arm substitutes members, so it reads NEW's member set)" if swaps_members
                else "NC (this arm keeps NC's members)")
        filled = r.get("cells_filled_with_nc_because_new_had_no_score", {}) or {}
        arrays = {nm: census(nm, mem, msrc, nm in filled) for nm in subs}''',
    1)

s = s.replace(
    '''    rec["coverage_rule"] = "per-symbol arrays -> member cells in the use window; others -> in/out of window entries"''',
    '''    rec["coverage_rule"] = "per-symbol arrays -> member cells in the use window; others -> in/out of window entries"''',
    1)

s = s.replace(
    '''                    "silent_degradation_arrays": silent,''',
    '''                    "silent_degradation_arrays": silent,
                    "member_set_used": msrc,
                    "arrays_repaired_by_ncfill": sorted(filled.keys()),''',
    1)

s = s.replace(
    '''            if c.get("per_symbol"):
                print(f"      {nm:8s} {c['shape']:14s} non-finite member cells={c['non_finite_member_cells_in_use_window']:7d}"
                      f"  anchors={c['anchors_affected']:5d}  per_year={c.get('anchors_affected_per_year')}")''',
    '''            if c.get("per_symbol"):
                tag = " [REPAIRED by ncfill]" if c.get("repaired_by_ncfill") else ""
                print(f"      {nm:8s} {c['shape']:14s} non-finite member cells={c['non_finite_member_cells_in_use_window']:7d}"
                      f"  anchors={c['anchors_affected']:5d}  per_year={c.get('anchors_affected_per_year')}{tag}")''',
    1)

s = s.replace(
    '''        print(f"  {arm:20s} {d['verdict']:16s} loud={d['loud_degradation']} silent={d['silent_degradation_arrays']}")''',
    '''        print(f"  {arm:20s} {d['verdict']:16s} loud={d['loud_degradation']} silent={d['silent_degradation_arrays']}"
              f"  members={'NEW' if 'NEW' in d['member_set_used'] else 'NC'}")''',
    1)

open(p, "w").write(s)
ok = all(k in s for k in ("members_new", "repaired_by_ncfill", "member_set_used", "swaps_members"))
print("patched:", ok, "bytes", n0, "->", len(s))
