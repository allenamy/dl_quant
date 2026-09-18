#!/usr/bin/env python3
"""Paginated read-only income pull (v2). Raw pages land on disk untouched; nothing is written to any ledger.

★ R15-I1 (independent review round 15). v1 advanced the cursor with `nxt = max(time) + 1`. A FULL page whose rows all
  carry the SAME millisecond therefore skipped that millisecond entirely: 1,001 distinct records in one millisecond
  produced a saved file of 1,000 rows and rc 0. Time advancement is not a completeness proof, and a saturated page is
  not evidence that the page holds the whole instant.

  The cursor now advances to `max(time)` WITHOUT the +1, so the boundary millisecond is re-requested, and the overlap
  is removed by BOUNDARY MULTISET SUBTRACTION rather than by a global de-duplication set.

★ WHY MULTISET SUBTRACTION AND NOT A `seen` SET (E-0909-H, 2026-09-09): one venue trade emits TWO income rows that
  share a tranId (COMMISSION + REALIZED_PNL). A de-duplication key coarser than the ROW dropped one row per trade and
  understated the day's commission by 120 USDT, in the loss-making direction only. v1's key
  (tranId, incomeType, symbol, time, income) is finer than that one but still not the row: it has no `asset`, so a
  BNB-denominated and a USDT-denominated row of the same type, symbol, instant and numeric amount collapse into one.
  And GENUINELY identical rows are indistinguishable by construction — a global set silently keeps one of them.
  Subtracting only the rows we actually re-requested at the boundary removes exactly the overlap and preserves
  duplicates the venue really emitted. The count of subtractions is published so the operation is never invisible.

★ COMPLETENESS IS DECLARED, NEVER ASSUMED. `completeness` is COMPLETE only when every segment ended on a short page
  with no refusal. A saturated single millisecond is enumerated through the endpoint's own `page` parameter; if that
  enumeration itself saturates, or any page errors, the pull is INCOMPLETE, the reason is named, and the process
  EXITS NONZERO. v1 printed "PAGE FAIL" and still exited 0 with a partial file, which is how a truncated pull becomes
  a cash receipt.

usage: fetch_income_paged.py <startMs> <endMs> <out.json> [label]"""
import collections, hashlib, hmac, json, os, sys, time, urllib.parse, urllib.request

LIMIT = 1000                     # the endpoint's maximum page size
PAGE_CAP = 200                   # refuse rather than loop forever inside one saturated millisecond

BASE = "https://fapi.binance.com"; _last = [0.0]; _cred = []


def credentials():
    """★ read LAZILY, from the one hardcoded read-only path. Lazy because the pagination logic must be testable against
    a fake network without any credential present — importing this module must never require a key. The path stays
    HARDCODED on purpose: an environment variable that selects a credential file is exactly the unregistered-input
    class that R15-C1 found in the chain gates, and it is not worth re-introducing here for test convenience."""
    if not _cred:
        kv = {}
        for line in open(os.path.expanduser("~/.quant_readonly.env")):
            line = line.strip()
            if line and not line.startswith("#"):
                for sep in ("=", ":"):
                    if sep in line:
                        k, v = line.split(sep, 1); kv[k.strip()] = v.strip(); break
        _cred.append((kv["QUANT_RO_API_KEY"], kv["QUANT_RO_API_SECRET"]))
    return _cred[0]


def get(params):
    K, SEC = credentials()
    dt = time.time() - _last[0]
    if dt < 0.35: time.sleep(0.35 - dt)
    p = dict(params); p["timestamp"] = int(time.time() * 1000); p["recvWindow"] = 5000
    q = urllib.parse.urlencode(p, safe=",")
    sig = hmac.new(SEC.encode(), q.encode(), hashlib.sha256).hexdigest()
    req = urllib.request.Request(f"{BASE}/fapi/v1/income?{q}&signature={sig}", headers={"X-MBX-APIKEY": K})
    _last[0] = time.time()
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read().decode()), dict(r.headers)
    except urllib.error.HTTPError as e:
        try: b = json.loads(e.read().decode())
        except Exception: b = {"raw": "unparsable"}
        return e.code, b, dict(e.headers)


def row_identity(r):
    """the ROW, not the transaction (E-0909-H): every field the venue sent, canonically ordered. Two rows are the same
    row only if the venue sent the same bytes; a tranId is a transaction identity and is deliberately NOT used alone."""
    return json.dumps(r, sort_keys=True, separators=(",", ":"))


