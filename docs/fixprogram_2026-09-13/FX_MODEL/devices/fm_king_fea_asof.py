"""fm_king_fea_asof.py -- FX-MODEL new builder for TIM-01. Base: v4_chain_2026-09-09/pod_fea_ext_clamp.py
(sha256 b9f9c72816241715fc4b767950420e74f50adbbbcfc4ea77b362407ab5efa4ac), copied VERBATIM except that three
behaviours become explicit knobs. Channel order, window list, cumsum dtypes, rank rule, clipping, float16 storage,
screen thresholds and output layout are unchanged.

KNOBS (all REQUIRED env; no defaults, deliberately -- a missing or unrecognised knob refuses rather than guessing):

  FMK_CLOCK        legacy_Em1 | serve_E
      legacy_Em1 : feature/member windows are rows [E-w, E-1] (last input bar E-1) and the label is rows [E, E+47].
                   This is what the September chain trained on.
      serve_E    : windows are rows [E-w+1, E] (last input bar E, the bar closing AT the anchor, which is what
                   shadow_loop_v3.py::run_anchor serves) and the label is rows [E+1, E+48] (the accounted book window).
      Both arms are internally contiguous and causal -- features end exactly where the label begins. The difference is
      a DEFINITION SHIFT of one 5-minute bar between what was fitted and what is applied, NOT a peek at future prices.
      Note the grid differs by one anchor at the tail: serve_E needs row E+48 to exist, so it requires grid+49 <= TT.

  FMK_MEMBER_CLAMP legacy_unclamped | clamped
      legacy_unclamped : reproduces the base's MIX exactly -- covr is clamped with max(.,0) but n7/qvm/m7/v7 index an
                   unclamped E-2016. For E < 2016 that index is negative and wraps to the CACHE TAIL. Because the
                   prefix sums are non-decreasing, r2s[E]-r2s[wrapped] <= 0, so v7 collapses to 0, no name clears
                   v7 >= 1e-4, and the anchor is DELETED. That holds for any cache with T+1 > 2016, so on the real
                   axis the king meta begins at E = 2016 with zero anchors below it (measured: 30 anchors,
                   2022-01-03 00Z .. 2022-01-07 20Z, exactly the set the DL targets axis has and king does not).
      clamped    : every member statistic uses max(HI-2016, 0), as the producer does (shadow_loop_v3.py L365/L371).

  FMK_COVR_DIV     const2016 | actual_window
      const2016     : covr = finite_count / 2016 even when the window was truncated at row 0 -- the base's rule, and
                      also pod_fea_ext_e.py's. On a truncated window this UNDERSTATES coverage, so clamping alone
                      still drops early anchors: covr <= (E+1)/2016 needs E >= 1915.2 to clear 0.95.
      actual_window : covr = finite_count / actual rows in the window, as pod_dlw_targets_raw.py L90 does. This is why
                      the DL targets axis keeps all 30 early anchors while king keeps none.
      Kept separate from FMK_MEMBER_CLAMP on purpose: they are two different interventions and the review's narrowing
      (iii) forbids bundling them into one "fix" whose effect could not then be attributed.

POSITIVE CONTROL: legacy_Em1 + legacy_unclamped + const2016 must reproduce the base's FEA / y4 / members / qvk / E_ts /
names BITWISE. "Bitwise" means the ARRAYS; see fm_newbuilder_control.py for why an artifact file cannot be identical.
"""
import time, hashlib
import numpy as np
import sys
from scipy.stats import rankdata
import os as _os

_REQ = ("FMK_CACHE", "FMK_PANEL", "FMK_FEA_OUT", "FMK_META_OUT", "FMK_CLOCK", "FMK_MEMBER_CLAMP", "FMK_COVR_DIV")
_missing = [k for k in _REQ if not _os.environ.get(k)]
if _missing:
    raise SystemExit("FMK_REFUSED: required env not set, and this builder has no defaults: %s" % _missing)
