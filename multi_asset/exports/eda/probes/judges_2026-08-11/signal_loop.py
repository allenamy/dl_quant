"""Live shadow — item 2: the 4h-anchor signal loop.

For each 4h anchor on the live panel, run the full C1 chain — king/S2 fold_4 inference + funding/SIZE
factor formulas -> combine -> cross-leg netting -> unit-gross market-neutral positions -> write
positions_YYYYMMDD_HH.json (schema identical to the backtest data package's target_weight, so the
partner moves from backtesting the historical data to receiving daily new files with no change).

Open-month funding (c2 dual-curve, per the lead ruling):
  Curve A (provisional, 3-leg): what this feed can actually trade for the open month — funding leg
          dropped, king/S2/SIZE renormalized. This is the live position we emit.
  Curve B (backfilled, 4-leg): recomputed once the funding monthly archive publishes at month-end —
          what a real-time REST feed with live funding would get. Emitted per anchor as a companion.

Dry-run gate: run on the last ~100 FROZEN anchors with fresh fold_4 inference and confirm the
positions reproduce the engine replay's positions for the same anchors (validates inference -> signal
-> netting end to end). CPU-only.
"""
import argparse
import datetime as dt
import glob
import json
import os
import sys

import numpy as np
import pandas as pd
import torch
from scipy.stats import rankdata

torch.backends.mkldnn.enabled = False
REPO = "/mnt/storage/private/work_hsy/quant_research_multi_asset"
MA = REPO + "/multi_asset"
sys.path.insert(0, REPO)
sys.path.insert(0, MA)
import multi_asset.train.train_wide_harness as th  # noqa: E402
th.DEV = torch.device("cpu")
from multi_asset.data.wide_panel_dataset import WidePanelData  # noqa: E402
from multi_asset.model.wide_harness import WideFactorModel, ConformerPanelEncoder  # noqa: E402

WIDE_DL_LIVE = MA + "/exports/live/wide_dl_live.npz"
KING_DIR = MA + "/exports/train/wideA_lamorth0_xattn_5yr"
S2_DIR = MA + "/exports/train/wideA_s2_y24_5yr"
KING_FROZEN = MA + "/exports/eda/king_pred_panel.npz"
S2_FROZEN = MA + "/exports/eda/s2_pred_panel_cl4.npz"
OUT_DIR = MA + "/exports/live/positions"
W = 168


def _model(d):
    m = WideFactorModel(ConformerPanelEncoder(32, d=64, n_blocks=2, kernel_size=15, dropout=0.2),
                        n_factor_heads=6, xattn=True, n_xattn=1, dropout=0.2)
    m.load_state_dict(torch.load(d, map_location="cpu"), strict=True)
    m.eval()
    return m


def _composite(scores_bnk, base):
    """honest z-mean of the 6 heads over `base` coins -> length-|base| vector (or None)."""
    comp = np.zeros(base.size); nk = 0
    for k in range(scores_bnk.shape[1]):
        col = scores_bnk[base, k]
        if np.isfinite(col).all() and col.std() > 1e-12:
            comp += (col - col.mean()) / col.std(); nk += 1
    return comp / nk if nk else None


def infer(data, model, anchor_rows):
    """fold_4 inference on `anchor_rows` with a MEMBER-ONLY mask (no future-Y gate, so live anchors
    with unrealized targets still score). Returns (T,N) composite, finite at member cells of anchors."""
    T, N, C = data.T, data.N, data.C
    out = np.full((T, N), np.nan, np.float32)
    CH = data.CH
    with torch.no_grad():
        for t in anchor_rows:
            if t < W - 1:
                continue
            widx = t + np.arange(-W + 1, 1)
            Xseq = CH[widx].transpose(1, 0, 2)[None]                 # (1,N,W,C)
            Xn = np.clip((np.nan_to_num(Xseq) - data.mu) / data.sd, -10, 10).astype(np.float32)
            mask = data.member[t][None].astype(np.float32)          # member-only (live-safe)
            sc = model(torch.from_numpy(Xn), torch.from_numpy(mask))["factor_scores"][0].numpy()  # (N,6)
            base = np.where(data.member[t])[0]
            comp = _composite(sc, base)
            if comp is not None:
                out[t, base] = comp
    return out


