#!/usr/bin/env python3
"""equivalence_labels.py — shared labels for 'no difference / not material / same' claims (FIXPROGRAM 2026-09-13, item K2).

A confidence interval that contains 0 does not establish that two things are the same, and a point estimate inside a band does not
either. This module issues such a label only when the whole interval lies inside a band that was declared in advance, with its unit,
its economic justification and where it was declared. There is no default band and no point-only entry point.

  equivalence(ci, margin=)                      two one-sided tests (TOST) read off a two-sided interval at level c:
                                                EQUIVALENT     ⇔ −δ < lo  and  hi < +δ   (α = (1 − c)/2 per side; c = 0.95 ⇒ α = 0.025)
                                                NOT EQUIVALENT ⇔ lo ≥ +δ  or   hi ≤ −δ
                                                INCONCLUSIVE   otherwise
  one_sided(ci, margin=, material_side=, center=0)   a one-sided materiality line L = center ± δ:
                                                side 'upper': WITHIN MARGIN ⇔ hi < L;  BEYOND MARGIN ⇔ lo ≥ L;  else INCONCLUSIVE
                                                side 'lower': WITHIN MARGIN ⇔ lo > L;  BEYOND MARGIN ⇔ hi ≤ L;  else INCONCLUSIVE
  aggregate(readings)                           several intervals judged jointly (seeds, cells): a label holds only if every member has it
  direction_v4(cells)                           the frozen judge_v4 direction rule, unchanged: (A) ⇔ every point > 0 and lo > 0;
                                                (B) ⇔ every hi < 0; otherwise (C)
  v4_label(cells, margin=)                      (A) / (B) exactly as above; (C) split into (C) EQUIVALENT / (C) INCONCLUSIVE / (C) NOT EQUIVALENT
  shared_loss_reading(...)                      a LOSS label only for books whose realised mean is < 0; 'same loss' only with an EQUIVALENT difference
  loss_label_admissible(label, means)           guard for labels written elsewhere

Intervals are taken as given (percentile bootstrap, verdict intervals, ...); this module never recomputes them. Boundaries are strict
on the claim side: an endpoint exactly on ±δ is not inside the band.
"""
from dataclasses import dataclass
import math

EQUIVALENT = "EQUIVALENT"
NOT_EQUIVALENT = "NOT EQUIVALENT"
INCONCLUSIVE = "INCONCLUSIVE"
WITHIN_MARGIN = "WITHIN MARGIN"
BEYOND_MARGIN = "BEYOND MARGIN"
MIN_JUSTIFICATION_CHARS = 20


class LabelError(ValueError):
    """an input that must not produce any label"""


def _finite(name, x):
    if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x):
        raise LabelError("%s must be a finite number, got %r" % (name, x))
    return float(x)


def _text(name, s, min_chars=1):
    if not isinstance(s, str) or len(s.strip()) < min_chars:
        raise LabelError("%s must be a non-empty string of at least %d characters, got %r" % (name, min_chars, s))
    return s


@dataclass(frozen=True, kw_only=True)
class Margin:
    """a pre-declared band: half-width delta > 0, its unit, why that size is economically immaterial, and where it was declared"""
    delta: float
    unit: str
    justification: str
    source: str

    def __post_init__(self):
        d = _finite("delta", self.delta)
        if d <= 0: raise LabelError("delta must be > 0, got %r" % self.delta)
        _text("unit", self.unit); _text("justification", self.justification, MIN_JUSTIFICATION_CHARS); _text("source", self.source)


@dataclass(frozen=True, kw_only=True)
class Interval:
    """a two-sided interval [lo, hi] with coverage `level`, and the point estimate it belongs to"""
    point: float
    lo: float
    hi: float
    level: float

    def __post_init__(self):
        _finite("point", self.point); lo = _finite("lo", self.lo); hi = _finite("hi", self.hi); lv = _finite("level", self.level)
        if lo > hi: raise LabelError("lo %r > hi %r" % (lo, hi))
        if not 0.0 < lv < 1.0: raise LabelError("level must lie in (0, 1), got %r" % lv)


def _require(ci, margin):
    if not isinstance(ci, Interval): raise TypeError("ci must be an Interval, got %s" % type(ci).__name__)
    if not isinstance(margin, Margin): raise TypeError("margin must be a Margin, got %s" % type(margin).__name__)


def _reading(ci, margin, label, kind, rule, **extra):
    r = dict(label=label, kind=kind, rule=rule, point=ci.point, lo=ci.lo, hi=ci.hi, level=ci.level, alpha_per_side=(1.0 - ci.level) / 2.0,
             delta=margin.delta, unit=margin.unit, justification=margin.justification, source=margin.source)
    r.update(extra); return r