CLOCK = _os.environ["FMK_CLOCK"]
MCLAMP = _os.environ["FMK_MEMBER_CLAMP"]
COVRDIV = _os.environ["FMK_COVR_DIV"]
for _k, _v, _allowed in (("FMK_CLOCK", CLOCK, ("legacy_Em1", "serve_E")),
                         ("FMK_MEMBER_CLAMP", MCLAMP, ("legacy_unclamped", "clamped")),
                         ("FMK_COVR_DIV", COVRDIV, ("const2016", "actual_window"))):
    if _v not in _allowed:
        raise SystemExit("FMK_REFUSED: %s=%r not in %s" % (_k, _v, list(_allowed)))

sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))))
sys.path.insert(0, "/workspace")
try:
    from zload import zload
except ImportError:                                     # local runs: zload lives beside the retrain scripts
    _R = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), "..", "..", "..", "..",
                                        "multi_asset", "exports", "research", "retrain_2026-09"))
    sys.path.insert(0, _R)
    from zload import zload

Z = zload(_os.environ["FMK_CACHE"], allow_pickle=True)
CTS = Z["ts"].astype(np.int64); CD = Z["data"]; syms = [str(s) for s in Z["symbols"]]
NW = len(syms); TT = CD.shape[0]
CHN = ["ret5", "range", "cpos", "log_qv", "log_cnt", "log_avgsz", "tbf"]
WINS = (48, 288, 864, 2016, 8640)
def cs_pair(x):
    fin = np.isfinite(x)
    xz = np.where(fin, x, 0).astype(np.float64)
    return (np.concatenate([np.zeros((1, NW)), np.cumsum(xz, 0)]),
            np.concatenate([np.zeros((1, NW), np.int32), np.cumsum(fin, 0, dtype=np.int32)]))
CS = {}
t0 = time.time()
for c, nm in enumerate(CHN):
    CS[nm] = cs_pair(CD[:, :, c].astype(np.float32))
    print(f"cumsum {nm} ({time.time()-t0:.0f}s)", flush=True)
r2s, r2f = cs_pair((CD[:, :, 0].astype(np.float64)) ** 2)
grid = np.where(CTS % 14400 == 0)[0]
# ─── KNOB FMK_CLOCK: the grid bound and the half-open upper index ───
if CLOCK == "legacy_Em1":
    grid = grid[(grid >= 576) & (grid + 48 <= TT)]          # base line, verbatim
    E = grid
    HI = E                                                  # half-open upper bound => last input row E-1
    LAB_LO, LAB_HI = E, E + 48                              # label rows [E, E+47]
else:
    grid = grid[(grid >= 576) & (grid + 49 <= TT)]          # serve_E needs row E+48 to exist
    E = grid
    HI = E + 1                                              # last input row E (the bar closing at the anchor)
    LAB_LO, LAB_HI = E + 1, E + 49                          # label rows [E+1, E+48]
qv_s, qv_f = CS["log_qv"]
# ─── KNOB FMK_MEMBER_CLAMP: the base clamps covr but NOT n7/qvm/m7/v7 ───
LO7_RAW = HI - 2016
LO7_CLAMPED = np.maximum(HI - 2016, 0)
LO7 = LO7_RAW if MCLAMP == "legacy_unclamped" else LO7_CLAMPED
n7 = np.maximum(qv_f[HI] - qv_f[LO7], 1)
# ─── KNOB FMK_COVR_DIV: constant 2016 vs the actual number of rows in the window ───
_covr_num = CS["ret5"][1][HI] - CS["ret5"][1][LO7_CLAMPED if MCLAMP == "legacy_unclamped" else LO7]
if COVRDIV == "const2016":
    covr = _covr_num / 2016                                 # base line, verbatim
else:
    _den = np.maximum(HI - (LO7_CLAMPED if MCLAMP == "legacy_unclamped" else LO7), 1)
    covr = _covr_num / (_den[:, None] if np.ndim(_den) == 1 else _den)
