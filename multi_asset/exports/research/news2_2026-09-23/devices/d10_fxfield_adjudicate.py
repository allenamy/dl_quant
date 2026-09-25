#!/usr/bin/env python3
"""d10_fxfield_adjudicate.py -- fresh's 5,613 disagreement cells, judged against the exchange archive.

lead's priority target 2026-09-25, ahead of the census year order:
  (1) for the disagreement cells in months whose archive is already fetched and CHECKSUM-verified, judge
      each cell: panel right / ledger right / neither, with a per-cell count table and the top 10 names;
  (2) separately: which source does the LIVE producer's funding leg consume, citing the code line.

FIRST, REPRODUCE A KNOWN NUMBER. lead: "先断言计数等于 5,613". This device recomputes fresh's mismatch set
from their two sources with their comparison (fa_fxfield.py L59-61, L93) and ASSERTS the count is 5,613
before judging anything. A new reading that cannot reproduce the reading it is extending is not trusted.

BOTH SIDES CLAIM THE SAME QUANTITY, which is why the archive can adjudicate at all:
  * panel `f_fund_now` -- r6_panel_splice.py L95-100: pos = searchsorted(ft, tail_ts, "right") - 1, so the
    last event AT OR BEFORE the anchor; fn = fr[pos] is the RAW rate; NaN when anchor - ft > 12h (L98-99).
  * ledger `last_rate` -- fund_replay.npz, built from the producer's own funding_state
    (feature_contract.py:72 funding_state(..., max_age=43200)), i.e. also "last settlement <= anchor, raw
    rate, 12h staleness".
Same claimed quantity, two implementations => a genuine implementation divergence, and the archive's own
per-settlement records decide it.

TRUTH, and where truth is not available: for a cell (symbol, anchor) the archive truth is the raw
`last_funding_rate` of the latest archive settlement with calc_time <= anchor, NaN if that settlement is
more than 12h old. Because the staleness window is 12h, a settlement relevant to an anchor in the first
12h of a month can lie in the PREVIOUS month; if that month's archive is not fetched, the cell is marked
TRUTH_UNAVAILABLE rather than being silently judged as stale. That is the difference between "no
settlement within 12h" and "I did not look".
"""
import argparse, collections, csv, datetime, glob, hashlib, io, json, os, sys, zipfile

import numpy as np

FRESH_S = 43200          # 12h, both sides' staleness window
EXPECT_MISMATCH = 5613   # fresh's count, asserted before any judging


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(16 << 20), b""):
            h.update(b)
    return h.hexdigest()


