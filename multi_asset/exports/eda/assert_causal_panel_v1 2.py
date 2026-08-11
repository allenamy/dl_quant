"""S1 clause-(a) assertion battery — the clean panel differs from the as-trained panel in ch31 ONLY.

> **创建:** 2026-08-03 16:1x UTC | **Session:** B4-retrain | **状态:** final — 预注册条款 (a) 的可执行形式
> **规格:** `PREREG_retrain_causal_panel_2026-08-03.md` (v3, SHA `bcce2f97…`) §3-1
> **作废条件:** 条款 (a) 的清单改变 ⇒ 本文件须同步改

Prereg §3-1 spells the assertion out and then says the interesting thing about it:

    「★ 它预期会通过, 所以价值在失败时」

so this script is written to be informative WHEN RED: every comparison reports the first offending
row/column, not just a boolean.

★ ch31 IS NOT CHECKED BY A DELTA. A delta test ("new − old == −beta·Δmkt24") shares the panel's own
  arithmetic with the thing it is checking, so a builder that applied the intended change to the
  WRONG QUANTITY could still satisfy it. Instead both ch31 columns are rebuilt from the SOURCE panel
  by an independent implementation of the two window conventions, in the same float64 → float32
  order the builder uses, and required to match BIT-FOR-BIT. That makes the claim "the new panel is
  the causal one and the old panel is the centered one" testable on its own terms rather than
  relative to each other.

Usage:
  python assert_causal_panel_v1.py --old <as_trained.npz> --new <causal_v1.npz> --source <wide_panel_full.npz>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import os.path as _p
import sys

import numpy as np

_ROOT = _p.dirname(_p.dirname(_p.dirname(_p.dirname(_p.abspath(__file__)))))
sys.path.insert(0, _ROOT)
from multi_asset.data.wide_factory import build_factors, _shift  # noqa: E402

LEAKY_CH = "betaadj_ret24"
WHOLE_KEYS = ["ts", "symbols", "ch_names", "baseline_cols", "MEMBER110",
              "CL1", "CL4", "CL24", "Y1", "Y4", "Y24", "YR1", "YR4", "YR24"]

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


def eq(a, b):
    """array_equal with NaN treated as equal where the dtype can hold one."""
    if a.shape != b.shape or a.dtype != b.dtype:
        return False, f"shape/dtype {a.shape}/{a.dtype} vs {b.shape}/{b.dtype}"
    if a.dtype.kind == "f":
        same = np.array_equal(a, b, equal_nan=True)
    else:
        same = np.array_equal(a, b)
    if same:
        return True, ""
    d = np.argwhere(~((a == b) | (_isnan(a) & _isnan(b))))
    return False, f"{len(d)} differing cells, first at {tuple(d[0])}"


def _isnan(a):
    return np.isnan(a) if a.dtype.kind == "f" else np.zeros(a.shape, bool)


def sha256(path, buf=1 << 22):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(buf), b""):
            h.update(chunk)
    return h.hexdigest()


def rebuild_ch31(source_panel):
    """Independent rebuild of ch31 under BOTH window conventions, mirroring the builder's dtype
    order exactly: float64 arithmetic -> np.float32 cast -> nan_to_num(0.0)."""
    z = np.load(source_panel, allow_pickle=True)
    C = z["CLOSE"].astype(np.float64)
    logc = np.log(np.where(C > 0, C, np.nan))
    ret1 = logc - _shift(logc, 1)
    F = build_factors(z)
    beta = F["beta_24h"][0]
    market = np.nanmean(np.where(np.isfinite(ret1), ret1, np.nan), axis=1)
    m = np.nan_to_num(market)
    same = np.convolve(m, np.ones(24), "same")                 # centered  -> input[t-12 … t+11]
    causal = np.convolve(m, np.ones(24), "full")[: len(m)]     # trailing  -> input[t-23 … t]
    ret24 = logc - _shift(logc, 24)
    out = {}
    for nm, mk in (("same", same), ("causal", causal)):
        v = (ret24 - beta * mk[:, None]).astype(np.float32)
        out[nm] = np.nan_to_num(v, nan=0.0, posinf=0.0, neginf=0.0)
    return out, same, causal


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--old", required=True, help="the AS-TRAINED panel (frozen heads were fitted on it)")
    ap.add_argument("--new", required=True, help="the S1 clean panel")
    ap.add_argument("--source", required=True, help="source wide_panel used by both builds")
    ap.add_argument("--out", default=None, help="where to write the JSON record")
    a = ap.parse_args()

    print(f"OLD  {a.old}\nNEW  {a.new}\nSRC  {a.source}\n", flush=True)
    O = np.load(a.old, allow_pickle=True)
    Nw = np.load(a.new, allow_pickle=True)

    print("[S] structural / lineage")
    ko, kn = sorted(O.keys()), sorted(Nw.keys())
    ok(ko == kn, "npz key sets identical", f"old {len(ko)} / new {len(kn)}"
       + ("" if ko == kn else f"  only-old={set(ko)-set(kn)} only-new={set(kn)-set(ko)}"))
    shp = [(k, O[k].shape, O[k].dtype, Nw[k].shape, Nw[k].dtype) for k in ko if k in kn]
    ok(all(s[1] == s[3] and s[2] == s[4] for s in shp), "every shared key has identical shape+dtype",
       "; ".join(f"{s[0]}:{s[1]}{s[2]}" for s in shp[:3]) + " …")

    chn_o = [str(x) for x in O["ch_names"]]
    chn_n = [str(x) for x in Nw["ch_names"]]
    ok(chn_o == chn_n, "channel axis identical", f"{len(chn_n)} channels")
    ok(chn_n.count(LEAKY_CH) == 1, "exactly one channel named " + LEAKY_CH)
    J = chn_n.index(LEAKY_CH)
    ok(J == 31, f"{LEAKY_CH} is at index 31 (the prereg's 'ch31')", f"idx={J}")

    print("\n[A] clause (a) — 14 whole arrays bit-identical (NaN positions included)")
    for k in WHOLE_KEYS:
        same, det = eq(O[k], Nw[k])
        ok(same, f"{k}", det)

    print(f"\n[A] clause (a) — all {len(chn_n) - 1} non-ch31 channels bit-identical")
    CHo, CHn = O["CH"], Nw["CH"]
    per_ch = {}
    for j, nm in enumerate(chn_n):
        if j == J:
            continue
        same, det = eq(CHo[:, :, j], CHn[:, :, j])
        per_ch[nm] = same
        ok(same, f"CH[:,:,{j:2d}] {nm}", det)

    print(f"\n[A] clause (a) — ch31 MUST differ")
    d31 = not np.array_equal(CHo[:, :, J], CHn[:, :, J], equal_nan=True)
    nd = int((CHo[:, :, J] != CHn[:, :, J]).sum())
    ok(d31, f"CH[:,:,{J}] {LEAKY_CH} differs between the two panels",
       f"{nd} of {CHo.shape[0] * CHo.shape[1]} cells differ")

    print("\n[R] independent rebuild of ch31 under both conventions (bit-for-bit)")
    reb, mk_same, mk_causal = rebuild_ch31(a.source)
    s_old, det_old = eq(CHo[:, :, J], reb["same"])
    ok(s_old, "OLD ch31 == independent CENTERED('same') rebuild", det_old)
    s_new, det_new = eq(CHn[:, :, J], reb["causal"])
    ok(s_new, "NEW ch31 == independent CAUSAL(trailing-24) rebuild", det_new)

    # the causal window, verified against a cumulative-sum identity rather than against convolve
    z = np.load(a.source, allow_pickle=True)
    C = z["CLOSE"].astype(np.float64)
    logc = np.log(np.where(C > 0, C, np.nan))
    ret1 = logc - _shift(logc, 1)
    m = np.nan_to_num(np.nanmean(np.where(np.isfinite(ret1), ret1, np.nan), axis=1))
    pref = np.concatenate([[0.0], np.cumsum(m)])
    trail = np.array([pref[t + 1] - pref[max(0, t + 1 - 24)] for t in range(len(m))])
    ok(np.allclose(mk_causal, trail, rtol=0, atol=1e-9),
       "causal mkt24 == trailing-24 sum computed by prefix-sums (independent of np.convolve)",
       f"max|diff|={float(np.abs(mk_causal - trail).max()):.3e}")
    ok(not np.allclose(mk_same, trail, rtol=0, atol=1e-9),
       "centered mkt24 is NOT the trailing sum (the two conventions really are different)",
       f"max|diff|={float(np.abs(mk_same - trail).max()):.3e}")

    print("\n[H] artifact identity")
    for tag, path in (("old", a.old), ("new", a.new)):
        sz = os.path.getsize(path)
        print(f"  {tag}: {path}\n      size={sz} bytes  sha256={sha256(path)}", flush=True)

    print("\n" + "=" * 78)
    total = _n_pass + len(_fail)
    print(f"PASS {_n_pass}/{total}" + ("" if not _fail else f"   FAILED: {_fail}"))
    rec = dict(old=a.old, new=a.new, source=a.source, n_pass=_n_pass, n_total=total,
               failed=_fail, ch31_index=J, ch31_cells_differing=nd,
               old_sha256=sha256(a.old), new_sha256=sha256(a.new),
               old_bytes=os.path.getsize(a.old), new_bytes=os.path.getsize(a.new))
    if a.out:
        json.dump(rec, open(a.out, "w"), indent=1)
        print(f"record -> {a.out}")
    sys.exit(1 if _fail else 0)


if __name__ == "__main__":
    main()
