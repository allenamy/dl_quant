#!/usr/bin/python3
"""LED-05 write-back device for the 52 round-3 `reconstructed` order rows of the 2026-09-09 12Z crash anchor
(rebalance A1788956640, E-0909-D/G). Committed BEFORE any run. No venue call, no credentials: the rows were built on
09-10 02:35Z from allOrders + the backfilled fills (pilot_journal/e0909g_reconstructed_orders_12Z_DRYRUN.jsonl); this
device re-proves them OFFLINE against the ledger before appending them VERBATIM to <root>/pilot_log/20260909/orders.jsonl.
The older cc_tmp/e0909g_sim/reconstructed_orders_12Z.jsonl (order_type maker, doubled fees) is refused by C2/C4.

Checks, every mode (any failure ⇒ exit 2, nothing written):
  C1 the rows file's guarded sha256 equals --rows-sha; 52 lines; every row rebalance_id A1788956640, order_type
     `reconstructed`, terminal_reason filled, a venue_order_id, unique venue_order_id;
  C2 every row passes pilot_log.validate("orders") of --executor-tree;
  C3 the day file holds either NO row of A1788956640 (⇒ append) or EXACTLY these 52 lines verbatim (⇒ ALREADY
     APPLIED, 0 written); anything else ⇒ REFUSE;
  C4 against the day's fills collapsed through pilot_log.read_fills: per symbol, Σ|filled_notional| of the rows equals
     Σ|fill_notional| of the A1788956640 fills within 0.01 USDT and Σ fee_paid equals Σ commission (USDT) within 1e-8,
     and the two symbol sets are identical.
Apply: append the verbatim bytes with one write + fsync; re-read; every other ledger file of the day unchanged.
Rehearse: a temp root whose other days are SYMLINKS and whose 20260909 is a COPY; watchdog.evaluate before/after; apply
twice (second writes 0); the given root is never written.
Usage: led05_writeback_reconstructed.py --root R --rows F --rows-sha S --executor-tree T --receipt OUT [--apply|--rehearse]"""
import argparse, hashlib, json, os, shutil, stat, sys, tempfile, time
ap = argparse.ArgumentParser(allow_abbrev=False)
for k in ("--root", "--rows", "--rows-sha", "--executor-tree", "--receipt"): ap.add_argument(k, required=True)
ap.add_argument("--apply", action="store_true"); ap.add_argument("--rehearse", action="store_true")
a = ap.parse_args()
RID, DAY = "A1788956640", "20260909"
for d in ("live", "ops", "scheduler", "signal"): sys.path.insert(0, os.path.join(a.executor_tree, d))
os.environ.setdefault("LIVE_MODE", "DRY_RUN")
import pilot_log as PL
SF_DATALESS = getattr(stat, "SF_DATALESS", 0x40000000)
def gbytes(p):
    st = os.stat(p)
    if st.st_flags & SF_DATALESS: raise SystemExit(f"REFUSE {p}: dataless")
    b = open(p, "rb").read()
    if len(b) != st.st_size: raise SystemExit(f"REFUSE {p}: short read")
    return b
def day_shas(root):
    d = os.path.join(root, "pilot_log", DAY)
    return {f: hashlib.sha256(gbytes(os.path.join(d, f))).hexdigest() for f in sorted(os.listdir(d)) if f.endswith(".jsonl")}
blob = gbytes(a.rows); lines = [l for l in blob.splitlines(keepends=True) if l.strip()]
rows = [json.loads(l) for l in lines]
def checks(root):
    f = []
    if hashlib.sha256(blob).hexdigest() != a.rows_sha: f.append("C1 rows sha mismatch")
    if len(rows) != 52: f.append(f"C1 {len(rows)} rows, expected 52")
    if any(r.get("rebalance_id") != RID or r.get("order_type") != "reconstructed" or r.get("terminal_reason") != "filled"
           or r.get("venue_order_id") is None for r in rows): f.append("C1 row identity (rid/order_type/terminal/venue_order_id)")
    if len({r.get("venue_order_id") for r in rows}) != len(rows): f.append("C1 duplicate venue_order_id")
    for r in rows:
        try: PL.validate("orders", r)
        except Exception as e: f.append(f"C2 {r.get('symbol')}: {e}"); break
    day_orders = open(os.path.join(root, "pilot_log", DAY, "orders.jsonl"), "rb").read().splitlines(keepends=True)
    mine = [l for l in day_orders if l.strip() and json.loads(l).get("rebalance_id") == RID]
    state = "ABSENT" if not mine else ("PRESENT_VERBATIM" if mine == lines else "PRESENT_DIFFERENT")
    if state == "PRESENT_DIFFERENT": f.append(f"C3 day already holds {len(mine)} other row(s) of {RID}")
    _pl = os.path.join(root, "pilot_log")
    # the canonical reader when the executor tree has it (LED-01 3/3); on an older deployed tree, the same collapse
    # (collapse_supersedes over read_day) — identical on this ledger, which has 0 cross-symbol trade-id collisions
    _all = PL.read_fills(_pl, DAY) if hasattr(PL, "read_fills") else PL.collapse_supersedes(PL.read_day(_pl, DAY)["fills"])
    fills = [x for x in _all if x.get("rebalance_id") == RID]
    by_f, by_o = {}, {}
    for x in fills:
        s = by_f.setdefault(x["symbol"], [0.0, 0.0, set()])
        s[0] += abs(float(x["fill_notional"])); s[1] += float(x.get("commission") or 0.0); s[2].add(x.get("commission_asset"))
    for r in rows:
        s = by_o.setdefault(r["symbol"], [0.0, 0.0])
        s[0] += abs(float(r["filled_notional"])); s[1] += float(r["fee_paid"])
    if set(by_f) != set(by_o): f.append(f"C4 symbol sets differ: rows-only {sorted(set(by_o)-set(by_f))[:3]} fills-only {sorted(set(by_f)-set(by_o))[:3]}")
    for s in set(by_f) & set(by_o):
        if abs(by_f[s][0] - by_o[s][0]) > 0.01: f.append(f"C4 notional {s} rows {by_o[s][0]:.6f} fills {by_f[s][0]:.6f}")
        if by_f[s][2] != {"USDT"} or abs(by_f[s][1] - by_o[s][1]) > 1e-8: f.append(f"C4 fee {s} rows {by_o[s][1]:.10f} fills {by_f[s][1]:.10f} {by_f[s][2]}")
    return f, {"state": state, "n_fills_trades": len(fills), "n_symbols": len(by_o),
               "notional_rows": round(sum(v[0] for v in by_o.values()), 6), "fee_rows": round(sum(v[1] for v in by_o.values()), 10)}