def build_live_preds(verbose=True, fresh_tail=0):
    """king/S2 fold_4 inference on the NEW (live) anchors of wide_dl_live, spliced onto the frozen
    prediction panels -> king_pred_live / s2_pred_live (T,N). fresh_tail>0 ALSO re-infers the last
    `fresh_tail` FROZEN CL4 anchors from scratch (overwriting the spliced frozen values there) so the
    dry-run can compare a genuinely fresh inference against the engine's stitched panel."""
    kf = np.load(KING_FROZEN, allow_pickle=True); sf = np.load(S2_FROZEN, allow_pickle=True)
    frozen_end = int(kf["ts"].astype(np.int64).max())
    preds = {}
    for tag, (Ddir, horizon, emb, frozen, key) in {
            "king": (KING_DIR, 4, 8, kf, "king_pred"),
            "s2":   (S2_DIR, 24, 10, sf, "s2_pred")}.items():
        data = WidePanelData(path=WIDE_DL_LIVE, target_horizon=horizon)
        folds = th.year_folds(data, embargo_days=emb, val_days=30)
        data.set_fold(folds[4]["tr"])
        model = _model(f"{Ddir}/fold_4_model.pt")
        rows = list(np.where(data.ts > frozen_end)[0])
        if fresh_tail > 0:
            cl4_frozen = np.sort(np.where((data.member & data.CL & (data.ts <= frozen_end)[:, None]).any(1))[0])
            rows = list(cl4_frozen[-fresh_tail:]) + rows            # re-infer the frozen tail too
        live = infer(data, model, np.array(sorted(set(int(r) for r in rows))))
        full = np.full((data.T, data.N), np.nan, np.float32)
        full[:frozen[key].shape[0]] = frozen[key]
        m = np.isfinite(live); full[m] = live[m]                    # fresh inference overrides frozen where present
        preds[tag] = full
        if verbose:
            print(f"[preds] {tag}: {int(np.isfinite(live).any(1).sum())} anchors inferred (new + fresh_tail {fresh_tail})", flush=True)
    np.savez(MA + "/exports/live/king_pred_live.npz", ts=data.ts, king_pred=preds["king"])
    np.savez(MA + "/exports/live/s2_pred_live.npz", ts=data.ts, s2_pred=preds["s2"])
    return data.ts


def _panelsource_live():
    from engine.panel_source import PanelSource
    return PanelSource(panel=WIDE_DL_LIVE,
                       king=MA + "/exports/live/king_pred_live.npz",
                       s2=MA + "/exports/live/s2_pred_live.npz")


def _positions(src, anchors, drop_funding_open_month=None):
    """canonical rank+cap SignalChain + 4h-sync netting over `anchors`; returns {t: (m, unit_gross_w)}.
    drop_funding_open_month='YYYY-MM' -> Curve A: the funding leg is zeroed for that month's anchors
    (renormalized to the other 3 legs by the L1/combine machinery)."""
    from engine.signal_chain import SignalChain, DEFAULT_WEIGHTS
    from engine.netting import CrossLegNetting
    weights = dict(DEFAULT_WEIGHTS)
    if drop_funding_open_month is not None:
        weights = {"king": 0.30, "s2": 0.10, "funding": 0.0, "size": 0.30}   # Curve A (3-leg)
    chain = SignalChain(src, weights=weights, funding_mode="rank", pos_cap_pct=99.0)
    net = CrossLegNetting(chain, weights, cost_bps=1.9)
    yr = pd.to_datetime(src.ts[anchors], unit="ms", utc=True).year.to_numpy()
    res = net.run(anchors, src.ts, year_of=yr)
    out = {}
    for (t, m, p) in res["net_positions"]:
        g = float(np.abs(p).sum())
        out[int(t)] = (m, (p / g if g > 1e-12 else p))              # unit gross
    return out


