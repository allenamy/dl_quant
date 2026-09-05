import json, glob, os, collections, sys
base = os.path.expanduser("~/dl_quant_live/state/live/pilot_log")
days = [d for d in sorted(os.listdir(base)) if d.isdigit() and "20260826" <= d <= "20260905"]
print("days:", days)
for tbl in ["orders", "fills", "anchors", "daily_nav", "funding", "position_readback"]:
    keys = collections.Counter(); n = 0
    cats = collections.defaultdict(collections.Counter)
    catf = {"orders": ["order_type", "terminal_reason", "placement_arm", "topup_source", "side", "notional_currency", "fee_source", "attempt_idx"],
            "fills": ["order_type", "side", "commission_asset", "venue_maker_flag", "attempt_idx", "mid_at_fill_plus_60s_note"],
            "anchors": ["regime_at_anchor", "factor_version"],
            "daily_nav": ["sizing_policy", "mode"],
            "funding": ["funding_interval_h", "funding_interval_source"],
            "position_readback": ["source", "held", "targeted"]}[tbl]
    for d in days:
        p = f"{base}/{d}/{tbl}.jsonl"
        if not os.path.exists(p): continue
        for line in open(p):
            line = line.strip()
            if not line: continue
            try: r = json.loads(line)
            except Exception as e: print("BAD", p, e); continue
            n += 1
            for k in r: keys[k] += 1
            for c in catf:
                v = r.get(c, "<absent>")
                if isinstance(v, str) and len(v) > 80: v = v[:80] + "..."
                cats[c][str(v)] += 1
    print(f"\n=== {tbl}: n={n}")
    for k, c in keys.most_common(): print(f"  {k}: {c}")
    for c in catf:
        print(f"  -- {c}:")
        for v, cnt in cats[c].most_common(12): print(f"       {cnt:8d}  {v}")
