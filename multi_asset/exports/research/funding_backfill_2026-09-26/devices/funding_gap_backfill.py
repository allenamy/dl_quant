#!/usr/bin/env python3
"""funding_gap_backfill.py -- backfill the executor's M6 funding rows that the 2026-09-26 12Z/16Z outage left unpriceable
(lead task 2026-09-26: 545 settlements, write_funding_rows skipped them because the newest position readback before them was
older than one anchor interval). Criteria: CRITERIA.md next to this file, committed before any run.

ROW CONSTRUCTION IS THE EXECUTOR'S OWN, NOT A COPY. The rows are produced by calling ~/dl_quant_live/live/binance_funding.py
`write_funding_rows` itself, with three in-process substitutions and nothing else:
  * FundingLedger.fetch_income / fetch_rates and venue_funding_intervals return the RECORDED venue answers (from `fetch`, the only
    step that touches the exchange, read-only, run by the lead inside a quiet window);
  * `log` is a capture object, so the rows it would have written are returned instead of written (the plan);
  * state_path points into the plan directory, so the executor's own funding_last_pull.json is never touched;
  * max_age_s = the measured readback gap, so positions_at accepts the pre-gap readback -- which is exactly what the census proves
    is legitimate (quantities unchanged, zero fills between the two readbacks). Nothing else of the pricing rule changes.
Rows are then appended with the executor's own PilotLogger(root, day).funding (schema-validated at write time). Append-only;
idempotent by (symbol, settlement ms); every step records shas.

subcommands
  census   --root R --day D --out J                        offline: gap window + per-name position proof (no network)
  fetch    --root R --census J --out RAW                   NETWORK (read-only GETs, lead runs it in a quiet window)
  plan     --root R --census J --raw RAW --out DIR         offline: rows via write_funding_rows; exclusions named
  apply    --root R --plan DIR --plan-sha S --stamp T      appends; refuses if the target changed since the plan
  verify   --root R --apply-receipt F                      prefix untouched, tail == what apply wrote, each key exactly once
  rollback --root R --apply-receipt F                      truncates back to the pre-apply bytes (refuses if anything was appended after)
"""
import argparse, collections, contextlib, hashlib, json, os, shutil, sys, time

EXEC = os.path.expanduser(os.environ.get("EXEC_ROOT", "~/dl_quant_live"))
sys.path.insert(0, os.path.join(EXEC, "live"))
import binance_funding as BF          # noqa: E402  (the executor's module, imported, never copied)
import pilot_log as PL                 # noqa: E402

ANCHOR_S = 4 * 3600


def sha_bytes(b): return hashlib.sha256(b).hexdigest()
def sha(p): return sha_bytes(open(p, "rb").read())
def utc(t): return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(float(t)))


def stop(msg):
    print("BACKFILL STOP:", msg, flush=True); sys.exit(3)


def write_json(p, obj):
    body = json.dumps(obj, indent=1, sort_keys=True, default=str).encode()
    with open(p + ".tmp", "wb") as f:
        f.write(body); f.flush(); os.fsync(f.fileno())
    if open(p + ".tmp", "rb").read() != body: stop(f"read-back differs: {p}")
    os.replace(p + ".tmp", p)
    return sha_bytes(body)


def day_rows(root, day, table):
    return PL.read_day(root, day).get(table, [])


