#!/usr/bin/env python3
"""d10_live_ledger_vs_archive.py -- does the LIVE producer's ledger ingest the 1h spike settlements?

lead's priority 2026-09-25, ahead of everything else: the replayed ledger was missing the 1h settlements
that the venue inserts during a funding spike. The live funding leg's EMA (fe_v) and RN8 both come from
the LIVE ledger, and spike names are exactly the names that leg shorts, so the same defect in the live
path would be a live problem, not a backtest one. 12 cells was too small a sample to answer it.

CORRECTION 2026-09-25 (the paragraph above is left as written; this device's own MEASUREMENT is unaffected):
"the replayed ledger was missing the 1h settlements" is RETRACTED -- refuted by fresh. The 1h settlements
were IN that ledger. The real cause is the exp_iv skip gate self-locking from a cold start
(shadow_loop_v3.py:456, sha 6080073964bffc..., no _bulk_ok term), so the as-of never advanced past the
settlement that triggered the switch: the rows were present and never read. This device asks a DIFFERENT
and still-open question -- whether the LIVE ledger ingests those settlements -- and it answers that by
measurement, so its numbers stand on their own. Receipt:
receipts/d10_2026-09-25/D10_ROOTCAUSE_last_rate_CORRECTION_2026-09-25.json

THE LIVE LEDGER, cited:
  shadow_loop_v3.py:346  lg = json.load(open(f"{BUNDLE}/funding_ledger_seed.json"))   # cold-start seed
  shadow_loop_v3.py:376  self.ema = aux["ema"]; self.ledger = aux["ledger_tail"]      # warm state
  shadow_loop_v3.py:645  fx.get("/fapi/v1/fundingRate", startTime=(last_ts+1)*1000,
                                endTime=anchor*1000+999, limit=100)                   # live fetch
  shadow_loop_v3.py:654  led, _est, _n = NC.ingest_settlements(led, st.ema.get(s), _ev)
  shadow_loop_v3.py:421  "ledger_tail": {s: r[-400:] for s, r in self.ledger.items()} # rolling 400 rows
So the live path fetches EVERY settlement the venue returns between the last known one and the anchor,
which structurally should include 1h settlements. Reading the code shows intent; this device measures it.

TWO POPULATION GUARDS, without which truncation and coverage masquerade as missing data:
  1. the live tail keeps only the last 400 rows PER SYMBOL, so a symbol whose tail begins mid-August
     legitimately has no earlier August rows. Each symbol is compared only from its OWN earliest live
     row onward; archive events before that are counted separately as OUT_OF_LIVE_TAIL_WINDOW.
  2. the archive month boundary: a switch window can straddle 2026-08-01, so the live slice was
     extracted with a 24h margin and archive events outside the fetched month are not counted as absent.
"""
import argparse, collections, csv, datetime, glob, hashlib, io, json, os, sys, zipfile

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
import d10_manifest_gate as GATE   # R25-11: checksum_match must be True, set equality, per-file re-hash
for _c in (os.path.dirname(os.path.realpath(__file__)),
           os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), "common"),
           os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))), "common")):
    if os.path.exists(os.path.join(_c, "durable_write.py")):
        sys.path.insert(0, _c)
        break
else:
    raise ImportError("common/durable_write.py not found next to or above this device; deploy it with the device")
import durable_write as DW  # every file this device writes goes through it (news2 class fix 2026-09-27)

