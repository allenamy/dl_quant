#!/usr/bin/env python3
"""d10_declared_iv_evidence.py -- evidence for lead's s7 ruling 5 (runbook 3c): may the October producer read "a name absent from
/fapi/v1/fundingInfo" as "its declared funding interval is 8h"?

The official description (fetched 2026-09-27 06:3xZ) says the endpoint returns "funding rate info for symbols that had
FundingRateCap/FundingRateFloor / fundingIntervalHours adjustment". It does NOT say that every other symbol is 8h. So the rule is an
inference, and this device tests it against the archive, which records the interval on every settlement row:

  A  names ABSENT from the current response: every settlement row in the latest verified month must have interval 8.
     Expected 0 mismatches; any mismatch is named and falsifies the rule (unless the name is also absent from the current
     exchangeInfo, i.e. delisted -- reported separately, it cannot contradict a rule about listed names).
  B  names PRESENT: the response's fundingIntervalHours vs the interval of the name's last archive row. The archive ends before the
     response was taken, so a disagreement may be a legitimate change after the archive end: reported, not a verdict.
  C  (informational) absent names whose OLDER months show a non-8 interval: adjusted once, reverted since. They are consistent with
     "absent => currently 8" but show that absence does not mean "never adjusted".
Only VERIFIED archive months are read (d10_manifest_gate.require_verified). The response is fetched from pod2 (public market endpoint,
weight 0), and its raw bytes and sha go into the receipt.
usage: d10_declared_iv_evidence.py --zips-root DIR --months 2026-06,2026-07,2026-08 --out OUT.json [--info-file RAW.json]
       d10_declared_iv_evidence.py --selftest
"""
import argparse, csv, hashlib, io, json, os, sys, time, urllib.request, zipfile

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
for _c in (os.path.dirname(os.path.realpath(__file__)),
           os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), "common"),
           os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))), "common")):
    if os.path.exists(os.path.join(_c, "durable_write.py")):
        sys.path.insert(0, _c)
        break
else:
    raise ImportError("common/durable_write.py not found next to or above this device; deploy it with the device")
import durable_write as DW  # every file this device writes goes through it (news2 class fix 2026-09-27)

INFO_URL = "https://fapi.binance.com/fapi/v1/fundingInfo"
EXINFO_URL = "https://fapi.binance.com/fapi/v1/exchangeInfo"


def fetch(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "research/1.0"}), timeout=30) as r:
        return r.read()


def month_rows(zipdir, month):
    """{symbol: [(calc_time_ms, interval_hours_str), ...]} for every zip of a VERIFIED month."""
    import d10_manifest_gate as GATE
    GATE.require_verified(zipdir, month, what="d10_declared_iv_evidence")
    out = {}
    suffix = f"-fundingRate-{month}.zip"
    for n in sorted(os.listdir(zipdir)):
        if not n.endswith(suffix):
            continue
        s = n[: -len(suffix)]
        with zipfile.ZipFile(os.path.join(zipdir, n)) as z:
            rows = [r for r in csv.reader(io.TextIOWrapper(io.BytesIO(z.read(z.namelist()[0])), encoding="utf-8"))
                    if r and r[0].strip().isdigit()]
        out[s] = [(int(r[0]), r[1].strip()) for r in rows]
    return out


def evaluate(info, listed, months_rows):
    """info: {symbol: fundingIntervalHours}; listed: set of currently listed perpetual symbols or None; months_rows: [(month, rows)]
    in chronological order. Returns the A/B/C census."""
    last_month, last = months_rows[-1]
    A_bad, A_bad_delisted, A_checked = [], [], 0
    for s, rows in sorted(last.items()):
        if s in info:
            continue
        A_checked += 1
        bad = sorted({iv for _, iv in rows if float(iv) != 8.0})
        if bad:
            (A_bad_delisted if (listed is not None and s not in listed) else A_bad).append({"symbol": s, "intervals": bad, "rows": len(rows)})
    B_agree, B_diff, B_no_archive = 0, [], []
    for s, iv in sorted(info.items()):
        hist = [r for _, rows in months_rows for r in rows.get(s, [])] if any(s in r for _, r in months_rows) else []
        if not hist:
            B_no_archive.append(s)
            continue
        lastiv = float(sorted(hist)[-1][1])
        if lastiv == float(iv):
            B_agree += 1
        else:
            B_diff.append({"symbol": s, "fundingInfo": iv, "last_archive_iv": lastiv})
    C = []
    for s in sorted(last):
        if s in info:
            continue
        older = sorted({iv for m, rows in months_rows[:-1] for _, iv in rows.get(s, []) if float(iv) != 8.0})
        if older:
            C.append({"symbol": s, "older_non8": older})
    return {"latest_month": last_month,
            "A_absent_names_checked": A_checked, "A_mismatch": A_bad, "A_mismatch_delisted": A_bad_delisted,
            "B_present_names": len(info), "B_agree": B_agree, "B_differ_after_archive_end_possible": B_diff, "B_not_in_archive": B_no_archive,
            "C_absent_but_adjusted_earlier": C,
            "verdict": "RULE_HOLDS_ON_ARCHIVE" if not A_bad else "RULE_FALSIFIED"}


