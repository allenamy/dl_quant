"""S1 clean-panel builder — `build_wide_dl.py` with EXACTLY ONE change: ch31's `mkt24` goes causal.

> **创建:** 2026-08-03 16:0x UTC | **Session:** B4-retrain | **状态:** final — S1 面板构造器
> **规格:** `exports/eda/PREREG_retrain_causal_panel_2026-08-03.md` (v3, SHA `bcce2f97…`) §3-1 条款 (a)
> **作废条件:** 被包装的 `build_wide_dl.py` 的 pre-`savez` 段改变 ⇒ 本文件的 PIN 断言会自己变红并拒绝构建

WHAT THIS IS
------------
`data/build_wide_dl.py:124` builds the market-return window for `betaadj_ret24` (ch31) with

    mkt24 = np.convolve(np.nan_to_num(market), np.ones(24), "same")

`"same"` is CENTERED: `out[t]` draws on `input[t-12 … t+11]`, i.e. **11 hours of future market
return** (RESULT_channel_cutoff_audit_2026-08-03.md SHA `eedab22a…`, §2). This module produces the
same panel with the trailing-24 causal window instead:

    mkt24 = np.convolve(np.nan_to_num(market), np.ones(24), "full")[:T]   ->  sum(market[t-23 … t])

WHY IT WRAPS RATHER THAN COPIES
-------------------------------
S1 is a ONE-VARIABLE experiment (prereg §6 clause (f)). A copy-edit of the 200-line builder would
make "only that line changed" a claim about my editing; wrapping the original module makes it a
property of the call graph. The single change is injected by handing the wrapped module a numpy
proxy whose `convolve` is causal — so every other line executes the ORIGINAL bytes.

★ THE PROXY IS ALSO THE ASSERTION. It refuses any convolve call that is not the one we came for
  (mode != "same", kernel != ones(24)) and counts invocations; `build_causal` then requires the
  count to be exactly 1. "There is only one convolve in this file" stops being something I read and
  becomes something the run proves.

★ WHAT THE PIN BUYS. `wide_dl_full.npz` — the AS-TRAINED panel the frozen king/s2 heads were fitted
  on — was built 2026-07-11 by revision efecc05. This module pins the SHA-256 of the wrapped
  source UP TO AND INCLUDING `np.savez`, and efecc05 and the server's a58b3a8 hash IDENTICALLY
  there (`ca023f9d…`): a58b3a8's only delta is the funding gate, which runs AFTER the panel is
  written and therefore cannot touch its content. So the pin says the thing that actually matters —
  *the bytes that produce the arrays are the bytes that produced the as-trained arrays* — instead of
  the weaker "the file has the same name". A caliber-stamped or otherwise edited builder hashes
  differently and this module refuses to run at all.

Run:  python multi_asset/data/build_wide_dl_causal.py <source_panel.npz> <out.npz>
"""
from __future__ import annotations

import hashlib
import os.path as _p
import sys as _sys

import numpy as np

_sys.path.insert(0, _p.dirname(_p.dirname(_p.dirname(_p.abspath(__file__)))))

from multi_asset.data import build_wide_dl as _ORIG  # noqa: E402  the module whose bytes we reuse

# --- pinned provenance of the wrapped builder ------------------------------------------------
# sha256 of _ORIG's source text truncated after the `np.savez(f, **out)` line. Identical for
# efecc05 (built wide_dl_full.npz, 2026-07-11) and a58b3a8 (server copy) — verified by
# `git show <rev>:multi_asset/data/build_wide_dl.py`.
PRESAVEZ_SHA = "ca023f9de6291c60a084449a56e43c01"      # first 32 hex of the prefix digest
SAVEZ_MARK = "np.savez(f, **out)"
LEAKY_LINE = 'mkt24 = np.convolve(np.nan_to_num(market), np.ones(24), "same")'
KERNEL = 24
LEAKY_CH = "betaadj_ret24"


def _wrapped_source() -> str:
    with open(_ORIG.__file__, "r") as fh:
        return fh.read()


def _presavez_digest(src: str) -> str:
    i = src.index(SAVEZ_MARK)
    j = src.index("\n", i)
    return hashlib.sha256(src[: j + 1].encode()).hexdigest()


