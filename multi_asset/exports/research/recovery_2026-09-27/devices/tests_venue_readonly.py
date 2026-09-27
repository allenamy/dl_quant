#!/usr/bin/env python3
"""Offline tests for venue_readonly.py (fake transport, fake ledger; no credential, no network). usage: /usr/bin/python3 tests_venue_readonly.py"""
import io, json, os, sys, tempfile, contextlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import venue_readonly as V

FAILS = 0


def check(name, cond, extra=""):
    global FAILS
    print(f"  {'OK  ' if cond else 'FAIL'}  {name}" + (f"  — {extra}" if extra and not cond else ""))
    FAILS += (not cond)


T_OFF = "2026-09-27T10:00:00Z"; T_OFF_MS = V.parse_z(T_OFF); NOW = T_OFF_MS + 3_600_000
CALLS = []


def world(open_orders=(), positions=(), income=None, trades=None, all_orders=None, fail=None):
    income = income or {}
    trades = trades or {}
    all_orders = all_orders or {}

    def tr(path, p):
        CALLS.append((path, dict(p)))
        if fail and path == fail:
            raise V.Unknown(f"{path} HTTP 503: fake outage")
        if path == "/fapi/v1/openOrders": return list(open_orders)
        if path == "/fapi/v3/account": return {"positions": [{"symbol": s, "positionAmt": str(q), "notional": str(n)} for s, q, n in positions]}
        if path == "/fapi/v1/income":
            rows = [r for r in income.get(p["incomeType"], []) if p["startTime"] <= r["time"] <= p["endTime"]]
            rows.sort(key=lambda r: r["time"]); return rows[:p["limit"]]
        if path == "/fapi/v1/userTrades": return list(trades.get(p["symbol"], []))
        if path == "/fapi/v1/allOrders": return list(all_orders.get(p["symbol"], []))
        raise AssertionError(path)
    V.TRANSPORT = tr; CALLS.clear()


def row(t, i=0, sym="XUSDT", kind="COMMISSION"):
    return {"symbol": sym, "incomeType": kind, "income": "-0.01", "asset": "USDT", "time": t, "tranId": 1000 + i, "tradeId": str(i)}


print("[Q1–Q4]")
world(positions=[("AUSDT", 0, 0), ("BUSDT", 0, 0)])
r = V.q1q4(T_OFF, now_ms=NOW)
check("baseline: nothing open, flat, no income since t_off => PASS", r["VERDICT"] == "PASS" and r["bad"] == [], r)
check("only GET endpoints on the allow-list were called", all(c[0] in V.GET_ALLOWED for c in CALLS), CALLS)
check("Q3/Q4 windows start exactly at t_off and end at now", all(c[1]["startTime"] == T_OFF_MS and c[1]["endTime"] == NOW for c in CALLS if c[0] == "/fapi/v1/income"))
world(open_orders=[{"clientOrderId": "F20260927083112-XUSDT-1"}])
check("an open order anywhere => FAIL Q1", V.q1q4(T_OFF, now_ms=NOW)["bad"] == ["Q1_open_orders"])
world(positions=[("AUSDT", "-12", "-40.5")])
r = V.q1q4(T_OFF, now_ms=NOW)
check("a nonzero position => FAIL Q2 with its notional", r["bad"] == ["Q2_positions"] and r["Q2_positions"]["sum_abs_notional"] == 40.5, r)
world(income={"COMMISSION": [row(T_OFF_MS + 5, 1)]})
check("one commission row after t_off => FAIL Q3 only", V.q1q4(T_OFF, now_ms=NOW)["bad"] == ["Q3_COMMISSION"])
world(income={"COMMISSION": [row(T_OFF_MS - 5, 1)], "REALIZED_PNL": [row(T_OFF_MS - 1, 2, kind="REALIZED_PNL")]})
check("rows BEFORE t_off (the incident itself) do not count => PASS", V.q1q4(T_OFF, now_ms=NOW)["VERDICT"] == "PASS")
big = [row(T_OFF_MS + 10 + i, i) for i in range(999)] + [row(T_OFF_MS + 2000, 999), row(T_OFF_MS + 2000, 1000), row(T_OFF_MS + 2001, 1001)]
world(income={"COMMISSION": big})
r = V.q1q4(T_OFF, now_ms=NOW)
check("paging: 1,002 rows across a full page boundary are all counted (boundary rows subtracted once, not lost)", r["Q3_COMMISSION"]["n"] == 1002, r["Q3_COMMISSION"])
twin = [row(T_OFF_MS + 7, 5), row(T_OFF_MS + 7, 5)]
world(income={"COMMISSION": twin})
check("two genuinely identical rows the venue returned are BOTH kept (E-0909-H)", V.q1q4(T_OFF, now_ms=NOW)["Q3_COMMISSION"]["n"] == 2)
world(fail="/fapi/v1/income")
try:
    V.q1q4(T_OFF, now_ms=NOW); check("an income outage raises Unknown", False)
except V.Unknown as e:
    check("an income outage => Unknown (never PASS)", "503" in str(e))
world()
try:
    V.q1q4("2026-09-27T12:00:00Z", now_ms=T_OFF_MS); check("t_off in the future refused", False)
except V.Unknown:
    check("t_off not in the past => Unknown", True)
try:
    V._get("/fapi/v1/order", {"symbol": "X"}); check("non-allow-listed path refused", False)
except RuntimeError as e:
    check("a trading path (/fapi/v1/order) is REFUSED before any transport", "REFUSED" in str(e))
