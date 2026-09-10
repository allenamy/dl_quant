"""Pure helpers for the G1 king-clock parity gate (PREREG_king_clock_E §3, AMENDMENT 4 — round 3 after review 31fa3e4e §6).

★ THE AXIS CLAUSE (c), made explicit and boolean. The E-version builder changed TWO things at once: the feature clock (window ends at E)
  and the members' left-bound clamp (LO7 = max(HI-2016, 0)). The clamp lets the first two anchors of 2022 (2022-01-07 16Z and 20Z) pass
  the member volatility gate that the unclamped wrap-around read made impossible (v7 clipped to 0), so the new axis has those two anchors
  and the old one does not. The pre-registered rule "tail difference <= 1" did not foresee this. Round 3 states the rule instead of
  leaving the difference in a report field:
    new_not_in_old  ⊆ ALLOWED_NEW  ∪  {last anchor of the new axis}        (at most ONE unexplained anchor, and only at the tail)
    old_not_in_new  ⊆ {last anchor of the old axis}                        (at most one, only at the tail)
  ALLOWED_NEW defaults to the two clamp-produced anchors and is overridable via G1_ALLOWED_NEW_ANCHORS (comma-separated epoch seconds);
  every allowed anchor that is actually used is listed in the receipt (`allowed_hits`) so the exception is visible, not silent.
"""
import numpy as np

# 2022-01-07 16:00Z and 20:00Z — produced by the member-window left-bound clamp, not by the clock shift (review 31fa3e4e §2 of features/REVIEW.md:
# fixed old clock × old label with only the member clamp gives the same 136 names at both anchors)
DEFAULT_ALLOWED_NEW = (1641571200, 1641585600)


def parse_allowed(env_value, default=DEFAULT_ALLOWED_NEW):
    """G1_ALLOWED_NEW_ANCHORS env: comma-separated epoch seconds; empty string ⇒ no exception allowed; None ⇒ default."""
    if env_value is None:
        return tuple(int(x) for x in default)
    env_value = env_value.strip()
    if not env_value:
        return tuple()
    return tuple(int(x) for x in env_value.split(",") if x.strip())


def axis_clause(En, Eo, allowed_new=DEFAULT_ALLOWED_NEW):
    """Evaluate clause (c). Returns a dict with `ok` and every set that went into the decision."""
    En = np.asarray(En, dtype=np.int64); Eo = np.asarray(Eo, dtype=np.int64)
    allowed = {int(x) for x in allowed_new}
    new_not_old = [int(t) for t in np.setdiff1d(En, Eo)]
    old_not_new = [int(t) for t in np.setdiff1d(Eo, En)]
    allowed_hits = [t for t in new_not_old if t in allowed]
    unexplained_new = [t for t in new_not_old if t not in allowed]
    tail_new = int(En[-1]) if len(En) else None
    tail_old = int(Eo[-1]) if len(Eo) else None
    ok_new = (not unexplained_new) or (len(unexplained_new) == 1 and unexplained_new[0] == tail_new)
    ok_old = (not old_not_new) or (len(old_not_new) == 1 and old_not_new[0] == tail_old)
    return {"ok": bool(ok_new and ok_old), "n_new": int(len(En)), "n_old": int(len(Eo)),
            "new_not_in_old": new_not_old, "old_not_in_new": old_not_new,
            "allowed_new_anchors": sorted(allowed), "allowed_hits": allowed_hits, "unexplained_new": unexplained_new,
            "tail_new_ok": bool(ok_new), "tail_old_ok": bool(ok_old),
            "rule": "new_not_in_old ⊆ allowed ∪ {tail(new)}; old_not_in_new ⊆ {tail(old)}; at most one tail anchor each side"}


def anchors_present(E_axis, anchors):
    """{anchor: present?} for the pre-declared anchors — a missing anchor is a FAIL of (a)/(b), never a skipped row."""
    E = np.asarray(E_axis, dtype=np.int64)
    return {int(t): bool(np.any(E == int(t))) for t in anchors}
