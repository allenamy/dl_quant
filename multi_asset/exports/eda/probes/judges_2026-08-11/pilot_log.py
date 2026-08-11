"""Pilot log schema v2 — the frozen record format (§9.5 item ①, spec in protocol §10).

WHY THIS EXISTS: the pilot's entire output is M1-M6, and those can only be computed after the fact
from the log. Anything not written down is gone forever -- a missing field means the pilot ends
with nothing rather than with bad news, and the only remedy is to spend real money again.

v1 was FALSIFIED by 0C (exports/eda/log_schema_falsify.py): 7/7 metrics not cleanly computable,
M6 and the stop-loss inputs outright IMPOSSIBLE. This module implements v2.

★ THE STRUCTURAL LESSON v2 ENCODES (0C): an order log can only reconstruct order-derived
  quantities. Anything about ACCOUNT STATE -- funding, NAV, positions, liquidations -- needs its
  own stream. So the tables here are organised by WHICH PIPE the quantity flows through, not by
  which metric wants it. That is why `funding`, `position_readback` and `daily_nav` are separate
  tables rather than columns bolted onto orders.

Six tables:
  orders             one row per (anchor, symbol, attempt)   -- includes non-events (skips) so the
                                                                denominator of "what we meant to do"
                                                                is recoverable
  fills              one row per CHILD fill                  -- M2 must be computed per fill
  anchors            one row per rebalance anchor
  funding            settlement ledger                       -- M6 impossible without it
  position_readback  venue-reported positions per anchor     -- M5 reconciles against the VENUE
  daily_nav          daily NAV/P&L snapshot                  -- stop-losses must be auditable

Write-time validation is deliberate: a missing required field RAISES at write time, on day 1, when
it is still fixable -- not silently at analysis time when the money is already spent.

Storage: JSONL per table under <root>/<YYYYMMDD>/<table>.jsonl (append-only, human-inspectable,
crash-safe line-by-line).
"""
from __future__ import annotations
import json, os, time
from typing import Any, Dict, List

SCHEMA_VERSION = "v2"

TERMINAL_REASONS = {"filled", "partial_expired", "abandoned_spread_gt_25bps",
                    "abandoned_max_attempts", "skipped_min_notional", "skipped_rate_limit",
                    "venue_reject"}
REGIMES = {"calm", "normal", "stress", "unknown"}   # "unknown" is legitimate and must
# be representable: refusing to write the order because its regime label is missing would
# lose the record entirely, which is strictly worse. pilot_metrics surfaces any unknowns.
ORDER_TYPES = {"maker", "topup_taker"}

# required = must be present as a key; None is allowed only where the event genuinely has no value
# (e.g. a skipped order has no fill price). "not_null" fields must additionally be non-None.
SCHEMA: Dict[str, Dict[str, Any]] = {
    "orders": {
        "required": ["anchor_ts", "symbol", "side", "target_w", "prev_w", "intended_notional",
                     "order_type", "submit_ts", "price_submit", "mid_at_submit", "mid_at_anchor",
                     "filled_notional", "avg_fill_px", "first_fill_ts", "last_fill_ts",
                     "cancel_ts", "fee_paid", "rebalance_id", "attempt_idx", "terminal_reason",
                     "notional_currency"],
        "not_null": ["anchor_ts", "symbol", "order_type", "intended_notional", "mid_at_anchor",
                     "filled_notional", "fee_paid", "rebalance_id", "attempt_idx",
                     "terminal_reason", "notional_currency"],
    },
    "fills": {
        "required": ["anchor_ts", "symbol", "side", "order_type", "attempt_idx", "fill_ts",
                     "fill_px", "fill_notional", "mid_at_fill_plus_60s", "rebalance_id"],
        "not_null": ["anchor_ts", "symbol", "side", "order_type", "attempt_idx", "fill_ts",
                     "fill_px", "fill_notional", "mid_at_fill_plus_60s", "rebalance_id"],
    },
    "anchors": {
        "required": ["anchor_ts", "target_vector_hash", "realized_gross", "target_gross",
                     "n_names_skipped", "regime_at_anchor", "mid_at_anchor_vector",
                     "factor_version", "panel_hash"],
        "not_null": ["anchor_ts", "target_vector_hash", "target_gross", "regime_at_anchor",
                     "mid_at_anchor_vector", "factor_version", "panel_hash"],
    },
    "funding": {
        "required": ["settlement_ts", "symbol", "position_notional_at_settlement", "funding_rate",
                     "funding_paid"],
        "not_null": ["settlement_ts", "symbol", "position_notional_at_settlement", "funding_rate",
                     "funding_paid"],
    },
    "position_readback": {
        "required": ["anchor_ts", "symbol", "venue_position_notional", "source"],
        "not_null": ["anchor_ts", "symbol", "venue_position_notional", "source"],
    },
    "daily_nav": {
        "required": ["day", "target_gross", "nav", "realised_pnl", "unrealised_pnl"],
        "not_null": ["day", "target_gross", "nav", "realised_pnl"],
    },
}


