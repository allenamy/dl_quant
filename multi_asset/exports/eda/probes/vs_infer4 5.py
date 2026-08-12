"""B4 — re-infer the CORRFUND-caliber runs (S1F-xattn king, clean s2) under one ch31 arm.

> created 2026-08-04 07:xx UTC | Session: B4-retrain | status: final
> why: the clean-s2 book needs prediction arrays for two runs that have none. `vs_infer{,2,3}.py`
>      cover the as_trained/causal panels only; this adds the fifth-generation panel.

★ WHY A NEW FILE AND NOT AN EDIT. jpline authorisation this session is ADD-ONLY. The recipe below
  is copied from `vs_infer.py` (the s2 half) and `vs_infer3.py` (the ch31-arm half) rather than
  imported, because those scripts hard-code their panel at module scope. Every line that differs
  from them is a REGISTRY entry, not a change in method — the anchor grid, the composite base, the
  per-fold frozen normalisation and the head-compositing are byte-for-byte the same procedure.

★★ THE CALIBER THIS FILE EXISTS TO KEEP STRAIGHT. Both runs here trained on
   `wide_dl_full_corrfund_causal_v1.npz` (CAUSAL ch31 x corrected funding) — verified by
   `panel_ref.funding == c6a1f9e9e5a0` for both, and by PRODUCTION_FOLD provenance for the two
   production folds. Pairing them is the ONLY caliber-consistent book; pairing either with
   `wideA_*_causal_v1` (funding `dbaae69795db`) puts two funding calibers in one book.

★★★ SCORE UNDER **SERVE**, NOT UNDER THE TRAINING ARM. The models learned on causal ch31, but the
   live panel ends at the signal row and `np.convolve(..., "same")` zero-fills the 11 future taps,
   so production hands the model a **trailing-13** window. Reading the book at its training arm
   would report a caliber live never sees. (SERVE is also causal — "causal" and "the caliber it was
   trained on" are independent properties, and confusing them is how 0.079 and 0.041 were mistaken
   for each other. See PANELS_MANIFEST section 3.)

★★★ THE FIRST VERSION OF THIS FILE FAILED ITS OWN GATE, AND THAT IS THE POINT. It built the fold
   normalisation window as `uniq_days[day_year < te_year]` — every prior day — which is what
   `vs_infer{,2,3}.py` do. The frozen scores did not reproduce: max|d| = 2.6e-2 / 6.4e-2 against a
   wrong-weights control of 5.6e-1, i.e. the "correct" rebuild sat only ~10x better than deliberately
   loading the wrong model. The real training window is `TH.year_folds(embargo_days, val_days=30)`,
   which carves the val block and the embargo off the END of the train span before computing mu/sd.
   `measure_0079prime_three_caliber.py` uses it and reaches max|d| = 0.000e+00 on 5/5 folds.
   ⇒ This file now takes the fold construction from that script rather than re-deriving it.
   ⇒ **AND THE SAME DEFECT IS PRESENT, UNGATED, IN `vs_infer{,2,3}.py`** — none of them compares its
     rebuild against the frozen scores, so nothing there can go red. Every existing
     `/tmp/vs*_pred_*.npz` was built on the wide window. Whether that matters for a BOOK is a
     separate question and is measured, not assumed: the composite z-scores each head across the
     cross-section, so any affine part of a norm error cancels. See `--compare-legacy`.

★ FIDELITY GATE, and a partner that must go RED. `--fidelity` re-scores each fold's own `te_rows`
  under the run's native arm (CAUSAL) and compares against the frozen `fold_k_head_scores.npz`.
  A green gate says the normalisation reconstruction and the model rebuild are faithful; without it
  every number downstream comes from a rebuild nobody checked. `--selftest` deliberately loads the
  WRONG fold's weights and requires the gate to FAIL — because a gate observed only in green cannot
  be distinguished from a gate that is blind (protocol section 8-e).

READ-ONLY on all panels and run dirs; writes only /tmp.
"""
import argparse
import glob
import os
import sys
import time

import numpy as np
import pandas as pd
import torch

REPO = "/mnt/storage/private/work_hsy/quant_research_multi_asset"
MA = REPO + "/multi_asset"
sys.path.insert(0, REPO)
torch.backends.mkldnn.enabled = False
torch.set_num_threads(int(os.environ.get("NT", "6")))

