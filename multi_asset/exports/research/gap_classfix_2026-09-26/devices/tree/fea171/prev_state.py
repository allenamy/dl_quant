"""Previous-anchor state lookup that survives producer gaps (gap class fix 2026-09-26, ACCEPTANCE_gap_classfix_2026-09-26.md §1).

combo_stage keyed every previous state on EXACTLY A-14400; after any gap the fallback was a zero vector (gross ~0.07, preflight
abort, ~5 poisoned anchors, then a cold start the executor re-scales to full leverage). This module returns the MOST RECENT VALID
state with anchor < A, however far back, and names where it came from:
  own                       the A-4h state, valid (byte-identical behaviour to the old predicate)
  own_gap<m>                m anchors between the state used and A have no state (m = distance - 1)
  ..._rejected<n>           n newer files existed but were invalid (reason per file in `rejected`)
  ..._beyond_bound          m > MAX_GAP_ANCHORS: still carried (the executor HOLDs the old book while no target is published, so the
                            old state is what it holds; a cold start is never better), but the caller pages HIGH
A state with no valid predecessor at all returns vec None; the caller keeps its existing named fallback — unless that fallback is itself
below MIN_STATE_GROSS: that is a COLD START, and a cold-started book is never published and never written as state (combo_stage)."""
import glob, io, os, re
import numpy as np

ANCHOR_S = 14400
MAX_GAP_ANCHORS = 6          # 24 h. Declared bound: within it a gap is handled and recorded; beyond it the same carry pages HIGH.
MIN_STATE_GROSS = 0.4        # a state whose gross is below this is DEGENERATE (a zero-started ramp: alpha 0.1 reaches 0.4 after ~5 anchors),
                             # never a predecessor. Every retained kc/f10 state outside the 08-30 ramp is >= 0.78; the preflight floor is 0.4.


def load_state_vec(path, NW, expect_anchor, anchor_key=True, min_gross=MIN_STATE_GROSS):
    """(vec, None) for a valid state file, else (None, reason). vec is float64 of length NW."""
    try:
        with open(path, "rb") as f:
            raw = f.read()
        z = np.load(io.BytesIO(raw), allow_pickle=False)
        keys = set(z.files)
    except Exception as e:                                    # noqa: BLE001 — any unreadable file is a named rejection
        return None, f"unreadable: {type(e).__name__}: {str(e)[:80]}"
    need = {"idx", "val"} | ({"anchor"} if anchor_key else set())
    if not need <= keys:
        return None, f"keys {sorted(keys)} lack {sorted(need - keys)}"
    try:
        if anchor_key and int(z["anchor"]) != expect_anchor:
            return None, f"anchor key {int(z['anchor'])} != file anchor {expect_anchor}"
        idx, val = z["idx"], z["val"]
    except Exception as e:                                    # noqa: BLE001
        return None, f"unreadable array: {type(e).__name__}: {str(e)[:80]}"
    if idx.ndim != 1 or val.ndim != 1 or len(idx) != len(val):
        return None, f"shape idx {idx.shape} val {val.shape}"
    if not np.issubdtype(idx.dtype, np.integer):
        return None, f"idx dtype {idx.dtype}"
    idx = idx.astype(np.int64)
    if len(idx) and (idx.min() < 0 or idx.max() >= NW):
        return None, f"idx outside [0,{NW}): min {int(idx.min())} max {int(idx.max())}"
    if len(np.unique(idx)) != len(idx):
        return None, "duplicate idx"
    if not np.issubdtype(val.dtype, np.floating) or not np.all(np.isfinite(val)):
        return None, f"val dtype {val.dtype} or non-finite"
    v = np.zeros(NW)
    v[idx] = val.astype(np.float64)
    g = float(np.abs(v).sum())
    if g < min_gross:
        return None, f"degenerate: gross {g:.4f} < {min_gross}"
    return v, None


def candidates(pattern, A):
    """{anchor: path} for files matching pattern (one '{a}' placeholder) with anchor < A on the 4 h grid below A."""
    head, tail = pattern.split("{a}")
    rx = re.compile(re.escape(os.path.basename(head)) + r"(\d+)" + re.escape(tail) + r"$")
    out = {}
    for p in glob.glob(head + "*" + tail):
        m = rx.match(os.path.basename(p))
        if m and os.path.dirname(p) == os.path.dirname(head):
            a = int(m.group(1))
            if a < A and (A - a) % ANCHOR_S == 0:
                out[a] = p
    return out


def latest_state(pattern, A, NW, anchor_key=True, max_gap=MAX_GAP_ANCHORS, min_gross=MIN_STATE_GROSS):
    """Most recent valid state before A. Returns dict(vec, source, anchor, gap, rejected, beyond_bound, path)."""
    rejected = []
    for a in sorted(candidates(pattern, A), reverse=True):
        p = pattern.format(a=a)
        v, why = load_state_vec(p, NW, a, anchor_key, min_gross)
        if v is None:
            rejected.append({"path": p, "anchor": a, "reason": why})
            continue
        gap = (A - a) // ANCHOR_S - 1
        src = "own" if gap == 0 else f"own_gap{gap}"
        if rejected:
            src += f"_rejected{len(rejected)}"
        beyond = gap > max_gap
        if beyond:
            src += "_beyond_bound"
        return {"vec": v, "source": src, "anchor": a, "gap": gap, "rejected": rejected, "beyond_bound": beyond, "path": p}
    return {"vec": None, "source": None, "anchor": None, "gap": None, "rejected": rejected, "beyond_bound": False, "path": None}


def needs_page(lk):
    """A lookup a human must hear about: a rejected file, a gap beyond the bound, or no valid state at all."""
    return lk["vec"] is None or bool(lk["rejected"]) or lk["beyond_bound"]


def record(lk):
    """JSON-safe summary (no vector)."""
    return {k: lk[k] for k in ("source", "anchor", "gap", "beyond_bound", "rejected")}