def run(s, e, label):
    pages, rows, cur = [], [], s
    boundary = collections.Counter()      # identities already recorded AT `cur` — the only rows a re-request may repeat
    n_subtracted = 0
    status = "COMPLETE"; why = None

    def record(page_rows, at_boundary_ts):
        """append a page, subtracting exactly the rows we already hold at the boundary millisecond"""
        nonlocal n_subtracted
        kept = []
        for r in page_rows:
            if at_boundary_ts is not None and int(r.get("time", -1)) == at_boundary_ts:
                i = row_identity(r)
                if boundary[i] > 0:
                    boundary[i] -= 1; n_subtracted += 1; continue
            kept.append(r)
        rows.extend(kept)
        return kept

    while True:
        st, body, hdr = get({"startTime": cur, "endTime": e, "limit": LIMIT})
        pages.append({"startTime": cur, "status": st, "n": len(body) if isinstance(body, list) else 0,
                      "weight": hdr.get("X-MBX-USED-WEIGHT-1M"), "mode": "window"})
        if st != 200 or not isinstance(body, list):
            status, why = "INCOMPLETE", f"page_error_rc_{st}: {json.dumps(body)[:140]}"
            print(f"{label} PAGE FAIL rc {st} {json.dumps(body)[:140]}"); break
        kept = record(body, cur if boundary else None)
        if len(body) < LIMIT:
            break                                              # short page: this window is exhausted, by the venue's own answer
        times = [int(r["time"]) for r in body]
        mx, mn = max(times), min(times)
        if mx > mn:
            # ★ advance to mx, NOT mx+1: the boundary millisecond may hold rows this page could not carry.
            boundary = collections.Counter(row_identity(r) for r in rows if int(r.get("time", -1)) == mx)
            cur = mx
            continue
        # ── mx == mn on a FULL page: the whole page sits inside ONE millisecond. Advancing by time cannot enumerate
        #    the rest of that instant, so we enumerate it through the endpoint's own page parameter instead. ──
        pg = 2; ms_rows = list(kept)
        while True:
            st2, body2, hdr2 = get({"startTime": mx, "endTime": mx, "limit": LIMIT, "page": pg})
            pages.append({"startTime": mx, "endTime": mx, "page": pg, "status": st2,
                          "n": len(body2) if isinstance(body2, list) else 0,
                          "weight": hdr2.get("X-MBX-USED-WEIGHT-1M"), "mode": "saturated_millisecond"})
            if st2 != 200 or not isinstance(body2, list):
                status, why = "INCOMPLETE", f"saturated_millisecond_{mx}_page_{pg}_rc_{st2}"
                print(f"{label} SATURATED-MS PAGE FAIL rc {st2} at {mx} page {pg}"); break
            # page 1 of this millisecond is the page we already hold; pages >= 2 are new rows of the same instant
            ms_seen = collections.Counter(row_identity(r) for r in ms_rows)
            fresh = []
            for r in body2:
                i = row_identity(r)
                if ms_seen[i] > 0: ms_seen[i] -= 1; n_subtracted += 1; continue
                fresh.append(r)
            rows.extend(fresh); ms_rows.extend(fresh)
            if len(body2) < LIMIT: break                       # the instant is exhausted
            if not fresh:
                # ★ a FULL page beyond page 1 that carries nothing we do not already hold means the venue is not
                #   honouring `page`. Looping to the cap would burn 200 requests to reach the same refusal, and
                #   worse, a reader could mistake the repeated page for a completed enumeration.
                status, why = "INCOMPLETE", f"saturated_millisecond_{mx}_page_{pg}_repeated_page_1_page_cap_unreachable"
                print(f"{label} SATURATED-MS: venue ignored `page` at {mx}"); break
            pg += 1
            if pg > PAGE_CAP:
                status, why = "INCOMPLETE", f"saturated_millisecond_{mx}_exceeded_page_cap_{PAGE_CAP}"
                print(f"{label} SATURATED-MS PAGE CAP at {mx}"); break
        if status != "COMPLETE": break
        nxt = mx + 1                                           # the instant was enumerated in full, so stepping past it is safe
        if nxt > e: break
        boundary = collections.Counter(); cur = nxt
    return pages, rows, status, why, n_subtracted


if __name__ == "__main__":
    s, e, out = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
    label = sys.argv[4] if len(sys.argv) > 4 else ""
    pages, rows, status, why, n_sub = run(s, e, label)
    doc = {"endpoint": "/fapi/v1/income", "device": "fetch_income_paged.py v2 (R15-I1)", "label": label,
           "startTime": s, "endTime": e, "fetched_utc": time.strftime("%FT%TZ", time.gmtime()),
           "pages": pages, "n_pages": len(pages), "n_rows": len(rows),
           "completeness": status, "incomplete_reason": why,
           "n_boundary_rows_subtracted": n_sub,
           "dedupe_rule": "boundary multiset subtraction on the FULL row (E-0909-H: a tranId is a transaction identity, "
                          "not a row identity; a global de-duplication set silently drops genuinely duplicated rows)",
           "cursor_rule": "advance to max(time), never max(time)+1; a full page inside one millisecond is enumerated "
                          "through the endpoint's `page` parameter, and an exhausted page cap is a refusal",
           "body": rows}
    tmp = out + ".part"
    with open(tmp, "w") as fh: json.dump(doc, fh, indent=1)
    os.replace(tmp, out)                                       # atomic: a reader never sees a half-written pull
    print(f"{label} rows {len(rows)} pages {len(pages)} completeness {status}"
          f"{'' if why is None else ' (' + why + ')'} subtracted {n_sub} "
          f"types {dict(collections.Counter(r['incomeType'] for r in rows))}")
    sys.exit(0 if status == "COMPLETE" else 3)                 # an incomplete pull must never be read as a cash receipt