WINDOW_S = 24 * 3600


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
    ap.add_argument("--live", required=True)
    ap.add_argument("--zips", required=True, help="the 2026-08 zip dir")
    ap.add_argument("--month", default="2026-08")
    ap.add_argument("--mask", required=True)
    ap.add_argument("--crypto-axis", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    L = json.load(open(a.live))
    rec = {"device": os.path.basename(os.path.realpath(__file__)),
           "self_sha256": sha(os.path.realpath(__file__)), "argv": sys.argv[1:],
           # the archive gate is load-bearing for every number below it, so the receipt names
           # WHICH gate signed it (R25-11): a conclusion and its judging device share a lifetime.
           "gate_sha256": sha(os.path.realpath(GATE.__file__)),
           "python": sys.executable, "numpy": np.__version__,
           "task": "lead: does the LIVE ledger ingest the 1h spike settlements",
           "live_ledger": {"extract": a.live, "extract_sha256": sha(a.live),
                           "source": L["source"], "source_sha256": L["source_sha256"],
                           "window": L["extracted_window"],
                           "n_symbols": L["n_symbols"], "n_rows": L["n_rows"]},
           "live_lineage_cited": {
               "warm_state": "shadow_loop_v3.py:376 self.ledger = aux['ledger_tail']",
               "live_fetch": "shadow_loop_v3.py:645 /fapi/v1/fundingRate startTime=(last_ts+1)*1000 endTime=anchor*1000+999 limit=100",
               "ingest": "shadow_loop_v3.py:654 NC.ingest_settlements(led, ema, _ev)",
               "truncation": "shadow_loop_v3.py:421 ledger_tail keeps r[-400:] per symbol"},
           "guards": ["per-symbol comparison starts at that symbol's own earliest live row (400-row truncation)",
                      "archive events outside the fetched month are not counted as absent"]}

    live = {s: sorted((int(r[0]), float(r[1])) for r in v) for s, v in L["ledger_tail"].items()}
    live_ts = {s: {t for t, _ in v} for s, v in live.items()}
    live_start = {s: min(t for t, _ in v) for s, v in live.items() if v}

    # archive 2026-08, with the per-settlement interval
    man = os.path.join(a.zips, f"MANIFEST_{a.month}.json")
    # R25-11: checksum_match must be True for every zip-bearing entry, the disk set must equal the
    # manifest's, and every zip is re-hashed here and now -- a file edited after the pull is caught.
    gv = GATE.require_verified(a.zips, a.month, what=f"live-ledger-vs-archive {a.month}")
    rec["archive_gate"] = {k: gv[k] for k in ("verdict", "n_entries", "n_zip_entries", "n_on_disk",
                                              "n_404", "n_rehashed", "manifest_sha256")}
    arc = {}
    for zp in sorted(glob.glob(os.path.join(a.zips, "*-fundingRate-*.zip"))):
        s = os.path.basename(zp).split("-fundingRate-")[0]
        z = zipfile.ZipFile(zp)
        ev = []
        for row in csv.reader(io.StringIO(z.read(z.namelist()[0]).decode("utf-8"))):
            if row and row[0].strip().isdigit():
                ev.append((int(round(int(row[0]) / 1000.0)), float(row[1]), float(row[2])))
        ev.sort()
        arc[s] = ev
    rec["archive"] = {"month": a.month, "symbols": len(arc),
                      "events": int(sum(len(v) for v in arc.values())),
                      "manifest_sha256": sha(man)}

    mo_lo = datetime.datetime.strptime(a.month, "%Y-%m").replace(tzinfo=datetime.timezone.utc).timestamp()
    mo_hi = (datetime.datetime.strptime(a.month, "%Y-%m").replace(tzinfo=datetime.timezone.utc)
             + datetime.timedelta(days=32)).replace(day=1).timestamp()

    # interval-switch events in the archive, and their +/-24h windows
    switches = collections.defaultdict(list)
    for s, ev in arc.items():
        for i in range(1, len(ev)):
            if ev[i][1] != ev[i - 1][1]:
                switches[s].append((ev[i][0], ev[i - 1][1], ev[i][1]))
    rec["interval_switches"] = {"symbols_with_a_switch": len(switches),
                                "switch_events": int(sum(len(v) for v in switches.values())),
                                "top_symbols": sorted(((len(v), s) for s, v in switches.items()),
                                                      reverse=True)[:10]}

    # member mask at the anchor covering each settlement
    mk = np.load(a.mask, allow_pickle=False)
    A = mk["ts"].astype(np.int64); msk = np.asarray(mk["mask"], bool)
    msyms = [str(x) for x in mk["symbols"]]
    cry = np.asarray(np.load(a.crypto_axis, allow_pickle=False)["crypto"], bool)
    midx = {s: i for i, s in enumerate(msyms)}

    def was_member(s, t):
        j = midx.get(s)
        if j is None or not cry[j]:
            return False
        i = int(np.searchsorted(A, t, side="left"))      # the first anchor at/after the settlement
        if i >= A.size:
            return False
        return bool(msk[i, j])

    counts = collections.Counter()
    by_name = collections.Counter()
    missing_examples = []
    for s, sw in switches.items():
        ev = arc[s]
        ls = live_start.get(s)
        for t0, iv_from, iv_to in sw:
            lo, hi = t0 - WINDOW_S, t0 + WINDOW_S
            for t, ivh, rate in ev:
                if not (lo <= t <= hi):
                    continue
                if not (mo_lo <= t < mo_hi):
                    counts["outside_fetched_month"] += 1; continue
                if s not in live:
                    counts["symbol_absent_from_live_tail"] += 1; continue
                if ls is None or t < ls:
                    counts["out_of_live_tail_window_400row_truncation"] += 1; continue
                if t in live_ts[s]:
                    counts["present_in_live"] += 1
                else:
                    counts["ABSENT_FROM_LIVE"] += 1
                    by_name[s] += 1
                    if was_member(s, t):
                        counts["ABSENT_and_was_a_book_member"] += 1
                    if len(missing_examples) < 40:
                        missing_examples.append({"symbol": s, "utc": iso(t), "archive_iv_h": ivh,
                                                 "archive_rate": rate, "switch_at": iso(t0),
                                                 "switch": f"{iv_from}->{iv_to}",
                                                 "was_member": was_member(s, t)})
    rec["counts_in_switch_windows"] = dict(counts)
    comparable = counts["present_in_live"] + counts["ABSENT_FROM_LIVE"]
    rec["comparable_events"] = comparable
    rec["absent_rate_pct"] = round(100.0 * counts["ABSENT_FROM_LIVE"] / comparable, 4) if comparable else None
    rec["absent_by_name_top20"] = by_name.most_common(20)
    rec["absent_examples"] = missing_examples
    rec["verdict"] = ("LIVE_LEDGER_COMPLETE_IN_SWITCH_WINDOWS" if counts["ABSENT_FROM_LIVE"] == 0
                      else "LIVE_LEDGER_MISSING_SETTLEMENTS_IN_SWITCH_WINDOWS")
    rec["limits"] = ["one month (2026-08) and only +/-24h around interval switches, per lead's scoping",
                     "the live tail is a rolling 400 rows, so coverage is per-symbol and is guarded, not assumed",
                     "membership is evaluated at the first anchor at or after the settlement"]
    print("receipt_sha256", DW.write_json(a.out, rec, indent=2, allow_nan=True))

    print("LIVE LEDGER vs ARCHIVE, +/-24h around interval switches, " + a.month)
    print(f"  archive: {rec['archive']['symbols']} symbols, {rec['archive']['events']} events")
    print(f"  switches: {rec['interval_switches']['switch_events']} in "
          f"{rec['interval_switches']['symbols_with_a_switch']} symbols")
    for k, v in sorted(counts.items(), key=lambda kv: -kv[1]):
        print(f"     {k:46s} {v}")
    print(f"  comparable {comparable}   ABSENT rate {rec['absent_rate_pct']}%")
    print(f"  VERDICT {rec['verdict']}")
    if by_name:
        print(f"  worst names: {by_name.most_common(10)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
