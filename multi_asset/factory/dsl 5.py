"""Factory — formula DSL: parser + type system + vectorized evaluator.

Implements the frozen design (`factory/DSL_DESIGN.md`) + the 0C protocol (`exports/eda/factory_prereg.md`).
Everything here is a HARD constraint in code, not a runbook note:

  (i)   all trailing reductions use center=False (asserted; `_roll` refuses center=True).
  (ii)  NaN cells are EXCLUDED from every reduction (min-periods / masked), NEVER 0-filled. div/zscore
        use an eps floor and return NaN (not inf/0) on degenerate input.
  (iii) SPARSE leg columns (king/s2/funding_leg/size_leg — defined only at anchors) are rejected by the
        TYPE SYSTEM if fed to any temporal operator; legs enter only pointwise / cross-sectional /
        conditional operators. (parser-level, not runtime.)
  (iv)  ts_rank / ts_corr on a degenerate (zero-variance) window return NaN -> excluded from scoring.

Depth <= 6, operator count <= 12 (factory_prereg §3). Trailing-only is structural: no operator can index
the future, so every tree is causal by construction.
"""
from __future__ import annotations

import ast
import hashlib

import numpy as np
import pandas as pd
from numpy.lib.stride_tricks import sliding_window_view

MAX_DEPTH = 6
MAX_OPS = 12

# ---- operands: frozen channel + leg names (xsr_* removed per factory_prereg §1) -----------------
DENSE_CHANNELS = [
    "funding_ema", "mom_4h", "mom_8h", "mom_24h", "mom_72h", "mom_168h", "rev_1h", "rev_3h",
    "rvol_24h", "dvol_24h", "rvol_72h", "dvol_72h", "beta_24h", "beta_72h", "lturnover_24h",
    "illiq_72h", "size_dvol", "max_ret_24h", "gtja_046", "a101_044", "ret_1h", "ret_4h",
    "ret_12h", "ret_24h", "rvol_6h", "logqvol", "betaadj_ret24",
]                                                    # 27 dense (xsr_* excluded)
LEG_COLUMNS = ["king", "s2", "funding_leg", "size_leg"]   # SPARSE (anchor-only)

DENSE, SPARSE = "DENSE", "SPARSE"
EPS = 1e-9


class DSLError(ValueError):
    """parse/type/complexity violation — the formula is rejected before any evaluation."""


