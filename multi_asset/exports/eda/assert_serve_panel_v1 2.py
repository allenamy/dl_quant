"""SERVE panel assertions — same battery as the causal one, against the trailing-13 convention.

> **创建:** 2026-08-03 17:1x UTC | **Session:** B4-retrain | **状态:** final
> **规格:** team-lead 裁定(SERVE 面板"全套断言照跑")
> **作废条件:** SERVE 口径定义改变 ⇒ 重写

Deliberately a SEPARATE file from `assert_causal_panel_v1.py` rather than a `--caliber` flag on it:
that script's SHA is cited in a delivered report next to its 55/55 reading, and adding a branch to it
would mean the delivered number came from bytes that no longer exist. **New generation, new file.**

To keep the two from drifting on the parts that must be identical, the comparison primitives (`eq`,
`sha256`) are IMPORTED from the causal script rather than re-typed — so "bit-identical" means the
same thing in both, by construction rather than by my care.

Asserts, against the AS-TRAINED panel:
  · 31 non-ch31 channels + 14 whole arrays bit-identical      (the SERVE change touches only ch31)
  · ch31 differs from as-trained, AND differs from the CAUSAL panel — three distinct generations,
    not two names for one thing
  · ch31 == an independent rebuild of the trailing-13 window, bit-for-bit
  · the trailing-13 window is verified by prefix-sums, independent of np.convolve
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import os.path as _p
import sys

import numpy as np

_ROOT = _p.dirname(_p.dirname(_p.dirname(_p.dirname(_p.abspath(__file__)))))
sys.path.insert(0, _ROOT)
from multi_asset.data.wide_factory import build_factors, _shift  # noqa: E402
from multi_asset.data.build_wide_dl_serve import SERVE_TAPS      # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "acp", _p.join(_p.dirname(_p.abspath(__file__)), "assert_causal_panel_v1.py"))
ACP = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ACP)
eq, sha256 = ACP.eq, ACP.sha256

LEAKY_CH = "betaadj_ret24"
WHOLE_KEYS = ACP.WHOLE_KEYS

_n_pass, _fail = 0, []


def ok(cond, label, detail=""):
    global _n_pass
    print(("  OK    " if cond else "  FAIL  ") + label + (f"  — {detail}" if detail else ""),
          flush=True)
    if cond:
        _n_pass += 1
    else:
        _fail.append(label)
    return cond


def rebuild_ch31_serve(source_panel):
    z = np.load(source_panel, allow_pickle=True)
    C = z["CLOSE"].astype(np.float64)
    logc = np.log(np.where(C > 0, C, np.nan))
    ret1 = logc - _shift(logc, 1)
    beta = build_factors(z)["beta_24h"][0]
    m = np.nan_to_num(np.nanmean(np.where(np.isfinite(ret1), ret1, np.nan), axis=1))
    serve = np.convolve(m, np.ones(SERVE_TAPS), "full")[: len(m)]      # sum(market[t-12 … t])
    v = ((logc - _shift(logc, 24)) - beta * serve[:, None]).astype(np.float32)
    return np.nan_to_num(v, nan=0.0, posinf=0.0, neginf=0.0), serve, m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--old", required=True, help="AS-TRAINED panel")
    ap.add_argument("--serve", required=True)
    ap.add_argument("--causal", required=True)
    ap.add_argument("--source", required=True)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    O = np.load(a.old, allow_pickle=True)
    S = np.load(a.serve, allow_pickle=True)
    Cz = np.load(a.causal, allow_pickle=True)
    chn = [str(x) for x in S["ch_names"]]
    J = chn.index(LEAKY_CH)

    print("[S] structural")
    ok(sorted(O.keys()) == sorted(S.keys()), "npz key sets identical to as-trained",
       f"{len(list(S.keys()))} keys")
    ok(chn == [str(x) for x in O["ch_names"]], "channel axis identical", f"{len(chn)} channels")
    ok(J == 31, "betaadj_ret24 at index 31")

    print(f"\n[A] 14 whole arrays bit-identical to as-trained")
    for k in WHOLE_KEYS:
        s, d = eq(O[k], S[k])
        ok(s, k, d)

    print(f"\n[A] all {len(chn)-1} non-ch31 channels bit-identical to as-trained")
    for j, nm in enumerate(chn):
        if j == J:
            continue
        s, d = eq(O["CH"][:, :, j], S["CH"][:, :, j])
        ok(s, f"CH[:,:,{j:2d}] {nm}", d)

    print("\n[G] three GENERATIONS, not two names for one thing")
    d_old = not np.array_equal(O["CH"][:, :, J], S["CH"][:, :, J], equal_nan=True)
    d_cau = not np.array_equal(Cz["CH"][:, :, J], S["CH"][:, :, J], equal_nan=True)
    ok(d_old, "SERVE ch31 differs from AS-TRAINED ch31",
       f"{int((O['CH'][:,:,J] != S['CH'][:,:,J]).sum())} cells")
    ok(d_cau, "SERVE ch31 differs from CAUSAL ch31 — a third caliber, and the one 0.079 refers to",
       f"{int((Cz['CH'][:,:,J] != S['CH'][:,:,J]).sum())} cells")

    print("\n[R] independent rebuild of the trailing-13 window (bit-for-bit)")
    reb, serve_w, m = rebuild_ch31_serve(a.source)
    s, d = eq(S["CH"][:, :, J], reb)
    ok(s, f"SERVE ch31 == independent trailing-{SERVE_TAPS} rebuild", d)

    pref = np.concatenate([[0.0], np.cumsum(m)])
    trail13 = np.array([pref[t + 1] - pref[max(0, t + 1 - SERVE_TAPS)] for t in range(len(m))])
    ok(np.allclose(serve_w, trail13, rtol=0, atol=1e-9),
       f"trailing-{SERVE_TAPS} window == prefix-sum computation (independent of np.convolve)",
       f"max|diff|={float(np.abs(serve_w - trail13).max()):.3e}")
    trail24 = np.array([pref[t + 1] - pref[max(0, t + 1 - 24)] for t in range(len(m))])
    ok(not np.allclose(serve_w, trail24, rtol=0, atol=1e-9),
       "trailing-13 is NOT trailing-24 — SERVE and CAUSAL are genuinely different windows",
       f"max|diff|={float(np.abs(serve_w - trail24).max()):.3e}")

    print("\n[H] artifact identity")
    for tag, path in (("as-trained", a.old), ("causal_v1", a.causal), ("serve_v1", a.serve)):
        print(f"  {tag:11s} {os.path.getsize(path)} bytes  sha256={sha256(path)}", flush=True)

    print("\n" + "=" * 78)
    total = _n_pass + len(_fail)
    print(f"PASS {_n_pass}/{total}" + ("" if not _fail else f"   FAILED: {_fail}"))
    if a.out:
        json.dump(dict(n_pass=_n_pass, n_total=total, failed=_fail, serve_taps=SERVE_TAPS,
                       serve_sha256=sha256(a.serve), serve_bytes=os.path.getsize(a.serve)),
                  open(a.out, "w"), indent=1)
        print(f"record -> {a.out}")
    sys.exit(1 if _fail else 0)


if __name__ == "__main__":
    main()
