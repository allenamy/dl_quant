#!/usr/bin/env python3
"""t7_pull_checks.py — completeness checks C0–C6 (rules frozen in <root>/plan/PULL_PLAN_FROZEN.json 'checks'); no returns computed.
Also writes compact derived arrays for the guards (<root>/derived/<venue>/<market>_60m.npz: open_s, close, volume; <root>/derived/binance/<SYM>.npz: open_s, close).
Output: <root>/checks/CHECKS_T7_pull.json and <root>/checks/rows_<venue>.jsonl (one row per market-unit)."""
import os, sys, json, gzip, hashlib, calendar, time, collections, argparse, io, zipfile, csv
import numpy as np
ap = argparse.ArgumentParser(); ap.add_argument("--root", required=True); A = ap.parse_args(); ROOT = A.root
_pb = open(ROOT + "/plan/PULL_PLAN_FROZEN.json", "rb").read(); assert hashlib.sha256(_pb).hexdigest() == open(ROOT + "/plan/PULL_PLAN_FROZEN.json.sha256").read().split()[0]
PLAN = json.loads(_pb); PULL_END, CUTOFF = PLAN["pull_end_epoch"], PLAN["cutoff_epoch"]
for d in ("checks", "derived/upbit", "derived/bithumb", "derived/binance"): os.makedirs(ROOT + "/" + d, exist_ok=True)
def ep(s): return calendar.timegm(time.strptime(s[:19], "%Y-%m-%dT%H:%M:%S"))
def iso(t): return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t))
def sha(b): return hashlib.sha256(b).hexdigest()
def jl(p):
    out = []
    if os.path.exists(p):
        for line in open(p):
            line = line.strip()
            if line:
                try: out.append(json.loads(line))
                except json.JSONDecodeError: out.append({"_torn_line": True})
    return out
