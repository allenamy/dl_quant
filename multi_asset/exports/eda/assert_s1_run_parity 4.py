"""S1 POST-TRAINING parity — the two new runs differ from the frozen ones in the panel and nothing else.

> **创建:** 2026-08-03 17:0x UTC | **Session:** B4-retrain | **状态:** final — 训练完成后运行
> **规格:** team-lead 裁定 2(a)(b) + PREREG §3-2 的可执行断言
> **前置:** `preflight_s1_fold_parity.py` 的 JSON(架构基线取于任何新模型存在之前)
> **作废条件:** 架构或折结构的断言口径被重定 ⇒ 同步改

Clause (f) wanted "identical field by field" against a configuration record that does not exist.
team-lead's ruling replaced it with two things that ARE recorded exactly, and this asserts both:

  (a) ARCHITECTURE  new state_dict key set + per-key shapes == frozen counterpart's, per fold.
      Stronger than any config file: d_model / n_blocks / n_heads / K are uniquely determined by
      the shapes, so a shape match forecloses every architectural difference at once. A config file
      only tells you what was *passed*.
  (b) FOLD STRUCTURE  new `te_rows` == frozen `te_rows`, bit-for-bit, per fold. Already proven
      pre-flight on the panels; re-asserted here on what the runs ACTUALLY did, because
      "the loader would produce these folds" and "this run used these folds" are different claims.

  (§3-2) The two NEW runs must differ from each other by EXACTLY the 12 cross-asset-attention keys
      — the same superset relation independently verified on the frozen pair (12 / 0 / 94-shared).

★ WHAT THIS DELIBERATELY DOES NOT DO: judge S1. G1/G2 need the frozen champion RE-MEASURED under
  the same fold protocol (prereg §5-1's `0.079′`), which is a different job on a different artifact.
  σŷ/σy is REPORTED here, not gated: the head scores are not in return units, so the ratio's caliber
  has to be settled before a threshold means anything, and a gate on an unsettled caliber is a
  number wearing a guard's clothes.

Usage:
  python assert_s1_run_parity.py --new-xattn <dir> --new-plain <dir> \
      --frozen-xattn <dir> --frozen-plain <dir> --preflight <preflight.json> --out <out.json>
"""
from __future__ import annotations

import argparse
import json
import os.path as _p
import sys

import numpy as np
import torch

_n_pass, _fail = 0, []


def ok(cond, label, detail=""):
    global _n_pass
    print(("  OK    " if cond else "  FAIL  ") + label + (f"  — {detail}" if detail else ""),
          flush=True)
    if cond:
        _n_pass += 1
    else:
        _fail.append(label)
    return cond


def shapes(path):
    sd = torch.load(path, map_location="cpu")
    return {k: list(v.shape) for k, v in sd.items()}


