#!/usr/bin/env python3
"""Read-only recovery checks, derived from research commit 3b4a2815a.
2026-09-27: bind order and client identities to symbol, reject lossy IDs.
Run by the lead only after the external quiet-window guard permits the call.
No claim of global single-writer exclusivity: only commission-listed symbols,
filled orders, and [rid-minus-600s, call time] are covered.

  q1q4    --t-off <ISO Z> --out <json>
          Q1 GET /fapi/v1/openOrders (all symbols)            PASS iff []
          Q2 GET /fapi/v3/account                              PASS iff no position has positionAmt != 0
          Q3 GET /fapi/v1/income incomeType=COMMISSION   [t_off, now]  PASS iff 0 rows (paged to the end)
          Q4 GET /fapi/v1/income incomeType=REALIZED_PNL [t_off, now]  PASS iff 0 rows (paged to the end)
          last line: VENUE_Q1_Q4 PASS | FAIL [names] | UNKNOWN [why]     exit 0 | 1 | 2
  anchor  --anchor <A epoch, e.g. 1790510400> --out <json>
          after the first resumed anchor (run after N+30): every venue trade in [rid - 600 s, now] on every symbol that has a
          COMMISSION row in that window must belong to an orderId in the LOCAL ledger (orders.jsonl request_ledger[].order_id,
          any rebalance_id; client ids only for rows that record no order id, e.g. the flatten ladder); reports foreign orderIds (must be 0), fill-to-target ratio from the anchors row, and the taker
          share pooled (venue side from userTrades.maker, ledger side from fills.venue_maker_flag via pilot_log.read_fills).
          last line: VENUE_ANCHOR PASS | FAIL [names] | UNKNOWN [why]     exit 0 | 1 | 2
          PASS = foreign orderIds 0 AND fill ratio >= 0.60 AND no blocked_by_halt row at this anchor (plan §5 step 8).

★ READ-ONLY BY CONSTRUCTION: `_get` is the only function that talks to the venue; it refuses any path outside GET_ALLOWED and
  has no method argument. Nothing here can place, amend or cancel an order.
★ CREDENTIALS: loaded lazily, only inside `_get`, through the executor's own loader (live/envfile.load of ~/dl_quant_live/.env);
  never printed — only sha256(key)[:10] is printed so the operator can confirm it is the NEW key.
★ UNKNOWN IS NOT PASS: any HTTP / JSON / venue error, a page cap hit, or a saturated userTrades window => UNKNOWN, exit 2.
★ BLIND STATE: pooled numbers only (no arm split); per-name lists are position names, not execution-arm data.
★ KNOWN BLIND SPOT (named 2026-09-27 13:0xZ, first live run): /fapi/v3/account lists ONLY symbols that hold a position or an open
  order, so Q2 reads `positions: []` (n_listed 0) as flat — correct for v3, but Q2 alone cannot tell "flat" from "the endpoint returned
  nothing". The same endpoint listed 314 held positions at 05:00Z, and Q3/Q4 (no trades since t_off) cover the same fact independently."""
import argparse, collections, datetime, hashlib, hmac, json, os, re, sys, time, urllib.parse, urllib.request

BASE = "https://fapi.binance.com"
LIVE_REPO = os.path.expanduser("~/dl_quant_live")
GET_ALLOWED = {"/fapi/v1/openOrders", "/fapi/v3/account", "/fapi/v1/income", "/fapi/v1/userTrades", "/fapi/v1/allOrders"}
PAGE_CAP = 100
_cred = {}
TRANSPORT = None          # tests inject a callable(path, params) -> parsed JSON; None = the real venue


class Unknown(Exception):
    pass


def order_key(symbol, oid):
    """Lossless exchange identity; bool/float must never be coerced to an ID."""
    if not isinstance(symbol, str) or not symbol or symbol != symbol.strip():
        raise Unknown("missing or invalid order symbol")
    if type(oid) is int:
        val = oid
    elif isinstance(oid, str) and re.fullmatch(r"[0-9]+", oid):
        val = int(oid)
    else:
        raise Unknown("orderId must be an integer or decimal string (no float/bool coercion)")
    if val <= 0:
        raise Unknown("orderId must be positive")
    return symbol, val


def client_key(symbol, cid):
    if not isinstance(symbol, str) or not symbol or symbol != symbol.strip() or not isinstance(cid, str) or not cid:
        raise Unknown("missing or invalid client-order identity")
    return symbol, cid


