#!/usr/bin/env python3
"""Count ncfill fills at the granularity that means something: MEMBER cells, not the whole grid.

The first version reported 5,911,100 cells filled for KZ. That number is the full (anchor x symbol)
matrix, where non-member cells are NaN on BOTH sides by construction, so filling them changes nothing:
combo only ever reads KZ[i][members_i] (combo_target.py:23 asserts the member-field axes, and
continuous_combo slices by members). The consequential figure is the member-cell count -- the ~42,889
cells the coverage artifact actually refused anchors over.

"5,911,100 cells filled" written in a receipt is a number waiting to be misread, so both are now
reported and the member-cell one is named as the consequential one. Same defect family as reporting a
contamination bound in anchors when dbar's denominator is days.
"""
p = "/dev/shm/pnoise_2026-09-24/devices/pnoise_ladder_combo.py"
s = open(p).read()
n0 = len(s)

s = s.replace(
    '''    def sub(name, new_arr, rows, ncfill=False):
        v, n_kept, n_fill = take(base[name], new_arr, rows, ncfill)
        base[name] = v; swapped.append(name + ("(ncfill)" if ncfill else "")); kept_nc[name] = n_kept
        if ncfill:
            nc_filled[name] = n_fill''',
    '''    def sub(name, new_arr, rows, ncfill=False):
        v, n_kept, n_fill = take(base[name], new_arr, rows, ncfill)
        base[name] = v; swapped.append(name + ("(ncfill)" if ncfill else "")); kept_nc[name] = n_kept
        if ncfill:
            # The grid count is dominated by non-member cells, which are NaN on BOTH sides and never
            # read (combo slices by members). Count MEMBER cells too and name that the consequential one.
            NA = np.asarray(new_arr, np.float64)
            n_mem = n_mem_use = 0
            for i in range(len(anchors)):
                r = rows[i]
                if r < 0:
                    continue
                nb = int((~np.isfinite(NA[r][members[i]])).sum())
                n_mem += nb
                if anchors[i] >= 1672531200:
                    n_mem_use += nb
            nc_filled[name] = {"grid_cells": int(n_fill),
                               "grid_cells_note": ("whole (anchor x symbol) matrix; dominated by NON-member "
                                                   "cells that are NaN on both sides and never read"),
                               "member_cells_all_anchors": n_mem,
                               "member_cells_in_use_window": n_mem_use,
                               "consequential_count": "member_cells_in_use_window"}''',
    1)

s = s.replace(
    '''        rec["fill_rule"] = ("lead's path 2, per cell and literal: NEW value non-finite => use NC's. "
                            "Counts are reported because '0 cells filled' is itself a claim.")''',
    '''        rec["fill_rule"] = ("lead's path 2, per cell and literal: NEW value non-finite => use NC's. "
                            "Counts are reported because '0 cells filled' is itself a claim. Read "
                            "member_cells_in_use_window, NOT grid_cells: the grid count includes "
                            "non-member cells that are NaN on both sides and are never read by combo.")''',
    1)

s = s.replace(
    '''    if nc_filled:
        print(f"  cells filled with NC because NEW had no score: {nc_filled}")''',
    '''    for nm, v in nc_filled.items():
        print(f"  ncfill {nm}: member cells in use window = {v['member_cells_in_use_window']} "
              f"(consequential)   whole grid = {v['grid_cells']} (mostly non-member, never read)")''',
    1)

open(p, "w").write(s)
ok = all(k in s for k in ("member_cells_in_use_window", "consequential_count", "grid_cells_note"))
print("patched:", ok, "bytes", n0, "->", len(s))
