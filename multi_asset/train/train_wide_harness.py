"""Engine A — BACKBONE-AGNOSTIC wide-universe factor-mining TRAINER (USER direction 2026-07-11).

Trains the pluggable `WideFactorModel` (encoder -> [opt cross-asset attn] -> K orthogonal factor
heads) on the hourly wide panel (`wide_dl.npz`, T hours x N=140 coins x C channels). The whole
program is encoder-agnostic: swap the PanelEncoder arm, keep the SAME dataset / residual target /
K-head+orthogonality objective / persistence penalty / kill gates / factory export = a fair race,
one leaderboard (incremental orthogonal rank-IC over [funding+zoo] + persistence + execution econ).

Target = YR{H}, the per-ts cross-sectionally demeaned forward return residualised on the 8-col
[funding+zoo] baseline (BASELINE in build_wide_dl). So a head's rank-IC vs YR{H} IS its
incremental-over-carry content — the deployment gate, measured directly.

Objective (encoder-agnostic, per batch of prediction hours):
    stage2b_loss(scores (B,N,K), target_resid (B,N), funding (B,N), valid (B,N))
      = mean_k LambdaRankIC(head_k, YR)        # rank term = our headline trade metric, per head
      + w_mag * mean_k Huber(head_k, YR)       # magnitude calib + anti-collapse + pins score scale
      + lam_orth * [ mean pairwise |xsec corr among heads| + mean_k |corr(head_k, funding)| ]
    (+ optional P1b prediction-smoothness penalty lam_smooth * mean[(score_t - score_{t-1})^2] over
     CONTIGUOUS-hour batches — attacks drift-regime weight churn; raw target unchanged.)

Checkpoint / kill: sigma_ratio is meaningless for arbitrary-scale factor scores, so we checkpoint on
MAX-over-heads val cross-sectional rank-IC vs YR (a collapsed head has undefined/NaN rank-IC -> the
rank-IC gate IS the collapse guard, same as train_temporal_spatial STAGE-2B). Kill gates opt-in.

Export (factory format for 0C's leaderboard): per fold `fold_{i}_head_scores.npz` (scores (T,N,K) +
te hours/days) + a global `panel_ref.npz` (ts, day, symbols, Yraw raw fwd ret, YR residual target,
member, CL, funding, baseline_cols) so 0C scores each head as a candidate factor on the >=H
non-overlap clean grid vs the carry baseline.

Usage:
    python3 multi_asset/train/train_wide_harness.py --smoke
    python3 multi_asset/train/train_wide_harness.py --encoder conformer --n_factor_heads 6 \
        --target_horizon 4 --save_tag wideA_conformer_ref --tag conformer_ref
"""
from __future__ import annotations

import argparse
import json
import os
import os.path as p
import sys
import time

import numpy as np
import torch
from scipy.stats import rankdata

sys.path.insert(0, p.dirname(p.dirname(p.dirname(p.abspath(__file__)))))
from multi_asset.data.wide_panel_dataset import WidePanelData  # noqa: E402
from multi_asset.model.wide_harness import (  # noqa: E402
    ConformerPanelEncoder, WideFactorModel, WideQIMModel,
)
from multi_asset.model.temporal_spatial_panel import count_params  # noqa: E402
from multi_asset.losses.xsec_residual_loss import (  # noqa: E402
    stage2b_loss, masked_pinball, lambda_rank_ic,
)

EXPORT = ("/mnt/storage/private/work_hsy/quant_research_multi_asset/"
          "multi_asset/exports/train")
DEV = "cuda" if torch.cuda.is_available() else "cpu"

# --- recipe (reference arm; M1 capacity sweep varies d/blocks) ---
D_MODEL = 64
N_BLOCKS = 2
KERNEL = 15
DROPOUT = 0.2
LR = 6e-4
WD = 0.01
MAX_EPOCHS = 20
PATIENCE = 4
SEED = 42