def equivalence(ci, *, margin):
    _require(ci, margin); d = margin.delta
    if -d < ci.lo and ci.hi < d: label = EQUIVALENT
    elif ci.lo >= d or ci.hi <= -d: label = NOT_EQUIVALENT
    else: label = INCONCLUSIVE
    return _reading(ci, margin, label, "two-sided", "TOST: EQUIVALENT iff -delta < lo and hi < delta; NOT EQUIVALENT iff lo >= delta or hi <= -delta")


def one_sided(ci, *, margin, material_side, center=0.0):
    _require(ci, margin); c = _finite("center", center)
    if material_side == "upper":
        line = c + margin.delta
        label = WITHIN_MARGIN if ci.hi < line else (BEYOND_MARGIN if ci.lo >= line else INCONCLUSIVE)
    elif material_side == "lower":
        line = c - margin.delta
        label = WITHIN_MARGIN if ci.lo > line else (BEYOND_MARGIN if ci.hi <= line else INCONCLUSIVE)
    else:
        raise LabelError("material_side must be 'upper' or 'lower', got %r" % (material_side,))
    return _reading(ci, margin, label, "one-sided", "line = center %s delta; material side %s" % ("+" if material_side == "upper" else "-", material_side),
                    line=line, material_side=material_side, center=c)


def aggregate(readings):
    readings = list(readings)
    if not readings: raise LabelError("aggregate needs at least one reading")
    labels = [r["label"] for r in readings]; kinds = {r["kind"] for r in readings}
    if len(kinds) != 1: raise LabelError("aggregate cannot mix two-sided and one-sided readings: %s" % sorted(kinds))
    kind = kinds.pop(); extremes = {WITHIN_MARGIN, BEYOND_MARGIN} if kind == "one-sided" else {EQUIVALENT, NOT_EQUIVALENT}
    label = labels[0] if len(set(labels)) == 1 else INCONCLUSIVE
    return dict(label=label, kind=kind, members=labels, seed_conflict=bool(extremes <= set(labels)), n=len(labels), rule="a label holds only if every member has it")


def direction_v4(cells):
    cells = list(cells)
    if not cells or not all(isinstance(c, Interval) for c in cells): raise TypeError("direction_v4 needs a non-empty list of Interval")
    if all(c.point > 0 and c.lo > 0 for c in cells): return "(A)"
    if all(c.hi < 0 for c in cells): return "(B)"
    return "(C)"


def v4_label(cells, *, margin):
    cells = list(cells); d = direction_v4(cells)
    eq = aggregate([equivalence(c, margin=margin) for c in cells])
    return dict(direction=d, equivalence=eq["label"], seed_conflict=eq["seed_conflict"], label=(d if d != "(C)" else "(C) " + eq["label"]),
                delta=margin.delta, unit=margin.unit, justification=margin.justification, source=margin.source)


def _loss(name, x):
    return _finite(name, x) < 0.0


def shared_loss_reading(*, deployed_means, replay_means, differences, margin):
    """both books named as losing must have realised window means < 0; the difference (deployed − replay, one interval per seed/replicate)
    must be EQUIVALENT within ±δ before the loss can be called shared / the strategy's own"""
    dep = [_loss("deployed mean", x) for x in deployed_means]; rep = [_loss("replay mean", x) for x in replay_means]
    if not dep or not rep: raise LabelError("need at least one deployed and one replay mean")
    diffs = [equivalence(ci, margin=margin) for ci in differences]
    if not diffs: raise LabelError("need at least one difference interval")
    agg = aggregate(diffs)
    gap = all(r["lo"] > 0 or r["hi"] < 0 for r in diffs)
    lost_d, lost_r = all(dep), all(rep)
    if lost_d and lost_r:
        label = {EQUIVALENT: "SHARED LOSS, DIFFERENCE EQUIVALENT WITHIN ±δ", NOT_EQUIVALENT: "SHARED LOSS, MATERIAL DIFFERENCE"}.get(agg["label"], "SHARED LOSS, DIFFERENCE INCONCLUSIVE")
    else:
        who = "deployed only lost" if lost_d else ("replay only lost" if lost_r else "neither lost")
        label = "NOT A SHARED LOSS (%s; %s)" % (who, "gap detected" if gap else "no gap detected")
    return dict(label=label, deployed_lost=lost_d, replay_lost=lost_r, difference=agg["label"], difference_members=agg["members"], seed_conflict=agg["seed_conflict"],
                gap_detected=gap, delta=margin.delta, unit=margin.unit, justification=margin.justification, source=margin.source)


def loss_label_admissible(label, realised_means):
    """False when a label asserts a loss (contains LOSS and is not a negation) while any realised mean it covers is >= 0 or not finite"""
    up = str(label).upper(); means = list(realised_means)
    if "LOSS" not in up or up.startswith("NOT A SHARED LOSS") or "NO LOSS" in up: return True
    try: return len(means) > 0 and all(_finite("mean", m) < 0.0 for m in means)
    except LabelError: return False