# ---- vectorized primitives (operate on (T,N) float arrays; NaN = missing, never 0) ---------------
def _roll(A, w, center=False):
    if center:
        raise DSLError("centered rolling window would peek at the future — center=True is forbidden")
    return pd.DataFrame(A).rolling(int(w), min_periods=max(2, int(w) // 2), center=False)


def ts_delta(A, n):   return A - _shift(A, int(n))
def ts_mean(A, n):    return _roll(A, n).mean().to_numpy()
def ts_std(A, n):     return _roll(A, n).std().to_numpy()
def ts_min(A, n):     return _roll(A, n).min().to_numpy()
def ts_max(A, n):     return _roll(A, n).max().to_numpy()
def ts_zscore(A, n):
    m = ts_mean(A, n); s = ts_std(A, n)
    return np.where(s > EPS, (A - m) / np.where(s > EPS, s, np.nan), np.nan)


def ema(A, span):
    return pd.DataFrame(A).ewm(span=int(span), adjust=False, min_periods=1).mean().to_numpy()


def ts_rank(A, n):
    """centered trailing-window rank of x_t in [-0.5, 0.5]. Vectorized (no rolling.apply). NaN-aware;
    zero-variance window -> NaN (constraint iv). center=False by construction (windows end at t)."""
    n = int(n); T, N = A.shape; out = np.full((T, N), np.nan)
    if T < n:
        return out
    win = sliding_window_view(A, n, axis=0)              # (T-n+1, N, n); last axis ends at t
    last = win[:, :, -1]; finite = np.isfinite(win); cnt = finite.sum(-1)
    le = (win <= last[:, :, None]).sum(-1)               # NaN comparisons are False -> excluded
    sd = np.where(finite, win, np.nan)
    degenerate = np.nanstd(sd, axis=-1) <= EPS
    out[n - 1:] = np.where((cnt >= max(2, n // 2)) & np.isfinite(last) & ~degenerate,
                           (le - 1) / np.maximum(cnt - 1, 1) - 0.5, np.nan)
    return out


def ts_corr(A, B, n):
    n = int(n); dA = pd.DataFrame(A); dB = pd.DataFrame(B)
    r = dA.rolling(n, min_periods=max(3, n // 2), center=False)
    ma, mb = r.mean(), dB.rolling(n, min_periods=max(3, n // 2), center=False).mean()
    cov = (dA * dB).rolling(n, min_periods=max(3, n // 2), center=False).mean() - ma * mb
    sa = dA.rolling(n, min_periods=max(3, n // 2), center=False).std()
    sb = dB.rolling(n, min_periods=max(3, n // 2), center=False).std()
    out = cov / (sa * sb)
    out = out.where((sa > EPS) & (sb > EPS))          # degenerate window -> NaN (iv)
    return out.to_numpy()


def decay_linear(A, n):
    """linearly-weighted trailing mean (newest weighted most). Vectorized; NaN-aware (excluded, not
    0-filled — num/den both over finite cells). center=False by construction."""
    n = int(n); T, N = A.shape; out = np.full((T, N), np.nan)
    if T < n:
        return out
    w = np.arange(1, n + 1, dtype=float)
    win = sliding_window_view(A, n, axis=0); finite = np.isfinite(win)
    num = (np.where(finite, win, 0.0) * w).sum(-1); den = (finite * w).sum(-1)
    cnt = finite.sum(-1)
    out[n - 1:] = np.where((den > 1e-12) & (cnt >= max(2, n // 2)), num / den, np.nan)
    return out


def _shift(A, n):
    out = np.full_like(A, np.nan); n = int(n)
    if n < A.shape[0]:
        out[n:] = A[:-n]
    return out


def _xsec(A, fn):
    out = np.full_like(A, np.nan)
    for t in range(A.shape[0]):
        v = np.isfinite(A[t])
        if v.sum() >= 3:
            out[t, v] = fn(A[t, v])
    return out


def xsec_rank(A):    return _xsec(A, lambda x: pd.Series(x).rank(pct=True).to_numpy() - 0.5)
def xsec_z(A):       return _xsec(A, lambda x: (x - x.mean()) / x.std() if x.std() > EPS else np.full_like(x, np.nan))
def xsec_demean(A):  return _xsec(A, lambda x: x - x.mean())


def _div(a, b):      return np.where(np.abs(b) > EPS, a / np.where(np.abs(b) > EPS, b, np.nan), np.nan)
def _log1p(x):       return np.sign(x) * np.log1p(np.abs(x))
def _power(x, p):    return np.sign(x) * np.power(np.abs(x), float(p))
def _where(c, a, b): return np.where(np.isfinite(c) & (c > 0), a, b)
def _clip(x, lo, hi): return np.clip(x, float(lo), float(hi))


# ---- operator registry: name -> (fn, arity, kind, cost). kind decides type rules. ----------------
TEMPORAL, XSEC, POINT, COND = "temporal", "xsec", "pointwise", "conditional"
OPS = {
    # temporal (require DENSE series operand(s); a scalar-int window is fine) — cost 1-3
    "ts_delta": (ts_delta, 2, TEMPORAL, 1), "ts_mean": (ts_mean, 2, TEMPORAL, 1),
    "ts_std": (ts_std, 2, TEMPORAL, 1), "ts_zscore": (ts_zscore, 2, TEMPORAL, 2),
    "ema": (ema, 2, TEMPORAL, 1), "ts_rank": (ts_rank, 2, TEMPORAL, 2),
    "ts_corr": (ts_corr, 3, TEMPORAL, 3), "ts_min": (ts_min, 2, TEMPORAL, 1),
    "ts_max": (ts_max, 2, TEMPORAL, 1), "decay_linear": (decay_linear, 2, TEMPORAL, 1),
    # cross-sectional (any series) — cost 1
    "xsec_rank": (xsec_rank, 1, XSEC, 1), "xsec_z": (xsec_z, 1, XSEC, 1),
    "xsec_demean": (xsec_demean, 1, XSEC, 1),
    # pointwise (any) — cost 1
    "add": (np.add, 2, POINT, 1), "sub": (np.subtract, 2, POINT, 1), "mul": (np.multiply, 2, POINT, 1),
    "div": (_div, 2, POINT, 1), "neg": (np.negative, 1, POINT, 1), "abs": (np.abs, 1, POINT, 1),
    "sign": (np.sign, 1, POINT, 1), "log1p_safe": (_log1p, 1, POINT, 1), "power": (_power, 2, POINT, 1),
    # conditional (any) — cost 1-2
    "where": (_where, 3, COND, 2), "gt": (np.greater, 2, COND, 1), "lt": (np.less, 2, COND, 1),
    "clip": (_clip, 3, COND, 1),
}
# operator args that are SCALAR ints/floats (windows / powers / bounds), not series
SCALAR_ARGS = {"ts_delta": [1], "ts_mean": [1], "ts_std": [1], "ts_zscore": [1], "ema": [1],
               "ts_rank": [1], "ts_corr": [2], "ts_min": [1], "ts_max": [1], "decay_linear": [1],
               "power": [1], "clip": [1, 2]}


# ---- parse + type-check --------------------------------------------------------------------------
class Node:
    __slots__ = ("op", "args", "type", "is_scalar", "value")

    def __init__(self, op=None, args=None, type=None, is_scalar=False, value=None):
        self.op = op; self.args = args or []; self.type = type; self.is_scalar = is_scalar; self.value = value


def parse(formula: str) -> Node:
    """Parse a formula string (Python-call syntax) into a typed tree, enforcing the operand whitelist,
    the leg-column temporal ban (type system), depth<=6, and ops<=12. Raises DSLError on any violation."""
    try:
        tree = ast.parse(formula.strip(), mode="eval").body
    except SyntaxError as e:
        raise DSLError(f"syntax error: {e}")
    n_ops = [0]

    def build(node) -> Node:
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name) or node.func.id not in OPS:
                raise DSLError(f"unknown operator: {ast.dump(node.func)}")
            name = node.func.id
            fn, arity, kind, cost = OPS[name]
            if len(node.args) != arity:
                raise DSLError(f"{name} expects {arity} args, got {len(node.args)}")
            n_ops[0] += 1
            scalar_pos = SCALAR_ARGS.get(name, [])
            children = []
            for i, a in enumerate(node.args):
                ch = build(a)
                if i in scalar_pos and not ch.is_scalar:
                    raise DSLError(f"{name} arg {i} must be a numeric constant (window/power/bound)")
                # a bare constant is allowed as a broadcast threshold ONLY in pointwise/conditional ops;
                # temporal/xsec series operands must be series.
                if ch.is_scalar and i not in scalar_pos and kind in (TEMPORAL, XSEC):
                    raise DSLError(f"{name} arg {i} must be a series, not a constant")
                children.append(ch)
            series_children = [c for c in children if not c.is_scalar]
            if not series_children:
                raise DSLError(f"{name}: needs at least one series operand (not all constants)")
            # ---- type rule (iii): temporal operators require DENSE series operands ----
            if kind == TEMPORAL:
                for c in series_children:
                    if c.type == SPARSE:
                        raise DSLError(f"temporal operator '{name}' cannot take a SPARSE leg column "
                                       f"(leg scores exist only at anchors); legs are pointwise/xsec/conditional only")
                out_type = DENSE
            elif kind == XSEC:
                out_type = series_children[0].type
            else:  # POINT / COND: SPARSE if any series operand is SPARSE, else DENSE
                out_type = SPARSE if any(c.type == SPARSE for c in series_children) else DENSE
            return Node(op=name, args=children, type=out_type)
        if isinstance(node, ast.Name):
            if node.id in DENSE_CHANNELS:
                return Node(op=node.id, type=DENSE)
            if node.id in LEG_COLUMNS:
                return Node(op=node.id, type=SPARSE)
            raise DSLError(f"unknown operand: {node.id} (not a whitelisted channel or leg)")
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return Node(is_scalar=True, value=float(node.value))
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub) and isinstance(node.operand, ast.Constant):
            return Node(is_scalar=True, value=-float(node.operand.value))
        raise DSLError(f"illegal node: {ast.dump(node)}")

    root = build(tree)
    d = _depth(root)
    if d > MAX_DEPTH:
        raise DSLError(f"depth {d} > MAX_DEPTH {MAX_DEPTH}")
    if n_ops[0] > MAX_OPS:
        raise DSLError(f"operator count {n_ops[0]} > MAX_OPS {MAX_OPS}")
    root.value = dict(depth=d, n_ops=n_ops[0], md5=hashlib.md5(formula.strip().encode()).hexdigest()[:12])
    return root


def _depth(node) -> int:
    if node.is_scalar or not node.args:
        return 0
    return 1 + max(_depth(a) for a in node.args)


# ---- evaluate ------------------------------------------------------------------------------------
def evaluate(node: Node, ctx: dict) -> np.ndarray:
    """ctx: {channel_or_leg_name -> (T,N) float array}. Returns the factor (T,N), causal <=t.

    If ctx carries '__universe__' (T,N bool = the scoring universe member&CL), every XSEC operator
    normalizes ONLY over that universe. Fix (0C, 2026-07-20): xsec_z/xsec_rank/xsec_demean previously
    normalized over all-finite coins (=140, incl. non-member/non-CL). Monotone formulas are unaffected
    (per-anchor ranks over member&CL are invariant to the normalization universe), but a NON-monotone
    composition (e.g. mul of two xsec_z) inherits the wrong relative scale from the off-universe coins,
    producing a scored-rank artifact. Masking the XSEC input to member&CL removes it. Temporal operators
    are deliberately NOT masked — they need full per-coin history; only the cross-sectional reduction is
    restricted to the tradable universe."""
    if node.is_scalar:
        return node.value
    if not node.args:                                 # leaf operand
        return ctx[node.op]
    fn, arity, kind, cost = OPS[node.op]
    vals = [evaluate(a, ctx) for a in node.args]
    if kind == XSEC:
        uni = ctx.get("__universe__")
        if uni is not None:                           # cross-sectional normalization over member&CL only
            vals[0] = np.where(uni, vals[0], np.nan)
    return fn(*vals)


def validate(formula: str) -> dict:
    """Parse-only check; returns {ok, depth, n_ops, out_type, md5} or {ok:False, error}."""
    try:
        root = parse(formula)
        return dict(ok=True, out_type=root.type, **root.value)
    except DSLError as e:
        return dict(ok=False, error=str(e))
