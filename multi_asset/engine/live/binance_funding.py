"""Funding ledger for Binance USDT-M perps — the M6 stream, and the input to the §3f wiring check.

★ WHY THIS IS A SEPARATE PIPELINE, NOT A FIELD ON AN ORDER
Funding does not flow through orders. An order log can only ever reconstruct order-derived
quantities; anything that touches ACCOUNT STATE (funding, NAV, positions, liquidations) needs its
own stream. That was one of the two metrics found to be *impossible* from the v1 schema — not hard,
impossible — and the fix was to stop organising the schema by "which metric does this belong to"
and organise it by "which pipeline does this quantity arrive on".

★ THE HARD VENUE LIMIT: income history is retained for the LAST THREE MONTHS ONLY.
So this ledger has exactly the property today taught repeatedly: **what is not recorded cannot be
recovered later**. Beyond 90 days there is no backfill, no support ticket, no workaround. The
ledger therefore (a) pulls incrementally from the last stored settlement, and (b) refuses to
paper over a gap — a gap older than the retention window is permanent, and pretending otherwise
would produce a ledger that looks complete and is not.

★★ THE TRAP THIS FILE EXISTS TO AVOID
GET /fapi/v1/income gives the amount PAID. It does not give the rate, nor the position size.
It is tempting to derive:

        position_notional_at_settlement = funding_paid / funding_rate

...because algebraically that is exact. **Do not.** The §3f wiring check compares
    sign(actual funding cash flow)   vs   sign(our position x the rate we used)
and its whole purpose is to catch a sign or settlement-time error in OUR bookkeeping. If the
position is derived from the cash flow and the rate, the two sides of the comparison come from the
same two numbers and the check becomes **tautological — it can never fail**.

So `position_notional_at_settlement` must come from OUR OWN position record near the settlement.
A check that cannot fail is not a check; it is a green light with no bulb behind it.
"""
from __future__ import annotations

import bisect
import json
import os
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from binance_broker import BinanceBroker, VenueError  # noqa: E402

RETENTION_DAYS = 90          # venue: "Income history only contains data for the last three months"
PAGE_LIMIT = 1000            # venue max per /fapi/v1/income call
SIGN_MISMATCH_THRESHOLD = 0.05   # >5% of settlements inconsistent => wiring error (§3f)


