#!/usr/bin/env python3
"""cf_lib.py — shared library for CF3 (three-signal counterfactual re-chaining).
PREREG: docs/PREREG_three_signal_counterfactual_2026-09-20.md (frozen before any number).

════════ THE PRODUCTION DEFINITION, COPIED VERBATIM (file:line + code) ════════
Object-B replay copy of the producer's combo stage:
  /workspace/object_b_2026-09-19/devices/combo_stage_replay_3520d363.py
  (generated from ~/wide_shadow/fea171/combo_stage.py sha256 3520d363...; production line numbers = replay - 3)

  L232  w3m = np.array([w3[0], 0.0, w3[2]])
  L233  w3m = w3m / w3m.sum() if w3m.sum() > 1e-12 else np.array([0.5, 0.0, 0.5])
  L234  z_kc = w3m[0] * np.nan_to_num(legz["king"]) + w3m[2] * np.nan_to_num(legz["fund"])
  L235  z_fc = w3m[0] * np.nan_to_num(zf)           + w3m[2] * np.nan_to_num(legz["fund"])
  L251  z_kc = np.where(_band_kc, 0.0, z_kc)
  L252  z_fc = np.where(_band_fc, 0.0, z_fc)
  L268  H = H_kc_prev; sm_kc = chain(z_kc)
  L269  H = H_fc_prev; sm_fc = chain(z_fc)
  L274  combo_raw = 0.55 * sm_kc + 0.45 * sm_fc
  L81   def chain(zc): ...                       <- reproduced verbatim in Chain.run below

The producer's own run_anchor (shadow_loop_v3_replay.py, from e9c98374):
  L332  CDf = st.cd.astype(np.float32)
  L348  qseg = CDf[max(ai + 1 - 2016, 0):ai + 1, :, 3]; finq = np.isfinite(qseg)
  L350  qvm  = np.where(finq, qseg, 0).sum(0) / np.maximum(finq.sum(0), 1)
  L450  qv4h = np.expm1(np.clip(qvm[m], 0, 30)) * 48
  L451  sel  = qv4h >= P["qv4h_min"]
  L405  seg  = CDf[pi + 1:ai + 1, :, 0]; fin = np.isfinite(seg)
  L407  y4v  = np.where(fin, seg, 0).sum(0); y4v[fin.sum(0) < 46] = np.nan
  L410-416  per leg: z = prev legz; okl = isfinite(y4v[pm]); zz = where(okl, z, 0); zz -= zz[okl].mean()
            g = |zz|.sum(); LR[leg].append((zz/g * nan_to_num(y4v[pm])).sum() * 1e4 if g > 1e-9 else 0.0)
  L433-437  look = 900; r = stack(LR[leg][-900:]); shp = r.mean(1)/(r.std(1)+1e-9); shp = max(shp,0)
            w3 = shp/shp.sum() if shp.sum() > 0 else [1/3]*3
  L298-329  funding ledger: per base name, skip if anchor - last_ts < exp_iv*3600*0.9; else rows in
            (last_ts, anchor], limit 100; iv = (ft - prev_ft)/3600 snapped to {1,2,4,6,8}; rows = [ft, rate, iv]
  L541-544  state/weights/<A>.npz stores val = sm[wnz].astype(np.float32) for |sm| > 1e-9   <- float32!
"""
import hashlib
import json
import os
import sys
import time

import numpy as np
from scipy.stats import rankdata

OBJB = "/workspace/object_b_2026-09-19"
ROOT = "/workspace/cf3_2026-09-20"
NW = 829
H4 = 14400

