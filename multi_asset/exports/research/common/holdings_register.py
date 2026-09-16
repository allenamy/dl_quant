#!/usr/bin/env python3
"""holdings_register.py — the three objects of SPEC_TRADABILITY_v2_2026-09-16 as code (FX-DATA, FXR-DATA-1).

v1 used one predicate for three jobs and booked nothing for a position whose name stopped qualifying. Booking nothing is zero
compensation, which the review branch's AGENTS 2026-09-08 rule forbids by name: an unknown exit price for a held position must stop
in an explicit not-priceable state. This module is the reference implementation of the split:

  Object A  `activity_state`  — an admission proxy over a declared window. ACTIVE / QUIET / ACTIVITY_UNKNOWN.
                                It answers "did this name trade recently", nothing else. It may screen admission and may not
                                decide payability or the fate of a held position.
  Object B  `HoldingsRegister` — a position held past the end of admission does not vanish. It keeps quantity, last reliable price
                                and its evidence class, sits in an explicit unknown state, and closes ONLY on evidence.
  Object C  `settlement_pnl`   — exit P&L from original prices, never from the clipped ret5 channel.

Deliberate absences, each of which a red test checks for:
  * no default window and no default stress basis — both are required keywords;
  * no path that writes exit_price = 0 or pnl = 0 for an unpriced position;
  * no transition takes `last_traded_ts`, `dead_after`, or any other future-dependent input.
"""
from dataclasses import dataclass, field
from typing import Optional
import math

WINDOWS = {"W24H": 86400, "W4H": 14400}
ACTIVE, QUIET, ACTIVITY_UNKNOWN = "ACTIVE", "QUIET", "ACTIVITY_UNKNOWN"
OPEN, HELD_QUIET, HELD_UNPRICEABLE = "OPEN", "HELD_QUIET", "HELD_UNPRICEABLE"
CLOSED_BY_TRADE, CLOSED_BY_EVIDENCE = "CLOSED_BY_TRADE", "CLOSED_BY_EVIDENCE"
TERMINAL = (CLOSED_BY_TRADE, CLOSED_BY_EVIDENCE)
PRICE_EVIDENCE = ("TRADE", "MARK_ONLY", "FROZEN_CLOSE", "NONE")
RELIABLE_PRICE_EVIDENCE = ("TRADE",)                    # FROZEN_CLOSE and NONE are not reliable prices (SPEC v2 section 2.3)
EXIT_EVIDENCE = ("TRADE", "SETTLEMENT_RECORD", "ANNOUNCEMENT", "NONE")
STRESS_BASES = ("TO_ZERO", "OBSERVED_RANGE_k", "VOL_MULTIPLE_k", "ANNOUNCED")
K_VOL = 3.0                                             # registered before any v2 number (SPEC v2 section 2.3)
SPEC_V2 = "SPEC_TRADABILITY_v2_2026-09-16.md"


class RegisterError(ValueError):
    """a transition or a reading the contract refuses"""


# ---------------------------------------------------------------- Object A
def activity_state(n_traded, n_untraded, n_nodata, *, window):
    """Counts of bar states inside (A - W, A] -> the admission proxy. `window` is required; there is no default."""
    if window not in WINDOWS:
        raise RegisterError("window must be one of %s (no default), got %r" % (sorted(WINDOWS), window))
    for nm, v in (("n_traded", n_traded), ("n_untraded", n_untraded), ("n_nodata", n_nodata)):
        if int(v) < 0: raise RegisterError("%s must be >= 0" % nm)
    if int(n_traded) > 0: return ACTIVE
    if int(n_untraded) > 0: return QUIET
    return ACTIVITY_UNKNOWN            # NOT "ineligible": archive absence is missing evidence (AGENTS 2026-09-08)


def admits(state):
    """the ONLY decision Object A is allowed to make"""
    return state == ACTIVE


def payable(*_a, **_k):
    """v1 section 5 said a settlement is payable iff the name was tradable. v2 refuses to answer from the proxy."""
    raise RegisterError("payability is not an activity question (SPEC v2 section 1): it needs settlement evidence. "
                        "Use HoldingsRegister.close_by_evidence with a SETTLEMENT_RECORD.")


