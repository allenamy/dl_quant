#!/usr/bin/env python3
"""R15-I1 controls for fetch_income_paged.py, against a FAKE network. No credential is read and no request leaves the
process: the module's `get` is replaced by a fixture that serves a synthetic ledger through the real `/fapi/v1/income`
pagination semantics (startTime/endTime inclusive, limit, page).

The controls that matter:
  RED   — 1,001 distinct rows inside ONE millisecond. v1 advanced `max(time)+1` and saved 1,000 with rc 0.
  GREEN — the same fixture must now yield all 1,001 and stay COMPLETE.
  POSITIVE CONTROL (E-0909-H) — the fix must not create a NEW truncation. One venue trade emits COMMISSION and
          REALIZED_PNL rows that SHARE a tranId; genuinely duplicated rows must survive the boundary subtraction.
          Fixing one truncation by de-duplicating too coarsely is how E-0909-H happened in the first place.
usage: tests_income_paging_r15.py"""
import importlib.util, json, os, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
OK = [0]; BAD = []


def check(name, cond, detail=None):
    if cond: OK[0] += 1; print(f"  PASS {name}")
    else: BAD.append(name); print(f"  FAIL {name}" + (f"  <{detail}>" if detail is not None else ""))


def load(path, mod):
    spec = importlib.util.spec_from_file_location(mod, path)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


def fixture(ledger, fail_on=None, no_page_param=False):
    """serve `ledger` (a list of row dicts, sorted by time) the way the venue does: rows with
    startTime <= time <= endTime, at most `limit`, `page` selecting the 1-based block."""
    calls = []

    def _get(params):
        calls.append(dict(params))
        if fail_on is not None and len(calls) == fail_on:
            return 500, {"code": -1001, "msg": "Internal error"}, {}
        lo = int(params["startTime"]); hi = int(params["endTime"]); lim = int(params["limit"])
        pg = int(params.get("page", 1))
        if no_page_param: pg = 1                      # a venue that ignores `page` must not look like completeness
        sel = [r for r in ledger if lo <= int(r["time"]) <= hi]
        blk = sel[(pg - 1) * lim: pg * lim]
        return 200, blk, {"X-MBX-USED-WEIGHT-1M": "1"}
    return _get, calls


def row(i, t, itype="COMMISSION", sym="BTCUSDT", asset="USDT", income="-0.01", tran=None):
    return {"tranId": (tran if tran is not None else 1_000_000 + i), "incomeType": itype, "symbol": sym,
            "asset": asset, "income": income, "time": int(t), "info": "", "tradeId": str(2_000_000 + i)}


def run(mod, ledger, s, e, **kw):
    g, calls = fixture(ledger, **kw)
    mod.get = g
    pages, rows, status, why, n_sub = mod.run(s, e, "T")
    return pages, rows, status, why, n_sub, calls


def run_v1(mod, ledger, s, e, **kw):
    """v1 had no `run()`; replay its exact loop so the RED control is the OLD ALGORITHM, not a paraphrase of it."""
    g, calls = fixture(ledger, **kw)
    pages, out, cur, seen = [], [], s, set()
    while True:
        st, body, hdr = g({"startTime": cur, "endTime": e, "limit": 1000})
        pages.append({"startTime": cur, "status": st, "n": len(body)})
        if st != 200 or not isinstance(body, list): break
        new = [r for r in body if (r.get("tranId"), r.get("incomeType"), r.get("symbol"), r.get("time"), r.get("income")) not in seen]
        for r in new: seen.add((r.get("tranId"), r.get("incomeType"), r.get("symbol"), r.get("time"), r.get("income")))
        out += new
        if len(body) < 1000: break
        nxt = max(int(r["time"]) for r in body) + 1
        if nxt <= cur: break
        cur = nxt
    return pages, out


print("── R15-I1: same-millisecond pagination ──")
M = load(os.path.join(HERE, "fetch_income_paged.py"), "fip_v2")

# ── 0. the module must import with NO credential present (the fixture never calls the real transport) ──
check("importing the device does not read a credential (lazy `credentials()`)", M._cred == [], M._cred)

# ── 1. BASELINE GREEN FIRST. A red-capability check on an already-red baseline is vacuous. ──
plain = [row(i, 1_000_000 + i) for i in range(2_500)]
_, r_ok, st_ok, _, sub_ok, calls_ok = run(M, plain, 0, 9_999_999_999_999)
check("baseline: 2,500 rows across distinct milliseconds come back whole", len(r_ok) == 2_500, len(r_ok))
check("baseline: completeness COMPLETE", st_ok == "COMPLETE", st_ok)
check("baseline: no row was subtracted at a boundary that held nothing new", sub_ok >= 0 and len(r_ok) == 2_500, sub_ok)
_, r_v1 = run_v1(M, plain, 0, 9_999_999_999_999)
check("baseline: the OLD algorithm is also whole here (so the red below is the defect, not the fixture)",
      len(r_v1) == 2_500, len(r_v1))

