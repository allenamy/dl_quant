"""Diagnostic 1 (FREEZE §2 must-report): score-layer IC of the three versions ON THE SAME ANCHORS.

Researcher NEW / NEW_S / NC each produced a King out-of-fold prediction matrix. Their anchor axes are NOT
the same length (NEW 10,321; NEW_S and NC 10,333), so "compare their IC" is only meaningful on the
INTERSECTION -- comparing each version on its own axis would let a difference in which anchors were scored
masquerade as a difference in skill. The intersection is computed, its size reported, and every version is
evaluated on exactly those anchors.

What this is and is not:
  * it is the SCORE layer (King prediction vs the y4s label), not the book layer. Score-layer ordering is
    necessary but not sufficient for book value -- that is a standing result in this project, not a
    hedge invented here.
  * F10 is NOT included: the researcher NEW tree has no top-level F10_OOF (only per-fold directories), so
    a three-way F10 comparison cannot be made from what exists. Named, not silently dropped.

Null control: the same computation with the labels shuffled WITHIN each anchor (fixed RNG). A readout that
cannot produce ~0 on destroyed labels is not measuring what it claims. Reported next to the real numbers.

usage: python news2_diag1_score_ic.py <out.json> <out.md>
"""
import hashlib, json, os, sys, time

import numpy as np
from scipy.stats import spearmanr

NEW = "/workspace/codex_research/QNT-2026-0907/combo_20260923/corrected_combo_v1d"
NEW_S = "/dev/shm/news_2026-09-23"
NC = "/dev/shm/news2_2026-09-23"
LABELS = f"{NEW}/data/dlw_targets.npz"
SEG = {"2023H2": ("2023-06-30T04:00:00Z", "2023-12-31T20:00:00Z"),
       "2024": ("2024-01-01T00:00:00Z", "2024-12-31T20:00:00Z"),
       "2025": ("2025-01-01T00:00:00Z", "2025-12-31T20:00:00Z"),
       "pre2026": ("2023-06-30T04:00:00Z", "2025-12-31T20:00:00Z"),
       "2026": ("2026-01-01T00:00:00Z", "2026-08-31T00:00:00Z")}
MIN_NAMES = 20          # an anchor with fewer comparable names carries no cross-sectional information
RNG_SEED = 20260924


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 24), b""): h.update(b)
    return h.hexdigest()