# --------------------------------------------------------------------------- #
# Pluggable ENCODER factory — the single swap point for paradigm arms.
# Every arm returns a PanelEncoder: forward(x (B,N,W,C), mask (B,N)) -> h (B,N,d).
# --------------------------------------------------------------------------- #
def build_encoder(name, n_feat, d, n_blocks, kernel, dropout):
    if name == "conformer":
        return ConformerPanelEncoder(n_feat, d=d, n_blocks=n_blocks,
                                     kernel_size=kernel, dropout=dropout)
    raise ValueError(f"unknown encoder arm '{name}' (registered: conformer)")


# --------------------------------------------------------------------------- #
# Walk-forward folds on the hourly-derived day grid (day = hour // 24). Expanding
# train, val carved from the train tail, embargo (>= lookback-days + horizon) between
# train/val end and test start so no forward label overlaps the test window.
# --------------------------------------------------------------------------- #
def wf_folds(uniq, n_folds=3, test_frac=0.45, embargo_days=8, val_days=30):
    D = len(uniq)
    test_total = int(D * test_frac)
    test_start0 = D - test_total
    block = max(1, test_total // n_folds)
    folds = []
    for k in range(n_folds):
        ts0 = test_start0 + k * block
        ts1 = (test_start0 + (k + 1) * block) if k < n_folds - 1 else D
        tr_end = ts0 - embargo_days
        va0 = tr_end - val_days
        if va0 < 30 or ts1 <= ts0:
            continue
        folds.append(dict(tr=uniq[:va0], va=uniq[va0:tr_end], te=uniq[ts0:ts1]))
    return folds


# --------------------------------------------------------------------------- #
# Streaming predict of the K factor-head scores over a set of days -> (T,N,K).
# --------------------------------------------------------------------------- #
def predict_scores_wide(model, data, split_days, batch_hours, K):
    model.eval()
    out = np.full((data.T, data.N, K), np.nan, np.float32)
    with torch.no_grad():
        for b in data.iter_batches(split_days, batch_hours=batch_hours, rng=None, shuffle=False):
            x = torch.from_numpy(b["Xseq"]).to(DEV)
            m = torch.from_numpy(b["mask"]).to(DEV)
            sc = model(x, m)["factor_scores"].detach().cpu().numpy()   # (B,N,K)
            mm = b["mask"] > 0.5
            out[b["rows"]] = np.where(mm[:, :, None], sc, np.nan)
    return out


def _perhead_ic(scores, Ytgt, rows, member, CL, want_ir=False):
    """Per-head mean cross-sectional rank-IC of the (T,N,K) scores vs Ytgt (T,N) over the given
    prediction hours, restricted to member & CL & finite. Optionally the IC-IR too."""
    K = scores.shape[2]
    per = [[] for _ in range(K)]
    for i in rows:
        base = member[i] & CL[i] & np.isfinite(Ytgt[i])
        if base.sum() < 5:
            continue
        for k in range(K):
            v = base & np.isfinite(scores[i, :, k])
            if v.sum() >= 5:
                ic = np.corrcoef(rankdata(scores[i, v, k]), rankdata(Ytgt[i, v]))[0, 1]
                if np.isfinite(ic):
                    per[k].append(ic)
    ic_mean = [float(np.mean(x)) if x else np.nan for x in per]
    if not want_ir:
        return ic_mean
    ic_ir = [float(np.mean(x) / np.std(x) * np.sqrt(len(x)))
             if (len(x) > 1 and np.std(x) > 1e-9) else np.nan for x in per]
    return ic_mean, ic_ir


def _head_persistence(scores, rows, member, CL, k):
    """Lag-1 persistence of head k: mean over assets of corr(score_t, score_{t+1}) on the sorted
    clean prediction hours (a proxy for weight-autocorr / turnover; higher = more tradeable)."""
    rows = np.sort(rows)
    N = scores.shape[1]
    cors = []
    for a in range(N):
        v = np.array([i for i in rows if member[i, a] and CL[i, a] and np.isfinite(scores[i, a, k])])
        if v.size < 20:
            continue
        s = scores[v, a, k]
        if s[:-1].std() > 1e-9 and s[1:].std() > 1e-9:
            c = np.corrcoef(s[:-1], s[1:])[0, 1]
            if np.isfinite(c):
                cors.append(c)
    return float(np.mean(cors)) if cors else float("nan")


# --------------------------------------------------------------------------- #
# Train one walk-forward fold.
# --------------------------------------------------------------------------- #
def train_fold(fold_i, fold, data, args, fund_idx, save_dir=None, verbose=True):
    tr_days, va_days, te_days = fold["tr"], fold["va"], fold["te"]
    # K_score = number of scored candidate columns (QIM -> [implied_mean, q50]).
    K = 2 if args.qim else args.n_factor_heads
    data.set_fold(tr_days)
    if verbose:
        print(f"[fold {fold_i}] days tr={len(tr_days)} va={len(va_days)} te={len(te_days)} | "
              f"resid_sigma={data.resid_sigma:.5f}", flush=True)

    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    enc = build_encoder(args.encoder, data.C, args.d_model, args.n_blocks, KERNEL, DROPOUT)
    if args.qim:
        model = WideQIMModel(enc, n_quantiles=args.n_quantiles, xattn=args.xattn,
                             n_xattn=args.n_xattn, dropout=DROPOUT).to(DEV)
        taus = model.head.taus.detach().cpu().tolist()
    else:
        aux_h = tuple(int(x) for x in args.aux_horizons.split(",") if x.strip()) if args.aux_mtl else ()
        model = WideFactorModel(enc, n_factor_heads=K, xattn=args.xattn,
                                n_xattn=args.n_xattn, dropout=DROPOUT, aux_horizons=aux_h).to(DEV)
    if fold_i == 0 and verbose:
        head = f"QIM(Q={args.n_quantiles}, cols=[imean,q50])" if args.qim else f"K={K}"
        print(f"[model] arm={args.encoder} params={count_params(model):,} "
              f"(d={args.d_model}, blocks={args.n_blocks}, {head}, xattn={args.xattn})", flush=True)
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=WD)
    rng = np.random.default_rng(args.seed)

    best_val, best_state, best_epoch, bad = -1e9, None, -1, 0
    for ep in range(args.max_epochs):
        model.train()
        t_ep = time.time()
        ep_loss = ep_rank = ep_mag = ep_orth = ep_sm = 0.0
        nb = 0
        # pred-smooth needs contiguous-hour batches (shuffle off); else shuffle for SGD.
        for b in data.iter_batches(tr_days, batch_hours=args.batch_hours, rng=rng,
                                   shuffle=(args.pred_smooth_lambda <= 0), want_aux=args.aux_mtl):
            x = torch.from_numpy(b["Xseq"]).to(DEV)        # (B,N,W,C) standardized
            y = torch.from_numpy(b["y"]).to(DEV)           # (B,N) normalized YR residual
            m = torch.from_numpy(b["mask"]).to(DEV)        # (B,N)
            fund = x[:, :, -1, fund_idx]                   # (B,N) funding at pred hour (affine ok)
            out = model(x, m)
            scores = out["factor_scores"]                  # (B,N,K) or (B,N,2) for QIM
            if args.qim:
                valid = (m > 0.5) & torch.isfinite(y)
                loss = masked_pinball(out["quantiles"], y, valid, taus=taus)
                parts = {"rank": 0.0, "mag": float(loss.detach()), "orth": 0.0}
            else:
                loss, parts = stage2b_loss(scores, y, fund, m,
                                           w_mag=args.w_mag, lam_orth=args.lam_orth)
            sm_val = 0.0
            if args.pred_smooth_lambda > 0 and not args.qim and scores.shape[0] > 1:
                dq = scores[1:] - scores[:-1]              # (B-1,N,K) consecutive-hour diff
                vp = (m[1:] * m[:-1]).unsqueeze(-1)        # (B-1,N,1) valid both hours
                sm = (dq * dq * vp).sum() / vp.sum().clamp_min(1.0)
                loss = loss + args.pred_smooth_lambda * sm
                sm_val = float(sm.detach())
            if args.aux_mtl and "aux" in b and "aux_scores" in out:
                for h, (ayn, amask) in b["aux"].items():
                    ay = torch.from_numpy(ayn).to(DEV)
                    av = torch.from_numpy(amask).to(DEV) > 0.5
                    loss = loss + 0.3 * lambda_rank_ic(out["aux_scores"][h], ay, av)
            opt.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
            ep_loss += float(loss.item()); ep_rank += parts["rank"]; ep_mag += parts["mag"]
            ep_orth += parts["orth"]; ep_sm += sm_val; nb += 1
        ep_loss /= max(nb, 1); ep_rank /= max(nb, 1); ep_mag /= max(nb, 1)
        ep_orth /= max(nb, 1); ep_sm /= max(nb, 1)

        # val: MAX-over-heads xsec rank-IC vs YR residual (the incremental-over-carry gate).
        vsc = predict_scores_wide(model, data, va_days, args.eval_batch_hours, K)
        va_rows = np.where(np.isin(data.day, va_days) & data.valid_hour)[0]
        head_ics = _perhead_ic(vsc, data.Y, va_rows, data.member, data.CL)
        vIC = float(np.nanmax(head_ics)) if np.any(np.isfinite(head_ics)) else float("nan")
        if verbose:
            print(f"  ep{ep:2d} ({time.time()-t_ep:.0f}s) loss={ep_loss:.4f} "
                  f"(rank={ep_rank:.4f} mag={ep_mag:.4f} orth={ep_orth:.4f}"
                  f"{f' sm={ep_sm:.4f}' if args.pred_smooth_lambda > 0 else ''})  "
                  f"val head-ICs={[round(x, 4) if np.isfinite(x) else None for x in head_ics]} "
                  f"maxIC={vIC:+.4f}", flush=True)
        # pre-registered kill (opt-in): fold-0 val maxIC below floor after warmup -> dead config.
        if args.kill_gates and fold_i == 0 and ep >= args.kill_epoch:
            if not np.isfinite(vIC) or vIC < args.kill_ic:
                print(f"  KILL(fold0-floor): val maxIC={vIC:+.4f} < {args.kill_ic} @ep{ep}", flush=True)
                return None
        score = vIC if np.isfinite(vIC) else -1e9
        if score > best_val:
            best_val, best_epoch, bad = score, ep, 0
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
        else:
            bad += 1
            if bad >= args.patience:
                if verbose:
                    print(f"  early stop ep{ep} (best ep{best_epoch} maxIC={best_val:+.4f})", flush=True)
                break

    if best_state is not None:
        model.load_state_dict(best_state)

    # test export: per-head scores + IC on the >=H non-overlap clean grid (CL already >=H-spaced).
    tsc = predict_scores_wide(model, data, te_days, args.eval_batch_hours, K)
    te_rows = np.where(np.isin(data.day, te_days) & data.valid_hour)[0]
    ic_r, ir_r = _perhead_ic(tsc, data.Y, te_rows, data.member, data.CL, want_ir=True)      # vs residual
    ic_raw = _perhead_ic(tsc, data.Yraw, te_rows, data.member, data.CL)                     # vs raw fwd ret
    best_h = int(np.nanargmax(ic_r)) if np.any(np.isfinite(ic_r)) else 0
    persist = _head_persistence(tsc, te_rows, data.member, data.CL, best_h)
    if save_dir is not None:
        os.makedirs(save_dir, exist_ok=True)
        np.savez(p.join(save_dir, f"fold_{fold_i}_head_scores.npz"),
                 scores=tsc.astype(np.float32), te_rows=te_rows,
                 te_days=np.asarray(te_days), horizon=data.H)
        torch.save(best_state if best_state is not None else model.state_dict(),
                   p.join(save_dir, f"fold_{fold_i}_model.pt"))
    print(f"[fold {fold_i}] per-head test rank-IC (>=H CL) resid={[round(x, 4) if np.isfinite(x) else None for x in ic_r]} "
          f"| best head {best_h} IC={ic_r[best_h]:+.4f} IR={ir_r[best_h]:.2f} "
          f"raw={ic_raw[best_h]:+.4f} persist={persist:+.3f}", flush=True)
    return {"resid_rank_ic": round(float(ic_r[best_h]), 4) if np.isfinite(ic_r[best_h]) else 0.0,
            "resid_ic_ir": round(float(ir_r[best_h]), 3) if np.isfinite(ir_r[best_h]) else 0.0,
            "raw_rank_ic": round(float(ic_raw[best_h]), 4) if np.isfinite(ic_raw[best_h]) else 0.0,
            "best_head": best_h, "persistence": round(persist, 4) if np.isfinite(persist) else None,
            "per_head_resid_ic": [round(x, 4) if np.isfinite(x) else None for x in ic_r],
            "best_epoch": best_epoch,
            "best_val_maxic": round(best_val, 4) if best_val > -1e8 else None,
            "n_params": count_params(model)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--encoder", default="conformer", help="pluggable arm (conformer=#1 reference)")
    ap.add_argument("--n_factor_heads", type=int, default=6, help="K orthogonal factor heads (<=6 iron rule)")
    ap.add_argument("--qim", action="store_true",
                    help="ARM-QIM: quantile-implied-mean head (trade implied mean vs q50) instead "
                         "of K factor heads. Loss = multi-quantile pinball. scores=[imean,q50].")
    ap.add_argument("--n_quantiles", type=int, default=25, help="ARM-QIM quantile grid size (odd)")
    ap.add_argument("--aux_mtl", action="store_true",
                    help="aux-MTL lever: 1h/24h aux heads on the shared trunk (w=0.3 rank loss) to "
                         "regularise the encoder; primary YR4 heads unchanged, aux not shipped.")
    ap.add_argument("--target_horizon", type=int, default=4, help="primary YR horizon (1/4/24)")
    ap.add_argument("--aux_horizons", type=str, default="1,24",
                    help="aux horizons available in the dataset (loaded but MTL heads are a later arm)")
    ap.add_argument("--d_model", type=int, default=D_MODEL)
    ap.add_argument("--n_blocks", type=int, default=N_BLOCKS)
    ap.add_argument("--xattn", action="store_true", help="M3: cross-asset attention over members")
    ap.add_argument("--n_xattn", type=int, default=1)
    ap.add_argument("--w_mag", type=float, default=0.3, help="stage2b magnitude-Huber weight")
    ap.add_argument("--lam_orth", type=float, default=1.0, help="stage2b orthogonality-penalty weight")
    ap.add_argument("--pred_smooth_lambda", type=float, default=0.0,
                    help="P1b persistence penalty over CONTIGUOUS-hour batches (0=off=clean bar)")
    ap.add_argument("--lr", type=float, default=LR)
    ap.add_argument("--max_epochs", type=int, default=MAX_EPOCHS)
    ap.add_argument("--patience", type=int, default=PATIENCE)
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--batch_hours", type=int, default=16,
                    help="prediction hours / train batch (N=140 coins/hr -> ~2240 seqs @16; "
                         "48 OOMs a 24GB 3090 on backward)")
    ap.add_argument("--eval_batch_hours", type=int, default=32)
    ap.add_argument("--n_folds", type=int, default=3)
    ap.add_argument("--test_frac", type=float, default=0.45)
    ap.add_argument("--embargo_days", type=int, default=8)
    ap.add_argument("--val_days", type=int, default=30)
    ap.add_argument("--kill_gates", action="store_true", help="opt-in pre-registered fold-0 kill")
    ap.add_argument("--kill_epoch", type=int, default=8)
    ap.add_argument("--kill_ic", type=float, default=0.003)
    ap.add_argument("--save_tag", type=str, default=None)
    ap.add_argument("--tag", type=str, default=None)
    ap.add_argument("--smoke", action="store_true", help="1 fold, few epochs, reduced day span")
    args = ap.parse_args()

    print(f"[env] device={DEV} torch={torch.__version__}", flush=True)
    aux_h = tuple(int(x) for x in args.aux_horizons.split(",") if x.strip())
    t0 = time.time()
    data = WidePanelData(target_horizon=args.target_horizon, aux_horizons=aux_h)
    fund_idx = data.ch_names.index("funding_ema") if "funding_ema" in data.ch_names else -1
    print(f"[wide] T={data.T} N={data.N} C={data.C} W={data.W} H={data.H} "
          f"uniq_days={len(data.uniq_days)} valid_hours={int(data.valid_hour.sum())} "
          f"fund_idx={fund_idx} (load {time.time()-t0:.1f}s)", flush=True)
    if fund_idx < 0:
        print("[warn] funding_ema channel not found — orthogonality-vs-funding falls back to vs-0", flush=True)
        fund_idx = 0

    save_dir = p.join(EXPORT, args.save_tag) if args.save_tag else None
    # global panel_ref for 0C's factory scoring (raw + residual targets + masks + funding).
    if save_dir is not None:
        os.makedirs(save_dir, exist_ok=True)
        funding = np.full((data.T, data.N), np.nan, np.float32)
        funding[:] = data.CH[:, :, fund_idx]
        np.savez(p.join(save_dir, "panel_ref.npz"),
                 ts=data.ts, day=data.day, symbols=data.symbols,
                 Yraw=data.Yraw, YR=data.Y, member=data.member, CL=data.CL,
                 funding=funding, resid_sigma=np.float32(1.0), horizon=data.H,
                 ch_names=np.array(data.ch_names, dtype=object))
        print(f"[export] panel_ref -> {save_dir}/panel_ref.npz", flush=True)

    if args.smoke:
        u = data.uniq_days
        span = u[:min(len(u), 160)]                     # reduced span for a fast smoke
        n = len(span); tr = span[:int(n * 0.65)]
        va = span[int(n * 0.65):int(n * 0.8)]; te = span[int(n * 0.8):]
        print(f"\n===== SMOKE: {n} days -> tr={len(tr)} va={len(va)} te={len(te)}, 3 epochs =====", flush=True)
        args.max_epochs = 3; args.patience = 99
        m = train_fold(0, dict(tr=tr, va=va, te=te), data, args, fund_idx,
                       save_dir=save_dir, verbose=True)
        print("\n----- SMOKE RESULT -----", flush=True)
        print(json.dumps(m, indent=2), flush=True)
        return

    folds = wf_folds(data.uniq_days, n_folds=args.n_folds, test_frac=args.test_frac,
                     embargo_days=args.embargo_days, val_days=args.val_days)
    print(f"\n===== WIDE HARNESS WALK-FWD ({len(folds)} folds, arm={args.encoder}, K={args.n_factor_heads}, "
          f"YR{args.target_horizon} primary) =====", flush=True)
    for i, f in enumerate(folds):
        print(f"  fold {i}: tr {f['tr'][0]}..{f['tr'][-1]} va {f['va'][0]}..{f['va'][-1]} "
              f"te {f['te'][0]}..{f['te'][-1]}", flush=True)
    all_m = []
    for i, fold in enumerate(folds):
        print(f"\n----- fold {i} -----", flush=True)
        m = train_fold(i, fold, data, args, fund_idx, save_dir=save_dir, verbose=True)
        if m is not None:
            all_m.append(m)
        elif i == 0 and args.kill_gates:
            print("fold 0 KILLED by a pre-registered gate — STOPPING.", flush=True)
            break

    if all_m:
        pooled = dict(
            encoder=args.encoder, n_factor_heads=args.n_factor_heads,
            target_horizon=args.target_horizon, xattn=args.xattn,
            pred_smooth_lambda=args.pred_smooth_lambda,
            mean_resid_rank_ic=round(float(np.mean([m["resid_rank_ic"] for m in all_m])), 4),
            mean_resid_ic_ir=round(float(np.nanmean([m["resid_ic_ir"] for m in all_m])), 3),
            mean_raw_rank_ic=round(float(np.mean([m["raw_rank_ic"] for m in all_m])), 4),
            mean_persistence=round(float(np.nanmean([m["persistence"] for m in all_m
                                                     if m["persistence"] is not None])), 4),
            per_fold_resid_ic=[m["resid_rank_ic"] for m in all_m],
            per_fold_raw_ic=[m["raw_rank_ic"] for m in all_m],
            per_fold=all_m, n_params=all_m[0]["n_params"],
        )
        os.makedirs(EXPORT, exist_ok=True)
        tag = args.tag or f"wide_{args.encoder}"
        out = p.join(EXPORT, f"wide_harness_{tag}.json")
        with open(out, "w") as fh:
            json.dump(pooled, fh, indent=2)
        print("\n===== POOLED =====", flush=True)
        print(json.dumps({k: v for k, v in pooled.items() if k != "per_fold"}, indent=2), flush=True)
        print(f"\nsaved -> {out}", flush=True)


if __name__ == "__main__":
    main()