check("importing and testing never loaded a credential", V._cred == {})

print("\n[main: exit codes and receipt]")
d = tempfile.mkdtemp()
import time as _t
T_OFF_REAL = _t.strftime("%Y-%m-%dT%H:%M:%SZ", _t.gmtime(_t.time() - 3600))    # main() uses the real clock: t_off must be in the past
for name, kw, want_rc, want_tag in (("pass", {}, 0, "VENUE_Q1_Q4 PASS"), ("fail", {"open_orders": [{"clientOrderId": "x"}]}, 1, "VENUE_Q1_Q4 FAIL ['Q1_open_orders']"),
                                    ("unknown", {"fail": "/fapi/v3/account"}, 2, "VENUE_Q1_Q4 UNKNOWN /fapi/v3/account HTTP 503")):
    world(**kw); buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = V.main(["q1q4", "--t-off", T_OFF_REAL, "--out", f"{d}/{name}.json"])
    last = buf.getvalue().strip().splitlines()[-1]
    check(f"{name}: rc {want_rc} and last line starts '{want_tag}'", rc == want_rc and last.startswith(want_tag), (rc, last))
check("the receipt records the verdict and the device sha", json.load(open(f"{d}/pass.json")).get("VERDICT") == "PASS" and len(json.load(open(f"{d}/pass.json"))["self_sha256"]) == 64)
world(); buf = io.StringIO()
try:
    with contextlib.redirect_stdout(buf):
        V.main(["q1q4", "--t-off", T_OFF_REAL, "--out", f"{d}/pass.json"])
    check("an existing receipt is never overwritten", False)
except FileExistsError:
    check("an existing receipt is never overwritten (open 'x')", True)

print("\n[anchor: foreign orderIds, fill ratio, taker share]")
A = 1790510400; RID = "A1790511840"; START = (1790511840 - 600) * 1000; NOW2 = START + 3_600_000
arow = {"rebalance_id": RID, "target_gross": 200000.0, "realized_gross": 190000.0}
LED = ({101, 102, 103}, {"F20260927120000-ZUSDT-1"}, arow, 0, 0.3, 190000.0)
def tr_(oid, sym, maker, q=100.0): return {"orderId": oid, "symbol": sym, "maker": maker, "quoteQty": str(q)}
inc = {"COMMISSION": [row(START + 100, 1, "XUSDT"), row(START + 200, 2, "YUSDT")]}
world(income=inc, trades={"XUSDT": [tr_(101, "XUSDT", True), tr_(102, "XUSDT", False)], "YUSDT": [tr_(103, "YUSDT", True, 200.0)]})
r = V.anchor_check(A, now_ms=NOW2, ledger=LED)
check("all venue orderIds are ours, 95% filled, no halt rows => PASS", r["VERDICT"] == "PASS" and r["n_foreign_order_ids"] == 0, r)
check("venue taker share pooled = 100/400 = 0.25", r["taker_share_venue_pooled"] == 0.25, r["taker_share_venue_pooled"])
check("the userTrades window starts 600 s before the rid", all(c[1]["startTime"] == START for c in CALLS if c[0] == "/fapi/v1/userTrades"))
world(income=inc, trades={"XUSDT": [tr_(101, "XUSDT", True), tr_(999, "XUSDT", False)], "YUSDT": [tr_(103, "YUSDT", True)]},
      all_orders={"XUSDT": [{"orderId": 999, "clientOrderId": "A1790511840-XUSDT-1"}]})
r = V.anchor_check(A, now_ms=NOW2, ledger=LED)
check("a foreign order with OUR anchor clientOrderId (same-second rid collision) is still FOREIGN => FAIL", r["bad"] == ["foreign_order_ids"] and r["foreign_order_ids"] == [999], r)
world(income=inc, trades={"XUSDT": [tr_(101, "XUSDT", True), tr_(555, "XUSDT", False)], "YUSDT": [tr_(103, "YUSDT", True)]},
      all_orders={"XUSDT": [{"orderId": 555, "clientOrderId": "F20260927120000-ZUSDT-1"}]})
r = V.anchor_check(A, now_ms=NOW2, ledger=LED)
check("an order id the ledger lacks but whose clientOrderId is one of our id-less rows (flatten ladder) is ours => PASS",
      r["VERDICT"] == "PASS" and r["n_matched_by_client_id_only"] == 1, r)
world(income=inc, trades={"XUSDT": [tr_(101, "XUSDT", True)], "YUSDT": [tr_(103, "YUSDT", True)]})
r = V.anchor_check(A, now_ms=NOW2, ledger=({101, 103}, set(), dict(arow, realized_gross=100000.0), 0, 0.0, 1.0))
check("fill ratio 0.50 < 0.60 => FAIL", r["bad"] == ["fill_ratio_below_0.60"], r)
r = V.anchor_check(A, now_ms=NOW2, ledger=({101, 103}, set(), arow, 7, 0.0, 1.0))
check("blocked_by_halt rows at the resumed anchor => FAIL", r["bad"] == ["blocked_by_halt_rows"], r)
world(income=inc, trades={"XUSDT": [tr_(101 + i, "XUSDT", True) for i in range(1000)]})
try:
    V.anchor_check(A, now_ms=NOW2, ledger=LED); check("saturated userTrades page", False)
except V.Unknown:
    check("a saturated userTrades page => Unknown, never a partial PASS", True)

print(f"\n{'ALL PASS' if FAILS == 0 else str(FAILS) + ' FAIL'}")
sys.exit(1 if FAILS else 0)
