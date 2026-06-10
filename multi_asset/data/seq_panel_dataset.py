"""Sequence panel dataset for the temporal-spatial model.

Serves, per prediction timestamp t, the 14-asset panel of 600-bar lookback
windows:  Xseq (S, W, F), y (S,), mask (S,).

Two caches, two roles (deliberate, for a fair apples-to-apples comparison with
the shallow `CrossAssetPanelModel`):

  * panel_cache/<sym>.npz  — the SHALLOW last-token cache. We reuse it ONLY for
    (a) the master panel sample index (common-aligned stride-180 ts grid + per-ts
    day + clean600 flags), and (b) the per-fold standardization stats (shared
    44-feature mean/std over train asset-rows + per-asset y MAD-sigma). This is
    EXACTLY the index + stats the shallow panel trainer uses, so the only thing
    that changes between the two models is last-token-MLP vs temporal-Conformer.

  * seq_cache/<day>.npz  — the heavy CONTIGUOUS daily arrays (F (S,T,44),
    mask (S,T), ts (T,)). Read on demand, one day at a time (day-chunked), to
    slice the W=600 windows. Never fully materialised (would be ~1.6 TB in RAM).

Window slicing is strictly within-day (a window needs bar_idx >= W-1, so it never
crosses midnight — no cross-day leakage). y is taken from the seq file's y array
(identical to panel_cache y; both are compute_y600 on the same bars).

Iteration is day-chunked: shuffle the split's days, load each day's seq file once,
build all its window-batches, optionally shuffle within day. This reads each day
file exactly once per epoch (~110 GB hand-feats / epoch over 14 assets).
"""
from __future__ import annotations

import os.path as p

import numpy as np

WINDOW = 600
HORIZON = 600
PRED_STRIDE = 180
SYMBOLS = ["bnfbtc", "bnfeth", "bnfsol", "bnfbnb", "bnfxrp", "bnfdog", "bnfada",
           "bnflink", "bnfbch", "bnftrx", "bnfltc", "bnfdot", "bnffil", "bnfetc"]

SEQ_DIR = ("/mnt/storage/private/work_hsy/quant_research_multi_asset/"
           "multi_asset/exports/seq_cache")
PANEL_CACHE = ("/mnt/storage/private/work_hsy/quant_research_multi_asset/"
               "multi_asset/exports/panel_cache")


def _load_panel_cache(sym, cache_dir=PANEL_CACHE):
    d = np.load(p.join(cache_dir, f"{sym}.npz"))
    return d["X"], d["y"], d["day"], d["ts"], d["clean600"]


