"""[causality] EVERY training-panel channel is causal — proven BEHAVIOURALLY, on the real builder.

> **创建:** 2026-08-03 16:2x UTC | **Session:** B4-retrain | **状态:** final
> **规格:** `PREREG_retrain_causal_panel_2026-08-03.md` (v3, SHA `bcce2f97…`) §8-2 内建验证
> **来源:** `~/dl_quant_live/live/tests_channel_causality.py` 的毒化-未来法, 移植到训练构造器
> **作废条件:** `build_wide_dl.py` 的通道构造改变 ⇒ 重跑并重定签名

THE TEST: build the panel twice off the SAME source — once clean, once with every source input
POISONED strictly after a cut row. A causal channel cannot see the poison: its rows at and before
the cut must be BIT-IDENTICAL. A channel that reads the future moves. No pattern matching, no
reading code, no opinion about which numpy API is centered — the data testifies.

★ TWO DIFFERENCES FROM THE LIVE SUITE, BOTH DELIBERATE.

  1. **NO EXEMPTION.** The live suite exempts `betaadj_ret24` and asserts its defect precisely,
     because production is frozen on it by ruling. Here the whole point is that the exemption is
     gone: this asserts **32/32** causal. If ch31 still moves, the one-line fix did not take.

  2. **THE LABELS MUST MOVE, AND BY EXACTLY THEIR HORIZON.** `Y{H}` is a FORWARD return; a forward
     target that survived the future being rewritten would be the real bug. So this does not merely
     require "the labels changed" — it pins the reach: `Y{H}` and `YR{H}` must be identical up to
     row `cut-H`, and must differ somewhere inside the final `H` rows. A one-sided "it changed"
     check passes just as happily on a label that changed for the WRONG reason, e.g. one whose
     window slid. Both edges are asserted.

  Poison is RANDOM and multiplicative, not a constant factor. A constant would leave `MEMBER110`
  untouched by construction — it is a top-110 `argsort` of DVOL30, and scaling every coin by the
  same number preserves the ranking, so a constant-poisoned membership check would pass without
  ever having been exercised.

Usage:
  python tests_panel_causality_train.py --source <wide_panel_full.npz> --clean <causal_v1.npz> \
                                        --scratch <dir> [--cut 30000]
Exit 0 = all pass.
"""
from __future__ import annotations

import argparse
import json
import os.path as _p
import sys

import numpy as np

_ROOT = _p.dirname(_p.dirname(_p.dirname(_p.dirname(_p.abspath(__file__)))))
sys.path.insert(0, _ROOT)
from multi_asset.data import build_wide_dl_causal as BC  # noqa: E402

_n_pass = 0
_fail = []


def ok(cond, label, detail=""):
    global _n_pass
    print(("  OK    " if cond else "  FAIL  ") + label + (f"  — {detail}" if detail else ""),
          flush=True)
    if cond:
        _n_pass += 1
    else:
        _fail.append(label)
    return cond


def same(a, b):
    return np.array_equal(a, b, equal_nan=True) if a.dtype.kind == "f" else np.array_equal(a, b)


def first_diff_row(a, b):
    """First row index where a and b genuinely differ, treating NaN==NaN (else every NaN reads as a
    difference and the report names an innocent row)."""
    d = ~(a == b)
    if a.dtype.kind == "f":
        d &= ~(np.isnan(a) & np.isnan(b))
    w = np.argwhere(d)
    return int(w[:, 0].min()) if len(w) else -1


class PoisonNumpy(BC.CausalNumpy):
    """CausalNumpy plus one more interception: `np.load` hands back the poisoned payload.

    Subclassing is what keeps the tested wiring identical to the shipping wiring — the causal
    convolve substitution is inherited, not re-implemented here.
    """

    def __init__(self, payload):
        super().__init__()
        self._payload = payload

    def load(self, *a, **k):
        return self._payload


