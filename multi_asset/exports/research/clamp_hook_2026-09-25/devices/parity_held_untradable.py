#!/usr/bin/env python3
"""Live vs engine: the HELD-UNTRADABLE set that the clamp pins (lead 2026-09-25 ~15:4xZ, DECISION RULE step 1 rev 6 5756c1835: arm R paused,
parity investigation first). READ-ONLY, pooled, no venue.
Code that decides "untradable":
  live   ~/dl_quant_live/scheduler/anchor_loop.py L1864 (venue status gate), L1868 (sources record), L1873-L1883 (per_name_stop stop +
         cooldown via PNS.active_sets(PNS.load_state(), time.time())), L1893-L1898 (external meta), L1903-L1906 (external held exit),
         L2068-L2072 (external dust: EXT.below_min_notional(target, floors, min_notional_mult)); labels L509-L520.
  engine exec_sim.py (sha 29679672) Sim.on_anchor: untr = (symbols − c["tradable"]) ∪ (c["meta"] ∩ symbols) ∪ act["stop"] ∪ act["cooldown"]
         ∪ held_exit ∪ dust["names"], act = X.PNS.active_sets(self.pns, t_dec) with the SIMULATED stop state (per_name_stop.evaluate wide
         profile at N+45), then X.AL.apply_withhold_and_reshape(target, pos, untr, ...) — the same function as live.
Live side, per anchor (anchors rows 09-16 12Z →): the pinned set = reshape.clamped_after_reshape.names (exact, the executor's own record);
  per pinned name: held position (previous venue readback quantity × mid_at_anchor), the reshape target it had (L1, reconstructed exactly as
  layered_book.py, whose per-name identity holds on every anchor), the shift L2 − L1, and its SOURCE:
    external_held_exit — not in target_live/A (exact by definition);
    external_dust      — |producer target| < min_notional_mult × min_notional (book.json external.min_notional_mult, exchange_info_cache);
    per_name_stop / per_name_stop_cooldown — named in a held-withheld page (notify_audit, "逐名止损已停 / 逐名止损冷却期") within 90 min of the
                         anchor's decision (lists are truncated at 8 names per source: a name not found there is "unattributed");
    unattributed       — none of the above could be established from the ledger (reported, not guessed).
Engine side (hook v2 rows, path 0, the engine axis ends 2026-09-18T20Z): held_untradable {name: sources, pos_usdt} per anchor, book net / NAV.
Outputs per side: name-anchors by source, median |held position| (the dust size), persistence (anchors in a row), and the net shift by source.
usage: ~/wide_shadow/venv/bin/python parity_held_untradable.py <engine hook rows .jsonl.gz> <out dir> [--from 2026-09-16T12] [--to 2026-09-25T12]"""
import calendar, collections, glob, gzip, json, math, os, re, sys, time
import numpy as np

HOME = os.path.expanduser("~"); WS = f"{HOME}/wide_shadow"; DQ = f"{HOME}/dl_quant_live"; L = f"{DQ}/state/live/pilot_log"
bad = lambda k: "chase" in str(k).lower() or "arm" in str(k).lower()
fmt = lambda t: time.strftime("%m-%dT%HZ", time.gmtime(t))
LABELS = {"逐名止损已停": "per_name_stop", "逐名止损冷却期": "per_name_stop_cooldown", "外部书不再持有": "external_held_exit",
          "外部书目标低于": "external_dust", "场所 maxNotionalValue=0": "venue_zero_cap", "场所状态非 TRADING": "venue_not_trading", "外部书元数据排除": "external_meta"}


def num(v):
    try: x = float(v)
    except (TypeError, ValueError): return None
    return x if math.isfinite(x) else None


def runs(seq_by_anchor):
    """name -> list of run lengths (consecutive anchors present)"""
    out = collections.defaultdict(list); cur = {}
    for A in sorted(seq_by_anchor):
        names = seq_by_anchor[A]
        for n in list(cur):
            if n not in names: out[n].append(cur.pop(n))
        for n in names: cur[n] = cur.get(n, 0) + 1
    for n, k in cur.items(): out[n].append(k)
    return out


