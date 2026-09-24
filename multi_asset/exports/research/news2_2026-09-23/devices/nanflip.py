import json, math
r = json.load(open("/dev/shm/news2_2026-09-23/receipts/DIAG2_PASS2_REACH.json"))
print("arm    matrix     cells_diff  finite_deltas  NaN_flips     max|d|      med|d|     med_rel")
for a, v in r["arms"].items():
    for m in ("X82", "X89", "king_X78"):
        cd = fd = 0
        mx = md = mr = None
        for A, ent in v["per_anchor"].items():
            e = ent[m]
            cd += e.get("cells_different") or 0
            g = e.get("magnitude_on_changed_cells")
            if g:
                fd += g.get("n_finite_deltas") or 0
                mx = max(mx or 0.0, g.get("max_abs_delta") or 0.0)
                md = g.get("median_abs_delta")
                mr = g.get("median_rel_delta")
        if cd:
            mxs = "n/a" if mx is None else "%.3e" % mx
            mds = "n/a" if md is None else "%.3e" % md
            mrs = "n/a" if mr is None else "%.3e" % mr
            print("%-6s %-10s %10d %14d %10d %11s %11s %11s" % (a, m, cd, fd, cd - fd, mxs, mds, mrs))