def iso(t):
    return datetime.datetime.fromtimestamp(int(t), datetime.timezone.utc).strftime("%Y-%m-%dT%H:%MZ")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", required=True)
    ap.add_argument("--replay", required=True)
    ap.add_argument("--zips-root", required=True)
    ap.add_argument("--inventory", required=True,
                    help="D10_S1_ARCHIVE_INVENTORY.json -- gives each symbol's archive coverage window")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    panel_real = os.path.realpath(a.panel)     # fresh's warning: those backup names are symlinks
    rec = {"device": os.path.basename(os.path.realpath(__file__)),
           "self_sha256": sha(os.path.realpath(__file__)), "argv": sys.argv[1:],
           "python": sys.executable, "numpy": np.__version__,
           "task": "lead's priority target: judge fresh's 5,613 disagreement cells against the archive",
           "reproduces": "fanom_2026-09-24/receipts/FA_FXFIELD.json (commit e58ddaf3e), device fa_fxfield.py",
           "panel": {"path_given": a.panel, "resolved": panel_real, "sha256": sha(panel_real)},
           "replay": {"path": a.replay, "sha256": sha(a.replay)},
           "both_sides_claim": {
               "panel": "r6_panel_splice.py L95-100: last event at or before the anchor, RAW rate, NaN if >12h old",
               "ledger": "fund_replay.npz from funding_state(..., max_age=43200) -- the same claimed quantity"},
           "truth": "archive last_funding_rate of the latest settlement <= anchor, NaN if older than 12h"}

    P = np.load(panel_real, allow_pickle=True)
    R = np.load(a.replay, allow_pickle=True)
    pt = P["ts"].astype(np.int64); ft = R["anchors"].astype(np.int64)
    ps = [str(s) for s in P["symbols"]]; rs = [str(s) for s in R["symbols"]]
    ti = np.intersect1d(pt, ft)
    si = [s for s in ps if s in set(rs)]
    pr = np.searchsorted(pt, ti); frr = np.searchsorted(ft, ti)
    pc = [ps.index(s) for s in si]; rc = [rs.index(s) for s in si]
    FN = P["f_fund_now"][np.ix_(pr, pc)]; IV = P["f_fund_iv"][np.ix_(pr, pc)]
    LR = R["last_rate"][np.ix_(frr, rc)]; LIV = R["last_iv"][np.ix_(frr, rc)]
    both = np.isfinite(FN) & np.isfinite(LR)
    bad = both & (FN != LR.astype(np.float32))
    rec["reproduction"] = {"common_anchors": int(ti.size), "common_symbols": len(si),
                           "common_finite_cells": int(both.sum()),
                           "mismatched_cells": int(bad.sum()), "expected": EXPECT_MISMATCH,
                           "matches_fresh": bool(int(bad.sum()) == EXPECT_MISMATCH)}
    assert int(bad.sum()) == EXPECT_MISMATCH, (
        "must reproduce fresh's 5,613 before judging", int(bad.sum()), EXPECT_MISMATCH)

    # ---- archive: only months with a verified manifest ------------------------------------------
    have_months = set()
    arc = collections.defaultdict(list)       # symbol -> [(ts, rate)]
    for mdir in sorted(glob.glob(os.path.join(a.zips_root, "*-*"))):
        month = os.path.basename(mdir)
        if not os.path.exists(os.path.join(mdir, f"MANIFEST_{month}.json")):
            continue
        man = json.load(open(os.path.join(mdir, f"MANIFEST_{month}.json")))["files"]
        if any(v.get("checksum_match") is False for v in man.values()):
            rec.setdefault("months_skipped_checksum", []).append(month); continue
        have_months.add(month)
        for zp in glob.glob(os.path.join(mdir, "*-fundingRate-*.zip")):
            sym = os.path.basename(zp).split("-fundingRate-")[0]
            z = zipfile.ZipFile(zp)
            for row in csv.reader(io.StringIO(z.read(z.namelist()[0]).decode("utf-8"))):
                if row and row[0].strip().isdigit():
                    arc[sym].append((int(round(int(row[0]) / 1000.0)), float(row[2])))
    for s in arc:
        arc[s].sort()
    # A SYMBOL'S archive window, not just "which months I fetched". BDXNUSDT's archive ENDS 2026-03 while
    # the ledger runs to 2026-08, so "no archive settlement within 12h of a 2026-04 anchor" means THE ARCHIVE
    # STOPPED PUBLISHING THAT SYMBOL -- a coverage-window edge, already classified as such in
    # D10_S1_MONTH_COVERAGE.json -- and emphatically NOT "the rate is stale". Without this the stale bucket
    # silently fills with window-edge cells and the device reports "both sides wrong" about cells where it
    # simply has no truth. This is the same error class the month-granularity pass already found once.
    inv = json.load(open(a.inventory))["inventory"]
    sym_window = {s: (lambda ms: (ms[0], ms[-1]) if ms else None)(sorted(d["months"]))
                  for s, d in inv.items()}
    rec["symbol_window_source"] = {"path": a.inventory, "sha256": sha(a.inventory),
                                   "why": "distinguishes 'stale' from 'the archive does not cover this period'"}
    rec["archive_months_available"] = sorted(have_months)
    rec["archive_symbols_loaded"] = len(arc)

    def prev_month(m):
        y, mm = int(m[:4]), int(m[5:7])
        return f"{y-1:04d}-12" if mm == 1 else f"{y:04d}-{mm-1:02d}"

    # ---- judge -----------------------------------------------------------------------------------
    counts = collections.Counter()
    by_name = collections.defaultdict(collections.Counter)
    examples = collections.defaultdict(list)
    rows = np.flatnonzero(bad.any(1))
    for i in rows:
        anchor = int(ti[i])
        month = datetime.datetime.fromtimestamp(anchor, datetime.timezone.utc).strftime("%Y-%m")
        for j in np.flatnonzero(bad[i]):
            s = si[j]
            pv, lv = float(FN[i, j]), float(LR[i, j])
            if month not in have_months:
                counts["TRUTH_UNAVAILABLE_month_not_fetched"] += 1
                by_name[s]["TRUTH_UNAVAILABLE_month_not_fetched"] += 1
                continue
            ev = arc.get(s, [])
            k = None
            for t, r in reversed(ev):
                if t <= anchor:
                    k = (t, r); break
            # a settlement inside the 12h window can live in the previous month
            need_prev = (anchor - datetime.datetime.strptime(month, "%Y-%m")
                         .replace(tzinfo=datetime.timezone.utc).timestamp()) < FRESH_S
            w = sym_window.get(s)
            if k is None or (anchor - k[0] > FRESH_S):
                if w is None or month > w[1] or month < w[0]:
                    counts["TRUTH_UNAVAILABLE_outside_symbol_archive_window"] += 1
                    by_name[s]["TRUTH_UNAVAILABLE_outside_symbol_archive_window"] += 1
                    continue
                if need_prev and prev_month(month) not in have_months:
                    counts["TRUTH_UNAVAILABLE_prev_month_missing"] += 1
                    by_name[s]["TRUTH_UNAVAILABLE_prev_month_missing"] += 1
                    continue
                truth = float("nan")
            else:
                truth = k[1]
            t32 = np.float32(truth)
            pm = (np.float32(pv) == t32) if np.isfinite(truth) else False
            lm = (np.float32(lv) == t32) if np.isfinite(truth) else False
            if not np.isfinite(truth):
                v = "TRUTH_IS_STALE_both_sides_should_be_nan"
            elif pm and not lm:
                v = "PANEL_RIGHT"
            elif lm and not pm:
                v = "LEDGER_RIGHT"
            elif pm and lm:
                v = "IMPOSSIBLE_both_match_but_they_differ"
            else:
                v = "NEITHER"
            counts[v] += 1; by_name[s][v] += 1
            if len(examples[v]) < 12:
                examples[v].append({"symbol": s, "anchor": iso(anchor), "panel": pv, "ledger": lv,
                                    "archive_truth": truth,
                                    "archive_event_utc": iso(k[0]) if k else None,
                                    "panel_iv": float(IV[i, j]), "ledger_iv": float(LIV[i, j])})
    judged = sum(v for k, v in counts.items() if not k.startswith("TRUTH_UNAVAILABLE"))
    rec["verdict_counts"] = dict(counts)
    rec["cells_judged"] = judged
    rec["cells_not_judged"] = int(bad.sum()) - judged
    rec["closure_check"] = {"sum_of_all_buckets": int(sum(counts.values())),
                            "mismatched_cells": int(bad.sum()),
                            "equal": bool(sum(counts.values()) == int(bad.sum()))}
    assert sum(counts.values()) == int(bad.sum()), "every mismatch cell must land in exactly one bucket"
    top = sorted(by_name.items(), key=lambda kv: -sum(kv[1].values()))[:10]
    rec["top10_names"] = [{"symbol": s, "total": sum(c.values()), "by_verdict": dict(c)} for s, c in top]
    rec["examples"] = {k: v for k, v in examples.items()}
    rec["verdict"] = "MEASURED"
    rec["limits"] = ["only cells in months with a CHECKSUM-verified archive are judged; the rest are named "
                     "TRUTH_UNAVAILABLE rather than assumed",
                     "TRUTH_IS_STALE now means the archive COVERS the period and still has no settlement within "
                     "12h; cells after a symbol's last archived month (or before its first) are "
                     "TRUTH_UNAVAILABLE_outside_symbol_archive_window instead",
                     "the archive is treated as truth for the RAW rate; this device does not re-derive intervals"]
    with open(a.out, "w") as f:
        json.dump(rec, f, indent=2)

    print("FXFIELD ADJUDICATION")
    r = rec["reproduction"]
    print(f"  reproduction: {r['mismatched_cells']} mismatches vs fresh's {r['expected']} -> "
          f"matches={r['matches_fresh']}")
    print(f"  archive months available: {rec['archive_months_available']}")
    print(f"  judged {judged} of {int(bad.sum())} cells")
    for k, v in sorted(counts.items(), key=lambda kv: -kv[1]):
        print(f"     {k:44s} {v}")
    print("  top 10 names:")
    for e in rec["top10_names"]:
        print(f"     {e['symbol']:14s} {e['total']:5d}  {e['by_verdict']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