class SchemaError(ValueError):
    pass


def validate(table: str, row: Dict[str, Any]) -> None:
    if table not in SCHEMA:
        raise SchemaError(f"unknown table {table!r}")
    spec = SCHEMA[table]
    missing = [f for f in spec["required"] if f not in row]
    if missing:
        raise SchemaError(f"[{table}] missing required field(s): {missing}. "
                          f"Schema v2 is frozen -- a missing field means the metric it feeds "
                          f"cannot be reconstructed later.")
    nulls = [f for f in spec["not_null"] if row.get(f) is None]
    if nulls:
        raise SchemaError(f"[{table}] field(s) must not be null: {nulls}")
    if table == "orders":
        if row["terminal_reason"] not in TERMINAL_REASONS:
            raise SchemaError(f"terminal_reason {row['terminal_reason']!r} not in {TERMINAL_REASONS}")
        if row["order_type"] not in ORDER_TYPES:
            raise SchemaError(f"order_type {row['order_type']!r} not in {ORDER_TYPES}")
    if table == "anchors" and row["regime_at_anchor"] not in REGIMES:
        raise SchemaError(f"regime_at_anchor {row['regime_at_anchor']!r} not in {REGIMES}")
    if table == "fills" and row["order_type"] not in ORDER_TYPES:
        raise SchemaError(f"order_type {row['order_type']!r} not in {ORDER_TYPES}")


class PilotLogger:
    """Append-only v2 writer. Validates every row at write time."""

    def __init__(self, root: str, day: str | None = None):
        self.day = day or time.strftime("%Y%m%d", time.gmtime())
        self.dir = os.path.join(root, self.day)
        os.makedirs(self.dir, exist_ok=True)
        self._fh: Dict[str, Any] = {}
        meta = os.path.join(self.dir, "_schema.json")
        if not os.path.exists(meta):
            json.dump({"schema_version": SCHEMA_VERSION, "tables": {k: v["required"]
                                                                    for k, v in SCHEMA.items()},
                       "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())},
                      open(meta, "w"), indent=1)

    def _w(self, table: str, row: Dict[str, Any]) -> None:
        validate(table, row)
        if table not in self._fh:
            self._fh[table] = open(os.path.join(self.dir, f"{table}.jsonl"), "a")
        self._fh[table].write(json.dumps(row, default=str) + "\n")
        self._fh[table].flush()

    def order(self, **row):             self._w("orders", row)
    def fill(self, **row):              self._w("fills", row)
    def anchor(self, **row):            self._w("anchors", row)
    def funding(self, **row):           self._w("funding", row)
    def position_readback(self, **row): self._w("position_readback", row)
    def daily_nav(self, **row):         self._w("daily_nav", row)

    def close(self):
        for f in self._fh.values():
            f.close()
        self._fh = {}


def _read_jsonl(path: str) -> List[Dict[str, Any]]:
    """Tolerate a truncated FINAL line.

    An append-only JSONL read while it is being appended to will normally show a partial last line.
    In the production pipeline the writer and reader are the same process running sequentially, so
    this cannot bite there -- but every OTHER reader (audit, post-hoc analysis, an operator with
    `python -c`) is outside that guarantee, and a half-line would make them raise or, worse, skew a
    count. Dropping a trailing partial record is the correct and cheap behaviour; a partial line is
    by definition a record whose write had not completed.
    """
    rows, bad_tail = [], 0
    with open(path) as f:
        lines = f.readlines()
    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            if i == len(lines) - 1:
                bad_tail += 1          # truncated final record: expected, drop it
            else:
                raise                  # a corrupt line in the MIDDLE is real corruption
    return rows


def read_day(root: str, day: str) -> Dict[str, List[Dict[str, Any]]]:
    out: Dict[str, List[Dict[str, Any]]] = {}
    d = os.path.join(root, day)
    for table in SCHEMA:
        p = os.path.join(d, f"{table}.jsonl")
        out[table] = _read_jsonl(p) if os.path.exists(p) else []
    return out


def read_range(root: str, days: List[str]) -> Dict[str, List[Dict[str, Any]]]:
    agg: Dict[str, List[Dict[str, Any]]] = {t: [] for t in SCHEMA}
    for day in days:
        for t, rows in read_day(root, day).items():
            agg[t].extend(rows)
    return agg


def available_days(root: str) -> List[str]:
    if not os.path.isdir(root):
        return []
    return sorted(d for d in os.listdir(root)
                  if len(d) == 8 and d.isdigit() and os.path.isdir(os.path.join(root, d)))
