"""Do our loss terms actually FIGHT each other? — a diagnostic, run on the dirty AND clean panels.

> **创建:** 2026-08-04 03:5x UTC | **Session:** B4-retrain | **状态:** final — 纯诊断, 不改任何 loss
> **派工:** team-lead 2026-08-04 (用户反问"梯度干扰这个前提对我们真实成立吗" —— 从未测过)
> **作废条件:** `stage2b_loss` 的项构成改变 ⇒ 重跑

THE PREMISE NOBODY MEASURED. Judgements about the loss stack were made against an assumption that
different loss terms interfere. It is cheap to check and was never checked.

★ FIRST, A CORRECTION TO THE PREMISE'S SCOPE. The document that motivated this speaks of "seven
  weighted terms". **Our deployed recipe has THREE, and only TWO carry gradient:**

      total = lr  +  w_mag * lm  +  lam_orth * lo        (xsec_residual_loss.py:186)
              rank      0.3  mag      **0.0** orth        <- lam_orth=0.0 in every run we ship

  So `orth` contributes exactly zero to the update. Its direction is still measured here, labelled
  COUNTERFACTUAL — it answers "would switching it on fight the primary objective?", which is a live
  question next to the lam_orth ruling, but it is NOT part of any interference happening today.

THE DESIGN THAT EARNS ITS KEEP: the same diagnostic on BOTH panels.
  Mechanism under test (team-lead): the leak is a strong, cheap signal; gradient descent spends
  capacity on it first, so terms that need harder/weaker structure get starved. That bites LOSS
  TERMS harder than modules — if the primary can be satisfied cheaply via the leak while auxiliary
  terms cannot, measured "conflict" is inflated by the primary having an unfair energy source.

  PRE-REGISTERED (written before looking):
      hypothesis TRUE  -> dirty panel shows MORE NEGATIVE primary<->aux cosine, and/or LOWER aux
                          gradient-norm share, than clean
      hypothesis FALSE -> the two panels look the same => conflict (if any) is structural and has
                          nothing to do with the leak; the loss question is then closed for good

★★ TWO-ENDED RULERS (TEAM_PROTOCOL §8-b). A cosine of −0.15 cannot be called "conflict" without
   knowing what this instrument reads at each end, so both ends are constructed here:
       +1 end : the SAME term computed twice as independent tensors  -> cosine must be ~ +1
       −1 end : the rank loss on the NEGATED target                  -> cosine must be ~ −1
   If the rulers do not land near ±1, the instrument is wrong and no reading below means anything.

★★★ A UNIT ERROR I MADE AND CAUGHT BEFORE REPORTING — kept because the corrected number is the
    finding. I first measured `sd(scores_raw)/sd(YR_raw)` across runs, read 8–18, and concluded the
    scores were an order of magnitude TOO LARGE and the Huber was saturated in its linear regime.
    **Wrong units.** The Huber compares scores to the **normalised** target `y = YR/resid_sigma`:

        sd(scores_raw)        0.0978
        sd(y_NORMALISED)      1.5485      <- what the loss actually sees
        ratio                 0.0631      <- scores are ~16x TOO SMALL, not too large
        |s-y|: median 0.648, p90 2.158 ; fraction with |s-y| > delta(=2.0) = 0.116

    ⇒ the Huber is ~88% in its QUADRATIC regime, NOT saturated. My mechanism was backwards.
    ⇒ but the corrected direction MATCHES the A2 symptom: scores sit at 6.3% of target scale, i.e.
      severe shrinkage toward the centre — exactly what `mag` ("magnitude calib + anti-collapse +
      pins score scale") exists to prevent. Being quadratic, `mag`'s gradient points OUTWARD and
      scales with the gap; it is not saturating, it is being OUTVOTED. That makes this squarely an
      ENERGY question, which is what the weighted-share reading below measures.

Measurement point: the SHARED TRUNK output `h` (B,N,d) — encoder, plus attention when enabled —
i.e. the last representation every head sees, captured by a forward hook so the model is untouched.
"""
from __future__ import annotations

