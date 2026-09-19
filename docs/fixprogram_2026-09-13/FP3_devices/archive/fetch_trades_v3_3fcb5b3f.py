#!/usr/bin/env python3
"""FP3 I: read-only venue fetch. Raw responses land on disk untouched; nothing is written to any ledger.
usage: fetch_trades.py trades <SYMBOL> <startMs> <endMs> <out.json>

★ R15-I1 follow-through (2026-09-18). Round 14 fixed the single-shot income pull by moving to a paged fetcher, and round
  15 then found that the paged fetcher ITSELF lost rows at a full page's last millisecond — on the real account, in the
  windows already used for the cash reconciliation. "We switched to the paged device" was never a completeness proof.

  `trades` had the matching hole in a milder form: it sent ONE request with limit=1000 and, on a full page, DECLARED
  `completeness: UNPROVEN` and left the caller to narrow the window. An honest declaration is better than a silent
  truncation, but it is not a finished measurement, and the remaining flatten-bucket quantities and prices need one.

  This now pages by `fromId`, which is a TRUE RECORD-IDENTITY CURSOR: trade ids are unique and strictly increasing per
  symbol, so advancing to `last_id + 1` cannot skip a row and cannot repeat one. There is no timestamp-collision hazard
  here at all — that is exactly why `fromId` is the right cursor and a time cursor is not.

  The venue does not accept `fromId` together with `startTime`/`endTime`, so the window is opened with a time-bounded
  first request and continued by id, with each page filtered back to the window client-side. Completeness is DECLARED,
  and an unfinished pull EXITS NONZERO rather than leaving a partial file that reads like a receipt.

The `income` mode is refused here; use fetch_income_paged.py.
This is a one-round evidence tool, not a certified long-running ledger synchroniser: the 0.35 s single-process throttle
says nothing about multi-process rate limits or 429 handling.

★ v3 (2026-09-19, independent review round 5 R5-08): PER-ROW PAGE EVIDENCE. v2's page receipt carried only a count `n`,
  so a reader could not tell "the page returned 2 rows and both were outside the window" from "the page returned 2 rows
  and they vanished before the body was written" — the validator accepted a receipt claiming 2 rows over an empty body.
  Every page record now also carries
     returned    [id, time] of EVERY row the venue returned, in response order (kept or dropped)
     n_kept      how many rows this page added to the body
     past_window whether a row of this page lay beyond the window's right edge (the fetcher's stop signal)
  so the page -> body mapping can be REPLAYED under this fetcher's own rules (window filter, id de-duplication, fromId
  cursor = max(id)+1, stop on a short / empty / past-window page) instead of trusted. This is bookkeeping only: the
  requests sent, their order and the stop rules are byte-for-byte those of v2 (archive/fetch_trades_v2_7ad96418.py)."""
import hashlib, hmac, json, os, sys, time, urllib.parse, urllib.request

LIMIT = 1000
PAGE_CAP = 500                     # refuse rather than page forever
BASE = "https://fapi.binance.com"; _last = [0.0]; _cred = []


def credentials():
    """read LAZILY from the one hardcoded read-only path, so the pagination logic is testable against a fake network
    with no credential present. The path stays HARDCODED: an environment variable that selects a credential file is the
    same unregistered-input class R15-C1 found in the chain gates, and it is not worth re-introducing for convenience."""
    if not _cred:
        kv = {}
        for line in open(os.path.expanduser("~/.quant_readonly.env")):
            line = line.strip()
            if line and not line.startswith("#"):
                for sep in (":", "="):
                    if sep in line:
                        k, v = line.split(sep, 1); kv[k.strip()] = v.strip(); break
        _cred.append((kv["QUANT_RO_API_KEY"], kv["QUANT_RO_API_SECRET"]))
    return _cred[0]


def get(path, params):
    K, SEC = credentials()
    dt = time.time() - _last[0]
    if dt < 0.35: time.sleep(0.35 - dt)
    p = dict(params); p["timestamp"] = int(time.time() * 1000); p["recvWindow"] = 5000
    q = urllib.parse.urlencode(p, safe=",")
    sig = hmac.new(SEC.encode(), q.encode(), hashlib.sha256).hexdigest()
    req = urllib.request.Request(f"{BASE}{path}?{q}&signature={sig}", headers={"X-MBX-APIKEY": K})
    _last[0] = time.time()
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read().decode()), dict(r.headers)
    except urllib.error.HTTPError as e:
        try: b = json.loads(e.read().decode())
        except Exception: b = {"raw": "unparsable"}
        return e.code, b, dict(e.headers)


def page_evidence(body, n_kept, past):
    """★ v3 (R5-08): the per-row evidence of ONE page — [id, time] of every row the venue returned, in response order,
    kept or not — plus what this page added and whether it ran past the window. Raw values, no conversion, so recording
    the evidence can never raise where v2 did not."""
    return {"returned": [[r.get("id"), r.get("time")] for r in body], "n_kept": n_kept, "past_window": past}


