"""Synthetic panel fixture so the data-dependent suites are HERMETIC (run anywhere).

WHY: `tests_production_signature` and `inject_failures` drive `pilot_daily.main()`, which loads the
live panel. That panel is a build artifact -- it lives under `exports/`, is excluded from git and
from the sync, and therefore exists only on the server. A suite that can only run where the data
happens to be is not a suite you can develop against: under the "edit locally, server executes"
rule it would mean never being able to verify a change before shipping it.

So the suites build a tiny synthetic panel instead. It is not a data substitute -- it carries no
alpha and proves nothing about returns. It exists purely so the WIRING can be exercised: schema,
guards, watchdog inputs, report generation, blocking paths. Anything that needs real data (actual
IC, actual cost) is still server-only and is not claimed here.

Shapes are the minimum PanelSource requires: ch_names must contain `funding_ema` and `size_dvol`,
symbols must contain `BTCUSDT`, and the king/s2 prediction panels must align to `ts`.
"""
from __future__ import annotations
import os
import numpy as np

N_HOURS = 24 * 14           # two weeks of hourly bars
SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT", "ADAUSDT",
           "LINKUSDT", "BCHUSDT", "LTCUSDT", "DOTUSDT", "AVAXUSDT", "TRXUSDT"]
CH_NAMES = ["funding_ema", "mom_4h", "mom_24h", "rev_1h", "rvol_24h", "size_dvol",
            "max_ret_24h", "beta_24h", "logqvol", "ret_4h", "xsr_rvol", "xsr_fund"]
# Anchored to "now" rather than a fixed epoch: pilot_daily has a data-freshness guard, so a
# fixture with old timestamps would BLOCK the run and the suite would be testing the blocked
# path by accident instead of the path it means to test.
import time as _time


def build(dirpath: str, seed: int = 20260725, frozen_frac: float = 0.6):
    """Write wide_dl_live.npz + king/s2 pred panels + a frozen king panel. Returns paths."""
    os.makedirs(dirpath, exist_ok=True)
    rng = np.random.default_rng(seed)
    T, N, C = N_HOURS, len(SYMBOLS), len(CH_NAMES)
    end_ms = int(_time.time() * 1000) - 3600_000        # last bar = one hour ago
    ts = (end_ms - (T - 1 - np.arange(T)) * 3600_000).astype(np.int64)

    CH = rng.standard_normal((T, N, C)).astype(np.float32) * 0.01
    CH[:, :, CH_NAMES.index("funding_ema")] *= 1e-4          # funding is a small rate
    member = np.ones((T, N), bool)
    Y1 = (rng.standard_normal((T, N)) * 0.002).astype(np.float32)
    Y4 = (rng.standard_normal((T, N)) * 0.004).astype(np.float32)
    CL4 = np.zeros((T, N), bool)
    CL4[::4] = True                                          # 4h anchor grid
    CL4 &= member

    panel = os.path.join(dirpath, "wide_dl_live.npz")
    np.savez(panel, ts=ts, symbols=np.array(SYMBOLS, dtype=object),
             ch_names=np.array(CH_NAMES, dtype=object), CH=CH, MEMBER110=member,
             Y1=Y1, Y4=Y4, CL1=CL4, CL4=CL4, CL24=CL4,
             YR1=Y1, YR4=Y4, YR24=Y4)

    # predictions correlated with Y4 so rank-IC is non-degenerate
    king = (0.3 * Y4 + 0.7 * rng.standard_normal((T, N)) * 0.004).astype(np.float32)
    s2 = (0.2 * Y4 + 0.8 * rng.standard_normal((T, N)) * 0.004).astype(np.float32)
    kp = os.path.join(dirpath, "king_pred_live.npz")
    sp = os.path.join(dirpath, "s2_pred_live.npz")
    np.savez(kp, ts=ts, king_pred=king)
    np.savez(sp, ts=ts, s2_pred=s2)

    # "frozen" panel marks where the shadow slice begins (anything after it is out-of-sample)
    cut = int(T * frozen_frac)
    fz = os.path.join(dirpath, "king_pred_panel.npz")
    np.savez(fz, ts=ts[:cut], king_pred=king[:cut])
    return {"panel": panel, "king": kp, "s2": sp, "frozen": fz, "ts": ts, "cut": cut}


def install(PD, RC=None, SPL=None, dirpath: str = "", **_):
    """Point the daily-chain modules at a fixture. Returns a restore callable.

    Mirrors `production_state_guard.override_all`: override EVERY panel reference, not just the one
    that happened to break, since overriding only that one is how the next one breaks.
    """
    paths = build(dirpath)
    saved = {}

    def _set(mod, attr, val):
        if mod is not None and hasattr(mod, attr):
            saved[(mod, attr)] = getattr(mod, attr)
            setattr(mod, attr, val)

    _set(PD, "LIVE_PANEL", paths["panel"])
    # ★ DECLARE THE PANEL SYNTHETIC (0C 2026-07-27). This fixture writes no `xsr_fund` channel and
    # no settlement-interval archive, so `assert_funding_dim` has nothing to measure on it — the
    # funding-caliber question is UNDEFINED here, not merely unanswered. Until today the guard chain
    # accommodated that BY ACCIDENT: its criterion expected the gate to fail on the declared pre-fix
    # factor version, and the gate did fail — for the unrelated reason that a channel was missing.
    # A suite stayed green on a coincidence between two unrelated states. The declaration is now
    # explicit, `run_guards` refuses it if LIVE_PANEL is still the production path, and the report
    # records NOT_VERIFIED rather than a pass.
    _set(PD, "SYNTHETIC_PANEL", True)
    for mod in (RC, SPL):
        _set(mod, "PANEL", paths["panel"])
        _set(mod, "KING", paths["king"])
        _set(mod, "S2", paths["s2"])
    _set(RC, "OUT", os.path.join(dirpath, "regime"))
    _set(SPL, "ROOT", os.path.join(dirpath, "pilot_log"))

    def restore():
        for (mod, attr), val in saved.items():
            setattr(mod, attr, val)
    return paths, restore
