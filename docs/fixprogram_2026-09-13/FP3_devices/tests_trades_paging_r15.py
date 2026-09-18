#!/usr/bin/env python3
"""R15-I1 follow-through controls for fetch_trades.py, against a FAKE network. No credential is read and no request
leaves the process: the module's `get` is replaced by a fixture that serves a synthetic userTrades ledger through the
real endpoint semantics (startTime/endTime inclusive with limit, OR fromId with limit; the venue refuses both together).

The controls that matter:
  RED   — a window holding more than one full page. v1 sent ONE request, kept 1,000 rows, declared UNPROVEN and exited 0.
  GREEN — the same fixture must now return every in-window trade and read COMPLETE.
  THE POINT OF fromId — 1,001 trades in ONE millisecond is fatal to a time cursor and irrelevant to an id cursor.
          This is why the trades fix is not a copy of the income fix: the right cursor removes the hazard instead of
          working around it.
usage: tests_trades_paging_r15.py"""
import importlib.util, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
OK = [0]; BAD = []


def check(name, cond, detail=None):
    if cond: OK[0] += 1; print(f"  PASS {name}")
    else: BAD.append(name); print(f"  FAIL {name}" + (f"  <{detail}>" if detail is not None else ""))


def load(path, mod):
    spec = importlib.util.spec_from_file_location(mod, path)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


def fixture(ledger, fail_on=None, reject_fromId=False):
    """`ledger` = trades sorted by id. Serves the venue's two mutually exclusive selectors."""
    calls = []

    def _get(path, params):
        calls.append(dict(params))
        if fail_on is not None and len(calls) == fail_on:
            return 500, {"code": -1001, "msg": "Internal error"}, {}
        lim = int(params["limit"])
        if "fromId" in params:
            if "startTime" in params or "endTime" in params:
                return 400, {"code": -1128, "msg": "fromId cannot be sent with startTime or endTime"}, {}
            if reject_fromId:
                return 400, {"code": -1104, "msg": "Not all sent parameters were read"}, {}
            sel = [r for r in ledger if int(r["id"]) >= int(params["fromId"])]
        else:
            lo, hi = int(params["startTime"]), int(params["endTime"])
            sel = [r for r in ledger if lo <= int(r["time"]) <= hi]
        return 200, sel[:lim], {"X-MBX-USED-WEIGHT-1M": "5"}
    return _get, calls


def trade(i, t, sym="BTCUSDT"):
    return {"id": 900_000 + i, "orderId": 700_000 + i, "symbol": sym, "side": "BUY", "price": "100.0",
            "qty": "1.0", "quoteQty": "100.0", "realizedPnl": "0.1", "commission": "0.004",
            "commissionAsset": "USDT", "time": int(t), "buyer": True, "maker": True}


def run(mod, ledger, sym, s, e, **kw):
    g, calls = fixture(ledger, **kw)
    mod.get = g
    pages, rows, status, why = mod.fetch_trades(sym, s, e)
    return pages, rows, status, why, calls


def run_v1(ledger, s, e, **kw):
    """v1's exact behaviour: ONE window request, keep it, declare saturated on a full page, exit 0."""
    g, _ = fixture(ledger, **kw)
    st, body, _h = g("/fapi/v1/userTrades", {"symbol": "BTCUSDT", "startTime": s, "endTime": e, "limit": 1000})
    n = len(body) if isinstance(body, list) else 0
    return body, (n >= 1000), 0


print("── R15-I1 follow-through: userTrades pagination ──")
M = load(os.path.join(HERE, "fetch_trades.py"), "ft_v2")

# ── 0. no credential is read on import ──
check("importing the device does not read a credential (lazy `credentials()`)", M._cred == [], M._cred)

# ── 1. BASELINE GREEN FIRST — a red-capability check on an already-red baseline is vacuous ──
small = [trade(i, 1_700_000_000_000 + i * 10) for i in range(400)]
_, r_ok, st_ok, _, calls_ok = run(M, small, "BTCUSDT", 0, 9_999_999_999_999)
check("baseline: a 400-trade window comes back whole", len(r_ok) == 400, len(r_ok))
check("baseline: completeness COMPLETE", st_ok == "COMPLETE", st_ok)
check("baseline: a short first page needs exactly ONE request", len(calls_ok) == 1, len(calls_ok))
b_v1, sat_v1, _ = run_v1(small, 0, 9_999_999_999_999)
check("baseline: v1 is also whole here (so the red below is the defect, not the fixture)",
      len(b_v1) == 400 and not sat_v1, (len(b_v1), sat_v1))

