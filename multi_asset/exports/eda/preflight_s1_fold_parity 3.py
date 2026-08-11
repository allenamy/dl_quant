"""S1 PRE-FLIGHT — prove the fold structure and the launch args BEFORE spending GPU hours.

> **创建:** 2026-08-03 16:5x UTC | **Session:** B4-retrain | **状态:** final — 开训前置
> **规格:** team-lead 裁定 2(b) —— 折结构烤在 head_scores 的 `te_rows` 里, 逐位断言
> **作废条件:** `year_folds()` / `WidePanelData.valid_hour` 的定义改变 ⇒ 重跑

Clause (f) asks that the S1 runs differ from the `_5yr` runs in nothing but the panel. There is no
recorded config to diff against (see the UNRECORDED list below), so team-lead's ruling replaces the
missing record with two things that ARE recorded, exactly:

    (b) fold structure  -> `fold_i_head_scores.npz::te_rows` of the frozen run
    (a) architecture    -> the frozen checkpoint's state_dict key set + per-key shapes

This script closes (b) **before** training rather than after, and it splits the claim in two so a
failure names its own cause:

    TEST A   recompute folds on the OLD panel with the args I intend to use
             -> must reproduce the OLD run's te_rows bit-for-bit
             ⇒ validates MY ARGUMENT CHOICE. Fails if I guessed embargo/val_days/year_folds wrong.

    TEST B   recompute folds on the CAUSAL panel with the same args
             -> must also reproduce the OLD run's te_rows bit-for-bit
             ⇒ validates THE PANEL. Fails if the rebuild moved a fold boundary.

Running only B would confound the two: a wrong-args result and a panel-that-shifts-folds result look
identical from inside it. Both must pass, and they answer different questions.

It also FREEZES the architecture baseline (a) to JSON now, so the post-training comparison is made
against a record taken before any new model existed.
"""
from __future__ import annotations

import argparse
import json
import os.path as _p
import sys

import numpy as np

_ROOT = _p.dirname(_p.dirname(_p.dirname(_p.dirname(_p.abspath(__file__)))))
sys.path.insert(0, _ROOT)
from multi_asset.data.wide_panel_dataset import WidePanelData      # noqa: E402
from multi_asset.train.train_wide_harness import year_folds        # noqa: E402

# The args I intend to launch with. Anything not here is a script default and is listed as
# UNRECORDED below — the point is that this dict is the ENTIRE claimed-reproduced surface.
INTENDED = dict(encoder="conformer", n_factor_heads=6, target_horizon=4, xattn=None,
                lam_orth=0.0, pred_smooth_lambda=0.0, year_folds=True, year_folds_from=None,
                embargo_days=8, val_days=30)

# Recorded nowhere in any artifact of the `_5yr` runs — neither the harness JSON (which carries 5
# config fields) nor the checkpoints (pure state_dicts). Script defaults are used and SAID SO.
UNRECORDED = ["lr", "max_epochs", "patience", "seed", "batch_hours", "eval_batch_hours",
              "d_model", "n_blocks", "n_xattn", "w_mag", "dense_train", "aux_mtl", "aux_horizons",
              "qim", "n_quantiles", "multirel", "kill_gates", "enc_lr_mult", "pretrained_encoder"]

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


def te_rows_of(data, folds):
    """Exactly train_fold()'s line 333: te_rows = where(isin(day, te_days) & valid_hour)."""
    return [np.where(np.isin(data.day, f["te"]) & data.valid_hour)[0] for f in folds]


def describe(folds):
    return [dict(year=int(f["year"]), n_tr=len(f["tr"]), n_va=len(f["va"]), n_te=len(f["te"]),
                 tr=[int(f["tr"][0]), int(f["tr"][-1])], va=[int(f["va"][0]), int(f["va"][-1])],
                 te=[int(f["te"][0]), int(f["te"][-1])]) for f in folds]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--old-panel", required=True)
    ap.add_argument("--causal-panel", required=True)
    ap.add_argument("--frozen-run", required=True, help="dir with fold_i_head_scores.npz + models")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    print("=== recorded te_rows from the frozen run ===", flush=True)
    rec = []
    i = 0
    while _p.exists(_p.join(a.frozen_run, f"fold_{i}_head_scores.npz")):
        z = np.load(_p.join(a.frozen_run, f"fold_{i}_head_scores.npz"))
        rec.append(z["te_rows"])
        print(f"  fold {i}: te_rows n={len(rec[-1])}  [{rec[-1].min()} … {rec[-1].max()}]", flush=True)
        i += 1
    ok(len(rec) > 0, "frozen run exposes per-fold te_rows", f"{len(rec)} folds")

    results = {}
    for tag, path in (("A_old", a.old_panel), ("B_causal", a.causal_panel)):
        print(f"\n=== TEST {tag}: recompute folds on {_p.basename(path)} ===", flush=True)
        data = WidePanelData(path=path, target_horizon=INTENDED["target_horizon"],
                             aux_horizons=(1, 24))
        folds = year_folds(data, embargo_days=INTENDED["embargo_days"],
                           val_days=INTENDED["val_days"], year_from=INTENDED["year_folds_from"])
        got = te_rows_of(data, folds)
        for f in describe(folds):
            print(f"  te={f['year']}  tr {f['tr'][0]}..{f['tr'][1]} "
                  f"va {f['va'][0]}..{f['va'][1]} te {f['te'][0]}..{f['te'][1]}  n_te={f['n_te']}d",
                  flush=True)
        ok(len(got) == len(rec), f"[{tag}] fold COUNT matches the frozen run",
           f"{len(got)} vs {len(rec)}")
        allsame = True
        for k in range(min(len(got), len(rec))):
            s = np.array_equal(got[k], rec[k])
            allsame &= s
            ok(s, f"[{tag}] fold {k} te_rows bit-identical to the frozen run",
               "" if s else f"n {len(got[k])} vs {len(rec[k])}; "
                            f"first delta at {int(np.argmax(got[k][:len(rec[k])] != rec[k][:len(got[k])]))}")
        results[tag] = dict(panel=path, folds=describe(folds),
                            te_rows_n=[int(len(x)) for x in got], all_match=bool(allsame))
        del data

    print("\n=== freeze architecture baseline (ruling 2a), taken before any new model exists ===")
    import torch
    arch = {}
    for name in ("wideA_lamorth0_xattn_5yr", "wideA_lamorth0_5yr"):
        d = _p.join(_p.dirname(a.frozen_run), name, "fold_4_model.pt")
        if not _p.exists(d):
            print(f"  (missing {d})", flush=True)
            continue
        sd = torch.load(d, map_location="cpu")
        arch[name] = {k: list(v.shape) for k, v in sd.items()}
        print(f"  {name}: {len(sd)} keys, {sum(int(np.prod(v.shape)) for v in sd.values())} params",
              flush=True)
    ok(len(arch) == 2, "both frozen architectures captured", f"{list(arch)}")

    print("\n" + "=" * 78)
    total = _n_pass + len(_fail)
    print(f"PASS {_n_pass}/{total}" + ("" if not _fail else f"   FAILED: {_fail}"))
    print(f"\nUNRECORDED (script defaults used, NOT claimed reproduced): {UNRECORDED}")
    json.dump(dict(intended_args=INTENDED, unrecorded=UNRECORDED, tests=results,
                   frozen_arch_shapes=arch, n_pass=_n_pass, n_total=total, failed=_fail),
              open(a.out, "w"), indent=1, default=str)
    print(f"record -> {a.out}")
    sys.exit(1 if _fail else 0)


if __name__ == "__main__":
    main()