import argparse
import json
import os.path as _p
import sys

import numpy as np
import torch

sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset")
import multi_asset.train.train_wide_harness as TH  # noqa: E402
from multi_asset.model.wide_harness import WideFactorModel  # noqa: E402
from multi_asset.losses.xsec_residual_loss import (  # noqa: E402
    lambda_rank_ic, masked_huber, orthogonality_penalty)

STAGES = (0, 2, 5)          # epochs at which to measure: early / mid / late
N_EPOCHS = 6
W_MAG = 0.3                 # harness default, confirmed by capturing its own parser (not retyped)


def terms(scores, y, fund, valid_b):
    """The three real terms, plus the two rulers. Each an independent graph node."""
    K = scores.shape[-1]
    lr = torch.stack([lambda_rank_ic(scores[..., k], y, valid_b) for k in range(K)]).mean()
    lm = torch.stack([masked_huber(scores[..., k], y, valid_b) for k in range(K)]).mean()
    lo = orthogonality_penalty(scores, fund, valid_b)
    lr_dup = torch.stack([lambda_rank_ic(scores[..., k], y, valid_b) for k in range(K)]).mean()
    lr_neg = torch.stack([lambda_rank_ic(scores[..., k], -y, valid_b) for k in range(K)]).mean()
    return {"rank": lr, "mag": lm, "orth_COUNTERFACTUAL": lo,
            "RULER_dup(+1)": lr_dup, "RULER_neg(-1)": lr_neg}