class SeqPanelData:
    """Holds the common-aligned panel index + per-fold stats; streams windows.

    Build once (assembles the panel index from panel_cache, ~seconds). Call
    `set_fold(train_days, val_days, test_days)` to fit train-only stats, then
    `iter_day_batches(split, ...)` to stream standardized window batches.
    """

    def __init__(self, seq_dir=SEQ_DIR, panel_cache=PANEL_CACHE,
                 symbols=SYMBOLS, window=WINDOW, n_feat=44, target_horizon=600):
        self.seq_dir = seq_dir
        self.panel_cache = panel_cache
        self.symbols = symbols
        self.S = len(symbols)
        self.W = window
        self.F = n_feat
        # target_horizon=600 -> use the seq_cache y (y_600). Otherwise swap the
        # TARGET (y + mask) to the mh_targets cache — same features, same bar
        # grid, only the forward-return horizon changes. 60/180 live in
        # mh_targets; 1800/3600 (NX long horizons) live in mh_targets_long.
        self.target_horizon = target_horizon
        sub = "mh_targets_long" if target_horizon > 600 else "mh_targets"
        self.mh_dir = (seq_dir.rsplit("/", 1)[0] + "/" + sub)

        # ---- assemble the common-aligned panel index from panel_cache ----
        per = {s: _load_panel_cache(s, panel_cache) for s in symbols}
        common = sorted(set.intersection(*[set(per[s][3].tolist()) for s in symbols]))
        cidx = {int(t): i for i, t in enumerate(common)}
        nT = len(common)
        self.ts = np.array(common, dtype=np.int64)          # (T,)
        self.day = np.zeros(nT, np.int64)
        self.X_last = np.full((nT, self.S, self.F), np.nan, np.float32)  # last-token (stats only)
        self.Y = np.full((nT, self.S), np.nan, np.float32)
        self.CL = np.zeros((nT, self.S), bool)
        for si, s in enumerate(symbols):
            Xs, ys, days, tss, cl = per[s]
            # symbols may have ts outside the common intersection (pre-2024 the
            # valid windows differ per asset) — keep only common-ts rows.
            keep = np.isin(tss, self.ts)
            rows = np.searchsorted(self.ts, tss[keep])
            self.X_last[rows, si] = Xs[keep]
            self.Y[rows, si] = ys[keep]
            self.CL[rows, si] = cl[keep]
            self.day[rows] = days[keep]
        self.uniq_days = np.unique(self.day)
        # group common-ts row indices by day (for day-chunked streaming)
        self._rows_by_day = {int(d): np.where(self.day == d)[0] for d in self.uniq_days}

        # for a non-600 horizon, rebuild the panel target self.Y from mh_targets
        # (aligned to the common pred-ts via each day's ts grid).
        if self.target_horizon != 600:
            Yh = np.full((nT, self.S), np.nan, np.float32)
            for d in self.uniq_days:
                z = np.load(p.join(self.mh_dir, f"{int(d)}.npz"))
                pos = {int(t): i for i, t in enumerate(z["ts"])}
                yh = z[f"y_{self.target_horizon}"]                # (S, T_day)
                for r in self._rows_by_day[int(d)]:
                    bi = pos.get(int(self.ts[r]))
                    if bi is not None:
                        Yh[r] = yh[:, bi]
            self.Y = Yh

        # per-fold state (set by set_fold)
        self.mu = self.sd = None
        self.sigma = None
        # optional in-RAM day cache (removes per-epoch disk IO). Keyed by day int.
        self._day_cache = {}
        self._cache_enabled = False

    # ----------------------------------------------------------------- stats
    def set_fold(self, train_days):
        """Fit shared (F,) feature mean/std + per-asset (S,) y MAD-sigma on the
        TRAIN rows only (identical recipe to the shallow panel trainer)."""
        trm = np.isin(self.day, np.asarray(train_days))
        blk = self.X_last[trm].reshape(-1, self.F)
        blk = blk[np.isfinite(blk).all(axis=1)]
        mu = blk.mean(axis=0)
        sd = blk.std(axis=0)
        self.mu = mu.astype(np.float32)
        self.sd = np.where(sd > 1e-9, sd, 1.0).astype(np.float32)
        sig = np.ones(self.S, np.float32)
        for si in range(self.S):
            col = self.Y[trm, si]
            col = col[np.isfinite(col)]
            if col.size > 10:
                mad = np.median(np.abs(col - np.median(col))) * 1.4826
                sig[si] = mad if mad > 1e-12 else 1.0
        self.sigma = sig
        # per-asset RESIDUAL MAD-sigma: cross-sectional demean (equal-weight over valid
        # assets per timestamp) then per-asset MAD on TRAIN rows. Used to normalise the
        # residual target for the cross-sectional long-short loss.
        Ytr = self.Y[trm]                                   # (n_tr, S)
        valid = np.isfinite(Ytr)
        rmean = np.nanmean(np.where(valid, Ytr, np.nan), axis=1, keepdims=True)
        resid = Ytr - rmean
        rsig = np.ones(self.S, np.float32)
        for si in range(self.S):
            col = resid[:, si]
            col = col[np.isfinite(col)]
            if col.size > 10:
                mad = np.median(np.abs(col - np.median(col))) * 1.4826
                rsig[si] = mad if mad > 1e-12 else 1.0
        self.resid_sigma = rsig
        return self.mu, self.sd, self.sigma

    # ----------------------------------------------------------------- cache
    def enable_cache(self, on=True):
        self._cache_enabled = on
        if not on:
            self._day_cache.clear()

    def preload(self, days, want_raw=False):
        """Load the given days' arrays into the in-RAM cache (one disk pass)."""
        self._cache_enabled = True
        for d in days:
            self._load_day(int(d), want_raw=want_raw)

    def _load_day(self, d, want_raw=False):
        """Return {'F','mask','y','ts'(,'Xraw')} for day d, using the cache."""
        d = int(d)
        c = self._day_cache.get(d)
        need_raw = want_raw and (c is None or "Xraw" not in c)
        if c is not None and not need_raw:
            return c
        z = np.load(p.join(self.seq_dir, f"{d}.npz"))
        out = {"F": z["F"], "mask": z["mask"], "y": z["y"], "ts": z["ts"]}
        if want_raw:
            out["Xraw"] = z["Xraw"]
        if hasattr(z, "close"):
            z.close()
        if self.target_horizon != 600:
            zh = np.load(p.join(self.mh_dir, f"{d}.npz"))
            out["y"] = zh[f"y_{self.target_horizon}"].astype(np.float32)   # (S,T) same grid
            out["mask"] = zh[f"m_{self.target_horizon}"]                    # target validity
            if hasattr(zh, "close"):
                zh.close()
        if self._cache_enabled:
            self._day_cache[d] = out
        return out

    # ----------------------------------------------------------------- stream
    def _day_pred_rows(self, d, split_rows_set, want_raw=False):
        """For day d, return (arrays, common_rows, bar_idx) for pred timestamps
        that are in `split_rows_set` AND form a full within-day window."""
        rows = self._rows_by_day[int(d)]
        rows = np.array([r for r in rows if r in split_rows_set], dtype=np.int64)
        if rows.size == 0:
            return None
        arr = self._load_day(d, want_raw=want_raw)
        ts_day = arr["ts"]                                  # (T_day,)
        ts_pos = {int(t): i for i, t in enumerate(ts_day)}
        keep_rows, keep_bar = [], []
        for r in rows:
            bi = ts_pos.get(int(self.ts[r]), None)
            if bi is None or bi < self.W - 1:
                continue
            keep_rows.append(r)
            keep_bar.append(bi)
        if not keep_rows:
            return None
        return arr, np.array(keep_rows, np.int64), np.array(keep_bar, np.int64)

    def iter_days(self, split_rows, rng=None, shuffle=True, want_raw=False):
        """Yield per-day RAW arrays for GPU-side windowing (fast path).

        Yields (F_all (S,T,F), mask_all (S,T), y_all (S,T), rows (n,), bars (n,))
        where rows are common-ts indices and bars the in-day pred bar index. The
        trainer moves F_all to the GPU ONCE per day and slices/standardizes
        windows there (the CPU numpy gather was starving the GPU)."""
        split_set = set(int(r) for r in split_rows)
        days = np.unique(self.day[split_rows])
        if shuffle and rng is not None:
            rng.shuffle(days)
        for d in days:
            got = self._day_pred_rows(d, split_set, want_raw=want_raw)
            if got is None:
                continue
            arr, rows, bars = got
            yield arr["F"], arr["mask"], arr["y"], rows, bars

    def iter_days_raw(self, split_rows, rng=None, shuffle=True):
        """Like iter_days but ALSO yields the raw-LOB array Xraw (S,T,5,4) for the
        full REG_arch panel (dual-path). Yields (F, Xraw, mask, y, rows, bars)."""
        split_set = set(int(r) for r in split_rows)
        days = np.unique(self.day[split_rows])
        if shuffle and rng is not None:
            rng.shuffle(days)
        for d in days:
            got = self._day_pred_rows(d, split_set, want_raw=True)
            if got is None:
                continue
            arr, rows, bars = got
            yield arr["F"], arr["Xraw"], arr["mask"], arr["y"], rows, bars

    def iter_day_batches(self, split_rows, batch_ts, rng=None, shuffle=True,
                         want_raw=False):
        """Yield standardized window batches, day-chunked.

        split_rows : 1-D array of common-ts row indices in this split.
        batch_ts   : number of prediction timestamps per yielded batch.
        Yields dict: Xseq (B,S,W,F) f32 standardized, y (B,S) f32 NORMALISED,
                     mask (B,S) f32, rows (B,) common-ts indices.
        """
        split_set = set(int(r) for r in split_rows)
        days = np.unique(self.day[split_rows])
        if shuffle and rng is not None:
            rng.shuffle(days)
        for d in days:
            got = self._day_pred_rows(d, split_set, want_raw=want_raw)
            if got is None:
                continue
            arr, rows, bars = got
            F_all = arr["F"]                                # (S, T_day, 44)
            mask_all = arr["mask"]                          # (S, T_day) bool
            y_all = arr["y"]                                # (S, T_day)
            order = np.arange(rows.shape[0])
            if shuffle and rng is not None:
                rng.shuffle(order)
            offs = np.arange(-self.W + 1, 1)               # (W,) window offsets
            for b0 in range(0, order.shape[0], batch_ts):
                bidx = order[b0:b0 + batch_ts]
                rr = rows[bidx]; bb = bars[bidx]
                B = bb.shape[0]
                # vectorized gather: (B,W) bar indices -> (S,B,W,F) -> (B,S,W,F)
                widx = bb[:, None] + offs[None, :]           # (B, W)
                Xseq = F_all[:, widx, :].transpose(1, 0, 2, 3)   # (B,S,W,F)
                ymat = y_all[:, bb].T                         # (B,S)
                valid = (mask_all[:, bb].T & np.isfinite(ymat))   # (B,S)
                win_ok = np.isfinite(Xseq).all(axis=(2, 3))  # (B,S)
                mmat = (valid & win_ok).astype(np.float32)
                # standardize features (shared mu/sd), clip; NaN->0 (masked anyway)
                Xn = np.clip((np.nan_to_num(Xseq, nan=0.0) - self.mu) / self.sd,
                             -10.0, 10.0).astype(np.float32)
                yn = np.nan_to_num(ymat / self.sigma[None, :], nan=0.0).astype(np.float32)
                out = dict(Xseq=Xn, y=yn, mask=mmat, rows=rr)
                if want_raw:
                    out["y_raw"] = ymat
                yield out
