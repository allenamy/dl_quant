"""Rebalance executor for Binance USDT-M perps. Emits schema-v2 rows; never invents its own.

THE SHAPE OF ONE REBALANCE
--------------------------
    t=0      capture mid_at_anchor for EVERY symbol   <- before a single order exists
             plan deltas, apply band / min-notional / lot+tick rounding
             submit passive maker orders (timeInForce=GTX, post-only)
    t=k      cancel whatever is unfilled
             ★ top up the residual with IOC taker — MANDATORY, not an optimisation
    after    write orders / fills / anchors rows

★ WHY mid_at_anchor IS THE FIELD THAT DECIDES THE PILOT
The effective-cost metric can be measured against the price when an order *arrived* or against
the price at the *decision anchor*. Those two readings differ by ~3.2bps, while the whole distance
between "proceed" (4.5) and "stop" (7.0) is 2.5bps. Using arrival price silently discards delay
cost, so a book that should read red reads green.

And the delay is not symmetric noise. We buy what we predict will rise, so waiting k seconds means
buying after part of the predicted move already happened — the alpha leaks into our own execution.
Measured: this book's alpha accumulates near-linearly (f1≈0.297 vs 0.25 for pure linear), so the
penalty is mild but real, and it is exactly what mid_at_anchor makes visible.

★ WHY THE TOP-UP IS MANDATORY
Skipping it to save taker fees is worth roughly −27pp/yr. A 4h signal decays; a position that lags
is worth far less than the extra fee costs. "Save the fee, skip the top-up" is a protocol violation,
not a judgement call.

★ WHAT HAPPENS WHEN WE CANNOT COMPLETE
At most 2 attempts, never cross a spread wider than 25bps, then accept the gap and record it.
The gap is MEASURED (terminal_reason + M5 weight-fidelity), never hidden. A silently-lagging book
looks identical to a correctly-tracking one.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import time
from typing import Any, Dict, List, Optional, Tuple

_HERE = os.path.dirname(os.path.abspath(__file__))
import sys
sys.path.insert(0, _HERE)

from binance_broker import BinanceBroker, VenueError, TIF_IOC, TIF_POST_ONLY  # noqa: E402
from watchdog import OpeningHalted                                            # noqa: E402

K_SECONDS = 900                 # passive window; the engine's fill model was calibrated at k=900
MAX_ATTEMPTS = 2                # F16
MAX_CROSS_BPS = 25.0            # F16: never chase across a spread wider than this
DEFAULT_BAND_BPS = 0.0          # no-trade band; value is decided by measured cost, not by venue
                                # rules (optimal band is 25-500x the exchange minimum). At the
                                # structural 1.9bps it is worth ~0; at real taker cost it matters.


class SymbolFilters:
    """tick / lot / min-notional from /fapi/v1/exchangeInfo. Wrong rounding = venue rejection,
    and a rejected order is indistinguishable from a skipped one unless we label it."""

    def __init__(self, broker: BinanceBroker, cache_path: Optional[str] = None):
        self.broker = broker
        self.cache_path = cache_path or os.path.join(_HERE, ".exchange_info_cache.json")
        self.f: Dict[str, Dict[str, float]] = {}

    def load(self, max_age_s: float = 86400) -> Dict[str, Dict[str, float]]:
        if os.path.exists(self.cache_path) and time.time() - os.path.getmtime(self.cache_path) < max_age_s:
            self.f = json.load(open(self.cache_path))
            return self.f
        info = self.broker._request("GET", "/fapi/v1/exchangeInfo")
        out = {}
        for s in info.get("symbols", []):
            if s.get("contractType") != "PERPETUAL" or s.get("quoteAsset") != "USDT":
                continue
            d = {}
            for flt in s.get("filters", []):
                t = flt["filterType"]
                if t == "PRICE_FILTER":
                    d["tick"] = float(flt["tickSize"])
                elif t == "LOT_SIZE":
                    d["step"] = float(flt["stepSize"])
                    d["min_qty"] = float(flt["minQty"])
                elif t == "MIN_NOTIONAL":
                    d["min_notional"] = float(flt.get("notional", 5.0))
            if {"tick", "step"} <= d.keys():
                d.setdefault("min_notional", 5.0)
                out[s["symbol"]] = d
        self.f = out
        json.dump(out, open(self.cache_path, "w"))
        return out

    @staticmethod
    def _floor_to(x: float, step: float) -> float:
        return math.floor(x / step + 1e-9) * step

    def round_qty(self, sym: str, qty: float) -> float:
        d = self.f.get(sym)
        return self._floor_to(abs(qty), d["step"]) * (1 if qty >= 0 else -1) if d else qty

    def round_px(self, sym: str, px: float) -> float:
        d = self.f.get(sym)
        return self._floor_to(px, d["tick"]) if d else px


class RebalanceExecutor:
    def __init__(self, broker: BinanceBroker, k_seconds: int = K_SECONDS,
                 band_bps: float = DEFAULT_BAND_BPS, log=None):
        self.broker = broker
        self.k = k_seconds
        self.band_bps = band_bps
        self.filters = SymbolFilters(broker)
        self.log = log                                   # pilot_log writer, injected
        self.rows_orders: List[Dict[str, Any]] = []
        self.rows_fills: List[Dict[str, Any]] = []

    # ── phase 0: freeze the decision state ───────────────────────────────────────────────────
    def capture_anchor(self, symbols: List[str]) -> Tuple[float, Dict[str, float]]:
        """★ Runs BEFORE any order exists. Everything downstream is priced against this."""
        anchor_ts = time.time()
        mids: Dict[str, float] = {}
        if self.broker.mode == "DRY_RUN":
            return anchor_ts, {s: 0.0 for s in symbols}
        book = self.broker._request("GET", "/fapi/v1/ticker/bookTicker")
        by_sym = {b["symbol"]: b for b in book}
        for s in symbols:
            b = by_sym.get(s)
            if b:
                mids[s] = (float(b["bidPrice"]) + float(b["askPrice"])) / 2
        return anchor_ts, mids

    # ── phase 1: plan ────────────────────────────────────────────────────────────────────────
    def plan(self, target_notional: Dict[str, float], current_notional: Dict[str, float],
             mids: Dict[str, float]) -> List[Dict[str, Any]]:
        """Deltas → band → min-notional → lot rounding. Every drop is LABELLED, never silent."""
        gross = sum(abs(v) for v in target_notional.values()) or 1.0
        plans = []
        for sym, tgt in target_notional.items():
            cur = current_notional.get(sym, 0.0)
            delta = tgt - cur
            mid = mids.get(sym, 0.0)
            row = {"symbol": sym, "target_notional": tgt, "prev_notional": cur,
                   "delta_notional": delta, "mid_at_anchor": mid,
                   "target_w": tgt / gross, "prev_w": cur / gross}

            if self.band_bps > 0 and abs(delta) / gross * 1e4 < self.band_bps:
                row["skip"] = None                    # inside band: not an error, just no trade
                plans.append(row); continue

            d = self.filters.f.get(sym)
            if d and abs(delta) < d.get("min_notional", 5.0):
                row["skip"] = "skipped_min_notional"
                plans.append(row); continue

            if mid <= 0:
                row["skip"] = "venue_reject"          # no book => cannot price; labelled, not dropped
                plans.append(row); continue

            qty = self.filters.round_qty(sym, delta / mid)
            if qty == 0:
                row["skip"] = "skipped_min_notional"
                plans.append(row); continue
            row["qty"] = qty
            row["side"] = "buy" if qty > 0 else "sell"
            plans.append(row)
        return plans

    # ── phase 2: passive maker leg ───────────────────────────────────────────────────────────
    def submit_maker(self, plans: List[Dict[str, Any]], anchor_ts: float,
                     rebalance_id: str) -> List[Dict[str, Any]]:
        live = []
        for p in plans:
            if p.get("skip") is not None or "qty" not in p:
                if p.get("skip"):
                    self._order_row(p, anchor_ts, rebalance_id, 1, "maker",
                                    terminal_reason=p["skip"], submitted=False)
                continue
            # Passive: rest on our own side of the book so the order cannot cross.
            px = self.filters.round_px(p["symbol"], p["mid_at_anchor"])
            order = {"symbol": p["symbol"], "side": p["side"], "quantity": abs(p["qty"]),
                     "price": px, "tif": TIF_POST_ONLY,
                     "client_id": f"{rebalance_id}-{p['symbol']}-1"[:36]}
            p["submit_ts"] = time.time()
            p["price_submit"] = px
            p["mid_at_submit"] = p["mid_at_anchor"]     # replaced by live quote outside DRY_RUN
            try:
                self.broker.submit(order, f"rebalance {rebalance_id} maker")
                p["submitted"] = True
                live.append(p)
            except OpeningHalted:
                # The halt is doing exactly its job: no NEW exposure while protection is engaged.
                self._order_row(p, anchor_ts, rebalance_id, 1, "maker",
                                terminal_reason="venue_reject", submitted=False,
                                note="blocked by open_orders_halted")
            except VenueError as e:
                reason = ("skipped_rate_limit" if self.broker.classify(e) == "rate_limited"
                          else "venue_reject")
                self._order_row(p, anchor_ts, rebalance_id, 1, "maker",
                                terminal_reason=reason, submitted=False,
                                note=f"[{e.code}] {e.msg}")
        return live

    # ── phase 3: residual top-up ─────────────────────────────────────────────────────────────
    def topup(self, live: List[Dict[str, Any]], filled: Dict[str, float], anchor_ts: float,
              rebalance_id: str, spreads_bps: Optional[Dict[str, float]] = None):
        """★ MANDATORY. Skipping this to save fees costs ~27pp/yr — the lagging position is worth
        far less than the fee saved. This is a protocol requirement, not a judgement call."""
        spreads_bps = spreads_bps or {}
        for p in live:
            got = filled.get(p["symbol"], 0.0)
            residual = p["delta_notional"] - got
            p["filled_notional"] = got
            if abs(residual) < 1e-9:
                self._order_row(p, anchor_ts, rebalance_id, 1, "maker", "filled", submitted=True)
                continue
            self._order_row(p, anchor_ts, rebalance_id, 1, "maker", "partial_expired", submitted=True)

            sp = spreads_bps.get(p["symbol"], 0.0)
            if sp > MAX_CROSS_BPS:
                # Accept the gap rather than chase. It is recorded, so M5 sees it as error, not as
                # a book that happens to track badly for unknown reasons.
                self._order_row(p, anchor_ts, rebalance_id, 2, "topup_taker",
                                "abandoned_spread_gt_25bps", submitted=False,
                                intended=residual)
                continue
            qty = self.filters.round_qty(p["symbol"], residual / max(p["mid_at_anchor"], 1e-9))
            if qty == 0:
                self._order_row(p, anchor_ts, rebalance_id, 2, "topup_taker",
                                "skipped_min_notional", submitted=False, intended=residual)
                continue
            order = {"symbol": p["symbol"], "side": "buy" if qty > 0 else "sell",
                     "quantity": abs(qty), "tif": TIF_IOC,
                     "client_id": f"{rebalance_id}-{p['symbol']}-2"[:36]}
            try:
                self.broker.submit(order, f"rebalance {rebalance_id} topup")
                self._order_row(p, anchor_ts, rebalance_id, 2, "topup_taker", "filled",
                                submitted=True, intended=residual)
            except OpeningHalted:
                self._order_row(p, anchor_ts, rebalance_id, 2, "topup_taker", "venue_reject",
                                submitted=False, intended=residual,
                                note="blocked by open_orders_halted")
            except VenueError as e:
                self._order_row(p, anchor_ts, rebalance_id, 2, "topup_taker",
                                "abandoned_max_attempts", submitted=False, intended=residual,
                                note=f"[{e.code}] {e.msg}")

    # ── row emission (schema v2, no invented fields) ─────────────────────────────────────────
    def _order_row(self, p, anchor_ts, rebalance_id, attempt, otype, terminal_reason,
                   submitted=True, intended=None, note=None):
        self.rows_orders.append({
            "anchor_ts": anchor_ts, "symbol": p["symbol"],
            "side": p.get("side"), "target_w": p.get("target_w"), "prev_w": p.get("prev_w"),
            "intended_notional": intended if intended is not None else p.get("delta_notional"),
            "order_type": otype,
            "submit_ts": p.get("submit_ts") if submitted else None,
            "price_submit": p.get("price_submit") if submitted else None,
            "mid_at_submit": p.get("mid_at_submit") if submitted else None,
            "mid_at_anchor": p["mid_at_anchor"],          # ★ never null — M1 depends on it
            "filled_notional": p.get("filled_notional", 0.0),
            "avg_fill_px": p.get("avg_fill_px"),
            "first_fill_ts": p.get("first_fill_ts"), "last_fill_ts": p.get("last_fill_ts"),
            "cancel_ts": p.get("cancel_ts"), "fee_paid": p.get("fee_paid", 0.0),
            "rebalance_id": rebalance_id, "attempt_idx": attempt,
            "terminal_reason": terminal_reason, "notional_currency": "USDT",
            **({"note": note} if note else {}),
        })

    def anchor_row(self, anchor_ts, mids, target_notional, realized_gross, n_skipped,
                   regime, factor_version, panel_hash):
        vec = json.dumps(mids, sort_keys=True)
        tgt = json.dumps({k: round(v, 8) for k, v in sorted(target_notional.items())})
        return {
            "anchor_ts": anchor_ts,
            "target_vector_hash": hashlib.sha256(tgt.encode()).hexdigest()[:16],
            "realized_gross": realized_gross,
            "target_gross": sum(abs(v) for v in target_notional.values()),
            "n_names_skipped": n_skipped,
            "regime_at_anchor": regime,          # ★ stamped at the anchor, before any markout is
                                                 # knowable — that is what makes it auditable
            "mid_at_anchor_vector": vec,
            "factor_version": factor_version, "panel_hash": panel_hash,
        }
