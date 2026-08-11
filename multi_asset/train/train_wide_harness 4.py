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
    ConformerPanelEncoder, WideFactorModel, WideQIMModel, WideMultiRelModel,
    FusionTwoTowerEncoder,
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
    if name == "fusion2t":
        # ARM-F2T (E10 治疗①): family split at col 32 — [:32] price/vol zoo -> conformer
        # tower; [32:] slow metrics -> light causal-conv tower; zero-init gated add.
        return FusionTwoTowerEncoder(n_feat, split=32, d=d, n_blocks=n_blocks,
                                     kernel_size=kernel, dropout=dropout)
    raise ValueError(f"unknown encoder arm '{name}' (registered: conformer, fusion2t)")


# --------------------------------------------------------------------------- #
# Walk-forward folds on the hourly-derived day grid (day = hour // 24). Expanding
# train, val carved from the train tail, embargo (>= lookback-days + horizon) between
# train/val end and test start so no forward label overlaps the test window.
# --------------------------------------------------------------------------- #
def year_folds(data, embargo_days=8, val_days=30, min_train_days=120, min_test_days=60, year_from=None):
    """Calendar-year expanding walk-forward (M0-style multi-year replay). Test each year in turn;
    train = all PRIOR-year days (minus embargo + val tail). Uses data.ts to assign each uniq day a
    calendar year. Returns dicts {tr,va,te} of day indices (same format as wf_folds)."""
    import pandas as pd
    yr_of_hour = pd.to_datetime(data.ts, unit="ms", utc=True).year.to_numpy()
    day_year = np.array([int(yr_of_hour[data.day == d][0]) for d in data.uniq_days])
    folds = []
    for Y in sorted(set(day_year.tolist())):
        if year_from is not None and Y < year_from:
            continue                                        # opt-in: skip degenerate early test years
        te = data.uniq_days[day_year == Y]
        tr_all = data.uniq_days[day_year < Y]
        if len(te) < min_test_days or len(tr_all) < min_train_days + val_days + embargo_days:
            continue
        tr_all = tr_all[:-embargo_days]                    # embargo before the year boundary
        tr, va = tr_all[:-val_days], tr_all[-val_days:]
        folds.append(dict(tr=tr, va=va, te=te, year=Y))
    return folds


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


def _ensemble_ic(scores, Ytgt, rows, member, CL):
    """Honest ENSEMBLE rank-IC (0C's selection-bias-free metric): per-ts composite = mean of the
    z-scored head columns, then xsec rank-IC vs Ytgt. The per-fold BEST-head IC is selection-biased
    UPWARD (max over K noisy heads); the deployable signal is the head combination, so this is the
    number that matches 0C's leaderboard scoring."""
    ics = []
    K = scores.shape[2]
    for i in rows:
        base = np.where(member[i] & CL[i] & np.isfinite(Ytgt[i]))[0]
        if base.size < 5:
            continue
        comp = np.zeros(base.size); nk = 0
        for k in range(K):
            col = scores[i, base, k]
            if np.isfinite(col).all() and col.std() > 1e-12:
                comp += (col - col.mean()) / col.std(); nk += 1
        if nk == 0:
            continue
        comp /= nk
        ic = np.corrcoef(rankdata(comp), rankdata(Ytgt[i, base]))[0, 1]
        if np.isfinite(ic):
            ics.append(ic)
    return float(np.mean(ics)) if ics else float("nan")


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


def _parse_pht(spec, K):
    """#46 head->target map. Hard-validated: silent misparse here would train a DIFFERENT
    experiment than the prereg froze."""
    toks = [t.strip() for t in spec.split(",") if t.strip()]
    assert len(toks) == K, f"--per_head_targets needs {K} entries, got {len(toks)}: {toks}"
    assert toks[0] == "4", "h0 must stay YR4 (deploy head; prereg v1-A)"
    assert set(toks) <= {"1", "4", "24", "vol"}, f"unknown target token in {toks}"
    groups = {}
    for i, t in enumerate(toks):
        groups.setdefault(t, []).append(i)
    return groups


