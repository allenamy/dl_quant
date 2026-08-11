import json, time, sys
sys.path.insert(0, "/Users/haosiyu/cc_tmp/claude-501/-Users-haosiyu-Desktop-quant-research/6737834a-f0b4-40e0-82a0-c0e83c0ccf5f/scratchpad")
from oc_income_probe import get, page_income, summarize, _calls

now = int(time.time()*1000)

print("=== T2: same-ms page-boundary hazard — did cursor=newest+1 DROP rows? ===")
# boundaries flagged in T1 (full page whose newest ms is shared by >1 row)
bounds = [(1785025050000, 20), (1785110483000, 18), (1785139298000, 9),
          (1785139337000, 15), (1785153667000, 17)]
total_dropped = 0
for ms, n_seen_on_page in bounds:
    exact = get("/fapi/v1/income", {"startTime": ms, "endTime": ms, "limit": 1000}, signed=True)
    n_true = len(exact) if isinstance(exact, list) else -1
    dropped = n_true - n_seen_on_page
    total_dropped += max(0, dropped)
    print(f"  ms={ms}  rows_truly_at_this_ms={n_true}  rows_on_that_page={n_seen_on_page}  "
          f"-> DROPPED={dropped}")
print(f"  TOTAL rows dropped by newest+1 advance across flagged boundaries: {total_dropped}")

print("\n=== T3: 90-day cold-start span (what the PRODUCTION path actually requested) ===")
floor90 = now - 90*86400_000
r = get("/fapi/v1/income", {"startTime": floor90, "endTime": now, "limit": 1000}, signed=True)
if isinstance(r, dict):
    print(f"  90d single request ERROR: {r}")
else:
    ts = [int(x["time"]) for x in r]
    print(f"  90d single request: n={len(r)} "
          + (f"earliest={time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(min(ts)/1000))} "
             f"latest={time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(max(ts)/1000))}" if ts else "EMPTY"))

print("\n=== T3b: replicate PRODUCTION fetch_income loop verbatim, but incomeType=COMMISSION ===")
# production: cursor = max(start_ms, floor); page; if not page: break; if len<LIMIT: break;
#             if newest<=cursor: break; cursor=newest+1
def prod_loop(start_ms, end_ms, income_type):
    out, cursor, pages = [], start_ms, 0
    while cursor < end_ms:
        page = get("/fapi/v1/income", {"incomeType": income_type, "startTime": cursor,
                                       "endTime": end_ms, "limit": 1000}, signed=True)
        if isinstance(page, dict):
            print(f"    ERROR {page}"); return out, pages, "error"
        pages += 1
        if not page:
            return out, pages, "empty_page_break"
        out.extend(page)
        newest = max(int(p["time"]) for p in page)
        if len(page) < 1000:
            return out, pages, "short_page_break"
        if newest <= cursor:
            return out, pages, "no_progress_break"
        cursor = newest + 1
    return out, pages, "cursor_reached_end"

got, pages, why = prod_loop(floor90, now, "COMMISSION")
print(f"  production-loop COMMISSION from 90d floor: n={len(got)} pages={pages} exit={why}")
print(f"  (independent chunked ground truth for COMMISSION = 6890 from T1)")
print(f"\n[calls={_calls[0]}]")
