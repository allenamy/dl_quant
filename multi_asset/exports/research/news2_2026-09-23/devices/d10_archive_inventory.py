#!/usr/bin/env python3
"""d10_archive_inventory.py -- which (symbol, month) fundingRate archives EXIST, in 832 requests not 67,392.

D10 stage 1, question 1 (真值可得性) and the sizing of question 2.
Pre-registration: docs/PREREG_D10_funding_truth_audit_stage1_2026-09-25.md @ 496142901.

WHY THIS DEVICE EXISTS -- a measured correction to my own first approach. I started a month-major pull
that asks the CDN for all 832 symbols in each of 81 months, i.e. 67,392 requests, most of them 404s for
symbols not yet listed. Measured rate: ~832 requests took about 11 minutes (per-request latency
dominates the 0.21 s spacing), so the full census would have been roughly 20 hours of requests spread
over eight-plus quiet windows. The archive fronts an S3 bucket whose XML listing API accepts a prefix,
so ONE request per symbol returns every month that symbol has. That is 832 requests for the complete
inventory -- an 81x reduction -- and it turns the download cost from an estimate into an exact count.

Rate discipline is unchanged from FX-PROD's puller: sequential, >= 0.21 s between requests, anonymous
GET of the public archive only, no trading or account endpoint, nothing written outside the output path.
Truncated listings are followed rather than assumed away.

WHAT THIS DOES NOT DO: it does not download any settlement data, so it cannot yet answer question 2's
event-level completeness. It answers "which months of truth exist at all" and prices the rest exactly.
"""
import argparse, collections, datetime, hashlib, json, os, re, sys, time, urllib.error, urllib.request

for _c in (os.path.dirname(os.path.realpath(__file__)),
           os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), "common"),
           os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))), "common")):
    if os.path.exists(os.path.join(_c, "durable_write.py")):
        sys.path.insert(0, _c)
        break
else:
    raise ImportError("common/durable_write.py not found next to or above this device; deploy it with the device")
import durable_write as DW  # every file this device writes goes through it (news2 class fix 2026-09-27)

BUCKET = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision"
PREFIX = "data/futures/um/monthly/fundingRate/"
MIN_SPACING_S = 0.21
KEY_RE = re.compile(r"<Key>([^<]+)</Key>")
SIZE_RE = re.compile(r"<Size>(\d+)</Size>")
CONT_RE = re.compile(r"<NextMarker>([^<]+)</NextMarker>")
MONTH_RE = re.compile(r"^(?P<sym>[A-Z0-9_]+)-fundingRate-(?P<month>\d{4}-\d{2})\.zip$")


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(16 << 20), b""):
            h.update(b)
    return h.hexdigest()


class Rate:
    def __init__(self):
        self.last = 0.0
        self.n = 0

    def get(self, url, timeout=40):
        dt = time.time() - self.last
        if dt < MIN_SPACING_S:
            time.sleep(MIN_SPACING_S - dt)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "research/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return 200, r.read()
        except urllib.error.HTTPError as e:
            return e.code, b""
        except Exception as e:
            return -1, repr(e)[:160].encode()
        finally:
            self.last = time.time()
            self.n += 1