def fetch_trades(sym, s, e):
    """every userTrade with s <= time <= e, paged by trade id. Returns (pages, rows, completeness, reason)."""
    pages, rows, seen_ids = [], [], set()
    status, why = "COMPLETE", None

    def take(body):
        """keep the in-window rows; report whether this page ran past the window's right edge, and how many it kept"""
        past = False; n0 = len(rows)
        for r in body:
            tid = r.get("id")
            t = int(r["time"])
            if t > e: past = True; continue
            if t < s: continue
            if tid in seen_ids: continue                   # ids are unique: a repeat is a re-request, never a twin row
            seen_ids.add(tid); rows.append(r)
        return past, len(rows) - n0

    st, body, hdr = get("/fapi/v1/userTrades", {"symbol": sym, "startTime": s, "endTime": e, "limit": LIMIT})
    pages.append({"mode": "window", "startTime": s, "endTime": e, "status": st,
                  "n": len(body) if isinstance(body, list) else 0, "weight": hdr.get("X-MBX-USED-WEIGHT-1M")})
    if st != 200 or not isinstance(body, list):
        return pages, rows, "INCOMPLETE", f"page_error_rc_{st}: {json.dumps(body)[:140]}"
    past0, k0 = take(body)
    pages[-1].update(page_evidence(body, k0, past0))
    if len(body) < LIMIT:
        return pages, rows, status, why                    # short page: the venue says this window is exhausted

    # ── the window page is FULL, so it may be truncated. Continue by trade id, which cannot skip or repeat a row.
    #    The venue refuses fromId together with startTime/endTime, so the window is re-applied client-side. ──
    cur = max(int(r["id"]) for r in body) + 1
    for _ in range(PAGE_CAP):
        st2, body2, hdr2 = get("/fapi/v1/userTrades", {"symbol": sym, "fromId": cur, "limit": LIMIT})
        pages.append({"mode": "fromId", "fromId": cur, "status": st2,
                      "n": len(body2) if isinstance(body2, list) else 0, "weight": hdr2.get("X-MBX-USED-WEIGHT-1M")})
        if st2 != 200 or not isinstance(body2, list):
            return pages, rows, "INCOMPLETE", f"fromId_page_error_rc_{st2}_at_{cur}"
        if not body2:
            pages[-1].update(page_evidence(body2, 0, False))
            return pages, rows, status, why                # no trades at or beyond this id: exhausted
        past, k = take(body2)
        pages[-1].update(page_evidence(body2, k, past))
        nxt = max(int(r["id"]) for r in body2) + 1
        if past or len(body2) < LIMIT:
            return pages, rows, status, why                # ran past the window, or the account has no more trades
        if nxt <= cur:
            return pages, rows, "INCOMPLETE", f"fromId_cursor_did_not_advance_at_{cur}"
        cur = nxt
    return pages, rows, "INCOMPLETE", f"exceeded_page_cap_{PAGE_CAP}"


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "trades":
        sym, s, e, out = sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), sys.argv[5]
        pages, rows, status, why = fetch_trades(sym, s, e)
        doc = {"endpoint": "/fapi/v1/userTrades", "device": "fetch_trades.py v3 (R15-I1 follow-through + R5-08 per-row page evidence)",
               "symbol": sym, "startTime": s, "endTime": e,
               "fetched_utc": time.strftime("%FT%TZ", time.gmtime()),
               "pages": pages, "n_pages": len(pages), "n_rows": len(rows),
               "completeness": status, "incomplete_reason": why,
               "cursor_rule": "time-bounded first request, then paged by fromId (trade ids are unique and strictly "
                              "increasing, so the cursor can neither skip nor repeat a row); each page re-filtered to "
                              "the window because the venue refuses fromId together with startTime/endTime",
               "page_evidence_rule": "each page carries returned=[id, time] of every row the venue returned (response order), "
                                     "n_kept and past_window, so the page -> body mapping can be replayed, not trusted (R5-08)",
               "body": rows}
        tmp = out + ".part"
        with open(tmp, "w") as fh: json.dump(doc, fh, indent=1)
        os.replace(tmp, out)
        print(f"{sym} rows {len(rows)} pages {len(pages)} completeness {status}" + ("" if why is None else f" ({why})"))
        sys.exit(0 if status == "COMPLETE" else 3)
    elif mode == "income":
        # ★ R14-I2: this mode used to send ONE request with limit=1000 and no pagination, so a full page was
        #   indistinguishable from a complete window — two real pulls came back at exactly 1,000 rows.
        print("REFUSED: single-shot income is not complete-by-construction (a full 1000-row page cannot be told from a finished window).")
        print("         Use fetch_income_paged.py <startMs> <endMs> <out.json> [label], which pages until a short page and records every page.")
        sys.exit(2)
    else:
        print(f"REFUSED: unknown mode {mode!r}; the only modes are `trades` and `income` (the latter refuses and points elsewhere)."); sys.exit(2)
