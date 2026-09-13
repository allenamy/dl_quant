#!/usr/bin/python3
"""OPS-03 measurement (read-only): replay each anchor's RECORDED request timeline (state/live/rate_timeline/<rid>.json,
host fapi.binance.com, rows with request=True, in time order) through two weight shapers with the same 1,000/min cap:
  FIXED   — today's RateBudget.spend_weight: a 60 s window opened by the first spend after a reset (live/rate_budget.py L147-166)
  SLIDING — any 60 s sliding window holds at most the cap; a request that would exceed it waits until enough weight ages out
and report, per anchor: the recorded sliding-60 s weight maximum, the sliding maximum after each shaper, how many requests
each shaper delays, the total and maximum added delay, and the time by which the last request would be pushed. Order
count and raw request count are already shaped by sliding windows in production and are reported, not re-shaped.
Writes argv[2] only. Usage: ops03_sliding_shaper_replay.py <rate_timeline_dir> <receipt.json> <rid>..."""
import collections, json, os, sys
TL, OUT, RIDS = sys.argv[1], sys.argv[2], sys.argv[3:]
CAP, WIN = 1000, 60.0
def maxwin(tw):
    m = s = 0; j = 0
    for i in range(len(tw)):
        s += tw[i][1]
        while tw[i][0] - tw[j][0] >= WIN: s -= tw[j][1]; j += 1
        m = max(m, s)
    return m
def fixed(reqs):
    out, used, start, delays = [], 0, None, []
    t_shift = 0.0
    for t, w in reqs:
        t = t + t_shift
        if start is None or t - start >= WIN: used, start = 0, t
        if used + w > CAP:
            wait = WIN - (t - start) + 0.25
            t_shift += wait; t += wait; delays.append(wait); used, start = w, t
        else:
            used += w
        out.append((t, w))
    return out, delays
def sliding(reqs, tag=None):
    out, delays, t_shift = [], [], 0.0
    where = collections.Counter()
    win = collections.deque(); s = 0
    for t, w in reqs:
        t = t + t_shift
        while win and t - win[0][0] >= WIN: s -= win.popleft()[1]
        if s + w > CAP:
            acc, need, wait_until = 0, s + w - CAP, t
            for tt, ww in win:
                acc += ww
                if acc >= need: wait_until = tt + WIN; break
            wait = max(0.0, wait_until - t) + 1e-6
            t_shift += wait; t += wait; delays.append(wait)
            if tag is not None:
                where[tag[len(out)]] += 1
            while win and t - win[0][0] >= WIN: s -= win.popleft()[1]
        win.append((t, w)); s += w; out.append((t, w))
    return (out, delays, where) if tag is not None else (out, delays)
res = {"cap_weight_per_min": CAP, "anchors": {}}
for rid in RIDS:
    p = os.path.join(TL, rid + ".json")
    rows = json.load(open(p))["rows"]
    _rq = sorted((r for r in rows if r.get("request") and r.get("host") == "fapi.binance.com"), key=lambda r: r["ts"])
    reqs = [(r["ts"], int(r.get("weight") or 0)) for r in _rq]
    hdr = [r for r in rows if r.get("kind") == "venue_header"]
    f_out, f_del = fixed(reqs)
    _tags = [("ORDER " if r.get("order") else "") + str(r.get("path")) for r in _rq]
    s_out, s_del, s_where = sliding(reqs, _tags)
    t0 = reqs[0][0] if reqs else 0.0
    _first_delay = next((i for i, (a_, b_) in enumerate(zip(reqs, s_out)) if b_[0] - a_[0] > 1e-3), None)
    res["anchors"][rid] = {
        "n_requests": len(reqs), "weight_total": sum(w for _, w in reqs),
        "recorded_sliding60_max": maxwin(reqs),
        "venue_header_used_weight_1m_max": max((h.get("used_weight_1m") or 0) for h in hdr) if hdr else None,
        "fixed_replay": {"sliding60_max": maxwin(f_out), "n_delayed": len(f_del), "total_delay_s": round(sum(f_del), 2),
                         "max_delay_s": round(max(f_del), 2) if f_del else 0.0},
        "sliding_replay": {"sliding60_max": maxwin(s_out), "n_delayed": len(s_del), "total_delay_s": round(sum(s_del), 2),
                           "max_delay_s": round(max(s_del), 2) if s_del else 0.0,
                           "last_request_pushed_s": round(s_out[-1][0] - reqs[-1][0], 2) if reqs else 0.0,
                           "delayed_by_path": dict(s_where.most_common(8)),
                           "first_delay_at_s_after_first_request": (round(reqs[_first_delay][0] - t0, 1) if _first_delay is not None else None)}}
json.dump(res, open(OUT, "w"), indent=1)
for rid, a in res["anchors"].items():
    print(rid, "recorded", a["recorded_sliding60_max"], "venue", a["venue_header_used_weight_1m_max"], "| fixed", a["fixed_replay"],
          "| sliding", a["sliding_replay"])