OUT = {"device": os.path.basename(__file__), "run_utc": iso(time.time()), "plan_sha256": hashlib.sha256(_pb).hexdigest(), "mode": PLAN["mode"], "venues": {}}
OFFSET = {"upbit": 0, "bithumb": 15 * 3600}
for V in ("upbit", "bithumb"):
    man = jl(ROOT + "/manifest/pages_%s.jsonl" % V); done = {}; errs = jl(ROOT + "/manifest/errors_%s.jsonl" % V)
    for d in jl(ROOT + "/manifest/done_%s.jsonl" % V):
        if "market" in d: done[(d["market"], d["unit"])] = d
    bypu = collections.defaultdict(list)
    for p in man:
        if "market" in p: bypu[(p["market"], p["unit"])].append(p)
    listed_files = set(p["file"] for p in man if "file" in p)
    orphan = 0
    vdir = ROOT + "/" + V
    if os.path.isdir(vdir):
        for dp, dn, fn in os.walk(vdir):
            for f in fn:
                rel = os.path.relpath(os.path.join(dp, f), ROOT)
                if rel not in listed_files: orphan += 1
    rows = []; S = collections.Counter(); fails = collections.defaultdict(list)
    for m in PLAN["krw"][V]:
        mk, first = m["market"], m["first_day_epoch"]; bars = {}
        for unit in ("60m", "days"):
            pages = sorted(bypu.get((mk, unit), []), key=lambda p: -p["to_epoch"])
            r = {"venue": V, "market": mk, "unit": unit, "done_reason": done.get((mk, unit), {}).get("reason"), "n_pages": len(pages)}
            # C0 integrity + load bars
            c0_bad = 0; dup = 0; data = {}
            for p in pages:
                fp = ROOT + "/" + p["file"]
                if not os.path.exists(fp): c0_bad += 1; continue
                raw = gzip.decompress(open(fp, "rb").read())
                js = json.loads(raw.decode())
                if sha(raw) != p["body_sha256"] or len(js) != p["n"]: c0_bad += 1
                for c in js:
                    o = ep(c["candle_date_time_utc"])
                    if o in data: dup += 1
                    data[o] = (float(c["trade_price"]), float(c["candle_acc_trade_volume"]))
            r["C0_bad_pages"] = c0_bad; r["n_bars"] = len(data); r["dup_bars"] = dup
            # C2 seams
            seam_bad = 0
            if pages and pages[0]["to_epoch"] != PULL_END: seam_bad += 1
            for k in range(1, len(pages)):
                if pages[k]["to_epoch"] != pages[k - 1]["oldest_open"] or pages[k]["newest_open"] >= pages[k - 1]["oldest_open"]: seam_bad += 1
            r["C2_seam_breaks"] = seam_bad
            # C1 earliest
            if data:
                e = min(data); r["earliest_utc"] = iso(e); r["newest_utc"] = iso(max(data))
                if unit == "60m": r["C1_ok"] = (first <= e < first + 86400) if first >= CUTOFF else (e < CUTOFF)
                else: r["C1_ok"] = (e == first) if first >= CUTOFF - 86400 else (e < CUTOFF - 86400)
            else:
                r["C1_ok"] = False
            bars[unit] = data; rows.append(r)
            if r["done_reason"] is None: fails["NOT_DONE"].append("%s %s" % (mk, unit))
            if c0_bad: fails["C0"].append("%s %s" % (mk, unit))
            if dup: fails["DUP"].append("%s %s" % (mk, unit))
            if seam_bad: fails["C2"].append("%s %s" % (mk, unit))
            if not r["C1_ok"]: fails["C1"].append("%s %s" % (mk, unit))
        # C3 volume identity + C4 freshness (per market, needs both units)
        h, dd = bars.get("60m", {}), bars.get("days", {})
        lo = max(first, CUTOFF); off = OFFSET[V]
        hsum = collections.defaultdict(float)
        for o, (_, vol) in h.items():
            d0 = ((o - off) // 86400) * 86400 + off; hsum[d0] += vol
        keys = set(k for k in dd if k >= lo and k + 86400 <= PULL_END) | set(k for k in hsum if k >= lo and k + 86400 <= PULL_END)
        tiers = collections.Counter(); worst = 0.0; ex = []
        for d0 in sorted(keys):
            hv = hsum.get(d0); dv = dd.get(d0, (None, None))[1]
            if hv is None or dv is None: tiers["MISMATCH"] += 1; ex.append([iso(d0), hv, dv]); continue
            rel = abs(hv - dv) / max(abs(dv), 1e-12) if (hv or dv) else 0.0; worst = max(worst, rel)
            t = "EXACT" if rel <= 1e-9 else ("ROUNDING" if rel <= 1e-6 else "MISMATCH"); tiers[t] += 1
            if t == "MISMATCH" and len(ex) < 5: ex.append([iso(d0), hv, dv])
        c3 = {"venue": V, "market": mk, "unit": "C3", "days_checked": len(keys), **{k: tiers.get(k, 0) for k in ("EXACT", "ROUNDING", "MISMATCH")}, "max_rel": worst, "examples": ex[:5]}
        if h:
            newest = max(h)
            if newest == PULL_END - 3600: c4 = "FRESH"
            else: c4 = "STALE_MISSING" if any(k > newest and k + 86400 <= PULL_END and v[1] > 0 for k, v in dd.items()) else "THIN_OK"
        else: c4 = "NO_BARS"
        c3["C4_freshness"] = c4; rows.append(c3)
        S["days_checked"] += len(keys); S["EXACT"] += tiers.get("EXACT", 0); S["ROUNDING"] += tiers.get("ROUNDING", 0); S["MISMATCH"] += tiers.get("MISMATCH", 0); S["C4_" + c4] += 1
        if tiers.get("MISMATCH"): fails["C3"].append(mk)
        if c4 in ("STALE_MISSING", "NO_BARS"): fails["C4"].append(mk)
        if h:
            oo = np.array(sorted(h), dtype=np.int64)
            np.savez_compressed(ROOT + "/derived/%s/%s_60m.npz" % (V, mk), open_s=oo, close=np.array([h[o][0] for o in oo]), volume=np.array([h[o][1] for o in oo]))
    with open(ROOT + "/checks/rows_%s.jsonl" % V, "w") as f:
        for r in rows: f.write(json.dumps(r) + "\n")
    # C5 http accounting
    st = collections.Counter(); sends = []; n429 = 0
    for l in jl(ROOT + "/logs/http_%s.jsonl" % V):
        if "status" not in l: continue
        st[str(l["status"])] += 1; n429 += l["status"] == 429
        t = l["utc"]; sends.append(calendar.timegm(time.strptime(t[:19], "%Y-%m-%dT%H:%M:%S")) + int(t[20:23]) / 1000.0)
    sends.sort(); mx = 0; j = 0
    for i in range(len(sends)):
        while sends[i] - sends[j] >= 1.0: j += 1
        mx = max(mx, i - j + 1)
    not_done_units = set("%s %s" % (mk, u) for m in PLAN["krw"][V] for mk in [m["market"]] for u in ("60m", "days") if (mk, u) not in done)
    unresolved = [e for e in errs if "market" in e and "%s %s" % (e["market"], e.get("unit")) in not_done_units]
    empties = collections.Counter(d["reason"] for d in done.values())
    OUT["venues"][V] = {"n_markets": len(PLAN["krw"][V]), "n_market_units": 2 * len(PLAN["krw"][V]), "n_done": len(done), "done_reasons": dict(empties),
                        "n_manifest_pages": sum(1 for p in man if "market" in p), "n_manifest_torn_lines": sum(1 for p in man if p.get("_torn_line")), "n_orphan_files": orphan, "C3_C4": dict(S), "fail_lists": {k: v for k, v in fails.items()},
                        "fail_counts": {k: len(v) for k, v in fails.items()},
                        "C5": {"attempts_by_status": dict(st), "n_429": n429, "max_sends_in_any_1s": mx, "rate_ok": mx <= 5, "n_error_records": len(errs),
                               "error_kinds": dict(collections.Counter(e.get("kind") for e in errs)), "n_unresolved_error_records": len(unresolved)}}
# C6 binance
man = jl(ROOT + "/manifest/pages_binance.jsonl"); last = {}
for r in man:
    if "symbol" in r: last[(r["symbol"], r["month"])] = r
c6 = collections.Counter(); flags = collections.defaultdict(list); nrows = 0
for b in PLAN["binance"]:
    sym = b["symbol"]; ef, el = b["elig_first_utc"][:7], b["elig_last_utc"][:7]; oo = []; cc = []
    for mth in b["months"]:
        r = last.get((sym, mth))
        if r is None: c6["MISSING_NO_RECORD"] += 1; flags["MISSING_NO_RECORD"].append("%s %s" % (sym, mth)); continue
        if r["status"] == "NOT_FOUND":
            c6["NOT_FOUND"] += 1
            if ef <= mth <= el: flags["FLAG_MISSING_INDEX"].append("%s %s" % (sym, mth))
            continue
        c6["OK"] += 1
        good = r["header"] and r["ms_units"] and r["contiguous"] and r["close_time_ok"]
        if not good: flags["FORMAT_FAIL"].append("%s %s" % (sym, mth))
        if r["n_rows"] != r["expected_rows_full_month"]: flags["PARTIAL_MONTH"].append("%s %s rows %d/%d" % (sym, mth, r["n_rows"], r["expected_rows_full_month"]))
        fp = ROOT + "/" + r["file"]; body = open(fp, "rb").read()
        if sha(body) != r["zip_sha256"]: flags["C0_ZIP_SHA"].append("%s %s" % (sym, mth)); continue
        zf = zipfile.ZipFile(io.BytesIO(body)); rows_ = list(csv.reader(io.StringIO(zf.read(zf.namelist()[0]).decode())))
        data = rows_[1:] if not rows_[0][0].strip().isdigit() else rows_
        oo += [int(x[0]) // 1000 for x in data]; cc += [float(x[4]) for x in data]; nrows += len(data)
    if oo:
        o = np.array(oo, dtype=np.int64); srt = np.argsort(o); o = o[srt]; c = np.array(cc)[srt]
        if len(np.unique(o)) != len(o): flags["DUP_HOURS"].append(sym)
        np.savez_compressed(ROOT + "/derived/binance/%s.npz" % sym, open_s=o, close=c)
st = collections.Counter(); sends = []
for l in jl(ROOT + "/logs/http_binance.jsonl"):
    if "status" not in l: continue
    st[str(l["status"])] += 1; t = l["utc"]; sends.append(calendar.timegm(time.strptime(t[:19], "%Y-%m-%dT%H:%M:%S")) + int(t[20:23]) / 1000.0)
sends.sort(); mx = 0; j = 0
for i in range(len(sends)):
    while sends[i] - sends[j] >= 1.0: j += 1
    mx = max(mx, i - j + 1)
errs = jl(ROOT + "/manifest/errors_binance.jsonl")
OUT["binance"] = {"n_symbol_months_planned": sum(len(b["months"]) for b in PLAN["binance"]), "status_counts": dict(c6), "n_rows_loaded": nrows,
                  "flags": {k: v for k, v in flags.items()}, "flag_counts": {k: len(v) for k, v in flags.items()},
                  "C5": {"attempts_by_status": dict(st), "max_sends_in_any_1s": mx, "rate_ok": mx <= 5, "n_error_records": len(errs),
                         "error_kinds": dict(collections.Counter(e.get("kind") for e in errs))}}
OUT["exits"] = {v: jl(ROOT + "/run/exits_%s.jsonl" % v) for v in ("upbit", "bithumb", "binance")}
OUT["controls"] = {v: [{"run_id": c.get("run_id"), "ok": c.get("ok")} for c in jl(ROOT + "/run/controls_%s.jsonl" % v)] for v in ("upbit", "bithumb", "binance")}
json.dump(OUT, open(ROOT + "/checks/CHECKS_T7_pull.json", "w"), indent=1)
for V in ("upbit", "bithumb"):
    x = OUT["venues"][V]; print(V, "done", x["n_done"], "/", x["n_market_units"], "pages", x["n_manifest_pages"], "orphans", x["n_orphan_files"], "C3C4", x["C3_C4"], "fails", x["fail_counts"], "C5", {k: x["C5"][k] for k in ("n_429", "max_sends_in_any_1s", "n_error_records", "n_unresolved_error_records")})
print("binance", OUT["binance"]["status_counts"], OUT["binance"]["flag_counts"], OUT["binance"]["C5"]["max_sends_in_any_1s"])
