"""`0.079′` — the frozen champion re-measured under S1's OWN fold protocol, in three calibers.

> **创建:** 2026-08-03 17:1x UTC | **Session:** B4-retrain | **状态:** final — 待 S1 训练结束后跑(GPU 串行)
> **规格:** PREREG §5-1(0.079 不得直接当 walk-forward 及格线, 须同折/同时段/同掩码重测) + team-lead 裁定(owner=B4, 逐折数必须全给)
> **作废条件:** 折结构或 SERVE 口径定义改变 ⇒ 重跑

WHY 0.079 IS NOT ALREADY THE ANSWER. It came from 160 overlapping hourly anchors of live cache, one
regime, under a "close price finite" mask rather than the production top-110. §5-1 forbids using it
as a walk-forward pass line. G1 needs the SAME frozen model measured on the SAME folds, period and
mask as S1 — otherwise S1's number is compared against a differently-constructed quantity, which is
the arithmetic version of comparing two different experiments.

ONE VARIABLE. Per fold k: fold-k's own frozen weights, fold-k's own reconstructed norm, evaluated on
fold-k's te_rows. Across calibers **only `CH[:,:,31]` changes** — the norm is held at the AS-TRAINED
reconstruction in all three, mirroring both audit §9 ("输入只改第 32 通道") and production, where
`inference.py::normalise` uses frozen per-channel constants (audit §11-4). Re-deriving the norm from
each panel would move a second thing and the comparison would stop being about the channel.

★★ THE FIDELITY GATE COMES FIRST, AND NOTHING IS REPORTED UNTIL IT PASSES.
   The frozen runs saved their own `scores` for every fold. So before trusting ANY caliber number,
   this reproduces the TRAIN-caliber scores from scratch — rebuilt norm + rebuilt model + reloaded
   weights — and requires them to match the saved ones. If the reconstruction is faithful there, the
   only thing that differs in the other two runs is the channel I meant to change.
   **Without this gate a wrong norm would still produce three plausible, ordered, entirely fictional
   numbers** — and they would look exactly like a result. `0.079′` is only defined if this passes.

Usage (after S1 training frees the GPU — never concurrently, see [[feedback_no_side_gpu_jobs]]):
  python measure_0079prime_three_caliber.py --run <frozen_run_dir> --as-trained <p> --serve <p> \
      --causal <p> --out <json>
"""
from __future__ import annotations

import argparse
import json
import os.path as _p
import sys

import numpy as np
import torch

_ROOT = _p.dirname(_p.dirname(_p.dirname(_p.dirname(_p.abspath(__file__)))))
sys.path.insert(0, _ROOT)
from multi_asset.data.wide_panel_dataset import WidePanelData          # noqa: E402
from multi_asset.model.wide_harness import WideFactorModel             # noqa: E402
import multi_asset.train.train_wide_harness as TH                      # noqa: E402

K_HEADS = 6
CALIBERS = ("TRAIN", "SERVE", "CAUSAL")

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


