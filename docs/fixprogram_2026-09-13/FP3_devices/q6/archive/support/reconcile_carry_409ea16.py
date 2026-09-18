"""EXE-04 / Q6 — the JOINT feasible set of per-request cumulative fills, carried ACROSS windows.

*** PURE FUNCTIONS. No venue, no credentials, no I/O. Nothing here is wired into a gate yet. ***

THE DEFECT THIS EXISTS FOR (`docs/PREREG_reconcile_carry_forward_unexplained_2026-09-10.md` §0).
`reconcile.reconcile()` compares window by window: the baseline for window t+1 is the venue's
OBSERVED position at t (`live/reconcile.py`: `n1, q1, _ = prev_rb.get(sym, ...)`,
`expected_qty = q1 + Σ_window`, and `prev_rb = cur` at the foot of the loop). So an unexplained
balance is absorbed into the next window's baseline and reads clean one anchor later: explained 50,
observed 80, residual 30; next anchor no fills and still 80 ⇒ residual 0 and §4-5b/5e both CLEAN.
The reviewer reproduced it on a real top-up (two requests EXPIRED at 25 each, read back 80, next
anchor zero fills, read back 80). THE NEWEST CELL BEING CLEAN IS NOT THE SAME STATEMENT AS THE
QUANTITY IDENTITY BEING CLOSED.

★★★ WHY THE OBJECT IS A JOINT SET AND NOT A PER-REQUEST INTERVAL. Revision 3 WITHDREW interval
propagation as the wrong object — not as an approximation that was too loose, but as a thing that
loses the correlation between requests. Two open BUY1 requests, read 1 then 0: the joint feasible
set at the first anchor is {(1,0), (0,1)}, so each request's MARGINAL lower bound is 0, and
propagating only the marginals admits (0,0) at the second anchor — while no single monotone
trajectory reaches it. The reviewer's grid: 2xBUY1 exact 6 pairs vs propagated 7, 3xBUY1 10 vs 13,
2xBUY2 15 vs 19. `feasible_exact` is therefore the contract and `feasible_marginal_UNSOUND` is kept
BESIDE it, never as a fallback, purely so the tests can assert the two disagree on exactly the
reviewer's named false accepts. A "faster" reimplementation that silently equals the marginal one
is the failure this file is shaped to make visible.

THE CONTRACT (PREREG §1c.1; where §1/§1b conflict, §1c governs). For each symbol, over requests
i with side sigma_i in {+1,-1}, capacity Q_i, birth anchor b_i and terminal anchor d_i (or None),
the joint feasible set F(t) is the set of vectors x(t) = (x_i(t)) of cumulative filled quantity
satisfying, for every anchor t_k <= t:
    (a) birth        t_k <  b_i          =>  x_i(t_k) = 0
    (b) monotone     t_1 <= t_2          =>  x_i(t_1) <= x_i(t_2)
    (c) post-terminal t_k >= d_i         =>  x_i(t_k) = x_i(d_i)   (an unknown PAST does not mean
                                             remaining FUTURE capacity)
    (d) evidence     x_i(t_k) >= C_i(t_k), and x_i = C_i exactly when terminal with a credible C
    (e) observation  sum_i sigma_i [x_i(t_k) - x_i(t_0)] = Q_s(t_k) - Q_s(t_0) - F_s(t_k)
(a)-(d) are HARD and never degrade. (e) is the only degradable constraint.

RECOVERY POLICY (PREREG §1d.2, registered, NOT an implementation detail). Observation equations are
admitted in ANCHOR-TIME ORDER; the first one whose admission empties F is downgraded to an EXCLUDED
OBSERVATION (recorded, never deleted) and admission continues. This is deliberately NOT the maximum
cardinality satisfiable subset: BUY2 read 2 -> 0 -> 1 keeps anchor 1 and excludes anchors 2 and 3,
where maximum cardinality would keep 2 and 3. Chronological admission is chosen because it is
deterministic (no ties), because a reading has already been consumed by risk by the time the next
one arrives, and because it matches "one judgement per anchor".

TWO NUMBERS, REPORTED SEPARATELY (PREREG §1b D1, §1d.6), because they answer different questions:
  `distance`            how far the CURRENT observation is from what the admitted history predicts;
                        may legitimately be 0 while history is unresolved.
  `history_unresolved`  whether any observation had to be excluded, and which.
Which of them trips which gate is NOT decided here (PREREG §1b: "本文不擅定停机政策").

HARD CONTRADICTION => UNMEASURABLE (PREREG §1d.4). If (a)-(d) alone are unsatisfiable — two
different credible terminal totals for one request, say — the symbol is NOT given a finite distance
and no fact is dropped to make it computable. `status = "unmeasurable"`.

NOT DONE HERE, and named so nobody reads this file as the whole fix: the wiring
(`carry_by_symbol` / `pending_requests` out of `reconcile()`, §4-5b/5e reading |E_s| instead of
|e_t|, the `reconstructed` supersedes rows, the next-anchor terminal lookup) and the 41-day ledger
replay. PREREG §2 and §3.5-3.6.
"""
from typing import Any, Dict, List, Optional, Sequence, Tuple