def _credentials():
    if not _cred:
        sys.path.insert(0, os.path.join(LIVE_REPO, "live"))
        import envfile                                        # the executor's own .env loader (launchd-safe)
        envfile.load()
        k, s = os.environ.get("BINANCE_KEY"), os.environ.get("BINANCE_SECRET")
        if not k or not s:
            raise Unknown("no BINANCE_KEY / BINANCE_SECRET after envfile.load()")
        _cred.update(key=k, secret=s)
        print(f"KEY fingerprint sha256[:10] = {hashlib.sha256(k.encode()).hexdigest()[:10]} (loaded key)")
    return _cred


def _get(path, params=None, signed=True):
    if path not in GET_ALLOWED:
        raise RuntimeError(f"REFUSED: {path} is not a read-only endpoint on this device's list")
    params = dict(params or {})
    if TRANSPORT is not None:
        return TRANSPORT(path, params)
    time.sleep(0.25)                                          # gentle pacing; weights: account 5, income 30, userTrades 5, openOrders 40
    hdr = {}
    if signed:
        c = _credentials()
        params["timestamp"] = int(time.time() * 1000); params["recvWindow"] = 5000
        qs = urllib.parse.urlencode(params)
        qs += "&signature=" + hmac.new(c["secret"].encode(), qs.encode(), hashlib.sha256).hexdigest()
        hdr["X-MBX-APIKEY"] = c["key"]
    else:
        qs = urllib.parse.urlencode(params)
    req = urllib.request.Request(f"{BASE}{path}?{qs}", method="GET", headers=hdr)
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        raise Unknown(f"{path} HTTP {e.code}") from None
    except Exception as e:                                     # noqa: BLE001 — any failure to look is UNKNOWN, never a pass
        raise Unknown(f"{path} {type(e).__name__}") from None


def income_all(kind, start_ms, end_ms):
    """Every income row of `kind` in [start_ms, end_ms]. Cursor = max(time) of a full page, boundary rows removed by full-row
    identity (the FP3 fetch_income_paged rule, simplified: the expected answer here is 0 rows, so the count is what matters)."""
    rows, cur, pages = [], int(start_ms), 0
    while True:
        pages += 1
        if pages > PAGE_CAP:
            raise Unknown(f"income {kind}: page cap {PAGE_CAP} hit")
        page = _get("/fapi/v1/income", {"incomeType": kind, "startTime": cur, "endTime": int(end_ms), "limit": 1000})
        if not isinstance(page, list):
            raise Unknown(f"income {kind}: not a list: {str(page)[:120]}")
        # boundary multiset subtraction (FP3 R15-I1 / E-0909-H): remove only the re-requested rows of millisecond `cur`
        # that the previous page already returned; genuinely identical rows the venue emitted twice are kept
        if pages > 1:
            prev = collections.Counter(json.dumps(r, sort_keys=True) for r in rows if int(r["time"]) == cur)
            keep = []
            for r in page:
                k = json.dumps(r, sort_keys=True)
                if int(r["time"]) == cur and prev[k] > 0:
                    prev[k] -= 1
                else:
                    keep.append(r)
            page_new = keep
        else:
            page_new = page
        rows += page_new
        if len(page) < 1000:
            return rows
        nxt = max(int(r["time"]) for r in page)
        if nxt == cur:
            raise Unknown(f"income {kind}: 1000+ rows in one millisecond {cur}")
        cur = nxt


def parse_z(s):
    t = datetime.datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc).timestamp()
    return int(t * 1000)