ap = argparse.ArgumentParser()
ap.add_argument("--run", required=True, choices=["s1f", "s2c"])
ap.add_argument("--arm", required=True, choices=["TRAIN", "SERVE", "CAUSAL"])
ap.add_argument("--bs", type=int, default=24)
ap.add_argument("--device", default="cpu", help="cpu|cuda — the FIDELITY RESIDUAL IS DEVICE-DEPENDENT: the frozen scores were produced on the training device, and float32 conv arithmetic differs between backends at ~1e-4. Run the gate on the training device before reading a residual as an error.")
ap.add_argument("--fidelity", action="store_true", help="gate the rebuild against frozen head scores")
ap.add_argument("--selftest", action="store_true", help="prove the fidelity gate can go RED")
ap.add_argument("--cap", type=int, default=400, help="anchors per fold used by the fidelity gate")
ap.add_argument("--nfold", type=int, default=2, help="folds used by the fidelity gate")
ap.add_argument("--legacy-norm", action="store_true", dest="legacy_norm",
                help="deliberately use the vs_infer{,2,3} window (for the comparison only)")
ap.add_argument("--native-mask", action="store_true", dest="native_mask",
                help="use the training mask (CL) instead of the densified one; REQUIRED for the "
                     "fidelity gate, because the mask is a model input")
ap.add_argument("--embargo", type=int, default=8, help="train/val embargo; the gate IDENTIFIES it")
ap.add_argument("--compare-legacy", action="store_true", dest="cmplegacy",
                help="quantify what the vs_infer{,2,3} window costs, at score AND composite level")
args = ap.parse_args()

# horizon/xattn/K read off the runs' own harness JSONs (both: K=6, xattn=True)
REG = {
    "s1f": dict(dir=MA + "/exports/train/wideA_lamorth0_xattn_5yr_corrfund_v1", H=4, K=6, xattn=True),
    "s2c": dict(dir=MA + "/exports/train/wideA_s2_y24_5yr_corrfund_v1", H=24, K=6, xattn=True),
}
cfg = REG[args.run]
FULL = MA + "/exports/wide_dl_full_corrfund_causal_v1.npz"

from multi_asset.data.wide_panel_dataset import WidePanelData          # noqa: E402
from multi_asset.model.wide_harness import WideFactorModel             # noqa: E402
import multi_asset.train.train_wide_harness as TH                      # noqa: E402

t00 = time.time()
zf = np.load(FULL, allow_pickle=True)
member = zf["MEMBER110"]
CL4 = zf["CL4"]
YR4 = zf["YR4"]
ts = zf["ts"].astype(np.int64)
yr = pd.to_datetime(ts, unit="ms", utc=True).year.to_numpy()
T, N = member.shape
CH = np.array(zf["CH"])
chn = [str(c) for c in zf["ch_names"]]
i_b = chn.index("betaadj_ret24")
assert i_b == 31, i_b

arms = np.load("/tmp/vs_ch31_arms.npz")
# The corrfund panel was rebuilt on top of causal_v1 (funding swap only), so its native ch31 MUST
# still be the causal arm. This assertion is the cheapest available proof that the fifth-generation
# panel did not silently pick up a different ch31 while its funding was being changed.
assert np.array_equal(arms["CAUSAL"], CH[:, :, i_b]), \
    "corrfund_causal_v1 ch31 != CAUSAL arm — the panel is not what its name claims"
CH[:, :, i_b] = arms[args.arm]
print("[%s/%s] ch31 arm installed (native=CAUSAL verified)" % (args.run, args.arm), flush=True)

AUX = tuple(x for x in (1, 24) if x != cfg["H"])       # portrait default "1,24" minus the target
d = WidePanelData(path=FULL, target_horizon=cfg["H"], aux_horizons=AUX)
FOLDS = TH.year_folds(d, embargo_days=args.embargo, val_days=30, year_from=None)
print("[%s] year_folds=%s embargo=%d aux=%s"
      % (args.run, [f["year"] for f in FOLDS], args.embargo, AUX), flush=True)
