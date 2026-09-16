#!/usr/bin/env python3
"""VER-OVERLAP: replay (independent researcher, 608d) vs live book, on the overlap days.

Read-only. Reads:
  - replay : <worktree>/.../current_rule_mark_cash_audit_20260915/completed/nohalt_current_main/audit1/DAILY_AGGREGATES.json
             (+ completed_closure1/completion1/RESULT.json and current_metrics complete_main RESULT.json for pins)
  - live   : ~/dl_quant_live/state/live/pilot_log/<YYYYMMDD>/{daily_nav,fills,funding,anchors}.jsonl

Writes ONE json to the receipts dir given on argv.  Writes nothing else, anywhere.

CALIBER (frozen here, before any number is read):
  unit of comparison = net return as a fraction of NAV over one UTC day, both sides
                       net of fees, net of funding, gross ~2x NAV (see gross columns; live was
                       1.5x for part of the window -> a gross-normalised column is also emitted).
  four buckets, identical definition on both sides:
      price     = everything that is not funding and not fee (mark + realised price move,
                  plus any settlement cash on the replay side)
      funding   = signed funding cash (negative = we paid)
      fee_trade = ordinary trading cost (negative = we paid)
      fee_settle= settlement/delisting cost (negative = we paid)
  replay: price is the residual of the doc's own identity
          net = price + funding_cash - ordinary_fees - settlement_fees   (verified against the doc totals)
  live  : NAV move (flow-adjusted) is ground truth; funding from funding.jsonl by settlement_ts;
          fee from fills.jsonl deduped on (symbol, trade_id) with commission_asset converted;
          price is the residual.  Any live settlement cost would land in price -> reported as 0 and flagged.

DAY BOUNDARY: replay boundaries are exactly 00:00:00Z.  Live daily_nav rows are anchor-time snapshots.
  Two conventions are computed and both reported:
      CONV_A  "watchdog"  day D closes at the LAST daily_nav row of UTC day D      (~20:4xZ)
      CONV_B  "midnight"  day D closes at the FIRST daily_nav row of UTC day D+1   (~00:4xZ)
  CONV_B is nearer the replay's 00:00Z boundary; CONV_A is what the live watchdog uses.
  Buckets are always summed over the SAME interval as the NAV move that they decompose.
"""
import json
import os
import sys
import hashlib
import datetime as dt
from collections import defaultdict

UTC = dt.timezone.utc

WORKTREE = "/Users/haosiyu/Desktop/quant_research/.claude/worktrees/codex-independent-20260907"
RBASE = os.path.join(
    WORKTREE,
    "multi_asset/exports/research/codex_causal_fullchain_2026-09-14/integration",
)
DAILY_AGG = os.path.join(
    RBASE, "current_rule_mark_cash_audit_20260915/completed/nohalt_current_main/audit1/DAILY_AGGREGATES.json"
)
CLOSURE = os.path.join(
    RBASE, "current_rule_mark_cash_audit_20260915/completed_closure1/completion1/RESULT.json"
)
METRICS = os.path.join(RBASE, "current_metrics_20260915/complete_main_20260915/RESULT.json")
REPLAY_DOC = os.path.join(WORKTREE, "docs/RESULT_current_strategy_replay_2026-09-15.md")

LIVE = os.path.expanduser("~/dl_quant_live/state/live/pilot_log")

# one day of run-up (0825) so the first overlap day has a left edge, and 0901 so 0831 has a right edge
DAYS = ["20260825", "20260826", "20260827", "20260828", "20260829", "20260830", "20260831", "20260901"]
OVERLAP = ["20260826", "20260827", "20260828", "20260829", "20260830", "20260831"]


def sha_and_len(path):
    """sha256 + byte count actually read + st_size.  An iCloud-evicted file reads short or
    hangs; we compare the two so an e3b0c442 on a non-empty file cannot pass silently."""
    st = os.stat(path)
    h = hashlib.sha256()
    n = 0
    with open(path, "rb") as fh:
        while True:
            b = fh.read(1 << 20)
            if not b:
                break
            h.update(b)
            n += len(b)
    return {"path": path, "sha256": h.hexdigest(), "bytes_read": n, "st_size": st.st_size,
            "read_equals_size": n == st.st_size}


