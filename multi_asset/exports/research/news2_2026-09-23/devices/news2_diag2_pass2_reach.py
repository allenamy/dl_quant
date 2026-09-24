"""Diagnostic 2 (FREEZE §2 must-report): which SERVED columns does each fix move, and how many cells.

The existing reach receipt (`NC_REACH_GATE.json`) covers PASS 1 (the King block) only, and every arm there
reads 0. Those zeros are BY DESIGN -- D4 patches dlw_features, D7/D8 patch f8, D7/D9 patch combo_stage, and
the King block reads none of them -- so reporting them bare would be read as "these fixes do nothing".
This measures the half that was missing: PASS 2, the served matrices X82 / X89.

Method: for each anchor, run base (no fixes) and each single-family arm, and count the cells that differ,
per matrix and per COLUMN. Arm-to-arm within one derivation generation, so anything the generation has in
common cancels.

  LIMITATION, stated rather than smoothed over: these arms are the 2026-09-23 20:0xZ derivation
  generation (shadow_loop_v3.py 15209f80), NOT the release generation (a68c7a5f). The comparison is
  base <-> base+fix inside that generation, so the generation difference cancels for the DELTA; but the
  absolute column contents are not the release tree's, and this receipt does not claim they are. I have
  not parity-tested this particular generation against the release tree.

Non-vacuity: an arm that moves nothing is reported NO-MEASUREMENT, never PASS, and the number of cells
COMPARED is reported next to the number that differ -- 0 differing out of 0 compared is not agreement.

usage: python news2_diag2_pass2_reach.py <nc_devices> <arms_root> <cfg> <work> <members_hist> <out.json> <out.md> <anchor>...
"""
import hashlib, json, os, sys, time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

ARMS = ["D4", "D5", "D6", "D7", "D8", "D9", "D14"]
MATS = ("X82", "X89", "king_X78")


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 24), b""): h.update(b)
    return h.hexdigest()


def diff_cells(a, b):
    """cells differing, NaN==NaN equal; per-column counts; AND the MAGNITUDE of the change.

    ★ A cell count alone is misleading and would have been here: D4 stores X82 as float32, which moves
    almost every cell of X82 by about 1e-7. Reporting "94,963 of 95,530 cells moved" without magnitude
    makes a pure storage-precision change look like the dominant fix. So every count is paired with
    max|delta|, median|delta| over the CHANGED cells, and the same relative to the base value.
    """
    a, b = np.asarray(a), np.asarray(b)
    if a.shape != b.shape:
        return None
    if a.dtype.kind == "f":
        ne = ~((a == b) | (np.isnan(a) & np.isnan(b)))
    else:
        ne = a != b
    out = {"cells": int(a.size), "cells_different": int(ne.sum()),
           "per_column_cells": ne.sum(axis=0).astype(int).tolist() if ne.ndim == 2 else None}
    if ne.any() and a.dtype.kind == "f":
        da = np.abs(a[ne].astype(np.float64) - b[ne].astype(np.float64))
        da = da[np.isfinite(da)]
        base = np.abs(a[ne].astype(np.float64))
        rel = da / np.maximum(base[np.isfinite(np.abs(a[ne].astype(np.float64)))][:da.size], 1e-12) if da.size else da
        out["magnitude_on_changed_cells"] = {
            "max_abs_delta": (float(da.max()) if da.size else None),
            "median_abs_delta": (float(np.median(da)) if da.size else None),
            "p99_abs_delta": (float(np.percentile(da, 99)) if da.size else None),
            "median_rel_delta": (float(np.median(rel)) if rel.size else None),
            "n_finite_deltas": int(da.size),
            "note": "NaN<->finite flips have no finite delta and are excluded from these percentiles; "
                    "n_finite_deltas vs cells_different shows how many those were"}
    return out