# ---------------------------------------------------------------------------------------------------------------- census
def census(root, day, exinfo):
    """The gap = the one pair of consecutive readbacks further apart than one anchor interval. Position proof per name:
    qty(pre-gap readback) == qty(post-gap readback) - net qty of the fills between the two readbacks, and every such fill
    must belong to the post-gap anchor's rebalance (after it started). A name failing either is EXCLUDED, by name."""
    rb = day_rows(root, day, "position_readback")
    times = sorted({float(r["read_ts"]) for r in rb})
    gaps = [(a, b) for a, b in zip(times, times[1:]) if b - a > ANCHOR_S + 1800]
    if len(gaps) != 1: stop(f"expected exactly one readback gap > 4.5 h on {day}, found {[(utc(a), utc(b)) for a, b in gaps]}")
    A, B = gaps[0]
    snapA = {r["symbol"]: r for r in rb if abs(float(r["read_ts"]) - A) < 1e-6}
    snapB = {r["symbol"]: r for r in rb if abs(float(r["read_ts"]) - B) < 1e-6}
    fills = [f for f in day_rows(root, day, "fills") if f.get("fill_ts") is not None and A < float(f["fill_ts"]) < B]
    reb = collections.Counter(f["rebalance_id"] for f in fills)
    post_rid = None
    if reb:
        # the post-gap anchor's rebalance: the one whose fills end last; any fill from another rebalance inside the gap is a change
        post_rid = max(reb, key=lambda r: max(float(f["fill_ts"]) for f in fills if f["rebalance_id"] == r))
    t_post_start = min((float(f["fill_ts"]) for f in fills if f["rebalance_id"] == post_rid), default=B)
    stray = [f for f in fills if f["rebalance_id"] != post_rid]
    net = collections.defaultdict(float)
    for f in fills:
        if f["rebalance_id"] != post_rid: continue
        q = float(f["fill_notional"]) / float(f["fill_px"])
        net[f["symbol"]] += q if str(f["side"]).upper() == "BUY" else -q
    names = sorted(set(snapA) | set(snapB) | set(net))
    per, excluded = {}, {}
    stray_syms = collections.Counter(f["symbol"] for f in stray)
    for s in names:
        qa = float(snapA[s]["venue_position_qty"]) if s in snapA else 0.0
        qb = float(snapB[s]["venue_position_qty"]) if s in snapB else 0.0
        pre = qb - net.get(s, 0.0)
        step = (exinfo.get(s) or {}).get("step")
        tol = 0.5 * float(step) if step else None
        why = None
        if s in stray_syms: why = f"{stray_syms[s]} fill(s) inside the gap outside the post-gap rebalance"
        elif tol is None: why = "no stepSize in exchange_info_cache: equality cannot be judged"
        elif abs(pre - qa) > tol: why = f"qty changed across the gap: pre-gap {qa} vs post-gap reconstructed {pre} (tol {tol})"
        per[s] = {"qty_pre_gap": qa, "qty_post_gap_readback": qb, "net_qty_post_gap_rebalance": net.get(s, 0.0),
                  "qty_post_gap_reconstructed_pretrade": pre, "tol": tol, "EQUAL": why is None}
        if why: excluded[s] = why
    return {"day": day, "readback_before_gap": {"read_ts": A, "utc": utc(A), "n": len(snapA)},
            "readback_after_gap": {"read_ts": B, "utc": utc(B), "n": len(snapB)},
            "fills_between_readbacks": len(fills), "post_gap_rebalance": post_rid,
            "post_gap_rebalance_first_fill_utc": utc(t_post_start) if fills else None,
            "fills_outside_post_gap_rebalance": len(stray),
            # settlements in [A + one interval, first post-gap fill) were unpriceable AND are covered by the pre-gap book
            "gap_window_ms": [int((A + ANCHOR_S) * 1000) + 1, int(t_post_start * 1000)],
            "max_age_s_needed": t_post_start - A, "names": per, "excluded": excluded,
            "n_names": len(names), "n_equal": sum(1 for v in per.values() if v["EQUAL"])}