def _build_vol_target(npz_path, member):
    """#46 vol-head target: xsec gaussian-rank of FORWARD 24-bar realized vol (nanstd of Y1 rows
    t..t+23). Future data in a LABEL is legitimate; training is dense (member & finite mask),
    the same discipline Y24 dense training already uses. Rank transform => scale-free, no
    per-fold sigma needed."""
    from scipy.special import erfinv
    from numpy.lib.stride_tricks import sliding_window_view
    z = np.load(npz_path, allow_pickle=True)
    Y1 = z["Y1"].astype(np.float32)
    T, N = Y1.shape
    fw = np.full((T, N), np.nan, np.float32)
    with np.errstate(all="ignore"):
        sw = sliding_window_view(Y1, 24, axis=0)            # (T-23, N, 24)
        fw[:sw.shape[0]] = np.nanstd(sw, axis=-1)
    VT = np.full((T, N), np.nan, np.float32)
    for t in range(T):
        msk = member[t] & np.isfinite(fw[t])
        n = int(msk.sum())
        if n >= 20:
            r = np.empty(n)
            r[np.argsort(fw[t, msk])] = np.arange(n)
            VT[t, msk] = (np.sqrt(2.0) * erfinv(2.0 * ((r + 0.5) / n) - 1.0)).astype(np.float32)
    return VT


def _ridge_ens_ic(vsc, tsc, Ytgt, va_rows, te_rows, member, CL, heads, lam=1e-2):
    """#46 judged ensemble (prereg v1-A): xsec-zscore each alpha head per row, ridge-fit the head
    weights on VAL clean rows against Ytgt, apply to TEST, mean xsec rank-IC. The fit never sees
    test — 折内适配. Returns (ic, weights) so the adapter's stability is recordable per fold."""
    def _gather(S, rows):
        Xs, ys = [], []
        for i in rows:
            base = np.where(member[i] & CL[i] & np.isfinite(Ytgt[i]))[0]
            if base.size < 5:
                continue
            cols, ok = [], True
            for k in heads:
                c = S[i, base, k]
                if not np.isfinite(c).all() or c.std() < 1e-12:
                    ok = False
                    break
                cols.append((c - c.mean()) / c.std())
            if ok:
                Xs.append(np.stack(cols, 1))
                ys.append(Ytgt[i, base])
        return Xs, ys
    Xv, yv = _gather(vsc, va_rows)
    if not Xv:
        return float("nan"), None
    X = np.concatenate(Xv)
    yy = np.concatenate(yv)
    H = X.shape[1]
    w = np.linalg.solve(X.T @ X + lam * len(X) * np.eye(H), X.T @ yy)
    Xt, yt = _gather(tsc, te_rows)
    ics = []
    for Xi, yi in zip(Xt, yt):
        ic = np.corrcoef(rankdata(Xi @ w), rankdata(yi))[0, 1]
        if np.isfinite(ic):
            ics.append(ic)
    return (float(np.mean(ics)) if ics else float("nan")), [round(float(x), 4) for x in w]


def _mean_pairwise_headcorr(scores, rows, member, CL, heads):
    """#46 intervention receipt: did the heads actually decorrelate? (aux arm's silent failure:
    the lever moved, the mechanism never happened — recorded so 'ineffective' and 'never fired'
    stay distinguishable.)"""
    cors = []
    for i in rows:
        base = np.where(member[i] & CL[i])[0]
        if base.size < 10:
            continue
        cols = [scores[i, base, k] for k in heads]
        if any((not np.isfinite(c).all()) or c.std() < 1e-12 for c in cols):
            continue
        for a in range(len(cols)):
            for bb in range(a + 1, len(cols)):
                c = np.corrcoef(cols[a], cols[bb])[0, 1]
                if np.isfinite(c):
                    cors.append(abs(c))
    return float(np.mean(cors)) if cors else float("nan")