__all__ = ["Request", "feasible_exact", "feasible_marginal_UNSOUND", "carry_state"]


class Request:
    """One order request of one symbol, as the reconciler knows it.

    `cap` is capacity in the SAME unit the observations are expressed in (contracts). `lower` is
    the credible evidence lower bound C on cumulative filled quantity — sub-fill union, or a
    trusted executedQty snapshot, which per PREREG §1c.5 is a CUMULATIVE constraint and not that
    instant's increment. `exact` is set only when the request is terminal AND its total is
    credible; it is a different statement from `lower` and is kept apart on purpose (§1c.2:
    evidence lower bounds enter K, feasibility-derived bounds never do).
    """

    def __init__(self, rid: str, side: int, cap: float, birth: float,
                 terminal: Optional[float] = None, lower: float = 0.0,
                 exact: Optional[float] = None):
        if side not in (1, -1):
            raise ValueError(f"side must be +1 or -1, got {side!r}")
        if not (cap >= 0):
            raise ValueError(f"cap must be a non-negative number, got {cap!r}")
        self.rid, self.side, self.cap = rid, int(side), float(cap)
        self.birth, self.terminal = float(birth), (None if terminal is None else float(terminal))
        self.lower, self.exact = float(lower), (None if exact is None else float(exact))

    def __repr__(self):                                       # pragma: no cover — diagnostics only
        return (f"Request({self.rid!r}, side={self.side:+d}, cap={self.cap}, birth={self.birth}, "
                f"terminal={self.terminal}, lower={self.lower}, exact={self.exact})")

    def contradiction(self) -> Optional[str]:
        """A HARD contradiction in this request alone, or None. (PREREG §1d.4: such a name is
        UNMEASURABLE — we do not drop a fact to make it computable.)"""
        if self.exact is None:
            return None if self.lower <= self.cap + 1e-12 else (
                f"evidence floor {self.lower} exceeds capacity {self.cap}")
        if self.exact + 1e-12 < self.lower:
            return f"credible total {self.exact} is below the evidence floor {self.lower}"
        if self.exact > self.cap + 1e-12:
            return f"credible total {self.exact} exceeds capacity {self.cap}"
        return None

    def domain(self, t: float, step: float) -> List[float]:
        """The values x_i(t) may take under the HARD constraints alone, on the lattice.

        ★ `exact` IS A STATEMENT ABOUT THE TERMINAL TOTAL, SO IT BINDS ONLY FROM d_i ONWARD.
        Applying it at every anchor would assert that the request was filled to its final total
        from birth — over-constraining the past, and in the Q6 fixture it makes the 80 read at the
        FIRST anchor look impossible for the wrong reason. Before d_i the cumulative fill is only
        bounded by the evidence floor and the capacity.
        """
        if t < self.birth:
            return [0.0]
        if self.contradiction():
            return []
        lo, hi = self.lower, self.cap
        if self.exact is not None and self.terminal is not None and t >= self.terminal:
            lo = hi = self.exact
        if lo > hi + 1e-12:
            return []
        n = int(round((hi - lo) / step)) if step > 0 else 0
        return [lo + k * step for k in range(max(n, 0) + 1)]