def grads_at_trunk(model, hbox, tdict, mask):
    out = {}
    sel = mask > 0.5
    for name, t in tdict.items():
        model.zero_grad(set_to_none=True)
        if hbox["h"].grad is not None:
            hbox["h"].grad = None
        t.backward(retain_graph=True)
        g = hbox["h"].grad
        out[name] = (g[sel].detach().float().flatten().cpu().numpy() if g is not None
                     else np.zeros(1, np.float32))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--panels", nargs="+", required=True, help="label=path")
    ap.add_argument("--out", required=True)
    ap.add_argument("--xattn", action="store_true", default=True)
    a = ap.parse_args()

    rec = {}
    for spec in a.panels:
        label, path = spec.split("=", 1)
        print(f"\n########## {label}  ({_p.basename(path)}) ##########", flush=True)
        torch.manual_seed(TH.SEED); np.random.seed(TH.SEED)
        data = TH.WidePanelData(path=path, target_horizon=4, aux_horizons=(1, 24))
        folds = TH.year_folds(data, embargo_days=8, val_days=30, year_from=None)
        fold = folds[0]                                   # smallest fold — this is a diagnostic
        data.set_fold(fold["tr"])
        fund_idx = data.ch_names.index("funding_ema")
        enc = TH.build_encoder("conformer", data.C, TH.D_MODEL, TH.N_BLOCKS, TH.KERNEL, TH.DROPOUT)
        model = WideFactorModel(enc, n_factor_heads=6, xattn=a.xattn, n_xattn=1,
                                dropout=TH.DROPOUT, aux_horizons=()).to(TH.DEV)
        opt = torch.optim.AdamW(model.parameters(), lr=TH.LR, weight_decay=TH.WD)

        hbox = {"h": None}
        target = model.attn[-1] if a.xattn else model.encoder

        def hook(_m, _i, o):
            t = o[0] if isinstance(o, tuple) else o
            t.retain_grad()
            hbox["h"] = t
        target.register_forward_hook(hook)

        rec[label] = {}
        for ep in range(N_EPOCHS):
            measured = False
            for b in data.iter_batches(fold["tr"], batch_hours=16, rng=np.random.default_rng(0),
                                       shuffle=True, train=True):
                x = torch.from_numpy(b["Xseq"]).to(TH.DEV)
                y = torch.from_numpy(b["y"]).to(TH.DEV)
                m = torch.from_numpy(b["mask"]).to(TH.DEV)
                fund = x[:, :, -1, fund_idx]
                out = model(x, m)
                sc = out["factor_scores"]
                vb = m > 0.5
                td = terms(sc, y, fund, vb)

                if ep in STAGES and not measured:
                    g = grads_at_trunk(model, hbox, td, m)
                    names = list(g)
                    norms = {k: float(np.linalg.norm(v)) for k, v in g.items()}
                    # the ACTUAL update direction as shipped: rank + 0.3*mag (lam_orth = 0)
                    tot = float(np.linalg.norm(g["rank"] + W_MAG * g["mag"]))
                    cos = {}
                    for i in range(len(names)):
                        for j in range(i + 1, len(names)):
                            u, v = g[names[i]], g[names[j]]
                            du, dv = np.linalg.norm(u), np.linalg.norm(v)
                            cos[f"{names[i]} | {names[j]}"] = (float(u @ v / (du * dv))
                                                               if du > 0 and dv > 0 else float("nan"))
                    # ★ SCALE / REGIME, measured in the LOSS'S OWN UNITS (see header note)
                    with torch.no_grad():
                        sv = sc[..., 0][vb]; yv = y[vb]
                        dv = (sv - yv).abs()
                        scale_ratio = float(sv.std() / yv.std().clamp_min(1e-12))
                        lin_frac = float((dv > 2.0).float().mean())
                        med_absdiff = float(dv.median())
                    rec[label][f"epoch{ep}"] = dict(
                        sd_scores_over_sd_target=round(scale_ratio, 5),
                        huber_linear_regime_frac=round(lin_frac, 5),
                        median_abs_diff=round(med_absdiff, 5),
                        grad_norms=norms,
                        weighted_norms={"rank": norms["rank"], "mag": W_MAG * norms["mag"],
                                        "orth_COUNTERFACTUAL": 0.0},
                        aux_share_of_update=(W_MAG * norms["mag"]) / max(
                            norms["rank"] + W_MAG * norms["mag"], 1e-12),
                        cosines=cos, combined_norm=tot)
                    print(f"  [ep{ep}] |g| rank={norms['rank']:.4e} mag={norms['mag']:.4e} "
                          f"orth*={norms['orth_COUNTERFACTUAL']:.4e}", flush=True)
                    print(f"         RULERS  dup(+1)={cos.get('rank | RULER_dup(+1)'):+.4f}   "
                          f"neg(-1)={cos.get('rank | RULER_neg(-1)'):+.4f}", flush=True)
                    print(f"         rank|mag={cos.get('rank | mag'):+.4f}   "
                          f"rank|orth*={cos.get('rank | orth_COUNTERFACTUAL'):+.4f}   "
                          f"mag|orth*={cos.get('mag | orth_COUNTERFACTUAL'):+.4f}", flush=True)
                    measured = True

                loss = td["rank"] + W_MAG * td["mag"]      # lam_orth = 0.0, as shipped
                opt.zero_grad(); loss.backward(); torch.nn.utils.clip_grad_norm_(
                    model.parameters(), 1.0); opt.step()
        del model, data
        torch.cuda.empty_cache()

    print("\n" + "=" * 90)
    print("PRE-REGISTERED READ: dirty MORE NEGATIVE rank|mag, and/or LOWER aux share, => leak-starvation")
    for st in STAGES:
        k = f"epoch{st}"
        row = []
        for lab in rec:
            if k in rec[lab]:
                row.append(f"{lab}: rank|mag {rec[lab][k]['cosines']['rank | mag']:+.4f} "
                           f"aux_share {rec[lab][k]['aux_share_of_update']:.4f}")
        print(f"  [{k}] " + "   |   ".join(row))
    json.dump(rec, open(a.out, "w"), indent=1, default=str)
    print(f"\nrecord -> {a.out}")


if __name__ == "__main__":
    main()
