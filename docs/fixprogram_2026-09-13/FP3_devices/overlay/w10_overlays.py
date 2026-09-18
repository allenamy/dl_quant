#!/usr/bin/env python3
"""FP3-R overlays (PREREG_FP3_R_fast_move_nonresponse_2026-09-18 §2): book-layer rules applied INSIDE the frozen replay engine to the blended book sm
at anchor i, using only information available at that anchor (rows < i of the 4h-ahead return matrix y4, current funding, current members).
R7C-R1 (2026-09-18): make(spec) must be called ONCE PER RUN (arm) — the quantile histories live in the closure; the engine instantiates per run.
The legs' own EMA states are untouched; the overlaid book is what is traded and carried (HB) — a risk layer on top of the strategy.
Spec string: "none" | "r1a:q=0.95,s=0.5" | "r1b:q=0.95,s=0.5" | "r2:c=1.0" | "r3:th=0.20" | "r3f" | "r4:win=360" | "r5:age=30,s=0.5" (exploratory) | "r6:k=1,q=0.95,s=0.5" / "r6l:…" (short-basket rebound, PREREG R6) | "r6c:c=0.975" (control) """
import numpy as np
def _params(spec):
    name, _, ps = spec.partition(":"); d = {}
    for kv in filter(None, ps.split(",")):
        k, v = kv.split("="); d[k] = float(v)
    return name, d
def breadth(y4, i, m, look=6):
    """causal breadth signal: equal-weight mean of the members' 4h returns over the last `look` anchors (rows i-look..i-1), summed"""
    if i < look: return np.nan
    seg = y4[i - look:i][:, m]; seg = np.where(np.isfinite(seg), seg, 0.0); return float(seg.mean(1).sum())
class _Hist:
    def __init__(self): self.B = []                      # breadth history for the causal quantile
