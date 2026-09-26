"""alloc_rules.py — combination-layer arms for docs/DESIGN_combination_layer_2026-09-26.md. Library; no side effects on import.

An ARM = (seat rule, mix). Every arm goes through the SAME code path (alloc_combo.alloc_evolve -> alloc_step); the in-service arm is
not a shortcut that passes legs.npz WL through -- it RECOMPUTES the seat from legs.npz LR and must land on WL bit for bit (G1), so the
identity control certifies the path every candidate uses.

Seat rules return an (n, 3) float64 array [king, rev24, fund] that alloc_step masks exactly like combo_target.step L30
(w = [s0, 0, s2] / sum). Every rule is CAUSAL by construction: the seat at anchor i reads only LR rows < i (the history convention of
nc_legs.py L42-L59: LR[i-1] is appended at step i BEFORE the seat is computed). `causality_probe` re-checks that claim by poisoning
every LR row >= i and requiring the seat at i to be unchanged.

Mixes (how the two books are built from the masked seat w = [w0, 0, w2]):
  shared      in service:  King book = chain(w0*king + w2*fund), F10 book = chain(w0*zf10 + w2*fund), raw = 0.55*K + 0.45*F
  orth        (c):         King book = chain((0.55*w0*king + w2*fund)/(1-0.45*w0)), F10 book = chain(zf10), raw = (1-0.45*w0)*K + 0.45*w0*F
              -> the SAME pre-chain linear combination 0.55*w0*king + 0.45*w0*zf10 + w2*fund as `shared`, with the fund term held once
  fundflip    RED CONTROL: `shared` with fund -> -fund in both books (trades against the funding signal the book is built on)
"""
import numpy as np

LEGS3 = ("king", "rev24", "fund")
INSERVICE_LOOK = 900


def _history(LR):
    """yield (i, list-of-finite-LR-rows-before-i) with the nc_legs.py convention, as three python lists (same float objects)."""
    hist = ([], [], [])
    for i in range(LR.shape[0]):
        if i >= 1 and np.isfinite(LR[i - 1]).all():
            for j in range(3): hist[j].append(float(LR[i - 1, j]))
        yield i, hist


def msharpe(LR, look):
    """production msharpe (shadow_loop_v3.py L784-790 == nc_legs.py L54-59), any look."""
    W = np.full((LR.shape[0], 3), np.nan)
    for i, h in _history(LR):
        if len(h[0]) >= look:
            r = np.stack([np.array(h[j][-look:]) for j in range(3)])
            shp = r.mean(1) / (r.std(1) + 1e-9); shp = np.maximum(shp, 0.0)
            W[i] = shp / shp.sum() if shp.sum() > 0 else np.array([1 / 3] * 3)
        else:
            W[i] = np.array([1 / 3] * 3)
    return W


def masked_fund(W):
    """w2m = W2/(W0+W2), with combo_target.step's degenerate fallback [.5, 0, .5]."""
    den = W[:, 0] + W[:, 2]; ok = den > 1e-12
    return np.where(ok, W[:, 2] / np.where(ok, den, 1.0), 0.5)


def from_masked(w2m):
    """a masked seat [1-w2m, 0, w2m]; alloc_step's mask+renormalise leaves it unchanged."""
    return np.stack([1.0 - w2m, np.zeros_like(w2m), w2m], 1)


def cap_fund(W, c):
    """(a) the masked fund seat capped at c; the excess goes to the model side (king/F10 through w0)."""
    return from_masked(np.minimum(masked_fund(W), c))


def inverse_vol(LR, look=INSERVICE_LOOK):
    """(d) risk-based, no mean: masked seat proportional to 1/sigma over the same trailing window (king and fund only)."""
    W = np.full((LR.shape[0], 3), np.nan)
    for i, h in _history(LR):
        if len(h[0]) >= look:
            sk = np.array(h[0][-look:]).std(); sf = np.array(h[2][-look:]).std()
            W[i] = [1.0 / sk, 0.0, 1.0 / sf] if sk > 0 and sf > 0 else [0.5, 0.0, 0.5]
            W[i] = W[i] / W[i].sum()
        else:
            W[i] = np.array([1 / 3] * 3)
    return W