# --------------------------------------------------------------------------- #
# Train one walk-forward fold.
# --------------------------------------------------------------------------- #
def train_fold(fold_i, fold, data, args, fund_idx, save_dir=None, verbose=True):
    tr_days, va_days, te_days = fold["tr"], fold["va"], fold["te"]
    # K_score = number of scored candidate columns (QIM -> [implied_mean, q50]).
    K = 2 if args.qim else args.n_factor_heads
    pht_groups = (_parse_pht(args.per_head_targets, K)
                  if (args.per_head_targets and not args.qim and not args.multirel) else None)
    if pht_groups and fold_i == 0 and verbose:
        print(f"[#46] per-head targets ACTIVE: {args.per_head_targets} -> groups {pht_groups}",
              flush=True)
    data.set_fold(tr_days)
    if verbose:
        print(f"[fold {fold_i}] days tr={len(tr_days)} va={len(va_days)} te={len(te_days)} | "
              f"resid_sigma={data.resid_sigma:.5f}", flush=True)

    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    enc = build_encoder(args.encoder, data.C, args.d_model, args.n_blocks, KERNEL, DROPOUT)
    if args.pretrained_encoder:
        enc.load_state_dict(torch.load(args.pretrained_encoder, map_location=DEV))
        if fold_i == 0 and verbose:
            print(f"[n1a] loaded pretrained encoder <- {args.pretrained_encoder}", flush=True)
    if args.qim:
        model = WideQIMModel(enc, n_quantiles=args.n_quantiles, xattn=args.xattn,
                             n_xattn=args.n_xattn, dropout=DROPOUT).to(DEV)
        taus = model.head.taus.detach().cpu().tolist()
    else:
        aux_h = tuple(int(x) for x in args.aux_horizons.split(",") if x.strip()) if args.aux_mtl else ()
        if args.multirel:
            lbs = tuple(int(x) for x in args.n1b_lookbacks.split(",") if x.strip())
            ridx = data.ch_names.index("ret_1h") if "ret_1h" in data.ch_names else 20
            model = WideMultiRelModel(enc, n_factor_heads=K, lookbacks=lbs, ret_idx=ridx,
                                      dropout=DROPOUT).to(DEV)
        else:
            model = WideFactorModel(enc, n_factor_heads=K, xattn=args.xattn,
                                    n_xattn=args.n_xattn, dropout=DROPOUT, aux_horizons=aux_h).to(DEV)
    if fold_i == 0 and verbose:
        head = f"QIM(Q={args.n_quantiles}, cols=[imean,q50])" if args.qim else f"K={K}"
        print(f"[model] arm={args.encoder} params={count_params(model):,} "
              f"(d={args.d_model}, blocks={args.n_blocks}, {head}, xattn={args.xattn})", flush=True)
    if args.enc_lr_mult != 1.0:
        _eid = {id(p) for p in model.encoder.parameters()}
        _encp = [p for p in model.parameters() if id(p) in _eid]
        _othp = [p for p in model.parameters() if id(p) not in _eid]
        opt = torch.optim.AdamW([{"params": _encp, "lr": args.lr * args.enc_lr_mult},
                                 {"params": _othp, "lr": args.lr}], weight_decay=WD)
    else:
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
                                   shuffle=(args.pred_smooth_lambda <= 0),
                                   want_aux=(args.aux_mtl or bool(pht_groups)),
                                   train=True):
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
            elif pht_groups:
                # #46: each target-group gets stage2b_loss on its OWN residual target, weighted
                # by its head share so the total gradient scale matches the baseline call.
                # Masks follow the aux discipline: valid_g = member-mask x finite(target_g);
                # nan_to_num only ever multiplies against a 0 in the mask.
                loss = None
                parts = {"rank": 0.0, "mag": 0.0, "orth": 0.0}
                for _tgt, _idxs in pht_groups.items():
                    if _tgt == "4":
                        yg, vg = y, m
                    elif _tgt == "vol":
                        _vt = data.VOLT[b["rows"]]
                        yg = torch.from_numpy(np.nan_to_num(_vt)).to(DEV)
                        vg = m * torch.from_numpy(np.isfinite(_vt).astype(np.float32)).to(DEV)
                    else:
                        _ayn, _amask = b["aux"][int(_tgt)]
                        yg = torch.from_numpy(np.nan_to_num(_ayn)).to(DEV)
                        vg = m * torch.from_numpy(np.asarray(_amask, np.float32)).to(DEV)
                    lg, pg = stage2b_loss(scores[:, :, _idxs], yg, fund, vg,
                                          w_mag=args.w_mag, lam_orth=args.lam_orth)
                    _w = len(_idxs) / float(K)
                    loss = lg * _w if loss is None else loss + lg * _w
                    for _kk in parts:
                        parts[_kk] += pg[_kk] * _w
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
        if pht_groups:
            _cand = [head_ics[k] for k in pht_groups["4"]]
            vIC = float(np.nanmax(_cand)) if np.any(np.isfinite(_cand)) else float("nan")
        else:
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
    ens_ic = _ensemble_ic(tsc, data.Y, te_rows, data.member, data.CL)       # honest (selection-bias-free)
    ens_raw = _ensemble_ic(tsc, data.Yraw, te_rows, data.member, data.CL)
    persist = _head_persistence(tsc, te_rows, data.member, data.CL, best_h)
    ens_ridge_ic, ridge_w, headcorr, vol_sanity = None, None, None, None
    if pht_groups:
        # judged ensemble (prereg v1-A): fit on the BEST checkpoint's val scores, apply to test.
        _vsc_b = predict_scores_wide(model, data, va_days, args.eval_batch_hours, K)
        _va_rows_b = np.where(np.isin(data.day, va_days) & data.valid_hour)[0]
        _alpha = [k for k in range(K) if k not in pht_groups.get("vol", [])]
        ens_ridge_ic, ridge_w = _ridge_ens_ic(_vsc_b, tsc, data.Y, _va_rows_b, te_rows,
                                              data.member, data.CL, _alpha)
        # intervention receipt: pairwise |corr| among alpha heads (did they ACTUALLY diverge?)
        headcorr = _mean_pairwise_headcorr(tsc, te_rows, data.member, data.CL, _alpha)
        # vol-head sanity: does h_vol actually rank future vol? (recorded, never judged)
        if "vol" in pht_groups and hasattr(data, "VOLT"):
            _vh = pht_groups["vol"][0]
            _ics = []
            for i in te_rows:
                bmask = data.member[i] & data.CL[i] & np.isfinite(data.VOLT[i]) \
                        & np.isfinite(tsc[i, :, _vh])
                if bmask.sum() >= 10:
                    _c = np.corrcoef(rankdata(tsc[i, bmask, _vh]),
                                     rankdata(data.VOLT[i, bmask]))[0, 1]
                    if np.isfinite(_c):
                        _ics.append(_c)
            vol_sanity = round(float(np.mean(_ics)), 4) if _ics else None
    if save_dir is not None:
        os.makedirs(save_dir, exist_ok=True)
        np.savez(p.join(save_dir, f"fold_{fold_i}_head_scores.npz"),
                 scores=tsc.astype(np.float32), te_rows=te_rows,
                 te_days=np.asarray(te_days), horizon=data.H)
        torch.save(best_state if best_state is not None else model.state_dict(),
                   p.join(save_dir, f"fold_{fold_i}_model.pt"))
    print(f"[fold {fold_i}] ENSEMBLE resid IC={ens_ic:+.4f} raw={ens_raw:+.4f} (honest) | "
          f"best-head resid={ic_r[best_h]:+.4f} (selection-biased) IR={ir_r[best_h]:.2f} persist={persist:+.3f} | "
          f"per-head={[round(x, 4) if np.isfinite(x) else None for x in ic_r]}", flush=True)
    if pht_groups:
        print(f"[fold {fold_i}] [#46] ridge-ens IC={ens_ridge_ic if ens_ridge_ic is None else round(ens_ridge_ic, 4)} "
              f"w={ridge_w} | alpha-head pairwise|corr|={headcorr if headcorr is None else round(headcorr, 4)} "
              f"| vol-head sanity rankcorr={vol_sanity}", flush=True)
    return {"ensemble_resid_ic": round(float(ens_ic), 4) if np.isfinite(ens_ic) else 0.0,
            "ens_ridge_ic": (round(float(ens_ridge_ic), 4)
                             if (ens_ridge_ic is not None and np.isfinite(ens_ridge_ic)) else None),
            "ridge_w": ridge_w,
            "alpha_headcorr": (round(float(headcorr), 4)
                               if (headcorr is not None and np.isfinite(headcorr)) else None),
            "vol_head_sanity": vol_sanity,
            "ensemble_raw_ic": round(float(ens_raw), 4) if np.isfinite(ens_raw) else 0.0,
            "resid_rank_ic": round(float(ic_r[best_h]), 4) if np.isfinite(ic_r[best_h]) else 0.0,
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
    ap.add_argument("--per_head_targets", type=str, default="",
                    help="#46 (prereg fea334e1 v1-A): comma map, len==K, tokens {1,4,24,vol}; "
                         "h0 must be '4' (deploy head unchanged). Each target-group runs "
                         "stage2b_loss on its OWN residual target; diversification is forced by "
                         "the targets, not begged from a regulariser. Val checkpoint selection = "
                         "max over the '4'-group heads only (same semantics as baseline, minus "
                         "pollution from heads whose job is another horizon).")
    ap.add_argument("--d_model", type=int, default=D_MODEL)
    ap.add_argument("--n_blocks", type=int, default=N_BLOCKS)
    ap.add_argument("--xattn", action="store_true", help="M3: cross-asset attention over members")
    ap.add_argument("--n_xattn", type=int, default=1)
    ap.add_argument("--multirel", action="store_true",
                    help="ARM-N1b: replace single xattn with king-base + zero-init gated "
                         "multi-relation delta (rolling-corr buckets @ --n1b_lookbacks).")
    ap.add_argument("--n1b_lookbacks", type=str, default="24,72,168",
                    help="N1b relation-edge correlation lookbacks in hours (K edges).")
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
    ap.add_argument("--dense_train", action="store_true",
                    help="opt-in: train on ALL overlapping 1h-grid labels (member&finite); "
                         "eval/score/checkpoint stay CL{H} clean. For long horizons where "
                         "CL stride-H starves training (H=24: 1:0.8 -> ~1:20 params:samples).")
    ap.add_argument("--target_npz", type=str, default=None,
                    help="opt-in sidecar replacement primary target (e.g. YR4K king-residual for "
                         "ARM-S1): keys ts, YR4K, KMASK. Input CH still from --wide_dl_path.")
    ap.add_argument("--year_folds_from", type=int, default=None,
                    help="opt-in: with --year_folds, skip test years < this (drop degenerate early "
                         "folds, e.g. ARM-S1 te=2022 whose 2021 train has no king-residual target).")
    ap.add_argument("--pretrained_encoder", type=str, default=None,
                    help="ARM-N1a: init encoder from comovement-pretrained weights (per-fold).")
    ap.add_argument("--enc_lr_mult", type=float, default=1.0,
                    help="ARM-N1a: discriminative LR multiplier for encoder params (e.g. 0.3).")
    ap.add_argument("--max_folds", type=int, default=0,
                    help="cap #folds (0=all); fold0 early-screen uses 1.")
    ap.add_argument("--val_days", type=int, default=30)
    ap.add_argument("--kill_gates", action="store_true", help="opt-in pre-registered fold-0 kill")
    ap.add_argument("--kill_epoch", type=int, default=8)
    ap.add_argument("--kill_ic", type=float, default=0.003)
    ap.add_argument("--save_tag", type=str, default=None)
    ap.add_argument("--tag", type=str, default=None)
    ap.add_argument("--smoke", action="store_true", help="1 fold, few epochs, reduced day span")
    ap.add_argument("--wide_dl_path", type=str, default=None,
                    help="alternate wide_dl.npz (e.g. wide_dl_full.npz for the multi-year replay)")
    ap.add_argument("--year_folds", action="store_true",
                    help="calendar-year expanding walk-forward (M0-style multi-year replay): train "
                         "on all prior years, test each of 2022/2023/2024/2025/2026 in turn.")
    args = ap.parse_args()

    print(f"[env] device={DEV} torch={torch.__version__}", flush=True)
    aux_h = tuple(int(x) for x in args.aux_horizons.split(",") if x.strip())
    t0 = time.time()
    dl_kwargs = {"path": args.wide_dl_path} if args.wide_dl_path else {}
    dl_kwargs["dense_train"] = args.dense_train
    dl_kwargs["target_npz"] = args.target_npz
    data = WidePanelData(target_horizon=args.target_horizon, aux_horizons=aux_h, **dl_kwargs)
    fund_idx = data.ch_names.index("funding_ema") if "funding_ema" in data.ch_names else -1
    print(f"[wide] T={data.T} N={data.N} C={data.C} W={data.W} H={data.H} "
          f"uniq_days={len(data.uniq_days)} valid_hours={int(data.valid_hour.sum())} "
          f"fund_idx={fund_idx} (load {time.time()-t0:.1f}s)", flush=True)
    if fund_idx < 0:
        print("[warn] funding_ema channel not found — orthogonality-vs-funding falls back to vs-0", flush=True)
        fund_idx = 0
    if args.per_head_targets and "vol" in args.per_head_targets:
        from multi_asset.data.wide_panel_dataset import WIDE_DL as _WDL
        _pp = args.wide_dl_path or _WDL
        data.VOLT = _build_vol_target(_pp, data.member)
        print(f"[#46] VOLT (fwd-24 realized-vol gaussian-rank) built from {p.basename(_pp)}: "
              f"finite={np.isfinite(data.VOLT).mean():.3f}", flush=True)

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

    if args.year_folds:
        folds = year_folds(data, embargo_days=args.embargo_days, val_days=args.val_days,
                            year_from=args.year_folds_from)
    else:
        folds = wf_folds(data.uniq_days, n_folds=args.n_folds, test_frac=args.test_frac,
                         embargo_days=args.embargo_days, val_days=args.val_days)
    mode = ", YEAR-FOLDS" if args.year_folds else ""
    print(f"\n===== WIDE HARNESS WALK-FWD ({len(folds)} folds, arm={args.encoder}, K={args.n_factor_heads}, "
          f"YR{args.target_horizon} primary{mode}) =====", flush=True)
    for i, f in enumerate(folds):
        ytag = " [te=%d]" % f["year"] if "year" in f else ""
        print("  fold %d%s: tr %d..%d va %d..%d te %d..%d" % (
            i, ytag, f["tr"][0], f["tr"][-1], f["va"][0], f["va"][-1],
            f["te"][0], f["te"][-1]), flush=True)
    all_m = []
    for i, fold in enumerate(folds):
        if args.max_folds and i >= args.max_folds:
            print(f"[n1a] max_folds={args.max_folds} reached -- stopping (early-screen).", flush=True)
            break
        print(f"\n----- fold {i} -----", flush=True)
        m = train_fold(i, fold, data, args, fund_idx, save_dir=save_dir, verbose=True)
        if m is not None:
            if "year" in fold:
                m["year"] = fold["year"]
            all_m.append(m)
        elif i == 0 and args.kill_gates:
            print("fold 0 KILLED by a pre-registered gate — STOPPING.", flush=True)
            break

    if all_m:
        pooled = dict(
            encoder=args.encoder, n_factor_heads=args.n_factor_heads,
            target_horizon=args.target_horizon, xattn=args.xattn,
            pred_smooth_lambda=args.pred_smooth_lambda,
            per_head_targets=args.per_head_targets or None,
            mean_ens_ridge_ic=(round(float(np.mean([m["ens_ridge_ic"] for m in all_m])), 4)
                               if all(m.get("ens_ridge_ic") is not None for m in all_m) else None),
            per_fold_ens_ridge_ic=[m.get("ens_ridge_ic") for m in all_m],
            mean_alpha_headcorr=(round(float(np.mean([m["alpha_headcorr"] for m in all_m])), 4)
                                 if all(m.get("alpha_headcorr") is not None for m in all_m) else None),
            per_fold_ridge_w=[m.get("ridge_w") for m in all_m],
            per_fold_vol_sanity=[m.get("vol_head_sanity") for m in all_m],
            mean_ensemble_resid_ic=round(float(np.mean([m["ensemble_resid_ic"] for m in all_m])), 4),
            per_fold_ensemble_ic=[m["ensemble_resid_ic"] for m in all_m],
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