ok = np.arange(T) >= (d.W - 1)
d.valid_hour = np.zeros(T, bool)
d.valid_hour[ok] = CL4[ok].any(1)                 # CL4 anchor grid for BOTH models (vs_infer.py)
# ★★ THE DENSIFY MASK MUST NOT TOUCH `d.CL`. `vs_infer.py` sets `d.CL = member` for s2 so that
#    inference covers the CL4 grid rather than s2's sparse daily rows. But `d.set_fold()` derives the
#    fold's mu/sd from rows selected via `d.CL`, so mutating it silently re-normalises on a different
#    population. Measured: with the mutation, s2c's fidelity gate fails at BOTH embargo 8 and 10
#    (max|d| 3.2e-2 / 3.2e-2 — near-identical, which is itself the tell that embargo was not the
#    variable). `vs_infer.py` never noticed because it has no gate. Keep the densified mask as a
#    SEPARATE array used only for the model input mask.
# The densified mask is a DELIBERATE DEVIATION, and it is a MODEL INPUT, not just a row filter:
# `mm` is passed into the forward pass and the cross-asset attention normalises over it, so widening
# it from CL24 to `member` changes the scores. That is why s2c's gate failed at 3.2e-2 under BOTH
# embargos while s1f (which does not densify) passed at 1.2e-7 — the variable was never the embargo.
# ⇒ FIDELITY IS GATED ON THE NATIVE MASK (reproduces training); the densified product is the
#   coverage-extended one and IS NOT COVERED BY THE GATE. Two different functions, said out loud.
DENSIFY = (args.run == "s2c") and not args.native_mask
CL_INFER = member.copy() if DENSIFY else d.CL
day_year = np.array([int(yr[d.day == dd][0]) for dd in d.uniq_days])
mask_mat = (member & CL_INFER & np.isfinite(d.Y))
print("[%s] mask = %s (%d cells)" % (args.run, "DENSIFIED (member)" if DENSIFY else "native CL",
                                     int(mask_mat.sum())), flush=True)
base_mask = member & CL4 & np.isfinite(YR4)       # composite base (king_pred_panel / densify recipe)
offs = np.arange(-d.W + 1, 1)
K = cfg["K"]


def build():
    enc = TH.build_encoder("conformer", 32, TH.D_MODEL, TH.N_BLOCKS, TH.KERNEL, TH.DROPOUT)
    return WideFactorModel(enc, n_factor_heads=K, xattn=cfg["xattn"], n_xattn=1,
                           dropout=TH.DROPOUT, aux_horizons=())


folds = sorted(glob.glob(cfg["dir"] + "/fold_*_head_scores.npz"),
               key=lambda x: int(x.split("fold_")[1].split("_")[0]))
assert folds, cfg["dir"]


def load_fold(fi, wrong=False, legacy=False):
    """Restore fold fi's frozen normalisation + weights.

    `legacy=True` reproduces the `vs_infer{,2,3}.py` window (all prior days, no val/embargo
    carve-out) so the two can be measured against each other rather than argued about.
    `wrong=True` loads a DIFFERENT fold's weights — the negative control for the fidelity gate."""
    f = cfg["dir"] + "/fold_%d_head_scores.npz" % fi
    te = np.load(f)["te_rows"]
    te_year = int(np.bincount(yr[te] - yr[te].min()).argmax() + yr[te].min())
    if legacy:
        d.set_fold(d.uniq_days[day_year < te_year])
    else:
        fold = [x for x in FOLDS if int(x["year"]) == te_year]
        assert len(fold) == 1, (te_year, [x["year"] for x in FOLDS])
        d.set_fold(fold[0]["tr"])
    model = build()
    src = fi if not wrong else (fi + 1) % len(folds)
    sd_path = cfg["dir"] + "/fold_%d_model.pt" % src
    miss, unexp = model.load_state_dict(torch.load(sd_path, map_location="cpu"), strict=False)
    assert not miss and not unexp, (args.run, fi, miss, unexp)   # silent key mismatch = another model
    model.eval()
    model.to(args.device)
    return te, te_year, model, d.mu.copy(), d.sd.copy()


def raw_scores(model, mu, sd, rows, bs):
    """Model factor_scores on `rows`, no compositing — the quantity the frozen file stores."""
    out = np.full((len(rows), N, K), np.nan, np.float32)
    with torch.no_grad():
        for b0 in range(0, len(rows), bs):
            bh = rows[b0:b0 + bs]
            X = CH[bh[:, None] + offs[None, :]].transpose(0, 2, 1, 3)
            Xn = np.clip((np.nan_to_num(X) - mu) / sd, -10, 10).astype(np.float32)
            mm = mask_mat[bh].astype(np.float32)
            sc = model(torch.from_numpy(Xn).to(args.device),
                       torch.from_numpy(mm).to(args.device))["factor_scores"].cpu().numpy()
            out[b0:b0 + len(bh)] = np.where(mm[:, :, None] > 0.5, sc, np.nan)
    return out


