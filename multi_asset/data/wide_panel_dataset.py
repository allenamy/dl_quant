"""Engine A — hourly WIDE panel dataset layer for the temporal-spatial trainer.

Wraps wide_dl.npz (CH (T,N,C) causal channels + YR/Y/CL{H} + MEMBER110) and streams the trainer's
expected batches: per prediction hour t, window CH[t-W+1:t+1] -> (N,W,C), variable membership via
the member mask. Mirrors SeqPanelData's set_fold/iter interface so the model + losses + gates carry
over unchanged; only the data grid differs (hourly (T,N,C), no per-day 1s seq_cache).

Batch: Xseq (B,N,W,C) standardized f32, y (B,N) residual target NORMALISED, mask (B,N) f32, rows (B,).
"""
from __future__ import annotations
import numpy as np

WIDE_DL = ("/mnt/storage/private/work_hsy/quant_research_multi_asset/"
           "multi_asset/exports/wide_dl.npz")
WINDOW = 168


class WidePanelData:
    def __init__(self, path=WIDE_DL, target_horizon=4, aux_horizons=(1, 24), window=WINDOW):
        z = np.load(path, allow_pickle=True)
        self.CH = z["CH"].astype(np.float32)                # (T,N,C)
        self.ts = z["ts"]; self.symbols = z["symbols"]
        self.ch_names = [str(x) for x in z["ch_names"]]
        self.T, self.N, self.C = self.CH.shape
        self.S = self.N                                     # trainer calls it S
        self.F = self.C
        self.W = window
        self.H = target_horizon
        self.member = z["MEMBER110"]                        # (T,N) bool
        self.Y = z[f"YR{target_horizon}"].astype(np.float32)     # residual target (primary)
        self.Yraw = z[f"Y{target_horizon}"].astype(np.float32)   # raw forward return (eval)
        self.CL = z[f"CL{target_horizon}"]                       # >=H non-overlap clean
        self.aux = {int(h): (z[f"YR{h}"].astype(np.float32), z[f"CL{h}"]) for h in aux_horizons}
        # hourly grid -> day index for walk-forward folds
        self.day = np.arange(self.T) // 24
        self.uniq_days = np.unique(self.day)
        # valid prediction hours: enough lookback AND target finite for >=1 member
        self.valid_hour = np.zeros(self.T, bool)
        ok = np.arange(self.T) >= (self.W - 1)
        self.valid_hour[ok] = (self.CL[ok].any(1))
        self.mu = self.sd = self.sigma = None

    # ---- per-fold stats (train-only) ----
    def set_fold(self, train_days):
        trm = np.isin(self.day, np.asarray(train_days))     # train_days = day indices
        rows = np.where(trm & self.valid_hour)[0]
        # channel mu/sd over train member-hours (mask non-members)
        m = self.member[rows]                               # (n,N)
        blk = self.CH[rows]                                 # (n,N,C)
        w = m[..., None].astype(np.float32)
        cnt = w.sum((0, 1)).clip(1)
        mu = (blk * w).sum((0, 1)) / cnt
        var = ((blk - mu) ** 2 * w).sum((0, 1)) / cnt
        self.mu = mu.astype(np.float32)
        self.sd = np.sqrt(var).clip(1e-6).astype(np.float32)
        # residual-target sigma: cross-sectional MAD of the residual target on train clean rows
        yy = self.Y[rows][self.CL[rows]]
        yy = yy[np.isfinite(yy)]
        mad = np.median(np.abs(yy - np.median(yy))) * 1.4826 if yy.size > 100 else 1.0
        self.resid_sigma = np.float32(max(mad, 1e-6))
        return self.mu, self.sd

    def iter_batches(self, split_hours, batch_hours=256, rng=None, shuffle=True, want_raw=False):
        """Yield standardized window batches over the prediction hours in split_hours (day list)."""
        sel = np.isin(self.day, split_hours) & self.valid_hour
        hrs = np.where(sel)[0]
        if shuffle and rng is not None:
            rng.shuffle(hrs)
        offs = np.arange(-self.W + 1, 1)                    # (W,)
        for b0 in range(0, len(hrs), batch_hours):
            bh = hrs[b0:b0 + batch_hours]                   # (B,) prediction hours
            widx = bh[:, None] + offs[None, :]              # (B,W)
            Xseq = self.CH[widx].transpose(0, 2, 1, 3)      # (B,N,W,C)
            Xn = np.clip((np.nan_to_num(Xseq) - self.mu) / self.sd, -10, 10).astype(np.float32)
            ymat = self.Y[bh]                               # (B,N)
            mask = (self.member[bh] & self.CL[bh] & np.isfinite(ymat)).astype(np.float32)
            yn = np.nan_to_num(ymat / self.resid_sigma).astype(np.float32)
            out = dict(Xseq=Xn, y=yn, mask=mask, rows=bh)
            if want_raw:
                out["y_raw"] = self.Yraw[bh]
            yield out


if __name__ == "__main__":     # smoke: shapes + a fold + one batch
    d = WidePanelData()
    print(f"[wide] T={d.T} N={d.N} C={d.C} W={d.W} valid_hours={int(d.valid_hour.sum())} "
          f"uniq_days={len(d.uniq_days)}")
    ndays = len(d.uniq_days)
    d.set_fold(d.uniq_days[:int(ndays * 0.7)])
    print(f"[wide] fold stats: mu/sd shape {d.mu.shape} resid_sigma={d.resid_sigma:.5f}")
    import numpy as _np
    for b in d.iter_batches(d.uniq_days[int(ndays * 0.7):], batch_hours=128,
                            rng=_np.random.default_rng(0)):
        print(f"[wide] batch Xseq {b['Xseq'].shape} y {b['y'].shape} mask sum {int(b['mask'].sum())} "
              f"(members/hr~{b['mask'].sum(1).mean():.0f})")
        break