# ---------------------------------------------------------------- Object B
@dataclass
class Episode:
    symbol: str
    episode_id: str
    entry_anchor_ts: int
    qty: float
    entry_price: Optional[float] = None
    state: str = OPEN
    last_reliable_price: Optional[float] = None
    last_reliable_price_ts: Optional[int] = None
    price_evidence: str = "NONE"
    exit_price: Optional[float] = None
    exit_evidence: str = "NONE"
    opened_at: Optional[int] = None
    resolved_at: Optional[int] = None
    resolution_source: Optional[str] = None
    sigma24: Optional[float] = None
    history: list = field(default_factory=list)

    @property
    def unknown_flag(self):
        return self.exit_price is None

    def as_row(self, *, stress_basis):
        lo, hi = self.stress_prices(stress_basis=stress_basis)
        plo, phi = self.stress_pnl(stress_basis=stress_basis)
        return {"symbol": self.symbol, "episode_id": self.episode_id, "entry_anchor_ts": self.entry_anchor_ts,
                "qty": self.qty, "last_reliable_price": self.last_reliable_price,
                "last_reliable_price_ts": self.last_reliable_price_ts, "price_evidence": self.price_evidence,
                "state": self.state, "exit_price": self.exit_price, "exit_evidence": self.exit_evidence,
                "unknown_flag": self.unknown_flag, "stress_basis": stress_basis,
                "stress_px_lo": lo, "stress_px_hi": hi, "pnl_lo": plo, "pnl_hi": phi,
                "opened_at": self.opened_at, "resolved_at": self.resolved_at, "resolution_source": self.resolution_source}

    def stress_prices(self, *, stress_basis):
        """the registered pair; `stress_basis` is required and named in the output (SPEC v2 section 2.3)"""
        if stress_basis not in STRESS_BASES:
            raise RegisterError("stress_basis must be one of %s (no default)" % list(STRESS_BASES))
        if self.state in TERMINAL and self.exit_price is not None:
            return self.exit_price, self.exit_price
        p = self.last_reliable_price
        if p is None or not math.isfinite(p):
            return None, None                      # unpriceable stays unpriceable; it does not become 0
        if stress_basis == "TO_ZERO":
            return (0.0, p) if self.qty > 0 else (p, 0.0)
        if stress_basis == "VOL_MULTIPLE_k":
            if self.sigma24 is None or not math.isfinite(self.sigma24):
                raise RegisterError("VOL_MULTIPLE_k needs sigma24 on the episode")
            d = K_VOL * self.sigma24 * p
            return p - d, p + d
        if stress_basis == "OBSERVED_RANGE_k":
            raise RegisterError("OBSERVED_RANGE_k needs an observed range; pass it through a subclass rather than guessing")
        if self.exit_price is None:                 # ANNOUNCED with no price announced yet is still unresolved
            return None, None
        return self.exit_price, self.exit_price

    def stress_pnl(self, *, stress_basis):
        lo, hi = self.stress_prices(stress_basis=stress_basis)
        if lo is None or hi is None or self.entry_price is None:
            return None, None
        a = self.qty * (lo - self.entry_price); b = self.qty * (hi - self.entry_price)
        return (a, b) if a <= b else (b, a)