# ---------------------------------------------------------------------------------------------------------------- fetch
def fetch(root, cen, out):
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "common"))
    import venue_quiet_window as QW                      # the canonical guard; it raises unless the window is open
    QW.require_quiet_window(min_remaining_min=20)
    import binance_broker as BB
    b = BB.BinanceBroker(mode="LIVE")
    lg = BF.FundingLedger(b)
    s0, s1 = cen["gap_window_ms"]
    income = [i for i in lg.fetch_income(s0, s1) if str(i.get("incomeType", "FUNDING_FEE")) == "FUNDING_FEE"]
    syms = sorted({str(i["symbol"]) for i in income})
    t_min = min((int(i["time"]) for i in income), default=s0)
    rates = {s: (lg.fetch_rates(s, t_min - 3600_000, s1) or []) for s in syms}
    intervals = BF.venue_funding_intervals(b)
    rec = {"fetched_utc": utc(time.time()), "window_ms": [s0, s1], "income": income, "rates": rates, "intervals": intervals,
           "note": "recorded venue answers; income is FUNDING_FEE rows in the window, rates from the public endpoint"}
    return rec


# ---------------------------------------------------------------------------------------------------------------- plan
class _Capture:
    def __init__(self): self.rows = []
    def funding(self, **r): self.rows.append(dict(r))


@contextlib.contextmanager
def _replay(raw):
    """Substitute the three venue calls with the recorded answers; restore them whatever happens."""
    saved = (BF.FundingLedger.fetch_income, BF.FundingLedger.fetch_rates, BF.venue_funding_intervals)
    s0, s1 = raw["window_ms"]
    BF.FundingLedger.fetch_income = lambda self, start_ms, end_ms=None: [i for i in raw["income"] if start_ms <= int(i["time"]) <= (end_ms or s1)]
    BF.FundingLedger.fetch_rates = lambda self, symbol, start_ms, end_ms=None: raw["rates"].get(symbol, [])
    BF.venue_funding_intervals = lambda broker: dict(raw["intervals"])
    try:
        yield
    finally:
        BF.FundingLedger.fetch_income, BF.FundingLedger.fetch_rates, BF.venue_funding_intervals = saved


class _NoBroker:
    mode = "REPLAY"          # not DRY_RUN (which would return [] before the substituted fetch); never used for a request


def plan(root, cen, raw, outdir, day):
    os.makedirs(outdir, exist_ok=True)
    s0, s1 = cen["gap_window_ms"]
    excl = set(cen["excluded"])
    inc_all = [i for i in raw["income"] if s0 <= int(i["time"]) <= s1]
    existing = {(r["symbol"], int(round(float(r["settlement_ts"]) * 1000))) for r in day_rows(root, day, "funding")}
    keep = [i for i in inc_all if i["symbol"] not in excl and (i["symbol"], int(i["time"])) not in existing]
    dropped_excl = sorted({i["symbol"] for i in inc_all if i["symbol"] in excl})
    n_present = sum(1 for i in inc_all if (i["symbol"], int(i["time"])) in existing)
    raw2 = dict(raw, income=keep)
    cap, alarms = _Capture(), []
    with _replay(raw2):
        out = BF.write_funding_rows(_NoBroker(), cap, root, now_ms=s1 + 1, max_age_s=float(cen["max_age_s_needed"]) + 1.0,
                                    alarm=lambda sev, msg: alarms.append([sev, msg[:300]]), since_ms=s0,
                                    state_path=os.path.join(outdir, "funding_last_pull.REPLAY.json"))
    # the rows must have EXACTLY the key set the executor wrote on this day (derived from the file, not typed here)
    ref_keys = collections.Counter(tuple(sorted(r.keys())) for r in day_rows(root, day, "funding"))
    ref = ref_keys.most_common(1)[0][0] if ref_keys else None
    bad_schema = [r for r in cap.rows if tuple(sorted(r.keys())) != ref]
    for r in cap.rows: PL.validate("funding", r)
    if bad_schema: stop(f"{len(bad_schema)} planned row(s) have a key set != the executor's rows on {day}: {sorted(bad_schema[0].keys())} vs {ref}")
    if out["skipped_no_position"]: stop(f"{out['skipped_no_position']} settlement(s) still unpriceable after the census: {out['skipped_symbols'][:8]}")
    target = os.path.join(root, day, "funding.jsonl")
    rec = {"day": day, "target": target, "target_size_at_plan": os.path.getsize(target), "target_sha_at_plan": sha(target),
           "census_window_ms": [s0, s1], "n_income_in_window": len(inc_all), "n_already_present_skipped": n_present,
           "n_excluded_rows": sum(1 for i in inc_all if i["symbol"] in excl), "excluded_symbols": dropped_excl,
           "excluded_reasons": {s: cen["excluded"][s] for s in dropped_excl},
           "n_rows_planned": len(cap.rows), "writer_report": {k: v for k, v in out.items() if k not in ("freshness",)},
           "alarms_during_replay": alarms, "reference_key_set": list(ref) if ref else None,
           "executor_module_sha256": {"binance_funding.py": sha(BF.__file__), "pilot_log.py": sha(PL.__file__)},
           "rows": cap.rows}
    rec["plan_sha256"] = write_json(os.path.join(outdir, "PLAN.json"), rec)
    return rec