# ── 2. THE RED CONTROL: 1,001 distinct rows in ONE millisecond ──
onems = [row(i, 1_700_000_000_000) for i in range(1_001)]
_, r_old = run_v1(M, onems, 0, 9_999_999_999_999)
check("RED on v1: 1,001 rows in one millisecond, the old cursor saves only 1,000", len(r_old) == 1_000, len(r_old))
_, r_new, st_new, why_new, sub_new, calls_new = run(M, onems, 0, 9_999_999_999_999)
check("GREEN on v2: all 1,001 rows are recovered", len(r_new) == 1_001, (len(r_new), st_new, why_new))
check("GREEN on v2: completeness COMPLETE", st_new == "COMPLETE", (st_new, why_new))
check("GREEN on v2: no row is duplicated", len({json.dumps(x, sort_keys=True) for x in r_new}) == 1_001, len(r_new))
check("GREEN on v2: the saturated millisecond was enumerated with the `page` parameter",
      any(c.get("page") for c in calls_new), calls_new[:4])

# ── 3. POSITIVE CONTROL (E-0909-H): genuine twin rows sharing a tranId must BOTH survive ──
#    One trade → COMMISSION + REALIZED_PNL, same tranId, same symbol, same millisecond.
twins = []
for i in range(600):
    t = 1_700_000_000_000 + i
    twins.append(row(i, t, "COMMISSION", tran=5_000_000 + i))
    twins.append(row(i, t, "REALIZED_PNL", income="1.25", tran=5_000_000 + i))
_, r_tw, st_tw, _, _, _ = run(M, twins, 0, 9_999_999_999_999)
check("twin rows: both halves of every trade survive (1,200 rows, not 600)", len(r_tw) == 1_200, len(r_tw))
check("twin rows: COMMISSION and REALIZED_PNL are both present for every tranId",
      len({r["tranId"] for r in r_tw}) == 600 and
      sum(1 for r in r_tw if r["incomeType"] == "COMMISSION") == 600 and
      sum(1 for r in r_tw if r["incomeType"] == "REALIZED_PNL") == 600,
      {r["incomeType"] for r in r_tw})
check("twin rows: completeness COMPLETE", st_tw == "COMPLETE", st_tw)

# ── 4. BYTE-IDENTICAL rows the venue really emitted twice are NOT collapsed ──
#    A global de-duplication set keeps one of them by construction; boundary subtraction keeps both.
dupes = [row(0, 1_700_000_000_000 + i) for i in range(1_200)]
dupes.insert(1_100, dict(dupes[1_100]))                    # an exact byte-for-byte repeat, mid-ledger
dupes.sort(key=lambda r: int(r["time"]))
_, r_dp, st_dp, _, _, _ = run(M, dupes, 0, 9_999_999_999_999)
check("a genuinely repeated row is kept, not collapsed", len(r_dp) == 1_201, len(r_dp))

# ── 5. the boundary millisecond is not double-counted when the page really does advance ──
span = [row(i, 1_700_000_000_000 + (i // 3)) for i in range(2_400)]   # three rows per millisecond, crosses a page edge
_, r_sp, st_sp, _, sub_sp, _ = run(M, span, 0, 9_999_999_999_999)
check("a boundary millisecond crossed by a page edge is neither lost nor doubled", len(r_sp) == 2_400, len(r_sp))
check("the boundary subtraction actually fired and was published", sub_sp > 0, sub_sp)

# ── 6. an error page is a REFUSAL with a nonzero exit, not a partial file with rc 0 ──
_, r_er, st_er, why_er, _, _ = run(M, plain, 0, 9_999_999, fail_on=2)
check("an error page marks the pull INCOMPLETE", st_er == "INCOMPLETE", st_er)
check("the refusal names the page error", bool(why_er) and "page_error_rc_500" in why_er, why_er)
check("v1 by contrast would have kept its partial result with no status at all",
      len(run_v1(M, plain, 0, 9_999_999, fail_on=2)[1]) < 2_500)

# ── 7. a venue that ignores `page` must not be mistaken for a complete enumeration ──
_, r_np, st_np, why_np, _, _ = run(M, onems, 0, 9_999_999_999_999, no_page_param=True)
check("a venue ignoring `page` inside a saturated millisecond is INCOMPLETE, not silently short",
      st_np == "INCOMPLETE", (st_np, why_np, len(r_np)))
check("the refusal names the page cap", bool(why_np) and "page_cap" in why_np, why_np)

# ── 8. the CLI writes atomically and exits nonzero on an incomplete pull ──
src = open(os.path.join(HERE, "fetch_income_paged.py")).read()
check("the writer is atomic (temp file then os.replace)", ".part" in src and "os.replace(tmp, out)" in src)
check("an incomplete pull exits nonzero", 'sys.exit(0 if status == "COMPLETE" else 3)' in src)
check("the receipt declares its completeness and its de-duplication rule",
      '"completeness"' in src and '"dedupe_rule"' in src and '"cursor_rule"' in src)

print(f"\n{OK[0]} pass, {len(BAD)} fail" + ("" if not BAD else "\n  " + "\n  ".join(BAD)))
sys.exit(1 if BAD else 0)
