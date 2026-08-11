"""RED TEST for live/binance_funding.py::FundingLedger.fetch_income.

Proves against the PRODUCTION code (no venue) that `cursor = newest + 1` silently drops
income rows whose timestamp collides with the last row of a full page — the exact shape a
funding settlement has, because every symbol on a book is charged at the SAME millisecond.
"""
import sys
sys.path.insert(0, "/Users/haosiyu/dl_quant_live/live")
import binance_funding as BF

SETTLE_MS = 1785168000000          # 2026-07-27T16:00:00Z, a real 8h settlement instant
N_NAMES   = 109                    # our book
PAGE      = BF.PAGE_LIMIT          # 1000


class FakeBroker:
    """Serves /fapi/v1/income exactly as Binance does: rows in [startTime, endTime],
    ordered by time ascending, truncated at `limit`."""
    mode = "TESTNET"

    def __init__(self, rows):
        self.rows = sorted(rows, key=lambda r: r["time"])
        self.calls = 0

    def _request(self, method, path, params, signed=False):
        self.calls += 1
        lo, hi, lim = int(params["startTime"]), int(params["endTime"]), int(params["limit"])
        sel = [r for r in self.rows if lo <= r["time"] <= hi
               and (params.get("incomeType") in (None, r["incomeType"]))]
        return sel[:lim]


# 12 consecutive 8h settlements, 109 rows each, every row of one settlement sharing ONE ms.
rows, t = [], SETTLE_MS - 11 * 8 * 3600_000
for k in range(12):
    for i in range(N_NAMES):
        rows.append({"symbol": f"SYM{i}USDT", "incomeType": "FUNDING_FEE",
                     "income": "-0.01", "time": t, "tranId": k * 1000 + i})
    t += 8 * 3600_000
TOTAL = len(rows)

b = FakeBroker(rows)
lg = BF.FundingLedger(b)
got = lg.fetch_income(rows[0]["time"], rows[-1]["time"] + 1)

print(f"settlements={12}  names/settlement={N_NAMES}  page_limit={PAGE}")
print(f"rows the venue holds : {TOTAL}")
print(f"rows fetch_income got: {len(got)}   (venue calls: {b.calls})")
lost = TOTAL - len(got)
print(f"SILENTLY DROPPED     : {lost}")

by_t = {}
for r in got:
    by_t[r["time"]] = by_t.get(r["time"], 0) + 1
partial = {k: v for k, v in by_t.items() if v != N_NAMES}
missing = [t for t in {r["time"] for r in rows} if t not in by_t]
print(f"settlements returned COMPLETE ({N_NAMES} rows): {sum(1 for v in by_t.values() if v == N_NAMES)}/12")
print(f"settlements returned PARTIAL: {len(partial)}  -> {partial}")
print(f"settlements returned NOT AT ALL: {len(missing)}")
print()
print("★ a PARTIAL settlement is the dangerous one: it is present in the ledger, so a coverage")
print("  metric counting DISTINCT settlements scores it as covered, while rows are missing.")
print()
print(f"ASSERT len(got) == {TOTAL}  ->  {'PASS' if len(got) == TOTAL else 'FAIL (defect reproduced)'}")

# ── the proposed fix, run against the same fixture ────────────────────────────────────────
def fetch_income_fixed(lg, start_ms, end_ms):
    out, cursor, seen = [], start_ms, set()
    while cursor <= end_ms:
        page = lg.broker._request("GET", "/fapi/v1/income", {
            "incomeType": "FUNDING_FEE", "startTime": cursor,
            "endTime": end_ms, "limit": BF.PAGE_LIMIT}, signed=True)
        if not page:
            break
        newest = max(int(p["time"]) for p in page)
        if len(page) >= BF.PAGE_LIMIT:
            # the page may have been cut INSIDE `newest`; re-ask for that instant exactly
            exact = lg.broker._request("GET", "/fapi/v1/income", {
                "incomeType": "FUNDING_FEE", "startTime": newest,
                "endTime": newest, "limit": BF.PAGE_LIMIT}, signed=True)
            if len(exact) >= BF.PAGE_LIMIT:
                raise AssertionError(
                    f"a single millisecond ({newest}) holds >= {BF.PAGE_LIMIT} income rows; "
                    f"it cannot be enumerated by this endpoint — must alarm, never silently skip")
            page = [p for p in page if int(p["time"]) != newest] + exact
        for p in page:
            k = (p.get("tranId"), p["symbol"], p["time"], p["income"])
            if k not in seen:
                seen.add(k)
                out.append(p)
        if newest >= end_ms:
            break
        cursor = newest + 1
    return out

b2 = FakeBroker(rows)
lg2 = BF.FundingLedger(b2)
fixed = fetch_income_fixed(lg2, rows[0]["time"], rows[-1]["time"] + 1)
by_t2 = {}
for r in fixed:
    by_t2[r["time"]] = by_t2.get(r["time"], 0) + 1
print(f"\nproposed fix: got {len(fixed)}/{TOTAL} rows in {b2.calls} calls; "
      f"complete settlements {sum(1 for v in by_t2.values() if v == N_NAMES)}/12  "
      f"-> {'PASS' if len(fixed) == TOTAL else 'STILL FAILING'}")