def ts(s):
    import calendar, datetime
    return calendar.timegm(datetime.datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").timetuple())


def ic_series(P, Y, rows_p, rows_y, rng=None):
    """Per-anchor cross-sectional Spearman on names finite in BOTH. Returns (ics, n_names, n_skipped)."""
    ics, nn, skipped = [], [], 0
    for ip, iy in zip(rows_p, rows_y):
        p, y = P[ip], Y[iy]
        m = np.isfinite(p) & np.isfinite(y)
        if m.sum() < MIN_NAMES:
            skipped += 1
            continue
        yy = y[m]
        if rng is not None:
            yy = yy.copy(); rng.shuffle(yy)          # destroy the pairing, keep the marginal
        r = spearmanr(p[m], yy).statistic
        if np.isfinite(r):
            ics.append(float(r)); nn.append(int(m.sum()))
        else:
            skipped += 1
    return np.array(ics), np.array(nn), skipped


def main():
    out_json, out_md = sys.argv[1:3]
    lab = np.load(LABELS, allow_pickle=True)
    A_lab, Y, syms = lab["E_ts"].astype(np.int64), lab["y4s"], lab["symbols"]

    srcs = {"NEW(researcher)": f"{NEW}/king/KING_OOF.npz",
            "NEW_S": f"{NEW_S}/work/king/KING_OOF.npz",
            "NC": f"{NC}/work/king/KING_OOF.npz"}
    K = {}
    for k, p in srcs.items():
        z = np.load(p)
        assert np.array_equal(z["symbols"], syms), f"{k}: symbol axis differs from the labels"
        K[k] = {"A": z["E_ts"].astype(np.int64), "P": z["P"], "path": p, "sha256": sha(p)}

    common = set(A_lab.tolist())
    for k in K:
        common &= set(K[k]["A"].tolist())
    common = np.array(sorted(common), dtype=np.int64)
    assert common.size, "empty anchor intersection; nothing to compare"
    idx_lab = {int(a): i for i, a in enumerate(A_lab)}
    rows_y = [idx_lab[int(a)] for a in common]

    rec = {"device": "news2_diag1_score_ic.py", "self_sha256": sha(os.path.abspath(__file__)),
           "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "what": "score-layer King IC of the three versions on the SAME anchors (FREEZE section 2 diagnostic 1)",
           "labels": {"path": LABELS, "sha256": sha(LABELS), "field": "y4s"},
           "sources": {k: {"path": v["path"], "sha256": v["sha256"], "n_anchors_own_axis": int(v["A"].size)}
                       for k, v in K.items()},
           "anchor_intersection": {"n": int(common.size),
                                   "first": int(common[0]), "last": int(common[-1]),
                                   "dropped_per_version": {k: int(K[k]["A"].size - common.size) for k in K}},
           "min_names_per_anchor": MIN_NAMES, "null_control_rng_seed": RNG_SEED,
           "f10": {"STATUS": "NOT_COMPARABLE",
                   "why": "the researcher NEW tree has no top-level F10_OOF (only per-fold directories); a "
                          "three-way F10 comparison cannot be built from what exists"},
           "segments": {}}

    for seg, (a, b) in SEG.items():
        m = (common >= ts(a)) & (common <= ts(b))
        sel = common[m]
        if not sel.size:
            rec["segments"][seg] = {"NO_ANCHORS": f"{a}..{b}"}
            continue
        ry = [idx_lab[int(x)] for x in sel]
        row = {"n_anchors": int(sel.size)}
        for k in K:
            idx_p = {int(x): i for i, x in enumerate(K[k]["A"])}
            rp = [idx_p[int(x)] for x in sel]
            ics, nn, skipped = ic_series(K[k]["P"], Y, rp, ry)
            null, _, _ = ic_series(K[k]["P"], Y, rp, ry, rng=np.random.default_rng(RNG_SEED))
            row[k] = {"mean_cs_spearman": (None if not ics.size else float(ics.mean())),
                      "n_anchors_measured": int(ics.size), "n_anchors_skipped": int(skipped),
                      "median_names_per_anchor": (None if not nn.size else int(np.median(nn))),
                      "null_control_mean": (None if not null.size else float(null.mean()))}
        rec["segments"][seg] = row

    json.dump(rec, open(out_json, "w"), indent=1)

    L = [f"<!-- {rec['device']} sha {rec['self_sha256'][:16]} -->", "",
         "### 诊断 1:三版本分数层 King IC(同一批锚)", "",
         f"锚交集 **{rec['anchor_intersection']['n']}** 个"
         f"(各版本自身轴: " + ", ".join(f"{k} {v['n_anchors_own_axis']}" for k, v in rec["sources"].items()) + ")。",
         "", "> 分数层排序是书层价值的**必要非充分**条件 —— 这是本项目的既有结论, 不是此处的免责。",
         "> 零控制 = 把标签在锚内打乱后重算, 应当 ≈ 0; 它与真值并排列出。", "",
         "| 分段 | 锚数 | " + " | ".join(K) + " | 零控制(NC) |", "|---|---|" + "---|" * (len(K) + 1)]
    for seg in SEG:
        r = rec["segments"][seg]
        if "NO_ANCHORS" in r:
            L.append(f"| {seg} | **无锚** | " + " | ".join(["—"] * (len(K) + 1)) + " |")
            continue
        cells = []
        for k in K:
            v = r[k]["mean_cs_spearman"]
            cells.append("n/a" if v is None else f"{v:+.4f}")
        nullv = r["NC"]["null_control_mean"]
        L.append(f"| {seg} | {r['n_anchors']} | " + " | ".join(cells) +
                 f" | {'n/a' if nullv is None else f'{nullv:+.5f}'} |")
    L += ["", f"**F10**: `{rec['f10']['STATUS']}` — {rec['f10']['why']}。"]
    open(out_md, "w").write("\n".join(L) + "\n")
    print(f"DIAG1 anchors={rec['anchor_intersection']['n']} json={sha(out_json)[:16]} md={sha(out_md)[:16]}",
          flush=True)


if __name__ == "__main__":
    main()
