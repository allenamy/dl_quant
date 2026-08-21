"""Build the DUAL-SOURCE basis-SEQUENCE cache (Stage E) — basis as 600-step feats.

GOAL
----
Per UTC calendar day, write ``data/npz_dualbasis/<day>.npz`` = **ALL keys of the
dual-LOB cache ``data/npz_duallob/<day>.npz``** (which itself = the spot2perp
baseline contract PLUS the PERP deep book ``X_raw_perp_deep``) BUT with the
feature tensor ``X`` EXPANDED from (N,600,64) to **(N,600,68)** by appending FOUR
basis-SEQUENCE channels computed at EACH of the 600 window steps (not just the
last step, as ``build_basis_factors.py`` does):

    X[:, :, :64]   spot-64 features      (verbatim from npz_duallob X)
    X[:, :,  64]   basis_bps      seq     (perp_mid-spot_mid)/spot_mid*1e4, clip+-50
    X[:, :,  65]   basis_z        seq     causal 30-min rolling z of basis_bps
    X[:, :,  66]   basis_mom      seq     basis_bps(s) - basis_bps(s-300s)
    X[:, :,  67]   basis_ema_dev  seq     basis_bps(s) - causal EMA(span~60s)

Everything else is copied VERBATIM from npz_duallob:
    X_raw           float16 (N,600,20,4)  SPOT raw LOB   (Path B — unchanged)
    X_raw_perp_deep float16 (N,600,20,4)  PERP deep book (gated residual)
    regime_prior    float32 (N,6)
    y_600           float32 (N,)          PERP target
    y_mask_600      uint8   (N,)
    timestamps      int64   (N,)          PERP-pred-idx us (= window LAST step)

CHANNEL COUNT
-------------
We use **68** channels (spot-64 + the 4 basis-seq channels, NO spare). The model
(``DualLOBREGArch`` / ``DualPathLOBModelV3``) reads ``n_features`` from the data
(here 68), so RevIN / GDCN / input_proj all size to 68 automatically; nothing is
hardcoded to 64 in the multi_asset/ trainer or dataset.

WHY BASIS AS A SEQUENCE (mechanism)
-----------------------------------
perp ``y_600`` ≈ spot ``y_600`` (corr ~0.998); the RESIDUAL r = perp_y - spot_y
(~6% of perp variance) is strongly predicted by the basis (IC 0.20-0.33 vs r,
both regimes, sign = mean-reversion). A spot-feature model leaves r unmodeled.
By feeding the basis as a 600-step SEQUENCE through the SAME Path-A pipeline
(RevIN -> GDCN -> input_proj -> conformer), the GDCN crosses the basis trajectory
WITH the spot features, and the temporal backbone sees the basis dynamics over the
window — so the model can predict the spot direction AND the basis residual.
(``build_basis_factors.py`` only gave the basis at the window's LAST step, a
single scalar per window; here it is the full intra-window path.)

THE WINDOW <-> SECOND GRID (verified against build_windowed_npz.py)
------------------------------------------------------------------
The windowing pipeline (``build_windowed_npz.py`` lines ~22-26) is::

    pred_idx = start + input_len - 1
    window   = bars [pred_idx-599, pred_idx]  (inclusive)  -> X lookback
    timestamp at the window = ts[pred_idx]                  (the LAST step)

bars are the 1-second grid, so for a window whose stored ``timestamps[i]`` (us)
floors to second ``last_sec_i``, window step ``j`` (0..599) is the bar at second::

    s_ij = last_sec_i - 599 + j           (step 599 -> last_sec_i)

We therefore build the FOUR basis factors on the full per-second mid grid
(reusing ``build_basis_factors.per_second_factors`` verbatim — already causal),
then for each window gather the per-second factor value at each of its 600
seconds ``s_ij`` via a ``<= s`` lookup (searchsorted side='right' - 1, the same
causal sampler as ``build_basis_factors.sample_at_pred_secs`` but vectorised over
all 600*N seconds at once).

STRICT CAUSALITY (per STEP, not just per window)
------------------------------------------------
``per_second_factors`` computes every statistic causally: ``basis_bps[s]`` is a
``<= s`` quantity; ``basis_z`` / ``basis_ema_dev`` shift(1) their rolling/EMA
stat so the value at second s uses only seconds ``< s``; ``basis_mom`` subtracts
the value exactly 300s earlier (both ``<= s``). Sampling the per-second array at
window-step second ``s_ij`` with a ``<= s_ij`` lookup therefore makes step ``j``
of the basis sequence depend ONLY on mids at or before ``s_ij``. So corrupting
any mid strictly AFTER a step's second leaves that step (and all earlier steps)
byte-identical — asserted in ``_assert_causal`` (corrupt future mids -> <=t
basis-seq unchanged). The forward target ``y_600`` (over [last_sec, last_sec+600])
is untouched.

OUTPUT (NEW DIR — nothing existing is touched)
----------------------------------------------
  data/npz_dualbasis/<YYYY-MM-DD>.npz   (see GOAL for the key list)

CLI
---
  python multi_asset/data/build_basis_seq.py --days 2025-02-10 2025-02-11 2026-01-05
  python multi_asset/data/build_basis_seq.py --all          # skip existing
  python multi_asset/data/build_basis_seq.py --all --force  # rebuild
  python multi_asset/data/build_basis_seq.py --selftest     # leakage + shape unit
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import os.path as p
import sys
import time

import numpy as np

_REPO = p.dirname(p.dirname(p.dirname(p.abspath(__file__))))
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)

# Reuse the PROVEN per-second causal factor core verbatim (no re-derivation).
from multi_asset.data.build_basis_factors import (  # noqa: E402
    FACTOR_NAMES,
    US_PER_SEC,
    per_second_factors,
)
# Reuse the PROVEN spot2perp+perp position-join (constant-offset guard, y_600
# identity check) so the duallob-FALLBACK below is byte-identical to npz_duallob.
from multi_asset.data import build_duallob_npz as _dl  # noqa: E402

DUALLOB_DIR = p.join(_REPO, "data", "npz_duallob")       # base contract (READ)
SPOT2PERP_DIR = p.join(_REPO, "data", "npz_spot2perp")   # fallback base   (READ)
PERP_DIR = p.join(_REPO, "data", "npz_perp")             # fallback perp   (READ)
MID_DIR = p.join(_REPO, "data", "mid_cache")             # per-second mids (READ)
OUT_DIR = p.join(_REPO, "data", "npz_dualbasis")         # NEW output dir

# Per-channel sanity clip applied AFTER gathering (before nan_to_num). Rationale:
# `basis_z` is a ratio (basis - rollmean)/(rollstd + 1e-6); when the basis is flat
# across the 30-min window rollstd -> 0 and z explodes (observed max ~8e5 on a
# handful of windows). A z-score is dimensionless and physically bounded ~±10, so
# clip ±10 (matches the project's σ-clip discipline). The other three channels are
# bps-unit and already bounded (basis_bps clipped ±50 in the core; mom/ema_dev are
# differences of ±50-clipped values), so a generous ±50 clip is a no-op safety net
# that also stops any pathological print/EMA-warmup spike from reaching RevIN/GDCN.
_CH_CLIP = {"basis_bps": 50.0, "basis_z": 10.0, "basis_mom": 50.0,
            "basis_ema_dev": 50.0}

INPUT_LEN = 600                                       # window step count
N_BASIS_CH = len(FACTOR_NAMES)                        # 4 basis-seq channels
# Fill value for any (rare) window-second that predates the mid grid / is NaN in
# a causal stat (e.g. first ~2 seconds before any rolling stat is defined). 0.0
# is the post-RevIN-neutral value and matches the dataset's nan_to_num policy.
FILL = 0.0


# --------------------------------------------------------------------------- #
# core: per-second factors -> per-window (N,600,4) sequence tensor            #
# --------------------------------------------------------------------------- #
def basis_seq_for_windows(sec, factors, last_secs, input_len=INPUT_LEN):
    """Gather the 4 per-second basis factors onto every window's 600-step grid.

    Parameters
    ----------
    sec : (T,) int64
        Contiguous per-second grid from ``mid_cache`` (unix seconds).
    factors : dict name -> (T,) float64
        The per-second causal factor arrays (from ``per_second_factors``).
    last_secs : (N,) int64
        Each window's LAST-step second = floor(timestamps_us / 1e6).
    input_len : int
        Window length (600).

    Returns
    -------
    seq : (N, input_len, 4) float32
        ``seq[i, j, c]`` = factor c sampled (``<= s``) at second
        ``last_secs[i] - (input_len-1) + j``. Out-of-grid / NaN -> ``FILL``.

    Causality: each step uses a ``<= s`` lookup into the already-causal
    per-second factor arrays, so step j depends only on mids ``<= s_ij``.
    """
    sec = np.asarray(sec, dtype=np.int64)
    last_secs = np.asarray(last_secs, dtype=np.int64)
    N = last_secs.size
    T = sec.size

    # All window-second indices at once: (N, input_len).
    # step offsets 0..input_len-1 map to seconds last - (input_len-1) + j.
    offs = np.arange(input_len, dtype=np.int64) - (input_len - 1)   # (L,) in [-599..0]
    want = last_secs[:, None] + offs[None, :]                       # (N, L) seconds

    # <= s lookup into the contiguous grid: position of the latest grid second
    # that is <= the wanted second (searchsorted right - 1). Grid is contiguous
    # so this is just (want - sec[0]) clamped, but use searchsorted to stay
    # correct even if a day's grid is not perfectly contiguous.
    flat = want.reshape(-1)
    j = np.searchsorted(sec, flat, side="right") - 1               # (N*L,)
    valid = j >= 0
    jj = np.clip(j, 0, T - 1)

    seq = np.empty((N * input_len, N_BASIS_CH), dtype=np.float64)
    for c, name in enumerate(FACTOR_NAMES):
        arr = np.asarray(factors[name], dtype=np.float64)
        v = arr[jj]
        v[~valid] = np.nan
        # Per-channel sanity clip (esp. basis_z's near-zero-rollstd blow-ups);
        # NaNs pass through clip unchanged and are filled below.
        cl = _CH_CLIP[name]
        v = np.clip(v, -cl, cl)
        seq[:, c] = v
    seq = seq.reshape(N, input_len, N_BASIS_CH)
    # Any NaN (pre-grid seconds, or undefined early causal stats) -> FILL.
    seq = np.nan_to_num(seq, nan=FILL, posinf=FILL, neginf=FILL)
    return seq.astype(np.float32)


def _load_mids(date_str):
    """Load the per-second (sec, spot_mid, perp_mid) grid for one UTC day."""
    midf = p.join(MID_DIR, "%s.npz" % date_str)
    if not p.exists(midf):
        raise FileNotFoundError("mid_cache missing: %s" % midf)
    with np.load(midf) as zm:
        sec = zm["sec"].astype(np.int64)
        spot_mid = zm["spot_mid"].astype(np.float64)
        perp_mid = zm["perp_mid"].astype(np.float64)
    return sec, spot_mid, perp_mid


def _load_base_data(date_str):
    """Return the npz_duallob-equivalent key dict for one day + a source tag.

    Prefers the prebuilt ``data/npz_duallob/<day>.npz`` (read verbatim). When
    that day is absent (the duallob cache spans fewer days than spot2perp/mids,
    e.g. 2026), FALL BACK to assembling it in-memory from
    ``npz_spot2perp`` + ``npz_perp`` using the SAME position-join the duallob
    builder uses (equal length, constant per-day offset <= SHIFT_TOL_US, perp
    X_raw shape match, byte-identical PERP y_600) — so a dualbasis day built
    either way carries the identical base contract.
    """
    dl_npz = p.join(DUALLOB_DIR, "%s.npz" % date_str)
    if p.exists(dl_npz):
        with np.load(dl_npz, allow_pickle=True) as zd:
            return {k: zd[k] for k in zd.files}, "npz_duallob"

    # --- FALLBACK: spot2perp + perp position-join (duallob logic, in-memory) -
    spot_npz = p.join(SPOT2PERP_DIR, "%s.npz" % date_str)
    perp_npz = p.join(PERP_DIR, "%s.npz" % date_str)
    if not p.exists(spot_npz):
        raise FileNotFoundError("neither npz_duallob nor spot2perp for %s "
                                "(%s)" % (date_str, spot_npz))
    if not p.exists(perp_npz):
        raise FileNotFoundError("perp cache missing for %s: %s"
                                % (date_str, perp_npz))
    with np.load(spot_npz, allow_pickle=True) as zs:
        data = {k: zs[k] for k in zs.files}
    with np.load(perp_npz, allow_pickle=True) as zp:
        perp_raw = np.asarray(zp["X_raw"])
        perp_ts = np.asarray(zp["timestamps"], dtype=np.int64)
        yp = np.nan_to_num(np.asarray(zp["y_600"], dtype=np.float64))

    spot_raw = np.asarray(data["X_raw"])
    spot_ts = np.asarray(data["timestamps"], dtype=np.int64)
    if spot_raw.shape[0] != perp_raw.shape[0]:
        raise RuntimeError("%s: spot N=%d vs perp N=%d (cannot join)"
                           % (date_str, spot_raw.shape[0], perp_raw.shape[0]))
    diff = perp_ts - spot_ts
    if diff.size == 0 or not np.all(diff == diff[0]):
        raise RuntimeError("%s: non-constant perp-spot ts offset (fallback)"
                           % date_str)
    if abs(int(diff[0])) > _dl.SHIFT_TOL_US:
        raise RuntimeError("%s: constant offset %d us > tol (fallback)"
                           % (date_str, int(diff[0])))
    if perp_raw.shape != spot_raw.shape:
        raise RuntimeError("%s: perp X_raw %s != spot X_raw %s (fallback)"
                           % (date_str, perp_raw.shape, spot_raw.shape))
    ys = np.nan_to_num(np.asarray(data["y_600"], dtype=np.float64))
    if not np.array_equal(ys, yp):
        raise RuntimeError("%s: perp y_600 differs spot2perp vs perp (fallback)"
                           % date_str)
    data[_dl.NEW_KEY] = perp_raw
    return data, "spot2perp+perp(fallback)"


def build_one_day(date_str, out_path):
    """Build + atomically write ``data/npz_dualbasis/<day>.npz`` for one UTC day.

    Copies every key of the (real or fallback) npz_duallob cache verbatim, then
    REPLACES ``X`` with the (N,600,68) concat of spot-64 and the 4 basis-seq
    channels. Raises on any shape / contract violation so a bad day is never
    silently emitted.
    """
    t0 = time.time()

    data, src = _load_base_data(date_str)

    # --- contract checks on the base dual-LOB cache ----------------------- #
    for req in ("X", "X_raw", "X_raw_perp_deep", "y_600", "y_mask_600",
                "timestamps"):
        if req not in data:
            raise KeyError("%s: base cache (%s) lacks required key %r"
                           % (date_str, src, req))

    X = np.asarray(data["X"], dtype=np.float32)            # (N,600,64) spot feats
    if X.ndim != 3 or X.shape[1] != INPUT_LEN:
        raise RuntimeError("%s: unexpected X shape %s (want (N,%d,F))"
                           % (date_str, X.shape, INPUT_LEN))
    if X.shape[2] != 64:
        raise RuntimeError("%s: expected 64 spot feature channels, got %d "
                           "(is this already a dualbasis cache?)"
                           % (date_str, X.shape[2]))
    N = X.shape[0]
    ts_us = np.asarray(data["timestamps"], dtype=np.int64)
    if ts_us.shape[0] != N:
        raise RuntimeError("%s: timestamps N=%d != X N=%d"
                           % (date_str, ts_us.shape[0], N))

    # --- per-second basis factors (causal) + per-window 600-step gather --- #
    sec, spot_mid, perp_mid = _load_mids(date_str)
    factors = per_second_factors(sec, spot_mid, perp_mid)
    last_secs = ts_us // US_PER_SEC                        # window LAST-step second
    basis_seq = basis_seq_for_windows(sec, factors, last_secs, INPUT_LEN)  # (N,600,4)

    if basis_seq.shape != (N, INPUT_LEN, N_BASIS_CH):
        raise RuntimeError("%s: basis_seq shape %s != %s"
                           % (date_str, basis_seq.shape,
                              (N, INPUT_LEN, N_BASIS_CH)))
    if not np.isfinite(basis_seq).all():
        raise RuntimeError("%s: non-finite basis_seq after nan_to_num" % date_str)

    # --- expand X to (N,600,68): spot-64 ++ 4 basis-seq channels ---------- #
    X_new = np.concatenate([X, basis_seq], axis=-1).astype(np.float32)  # (N,600,68)
    data["X"] = X_new

    # Atomic write (tmp + os.replace), compressed like the source caches.
    os.makedirs(OUT_DIR, exist_ok=True)
    tmp = "%s.tmp.%d.npz" % (out_path, os.getpid())
    np.savez_compressed(tmp, **data)
    os.replace(tmp, out_path)

    # diagnostics: per-channel std over the (finite) sequence + coverage
    ch_std = [float(np.std(basis_seq[:, :, c])) for c in range(N_BASIS_CH)]
    pre_grid = float((last_secs - (INPUT_LEN - 1) < sec[0]).mean())  # windows starting before grid
    return {
        "N": int(N),
        "secs": time.time() - t0,
        "mb": os.path.getsize(out_path) / 1e6,
        "F": int(X_new.shape[2]),
        "ch_std": ch_std,
        "frac_window_pre_grid": pre_grid,
        "src": src,
    }


# --------------------------------------------------------------------------- #
# leakage self-test: corrupt FUTURE mids -> <=t basis-seq must be unchanged   #
# --------------------------------------------------------------------------- #
def _assert_causal(date_str="__synthetic__"):
    """Corrupt-future-mids leakage assert on the per-window basis sequence.

    Builds a synthetic contiguous mid grid + a few windows, computes the
    basis-seq, then sets every mid AFTER a chosen cut-second to garbage and
    recomputes. Every window step whose second is ``<= cut`` must be byte-
    identical (its value used only mids ``<= its own second`` ``<= cut``).
    """
    rng = np.random.default_rng(0)
    T = 4000
    sec = np.arange(1_000_000_000, 1_000_000_000 + T, dtype=np.int64)
    spot = 50_000.0 + np.cumsum(rng.normal(0, 1.0, T))
    perp = spot + rng.normal(0.5, 0.3, T)                  # small positive basis
    factors = per_second_factors(sec, spot, perp)

    # windows whose LAST second spans the back half of the grid
    last_secs = sec[np.arange(1500, T, 137)]
    seq0 = basis_seq_for_windows(sec, factors, last_secs, INPUT_LEN)

    # corrupt everything strictly AFTER cut (a second inside the windows' span)
    cut = int(sec[3000])
    perp_c = perp.copy()
    spot_c = spot.copy()
    future = sec > cut
    perp_c[future] = -1e9
    spot_c[future] = 1e-3                                   # nonsense
    factors_c = per_second_factors(sec, spot_c, perp_c)
    seq1 = basis_seq_for_windows(sec, factors_c, last_secs, INPUT_LEN)

    # mask of (window, step) whose second is <= cut -> must be byte-identical
    offs = np.arange(INPUT_LEN, dtype=np.int64) - (INPUT_LEN - 1)
    want = last_secs[:, None] + offs[None, :]              # (N, L) seconds
    le_cut = want <= cut
    a = seq0[le_cut]
    b = seq1[le_cut]
    same = np.array_equal(a, b)
    n_checked = int(le_cut.sum())
    # sanity: SOME steps are > cut and (for at least basis_bps) DID change, else
    # the test is vacuous (we corrupted the future but nothing downstream moved).
    gt_cut = want > cut
    changed_future = (not np.array_equal(seq0[gt_cut][:, 0], seq1[gt_cut][:, 0])
                      if gt_cut.any() else True)
    print("[selftest] causal: <=cut steps identical=%s (checked %d steps); "
          "future-steps changed=%s" % (same, n_checked, changed_future))
    assert same, "LEAKAGE: a <=cut basis-seq step changed when FUTURE mids were corrupted"
    assert changed_future, "VACUOUS TEST: corrupting future mids changed nothing downstream"
    return True


def _selftest():
    """Shape + causality unit test (no disk I/O)."""
    ok = _assert_causal()
    # shape contract on synthetic windows
    rng = np.random.default_rng(1)
    T = 2000
    sec = np.arange(2_000_000_000, 2_000_000_000 + T, dtype=np.int64)
    spot = 100.0 + np.cumsum(rng.normal(0, 0.01, T))
    perp = spot + rng.normal(0.02, 0.01, T)
    factors = per_second_factors(sec, spot, perp)
    last_secs = sec[np.arange(700, T, 200)]
    seq = basis_seq_for_windows(sec, factors, last_secs, INPUT_LEN)
    assert seq.shape == (last_secs.size, INPUT_LEN, N_BASIS_CH), seq.shape
    assert np.isfinite(seq).all(), "non-finite after nan_to_num"
    assert seq.dtype == np.float32, seq.dtype
    print("[selftest] shape ok: seq %s dtype=%s finite=%s"
          % (seq.shape, seq.dtype, bool(np.isfinite(seq).all())))
    print("[selftest] ALL OK" if ok else "[selftest] FAIL")
    return ok


# --------------------------------------------------------------------------- #
# driver                                                                       #
# --------------------------------------------------------------------------- #
def list_days():
    """Days with a mid_cache AND a base (npz_duallob OR spot2perp+perp).

    The base can be the prebuilt duallob cache or the spot2perp+perp fallback
    (``_load_base_data``), so a day qualifies if it has mids and EITHER a duallob
    file OR both a spot2perp and a perp file.
    """
    if not p.isdir(MID_DIR):
        raise FileNotFoundError("mid_cache dir not found: %s" % MID_DIR)

    def _days(d):
        out = set()
        if not p.isdir(d):
            return out
        for name in os.listdir(d):
            if not (len(name) == 14 and name.endswith(".npz")):
                continue
            stem = name[:-4]
            try:
                dt.date.fromisoformat(stem)
            except ValueError:
                continue
            out.add(stem)
        return out

    mids = _days(MID_DIR)
    base = _days(DUALLOB_DIR) | (_days(SPOT2PERP_DIR) & _days(PERP_DIR))
    return sorted(mids & base)


def build(days_subset=None, force=False):
    os.makedirs(OUT_DIR, exist_ok=True)
    days = days_subset if days_subset else list_days()
    print("[dualbasis] %d day(s) -> %s" % (len(days), OUT_DIR), flush=True)
    t0 = time.time()
    n_done = n_skip = n_fail = 0
    failed = []
    for i, d in enumerate(days):
        out = p.join(OUT_DIR, "%s.npz" % d)
        if (not force) and p.exists(out):
            n_skip += 1
            continue
        try:
            st = build_one_day(d, out)
        except Exception as e:  # noqa: BLE001 — keep going; report at the end
            n_fail += 1
            failed.append(d)
            print("  [warn] day %s failed: %s: %s"
                  % (d, type(e).__name__, e), flush=True)
            continue
        n_done += 1
        print("  [%d/%d] %s N=%d F=%d %.1fMB %.1fs ch_std=%s pre_grid=%.4f src=%s"
              % (i + 1, len(days), d, st["N"], st["F"], st["mb"], st["secs"],
                 ["%.3f" % s for s in st["ch_std"]], st["frac_window_pre_grid"],
                 st["src"]),
              flush=True)
    print("[dualbasis] DONE in %.1f min: built=%d skip=%d fail=%d%s -> %s"
          % ((time.time() - t0) / 60, n_done, n_skip, n_fail,
             ("  FAILED: %s" % failed[:20]) if failed else "", OUT_DIR),
          flush=True)
    return n_fail


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--all", action="store_true",
                   help="build every day in BOTH npz_duallob & mid_cache (skip existing)")
    g.add_argument("--days", type=str, nargs="+",
                   help="build only these YYYY-MM-DD days")
    g.add_argument("--selftest", action="store_true",
                   help="run the shape + leakage unit test (no disk I/O) and exit")
    ap.add_argument("--force", action="store_true",
                    help="rebuild day files that already exist")
    args = ap.parse_args()
    if args.selftest:
        sys.exit(0 if _selftest() else 1)
    nf = build(days_subset=args.days, force=args.force)
    sys.exit(1 if nf else 0)