# ── 2. THE RED CONTROL: a window holding 2,350 trades, i.e. more than one full page ──
big = [trade(i, 1_700_000_000_000 + i * 10) for i in range(2_350)]
b_old, sat_old, rc_old = run_v1(big, 0, 9_999_999_999_999)
check("RED on v1: 2,350 in-window trades, one request keeps only 1,000", len(b_old) == 1_000, len(b_old))
check("RED on v1: it declares saturation but still exits 0 with a partial file", sat_old and rc_old == 0)
_, r_new, st_new, why_new, calls_new = run(M, big, "BTCUSDT", 0, 9_999_999_999_999)
check("GREEN on v2: all 2,350 trades are recovered", len(r_new) == 2_350, (len(r_new), st_new, why_new))
check("GREEN on v2: completeness COMPLETE", st_new == "COMPLETE", (st_new, why_new))
check("GREEN on v2: no trade id is duplicated", len({r["id"] for r in r_new}) == 2_350, len(r_new))
check("GREEN on v2: continuation used fromId, never a time cursor", any("fromId" in c for c in calls_new[1:]), calls_new[:3])
check("GREEN on v2: fromId is never sent together with a time bound (the venue refuses that)",
      all(not ("fromId" in c and ("startTime" in c or "endTime" in c)) for c in calls_new), calls_new)

# ── 3. THE POINT OF AN ID CURSOR: a whole page inside ONE millisecond ──
#    For the income fetcher this exact shape lost rows and needed a separate enumeration path. Here it is a non-event.
onems = [trade(i, 1_700_000_000_000) for i in range(1_001)]
_, r_ms, st_ms, why_ms, _ = run(M, onems, "BTCUSDT", 0, 9_999_999_999_999)
check("1,001 trades in ONE millisecond: all recovered (an id cursor has no millisecond hazard)",
      len(r_ms) == 1_001, (len(r_ms), st_ms, why_ms))
check("1,001 trades in ONE millisecond: COMPLETE", st_ms == "COMPLETE", (st_ms, why_ms))

# ── 4. the window bounds are honoured even though fromId cannot carry them ──
wide = [trade(i, 1_700_000_000_000 + i * 10) for i in range(3_000)]
lo, hi = 1_700_000_000_000 + 5_000, 1_700_000_000_000 + 20_000        # ids 500..2000 inclusive
_, r_w, st_w, _, _ = run(M, wide, "BTCUSDT", lo, hi)
exp = [t for t in wide if lo <= t["time"] <= hi]
check("the client-side window filter reproduces the exact in-window set", len(r_w) == len(exp) == 1_501, (len(r_w), len(exp)))
check("no out-of-window trade leaks in", all(lo <= int(r["time"]) <= hi for r in r_w), st_w)
check("the pull is COMPLETE", st_w == "COMPLETE", st_w)

# ── 5. an error page is a REFUSAL with a nonzero exit, not a partial file read as a receipt ──
_, r_er, st_er, why_er, _ = run(M, big, "BTCUSDT", 0, 9_999_999_999_999, fail_on=2)
check("an error on a continuation page marks the pull INCOMPLETE", st_er == "INCOMPLETE", st_er)
check("the refusal names the failing page", bool(why_er) and "fromId_page_error_rc_500" in why_er, why_er)

# ── 6. a venue that refuses fromId must not look like a finished window ──
_, r_rj, st_rj, why_rj, _ = run(M, big, "BTCUSDT", 0, 9_999_999_999_999, reject_fromId=True)
check("a venue refusing fromId is INCOMPLETE, not silently truncated", st_rj == "INCOMPLETE", (st_rj, len(r_rj)))
check("the refusal is named", bool(why_rj) and "fromId_page_error" in why_rj, why_rj)

# ── 7. the CLI contract ──
src = open(os.path.join(HERE, "fetch_trades.py")).read()
check("the writer is atomic (temp file then os.replace)", ".part" in src and "os.replace(tmp, out)" in src)
check("an incomplete pull exits nonzero", 'sys.exit(0 if status == "COMPLETE" else 3)' in src)
check("the receipt declares its completeness and its cursor rule", '"completeness"' in src and '"cursor_rule"' in src)
check("the income mode still refuses and points at the paged fetcher",
      "REFUSED: single-shot income" in src and "fetch_income_paged.py" in src)
check("an unknown mode refuses instead of falling through silently", "unknown mode" in src)

print(f"\n{OK[0]} pass, {len(BAD)} fail" + ("" if not BAD else "\n  " + "\n  ".join(BAD)))
sys.exit(1 if BAD else 0)
