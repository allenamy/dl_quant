"""Engine shadow-pipeline v0 — shared panel data layer.

Replay mode: reads the assembled panel + strictly-OOS pred panels from disk and serves
per-anchor cross-sections. Real-time mode is a stub (wire to a live panel feed). All 4-leg
raw signals + realized forward returns are exposed causally (<=t) for the downstream chain.
"""
import numpy as np
import pandas as pd

MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
PANEL = MA + "/exports/wide_dl_full.npz"
KING = MA + "/exports/eda/king_pred_panel.npz"
S2 = MA + "/exports/eda/s2_pred_panel_cl4.npz"


class PanelSource:
    def __init__(self, panel=PANEL, king=KING, s2=S2, btc="BTCUSDT"):
        W = np.load(panel, allow_pickle=True)
        self.ts = W["ts"].astype(np.int64)
        self.symbols = [str(s) for s in W["symbols"]]
        self.CH = W["CH"]; self.member = W["MEMBER110"]; self.ch = [str(c) for c in W["ch_names"]]
        self.Y4 = W["Y4"].astype(np.float64)          # raw 4h fwd logret (realized target)
        self.Y1 = W["Y1"].astype(np.float64)          # raw 1h fwd logret (for BTC rvol)
        self.CL4 = W["CL4"]
        self.king = np.load(king, allow_pickle=True)["king_pred"].astype(np.float64)
        self.s2 = np.load(s2, allow_pickle=True)["s2_pred"].astype(np.float64)
        self.fund_idx = self.ch.index("funding_ema"); self.size_idx = self.ch.index("size_dvol")
        self.dt = pd.to_datetime(self.ts, unit="ms", utc=True)
        self.T, self.N = self.member.shape
        self.btc_j = self.symbols.index(btc)
        # causal realized 1h return by time t = Y1[t-1]; BTC series r[t]
        self.btc_r = np.empty(self.T); self.btc_r[0] = np.nan
        self.btc_r[1:] = self.Y1[:-1, self.btc_j]

    def month_anchors(self, ym):
        """CL4 trading-grid anchor hour-indices in calendar month ym (e.g. '2026-06') with
        both DL pred legs available for >=1 member."""
        lo = pd.Timestamp(ym + "-01", tz="UTC"); hi = lo + pd.offsets.MonthBegin(1)
        inmon = np.asarray((self.dt >= lo) & (self.dt < hi))
        has = (self.member & self.CL4 & np.isfinite(self.king) & np.isfinite(self.s2)).any(1)
        return np.where(inmon & has)[0]

    def tradeable(self, t):
        """member & both DL legs finite at anchor t -> the tradeable universe."""
        return np.where(self.member[t] & np.isfinite(self.king[t]) & np.isfinite(self.s2[t]))[0]

    def legs_raw(self, t):
        """per-tradeable-asset raw leg signals at anchor t (all causal <=t)."""
        m = self.tradeable(t)
        return {"king": self.king[t, m], "s2": self.s2[t, m],
                "funding": self.CH[t, m, self.fund_idx].astype(np.float64),
                "size": self.CH[t, m, self.size_idx].astype(np.float64)}, m

    def realized_fwd_bps(self, t):
        """realized 4h forward logret in bps over tradeable set (for calibration + IC eval)."""
        m = self.tradeable(t); return self.Y4[t, m] * 1e4

    def btc_rvol_bps_min(self, t, window_h=24):
        """causal BTC realized vol in bps/min: std of trailing 1h returns / sqrt(60)."""
        lo = max(1, t - window_h + 1)
        r = self.btc_r[lo:t + 1]; r = r[np.isfinite(r)]
        if r.size < 4:
            return np.nan
        return float(np.std(r) * 1e4 / np.sqrt(60.0))