def main():
    nc_dev, arms_root, cfg, work, mh, out_json, out_md = sys.argv[1:8]
    anchors = [int(x) for x in sys.argv[8:]]
    t0 = time.time()
    from news2_nc_adapter import Replay

    def run_tree(tree, tag):
        R = Replay(nc_dev, tree, cfg, os.path.join(work, tag), mh)
        out = {}
        for A in anchors:
            r = R.at(A)
            out[A] = {m: (None if r.get(m) is None else np.asarray(r[m])) for m in MATS}
            out[A]["unavailable"] = r.get("unavailable")
        return out

    base = run_tree(os.path.join(arms_root, "base"), "base")
    rows, unavailable = {}, []
    for arm in ARMS:
        tree = os.path.join(arms_root, arm)
        if not os.path.isdir(tree):
            unavailable.append({"arm": arm, "why": f"arm tree absent: {tree}"})
            continue
        try:
            got = run_tree(tree, arm)
        except Exception as e:
            unavailable.append({"arm": arm, "why": f"{type(e).__name__}: {e}"})
            continue
        per_anchor = {}
        for A in anchors:
            ent = {}
            for m in MATS:
                a, b = base[A][m], got[A][m]
                if a is None or b is None:
                    ent[m] = {"STATUS": "NOT_PRODUCED",
                              "base_unavailable": base[A]["unavailable"], "arm_unavailable": got[A]["unavailable"]}
                    continue
                d = diff_cells(a, b)
                percol = None if d is None else d["per_column_cells"]
                ent[m] = {"cells_compared": int(a.size),
                          "cells_different": (None if d is None else d["cells_different"]),
                          "columns_touched": (None if percol is None else int(sum(1 for c in percol if c))),
                          "n_columns": (None if percol is None else len(percol)),
                          "magnitude_on_changed_cells": (None if d is None else d.get("magnitude_on_changed_cells")),
                          "per_column_cells": percol}
            per_anchor[A] = ent
        tot = {m: sum(per_anchor[A][m].get("cells_different") or 0 for A in anchors) for m in MATS}
        cmp_ = {m: sum(per_anchor[A][m].get("cells_compared") or 0 for A in anchors) for m in MATS}
        cols = {m: sorted({i for A in anchors
                           for i, c in enumerate(per_anchor[A][m].get("per_column_cells") or []) if c})
                for m in MATS}
        rows[arm] = {"per_anchor": per_anchor, "total_cells_different": tot, "total_cells_compared": cmp_,
                     "columns_touched": {m: cols[m] for m in MATS},
                     "n_columns_touched": {m: len(cols[m]) for m in MATS},
                     "VERDICT": ("NO-MEASUREMENT: this fix moved no served cell on these anchors"
                                 if sum(tot.values()) == 0 else "MEASURED")}

    rec = {"device": "news2_diag2_pass2_reach.py", "self_sha256": sha(os.path.abspath(__file__)),
           "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "argv": list(sys.argv),
           "what": "PASS 2 served-column reach per fix (FREEZE section 2 diagnostic 2), base vs base+fix",
           "pass1_note": ("NC_REACH_GATE covers PASS 1 (the King block) and reads 0 for every arm. Those "
                          "zeros are BY DESIGN: D4 patches dlw_features, D7/D8 patch f8, D7/D9 patch "
                          "combo_stage, and the King block reads none of them. They do NOT mean the fixes "
                          "have no effect."),
           "limitation": ("these arms are the 2026-09-23 20:0xZ derivation generation "
                          "(shadow_loop_v3.py 15209f80), not the release generation (a68c7a5f). The "
                          "comparison is base <-> base+fix inside one generation, so the generation "
                          "difference cancels in the delta; the absolute contents are not the release "
                          "tree's and this receipt does not claim they are."),
           "arms_root": arms_root, "anchors": anchors, "matrices": list(MATS),
           "arms": rows, "unavailable": unavailable, "seconds": round(time.time() - t0, 1)}
    json.dump(rec, open(out_json, "w"), indent=1)

    L = [f"<!-- {rec['device']} sha {rec['self_sha256'][:16]} -->", "",
         "### 诊断 2:逐修复项在**服务列**上的作用(PASS 2, base 对 base+该项)", "",
         "> **PASS 1 的那些 0 是设计使然, 不等于「没有作用」。** `NC_REACH_GATE` 只覆盖 King 块, 而 "
         "D4 打的是 dlw_features、D7/D8 打 f8、D7/D9 打 combo_stage —— King 块一个都不读。", "",
         f"> 臂树为 2026-09-23 20:0xZ 那一代派生(`shadow_loop_v3.py` 15209f80), **不是发布代**"
         f"(a68c7a5f)。比较在同一代内 base ↔ base+该项, 所以代际差异在差分中抵消。", "",
         f"锚: {', '.join(str(a) for a in anchors)}", "",
         "> **动格数不是效应量。** D4 把 X82 存成 float32, 于是 X82 几乎每一格都动约 1e-7 —— "
         "只看格数会把一个纯存储精度改动读成作用最大的修复。所以每个格数都配 max|Δ| 与中位 |Δ|。", "",
         "| 修复 | X82 动格/比格 | X82 动列 | X82 幅度 | X89 动格/比格 | X89 动列 | X89 幅度 | King X78 动格 | King 幅度 | 判 |",
         "|---|---|---|---|---|---|---|---|---|---|"]
    for arm in ARMS:
        if arm not in rows:
            L.append(f"| {arm} | " + " | ".join(["**缺测**"] * 8) + " | — |")
            continue
        r = rows[arm]
        d, c, n = r["total_cells_different"], r["total_cells_compared"], r["n_columns_touched"]
        def mag(m):
            vals = [r["per_anchor"][A][m].get("magnitude_on_changed_cells") for A in anchors]
            vals = [v for v in vals if v and v.get("max_abs_delta") is not None]
            if not vals:
                return "—"
            return (f"max {max(v['max_abs_delta'] for v in vals):.2e} / "
                    f"med {np.median([v['median_abs_delta'] for v in vals]):.2e}")
        L.append(f"| {arm} | {d['X82']}/{c['X82']} | {n['X82']}/82 | {mag('X82')} | {d['X89']}/{c['X89']} "
                 f"| {n['X89']}/89 | {mag('X89')} | {d['king_X78']}/{c['king_X78']} | {mag('king_X78')} "
                 f"| {'**NO-MEASUREMENT**' if r['VERDICT'].startswith('NO') else 'MEASURED'} |")
    if unavailable:
        L += ["", "**缺测(具名)**", ""] + [f"- `{u['arm']}`: {u['why']}" for u in unavailable]
    open(out_md, "w").write("\n".join(L) + "\n")
    print(f"DIAG2 arms={len(rows)}/{len(ARMS)} unavailable={len(unavailable)} "
          f"json={sha(out_json)[:16]} md={sha(out_md)[:16]} seconds={rec['seconds']}", flush=True)


if __name__ == "__main__":
    main()