def emit_live(verbose=True):
    """Live: infer + emit positions_YYYYMMDD_HH.json (Curve A 3-leg) + Curve B (4-leg) for the new anchors."""
    os.makedirs(OUT_DIR, exist_ok=True)
    build_live_preds(verbose)
    src = _panelsource_live()
    frozen_end = int(np.load(KING_FROZEN, allow_pickle=True)["ts"].max())
    all_anchors = np.sort(np.where((src.member & src.CL4 & np.isfinite(src.king) & np.isfinite(src.s2)).any(1))[0])
    new_anchors = all_anchors[src.ts[all_anchors] > frozen_end]
    open_month = pd.to_datetime(src.ts[new_anchors].max(), unit="ms", utc=True).strftime("%Y-%m")
    posA = _positions(src, all_anchors, drop_funding_open_month=open_month)   # Curve A (3-leg live)
    posB = _positions(src, all_anchors, drop_funding_open_month=None)         # Curve B (4-leg backfill-ready)
    syms = np.array(src.symbols)
    written = 0
    for t in new_anchors:
        ti = int(t); d = pd.to_datetime(src.ts[ti], unit="ms", utc=True)
        mA, pA = posA[ti]; mB, pB = posB[ti]
        rec = {"anchor_ts_ms": int(src.ts[ti]), "anchor_utc": d.isoformat(), "horizon_h": 4,
               "schema": "target_weight (unit-gross, market-neutral); positive=long negative=short; multiply by gross notional G",
               "curve": {"A_provisional_3leg": {"note": "funding leg dropped for the open month (this feed cannot source it live)",
                                                "positions": {syms[j]: round(float(w), 8) for j, w in zip(mA, pA)}},
                         "B_backfilled_4leg": {"note": "includes funding (open-month funding is a premium-derived proxy; reconcile with the monthly archive at month-end)",
                                               "positions": {syms[j]: round(float(w), 8) for j, w in zip(mB, pB)}}}}
        fn = f"{OUT_DIR}/positions_{d.strftime('%Y%m%d_%H')}.json"
        json.dump(rec, open(fn, "w"), indent=1)
        written += 1
    if verbose:
        print(f"[emit] wrote {written} positions_*.json to {OUT_DIR} (open_month={open_month}, Curve A 3-leg + Curve B 4-leg)", flush=True)
    return written


def dry_run(n=100, verbose=True):
    """Run the loop's fresh fold_4 inference on the last `n` FROZEN anchors and confirm the resulting
    positions reproduce the engine replay's positions for the same anchors."""
    build_live_preds(verbose=False, fresh_tail=n)                    # re-infer the frozen tail from scratch
    src = _panelsource_live()
    from engine.panel_source import PanelSource
    eng = PanelSource()                                              # frozen engine (stitched panels)
    frozen_end = int(np.load(KING_FROZEN, allow_pickle=True)["ts"].max())
    anchors = np.sort(np.where((src.member & src.CL4 & np.isfinite(src.king) & np.isfinite(src.s2)).any(1))[0])
    frozen_anchors = anchors[src.ts[anchors] <= frozen_end]
    warm = frozen_anchors[-(n + 40):]                               # 40-anchor netting warmup (the slow
    anchors = frozen_anchors[-n:]                                   # 24h legs need ~6 anchors to populate)
    live_pos = _positions(src, warm)                                # loop (fresh inference), warm netting
    eng_pos = _positions(eng, np.sort(np.where((eng.member & eng.CL4 & np.isfinite(eng.king) & np.isfinite(eng.s2)).any(1))[0]))
    corrs, l1 = [], []
    for t in anchors:
        ti = int(t)
        if ti not in eng_pos:
            continue
        mL, pL = live_pos[ti]; mE, pE = eng_pos[ti]
        vL = np.zeros(src.N); vL[mL] = pL; vE = np.zeros(src.N); vE[mE] = pE
        both = (vL != 0) | (vE != 0)
        if both.sum() >= 8 and vL[both].std() > 1e-12 and vE[both].std() > 1e-12:
            corrs.append(float(np.corrcoef(vL[both], vE[both])[0, 1]))
            l1.append(float(np.abs(vL - vE).sum()))
    res = dict(n_anchors=len(corrs), median_position_corr=round(float(np.median(corrs)), 5),
               min_position_corr=round(float(np.min(corrs)), 4), median_l1_diff=round(float(np.median(l1)), 5),
               passed=bool(np.median(corrs) >= 0.999 and np.min(corrs) >= 0.99))
    if verbose:
        print(f"[dry-run] {res['n_anchors']} frozen anchors: live-loop vs engine position corr "
              f"median {res['median_position_corr']} min {res['min_position_corr']} "
              f"L1 median {res['median_l1_diff']} -> {'PASS' if res['passed'] else 'FAIL'}", flush=True)
    return res


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--emit", action="store_true")
    ap.add_argument("--n", type=int, default=100)
    a = ap.parse_args()
    if a.dry_run:
        r = dry_run(a.n)
        json.dump(r, open(MA + "/exports/live/signal_loop_dryrun.json", "w"), indent=1)
        sys.exit(0 if r["passed"] else 1)
    if a.emit:
        emit_live()