def summarise(rows):
    """rows: list of (A, name, source, held_usdt, shift_usdt)"""
    by = collections.defaultdict(list)
    for A, n, src, h, sh in rows: by[src].append((A, n, h, sh))
    seq = collections.defaultdict(set)
    for A, n, src, h, sh in rows: seq[A].add(n)
    rl = runs(seq)
    out = {}
    for src, v in sorted(by.items()):
        names = {n for _, n, _, _ in v}
        hs = [abs(h) for _, _, h, _ in v if h is not None]; shs = [s for *_, s in v if s is not None]
        out[src] = {"name_anchors": len(v), "distinct_names": len(names), "median_abs_held_usdt": float(np.median(hs)) if hs else None,
                    "p90_abs_held_usdt": float(np.percentile(hs, 90)) if hs else None, "median_run_anchors": float(np.median([x for n in names for x in rl[n]])) if names else None,
                    "max_run_anchors": max((x for n in names for x in rl[n]), default=None), "sum_shift_usdt": float(sum(shs)) if shs else None,
                    "examples": sorted(names)[:10]}
    return out


def main():
    hookf, out = sys.argv[1], sys.argv[2]; os.makedirs(out, exist_ok=True); a = sys.argv[3:]
    t_from = calendar.timegm(time.strptime(a[a.index("--from") + 1] if "--from" in a else "2026-09-16T12", "%Y-%m-%dT%H"))
    t_to = calendar.timegm(time.strptime(a[a.index("--to") + 1] if "--to" in a else "2026-09-25T12", "%Y-%m-%dT%H"))
    book = json.load(open(f"{DQ}/config/book.json")); mult = float(((book.get("external_book") or {}).get("min_notional_mult")) or 2.0)
    mn = {s: num(v.get("min_notional")) for s, v in json.load(open(f"{DQ}/state/exchange_info_cache.json")).items()}
    pages = []
    for l in open(f"{DQ}/state/notify_audit.jsonl"):
        try: d = json.loads(l)
        except ValueError: continue
        m = str(d.get("message", ""))
        if "withheld, reduce-only" not in m: continue
        srcs = {}
        for seg in m.split("by source:")[-1].split(";"):
            lab = next((v for k, v in LABELS.items() if k in seg), None)
            if lab: srcs[lab] = set(re.findall(r"'([A-Z0-9]+USDT)'", seg))
        pages.append((float(d.get("ts") or 0), srcs))
    days = sorted(os.path.basename(p) for p in glob.glob(f"{L}/2026*") if os.path.basename(p) >= time.strftime("%Y%m%d", time.gmtime(t_from - 86400)))
    AN = sorted(({k: v for k, v in json.loads(l).items() if not bad(k)} for d in days if os.path.exists(f"{L}/{d}/anchors.jsonl") for l in open(f"{L}/{d}/anchors.jsonl") if l.strip()),
                key=lambda r: float(r["anchor_ts"]))
    RB = [json.loads(l) for d in days if os.path.exists(f"{L}/{d}/position_readback.jsonl") for l in open(f"{L}/{d}/position_readback.jsonl") if l.strip()]
    rb = collections.defaultdict(dict)
    for p in RB: rb[float(p["anchor_ts"])][p["symbol"]] = num(p.get("venue_position_qty"))
    rbt = sorted(rb)
    live_rows = []; live_net = []; unattributed = collections.Counter()
    for an in AN:
        at = float(an["anchor_ts"]); A = int(at // 14400 * 14400)
        if not (t_from <= A <= t_to): continue
        rs = {k: v for k, v in (an.get("reshape") or {}).items() if not bad(k)}; ca = rs.get("clamped_after_reshape") or {}
        tl = f"{WS}/state/target_live/{A}.json"
        if not rs or not os.path.exists(tl): continue
        G = float(rs["sizing_gross"]); W = json.load(open(tl))["weights"]; sw = sum(abs(v) for v in W.values())
        L0 = {s: v / sw * G for s, v in W.items()}
        removed = set(rs["removed_names"]) if "removed_names" in rs else set(rs.get("popped_names") or []) | set(rs.get("forced_flat_names") or [])
        keep = [s for s in L0 if s not in removed]; v = np.array([L0[s] / G for s in keep]); v = v - v.mean(); v = v / np.abs(v).sum()
        L1 = dict(zip(keep, (v * G).tolist()))
        mids = an.get("mid_at_anchor_vector"); mids = json.loads(mids) if isinstance(mids, str) else (mids or {})
        prev = [t for t in rbt if t < at]; held = rb[prev[-1]] if prev else {}
        pg = [p for p in pages if at - 600 <= p[0] <= at + 5400]
        pg_src = collections.defaultdict(set)
        for _, s_ in pg:
            for k, names in s_.items(): pg_src[k] |= names
        nav = G / 2.0; live_net.append((A, float(ca.get("book_net_usdt") or 0.0) / nav))
        tg = num(an.get("target_gross"))
        for n in ca.get("names") or []:
            q = held.get(n); m = num(mids.get(n)); h = (q * m) if (q is not None and m is not None) else None
            if n not in W: src = "external_held_exit"
            elif mn.get(n) and abs(L0.get(n, 0.0)) < mult * mn[n]: src = "external_dust"
            else:
                src = next((k for k in ("per_name_stop", "per_name_stop_cooldown", "venue_zero_cap", "venue_not_trading", "external_meta") if n in pg_src.get(k, ())), "unattributed")
                if src == "unattributed": unattributed[n] += 1
            live_rows.append((A, n, src, h, (h - L1.get(n, 0.0)) if h is not None else None))
    eng_rows = []; eng_net = []
    for l in gzip.open(hookf, "rt"):
        r = json.loads(l)
        if not r.get("A") or not (t_from <= r["A"] <= t_to): continue
        eng_net.append((r["A"], (r.get("book_net_usdt") or 0.0) / (r["sizing_gross"] / 2.0)))
        for n, e in (r.get("held_untradable") or {}).items():
            if n.startswith("_"): continue
            srcs = e.get("sources") or ["none"]
            src = next((k for k in ("per_name_stop", "per_name_stop_cooldown", "held_exit", "dust", "not_tradable", "meta") if k in srcs), srcs[0])
            eng_rows.append((r["A"], n, {"held_exit": "external_held_exit", "dust": "external_dust", "not_tradable": "venue_not_trading", "meta": "external_meta"}.get(src, src),
                             e.get("pos_usdt"), None))
    overlap = sorted({A for A, *_ in eng_rows} | {A for A, _ in eng_net})
    live_ov = [x for x in live_rows if x[0] in set(overlap)]
    rec = {"window": [fmt(t_from), fmt(t_to)], "engine_axis_last": fmt(max((A for A, _ in eng_net), default=0)), "overlap_anchors": [fmt(A) for A in overlap],
           "live_all": summarise(live_rows), "live_overlap": summarise(live_ov), "engine_overlap": summarise(eng_rows),
           "live_net_over_nav_pct": {fmt(A): round(x * 100, 3) for A, x in live_net}, "engine_net_over_nav_pct": {fmt(A): round(x * 100, 3) for A, x in eng_net},
           "live_unattributed_names": dict(unattributed), "min_notional_mult": mult}
    json.dump(rec, open(f"{out}/PARITY_HELD_UNTRADABLE.json", "w"), indent=1, default=str)
    for side in ("live_all", "live_overlap", "engine_overlap"):
        print(f"== {side}")
        for k, v in rec[side].items():
            print(f"   {k:24s} name-anchors {v['name_anchors']:4d} names {v['distinct_names']:3d} median|held| {v['median_abs_held_usdt'] if v['median_abs_held_usdt'] is None else round(v['median_abs_held_usdt'], 1)} "
                  f"p90 {v['p90_abs_held_usdt'] if v['p90_abs_held_usdt'] is None else round(v['p90_abs_held_usdt'])} run median {v['median_run_anchors']} max {v['max_run_anchors']} "
                  f"shift {v['sum_shift_usdt'] if v['sum_shift_usdt'] is None else round(v['sum_shift_usdt'])} e.g. {v['examples'][:6]}")
    print("overlap anchors:", rec["overlap_anchors"]); print("live unattributed:", rec["live_unattributed_names"])
    print("live net/NAV % (overlap):", {k: v for k, v in rec["live_net_over_nav_pct"].items() if k in rec["overlap_anchors"]})
    print("engine net/NAV % (overlap):", rec["engine_net_over_nav_pct"])


if __name__ == "__main__":
    main()
