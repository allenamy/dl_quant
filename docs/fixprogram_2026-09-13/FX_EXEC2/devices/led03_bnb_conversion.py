#!/usr/bin/python3
"""LED-03 — convert the BNB commissions of the eight older protective-flatten batches to USDT at the RULED caliber.

WHAT IT TOUCHES. Only `data.binance.vision`, the PUBLIC STATIC archive (the pull the user exempted on 2026-09-05),
plus two local read-only files: the guard_twin income ledger copy and the committed LED-03 proxy receipt. It makes
**no venue API call, uses no credentials, and writes no ledger** — it writes one receipt.

THE CALIBER IS NOT DEFINED HERE. It is `live/bnb_conversion.py` in the executor clone, imported from the tree passed
as argv[1], so the device and whatever eventually consumes the number share ONE definition of
`bnb_spot_1m_close_at_fill` rather than two that agree today.

THE PRICE FILES ARE VERIFIED AGAINST THE PUBLISHER'S OWN CHECKSUM, not only against a sha we computed ourselves.
data.binance.vision publishes a `.CHECKSUM` beside each zip; a sha256 we compute proves only that we hashed what we
downloaded, which is a weaker claim than "this is the file Binance published". Both are recorded.

POSITIVE CONTROL, BEFORE ANY CONVERTED NUMBER IS USED. The BNB commission rows this device selects per batch must sum
to the per-batch BNB total in the committed proxy receipt (`proxy_fee_by_asset_unambiguous.BNB`, device
led03_flatten_fee_proxy.py). If a batch disagrees the device FAILS rather than reporting a converted figure built on
a different row set — a conversion of the wrong rows is still a wrong number, and a tidy one.

THE PERP MARK IS A SENSITIVITY COLUMN. The futures/um BNBUSDT 1m close is carried beside the spot figure and never
substituted for it; the receipt reports the spread so the reader can see how much the choice of venue is worth.

Usage:
  /usr/bin/python3 led03_bnb_conversion.py <executor_tree> <income.jsonl> <LED03_proxy.json> <cache_dir> <out.json>
"""
import calendar
import csv
import hashlib
import io
import json
import os
import sys
import time
import urllib.request
import zipfile

TREE, INCOME, PROXY, CACHE, OUT = sys.argv[1:6]
sys.path.insert(0, os.path.join(TREE, "live"))
import bnb_conversion as BC        # noqa: E402  — the caliber, not re-implemented here

BASE = "https://data.binance.vision/data"
# ★ DAILY files, one per batch DAY, not monthly. The monthly archive for an in-progress month does not exist —
#   2026-09 returns 404 while 2026-08 returns 200 — so a monthly-only device would have silently had no prices for
#   the 09-06 batch, which is the largest BNB one. Daily files also make the provenance exact: the receipt names one
#   archived file per day converted, instead of a month of minutes of which a few were used.
SPOT = BASE + "/spot/daily/klines/BNBUSDT/1m/BNBUSDT-1m-{d}.zip"
PERP = BASE + "/futures/um/daily/klines/BNBUSDT/1m/BNBUSDT-1m-{d}.zip"


def sha(b):
    return hashlib.sha256(b).hexdigest()


def fetch(url, dest):
    """Download once into the cache; afterwards read the cached bytes. Returns (bytes, from_cache)."""
    if os.path.exists(dest):
        return open(dest, "rb").read(), True
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with urllib.request.urlopen(url, timeout=120) as r:
        b = r.read()
    tmp = dest + ".part"
    with open(tmp, "wb") as f:
        f.write(b)
    os.replace(tmp, dest)
    return b, False


