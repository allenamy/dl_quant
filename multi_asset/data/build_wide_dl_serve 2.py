"""SERVE-caliber panel — what the LIVE system actually hands the frozen model, at every anchor.

> **创建:** 2026-08-03 17:0x UTC | **Session:** B4-retrain | **状态:** final — `0.079′` 的评测输入
> **规格:** team-lead 裁定(0.079′ owner=B4); 口径出处 `RESULT_channel_cutoff_audit_2026-08-03.md`
>          (SHA `eedab22a…`) §3 与 §9 的 SERVE 行
> **作废条件:** SERVE 口径的定义(尾部-13)被重定 ⇒ 重写

THREE CALIBERS OF ONE CHANNEL, AND WHY A THIRD PANEL EXISTS
-----------------------------------------------------------
`ch31 = ret_24h − beta_24h × mkt24`. Only `mkt24` differs between generations:

    TRAIN   sum(market[t−12 … t+11])   centered-24, 11 future taps   -> wide_dl_full.npz
    SERVE   sum(market[t−12 … t])      trailing-13                   -> THIS FILE
    CAUSAL  sum(market[t−23 … t])      trailing-24                   -> wide_dl_full_causal_v1.npz

★ SERVE IS NOT "THE CAUSAL ONE". It is a THIRD thing, and that is the whole reason this file exists.
  Live builds its panel ending at the signal row, so `np.convolve(..., "same")` zero-pads everything
  past `t` — the future half of the centered window is silently 0. The channel the deployed model
  receives is therefore neither the trained one nor its causal repair: it is the centered window
  with its future taps deleted, i.e. **13 taps, not 24**. Audit §9 measures the frozen king at
  0.135 / 0.079 / 0.041 across exactly these three, and `0.079` is the SERVE row — the only one of
  the three that is a real number about the live system.

★ WHY EVERY ROW, NOT JUST THE LAST. In production only the final row is truncated, once per anchor.
  To evaluate the frozen model over history under the caliber it actually receives, every row must
  be computed AS IF IT WERE THE LAST ROW — which is what a trailing-13 window over the whole panel
  produces. Building it any other way would measure a panel no anchor ever saw.

★ SERVE IS ALSO CAUSAL. Trailing-13 reads only the past, so the behavioural causality suite must
  pass 32/32 here too. "Causal" and "the caliber the model was trained on" are independent
  properties; this panel is the first and not the second, and conflating them is how 0.079 and
  0.041 get mistaken for each other.

It reuses `build_wide_dl_causal`'s wrapping, its pre-`savez` lineage pin, and its guard — the ONLY
difference is which trailing window the proxy returns. The causal builder is left byte-frozen: its
SHA is already cited in a delivered report, and editing it would retro-invalidate that citation.

Run: python multi_asset/data/build_wide_dl_serve.py <source_panel.npz> <out_serve.npz>
"""
from __future__ import annotations

import os.path as _p
import sys as _sys

import numpy as np

_sys.path.insert(0, _p.dirname(_p.dirname(_p.dirname(_p.abspath(__file__)))))

from multi_asset.data import build_wide_dl_causal as BC  # noqa: E402

SERVE_TAPS = 13          # audit §9: SERVE = sum(market[t−12 … t])


class ServeNumpy(BC.CausalNumpy):
    """CausalNumpy's guard, CausalNumpy's call recording — only the returned window differs.

    `super().convolve` is called for its GUARD and its bookkeeping (it refuses any convolve that is
    not the ch31 market window and counts invocations), then its trailing-24 result is discarded and
    replaced by trailing-13. Subclassing rather than copying keeps ONE copy of the guard: a second
    hand-written copy is exactly how two builders come to differ by which convention they enforce.
    """

    TAPS = SERVE_TAPS

    def convolve(self, a, v, mode="full"):
        super().convolve(a, v, mode)                       # guard + record; result deliberately unused
        return np.convolve(a, np.ones(self.TAPS), "full")[: np.size(a)]


def build_serve(panel, outpath):
    print(f"[serve] SERVE caliber = trailing-{SERVE_TAPS} (sum market[t-{SERVE_TAPS - 1} … t])",
          flush=True)
    return BC.build_causal(panel, outpath, proxy=ServeNumpy())


if __name__ == "__main__":
    if len(_sys.argv) < 3:
        raise SystemExit("usage: build_wide_dl_serve.py <source_panel.npz> <out_serve.npz>")
    build_serve(_sys.argv[1], _sys.argv[2])
