#!/usr/bin/env python3
"""W2 2026-09-12 receipt: the three buckets on the LIVE ledger COPY (read-only), per anchor, under the
canonical rule (anchor_loop.neutrality_price _pos/_fee), beside the pre-fix daily_summary formula.
Usage: python3 real_ledger_profile.py /Users/haosiyu/cc_tmp/exec_w2/state/live/pilot_log 20260805 20260912"""
import json, os, sys
def pos(x):
    try: v=float(x)
    except (TypeError,ValueError): return None
    return v if (v==v and v not in (float('inf'),float('-inf')) and v>0) else None
def fee(o):
    f=o.get("fee_paid")
    if f is None: return None
    if o.get("fee_all_usdt") is False and not o.get("fee_conversion"): return None
    try: v=float(f)
    except (TypeError,ValueError): return None
    return v if (v==v and v not in (float('inf'),float('-inf'))) else None
root=sys.argv[1]
for day in sys.argv[2:]:
    rows=[json.loads(l) for l in open(os.path.join(root,day,"orders.jsonl")) if l.strip()]
    anchors=[json.loads(l) for l in open(os.path.join(root,day,"anchors.jsonl")) if l.strip()]
    for a in anchors:
        ats=float(a["anchor_ts"]); rid=a.get("rebalance_id")
        og=[o for o in rows if float(o.get("anchor_ts") or 0)==ats]
        fl=[o for o in og if o.get("filled_notional") is not None and abs(float(o["filled_notional"]))>0]
        if not fl: print(day, rid, "no fills"); continue
        priced=[o for o in fl if pos(o.get("avg_fill_px")) and pos(o.get("mid_at_anchor"))]
        meas=[o for o in priced if fee(o) is not None]
        notl=sum(abs(float(o["filled_notional"])) for o in fl); np_=sum(abs(float(o["filled_notional"])) for o in priced); nm=sum(abs(float(o["filled_notional"])) for o in meas)
        fee_m=sum(fee(o) for o in meas); adv=sum((1 if float(o["filled_notional"])>0 else -1)*(pos(o["avg_fill_px"])-pos(o["mid_at_anchor"]))/pos(o["mid_at_anchor"])*abs(float(o["filled_notional"])) for o in meas)
        fee_old=sum(float(o.get("fee_paid") or 0) for o in priced); adv_old=sum((1 if float(o["filled_notional"])>0 else -1)*(float(o["avg_fill_px"])-float(o["mid_at_anchor"]))/float(o["mid_at_anchor"])*abs(float(o["filled_notional"])) for o in priced)
        new=(1e4*(fee_m+adv)/nm) if nm else None; old=(1e4*(fee_old+adv_old)/np_) if np_ else None
        print(f"{day} {rid} filled={len(fl)} priced={len(priced)} measured={len(meas)} fee_unknown={len(priced)-len(meas)} unpriced={len(fl)-len(priced)} "
              f"notl={notl:.4f} measured_notl={nm:.4f} cov={(nm/notl):.4f} NEW_bps={new} OLD_bps={old}")