def jl(path):
    out = []
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def iso(ts):
    return dt.datetime.fromtimestamp(ts, UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def main():
    if len(sys.argv) != 2:
        print("usage: ver_overlap_compare.py <out.json>", file=sys.stderr)
        return 2
    out_path = sys.argv[1]
    facts = {"device": os.path.abspath(__file__), "run_utc": dt.datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")}
    facts["device_self_sha256"] = hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest()

    # ---------------- pins ----------------
    pins = [sha_and_len(p) for p in (DAILY_AGG, CLOSURE, METRICS, REPLAY_DOC)]
    for d in DAYS:
        for f in ("daily_nav", "fills", "funding", "anchors"):
            p = os.path.join(LIVE, d, f + ".jsonl")
            if os.path.exists(p):
                pins.append(sha_and_len(p))
    facts["input_pins"] = pins
    facts["pins_all_fully_read"] = all(p["read_equals_size"] for p in pins)

    # ---------------- replay side ----------------
    agg = json.load(open(DAILY_AGG))
    by_day = {}
    for r in agg:
        key = dt.datetime.fromtimestamp(r["ts_ms"] / 1000, UTC)
        by_day[key.strftime("%Y%m%d")] = r
    facts["replay_n_boundaries"] = len(agg)
    facts["replay_first"] = iso(agg[0]["ts_ms"] / 1000)
    facts["replay_last"] = iso(agg[-1]["ts_ms"] / 1000)
    # every boundary must be exactly 00:00:00Z for the caliber statement to hold
    facts["replay_all_boundaries_at_midnight"] = all(
        dt.datetime.fromtimestamp(r["ts_ms"] / 1000, UTC).strftime("%H%M%S") == "000000" for r in agg
    )

    # whole-window identity check against the published doc totals
    a0, a1 = agg[0], agg[-1]
    t0, t1 = a0["independent_totals"], a1["independent_totals"]
    d_nav = a1["independent_nav"] - a0["independent_nav"]
    d_fund = t1["funding_cash"] - t0["funding_cash"]
    d_fee = t1["ordinary_fees"] - t0["ordinary_fees"]
    d_sfee = t1["settlement_fees"] - t0["settlement_fees"]
    facts["replay_window_identity"] = {
        "net_profit_usdt": d_nav,
        "funding_cash_usdt": d_fund,
        "ordinary_fee_cost_usdt": -d_fee,
        "settlement_fee_cost_usdt": -d_sfee,
        "price_pnl_residual_usdt": d_nav - d_fund + d_fee + d_sfee,
        "doc_says_price_pnl": 363572.31,
        "doc_says_funding": -114015.21,
        "doc_says_ordinary_fee": -24738.04,
        "doc_says_settlement_fee": -26.09,
        "doc_says_net": 224792.97474255,
    }

    replay_days = {}
    for d in OVERLAP:
        nxt = (dt.datetime.strptime(d, "%Y%m%d").replace(tzinfo=UTC) + dt.timedelta(days=1)).strftime("%Y%m%d")
        if d not in by_day or nxt not in by_day:
            replay_days[d] = {"status": "MISSING_BOUNDARY"}
            continue
        r0, r1 = by_day[d], by_day[nxt]
        s0, s1 = r0["independent_totals"], r1["independent_totals"]
        nav0, nav1 = r0["independent_nav"], r1["independent_nav"]
        dn = nav1 - nav0
        df = s1["funding_cash"] - s0["funding_cash"]
        dc = -(s1["ordinary_fees"] - s0["ordinary_fees"])
        ds = -(s1["settlement_fees"] - s0["settlement_fees"])
        replay_days[d] = {
            "status": "OK",
            "t0": iso(r0["ts_ms"] / 1000),
            "t1": iso(r1["ts_ms"] / 1000),
            "nav0": nav0,
            "nav1": nav1,
            "net_usdt": dn,
            "net_pct_of_nav0": 100.0 * dn / nav0,
            "price_usdt": dn - df - dc - ds,
            "funding_usdt": df,
            "fee_trade_usdt": dc,
            "fee_settle_usdt": ds,
            "turnover_usdt": s1["ordinary_turnover"] - s0["ordinary_turnover"],
            "gross_notional_t0": r0.get("independent_gross_notional"),
            "gross_over_nav_t0": (r0.get("independent_gross_notional") or 0.0) / nav0,
            "held_count_t0": r0.get("held_count"),
            "recorded_minus_independent_nav_t1": r1["recorded_nav"] - r1["independent_nav"],
        }
    facts["replay_days"] = replay_days

    # ---------------- live side ----------------
    # 1. NAV snapshots
    nav_rows = {}
    for d in DAYS:
        p = os.path.join(LIVE, d, "daily_nav.jsonl")
        rows = jl(p)
        rows.sort(key=lambda r: r["nav_ts"])
        nav_rows[d] = rows

    # 2. fills, deduped on (symbol, trade_id); keep dedupe counts
    fills = []
    dedupe = {"rows_raw": 0, "rows_kept": 0, "rows_collapsed": 0, "rows_without_trade_id": 0}
    seen = set()
    for d in DAYS:
        p = os.path.join(LIVE, d, "fills.jsonl")
        for r in jl(p):
            dedupe["rows_raw"] += 1
            tid = r.get("trade_id")
            if tid is None:
                dedupe["rows_without_trade_id"] += 1
                key = ("NOID", r["symbol"], r["fill_ts"], r["fill_px"], r["fill_notional"])
            else:
                key = (r["symbol"], tid)
            if key in seen:
                dedupe["rows_collapsed"] += 1
                continue
            seen.add(key)
            dedupe["rows_kept"] += 1
            fills.append(r)
    facts["live_fills_dedupe"] = dedupe

    # 3. funding settlements
    fund = []
    for d in DAYS:
        p = os.path.join(LIVE, d, "funding.jsonl")
        fund.extend(jl(p))
    # funding rows can repeat across day files if a pull overlaps; key on (settlement_ts, symbol)
    fseen, fkept, fdup = set(), [], 0
    for r in fund:
        k = (r["settlement_ts"], r["symbol"])
        if k in fseen:
            fdup += 1
            continue
        fseen.add(k)
        fkept.append(r)
    facts["live_funding_rows"] = {"raw": len(fund), "kept": len(fkept), "collapsed": fdup}
    fund = fkept

    # 4. BNB reference price per anchor, for commission_asset=BNB conversion
    bnb_px = []  # (anchor_ts, px)
    anchors_meta = []
    for d in DAYS:
        p = os.path.join(LIVE, d, "anchors.jsonl")
        for r in jl(p):
            mid = r.get("mid_at_anchor_vector")
            if isinstance(mid, str):
                try:
                    mid = json.loads(mid)
                except Exception:
                    mid = {}
            px = (mid or {}).get("BNBUSDT")
            if px:
                bnb_px.append((r["anchor_ts"], float(px)))
            anchors_meta.append({
                "day": d,
                "anchor_ts": r["anchor_ts"],
                "anchor_utc": iso(r["anchor_ts"]),
                "realized_gross": r.get("realized_gross"),
                "target_gross": r.get("target_gross"),
                "n_names_skipped": r.get("n_names_skipped"),
                "regime": r.get("regime_at_anchor"),
            })
    bnb_px.sort()
    facts["live_bnb_px_points"] = len(bnb_px)
    facts["live_bnb_px_range"] = [bnb_px[0][1], bnb_px[-1][1]] if bnb_px else None

    def bnb_at(ts):
        # nearest anchor mid, no interpolation (a price is a price)
        best, bd = None, None
        for a, px in bnb_px:
            dd = abs(a - ts)
            if bd is None or dd < bd:
                bd, best = dd, px
        return best

    def fee_usdt(r):
        c = r.get("commission")
        a = r.get("commission_asset")
        if c is None:
            return 0.0, "MISSING"
        if a in ("USDT", None):
            return float(c), "USDT"
        if a == "BNB":
            px = bnb_at(r["fill_ts"])
            if px is None:
                return 0.0, "BNB_NO_PX"
            return float(c) * px, "BNB"
        return 0.0, "OTHER:" + str(a)

    # per-fill fee, tallied by asset so the caliber is visible
    fee_by_asset = defaultdict(lambda: {"n": 0, "native": 0.0, "usdt": 0.0})
    for r in fills:
        u, tag = fee_usdt(r)
        k = tag.split(":")[0] if tag.startswith("OTHER") else tag
        fee_by_asset[k]["n"] += 1
        fee_by_asset[k]["native"] += float(r.get("commission") or 0.0)
        fee_by_asset[k]["usdt"] += u
    facts["live_fee_by_asset_whole_window"] = {k: v for k, v in fee_by_asset.items()}

    def sum_interval(t0, t1):
        """funding cash, fee cost, turnover over (t0, t1]."""
        f = sum(float(r["funding_paid"]) for r in fund if t0 < r["settlement_ts"] <= t1)
        c = 0.0
        turn = 0.0
        nfill = 0
        for r in fills:
            if t0 < r["fill_ts"] <= t1:
                u, _ = fee_usdt(r)
                c += u
                turn += abs(float(r["fill_notional"]))
                nfill += 1
        return f, -c, turn, nfill

    def build(conv):
        days = {}
        for d in OVERLAP:
            nxt = (dt.datetime.strptime(d, "%Y%m%d").replace(tzinfo=UTC) + dt.timedelta(days=1)).strftime("%Y%m%d")
            prev = (dt.datetime.strptime(d, "%Y%m%d").replace(tzinfo=UTC) - dt.timedelta(days=1)).strftime("%Y%m%d")
            if conv == "A":       # close = last row of day D ; open = last row of day D-1
                r0 = nav_rows[prev][-1] if nav_rows.get(prev) else None
                r1 = nav_rows[d][-1] if nav_rows.get(d) else None
                flow_days = [d]
            else:                  # close = first row of day D+1 ; open = first row of day D
                r0 = nav_rows[d][0] if nav_rows.get(d) else None
                r1 = nav_rows[nxt][0] if nav_rows.get(nxt) else None
                flow_days = [d, nxt]
            if r0 is None or r1 is None:
                days[d] = {"status": "MISSING_NAV_ROW"}
                continue
            t0, t1 = r0["nav_ts"], r1["nav_ts"]
            # external flow strictly inside (t0, t1]; external_flow_usdt is cumulative since 00:00Z
            flow = 0.0
            flow_detail = []
            for fd in flow_days:
                rows = nav_rows.get(fd) or []
                # flow attributable to this day = last row's cumulative-since-00:00Z value,
                # minus whatever part of it already sat before t0 / after t1
                lo = None
                hi = None
                for rr in rows:
                    if rr["nav_ts"] <= t0:
                        lo = rr.get("external_flow_usdt", 0.0) or 0.0
                    if rr["nav_ts"] <= t1:
                        hi = rr.get("external_flow_usdt", 0.0) or 0.0
                if hi is None:
                    continue
                if lo is None:
                    lo = 0.0
                seg = hi - lo
                if abs(seg) > 1e-9:
                    flow_detail.append({"day": fd, "flow_usdt": seg})
                flow += seg
            nav0, nav1 = r0["nav"], r1["nav"]
            net = nav1 - nav0 - flow
            fnd, fee, turn, nfill = sum_interval(t0, t1)
            days[d] = {
                "status": "OK",
                "t0": iso(t0),
                "t1": iso(t1),
                "hours": (t1 - t0) / 3600.0,
                "nav0": nav0,
                "nav1": nav1,
                "external_flow_usdt": flow,
                "external_flow_detail": flow_detail,
                "net_usdt": net,
                "net_pct_of_nav0": 100.0 * net / nav0,
                "funding_usdt": fnd,
                "fee_trade_usdt": fee,
                "fee_settle_usdt": 0.0,
                "price_usdt": net - fnd - fee,
                "turnover_usdt": turn,
                "n_fills": nfill,
                "sizing_policy_t1": r1.get("sizing_policy"),
                "target_gross_t1": r1.get("target_gross"),
                "ledger_realised_by_type_t1": r1.get("realised_by_type"),
                "unrealised_t0": r0.get("unrealised_pnl"),
                "unrealised_t1": r1.get("unrealised_pnl"),
            }
        return days

    facts["live_days_convA_watchdog"] = build("A")
    facts["live_days_convB_midnight"] = build("B")

    # live gross / NAV per day, from the anchors rows (realized_gross) and the nav row nearest it
    gross = {}
    for d in OVERLAP:
        rows = [a for a in anchors_meta if a["day"] == d]
        navs = nav_rows[d]
        per = []
        for a in rows:
            near = min(navs, key=lambda r: abs(r["nav_ts"] - a["anchor_ts"])) if navs else None
            if near and near["nav"]:
                per.append({"anchor_utc": a["anchor_utc"],
                            "realized_gross": a["realized_gross"],
                            "nav": near["nav"],
                            "gross_over_nav": (a["realized_gross"] or 0.0) / near["nav"],
                            "n_names_skipped": a["n_names_skipped"]})
        gross[d] = {"n_anchors": len(rows), "per_anchor": per,
                    "mean_gross_over_nav": (sum(x["gross_over_nav"] for x in per) / len(per)) if per else None}
    facts["live_gross_by_day"] = gross
    facts["live_anchor_count_in_window"] = len([a for a in anchors_meta if a["day"] in OVERLAP])

    json.dump(facts, open(out_path, "w"), indent=1, sort_keys=False)
    print("WROTE", out_path)
    print("pins_all_fully_read:", facts["pins_all_fully_read"])
    print("replay boundaries:", facts["replay_n_boundaries"],
          facts["replay_first"], "->", facts["replay_last"],
          "all_midnight:", facts["replay_all_boundaries_at_midnight"])
    wi = facts["replay_window_identity"]
    print("replay window identity: price=%.2f (doc %.2f) net=%.2f (doc %.2f)" % (
        wi["price_pnl_residual_usdt"], wi["doc_says_price_pnl"], wi["net_profit_usdt"], wi["doc_says_net"]))
    print("live fills dedupe:", facts["live_fills_dedupe"])
    print("live fee by asset:", dict(facts["live_fee_by_asset_whole_window"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