def q1q4(t_off_iso, now_ms=None):
    t_off = parse_z(t_off_iso)
    now_ms = int(now_ms if now_ms is not None else time.time() * 1000)
    if t_off >= now_ms:
        raise Unknown(f"t_off {t_off_iso} is not in the past")
    rec, bad = {"t_off": t_off_iso, "t_off_ms": t_off, "now_ms": now_ms}, []
    oo = _get("/fapi/v1/openOrders")
    if not isinstance(oo, list):
        raise Unknown(f"openOrders not a list: {str(oo)[:120]}")
    rec["Q1_open_orders"] = {"n": len(oo), "client_order_ids": [o.get("clientOrderId") for o in oo][:50]}
    if oo: bad.append("Q1_open_orders")
    acct = _get("/fapi/v3/account")
    if not isinstance(acct, dict) or "positions" not in acct:
        raise Unknown(f"account has no positions: {str(acct)[:120]}")
    held = [{"symbol": p.get("symbol"), "positionAmt": p.get("positionAmt"), "notional": p.get("notional")}
            for p in acct["positions"] if float(p.get("positionAmt") or 0) != 0.0]
    rec["Q2_positions"] = {"n_listed": len(acct["positions"]), "n_nonzero": len(held), "nonzero": held[:50],
                           "sum_abs_notional": round(sum(abs(float(h.get("notional") or 0)) for h in held), 2)}
    if held: bad.append("Q2_positions")
    for q, kind in (("Q3", "COMMISSION"), ("Q4", "REALIZED_PNL")):
        rows = income_all(kind, t_off, now_ms)
        rec[f"{q}_{kind}"] = {"n": len(rows), "symbols": sorted({r.get("symbol") for r in rows})[:50],
                              "first_time_ms": min([int(r["time"]) for r in rows], default=None)}
        if rows: bad.append(f"{q}_{kind}")
    rec["VERDICT"] = "PASS" if not bad else "FAIL"; rec["bad"] = bad
    return rec


def local_ledger(A):
    """Local order ids (every rebalance_id, the anchor's day and the day before), the anchors row whose rid time is in
    [A, A + 4h), that anchor's blocked_by_halt count, and the pooled ledger taker share of that anchor's fills."""
    sys.path.insert(0, os.path.join(LIVE_REPO, "live"))
    import pilot_log as PL
    root = os.path.join(LIVE_REPO, "state", "live", "pilot_log")
    days = [time.strftime("%Y%m%d", time.gmtime(A - 86400)), time.strftime("%Y%m%d", time.gmtime(A))]
    oids, cids_no_oid, rows, anchors, fills = set(), set(), [], [], []
    for d in days:
        D = PL.read_day(root, d)
        for o in D["orders"]:
            got = [order_key(o.get("symbol"), q["order_id"]) for q in (o.get("request_ledger") or []) if q.get("order_id") is not None]
            oids.update(got)
            if not got and o.get("client_id") and o.get("submit_ts") is not None:
                cids_no_oid.add(client_key(o.get("symbol"), o["client_id"]))
        rows += D["orders"]; anchors += D["anchors"]; fills += PL.read_fills(root, d)
    arow = [a for a in anchors if str(a.get("rebalance_id", "")).startswith("A") and A <= int(a["rebalance_id"][1:]) < A + 14400]
    if len(arow) != 1:
        raise Unknown(f"expected exactly one anchors row for A={A}, found {len(arow)}")
    rid = arow[0]["rebalance_id"]
    blocked = sum(1 for o in rows if o.get("rebalance_id") == rid and o.get("terminal_reason") == "blocked_by_halt")
    fn = [f for f in fills if f.get("rebalance_id") == rid]
    N = sum(abs(f.get("fill_notional") or 0) for f in fn); T = sum(abs(f.get("fill_notional") or 0) for f in fn if f.get("venue_maker_flag") is False)
    return oids, cids_no_oid, arow[0], blocked, (round(T / N, 3) if N else None), round(N, 2)