def closes_from_zip(raw):
    """{kline open ms: close} from a Binance monthly kline zip. Tolerates the header row some months carry."""
    out = {}
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        name = z.namelist()[0]
        with z.open(name) as fh:
            for row in csv.reader(io.TextIOWrapper(fh, encoding="utf-8")):
                if not row or len(row) < 5:
                    continue
                try:
                    t = int(float(row[0]))
                    c = float(row[4])
                except (TypeError, ValueError):
                    continue                      # header row, or a line we cannot read: skipped, never guessed
                # some months publish microseconds; normalise to ms by magnitude, never by assumption of the month
                if t > 10 ** 14:
                    t //= 1000
                out[(t // 60000) * 60000] = c
    return out


proxy_pre = json.load(open(PROXY))
DAYS = sorted({b["day"] for b in proxy_pre["batches"].values()
               if (b.get("proxy_fee_by_asset_unambiguous") or {}).get("BNB") is not None})
assert DAYS, "no batch carries a BNB proxy fee"

sources, spot_closes, perp_closes = {}, {}, {}
for _d in DAYS:
    dash = f"{_d[:4]}-{_d[4:6]}-{_d[6:8]}"
    for label, url_t, sink in (("spot", SPOT, spot_closes), ("perp_sensitivity", PERP, perp_closes)):
        url = url_t.format(d=dash)
        dest = os.path.join(CACHE, label, os.path.basename(url))
        raw, cached = fetch(url, dest)
        our = sha(raw)
        try:
            csum_raw, _ = fetch(url + ".CHECKSUM", dest + ".CHECKSUM")
            published = csum_raw.decode().split()[0].strip()
        except Exception as e:
            published, csum_raw = None, None
        ok = (published is not None and published.lower() == our.lower())
        sources[f"{label}:{dash}"] = {"url": url, "bytes": len(raw), "sha256_ours": our,
                                   "published_checksum": published,
                                   "matches_published_checksum": ok, "served_from_cache": cached}
        assert published is None or ok, f"{url}: published checksum {published} != ours {our}"
        sink.update(closes_from_zip(raw))

proxy = proxy_pre
inc = [json.loads(l) for l in open(INCOME) if l.strip()]
inc_sha = sha(open(INCOME, "rb").read())
assert inc_sha == proxy.get("income_sha256", inc_sha), "income ledger is not the one the proxy receipt was built on"

bnb_rows = [r for r in inc if r.get("type") == "COMMISSION" and r.get("asset") == "BNB"]
bnb_rows.sort(key=lambda r: r["time"])

out_batches, control = {}, {"checked": 0, "mismatch": []}
for rid, b in sorted(proxy["batches"].items()):
    want = (b.get("proxy_fee_by_asset_unambiguous") or {}).get("BNB")
    if want is None:
        continue
    t0 = calendar.timegm(time.strptime(b["trip_utc"], "%Y-%m-%dT%H:%M:%SZ")) * 1000
    t1 = t0 + int(round(float(b["window_s"]) * 1000))
    rows = [{"commission_bnb": r["income"], "fill_ts_ms": r["time"], "symbol": r.get("symbol"),
             "tranId": r.get("tranId")} for r in bnb_rows if t0 <= r["time"] <= t1]
    got = sum(r["commission_bnb"] for r in rows)
    control["checked"] += 1
    # ★ the selected rows must BE the proxy's rows; the proxy reports magnitudes, the ledger signs them negative
    if abs(abs(got) - abs(float(want))) > 1e-8:
        control["mismatch"].append({"rid": rid, "proxy_bnb": want, "selected_bnb": got, "n_rows": len(rows)})
        continue
    agg = BC.convert_rows(rows, spot_closes, source={"caliber_source": "data.binance.vision spot DAILY klines",
                                                     "days": DAYS})
    sens = BC.convert_rows(rows, perp_closes, source={"caliber_source": "futures/um DAILY klines (SENSITIVITY ONLY)"})
    out_batches[rid] = {
        "day": b["day"], "trip_utc": b["trip_utc"], "window_s": b["window_s"],
        "proxy_bnb": want, "selected_bnb": got, "n_rows": len(rows),
        "usdt_spot_close_at_fill": agg["usdt_total_converted_only"],
        "n_converted": agg["n_converted"], "n_unconverted": agg["n_unconverted"],
        "unconverted_bnb": agg["unconverted_bnb"], "unconverted_by_reason": agg["unconverted_by_reason"],
        "usdt_perp_mark_SENSITIVITY_ONLY": sens["usdt_total_converted_only"],
        "sensitivity_spread_usdt": (agg["usdt_total_converted_only"] - sens["usdt_total_converted_only"]),
        "rows": [{k: r.get(k) for k in ("symbol", "tranId", "fill_ts_ms", "minute_open_ms", "commission_bnb",
                                        "rate_usdt_per_bnb", "usdt", "reason", "caliber")} for r in agg["rows"]],
    }

assert not control["mismatch"], f"positive control failed: {control['mismatch']}"

tot_usdt = sum(v["usdt_spot_close_at_fill"] for v in out_batches.values())
tot_sens = sum(v["usdt_perp_mark_SENSITIVITY_ONLY"] for v in out_batches.values())
tot_unconv = sum(v["unconverted_bnb"] for v in out_batches.values())
rec = {"device": os.path.basename(__file__), "device_sha256": sha(open(os.path.abspath(__file__), "rb").read()),
       "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
       "caliber": BC.CALIBER, "executor_tree": TREE,
       "bnb_conversion_sha256": sha(open(os.path.join(TREE, "live", "bnb_conversion.py"), "rb").read()),
       "income_sha256": inc_sha, "proxy_receipt_sha256": sha(open(PROXY, "rb").read()),
       "price_days": DAYS, "price_sources": sources,
       "n_spot_minutes": len(spot_closes), "n_perp_minutes": len(perp_closes),
       "positive_control": control,
       "totals": {"bnb_selected": sum(v["selected_bnb"] for v in out_batches.values()),
                  "usdt_spot_close_at_fill": tot_usdt,
                  "usdt_perp_mark_SENSITIVITY_ONLY": tot_sens,
                  "sensitivity_spread_usdt": tot_usdt - tot_sens,
                  "unconverted_bnb": tot_unconv},
       "batches": out_batches}
json.dump(rec, open(OUT, "w"), ensure_ascii=False, indent=1)

print(f"caliber {BC.CALIBER} · spot minutes {len(spot_closes)} · perp minutes {len(perp_closes)}")
for k, v in sources.items():
    print(f"  {k:<26} {v['bytes']:>9} B  sha {v['sha256_ours'][:16]}  published-checksum "
          f"{'MATCH' if v['matches_published_checksum'] else 'ABSENT/MISMATCH'}  cached={v['served_from_cache']}")
print(f"positive control: {control['checked']} batches, mismatches {len(control['mismatch'])}")
for rid, v in sorted(out_batches.items()):
    print(f"  {rid:<26} {v['selected_bnb']:+.8f} BNB -> {v['usdt_spot_close_at_fill']:+.6f} USDT "
          f"(converted {v['n_converted']}/{v['n_converted'] + v['n_unconverted']}"
          f"{', unconverted ' + str(v['unconverted_by_reason']) if v['n_unconverted'] else ''}) "
          f"| perp sensitivity {v['usdt_perp_mark_SENSITIVITY_ONLY']:+.6f} "
          f"(spread {v['sensitivity_spread_usdt']:+.6f})")
print(f"TOTAL {rec['totals']['bnb_selected']:+.8f} BNB -> {tot_usdt:+.6f} USDT "
      f"| perp sensitivity {tot_sens:+.6f} (spread {tot_usdt - tot_sens:+.6f}) "
      f"| unconverted {tot_unconv:+.8f} BNB")
print(f"receipt -> {OUT}")