# ── pinned inputs (verified by sha256 before any work) ────────────────────────
PINS = {
    "P1VEC":    (f"{OBJB}/work/A0_main/P1.vec.npz", "04249082f6b9d42b3e93482e467e5552fe9f0603d51dadb8c8152568c260b49d"),
    "P2SCORES": (f"{OBJB}/work/A0_main/P2_SCORES.npz", "06d3dc8972e097623c9f83df48a8a621b5d6f189f0ed78f4348d6202a9b6751a"),
    "P3VEC":    (f"{OBJB}/work/A0_main/P3.vec.npz", "dae0107140673c98f346073733a99b48aea33b002a51ea6c660bb75aac554d92"),
    "P3JSON":   (f"{OBJB}/work/A0_main/P3.json", "cff3e160f4a4961e97043cdcdb93a105c24694f83931509dc5539bac72826bcd"),
    "TARGETS":  (f"{OBJB}/work/A0_main/TARGETS_A0_main.npz",
                 "b9f0dc9f2011f9defaac80b116415de3f4d75ffb497cbb9533cd995879036c41"),
    "LRLIVE":   (f"{OBJB}/work/A0_main/rh_p3/state/leg_returns_live.json", "e2a2a9cdf3f7085e57fc562348f7ccd5db5eca48047361743addf613958ddebe"),
    "STAGE":    (f"{OBJB}/devices/combo_stage_replay_3520d363.py",
                 "92c49fa82d4c5c1bdb70c6155c0c3e7bfe3c5f012e1db0aeb686ef1fbcd6e1d8"),
    "PRODUCER": (f"{OBJB}/devices/shadow_loop_v3_replay.py",
                 "4d3bc157f03e3462a69e64f817b3fd4cd51be4c03d72650304b7d0c1a0089d42"),
    "BDRIVER":  (f"{OBJB}/devices/b_driver.py", None),
    "BLIB":     (f"{OBJB}/devices/b_lib.py", None),
}


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def iso(t):
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(t)))


class Checks:
    """every check is named; the verdict line prints the failed list, never a bare N/N count."""

    def __init__(self, t0):
        self.items = []
        self.fails = []
        self.t0 = t0

    def __call__(self, name, ok, detail=None):
        self.items.append({"check": name, "ok": bool(ok), "detail": detail})
        if not ok:
            self.fails.append(name)
        return bool(ok)


def rec_head(device, argv):
    return {"device": device, "self_sha256": sha(os.path.abspath(sys.argv[0])), "argv": list(argv),
            "env": dict(os.environ), "python": sys.version.split()[0], "numpy": np.__version__,
            "utc_start": iso(time.time()), "prereg": "docs/PREREG_three_signal_counterfactual_2026-09-20.md"}


def write_receipt(rec, chk, path, verdict):
    rec["checks"] = chk.items
    rec["failed"] = chk.fails
    rec["verdict"] = verdict
    rec["runtime_s"] = round(time.time() - chk.t0, 1)
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(rec, f, indent=1, default=float)
    os.replace(tmp, path)
    return sha(path)


def bitwise_equal(a, b):
    """uint64 view equality of two float64 arrays of the same shape (NaN-safe, -0.0 != 0.0 is reported)."""
    a = np.ascontiguousarray(np.asarray(a, np.float64))
    b = np.ascontiguousarray(np.asarray(b, np.float64))
    if a.shape != b.shape:
        return False, -1
    ne = a.view(np.uint64) != b.view(np.uint64)
    return (not ne.any()), int(ne.sum())


# ── the chain, VERBATIM from combo_stage_replay_3520d363.py L81-L105 ─────────
class Chain:
    """One anchor's chain context. `run(zc, H)` is the replay's `chain(zc)` with the globals it closes over
    (sel, pm, NW, P, LIVE_MASK, H) passed in explicitly. The body below is copied statement for statement;
    the only edits are `self.` prefixes on the closed-over names and `H` as an argument."""

    def __init__(self, sel, pm, P, LIVE_MASK, NW=NW):
        self.sel, self.pm, self.P, self.LIVE_MASK, self.NW = sel, pm, P, LIVE_MASK, NW

    def run(self, zc, H):
        sel, pm, P, LIVE_MASK, NW = self.sel, self.pm, self.P, self.LIVE_MASK, self.NW
        w = np.where(sel, zc, 0.0)
        w = np.where(sel, w - (w[sel].mean() if sel.any() else 0), w)
        g = np.abs(w).sum()
        if g < 1e-9:
            return None
        w = w / g
        capw = P["cap_mult"] / max(int(sel.sum()), 1)
        w = np.clip(w, -capw, capw)
        g2 = np.abs(w).sum()
        if g2 > 1e-9:
            w = w / g2
        tgt = np.zeros(NW)
        tgt[pm] = w
        smv = H + P["alpha"] * (tgt - H)
        trade = smv - H
        smv = np.where(np.abs(trade) < P["band"], H, smv)
        _keep_liq = np.zeros(NW, bool)
        _keep_liq[pm[sel]] = True
        keep = (LIVE_MASK.copy() if LIVE_MASK is not None else np.ones(NW, bool))
        if LIVE_MASK is not None:
            _mm = np.zeros(NW, bool)
            _mm[pm] = True
            keep &= _mm
        keep &= _keep_liq
        leave = (~keep) & (np.abs(smv) > 1e-12)
        smv = np.where(leave, 0.0, smv)
        return smv


