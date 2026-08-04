"""PRODUCTION FOLD — train on ALL data to the panel's end, no held-out test segment.

> **创建:** 2026-08-04 01:5x UTC | **Session:** B4-retrain | **状态:** final
> **裁定:** team-lead 2026-08-04(生产折批准建; 治理 = 配方认证 + 实盘影子作它的 OOS)
> **作废条件:** `train_wide_harness.train_fold` 的签名或 fold 字典契约改变 ⇒ 同步改

WHY IT EXISTS. Every shipped model so far has been `fold_4` of a walk-forward CV — trained through
2025-11-23 and serving live 253 days later, because nothing in the harness ever retrains on all
data before deployment. Extending the panel moves the TEST window, not the training window, so it
delivers ~nothing to the deployed model. This trains the last fold anyone actually deploys.

★★ WHAT IT GIVES UP, SAID PLAINLY: a production fold has **no out-of-sample segment by
   construction**, so G1/G4 cannot score it. It is NOT "fold 5". Its warrant comes from elsewhere
   (team-lead's ruling):
     (i) RECIPE CERTIFICATION — S1's five walk-forward folds certify this recipe; this applies the
         same recipe to all the data. The parity / lineage / leakage assertions still run.
     (ii) LIVE SHADOW IS ITS OOS — scored in parallel against S1-fold4 for N days after deploy.
   ⇒ Any number this run prints about its own `te` is NOT an OOS score. It does not emit one:
     `te` is EMPTY, and the harness's guarded metrics return NaN/0 rather than a flattering figure.
     A production fold that printed an "IC" would be the most dangerous artifact in the repo.

★ HYPERPARAMETERS ARE TAKEN FROM THE HARNESS'S OWN PARSER, NOT RETYPED HERE. `main()`'s
  `ArgumentParser` is captured live (by intercepting `parse_args`) and asked for its defaults, then
  given the same CLI flags S1 used. Retyping ~20 defaults into a hand-built Namespace is exactly how
  a "same hyperparameters" claim quietly becomes false — and this run has no OOS score that would
  catch it.

Usage:
  python multi_asset/train/train_production_fold.py --panel <p> --save-tag <t> [--xattn] [--val-days 30]
"""
from __future__ import annotations

import argparse
import json
import os
import os.path as _p
import sys

import numpy as np
import torch

sys.path.insert(0, _p.dirname(_p.dirname(_p.dirname(_p.abspath(__file__)))))
import multi_asset.train.train_wide_harness as TH  # noqa: E402


class _Captured(Exception):
    pass


def harness_parser():
    """The REAL parser from `TH.main()`, captured by intercepting its `parse_args` call.

    `main()` constructs the parser and calls `parse_args()` as its first side-effect-free act, so
    interrupting there yields the genuine parser — every option, every default, as S1 saw them.
    """
    holder = {}
    orig = argparse.ArgumentParser.parse_args

    def grab(self, *a, **k):
        holder["p"] = self
        raise _Captured()

    argparse.ArgumentParser.parse_args = grab
    try:
        TH.main()
    except _Captured:
        pass
    finally:
        argparse.ArgumentParser.parse_args = orig
    assert "p" in holder, "failed to capture the harness parser — main() changed shape"
    return holder["p"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", required=True)
    ap.add_argument("--save-tag", required=True, dest="save_tag")
    ap.add_argument("--xattn", action="store_true")
    ap.add_argument("--val-days", type=int, default=30, dest="val_days")
    ap.add_argument("--dry-run", action="store_true", dest="dry_run",
                    help="build the fold and print the captured hyperparameters, then stop before "
                         "training — so the risky part (parser capture, fold edges, val coverage) "
                         "is verified without taking the GPU")
    a = ap.parse_args()

    flags = ["--lam_orth", "0.0", "--year_folds", "--wide_dl_path", a.panel,
             "--save_tag", a.save_tag, "--tag", a.save_tag]
    if a.xattn:
        flags.insert(0, "--xattn")
    args = harness_parser().parse_args(flags)
    print(f"[prod] hyperparameters captured from the harness parser; flags = {flags}", flush=True)

    data = TH.WidePanelData(target_horizon=args.target_horizon,
                            aux_horizons=tuple(int(x) for x in args.aux_horizons.split(",")
                                               if x.strip()),
                            path=args.wide_dl_path, dense_train=args.dense_train,
                            target_npz=args.target_npz)
    fund_idx = data.ch_names.index("funding_ema") if "funding_ema" in data.ch_names else 0

    # ---- the production fold: everything up to the end, last `val_days` held for checkpointing ----
    u = data.uniq_days
    tr, va = u[: -a.val_days], u[-a.val_days:]
    te = np.array([], dtype=u.dtype)          # EMPTY ON PURPOSE — see the header
    fold = dict(tr=tr, va=va, te=te)
    print(f"[prod] tr {tr[0]}..{tr[-1]} ({len(tr)}d) | va {va[0]}..{va[-1]} ({len(va)}d) | te EMPTY",
          flush=True)

    # Sanity: val must contain scorable anchors or checkpoint selection is silently arbitrary.
    va_rows = np.where(np.isin(data.day, va) & data.valid_hour)[0]
    assert len(va_rows) >= 50, (f"val has only {len(va_rows)} scorable anchors — checkpointing would "
                                f"be noise. Widen --val-days or check the panel tail's labels.")
    print(f"[prod] val scorable anchors: {len(va_rows)}", flush=True)

    if a.dry_run:
        keys = ["encoder", "n_factor_heads", "target_horizon", "xattn", "n_xattn", "lam_orth",
                "w_mag", "pred_smooth_lambda", "lr", "max_epochs", "patience", "seed",
                "batch_hours", "eval_batch_hours", "d_model", "n_blocks", "dense_train",
                "aux_mtl", "aux_horizons", "qim", "multirel", "embargo_days", "val_days"]
        print("[prod][dry-run] hyperparameters as captured from the harness parser:")
        for k in keys:
            print(f"      {k:20s} = {getattr(args, k, '<absent>')}")
        print("[prod][dry-run] STOP before training (no GPU touched).", flush=True)
        return

    save_dir = _p.join(TH.EXPORT, a.save_tag)
    os.makedirs(save_dir, exist_ok=True)
    m = TH.train_fold(0, fold, data, args, fund_idx, save_dir=save_dir, verbose=True)

    prov = dict(kind="PRODUCTION_FOLD", panel=a.panel, xattn=bool(a.xattn),
                train_days=[int(tr[0]), int(tr[-1])], n_train_days=int(len(tr)),
                val_days=[int(va[0]), int(va[-1])], n_val_scorable_anchors=int(len(va_rows)),
                test_segment="EMPTY BY CONSTRUCTION",
                oos_score="NONE — this artifact has no out-of-sample score. Warrant = recipe "
                          "certification (S1's 5 walk-forward folds) + live shadow as its OOS.",
                harness_metrics_are_not_oos=m, flags=flags)
    with open(_p.join(save_dir, "PRODUCTION_FOLD_PROVENANCE.json"), "w") as fh:
        json.dump(prov, fh, indent=1, default=str)
    print(f"\n[prod] wrote {save_dir}/PRODUCTION_FOLD_PROVENANCE.json", flush=True)
    print("[prod] ★ this run has NO OOS score. Any IC printed above is not one.", flush=True)


if __name__ == "__main__":
    main()