class FundingLedger:
    """Incremental, gap-aware funding ledger emitting schema-v2 `funding` rows."""

    def __init__(self, broker: BinanceBroker, store_path: Optional[str] = None):
        self.broker = broker
        self.store_path = store_path or os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "..", "..",
            "exports", "live", "pilot_log", "funding.jsonl")
        self.rows: List[Dict[str, Any]] = []

    # ── retention ────────────────────────────────────────────────────────────────────────────
    def retention_floor_ms(self, now_ms: Optional[int] = None) -> int:
        now_ms = now_ms or int(time.time() * 1000)
        return now_ms - RETENTION_DAYS * 86400_000

    def gap_report(self, last_stored_ms: Optional[int], now_ms: Optional[int] = None) -> Dict[str, Any]:
        """Answers one question honestly: is anything already unrecoverable?"""
        now_ms = now_ms or int(time.time() * 1000)
        floor = self.retention_floor_ms(now_ms)
        if last_stored_ms is None:
            return {"status": "COLD_START",
                    "recoverable_from_ms": floor,
                    "note": "no prior ledger; only the last 90 days can ever be obtained"}
        if last_stored_ms < floor:
            return {"status": "PERMANENT_GAP",
                    "gap_start_ms": last_stored_ms, "gap_end_ms": floor,
                    "gap_days": round((floor - last_stored_ms) / 86400_000, 2),
                    "note": "settlements in this window are past the venue retention window and "
                            "cannot be recovered by any means. Do not present the ledger as complete."}
        return {"status": "CONTINUOUS", "resume_from_ms": last_stored_ms + 1}

    # ── pulls ────────────────────────────────────────────────────────────────────────────────
    def fetch_income(self, start_ms: int, end_ms: Optional[int] = None) -> List[Dict[str, Any]]:
        """Paginated FUNDING_FEE income. Empty in DRY_RUN — no credentials, no call."""
        if self.broker.mode == "DRY_RUN":
            return []
        out, cursor = [], max(start_ms, self.retention_floor_ms())
        end_ms = end_ms or int(time.time() * 1000)
        while cursor < end_ms:
            page = self.broker._request("GET", "/fapi/v1/income", {
                "incomeType": "FUNDING_FEE", "startTime": cursor,
                "endTime": end_ms, "limit": PAGE_LIMIT}, signed=True)
            if not page:
                break
            out.extend(page)
            newest = max(int(p["time"]) for p in page)
            if len(page) < PAGE_LIMIT:
                break
            if newest <= cursor:        # no forward progress => stop rather than loop forever
                break
            cursor = newest + 1
        return out

    def fetch_rates(self, symbol: str, start_ms: int, end_ms: Optional[int] = None):
        """Public endpoint — the rate is NOT derived from our own cash flow (see module header)."""
        if self.broker.mode == "DRY_RUN":
            return []
        end_ms = end_ms or int(time.time() * 1000)
        return self.broker._request("GET", "/fapi/v1/fundingRate",
                                    {"symbol": symbol, "startTime": start_ms,
                                     "endTime": end_ms, "limit": PAGE_LIMIT})

    # ── row assembly ─────────────────────────────────────────────────────────────────────────
    @staticmethod
    def _nearest_rate(rate_times: List[int], rates: List[float], t: int,
                      tol_ms: int = 5 * 60_000) -> Optional[float]:
        if not rate_times:
            return None
        i = bisect.bisect_left(rate_times, t)
        best = None
        for j in (i - 1, i):
            if 0 <= j < len(rate_times) and abs(rate_times[j] - t) <= tol_ms:
                if best is None or abs(rate_times[j] - t) < abs(rate_times[best] - t):
                    best = j
        return rates[best] if best is not None else None

    def build_rows(self, income: List[Dict[str, Any]],
                   rates_by_symbol: Dict[str, List[Tuple[int, float]]],
                   our_positions: Dict[Tuple[str, int], float]) -> List[Dict[str, Any]]:
        """`our_positions[(symbol, settlement_ms)]` MUST come from our own position record.

        Deriving it from funding_paid / funding_rate would make the §3f sign check tautological —
        both sides would then be functions of the same two numbers, and it could never fail.
        """
        rows = []
        for it in income:
            sym, t = it["symbol"], int(it["time"])
            paid = float(it["income"])
            times = [x[0] for x in rates_by_symbol.get(sym, [])]
            vals = [x[1] for x in rates_by_symbol.get(sym, [])]
            rate = self._nearest_rate(times, vals, t)
            pos = our_positions.get((sym, t))
            rows.append({
                "settlement_ts": t / 1000.0,
                "symbol": sym,
                "position_notional_at_settlement": pos,   # ← OUR record, never derived from paid
                "funding_rate": rate,
                "funding_paid": paid,
            })
        self.rows = rows
        return rows

    # ── §3f: the wiring detector ─────────────────────────────────────────────────────────────
    def sign_consistency(self, rows: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Per-settlement: does the cash we actually received/paid have the sign our position and
        the rate imply? Mechanical, no statistics, live from day one.

        Talking about statistical significance here would be the wrong tool: a wiring error (sign
        flipped, settlement time misaligned) is not a faint effect to be detected against noise —
        it is a large, persistent, deterministic effect. The right question is simply "do these
        two disagree, and how often".
        """
        rows = rows if rows is not None else self.rows
        checked = mismatched = 0
        examples = []
        for r in rows:
            pos, rate, paid = (r.get("position_notional_at_settlement"),
                               r.get("funding_rate"), r.get("funding_paid"))
            if pos is None or rate is None or paid is None:
                continue                     # cannot check; counted in `unverifiable`, not as pass
            if abs(pos) < 1e-9 or abs(rate) < 1e-12 or abs(paid) < 1e-12:
                continue
            checked += 1
            # long pays when rate>0  =>  income has the sign of -(pos * rate)
            if (paid > 0) != (-(pos * rate) > 0):
                mismatched += 1
                if len(examples) < 5:
                    examples.append({k: r[k] for k in
                                     ("settlement_ts", "symbol", "position_notional_at_settlement",
                                      "funding_rate", "funding_paid")})
        frac = (mismatched / checked) if checked else 0.0
        return {
            "checked": checked,
            "unverifiable": len(rows) - checked,
            "mismatched": mismatched,
            "mismatch_frac": round(frac, 6),
            "threshold": SIGN_MISMATCH_THRESHOLD,
            "verdict": "WIRING_ERROR" if (checked and frac > SIGN_MISMATCH_THRESHOLD)
                       else ("OK" if checked else "NO_DATA"),
            "examples": examples,
        }
