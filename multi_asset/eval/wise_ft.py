"""WiSE-FT for the NX pretrain->fine-tune protocol (Wortsman et al. 2022).

theta(alpha) = (1-alpha)*theta_pretrained + alpha*theta_finetuned, per fold.
Valid ONLY when both endpoints share the input-standardization convention
(P0 stats unification) — interpolating across stats conventions crosses garbage.

Per fold: select alpha on that fold's VAL rank-IC only (clamped to [0.3,0.7],
per the known ID-val-overweights-FT-end caveat), evaluate the selected alpha on
TEST (dense preds saved for nx_battery), and always log the alpha=0.5 reference
arm. sigma-ratio re-checked post-interpolation (weight averaging can shrink
output variance).

Usage:
  python3 multi_asset/eval/wise_ft.py --pre_ckpt .../P1_pretrain/fold_0_model.pt \
      --ft_tag P1v2_y1800 --out_tag WISE_y1800 --horizon 1800 \
      --stats_from .../pretrain_stats.npz
"""
from __future__ import annotations

import argparse
import json
import os
import os.path as p
import sys

import numpy as np
import torch

sys.path.insert(0, p.dirname(p.dirname(p.dirname(p.abspath(__file__)))))
from multi_asset.data.seq_panel_dataset import SeqPanelData  # noqa: E402
from multi_asset.model.temporal_spatial_panel import TemporalSpatialPanelModel  # noqa: E402
import multi_asset.train.train_temporal_spatial as TT  # noqa: E402
from multi_asset.train.train_temporal_spatial import (  # noqa: E402
    fold_day_lists, FOLDS, predict_split, eval_metrics,
)

EXPORT = ("/mnt/storage/private/work_hsy/quant_research_multi_asset/"
          "multi_asset/exports/train")
ALPHAS = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
CLAMP = (0.3, 0.7)


def interp(sd_a, sd_b, alpha):
    return {k: (1 - alpha) * sd_a[k].float() + alpha * sd_b[k].float() for k in sd_a}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pre_ckpt", required=True)
    ap.add_argument("--ft_tag", required=True, help="fine-tuned run save_tag (fold ckpts)")
    ap.add_argument("--out_tag", required=True)
    ap.add_argument("--horizon", type=int, default=1800)
    ap.add_argument("--stats_from", default=None)
    ap.add_argument("--coarse", action="store_true", default=True)
    args = ap.parse_args()

    data = SeqPanelData(target_horizon=args.horizon)
    out_dir = p.join(EXPORT, args.out_tag)
    os.makedirs(out_dir, exist_ok=True)
    np.savez(p.join(out_dir, "panel_ref.npz"), ts=data.ts, day=data.day,
             Y=data.Y, CL=data.CL,
             symbols=np.array([s for s in __import__("multi_asset.data.seq_panel_dataset",
                                                     fromlist=["SYMBOLS"]).SYMBOLS]))
    sd_pre = torch.load(args.pre_ckpt, map_location="cpu")
    report = {}
    for fi, fold in enumerate(FOLDS):
        tr, va, te = fold_day_lists(data.uniq_days, fold)
        data.set_fold(tr)
        if args.stats_from:
            st = np.load(args.stats_from)
            data.mu, data.sd, data.resid_sigma = st["mu"], st["sd"], st["resid_sigma"]
        data._day_cache.clear(); data.enable_cache(True)
        va_rows = np.where(np.isin(data.day, va))[0]
        te_rows = np.where(np.isin(data.day, te))[0]
        mu = torch.from_numpy(data.mu).to(TT.DEV); sdv = torch.from_numpy(data.sd).to(TT.DEV)
        sg = torch.from_numpy(data.resid_sigma).to(TT.DEV)
        offs = torch.arange(-data.W + 1, 1, device=TT.DEV)
        sd_ft = torch.load(p.join(EXPORT, args.ft_tag, f"fold_{fi}_model.pt"),
                           map_location="cpu")
        model = TemporalSpatialPanelModel(data.F, data.S, d=32, n_blocks=2,
                                          kernel_size=15, n_xattn=2,
                                          coarse=args.coarse).to(TT.DEV)
        # val sweep
        val_ic = {}
        for a in ALPHAS:
            model.load_state_dict(interp(sd_pre, sd_ft, a))
            vp = predict_split(model, data, va_rows, mu, sdv, sg, offs,
                               coarse=args.coarse)
            vm = eval_metrics(vp, data.Y, data.CL, data.resid_sigma, clean=False)
            val_ic[a] = round(vm["xsec_rank_ic"], 4)
        best_a = max((a for a in ALPHAS if CLAMP[0] <= a <= CLAMP[1]),
                     key=lambda a: val_ic[a])
        # test at selected alpha + 0.5 reference
        fold_rep = {"val_ic_by_alpha": val_ic, "alpha_sel": best_a}
        for label, a in (("sel", best_a), ("ref05", 0.5)):
            model.load_state_dict(interp(sd_pre, sd_ft, a))
            tp = predict_split(model, data, te_rows, mu, sdv, sg, offs,
                               coarse=args.coarse)
            tm = eval_metrics(tp, data.Y, data.CL, data.resid_sigma, clean=False)
            fold_rep[label] = {"alpha": a, "rank_ic": round(tm["xsec_rank_ic"], 4),
                               "sigma": round(tm["sigma_ratio"], 4)}
            if label == "sel":
                np.savez(p.join(out_dir, f"fold_{fi}_preds.npz"),
                         pred=tp, te_rows=te_rows, te_days=te)
        report[fi] = fold_rep
        print(f"fold {fi}: alpha*={best_a} val={val_ic} "
              f"test_sel={fold_rep['sel']} test_05={fold_rep['ref05']}", flush=True)
    json.dump(report, open(p.join(out_dir, "wise_ft_report.json"), "w"), indent=2)
    print("saved ->", out_dir)


if __name__ == "__main__":
    main()
