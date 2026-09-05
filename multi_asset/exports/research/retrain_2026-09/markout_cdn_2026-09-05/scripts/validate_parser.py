#!/workspace/venv/bin/python
"""
validate_parser.py -- independent check of markout_cdn.py on 20 random marked rows.

Second implementation on purpose: pure `csv` streaming (no pandas / numpy), re-downloads the
archive, re-verifies its sha256 against marks.json, walks the file in order, and prints the
2 trades before the mark, the mark itself, and the 2 trades after it.  Asserts mark_ts / mark_px
agree with marks.json.  Seeded sample: random.Random(20260905).sample(ok_rows, 20).
"""
import collections
import csv
import datetime as dt
import hashlib
import io
import json
import random
import sys
import urllib.request
import zipfile

ROOT = "/workspace/review_scratch/markout_cdn"
BASE = "https://data.binance.vision/data/futures/um/daily/aggTrades/{sym}/{fname}"
MARK_DELAY_MS, WINDOW_MS = 60_000, 60_000


def iso(ms):
    return dt.datetime.fromtimestamp(ms / 1000, tz=dt.timezone.utc).strftime("%H:%M:%S.%f")[:-3]


def main():
    marks = json.load(open(f"{ROOT}/out/marks.json"))
    rows = json.load(open(f"{ROOT}/input/pending_fills.json"))["rows"]
    ok = [r for r in rows if marks[str(r["trade_id"])]["status"] == "ok"]
    rng = random.Random(20260905)
    sample = rng.sample(ok, 20)
    out = io.StringIO()
    n_agree = 0
    mism = []
    for r in sample:
        tid = str(r["trade_id"])
        m = marks[tid]
        fname = m["source"].split()[-1]
        sym = r["symbol"]
        data = urllib.request.urlopen(BASE.format(sym=sym, fname=fname), timeout=180).read()
        sha = hashlib.sha256(data).hexdigest()
        target = int(round(r["fill_ts"] * 1000)) + MARK_DELAY_MS
        hi = target + WINDOW_MS
        z = zipfile.ZipFile(io.BytesIO(data))
        name = [n for n in z.namelist() if n.endswith(".csv")][0]
        prev = collections.deque(maxlen=2)
        found, after = None, []
        n_seen, last_T, unsorted = 0, -1, 0
        with io.TextIOWrapper(z.open(name), encoding="utf-8", newline="") as f:
            for line in csv.reader(f):
                if line[0] == "agg_trade_id":
                    continue
                T = int(line[5])
                n_seen += 1
                if T < last_T:
                    unsorted += 1
                last_T = T
                if found is None:
                    if T >= target:
                        found = line
                    else:
                        prev.append(line)
                else:
                    after.append(line)
                    if len(after) == 2:
                        break
        if found is not None and int(found[5]) <= hi:
            v_ts, v_px = int(found[5]), float(found[1])
        else:
            v_ts, v_px = None, None
        agree = (v_ts == m["mark_ts"]) and (v_px == m["mark_px"]) and (sha == m["file_sha256"])
        n_agree += int(agree)
        if not agree:
            mism.append(dict(trade_id=tid, csv_ts=v_ts, csv_px=v_px, json_ts=m["mark_ts"], json_px=m["mark_px"],
                             sha_ok=sha == m["file_sha256"]))
        out.write(f"--- trade_id={tid} {sym} {r['side']} {r['order_type']} day={r['day']} fill_ts={r['fill_ts']} "
                  f"({iso(int(round(r['fill_ts']*1000)))}Z) fill_px={r['fill_px']}\n")
        out.write(f"    target={target} ({iso(target)}Z)  window_end={hi} ({iso(hi)}Z)  archive={fname} sha256={sha[:16]}.. "
                  f"{'sha OK' if sha == m['file_sha256'] else 'SHA MISMATCH'}  rows_scanned={n_seen} unsorted_steps={unsorted}\n")
        out.write(f"    {'':6} {'agg_trade_id':>12} {'price':>12} {'qty':>12} {'transact_time':>14} {'utc':>12} {'lag_vs_target_s':>16}\n")
        for tag, line in [("before", x) for x in prev] + [("MARK", found)] + [("after", x) for x in after]:
            if line is None:
                out.write(f"    {tag:6} (none)\n")
                continue
            T = int(line[5])
            out.write(f"    {tag:6} {line[0]:>12} {line[1]:>12} {line[2]:>12} {T:>14} {iso(T):>12} {(T-target)/1000:>16.3f}\n")
        out.write(f"    csv-impl: mark_ts={v_ts} mark_px={v_px} | marks.json: mark_ts={m['mark_ts']} mark_px={m['mark_px']} "
                  f"lag={m['mark_lag_s']} -> {'AGREE' if agree else 'MISMATCH'}\n\n")
    summary = dict(n_checked=len(sample), n_agree=n_agree, mismatches=mism, seed=20260905,
                   sample_trade_ids=[str(r["trade_id"]) for r in sample])
    out.write(f"SUMMARY: {n_agree}/{len(sample)} agree (mark_ts, mark_px, archive sha256)\n")
    with open(f"{ROOT}/out/validation_20rows.txt", "w") as f:
        f.write(out.getvalue())
    with open(f"{ROOT}/out/validation_summary.json", "w") as f:
        json.dump(summary, f, indent=1)
    sys.stdout.write(out.getvalue())


if __name__ == "__main__":
    main()