def fidelity(wrong=False, nfold=None, cap=None, legacy=False):
    """Compare rebuilt scores against the frozen ones on the run's own te_rows."""
    assert args.arm == "CAUSAL", "fidelity gate is only defined at the run's native arm"
    assert not DENSIFY, ("fidelity gate requires --native-mask: the densified mask is a model input, "
                         "so gating with it compares the rebuild against a different function")
    nfold = args.nfold if nfold is None else nfold
    cap = args.cap if cap is None else cap
    worst = 0.0
    for fi in range(min(nfold, len(folds))):
        te, te_year, model, mu, sd = load_fold(fi, wrong=wrong, legacy=legacy)
        rows = te[:cap]
        got = raw_scores(model, mu, sd, rows, args.bs)
        want = np.load(cfg["dir"] + "/fold_%d_head_scores.npz" % fi)["scores"][rows]
        both = np.isfinite(got) & np.isfinite(want)
        nanpat = np.array_equal(np.isfinite(got), np.isfinite(want))
        dmax = float(np.abs(got[both] - want[both]).max()) if both.any() else np.inf
        worst = max(worst, dmax)
        print("   fold%d te=%d n=%d  max|d|=%.3e  nan-pattern-equal=%s"
              % (fi, te_year, len(rows), dmax, nanpat), flush=True)
        del model
    return worst


def composite_rows(model, mu, sd, rows):
    """The book's per-anchor composite: z-score each head across the base set, then average.
    Any AFFINE part of a norm error cancels here, which is precisely why the score-level max|d|
    cannot be read directly as a book-level error."""
    sc = raw_scores(model, mu, sd, rows, args.bs)
    out = np.full((len(rows), N), np.nan, np.float64)
    for j, t in enumerate(rows):
        base = np.where(base_mask[t])[0]
        if base.size < 5:
            continue
        comp = np.zeros(base.size)
        nk = 0
        for k in range(sc.shape[2]):
            col = sc[j, base, k]
            if np.isfinite(col).all() and col.std() > 1e-12:
                comp += (col - col.mean()) / col.std()
                nk += 1
        if nk:
            out[j, base] = comp / nk
    return out


if args.cmplegacy:
    from scipy.stats import rankdata, spearmanr
    print("\n=== WHAT THE vs_infer{,2,3} NORM WINDOW COSTS ===", flush=True)
    print("  (score-level max|d| is NOT the book-level error: the composite z-scores each head", flush=True)
    print("   across the cross-section, so any affine part of a norm error cancels)", flush=True)
    Y = zf["YR%d" % cfg["H"]] if ("YR%d" % cfg["H"]) in zf.files else YR4
    for fi in range(min(args.nfold, len(folds))):
        te, te_year, m_ok, mu_ok, sd_ok = load_fold(fi, legacy=False)
        rows = te[:args.cap]
        c_ok = composite_rows(m_ok, mu_ok, sd_ok, rows)
        del m_ok
        te2, _, m_lg, mu_lg, sd_lg = load_fold(fi, legacy=True)
        c_lg = composite_rows(m_lg, mu_lg, sd_lg, rows)
        del m_lg
        both = np.isfinite(c_ok) & np.isfinite(c_lg)
        dmax = float(np.abs(c_ok[both] - c_lg[both]).max()) if both.any() else np.nan
        rho = float(spearmanr(c_ok[both], c_lg[both]).statistic) if both.sum() > 10 else np.nan
        ic_ok, ic_lg = [], []
        for j, t in enumerate(rows):
            v = np.isfinite(c_ok[j]) & np.isfinite(c_lg[j]) & np.isfinite(Y[t])
            if v.sum() >= 5:
                ic_ok.append(np.corrcoef(rankdata(c_ok[j, v]), rankdata(Y[t, v]))[0, 1])
                ic_lg.append(np.corrcoef(rankdata(c_lg[j, v]), rankdata(Y[t, v]))[0, 1])
        print("  fold%d te=%d  n=%d | composite max|d|=%.3e  spearman(ok,legacy)=%.6f | "
              "xsec rank-IC  correct=%+.5f  legacy=%+.5f  delta=%+.5f"
              % (fi, te_year, len(rows), dmax, rho, np.mean(ic_ok), np.mean(ic_lg),
                 np.mean(ic_lg) - np.mean(ic_ok)), flush=True)
    print("\n  ⇒ read the rank-IC delta, not the max|d|: the delta is what a book would feel.",
          flush=True)
    sys.exit(0)


