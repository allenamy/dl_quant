#!/usr/bin/env python3
"""Member-cell counting only applies to per-SYMBOL arrays. WL is not one.

Crash: IndexError: index 12 is out of bounds for axis 0 with size 3, at NA[r][members[i]] for WL.
MEASURED shapes: KZ (10321, 829) and ZFD (10321, 829) are per-symbol; **WL is (10321, 3)** -- the
three SEAT weights per anchor -- and `ready` is (10321,). Confirmed against the consuming line,
combo_target.py:24: `if np.asarray(seats).shape != (3,) ... raise ValueError('seats')`. WL is the
`seats` argument.

Consequences, both measured rather than assumed:
  * "member cells filled" is undefined for WL; the count must be shape-aware.
  * combo RAISES on non-finite seats (it does not refuse the anchor), so an arm swapping WL could only
    have run at all if NEW's WL is finite throughout the use window. It is: NEW's WL has 3,222
    non-finite entries over 1,074 anchors, **all of them OUTSIDE the use window** (0 inside). So the
    earlier "WL: 3222" was non-finite entries of an (n x 3) seat array, not member cells, and its
    consequence inside the window is zero.
"""
p = "/dev/shm/pnoise_2026-09-24/devices/pnoise_ladder_combo.py"
s = open(p).read()
n0 = len(s)

s = s.replace(
    '''            NA = np.asarray(new_arr, np.float64)
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
    '''            NA = np.asarray(new_arr, np.float64)
            per_symbol = NA.ndim == 2 and NA.shape[1] == len(syms)
            ent = {"grid_entries": int(n_fill), "array_shape": str(NA.shape),
                   "per_symbol_array": bool(per_symbol)}
            if per_symbol:
                n_mem = n_mem_use = 0
                for i in range(len(anchors)):
                    r = rows[i]
                    if r < 0:
                        continue
                    nb = int((~np.isfinite(NA[r][members[i]])).sum())
                    n_mem += nb
                    if anchors[i] >= 1672531200:
                        n_mem_use += nb
                ent.update({"member_cells_all_anchors": n_mem,
                            "member_cells_in_use_window": n_mem_use,
                            "consequential_count": "member_cells_in_use_window",
                            "grid_entries_note": ("whole (anchor x symbol) matrix; dominated by NON-member "
                                                  "cells that are NaN on both sides and never read")})
            else:
                # not per-symbol (WL is (n,3) seat weights; ready is (n,)) -> member cells undefined.
                # combo RAISES on non-finite seats (combo_target.py:24), it does not refuse the anchor,
                # so what matters is whether any non-finite entry falls INSIDE the use window.
                nf = ~np.isfinite(NA)
                inw = np.zeros(NA.shape[0], bool)
                for i in range(len(anchors)):
                    if rows[i] >= 0 and anchors[i] >= 1672531200:
                        inw[rows[i]] = True
                ent.update({"member_cells_in_use_window": None,
                            "consequential_count": "non_finite_entries_inside_use_window",
                            "non_finite_entries_inside_use_window": int(nf[inw].sum()),
                            "non_finite_entries_outside_use_window": int(nf[~inw].sum()),
                            "note": ("member-cell count undefined for a non per-symbol array; combo_target.py:24 "
                                     "RAISES on non-finite seats rather than refusing the anchor, so only the "
                                     "in-window count has any consequence")})
            nc_filled[name] = ent''',
    1)

s = s.replace(
    '''    for nm, v in nc_filled.items():
        print(f"  ncfill {nm}: member cells in use window = {v['member_cells_in_use_window']} "
              f"(consequential)   whole grid = {v['grid_cells']} (mostly non-member, never read)")''',
    '''    for nm, v in nc_filled.items():
        key = v["consequential_count"]
        print(f"  ncfill {nm} {v['array_shape']}: {key} = {v[key]} (consequential)   "
              f"whole-array entries = {v['grid_entries']}")''',
    1)

open(p, "w").write(s)
ok = all(k in s for k in ("per_symbol_array", "non_finite_entries_inside_use_window", "array_shape"))
print("patched:", ok, "bytes", n0, "->", len(s))