def _trajectories(reqs: Sequence[Request], times: Sequence[float], step: float):
    """Every HARD-feasible joint trajectory, as a tuple of per-anchor vectors.

    Enumeration, not a solver: the reviewer's acceptance is a SOLUTION SET and contract quantities
    live on the lot-size lattice, so the honest object is the set itself. `feasible_exact` bounds
    the size before calling this and refuses rather than truncating.
    """
    def per_request(i: int):
        r = reqs[i]
        out: List[Tuple[float, ...]] = []

        def walk(k: int, sofar: Tuple[float, ...], pinned: bool):
            if k == len(times):
                out.append(sofar)
                return
            t = times[k]
            prev = sofar[-1] if sofar else 0.0
            if pinned:
                # (c) post-terminal constant
                walk(k + 1, sofar + (prev,), True)
                return
            # ★ THE FIRST ANCHOR AT OR AFTER d_i IS STILL FREE. x_i(d_i) is whatever the request
            #   reached by the moment it went terminal, and fills between the previous anchor and
            #   d_i are part of that. Only from the NEXT anchor on is the value constant. Pinning
            #   at the first post-terminal anchor would forbid the very fills that closed it.
            is_post = r.terminal is not None and t >= r.terminal
            for v in r.domain(t, step):
                if v + 1e-12 < prev:                          # (b) monotone
                    continue
                walk(k + 1, sofar + (v,), is_post)
        walk(0, (), False)
        return out

    per = [per_request(i) for i in range(len(reqs))]
    if any(not p for p in per):
        return []

    combos: List[Tuple[Tuple[float, ...], ...]] = [()]
    for p in per:
        combos = [c + (one,) for c in combos for one in p]
    return combos


def _sum_at(reqs: Sequence[Request], traj, k: int) -> float:
    """sum_i sigma_i [x_i(t_k) - x_i(t_0)] — the quantity observation equation (e) constrains."""
    return sum(r.side * (traj[i][k] - traj[i][0]) for i, r in enumerate(reqs))


def feasible_exact(reqs: Sequence[Request], times: Sequence[float],
                   observations: Sequence[Optional[float]], step: float = 1.0,
                   max_trajectories: int = 2_000_000) -> Dict[str, Any]:
    """Admit observation equations in anchor order; return what survived and how far we are.

    `observations[k]` is the RIGHT-HAND SIDE of (e) at `times[k]` — already net of non-trading flow
    and of the baseline Q_s(t_0) — or None where no readback exists for that anchor.

    Returns {status, admitted, excluded, distance, predicted, history_unresolved, n_trajectories}.
    `status` is "ok" or "unmeasurable"; a distance is never invented for the latter.
    """
    times = list(times)
    if len(observations) != len(times):
        raise ValueError(f"{len(observations)} observations for {len(times)} anchors")

    est = 1
    for r in reqs:
        est *= max(len(r.domain(times[-1], step)), 1) ** len(times)
        if est > max_trajectories:
            # ★ refuse rather than fall back to the marginal method. A silent downgrade to the
            #   UNSOUND object is precisely the failure revision 3 withdrew, and it would be
            #   invisible: the caller would still get a number.
            return {"status": "unmeasurable", "why": "too many joint trajectories to enumerate "
                                                     f"exactly (> {max_trajectories}); refusing "
                                                     "to fall back to the marginal method",
                    "admitted": [], "excluded": [], "distance": None, "predicted": None,
                    "history_unresolved": True, "n_trajectories": None}

    pool = _trajectories(reqs, times, step)
    if not pool:
        return {"status": "unmeasurable",
                "why": "the HARD constraints (birth / monotone / post-terminal / evidence) are "
                       "themselves unsatisfiable — no trajectory exists before any observation is "
                       "considered",
                "admitted": [], "excluded": [], "distance": None, "predicted": None,
                "history_unresolved": True, "n_trajectories": 0}

    admitted: List[int] = []
    excluded: List[Dict[str, Any]] = []
    live = pool
    # ★★ THE PREDICTION SET IS FORMED BEFORE THE CURRENT ANCHOR'S OWN EQUATION IS CONSIDERED
    # (PREREG §1c.3: "P(tₙ) = 满足 (a)–(d) 与 k < n 的所有和约束(不含当前锚的和约束)"). Folding the
    # current reading in first and THEN measuring the distance to it makes the distance 0 whenever
    # the reading is admissible at all — a number that can only ever report what it was just told.
    _idx = [k for k, o in enumerate(observations) if o is not None]
    _n = _idx[-1] if _idx else None
    predicted: List[float] = []
    distance: Optional[float] = None

    def _admit(k: int, obs: float):
        nonlocal live
        kept = [tr for tr in live if abs(_sum_at(reqs, tr, k) - obs) <= 1e-9]
        if kept:
            live = kept
            admitted.append(k)
        else:
            # ★ PREREG §1d.2: downgrade THIS equation, never revisit the ones already admitted.
            #   Deterministic, and it matches how the reading was actually consumed at the time.
            excluded.append({"index": k, "anchor_ts": times[k], "observation": obs,
                             "why": "admitting this reading emptied the joint feasible set; it is "
                                    "an EXCLUDED OBSERVATION (kept in the audit, never deleted) "
                                    "and the admitted history stands"})

    for k, obs in enumerate(observations):
        if obs is None or k == _n:
            continue
        _admit(k, obs)
    if _n is not None:
        predicted = sorted({round(_sum_at(reqs, tr, _n), 12) for tr in live})
        _last = observations[_n]
        distance = (None if not predicted else min(abs(_last - p) for p in predicted))
        _admit(_n, _last)
    return {"status": "ok", "admitted": admitted, "excluded": excluded,
            "distance": distance, "predicted": predicted,
            "history_unresolved": bool(excluded), "n_trajectories": len(live)}