def apply(root):
    fails, info = checks(root)
    if fails: return {"written": 0, "state": "REFUSED", "fails": fails[:5]}
    if info["state"] == "PRESENT_VERBATIM": return {"written": 0, "state": "ALREADY_APPLIED"}
    p = os.path.join(root, "pilot_log", DAY, "orders.jsonl")
    before = gbytes(p)
    if not before.endswith(b"\n"): return {"written": 0, "state": "REFUSED", "fails": ["orders.jsonl does not end with a newline"]}
    with open(p, "ab") as fh:
        fh.write(b"".join(lines)); fh.flush(); os.fsync(fh.fileno())
    after = gbytes(p)
    return {"written": len(lines), "state": "WRITTEN", "prefix_preserved": after[:len(before)] == before,
            "orders_sha256_before": hashlib.sha256(before).hexdigest(), "orders_sha256_after": hashlib.sha256(after).hexdigest()}
res = {"utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "root": a.root, "rows_sha256": a.rows_sha,
       "executor_tree": a.executor_tree, "pilot_log_py_sha256": hashlib.sha256(gbytes(os.path.join(a.executor_tree, "live", "pilot_log.py"))).hexdigest(),
       "mode": "rehearse" if a.rehearse else ("apply" if a.apply else "check")}
fails, info = checks(a.root); res.update(info); res["check_failures"] = fails
if fails:
    json.dump(res, open(a.receipt, "w"), indent=1); print("LED05 REFUSE", fails[:5]); sys.exit(2)
if a.rehearse:
    import watchdog as WD
    tmp = tempfile.mkdtemp(prefix="led05_rehearsal_"); pl = os.path.join(tmp, "pilot_log"); os.makedirs(pl)
    src_pl = os.path.join(os.path.abspath(a.root), "pilot_log")
    for d in os.listdir(src_pl):
        if d == DAY: shutil.copytree(os.path.join(src_pl, d), os.path.join(pl, d))
        else: os.symlink(os.path.join(src_pl, d), os.path.join(pl, d))
    def wd():
        ev = WD.evaluate(pl, venue_events=[], ops_stats=[])
        c = ev.get("conditions") or {}
        return {"tripped": ev.get("tripped"), "blind": ev.get("conditions_blind"),
                "conditions_sha256": hashlib.sha256(json.dumps(c, sort_keys=True, default=repr).encode()).hexdigest(),
                "conditions": c}
    given0 = day_shas(a.root)
    w0 = wd(); res["apply_1"] = apply(tmp); res["apply_2_idempotency"] = apply(tmp); w1 = wd()
    res["watchdog_before"] = {k: w0[k] for k in ("tripped", "blind", "conditions_sha256")}
    res["watchdog_after"] = {k: w1[k] for k in ("tripped", "blind", "conditions_sha256")}
    res["watchdog_conditions_changed"] = sorted(k for k in set(w0["conditions"]) | set(w1["conditions"])
                                                if json.dumps(w0["conditions"].get(k), sort_keys=True, default=repr) != json.dumps(w1["conditions"].get(k), sort_keys=True, default=repr))
    res["given_root_day_unchanged"] = day_shas(a.root) == given0
    res["verdict"] = ("PASS" if res["apply_1"].get("state") == "WRITTEN" and res["apply_1"].get("prefix_preserved")
                      and res["apply_2_idempotency"].get("written") == 0 and w1["tripped"] is False
                      and res["given_root_day_unchanged"] else "FAIL")
elif a.apply:
    d0 = day_shas(a.root); res["apply"] = apply(a.root); d1 = day_shas(a.root)
    res["other_day_files_unchanged"] = all(d0[k] == d1[k] for k in d0 if k != "orders.jsonl")
    res["verdict"] = "PASS" if res["apply"]["state"] in ("WRITTEN", "ALREADY_APPLIED") and res["other_day_files_unchanged"] else "FAIL"
else:
    res["verdict"] = "CHECKS_PASS"
json.dump(res, open(a.receipt, "w"), indent=1, default=str)
print("LED05", res["mode"], res["verdict"], {k: res.get(k) for k in ("state", "n_fills_trades", "n_symbols", "notional_rows", "fee_rows", "apply_1", "apply_2_idempotency", "watchdog_before", "watchdog_after", "watchdog_conditions_changed", "apply")})
sys.exit(0 if res["verdict"] in ("PASS", "CHECKS_PASS") else 1)