def build_frozen_model(ckpt):
    enc = TH.build_encoder("conformer", 32, TH.D_MODEL, TH.N_BLOCKS, TH.KERNEL, TH.DROPOUT)
    model = WideFactorModel(enc, n_factor_heads=K_HEADS, xattn=True, n_xattn=1,
                            dropout=TH.DROPOUT, aux_horizons=()).to(TH.DEV)
    sd = torch.load(ckpt, map_location=TH.DEV)
    model.load_state_dict(sd)      # strict=True: a shape/key mismatch raises rather than half-loads
    model.eval()
    return model


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True, help="frozen champion run dir (fold_k_model.pt + scores)")
    ap.add_argument("--as-trained", required=True, dest="as_trained")
    ap.add_argument("--serve", required=True)
    ap.add_argument("--causal", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--eval-batch-hours", type=int, default=32)
    a = ap.parse_args()

    print(f"[dev] {TH.DEV}", flush=True)
    data = WidePanelData(path=a.as_trained, target_horizon=4, aux_horizons=(1, 24))
    folds = TH.year_folds(data, embargo_days=8, val_days=30, year_from=None)
    ok(len(folds) == 5, "5 year-folds recomputed", f"{[f['year'] for f in folds]}")

    CH = {"TRAIN": data.CH}
    for tag, path in (("SERVE", a.serve), ("CAUSAL", a.causal)):
        CH[tag] = np.load(path, allow_pickle=True)["CH"].astype(np.float32)
        ok(CH[tag].shape == CH["TRAIN"].shape, f"{tag} CH shape matches", f"{CH[tag].shape}")
        j = [str(x) for x in data.ch_names].index("betaadj_ret24")
        others = [c for c in range(CH[tag].shape[2]) if c != j]
        ok(np.array_equal(CH[tag][:, :, others], CH["TRAIN"][:, :, others]),
           f"{tag} differs from TRAIN in ch31 ONLY (other 31 bit-identical)")

    rows = {}
    for k, fold in enumerate(folds):
        print(f"\n===== fold {k} (te={fold['year']}) =====", flush=True)
        data.CH = CH["TRAIN"]
        data.set_fold(fold["tr"])                       # rebuild fold-k norm from AS-TRAINED train rows
        mu, sd_, rs = data.mu.copy(), data.sd.copy(), float(data.resid_sigma)
        model = build_frozen_model(_p.join(a.run, f"fold_{k}_model.pt"))
        saved = np.load(_p.join(a.run, f"fold_{k}_head_scores.npz"))
        te_rows = saved["te_rows"]

        per_cal = {}
        for cal in CALIBERS:
            data.CH = CH[cal]
            data.mu, data.sd, data.resid_sigma = mu, sd_, rs     # norm HELD FIXED across calibers
            tsc = TH.predict_scores_wide(model, data, fold["te"], a.eval_batch_hours, K_HEADS)
            if cal == "TRAIN":
                # ★ THE GATE. Reconstructed pipeline vs what the frozen run itself wrote.
                A, B = tsc[te_rows], saved["scores"][te_rows]
                fin = np.isfinite(A) & np.isfinite(B)
                mx = float(np.abs(A[fin] - B[fin]).max()) if fin.any() else float("inf")
                same_nan = np.array_equal(np.isfinite(A), np.isfinite(B))
                ok(same_nan and mx < 1e-4,
                   f"★★ fold {k} FIDELITY: rebuilt TRAIN scores reproduce the frozen run's saved "
                   f"scores — norm reconstruction + model rebuild are faithful",
                   f"max|Δ|={mx:.3e} nan-pattern-equal={same_nan}")
            ic_r = TH._perhead_ic(tsc, data.Y, te_rows, data.member, data.CL)
            ic_raw = TH._perhead_ic(tsc, data.Yraw, te_rows, data.member, data.CL)
            ens = TH._ensemble_ic(tsc, data.Y, te_rows, data.member, data.CL)
            ens_raw = TH._ensemble_ic(tsc, data.Yraw, te_rows, data.member, data.CL)
            best = int(np.nanargmax(ic_r))
            per_cal[cal] = dict(ensemble_resid_ic=round(float(ens), 5),
                                ensemble_raw_ic=round(float(ens_raw), 5),
                                best_head_resid_ic=round(float(ic_r[best]), 5),
                                best_head=best, n_anchors=int(len(te_rows)),
                                per_head_resid_ic=[round(float(x), 5) for x in ic_r],
                                best_head_raw_ic=round(float(ic_raw[best]), 5))
            print(f"  {cal:7s} ensemble resid={ens:+.5f} raw={ens_raw:+.5f} | "
                  f"best-head resid={ic_r[best]:+.5f}", flush=True)
        rows[fold["year"]] = per_cal
        del model
        torch.cuda.empty_cache()

    print("\n" + "=" * 92)
    print(f"{'fold':>6} | {'TRAIN ens':>10} {'SERVE ens':>10} {'CAUSAL ens':>11} | "
          f"{'TRAIN best':>10} {'SERVE best':>10} {'CAUSAL best':>11}")
    for y, pc in rows.items():
        print(f"{y:>6} | {pc['TRAIN']['ensemble_resid_ic']:>10.5f} "
              f"{pc['SERVE']['ensemble_resid_ic']:>10.5f} {pc['CAUSAL']['ensemble_resid_ic']:>11.5f} | "
              f"{pc['TRAIN']['best_head_resid_ic']:>10.5f} "
              f"{pc['SERVE']['best_head_resid_ic']:>10.5f} "
              f"{pc['CAUSAL']['best_head_resid_ic']:>11.5f}")
    summ = {}
    for cal in CALIBERS:
        e = [rows[y][cal]["ensemble_resid_ic"] for y in rows]
        b = [rows[y][cal]["best_head_resid_ic"] for y in rows]
        summ[cal] = dict(mean_ensemble=round(float(np.mean(e)), 5),
                         mean_best_head=round(float(np.mean(b)), 5),
                         per_fold_ensemble=e, per_fold_best_head=b,
                         all_positive=bool(all(x > 0 for x in e)))
        print(f"  MEAN {cal:7s} ensemble={np.mean(e):+.5f}  best-head={np.mean(b):+.5f}  "
              f"sign-consistent={all(x > 0 for x in e)}")
    print("\n★ 0.079′ = the SERVE column's summary. Per-fold values above are the number that "
          "matters (anti-pattern #19); the mean alone hides a fold that flipped.")

    total = _n_pass + len(_fail)
    print(f"\nPASS {_n_pass}/{total}" + ("" if not _fail else f"   FAILED: {_fail}"))
    json.dump(dict(run=a.run, per_fold=rows, summary=summ, n_pass=_n_pass, n_total=total,
                   failed=_fail,
                   note="0.079' = SERVE mean; fidelity gate must be green or none of this is defined"),
              open(a.out, "w"), indent=1, default=str)
    print(f"record -> {a.out}")
    sys.exit(1 if _fail else 0)


if __name__ == "__main__":
    main()