def make(spec):
    name, P = _params(spec); H = _Hist()
    if name == "none": return None
    if name in ("r1a", "r1b"):
        q, s = P.get("q", 0.95), P.get("s", 0.5)
        def f(sm, ctx):
            b = breadth(ctx["y4"], ctx["i"], ctx["m"]); H.B.append(b)
            hist = np.array([x for x in H.B[:-1] if np.isfinite(x)])
            if len(hist) < 200 or not np.isfinite(b): return sm                     # no quantile yet: no action
            if b < np.quantile(hist, q): return sm
            if name == "r1a": return sm * s                                           # whole-book de-leverage in a broad rally
            FZ = ctx["FZ"]; sign_ok = np.zeros_like(sm, bool); mm = ctx["m"]; fz = np.nan_to_num(FZ)
            sign_ok[mm] = np.sign(sm[mm]) == np.sign(fz)                              # names whose book side agrees with the fund leg's view
            return np.where(sign_ok, sm * s, sm)
        return f
    if name == "r2":
        c = P.get("c", 1.0)
        def f(sm, ctx):
            i, m, y4, capw = ctx["i"], ctx["m"], ctx["y4"], ctx["capw"]
            if i < 42: return sm
            seg = y4[i - 42:i][:, m]; sig = np.nanstd(np.where(np.isfinite(seg), seg, np.nan), axis=0); med = np.nanmedian(sig)
            if not np.isfinite(med) or med <= 0: return sm
            cap = np.full(sm.shape, capw); cap[m] = np.where(np.isfinite(sig) & (sig > 0), np.minimum(capw, c * med / sig * capw), capw)   # default = the book's own cap (names carried outside the member set keep it); never inf
            mem = np.zeros(sm.shape, bool); mem[m] = True
            # constrained allocation (R7-R1 fix 2026-09-18): clip, then push the clipped excess pro rata into same-side names that still have headroom,
            # never above their own cap; iterate until the excess is absorbed or no headroom is left (then gross drops: capacity shortfall is accepted, not re-breached)
            out = np.clip(sm, -cap, cap)
            for side in (1.0, -1.0):
                tgt = np.abs(sm[np.sign(sm) == side]).sum(); sel_ = np.sign(sm) == side
                for _ in range(50):
                    cur = np.abs(out[sel_]).sum(); exc = tgt - cur
                    if exc <= 1e-12: break
                    head = np.where(sel_ & mem & np.isfinite(out) & (np.abs(out) < cap - 1e-15), cap - np.abs(out), 0.0); H = head.sum()   # excess goes to same-side MEMBERS with headroom only
                    if H <= 1e-15: break
                    add = np.minimum(head, head / H * exc) if H > exc else head            # pro rata to headroom, capped by headroom
                    out = out + side * add
            fin = np.isfinite(out); assert np.all(np.abs(out[fin]) <= cap[fin] + 1e-12), float(np.nanmax(np.abs(out[fin]) - cap[fin]))   # invariant on finite entries (NaN = not in the book)
            assert np.isfinite(out).sum() == np.isfinite(sm).sum(), "allocation introduced NaN"
            return out
        return f
    if name == "r3":
        th = P.get("th", 0.20)
        def f(sm, ctx):
            i, y4 = ctx["i"], ctx["y4"]
            if i < 18: return sm
            seg = y4[i - 18:i]; cum = np.exp(np.nansum(np.log1p(np.where(np.isfinite(seg), seg, 0.0)), axis=0)) - 1.0   # 3-day cumulative return per name
            return np.where((sm > 0) & (cum >= th), 0.0, sm)                          # parabolic-onset exit on the long side
        return f
    if name == "r3f":
        def f(sm, ctx):
            j, FN, IV = ctx["j"], ctx["FN"], ctx["IV"]; fn = np.nan_to_num(FN[j]); iv = np.where(np.isfinite(IV[j]) & (IV[j] > 0), IV[j], 8.0); rn8 = fn * (8.0 / iv)
            return np.where((sm < 0) & (rn8 <= -0.0010), 0.0, sm)                     # FTRIM hard exit at the book level
        return f
    if name == "r4":
        win = int(P.get("win", 360))
        def f(sm, ctx):
            i, m, y4 = ctx["i"], ctx["m"], ctx["y4"]
            if i < win: return sm
            seg = y4[i - win:i]; segm = np.where(np.isfinite(seg), seg, 0.0); mkt = segm[:, m].mean(1); mkt = mkt - mkt.mean(); v = (mkt ** 2).sum()
            if v <= 0: return sm
            beta = ((segm - segm.mean(0)) * mkt[:, None]).sum(0) / v                  # causal 60-day beta of every name to the member equal-weight index
            L = sm > 0; S = sm < 0; bl = float((sm[L] * beta[L]).sum()); bs = float((sm[S] * beta[S]).sum())       # bs is negative for a short leg with positive beta
            if bl + bs == 0 or bl <= 0 or bs >= 0: return sm
            out = sm.copy()
            if bl > -bs: out[L] *= (-bs / bl)                                          # shrink the leg that carries more breadth beta
            else: out[S] *= (bl / -bs)
            return out
        f.neutral = "beta"        # R7C-R2: R4's contract is Σwβ = 0 (notional net allowed); the engine's tail step must NOT re-impose notional neutrality
        return f
    if name == "r5":                                                                   # EXPLORATORY (added 2026-09-18 02:4xZ after the pre-registered grid was read; not gated by PREREG §3)
        age_d, s = P.get("age", 30.0), P.get("s", 0.5); st = {"first": None}
        def f(sm, ctx):
            i, y4 = ctx["i"], ctx["y4"]
            if st["first"] is None:
                fin = np.isfinite(y4); st["first"] = np.where(fin.any(0), fin.argmax(0), 10**9)          # first anchor with a finite 4h return = listing (causal: fixed once observed)
            age = i - st["first"]; young = (age >= 0) & (age < age_d * 6)
            return np.where(young, sm * s, sm)                                                            # scale (or zero) the weight of names younger than age_d days
        return f
    if name in ("r6", "r6l"):                                                          # PREREG_FP3_R6 (2026-09-18): short-basket collective rebound ⇒ cut the FINAL book budget
        k, q, s = int(P.get("k", 1)), P.get("q", 0.95), P.get("s", 0.5); H = _Hist()
        def f(sm, ctx):
            i, y4, HR = ctx["i"], ctx["y4"], ctx["HR"]                                    # HR = the accounted book entering this anchor (previous anchor's final book)
            if i < k or HR is None: return sm
            seg = y4[i - k:i]; cum = np.exp(np.nansum(np.log1p(np.where(np.isfinite(seg), seg, 0.0)), axis=0)) - 1.0   # k-anchor cumulative 4h return per name, rows < i only
            hr = np.nan_to_num(HR); sh = hr < 0; lo = hr > 0
            if sh.sum() < 5 or lo.sum() < 5: b = np.nan
            elif name == "r6": b = float(cum[sh].mean() - cum[lo].mean())                # SB_rel: short basket rebound relative to the long basket
            else: b = float(-(hr[sh] * cum[sh]).sum() / max(np.abs(hr).sum(), 1e-9))     # SB_loss: short-edge loss per unit gross (positive = loss)
            H.B.append(b); hist = np.array([x for x in H.B[:-1] if np.isfinite(x)])
            if len(hist) < 200 or not np.isfinite(b) or b < np.quantile(hist, q): return sm
            return sm * s                                                                # budget cut on the whole final book (neutrality kept; tail step scales down only)
        return f
    if name == "r6c":                                                                  # control arm: UNCONDITIONAL constant budget (same average leverage as the reference r6 arm)
        c = P.get("c", 1.0)
        def f(sm, ctx): return sm * c
        return f
    raise ValueError(spec)