# ---------------------------------------------------------------------------------------------------------------- apply / verify / rollback
def apply(root, plan_dir, plan_sha, stamp):
    pp = os.path.join(plan_dir, "PLAN.json")
    if sha(pp) != plan_sha: stop("PLAN.json is not the pinned plan")
    P = json.load(open(pp)); day, target = P["day"], P["target"]
    if os.path.getsize(target) != P["target_size_at_plan"] or sha(target) != P["target_sha_at_plan"]:
        stop("the target funding.jsonl changed since the plan -- re-plan (idempotency is decided at plan time)")
    existing = {(r["symbol"], int(round(float(r["settlement_ts"]) * 1000))) for r in day_rows(root, day, "funding")}
    rows = [r for r in P["rows"] if (r["symbol"], int(round(float(r["settlement_ts"]) * 1000))) not in existing]
    for r in rows: PL.validate("funding", r)
    pre_size, pre_sha = os.path.getsize(target), sha(target)
    bak = f"{target}.pre_gap_backfill_{stamp}"
    if os.path.exists(bak): stop(f"backup {bak} exists")
    shutil.copy2(target, bak)
    if sha(bak) != pre_sha: stop("backup copy differs")
    lg = PL.PilotLogger(root, day=day)
    for r in rows: lg.funding(**r)
    for fh in lg._fh.values(): fh.flush(); os.fsync(fh.fileno())
    post = open(target, "rb").read()
    tail = post[pre_size:]
    rec = {"stamp": stamp, "plan": [pp, plan_sha], "target": target, "backup": bak, "pre_size": pre_size, "pre_sha256": pre_sha,
           "post_size": len(post), "appended_rows": len(rows), "appended_bytes_sha256": sha_bytes(tail),
           "prefix_unchanged": sha_bytes(post[:pre_size]) == pre_sha,
           "keys": [[r["symbol"], int(round(float(r["settlement_ts"]) * 1000))] for r in rows], "utc": utc(time.time())}
    rp = os.path.join(plan_dir, f"APPLY_{stamp}.json"); rec["receipt_sha256"] = write_json(rp, rec)
    return rec, rp


def verify(root, receipt):
    R = json.load(open(receipt)); data = open(R["target"], "rb").read()
    rows = [json.loads(l) for l in data.decode().splitlines() if l.strip()]
    cnt = collections.Counter((r["symbol"], int(round(float(r["settlement_ts"]) * 1000))) for r in rows)
    res = {"prefix_unchanged": sha_bytes(data[:R["pre_size"]]) == R["pre_sha256"],
           "tail_is_what_apply_wrote": sha_bytes(data[R["pre_size"]:R["post_size"]]) == R["appended_bytes_sha256"],
           "each_applied_key_exactly_once": all(cnt[tuple(k)] == 1 for k in R["keys"]),
           "bytes_after_apply": len(data) - R["post_size"]}
    res["VERDICT"] = "VERIFIED" if all(v is True for k, v in res.items() if k != "bytes_after_apply") else "RED"
    return res