if args.selftest:
    print("\n=== SELFTEST: the fidelity gate must go RED on deliberately wrong weights ===", flush=True)
    print(" [A] correct weights (expect PASS):", flush=True)
    good = fidelity(wrong=False)
    print(" [B] WRONG fold's weights (expect FAIL):", flush=True)
    bad = fidelity(wrong=True)
    ok_green = good < 1e-4
    ok_red = bad > 1e-3
    print("\n  correct max|d| = %.3e -> %s" % (good, "PASS" if ok_green else "FAIL"))
    print("  wrong   max|d| = %.3e -> %s" % (bad, "RED (gate is sighted)" if ok_red else
                                             "STILL GREEN — GATE IS BLIND, DO NOT TRUST IT"))
    if not (ok_green and ok_red):
        print("\n*** SELFTEST FAILED — emitting nothing ***")
        sys.exit(1)
    print("\n=== SELFTEST PASSED: green on correct weights, red on wrong ones ===")
    sys.exit(0)

if args.fidelity:
    print("\n=== FIDELITY GATE (rebuild vs frozen head scores, native arm) ===", flush=True)
    worst = fidelity()
    if worst >= 1e-4:
        print("*** FIDELITY FAILED max|d|=%.3e — emitting nothing ***" % worst)
        sys.exit(1)
    print("=== FIDELITY PASSED max|d|=%.3e ===\n" % worst, flush=True)

OUT = np.full((T, N), np.nan, np.float32)
n_done = 0
for f in folds:
    fi = int(f.split("fold_")[1].split("_")[0])
    te, te_year, model, mu, sd = load_fold(fi, legacy=args.legacy_norm)
    rows = np.where(np.isin(d.day, d.uniq_days[day_year == te_year]) & d.valid_hour)[0]
    t0 = time.time()
    with torch.no_grad():
        for b0 in range(0, len(rows), args.bs):
            bh = rows[b0:b0 + args.bs]
            X = CH[bh[:, None] + offs[None, :]].transpose(0, 2, 1, 3)
            Xn = np.clip((np.nan_to_num(X) - mu) / sd, -10, 10).astype(np.float32)
            mm = mask_mat[bh].astype(np.float32)
            sc = model(torch.from_numpy(Xn).to(args.device),
                       torch.from_numpy(mm).to(args.device))["factor_scores"].cpu().numpy()
            sc = np.where(mm[:, :, None] > 0.5, sc, np.nan)
            for j, t in enumerate(bh):
                base = np.where(base_mask[t])[0]
                if base.size < 5:
                    continue
                comp = np.zeros(base.size)
                nk = 0
                for k in range(sc.shape[2]):
                    col = sc[j, base, k]
                    if np.isfinite(col).all() and col.std() > 1e-12:
                        comp += (col - col.mean()) / col.std()
                        nk += 1
                if nk:
                    OUT[t, base] = (comp / nk).astype(np.float32)
            if b0 % (args.bs * 40) == 0:
                el = time.time() - t0
                print("  [%s/%s] fold%d te=%d %d/%d %.0fs (%.3fs/anchor)"
                      % (args.run, args.arm, fi, te_year, b0, len(rows), el,
                         el / max(b0 + args.bs, 1)), flush=True)
    n_done += len(rows)
    print("[%s/%s] fold%d te=%d rows=%d %.0fs"
          % (args.run, args.arm, fi, te_year, len(rows), time.time() - t0), flush=True)
    del model

np.savez("/tmp/vs4_pred_%s_%s.npz" % (args.run, args.arm), pred=OUT, ts=ts)
print("[%s/%s] DONE rows=%d finite=%d total %.0fs"
      % (args.run, args.arm, n_done, int(np.isfinite(OUT).sum()), time.time() - t00), flush=True)