def zf_from_scores(scores):
    """combo_stage L175-176 on the object-B injection (b_lib.write_f10_injection + identity model):
    the stage uses f10 only through rankdata(f10_pm[okf]), and the injection encodes rank/128 exactly,
    so zf is bitwise the production zf of `scores`."""
    v = np.asarray(scores, np.float64)
    okf = np.isfinite(v)
    zf = np.full(len(v), np.nan)
    if okf.any():
        zf[okf] = rankdata(v[okf]) / max(int(okf.sum()) - 1, 1) - 0.5
    return zf, okf


def h_from_weights_file(vec_full):
    """state/weights/<A>.npz writes val = sm[|sm|>1e-9].astype(np.float32); the stage loads it back as float64."""
    wnz = np.where(np.abs(vec_full) > 1e-9)[0]
    H = np.zeros(NW)
    H[wnz] = vec_full[wnz].astype(np.float32).astype(np.float64)
    return H


# ── CSR helpers for the archived vectors ────────────────────────────────────
def csr(Z, name, k):
    o = Z[name + "_off"]
    a, b = int(o[k]), int(o[k + 1])
    return Z[name + "_idx"][a:b].astype(np.int64), Z[name + "_val"][a:b].astype(np.float64)


def csr_dense(Z, name, k, n=NW):
    i, v = csr(Z, name, k)
    out = np.zeros(n)
    out[i] = v
    return out


def pm_of(Z, k):
    o = Z["pm_off"]
    return Z["pm"][int(o[k]):int(o[k + 1])].astype(np.int64)


# ── periods (PREREG §7.1) ───────────────────────────────────────────────────
def ts(s):
    return int(time.mktime(time.strptime(s, "%Y-%m-%dT%H:%M:%SZ")) - time.timezone)


PERIODS = {
    "HIST":         ("2023-06-30T04:00:00Z", "2025-12-31T20:00:00Z"),
    "2026":         ("2026-01-01T00:00:00Z", "2026-08-31T00:00:00Z"),
    "FULL_RECIPE":  ("2023-06-30T04:00:00Z", "2026-08-31T00:00:00Z"),
    "PRE":          ("2022-06-30T00:00:00Z", "2023-06-30T00:00:00Z"),
    "ALL_2022_06":  ("2022-06-30T00:00:00Z", "2026-08-31T00:00:00Z"),
}


def period_mask(A, name):
    lo, hi = PERIODS[name]
    return (A >= ts(lo)) & (A <= ts(hi))


# ── the eight coalitions (PREREG §5) ────────────────────────────────────────
ARMS = {
    "BASE":     (1, 1, 1),
    "noFUND":   (0, 1, 1),
    "noKING":   (1, 0, 1),
    "noF10":    (1, 1, 0),
    "onlyFUND": (1, 0, 0),
    "onlyKING": (0, 1, 0),
    "onlyF10":  (0, 0, 1),
    "NONE":     (0, 0, 0),
}
ARM_ORDER = ["BASE", "noFUND", "noKING", "noF10", "onlyFUND", "onlyKING", "onlyF10", "NONE"]
