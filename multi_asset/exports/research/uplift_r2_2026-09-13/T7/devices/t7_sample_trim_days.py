#!/usr/bin/env python3
"""t7_sample_trim_days.py — keep the sample within its 60-day limit: day-candle files were written with the whole 200-day page;
keep only venue days whose [open, open+24h) intersects the window [2026-07-01, 2026-08-30) (Bithumb KST days start 15:00Z).
V4 used only days fully inside the window, so no verification result changes. Old/new sha256 recorded in the manifest. No network."""
import os, json, gzip, csv, calendar, time, hashlib
T7 = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); S = T7 + "/sample"
W0 = calendar.timegm((2026, 7, 1, 0, 0, 0)); W1 = calendar.timegm((2026, 8, 30, 0, 0, 0))
man = json.load(open(S + "/SAMPLE_MANIFEST.json")); log = []
def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()
for k, r in man["krw"].items():
    p = S + "/" + r["file_days"]; old = sha(p)
    with gzip.open(p, "rt") as f:
        rows = list(csv.reader(f))
    hdr, data = rows[0], rows[1:]
    keep = [x for x in data if calendar.timegm(time.strptime(x[0][:19], "%Y-%m-%dT%H:%M:%S")) < W1 and calendar.timegm(time.strptime(x[0][:19], "%Y-%m-%dT%H:%M:%S")) + 86400 > W0]
    with gzip.open(p, "wt", newline="") as f:
        w = csv.writer(f); w.writerow(hdr); [w.writerow(x) for x in keep]
    r["days_trim"] = {"rows_before": len(data), "rows_after": len(keep), "sha256_before": old, "first_open_utc": keep[0][0], "last_open_utc": keep[-1][0]}
    r["sha256_days"] = sha(p); log.append((k, len(data), len(keep)))
man["days_trimmed_by"] = os.path.basename(__file__)
json.dump(man, open(S + "/SAMPLE_MANIFEST.json", "w"), indent=1, ensure_ascii=False)
for x in log: print(x)