def list_symbol(rate, sym):
    """every key under this symbol's prefix, following truncation"""
    keys, marker, pages = [], None, 0
    while True:
        url = f"{BUCKET}?delimiter=&prefix={PREFIX}{sym}/"
        if marker:
            url += f"&marker={urllib.request.quote(marker)}"
        code, b = rate.get(url)
        pages += 1
        if code != 200:
            return None, code, pages
        body = b.decode("utf-8", "replace")
        ks = KEY_RE.findall(body)
        szs = SIZE_RE.findall(body)
        keys.extend(zip(ks, szs if len(szs) == len(ks) else ["0"] * len(ks)))
        m = CONT_RE.search(body)
        if m and "<IsTruncated>true</IsTruncated>" in body:
            marker = m.group(1)
            continue
        if "<IsTruncated>true</IsTruncated>" in body and ks:
            marker = ks[-1]          # S3 without NextMarker: continue from the last key
            continue
        return keys, 200, pages


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbols", required=True)
    ap.add_argument("--ledger", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--progress", default=None)
    a = ap.parse_args()

    syms = [l.strip() for l in open(a.symbols) if l.strip()]
    rec = {"device": os.path.basename(os.path.realpath(__file__)),
           "self_sha256": sha(os.path.realpath(__file__)), "argv": sys.argv[1:],
           "python": sys.executable,
           "prereg": "docs/PREREG_D10_funding_truth_audit_stage1_2026-09-25.md @ 496142901",
           "task": "D10 stage 1 question 1 (which months of truth exist) + exact sizing of question 2",
           "source": BUCKET + "/" + PREFIX,
           "rate_discipline": f"sequential, >= {MIN_SPACING_S}s between requests, anonymous public archive only",
           "why_listing_not_probing": ("a month-major probe is 832 x 81 = 67,392 requests, measured at "
                                       "~11 min per 832 requests => ~20 h; one listing per symbol is 832 "
                                       "requests total and yields an exact inventory"),
           "n_symbols_requested": len(syms)}

    rate = Rate()
    inv, failed = {}, {}
    t0 = time.time()
    for i, s in enumerate(syms):
        keys, code, pages = list_symbol(rate, s)
        if keys is None:
            failed[s] = {"http": code, "pages": pages}
            continue
        months = {}
        for k, sz in keys:
            base = k.rsplit("/", 1)[-1]
            m = MONTH_RE.match(base)
            if m and m.group("sym") == s:
                months[m.group("month")] = int(sz)
        inv[s] = {"months": months, "n_months": len(months),
                  "bytes": int(sum(months.values())), "listing_pages": pages}
        if a.progress and (i % 25 == 0 or i == len(syms) - 1):
            DW.write_json(a.progress, {"done": i + 1, "of": len(syms), "requests": rate.n,
                                       "elapsed_s": round(time.time() - t0, 1),
                                       "symbols_with_data": len(inv), "failed": len(failed)}, indent=1, allow_nan=True)

    rec["elapsed_s"] = round(time.time() - t0, 1)
    rec["requests_made"] = rate.n
    rec["symbols_listed_ok"] = len(inv)
    rec["symbols_failed"] = failed
    rec["inventory"] = inv

    pairs = [(s, m) for s, d in inv.items() for m in d["months"]]
    total_bytes = sum(d["bytes"] for d in inv.values())
    per_year = collections.Counter(m[:4] for _, m in pairs)
    rec["archive_symbol_months"] = len(pairs)
    rec["archive_total_bytes"] = total_bytes
    rec["archive_symbol_months_per_year"] = {y: per_year[y] for y in sorted(per_year)}
    rec["download_cost_exact"] = {
        "zips_to_fetch": len(pairs),
        "requests_at_two_per_zip_with_checksum": 2 * len(pairs),
        "seconds_at_min_spacing_only": round(2 * len(pairs) * MIN_SPACING_S, 1),
        "note": ("the spacing floor is a LOWER bound; the measured rate including latency was about "
                 "0.8 s per request, so multiply by roughly four for a realistic figure")}

    # cross-check against the ledger at MONTH granularity: this is not yet event completeness,
    # but it already shows where one side has a month the other does not.
    import numpy as np
    z = np.load(a.ledger, allow_pickle=True)
    ft = z["ft"].astype(np.int64); off = z["off"].astype(np.int64); lsyms = z["symbols"]
    led = collections.defaultdict(set)
    for i in range(len(lsyms)):
        for t in ft[off[i]:off[i + 1]]:
            led[str(lsyms[i])].add(datetime.datetime.fromtimestamp(int(t), datetime.timezone.utc)
                                   .strftime("%Y-%m"))
    led_pairs = {(s, m) for s, ms in led.items() for m in ms}
    arc_pairs = set(pairs)
    only_led = led_pairs - arc_pairs
    only_arc = arc_pairs - led_pairs
    rec["month_granularity_crosscheck"] = {
        "ledger_symbol_months": len(led_pairs), "archive_symbol_months": len(arc_pairs),
        "both": len(led_pairs & arc_pairs),
        "ledger_has_archive_does_not": len(only_led),
        "archive_has_ledger_does_not": len(only_arc),
        "ledger_only_per_year": {y: n for y, n in sorted(collections.Counter(m[:4] for _, m in only_led).items())},
        "archive_only_per_year": {y: n for y, n in sorted(collections.Counter(m[:4] for _, m in only_arc).items())},
        "ledger_only_examples": sorted(only_led)[:15],
        "archive_only_examples": sorted(only_arc)[:15],
        "reading": ("'ledger has, archive does not' includes the current month, which the archive only "
                    "publishes in early M+1, so it is expected to be non-zero for 2026-09 and must be "
                    "read per year rather than pooled")}
    rec["verdict"] = "MEASURED"
    rec["limits"] = ["month granularity only; event-level completeness (question 2) needs the zip contents",
                     "a listing proves a file exists, not that its contents are complete"]
    print("receipt_sha256", DW.write_json(a.out, rec, indent=2, allow_nan=True))

    print("INVENTORY MEASURED")
    print(f"  requests {rate.n} in {rec['elapsed_s']}s   symbols ok {len(inv)}   failed {len(failed)}")
    print(f"  archive symbol-months {len(pairs)}   total {total_bytes/1e6:.1f} MB")
    print(f"  per year: {rec['archive_symbol_months_per_year']}")
    c = rec["month_granularity_crosscheck"]
    print(f"  ledger symbol-months {c['ledger_symbol_months']}  archive {c['archive_symbol_months']}  both {c['both']}")
    print(f"  ledger-only {c['ledger_has_archive_does_not']} per year {c['ledger_only_per_year']}")
    print(f"  archive-only {c['archive_has_ledger_does_not']} per year {c['archive_only_per_year']}")
    print(f"  download cost: {rec['download_cost_exact']['zips_to_fetch']} zips, "
          f"{rec['download_cost_exact']['seconds_at_min_spacing_only']}s at the spacing floor "
          f"(~4x that in practice)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