def anchor_check(A, now_ms=None, ledger=None):
    oids, cids_no_oid, arow, blocked, taker_ledger, fill_n = ledger if ledger is not None else local_ledger(A)
    rid = arow["rebalance_id"]; start = (int(rid[1:]) - 600) * 1000
    now_ms = int(now_ms if now_ms is not None else time.time() * 1000)
    com = income_all("COMMISSION", start, now_ms)
    syms = sorted({r["symbol"] for r in com if r.get("symbol")})
    trades = []
    for s in syms:
        t = _get("/fapi/v1/userTrades", {"symbol": s, "startTime": start, "endTime": now_ms, "limit": 1000})
        if not isinstance(t, list):
            raise Unknown(f"userTrades {s}: not a list")
        if len(t) >= 1000:
            raise Unknown(f"userTrades {s}: saturated page (1000) — window too long for this device")
        trades += t
    unknown = sorted({order_key(t.get("symbol"), t["orderId"]) for t in trades} - oids)
    # an orderId the ledger does not carry is local only if its clientOrderId is one of OUR rows that recorded no order id
    # (flatten ladder). Anchor rows always carry order ids, so a same-second rid collision (two hosts minting the same
    # A<int(now)>) is still caught: that foreign order's id is not in request_ledger and its cid IS in request_ledger, not here.
    by_sym = {}
    for t in trades:
        key = order_key(t.get("symbol"), t["orderId"])
        if key in unknown: by_sym.setdefault(key[0], set()).add(key)
    cid_of = {}
    for s, ids in sorted(by_sym.items()):
        ao = _get("/fapi/v1/allOrders", {"symbol": s, "startTime": start, "endTime": now_ms, "limit": 1000})
        if not isinstance(ao, list) or len(ao) >= 1000:
            raise Unknown(f"allOrders {s}: not a list or saturated")
        for o in ao:
            key = order_key(o.get("symbol"), o["orderId"])
            if key in ids and o.get("clientOrderId"):
                cid_of[key] = client_key(key[0], o["clientOrderId"])
    foreign = sorted(i for i in unknown if cid_of.get(i) not in cids_no_oid)
    qn = sum(abs(float(t.get("quoteQty") or 0)) for t in trades)
    qt = sum(abs(float(t.get("quoteQty") or 0)) for t in trades if t.get("maker") is False)
    ratio = (arow.get("realized_gross") or 0) / arow["target_gross"] if arow.get("target_gross") else None
    rec = {"anchor": A, "rebalance_id": rid, "window_ms": [start, now_ms], "n_commission_rows": len(com), "n_symbols": len(syms),
           "n_venue_trades": len(trades), "n_foreign_order_ids": len(foreign), "foreign_order_ids": [i[1] for i in foreign[:50]],
           "foreign_orders": [{"symbol": i[0], "orderId": i[1]} for i in foreign[:50]],
           "foreign_client_order_id_prefixes": sorted({(cid_of[i][1] if i in cid_of else "?")[:15] for i in foreign})[:20],
           "n_matched_by_client_id_only": len(unknown) - len(foreign),
           "fill_ratio_realized_over_target": None if ratio is None else round(ratio, 4),
           "target_gross": arow.get("target_gross"), "realized_gross": arow.get("realized_gross"),
           "taker_share_venue_pooled": round(qt / qn, 3) if qn else None, "taker_share_ledger_pooled": taker_ledger,
           "ledger_fill_notional": fill_n, "blocked_by_halt_rows": blocked}
    bad = []
    if foreign: bad.append("foreign_order_ids")
    if ratio is None or ratio < 0.60: bad.append("fill_ratio_below_0.60")
    if blocked: bad.append("blocked_by_halt_rows")
    rec["VERDICT"] = "PASS" if not bad else "FAIL"; rec["bad"] = bad
    rec["identity_key"] = "symbol_orderId_v1"
    rec["coverage"] = {"global_single_writer_proven": False,
                       "symbol_discovery": "COMMISSION rows only", "orders": "filled orders only",
                       "window": "rid-minus-600s through request time; gaps between monitored windows not covered",
                       "client_fallback": "symbol plus clientOrderId for local rows with no orderId"}
    return rec


def main(argv=None):
    ap = argparse.ArgumentParser(); sub = ap.add_subparsers(dest="cmd", required=True)
    a1 = sub.add_parser("q1q4"); a1.add_argument("--t-off", required=True); a1.add_argument("--out", required=True)
    a2 = sub.add_parser("anchor"); a2.add_argument("--anchor", required=True, type=int); a2.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    tag = "VENUE_Q1_Q4" if a.cmd == "q1q4" else "VENUE_ANCHOR"
    try:
        rec = q1q4(a.t_off) if a.cmd == "q1q4" else anchor_check(a.anchor)
    except Unknown as e:
        rec = {"VERDICT": "UNKNOWN", "why": str(e)}
    rec.update(device="venue_readonly_symbol_bound.py", source_commit="3b4a2815a", self_sha256=hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest(),
               utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    with open(a.out, "x") as f:                                # never overwrite an earlier receipt
        json.dump(rec, f, indent=1, default=str)
    print(json.dumps({k: v for k, v in rec.items() if k not in ("self_sha256",)}, default=str)[:1500])
    v = rec["VERDICT"]
    print(f"{tag} {v}" + (f" {rec.get('bad')}" if v == "FAIL" else f" {rec.get('why')}" if v == "UNKNOWN" else ""))
    return {"PASS": 0, "FAIL": 1}.get(v, 2)


if __name__ == "__main__":
    sys.exit(main())
