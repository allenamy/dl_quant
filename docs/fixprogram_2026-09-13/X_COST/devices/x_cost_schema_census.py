#!/usr/bin/env python3
"""X-COST step 0: schema census (value SETS only) — committed before it is run.

Purpose: the decomposition device (x_cost_decompose.py) must name every category that occurs in the ledger so its
identity is exact. This census reads the LIVE pilot_log read-only and prints, per table, the set of keys and the set of
values of categorical fields. It computes NO notional, NO fee, NO count per category, NO price, NO markout.

Barrier: fields that carry experiment outcomes (prices, mids, markouts, fill prices) are never loaded; rows are projected
onto an allow-list of categorical fields at parse time.

Usage: python3 x_cost_schema_census.py <out_json>
"""
import json, os, sys, glob

ROOT = "/Users/haosiyu/dl_quant_live/state/live/pilot_log"
DAYS = [f"202608{d:02d}" for d in range(28, 32)] + [f"202609{d:02d}" for d in range(1, 14)]
CAT_ORDERS = ("order_type", "topup_source", "terminal_reason", "chase_arm", "chase_arm_assigned", "requote_arm",
              "attempt_idx", "side", "notional_currency", "fee_source")
CAT_FILLS = ("order_type", "commission_asset", "venue_maker_flag", "attempt_idx", "side")
CAT_ANCH_TOP = ("book_source", "opening_halted")


def rows(path):
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except ValueError:
                yield {"__unparsable__": True}
                continue
            yield r if isinstance(r, dict) else {"__not_a_dict__": True}


def main(out):
    res = {"root": ROOT, "days": DAYS, "orders": {"keys": set(), "values": {k: set() for k in CAT_ORDERS}},
           "fills": {"keys": set(), "values": {k: set() for k in CAT_FILLS}},
           "anchors": {"keys": set(), "values": {k: set() for k in CAT_ANCH_TOP},
                       "chase_experiment_keys": set(), "reshape_keys": set(), "external_book_keys": set(),
                       "excluded_because_prefixes": set()},
           "rid_prefixes": set(), "anomalies": []}
    for d in DAYS:
        for r in rows(os.path.join(ROOT, d, "orders.jsonl")):
            if "__unparsable__" in r or "__not_a_dict__" in r:
                res["anomalies"].append(f"orders {d}: {list(r)[0]}"); continue
            res["orders"]["keys"].update(r.keys())
            for k in CAT_ORDERS:
                if k in r:
                    res["orders"]["values"][k].add(json.dumps(r[k]))
            res["rid_prefixes"].add(str(r.get("rebalance_id"))[:1])
        for r in rows(os.path.join(ROOT, d, "fills.jsonl")):
            if "__unparsable__" in r or "__not_a_dict__" in r:
                res["anomalies"].append(f"fills {d}: {list(r)[0]}"); continue
            res["fills"]["keys"].update(r.keys())
            for k in CAT_FILLS:
                if k in r:
                    res["fills"]["values"][k].add(json.dumps(r[k]))
        for r in rows(os.path.join(ROOT, d, "anchors.jsonl")):
            if "__unparsable__" in r or "__not_a_dict__" in r:
                res["anomalies"].append(f"anchors {d}: {list(r)[0]}"); continue
            res["anchors"]["keys"].update(r.keys())
            for k in CAT_ANCH_TOP:
                if k in r:
                    res["anchors"]["values"][k].add(json.dumps(r[k]))
            ce = r.get("chase_experiment")
            if isinstance(ce, dict):
                res["anchors"]["chase_experiment_keys"].update(ce.keys())
                for e in (ce.get("excluded_because") or []):
                    res["anchors"]["excluded_because_prefixes"].add(str(e)[:40])
            rs = r.get("reshape")
            if isinstance(rs, dict):
                res["anchors"]["reshape_keys"].update(rs.keys())
            eb = r.get("external_book")
            if isinstance(eb, dict):
                res["anchors"]["external_book_keys"].update(eb.keys())

    def ser(x):
        if isinstance(x, set):
            return sorted(x)
        if isinstance(x, dict):
            return {k: ser(v) for k, v in x.items()}
        return x
    json.dump(ser(res), open(out, "w"), indent=1, ensure_ascii=False)
    print("SUMMARY x_cost_schema_census days=%d anomalies=%d out=%s" % (len(DAYS), len(res["anomalies"]), out))


if __name__ == "__main__":
    main(sys.argv[1])