qvm = (qv_s[HI] - qv_s[LO7]) / n7
m7 = (CS["ret5"][0][HI] - CS["ret5"][0][LO7])
v7 = np.sqrt(np.maximum((r2s[HI] - r2s[LO7]) / n7 - (m7 / n7) ** 2, 0))
y4n = CS["ret5"][1][LAB_HI] - CS["ret5"][1][LAB_LO]
y4 = (CS["ret5"][0][LAB_HI] - CS["ret5"][0][LAB_LO]).astype(np.float32); y4[y4n < 46] = np.nan
MS, keep = [], []
for i in range(len(E)):
    ok = (covr[i] >= 0.95) & (v7[i] >= 1e-4) & np.isfinite(y4[i])
    m = np.where(ok)[0]
    if len(m) > 400: m = np.sort(m[np.argsort(-qvm[i, m])[:400]])
    if len(m) >= 50: MS.append(m); keep.append(i)
keep = np.array(keep); E = E[keep]; HI = HI[keep]; y4 = y4[keep]; qvk = qvm[keep]
print(f"anchors {len(E)}", flush=True)
val_names = []
VAL = []
for nm in CHN:
    s_, f_ = CS[nm]
    for w in WINS:
        Ew = np.maximum(HI - w, 0)   # E-0909-A clamp (was E - w: negative index wraps to the cache tail)
        nf = np.maximum(f_[HI] - f_[Ew], 1)
        if nm == "ret5":
            VAL.append(((s_[HI] - s_[Ew])).astype(np.float32)); val_names.append(f"{nm}_sum_{w}")
        else:
            VAL.append(((s_[HI] - s_[Ew]) / nf).astype(np.float32)); val_names.append(f"{nm}_mean_{w}")
for w in WINS:
    Ew = np.maximum(HI - w, 0)   # E-0909-A clamp
    nf = np.maximum(CS["ret5"][1][HI] - CS["ret5"][1][Ew], 1)
    mm = (CS["ret5"][0][HI] - CS["ret5"][0][Ew]) / nf
    vv = np.sqrt(np.maximum((r2s[HI] - r2s[Ew]) / nf - mm ** 2, 0))
    VAL.append(vv.astype(np.float32)); val_names.append(f"vol_{w}")
del CS, r2s, r2f, CD
PW = np.load(_os.environ["FMK_PANEL"], allow_pickle=True)
pw_row = {int(t): j for j, t in enumerate(PW["ts"].astype(np.int64))}
FUND = [PW["f_fund_ema"], PW["f_fund_now"]]
fund_names = ["fund_ema", "fund_now"]
NVAL = len(VAL); NF = NVAL * 2 + len(FUND)
print(f"NF = {NVAL}值 + {NVAL}秩 + {len(FUND)}funding = {NF}", flush=True)
FEA = np.full((len(E), NW, NF), np.nan, np.float16)
t1 = time.time()
for i in range(len(E)):
    m = MS[i]
    col = 0
    for v in VAL:
        x = v[i, m]
        FEA[i, m, col] = np.clip(np.nan_to_num(x, nan=0), -1e4, 1e4); col += 1
        ok = np.isfinite(x); rr = np.zeros(len(m), np.float32)
        if ok.sum() >= 10:
            rr[ok] = rankdata(x[ok]) / max(ok.sum() - 1, 1) - 0.5
        FEA[i, m, col] = rr; col += 1
    j = pw_row.get(int(CTS[E[i]]))
    if j is not None:
        for fv in FUND:
            FEA[i, m, col] = np.nan_to_num(fv[j, m], nan=0); col += 1
    if i % 2000 == 0: print(f"fea {i}/{len(E)} ({time.time()-t1:.0f}s)", flush=True)
np.save(_os.environ["FMK_FEA_OUT"], FEA)
np.savez_compressed(_os.environ["FMK_META_OUT"], E_ts=CTS[E], members=np.array(MS, dtype=object),
                    y4=y4, qvk=qvk.astype(np.float32), names=np.array([n + s for n in val_names for s in ("_v", "_r")] + fund_names),
                    fm_knobs=np.array([CLOCK, MCLAMP, COVRDIV]),
                    fm_base_sha256=np.array(["b9f9c72816241715fc4b767950420e74f50adbbbcfc4ea77b362407ab5efa4ac"]))
print(f"FEA_EXT_DONE {FEA.shape} knobs clock={CLOCK} member_clamp={MCLAMP} covr_div={COVRDIV}", flush=True)