def oracle_future(LR, look=INSERVICE_LOOK):
    """O (ceiling control, NEVER admissible): the in-service estimator on the NEXT `look` finite LR rows, i.e. rows i .. i+look-1 in
    nc_legs order -- the same smoothness as the in-service seat with perfect foresight of the coming ~150 days. Where fewer than `look`
    future rows exist (the axis tail) it uses the rows that exist, down to 1; with none it falls back to [1/3]*3 like production."""
    fin = np.isfinite(LR).all(1); rows = LR[fin]; pos = np.cumsum(fin)          # pos[i] = finite rows at index <= i
    W = np.full((LR.shape[0], 3), np.nan)
    for i in range(LR.shape[0]):
        k0 = int(pos[i - 1]) if i >= 1 else 0                                     # first finite row NOT yet seen at anchor i
        r = rows[k0:k0 + look].T
        if r.shape[1] >= 1:
            shp = r.mean(1) / (r.std(1) + 1e-9); shp = np.maximum(shp, 0.0)
            W[i] = shp / shp.sum() if shp.sum() > 0 else np.array([1 / 3] * 3)
        else:
            W[i] = np.array([1 / 3] * 3)
    return W


def seats_for(rule, LR, WL):
    """-> (seats (n,3) float64, receipt dict). `WL` is legs.npz WL (float32), used ONLY by the in-service identity assertion."""
    if rule == "inservice":
        S = msharpe(LR, INSERVICE_LOOK).astype(np.float32)          # WL is stored float32 (nc_legs.py L37); evolve reads WL.astype(float64)
        fin = np.isfinite(WL).all(1)
        same = np.array_equal(S[fin].view(np.uint32), WL[fin].view(np.uint32))
        assert same, "G1: recomputed in-service seat != legs.npz WL -- the device does not know the in-service operator"
        return WL.astype(np.float64), {"rule": rule, "look": INSERVICE_LOOK, "G1_recompute_bitwise_WL": True, "rows": int(fin.sum()),
                                       "note": "the recomputed seat is asserted bitwise == WL and then WL itself is passed, so the identity arm "
                                               "feeds evolve the identical float64 array production-parity combos were built from"}
    if rule.startswith("cap"):                                       # cap050 = masked fund seat <= 0.50 (no '.' in arm names)
        c = int(rule[3:]) / 100.0; base = msharpe(LR, INSERVICE_LOOK).astype(np.float32).astype(np.float64)
        return cap_fund(base, c), {"rule": rule, "cap": c, "base": "in-service msharpe 900 (float32 as WL)"}
    if rule.startswith("look"):                                      # look1800
        L = int(rule[4:])
        return msharpe(LR, L).astype(np.float32).astype(np.float64), {"rule": rule, "look": L}
    if rule == "oracle":
        return oracle_future(LR).astype(np.float32).astype(np.float64), {"rule": rule, "look": INSERVICE_LOOK, "LOOK_AHEAD": True,
                                                                          "admissible": False, "role": "ceiling control"}
    if rule == "invvol":
        return inverse_vol(LR).astype(np.float32).astype(np.float64), {"rule": rule, "look": INSERVICE_LOOK}
    raise ValueError(f"unknown seat rule {rule!r}")


def causality_probe(rule, LR, WL, idx):
    """poison every LR row >= i (i in idx) and require the rule's seat at i unchanged. Returns {i: bool}."""
    S0, _ = seats_for(rule, LR, WL) if rule != "inservice" else (msharpe(LR, INSERVICE_LOOK), None)
    out = {}
    for i in idx:
        LRp = LR.copy(); LRp[i:] = np.where(np.isfinite(LRp[i:]), LRp[i:] + 1e3, LRp[i:])
        Sp = (seats_for(rule, LRp, WL)[0] if rule != "inservice" else msharpe(LRp, INSERVICE_LOOK))
        out[int(i)] = bool(np.array_equal(S0[i], Sp[i]))
    return out


def mix_weights(mix, w):
    """-> (a_k, b_k, a_f, b_f, m_k, m_f, fund_sign) from the masked seat w = [w0, 0, w2] (already renormalised as step L30 does).
    `shared` must return exactly the scalars combo_target.step uses so the identity is bitwise."""
    if mix == "shared":
        return w[0], w[2], w[0], w[2], .55, .45, 1.0
    if mix == "fundflip":
        return w[0], w[2], w[0], w[2], .55, .45, -1.0
    if mix == "orth":
        d = 1.0 - .45 * w[0]
        return .55 * w[0] / d, w[2] / d, 1.0, 0.0, d, .45 * w[0], 1.0
    raise ValueError(f"unknown mix {mix!r}")