def poison(source, cut, seed=20260803):
    """Return a dict payload identical to `source` at rows <= cut, garbage strictly after."""
    z = np.load(source, allow_pickle=True)
    rng = np.random.default_rng(seed)
    out = {k: z[k] for k in z.keys()}
    P = slice(cut + 1, None)
    for k, mult in (("OPEN", 3.0), ("HIGH", 3.0), ("LOW", 3.0), ("CLOSE", 3.0), ("VWAP", 3.0),
                    ("VOL", 7.0), ("QVOL", 7.0), ("DVOL30", 7.0)):
        a = z[k].copy()
        a[P] = a[P] * (mult * np.exp(rng.normal(0, 0.5, a[P].shape))).astype(a.dtype)
        out[k] = a
    f = z["FUND_EMA"].copy()
    f[P] = f[P] + (5e-3 + rng.normal(0, 1e-3, f[P].shape)).astype(f.dtype)
    out["FUND_EMA"] = f
    y = z["Y"].copy()
    y[P] = y[P] * 3.0 + rng.normal(0, 0.01, y[P].shape).astype(y.dtype)
    out["Y"] = y
    m = z["MEMBER"].copy()
    m[P] = ~m[P]
    out["MEMBER"] = m
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True)
    ap.add_argument("--clean", required=True, help="the causal panel built from --source")
    ap.add_argument("--scratch", required=True, help="dir for the poisoned build (new files only)")
    ap.add_argument("--cut", type=int, default=30000)
    ap.add_argument("--reuse", action="store_true",
                    help="reuse an existing poisoned build instead of rebuilding (same cut only)")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    CUT = a.cut

    poisoned_out = _p.join(a.scratch, "wide_dl_POISONED_probe.npz")
    if a.reuse and _p.exists(poisoned_out):
        print(f"[poison] reusing existing poisoned build {poisoned_out} (--reuse)", flush=True)
        calls, gate = "reused", "reused"
    else:
        print(f"[poison] building poisoned twin -> {poisoned_out}  (cut row {CUT})", flush=True)
        payload = poison(a.source, CUT)
        calls, gate = BC.build_causal(a.source, poisoned_out, proxy=PoisonNumpy(payload))
        print(f"[poison] build done; convolve calls={calls}", flush=True)

    C = np.load(a.clean, allow_pickle=True)
    Pz = np.load(poisoned_out, allow_pickle=True)
    names = [str(x) for x in C["ch_names"]]

    print("\n[0] the harness itself is sound")
    ok(names == [str(x) for x in Pz["ch_names"]] and len(names) == C["CH"].shape[2],
       "channel axis stable across the two builds", f"{len(names)} channels")
    ok(same(C["ts"], Pz["ts"]) and same(C["symbols"], Pz["symbols"]),
       "ts / symbols unchanged (same grid, so row indices mean the same thing in both)")
    post_moved = not np.array_equal(np.nan_to_num(C["CH"][CUT + 1:]),
                                    np.nan_to_num(Pz["CH"][CUT + 1:]))
    ok(post_moved, "★ poison actually reached the panel (post-cut rows differ) — without this "
                   "every check below passes vacuously and this suite asserts nothing")

    print(f"\n[1] all {len(names)}/{len(names)} channels are causal at rows <= {CUT} — NO EXEMPTION")
    bad = []
    for j, nm in enumerate(names):
        c0, c1 = C["CH"][: CUT + 1, :, j], Pz["CH"][: CUT + 1, :, j]
        s = np.array_equal(c0, c1, equal_nan=True)
        if not s:
            first = first_diff_row(c0, c1)
            bad.append((nm, j, first, CUT - first))
        ok(s, f"CH[:,:,{j:2d}] {nm}",
           "" if s else f"first moved row {bad[-1][2]} = cut-{bad[-1][3]}")
    ok(not bad, f"★★★ {len(names)}/{len(names)} channels unchanged at rows <= cut "
                f"(ch31's 11-hour reach is GONE — the whole point of S1)", bad[:4])

    print(f"\n[1b] ...and every channel is ALIVE — it reacts once the poison becomes its past")
    # Without this, a channel that is constant, all-zero, or otherwise dead passes [1] vacuously:
    # "did not change when the future changed" and "never changes" are the same reading there.
    dead = []
    for j, nm in enumerate(names):
        if np.array_equal(C["CH"][CUT + 1:, :, j], Pz["CH"][CUT + 1:, :, j], equal_nan=True):
            dead.append(nm)
    ok(not dead, f"all {len(names)} channels differ somewhere AFTER the cut — none passed [1] by "
                 f"being inert", dead[:6])
    j31 = names.index("betaadj_ret24")
    d31 = np.where((C["CH"][:, :, j31] != Pz["CH"][:, :, j31]).any(1))[0]
    ok(len(d31) and int(d31.min()) == CUT + 1,
       "★★ ch31 reacts at EXACTLY row cut+1 — the first row where the poison is its past. It is "
       "causal AND still reading the market series; a fix that merely broke the channel would show "
       "up here as a later reaction or none at all",
       f"first reaction row {int(d31.min()) if len(d31) else None} = cut+{int(d31.min()) - CUT if len(d31) else None}")

    print("\n[2] membership is causal too")
    ok(same(C["MEMBER110"][: CUT + 1], Pz["MEMBER110"][: CUT + 1]),
       "MEMBER110 rows <= cut unchanged (top-110 argsort of trailing DVOL30)")

    print("\n[3] the LABELS must move — and exactly within their own horizon")
    for H in (1, 4, 24):
        for pre in ("Y", "YR"):
            k = f"{pre}{H}"
            c0, c1 = C[k], Pz[k]
            deep = np.array_equal(c0[: CUT - H + 1], c1[: CUT - H + 1], equal_nan=True)
            ok(deep, f"{k}: identical at rows <= cut-{H} (reach does not exceed the horizon)",
               "" if deep else f"first moved row {first_diff_row(c0[:CUT-H+1], c1[:CUT-H+1])}")
            win0, win1 = c0[CUT - H + 1: CUT + 1], c1[CUT - H + 1: CUT + 1]
            moved = not np.array_equal(win0, win1, equal_nan=True)
            ok(moved, f"{k}: DOES move inside its final {H} row(s) — a forward target that ignored "
                      f"the future being rewritten would be the real bug")

    print("\n" + "=" * 78)
    total = _n_pass + len(_fail)
    print(f"PASS {_n_pass}/{total}" + ("" if not _fail else f"   FAILED: {_fail}"))
    if a.out:
        json.dump(dict(source=a.source, clean=a.clean, cut=CUT, n_pass=_n_pass, n_total=total,
                       failed=_fail, leaky_channels=bad, poison_reached=bool(post_moved),
                       convolve_calls=calls, wrapped_builder_gate=gate),
                  open(a.out, "w"), indent=1)
        print(f"record -> {a.out}")
    sys.exit(1 if _fail else 0)


if __name__ == "__main__":
    main()