def rollback(root, receipt):
    R = json.load(open(receipt)); target = R["target"]; data = open(target, "rb").read()
    if len(data) != R["post_size"]: stop(f"{len(data) - R['post_size']} byte(s) were appended after the backfill: truncation would remove them -- manual")
    if sha_bytes(data[R["pre_size"]:]) != R["appended_bytes_sha256"]: stop("the tail is not what apply wrote")
    with open(target, "r+b") as f:
        f.truncate(R["pre_size"]); f.flush(); os.fsync(f.fileno())
    ok = sha(target) == R["pre_sha256"] == sha(R["backup"])
    return {"rolled_back": ok, "size": os.path.getsize(target)}


def main():
    ap = argparse.ArgumentParser(); sp = ap.add_subparsers(dest="cmd", required=True)
    c = sp.add_parser("census"); c.add_argument("--root", required=True); c.add_argument("--day", required=True); c.add_argument("--out", required=True)
    f = sp.add_parser("fetch"); f.add_argument("--root", required=True); f.add_argument("--census", required=True); f.add_argument("--out", required=True)
    p = sp.add_parser("plan"); [p.add_argument(x, required=True) for x in ("--root", "--census", "--raw", "--out")]
    a = sp.add_parser("apply"); [a.add_argument(x, required=True) for x in ("--root", "--plan", "--plan-sha", "--stamp")]
    v = sp.add_parser("verify"); [v.add_argument(x, required=True) for x in ("--root", "--apply-receipt")]
    r = sp.add_parser("rollback"); [r.add_argument(x, required=True) for x in ("--root", "--apply-receipt")]
    x = ap.parse_args()
    base = {"device_sha256": sha(os.path.abspath(__file__)), "exec_root": EXEC}
    if x.cmd == "census":
        ex = json.load(open(os.path.join(os.path.dirname(os.path.abspath(x.root)), "exchange_info_cache.json")))
        rec = dict(base, **census(x.root, x.day, ex)); s = write_json(x.out, rec)
        print(f"CENSUS gap {rec['readback_before_gap']['utc']} -> {rec['readback_after_gap']['utc']} window_ms {rec['gap_window_ms']} "
              f"fills {rec['fills_between_readbacks']} (outside post-gap rebalance {rec['fills_outside_post_gap_rebalance']}) "
              f"names {rec['n_names']} equal {rec['n_equal']} excluded {len(rec['excluded'])} sha {s[:16]}")
    elif x.cmd == "fetch":
        rec = dict(base, **fetch(x.root, json.load(open(x.census)), x.out)); s = write_json(x.out, rec)
        print(f"FETCH income {len(rec['income'])} symbols {len(rec['rates'])} intervals {len(rec['intervals'])} sha {s[:16]}")
    elif x.cmd == "plan":
        cen = json.load(open(x.census)); raw = json.load(open(x.raw))
        rec = plan(x.root, cen, raw, x.out, cen["day"])
        print(f"PLAN rows {rec['n_rows_planned']} in_window {rec['n_income_in_window']} present {rec['n_already_present_skipped']} "
              f"excluded_rows {rec['n_excluded_rows']} ({rec['excluded_symbols'][:6]}) sha {rec['plan_sha256']}")
    elif x.cmd == "apply":
        rec, rp = apply(x.root, x.plan, x.plan_sha, x.stamp)
        print(f"APPLY rows {rec['appended_rows']} prefix_unchanged {rec['prefix_unchanged']} receipt {rp} sha {rec['receipt_sha256'][:16]}")
    elif x.cmd == "verify":
        res = verify(x.root, x.apply_receipt); print("VERIFY", json.dumps(res))
        sys.exit(0 if res["VERDICT"] == "VERIFIED" else 1)
    elif x.cmd == "rollback":
        res = rollback(x.root, x.apply_receipt); print("ROLLBACK", json.dumps(res)); sys.exit(0 if res["rolled_back"] else 1)


if __name__ == "__main__":
    main()