def selftest():
    info = {"XUSDT": 4}
    clean = [("2026-07", {"AUSDT": [(1, "8"), (2, "8")], "XUSDT": [(1, "4")]}),
             ("2026-08", {"AUSDT": [(3, "8")], "BUSDT": [(3, "8")], "XUSDT": [(3, "4")]})]
    r0 = evaluate(info, None, clean)
    bad = [("2026-08", {"AUSDT": [(3, "8")], "BUSDT": [(3, "8"), (4, "4")], "XUSDT": [(3, "4")]})]
    r1 = evaluate(info, None, bad)
    r2 = evaluate(info, {"AUSDT", "XUSDT"}, bad)                         # BUSDT delisted: separated, not a falsification
    reverted = [("2026-07", {"AUSDT": [(1, "4")]}), ("2026-08", {"AUSDT": [(3, "8")], "XUSDT": [(3, "2")]})]
    r3 = evaluate(info, None, reverted)
    cells = {"G_clean_holds": r0["verdict"] == "RULE_HOLDS_ON_ARCHIVE" and r0["B_agree"] == 1,
             "R1_absent_non8_falsifies": r1["verdict"] == "RULE_FALSIFIED" and r1["A_mismatch"][0]["symbol"] == "BUSDT",
             "R2_delisted_separated": r2["verdict"] == "RULE_HOLDS_ON_ARCHIVE" and r2["A_mismatch_delisted"][0]["symbol"] == "BUSDT",
             "R3_reverted_is_C_not_A": r3["verdict"] == "RULE_HOLDS_ON_ARCHIVE" and r3["C_absent_but_adjusted_earlier"][0]["symbol"] == "AUSDT",
             "R4_present_disagreement_is_B": r3["B_differ_after_archive_end_possible"][0]["symbol"] == "XUSDT"}
    ok = all(cells.values())
    print(json.dumps(cells)); print("SELFTEST", "GREEN" if ok else "RED")
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--zips-root"); ap.add_argument("--months"); ap.add_argument("--out")
    ap.add_argument("--info-file", default=None, help="use saved raw fundingInfo bytes instead of fetching")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    t0 = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    raw = open(a.info_file, "rb").read() if a.info_file else fetch(INFO_URL)
    info = {d["symbol"]: d["fundingIntervalHours"] for d in json.loads(raw)}
    exraw = fetch(EXINFO_URL)
    listed = {s["symbol"] for s in json.loads(exraw)["symbols"] if s.get("contractType") == "PERPETUAL" and s.get("status") == "TRADING"}
    months = [m for m in a.months.split(",") if m]
    mr = [(m, month_rows(os.path.join(a.zips_root, m), m)) for m in months]
    rec = {"device": os.path.basename(__file__), "self_sha256": hashlib.sha256(open(os.path.realpath(__file__), "rb").read()).hexdigest(),
           "argv": vars(a), "python": {"version": sys.version.split()[0], "executable": sys.executable},
           "fetched_utc": t0, "fundingInfo": {"url": INFO_URL if not a.info_file else a.info_file, "sha256": hashlib.sha256(raw).hexdigest(),
                                              "n": len(info), "interval_counts": {str(k): sum(1 for v in info.values() if v == k) for k in sorted(set(info.values()))}},
           "exchangeInfo_sha256": hashlib.sha256(exraw).hexdigest(), "listed_perpetual_trading": len(listed),
           "doc_statement": "Query funding rate info for symbols that had FundingRateCap/FundingRateFloor / fundingIntervalHours adjustment",
           "doc_note": "the doc does not state that absent symbols are 8h; this device tests that inference on the archive",
           **evaluate(info, listed, mr)}
    raw_path = a.out.replace(".json", "_fundingInfo_raw.json")
    rec["fundingInfo"]["raw_saved"] = [raw_path, DW.write_bytes(raw_path, raw)]
    print("receipt_sha256", DW.write_json(a.out, rec, indent=1, allow_nan=True))
    print("VERDICT", rec["verdict"], "A_checked", rec["A_absent_names_checked"], "A_mismatch", len(rec["A_mismatch"]),
          "A_delisted", len(rec["A_mismatch_delisted"]), "B_agree", rec["B_agree"], "B_differ", len(rec["B_differ_after_archive_end_possible"]),
          "C", len(rec["C_absent_but_adjusted_earlier"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