def feasible_marginal_UNSOUND(reqs: Sequence[Request], times: Sequence[float],
                              observations: Sequence[Optional[float]],
                              step: float = 1.0) -> bool:
    """The WITHDRAWN method (PREREG §1b "判定", withdrawn by §1c), kept ONLY as a contrast.

    ★★★ DO NOT CALL THIS FROM ANYTHING THAT DECIDES. It propagates each request's MARGINAL
    interval and therefore loses the correlation between requests, admitting readback paths for
    which no single joint monotone trajectory exists. It is here so the tests can assert that
    `feasible_exact` is NOT this — on the reviewer's own grid it over-admits exactly 1 pair at
    2xBUY1, 3 at 3xBUY1 and 4 at 2xBUY2. Without it in the tree, "the exact solver agrees with the
    solution set" is checkable but "the exact solver is not secretly the loose one" is not.
    """
    los = [0.0] * len(reqs)
    his = [r.cap for r in reqs]
    for k, obs in enumerate(observations):
        if obs is None:
            continue
        t = times[k]
        for i, r in enumerate(reqs):
            if t < r.birth:
                los[i] = his[i] = 0.0
            else:
                his[i] = min(his[i], r.cap)
                los[i] = max(los[i], r.lower)
                if r.exact is not None:
                    los[i] = his[i] = r.exact
        lo = sum(r.side * (los[i] if r.side > 0 else his[i]) for i, r in enumerate(reqs))
        hi = sum(r.side * (his[i] if r.side > 0 else los[i]) for i, r in enumerate(reqs))
        if not (min(lo, hi) - 1e-9 <= obs <= max(lo, hi) + 1e-9):
            return False
        # propagate only the MARGINAL lower bounds forward — the step that loses the correlation
        for i, r in enumerate(reqs):
            if r.side > 0:
                los[i] = max(los[i], min(his[i], obs - sum(
                    r2.side * his[j] for j, r2 in enumerate(reqs) if j != i)))
    return True


def carry_state(reqs: Sequence[Request], times: Sequence[float],
                observations: Sequence[Optional[float]], step: float = 1.0) -> Dict[str, Any]:
    """The reportable pair: the current distance, and whether history is unresolved.

    PREREG §1d.5 — a checkpoint must carry the HARD constraint set, the admitted equations, the
    excluded ones WITH their reason, and the policy identity, and replaying it under the same
    policy must be bit-identical. That is what this returns; `policy` is part of the value so a
    checkpoint can never be replayed under a different rule without the difference being visible.
    """
    out = feasible_exact(reqs, times, observations, step=step)
    out["policy"] = "chronological_admission/PREREG_reconcile_carry_forward_unexplained_2026-09-10#rev4"
    out["requests"] = [{"rid": r.rid, "side": r.side, "cap": r.cap, "birth": r.birth,
                        "terminal": r.terminal, "lower": r.lower, "exact": r.exact} for r in reqs]
    out["times"] = list(times)
    out["observations"] = list(observations)
    return out