class HoldingsRegister:
    """Every transition takes only information available at the anchor it is called with. No method accepts
    `last_traded_ts`, `dead_after`, or any other quantity that reads the future (SPEC v2 section 2.2 rule 2, red test RT-5)."""

    def __init__(self, *, spec=SPEC_V2):
        self.spec = spec
        self.episodes = {}

    def open(self, symbol, anchor_ts, qty, entry_price):
        if qty == 0: raise RegisterError("an episode with qty 0 is not a position")
        eid = "%s@%d" % (symbol, int(anchor_ts))
        e = Episode(symbol=symbol, episode_id=eid, entry_anchor_ts=int(anchor_ts), qty=float(qty),
                    opened_at=int(anchor_ts), entry_price=float(entry_price))
        e.history.append((int(anchor_ts), OPEN, "open"))
        self.episodes[eid] = e
        return e

    def mark(self, episode, anchor_ts, *, activity, price=None, price_evidence="NONE", sigma24=None):
        """advance one anchor. `activity` is Object A's state; it may move the position out of OPEN and may never close it."""
        if price_evidence not in PRICE_EVIDENCE:
            raise RegisterError("price_evidence must be one of %s" % list(PRICE_EVIDENCE))
        if episode.state in TERMINAL:
            return episode
        if price is not None and price_evidence in RELIABLE_PRICE_EVIDENCE and math.isfinite(price):
            episode.last_reliable_price = float(price); episode.last_reliable_price_ts = int(anchor_ts)
            episode.price_evidence = price_evidence
        if sigma24 is not None and math.isfinite(sigma24):
            episode.sigma24 = float(sigma24)
        if activity == ACTIVE:
            new = OPEN
        elif episode.last_reliable_price is None:
            new = HELD_UNPRICEABLE
        else:
            new = HELD_QUIET
        if new != episode.state:
            episode.history.append((int(anchor_ts), new, "activity=%s" % activity))
            episode.state = new
        return episode

    def mark_unpriceable(self, episode, anchor_ts, reason):
        """no trade-backed price within the declared reliability window"""
        if episode.state in TERMINAL: raise RegisterError("episode already closed")
        episode.state = HELD_UNPRICEABLE
        episode.history.append((int(anchor_ts), HELD_UNPRICEABLE, reason))
        return episode

    def close_by_trade(self, episode, anchor_ts, price):
        if not math.isfinite(price): raise RegisterError("a fill must carry a finite price")
        episode.state = CLOSED_BY_TRADE; episode.exit_price = float(price); episode.exit_evidence = "TRADE"
        episode.resolved_at = int(anchor_ts); episode.history.append((int(anchor_ts), CLOSED_BY_TRADE, "fill"))
        return episode

    def close_by_evidence(self, episode, anchor_ts, price, *, evidence, source):
        """the ONLY other way a position leaves the register. A timer cannot. An absence of rows cannot. Zero cannot."""
        if evidence not in ("SETTLEMENT_RECORD", "ANNOUNCEMENT"):
            raise RegisterError("close_by_evidence needs SETTLEMENT_RECORD or ANNOUNCEMENT, got %r" % evidence)
        if price is None or not math.isfinite(price):
            raise RegisterError("closing evidence must name a price; a missing price leaves the episode unresolved")
        if not source: raise RegisterError("closing evidence must name its source file and row")
        episode.state = CLOSED_BY_EVIDENCE; episode.exit_price = float(price); episode.exit_evidence = evidence
        episode.resolved_at = int(anchor_ts); episode.resolution_source = str(source)
        episode.history.append((int(anchor_ts), CLOSED_BY_EVIDENCE, "%s:%s" % (evidence, source)))
        return episode

    # ---- reporting contract (SPEC v2 section 2.2 rule 3, red test RT-6) ----
    def unresolved(self):
        return [e for e in self.episodes.values() if e.state not in TERMINAL]

    def report_net(self, point_estimate, *, stress_basis):
        """a net number may not be quoted while unresolved episodes exist unless their interval travels with it"""
        un = self.unresolved()
        if not un:
            return {"point": point_estimate, "unresolved_episodes": 0, "interval": None,
                    "statement": "no unresolved episodes"}
        lo = hi = 0.0; unquantified = 0
        for e in un:
            a, b = e.stress_pnl(stress_basis=stress_basis)
            if a is None or b is None: unquantified += 1
            else: lo += a; hi += b
        return {"point": point_estimate, "unresolved_episodes": len(un), "stress_basis": stress_basis,
                "interval": [point_estimate + lo, point_estimate + hi], "unquantified_episodes": unquantified,
                "statement": ("%d unresolved episode(s) present; the point estimate books nothing for them and the "
                              "interval is the registered %s scenario" % (len(un), stress_basis))}


# ---------------------------------------------------------------- Object C
def settlement_pnl(qty, entry_price, exit_price):
    """exit P&L from original prices. Never call this with a price rebuilt from the clipped ret5 channel; use
    common/bound_bars.py assert_clean on the window first (SPEC v2 section 3.1, red test RT-7)."""
    if exit_price is None:
        raise RegisterError("exit P&L is not defined without an exit price; the episode belongs in the register")
    return float(qty) * (float(exit_price) - float(entry_price))