def assert_wrapped_source(verbose=True):
    """Refuse to build unless the wrapped module is the one whose bytes made the as-trained panel.

    Returns the per-check dict so a caller can record it; raises SystemExit on any failure —
    a build that proceeds past a broken premise is worth less than no build.
    """
    src = _wrapped_source()
    n_convolve = src.count("convolve")
    dig = _presavez_digest(src)
    savez_at = src.index(SAVEZ_MARK)
    checks = {
        "presavez_sha_matches_as_trained_builder": (dig[:32] == PRESAVEZ_SHA, f"{dig[:32]}"),
        "exactly_one_convolve_in_wrapped_source": (n_convolve == 1, f"count={n_convolve}"),
        "leaky_line_present_verbatim": (LEAKY_LINE in src, ""),
        # the funding gate is a subprocess call; it must sit AFTER the write, so that whatever it
        # does it provably cannot alter the arrays this module is here to produce.
        "subprocess_call_is_after_savez": (
            all(k > savez_at for k in _find_all(src, "subprocess.call")),
            f"savez@{savez_at}, calls@{_find_all(src, 'subprocess.call')}"),
    }
    if verbose:
        for k, (okv, det) in checks.items():
            print(f"  [{'OK  ' if okv else 'FAIL'}] {k}" + (f"  — {det}" if det else ""), flush=True)
    bad = [k for k, (okv, _) in checks.items() if not okv]
    if bad:
        raise SystemExit(
            f"[causal] REFUSING TO BUILD: wrapped builder is not the as-trained revision — {bad}.\n"
            f"  The single-variable premise of S1 (prereg §6 clause (f)) rests on every non-ch31\n"
            f"  byte being the byte that produced exports/wide_dl_full.npz. It is not. Do not\n"
            f"  'update the pin' — find out which revision is on this machine and why.")
    return checks


def _find_all(s, sub):
    out, i = [], s.find(sub)
    while i != -1:
        out.append(i)
        i = s.find(sub, i + 1)
    return out


class CausalNumpy:
    """numpy, except `convolve` is the trailing-K causal sum — and refuses anything else.

    Installed into the wrapped module's globals for the duration of the build, so the module's
    own `np.` lookups (including inside `_xsec_residualize` and the nested `_xsr`) resolve here.
    Every attribute other than `convolve` is forwarded untouched to the real numpy.
    """

    def __init__(self):
        self.calls = []

    def __getattr__(self, name):                     # only reached for names not defined here
        return getattr(np, name)

    def convolve(self, a, v, mode="full"):
        v = np.asarray(v)
        rec = dict(mode=mode, klen=int(v.size), kernel_all_ones=bool(np.all(v == 1.0)),
                   alen=int(np.size(a)))
        self.calls.append(rec)
        if mode != "same" or v.size != KERNEL or not np.all(v == 1.0):
            raise AssertionError(
                f"[causal] unexpected convolve {rec}. This proxy exists to rewrite EXACTLY the "
                f"ch31 market window; a second convolve means the wrapped builder changed and the "
                f"one-line premise no longer holds.")
        return np.convolve(a, v, "full")[: np.size(a)]      # sum(a[t-23 … t]) — trailing, causal


def build_causal(panel, outpath, proxy=None):
    """Build the S1 clean panel. Returns (proxy_call_records, gate_report).

    `proxy` lets the behavioural causality suite drive THIS SAME wiring with a subclass that also
    intercepts `np.load` (to feed poisoned inputs). Sharing the path matters: a test that re-created
    the injection itself would be testing its own copy of the wiring, not the wiring that built the
    panel.
    """
    print(f"[causal] wrapped builder: {_ORIG.__file__}", flush=True)
    assert_wrapped_source()

    proxy = CausalNumpy() if proxy is None else proxy
    saved = _ORIG.np
    gate = {"ran": False, "raised": None}
    try:
        _ORIG.np = proxy
        try:
            _ORIG.build(panel=panel, outpath=outpath)
            gate["ran"] = True
        except SystemExit as e:
            # The wrapped builder ends with the funding-dimension gate, which lives AFTER the write
            # (asserted above). It is NOT silenced here: whatever it says is recorded and reported.
            gate["ran"] = True
            gate["raised"] = str(e)
    finally:
        _ORIG.np = saved

    n = len(proxy.calls)
    if n != 1:
        raise SystemExit(f"[causal] convolve was called {n} times, expected exactly 1: {proxy.calls}")
    print(f"[causal] convolve proxy invoked exactly once: {proxy.calls[0]}", flush=True)
    if gate["raised"]:
        print(f"[causal] wrapped builder's post-write funding gate raised:\n    {gate['raised']}",
              flush=True)
    return proxy.calls, gate


if __name__ == "__main__":
    if len(_sys.argv) < 3:
        raise SystemExit("usage: build_wide_dl_causal.py <source_panel.npz> <out_causal.npz>")
    build_causal(_sys.argv[1], _sys.argv[2])