def n_folds_in(d):
    i = 0
    while _p.exists(_p.join(d, f"fold_{i}_model.pt")):
        i += 1
    return i


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--new-xattn", required=True)
    ap.add_argument("--new-plain", required=True)
    ap.add_argument("--frozen-xattn", required=True)
    ap.add_argument("--frozen-plain", required=True)
    ap.add_argument("--preflight", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    pre = json.load(open(a.preflight))
    rec = {}

    print("=== (a) ARCHITECTURE: per-fold state_dict key set + shapes vs the frozen counterpart ===")
    for tag, newd, frzd, frzname in (
            ("xattn", a.new_xattn, a.frozen_xattn, "wideA_lamorth0_xattn_5yr"),
            ("plain", a.new_plain, a.frozen_plain, "wideA_lamorth0_5yr")):
        nf = n_folds_in(newd)
        ok(nf == 5, f"[{tag}] new run produced 5 folds", f"{nf}")
        # The baseline was frozen BEFORE any new model existed — prefer it over re-reading the
        # frozen checkpoint now, so this comparison cannot be silently retargeted.
        base = pre["frozen_arch_shapes"].get(frzname)
        ok(base is not None, f"[{tag}] pre-flight holds a frozen baseline for {frzname}")
        for i in range(nf):
            s = shapes(_p.join(newd, f"fold_{i}_model.pt"))
            same_keys = set(s) == set(base or {})
            same_shapes = same_keys and all(s[k] == base[k] for k in s)
            ok(same_shapes, f"[{tag}] fold {i} state_dict keys+shapes == frozen baseline",
               "" if same_shapes else
               f"only-new={sorted(set(s) - set(base or {}))[:4]} "
               f"only-frozen={sorted(set(base or {}) - set(s))[:4]} "
               f"shape-diff={[k for k in (set(s) & set(base or {})) if s[k] != base[k]][:4]}")
        rec[f"{tag}_n_folds"] = nf

    print("\n=== (b) FOLD STRUCTURE: te_rows of what the runs ACTUALLY did ===")
    for tag, newd, frzd in (("xattn", a.new_xattn, a.frozen_xattn),
                            ("plain", a.new_plain, a.frozen_plain)):
        for i in range(n_folds_in(newd)):
            zn = np.load(_p.join(newd, f"fold_{i}_head_scores.npz"))
            zf = np.load(_p.join(frzd, f"fold_{i}_head_scores.npz"))
            s = np.array_equal(zn["te_rows"], zf["te_rows"])
            ok(s, f"[{tag}] fold {i} te_rows bit-identical to the frozen run",
               "" if s else f"n {len(zn['te_rows'])} vs {len(zf['te_rows'])}")

    print("\n=== (§3-2) the two NEW runs differ by EXACTLY the 12 attention keys ===")
    sx = shapes(_p.join(a.new_xattn, "fold_4_model.pt"))
    sp = shapes(_p.join(a.new_plain, "fold_4_model.pt"))
    only_x, only_p = sorted(set(sx) - set(sp)), sorted(set(sp) - set(sx))
    shared = set(sx) & set(sp)
    ok(len(only_x) == 12, "exactly 12 keys unique to the xattn run", f"{len(only_x)}")
    ok(len(only_p) == 0, "zero keys unique to the no-attention run", f"{only_p[:4]}")
    ok(all(k.startswith("attn.") for k in only_x), "all 12 are attention keys", f"{only_x[:3]} …")
    ok(all(sx[k] == sp[k] for k in shared),
       f"all {len(shared)} shared keys have identical shapes ⇒ strict superset, "
       f"single variable = attention")
    rec["attn_only_keys"] = only_x

    print("\n=== REPORTED, NOT GATED: dispersion + per-fold sign (caliber note in the header) ===")
    for tag, newd in (("xattn", a.new_xattn), ("plain", a.new_plain)):
        ref = np.load(_p.join(newd, "panel_ref.npz"), allow_pickle=True)
        Y, mem, CL = ref["YR"], ref["member"], ref["CL"]
        per_fold = []
        for i in range(n_folds_in(newd)):
            z = np.load(_p.join(newd, f"fold_{i}_head_scores.npz"))
            te, sc = z["te_rows"], z["scores"]
            ens = np.nanmean(sc[te], axis=2)                      # (n,N) equal-weight head ensemble
            m = mem[te] & CL[te] & np.isfinite(Y[te]) & np.isfinite(ens)
            yy, pp = Y[te][m], ens[m]
            ic = float(np.corrcoef(pp, yy)[0, 1]) if pp.size > 100 else float("nan")
            per_fold.append(dict(fold=i, n=int(m.sum()), pooled_pearson=round(ic, 5),
                                 sd_ratio=round(float(pp.std() / yy.std()), 5)))
            print(f"  [{tag}] fold {i}: n={int(m.sum()):7d}  pooled r={ic:+.5f}  "
                  f"sd(pred)/sd(y)={pp.std()/yy.std():.4f}", flush=True)
        signs = [f["pooled_pearson"] for f in per_fold]
        ok(all(s > 0 for s in signs), f"[{tag}] G4 per-fold sign-consistent (no fold flips sign)",
           f"{[round(s,4) for s in signs]}")
        rec[f"{tag}_per_fold"] = per_fold

    print("\n" + "=" * 78)
    total = _n_pass + len(_fail)
    print(f"PASS {_n_pass}/{total}" + ("" if not _fail else f"   FAILED: {_fail}"))
    json.dump(dict(n_pass=_n_pass, n_total=total, failed=_fail, **rec),
              open(a.out, "w"), indent=1, default=str)
    print(f"record -> {a.out}")
    sys.exit(1 if _fail else 0)


if __name__ == "__main__":
    main()
