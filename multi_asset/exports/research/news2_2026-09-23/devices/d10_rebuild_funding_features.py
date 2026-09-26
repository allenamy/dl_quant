#!/usr/bin/env python3
"""d10_rebuild_funding_features.py -- line D (1): rebuild fund_now / fund_ema / rn8 / iv under the D10 rule.

Criteria: lead's DECISION_RULE_D10_stage2_2026-09-26.md §1 + revision 1 (millisecond event key).
Design:   docs/DESIGN_D10_lineD_prep_2026-09-26.md §1.

SOURCE-AGNOSTIC BY CONSTRUCTION. The truth comes through the MsLedger interface below, because lead's choice
between (a) rebuilding P2 with millisecond keys, (b) reading zip u API directly, and (c) keeping second keys is
still open. Measured facts behind that choice, all of them pinned here so the device cannot be pointed at a
source that silently lacks what it needs:

  P2 ledger_full.npz   ft is SECONDS (max 1788228000). Sub-second information is IRRECOVERABLE from it, so it
                       CANNOT back a millisecond-keyed rebuild. P2Seconds below refuses rather than rounding.
  monthly archive zip  calc_time in MILLISECONDS, plus funding_interval_hours -> ms AND declared interval
  fund_aug.json.gz     rates as [ms, rate] in MILLISECONDS, 2,474,251 rows, 1,092,526 with a non-zero ms part.
                       Its `intervals` key EXISTS BUT IS EMPTY (len 0), so the API side supplies NO declared
                       interval. Checked rather than assumed, in both directions.

CONSEQUENCE, and it is a SOURCE limit not a path limit: interval_d10's declared fallback (first event of a
symbol, or a gap > 24h) can only be filled from a zip. Zips are published for the whole 2022-06..2026-08 range,
so that range is fully coverable; SEPTEMBER's zip is unpublished until early October, which is why §1.4 of the
design leaves it as an interface rather than inventing a substitute.

The interval rule is IMPORTED from common/funding_interval.py. It is not reimplemented: "using the frozen
caliber" only holds when the code is called.

Modes:
  --interface-check   validate a source against the interface and report its resolution/coverage. No features.
  --rebuild           produce the four columns. Requires a millisecond-capable source.
"""
import argparse
import collections
import csv
import datetime
import glob
import gzip
import hashlib
import io
import json
import os
import sys
import zipfile

import numpy as np

for _c in (os.path.dirname(os.path.realpath(__file__)),
           os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), "common"),
           os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))), "common")):
    if os.path.exists(os.path.join(_c, "funding_interval.py")):
        sys.path.insert(0, _c)
        break
else:
    raise ImportError("common/funding_interval.py not found; this device must not reimplement interval_d10")
import funding_interval as FI

FRESH_S = 43200          # nc_contract.py:21 -- imported value would be better; pinned with its citation


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for c in iter(lambda: fh.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def iso(ms):
    return datetime.datetime.fromtimestamp(int(ms) / 1000.0, datetime.timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%S.%fZ")


class MsLedger:
    """events(symbol) -> [(ft_ms, rate, declared_iv|None)], strictly increasing in ft_ms."""
    name = "abstract"
    resolution = None

    def symbols(self):
        raise NotImplementedError

    def events(self, symbol):
        raise NotImplementedError

    def provenance(self):
        return {"source": self.name, "resolution": self.resolution}


class P2Seconds(MsLedger):
    """P2 ledger_full.npz. Present so that option (c) is an explicit decision and never an accident."""
    name = "P2 ledger_full.npz"
    resolution = "SECONDS"

    def __init__(self, path, allow_seconds=False):
        self.path, self.sha256 = path, sha(path)
        if not allow_seconds:
            raise RuntimeError(
                "P2 ledger_full.npz stores ft in SECONDS, so it cannot back a millisecond-keyed rebuild: the "
                "sub-second information was discarded by p2_prep_inputs.py's t_ms // 1000 and is not "
                "recoverable from this artifact. Pass allow_seconds=True only if lead has chosen option (c), "
                "in which case the 2 measured lost settlements (MSFTUSDT 2026-05-21, AAPLUSDT 2026-05-11) "
                "remain lost and nothing will detect the next such pair.")
        Z = np.load(path, allow_pickle=True)
        self.off, self.ft = Z["off"].astype(np.int64), Z["ft"].astype(np.int64)
        self.rate = Z["rate"].astype(np.float64)
        self.zip_iv = Z["zip_iv"].astype(np.float64)
        self.syms = [str(s) for s in Z["symbols"]]
        self.idx = {s: j for j, s in enumerate(self.syms)}

    def symbols(self):
        return list(self.syms)

    def events(self, symbol):
        j = self.idx.get(symbol)
        if j is None:
            return []
        a, b = int(self.off[j]), int(self.off[j + 1])
        out = []
        for k in range(a, b):
            d = float(self.zip_iv[k])
            out.append((int(self.ft[k]) * 1000, float(self.rate[k]), d if np.isfinite(d) else None))
        return out


class ZipApiUnion(MsLedger):
    """Monthly archive zips (ms + declared interval) unioned with fund_aug (ms, NO interval) by ft_ms."""
    name = "monthly zips u fund_aug (by ft_ms)"
    resolution = "MILLISECONDS"

    def __init__(self, zips_root, months, api_gz=None):
        self.zips_root, self.months, self.api_gz = zips_root, list(months), api_gz
        self.by_sym = collections.defaultdict(dict)       # sym -> {ft_ms: (rate, declared_iv|None)}
        self.stats = collections.Counter()
        for m in self.months:
            for zp in sorted(glob.glob(os.path.join(zips_root, m, f"*-fundingRate-{m}.zip"))):
                s = os.path.basename(zp).split("-fundingRate-")[0]
                z = zipfile.ZipFile(zp)
                for r in csv.reader(io.StringIO(z.read(z.namelist()[0]).decode("utf-8"))):
                    if r and r[0].strip().isdigit():
                        self.by_sym[s][int(r[0])] = (float(r[2]), float(r[1]))
                        self.stats["zip_rows"] += 1
        if api_gz and os.path.exists(api_gz):
            with gzip.open(api_gz, "rt") as fh:
                d = json.load(fh)
            self.stats["api_intervals_key_len"] = len(d.get("intervals") or {})
            for s, rows in (d.get("rates") or {}).items():
                for x in rows:
                    ft, rate = int(x[0]), float(x[1])
                    if ft in self.by_sym[s]:
                        old = self.by_sym[s][ft]
                        self.stats["api_row_already_present"] += 1
                        if old[0] != rate:
                            self.stats["API_ZIP_RATE_CONFLICT"] += 1
                    else:
                        self.by_sym[s][ft] = (rate, None)     # API carries no declared interval
                        self.stats["api_only_rows"] += 1

    def symbols(self):
        return sorted(self.by_sym)

    def events(self, symbol):
        return [(ft, v[0], v[1]) for ft, v in sorted(self.by_sym.get(symbol, {}).items())]


def interface_check(led, sample=12):
    rec = {"provenance": led.provenance(), "symbols": len(led.symbols()),
           "stats": dict(getattr(led, "stats", {})), "checks": {}}
    syms = led.symbols()
    tot = same_sec = nonzero_ms = no_declared = 0
    bad_order = []
    for s in syms:
        ev = led.events(s)
        prev = None
        seen_sec = collections.Counter()
        for ft, rate, d in ev:
            tot += 1
            if ft % 1000:
                nonzero_ms += 1
            if d is None:
                no_declared += 1
            seen_sec[ft // 1000] += 1
            if prev is not None and ft <= prev:
                bad_order.append((s, prev, ft))
            prev = ft
        same_sec += sum(v - 1 for v in seen_sec.values() if v > 1)
    rec["checks"] = {
        "events": tot,
        "strictly_increasing": len(bad_order) == 0,
        "order_violations": bad_order[:10],
        "events_with_nonzero_ms": nonzero_ms,
        "extra_events_sharing_a_second": same_sec,
        "events_without_declared_interval": no_declared,
        "resolution_usable_for_ms_key": led.resolution == "MILLISECONDS",
    }
    rec["reading"] = (
        f"{tot} events, {nonzero_ms} with a non-zero millisecond part, {same_sec} extra events that share a "
        f"second with another (these are exactly the ones a second key would DROP), "
        f"{no_declared} without a declared interval (only the first-event and >24h-gap branches of "
        f"interval_d10 need one).")
    return rec


def rebuild(led, features_npz, anchors_filter=None):
    """The four columns on the member cell set, using interval_d10 for iv. Shapes mirror the live artifacts."""
    F = np.load(features_npz, allow_pickle=True)
    anchors = F["anchors"].astype(np.int64)
    syms = [str(s) for s in F["symbols"]]
    off, m = F["off"].astype(np.int64), F["m"].astype(np.int64)
    n_entries = int(m.size)
    fund_now = np.full(n_entries, np.nan)
    fund_ema = np.full(n_entries, np.nan)
    iv_col = np.full(n_entries, np.nan)
    rn8 = np.full((len(anchors), len(syms)), np.nan, np.float32)
    tiers = collections.Counter()
    ev_cache = {}
    for i, A in enumerate(anchors):
        if anchors_filter is not None and int(A) not in anchors_filter:
            continue
        A_ms = int(A) * 1000
        for k in range(int(off[i]), int(off[i + 1])):
            s = syms[int(m[k])]
            ev = ev_cache.get(s)
            if ev is None:
                ev = led.events(s)
                ev_cache[s] = ev
            lo, hi = 0, len(ev)
            while lo < hi:
                mid = (lo + hi) // 2
                if ev[mid][0] <= A_ms:
                    lo = mid + 1
                else:
                    hi = mid
            j = lo - 1
            if j < 0:
                tiers["no_asof"] += 1
                continue
            ft, rate, decl = ev[j]
            prev_ft = ev[j - 1][0] if j >= 1 else None
            r = FI.interval_d10(None if prev_ft is None else prev_ft // 1000, ft // 1000, decl)
            tiers[r["tier"]] += 1
            if (A_ms - ft) / 1000.0 > FRESH_S or r["iv"] is None:
                tiers["gated_nan"] += 1
                continue
            fund_now[k] = rate
            iv_col[k] = r["iv"]
            rn8[i, int(m[k])] = np.float32(rate * 8.0 / r["iv"])
    return {"fund_now": fund_now, "iv": iv_col, "rn8": rn8, "fund_ema": fund_ema}, tiers, anchors, syms


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True, choices=["p2", "zipapi"])
    ap.add_argument("--p2", default="/workspace/uplift_r2_2026-09-13/P2/work/ledger_full.npz")
    ap.add_argument("--allow-seconds", action="store_true", help="only if lead chooses option (c)")
    ap.add_argument("--zips-root", default=None)
    ap.add_argument("--months", default=None)
    ap.add_argument("--api-gz", default="/workspace/fund_aug.json.gz")
    ap.add_argument("--features", default=None)
    ap.add_argument("--interface-check", action="store_true")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    if a.source == "p2":
        led = P2Seconds(a.p2, allow_seconds=a.allow_seconds)
    else:
        assert a.zips_root and a.months, "--zips-root and --months are required for zipapi"
        led = ZipApiUnion(a.zips_root, [x.strip() for x in a.months.split(",") if x.strip()], a.api_gz)

    rec = {"device": os.path.basename(__file__), "self_sha256": sha(os.path.realpath(__file__)),
           "rule_module_sha256": sha(os.path.realpath(FI.__file__)),
           "criteria": "DECISION_RULE_D10_stage2_2026-09-26.md §1 + revision 1 (ms key)",
           "design": "docs/DESIGN_D10_lineD_prep_2026-09-26.md §1",
           "rule": "common/funding_interval.py interval_d10 -- IMPORTED, not reimplemented",
           "argv": sys.argv[1:]}

    if a.interface_check:
        rec["interface_check"] = interface_check(led)
        print(json.dumps(rec["interface_check"], indent=1)[:1800])
        print("\n" + rec["interface_check"]["reading"])
    else:
        assert a.features, "--features is required for a rebuild"
        cols, tiers, anchors, syms = rebuild(led, a.features)
        rec["rebuild"] = {"tiers": {k: int(v) for k, v in tiers.items()},
                          "anchors": int(len(anchors)), "symbols": len(syms),
                          "shapes": {k: list(np.shape(v)) for k, v in cols.items()},
                          "fund_ema": "NOT REBUILT HERE -- must call the producer's own EMA accumulation "
                                      "(design §1.3 step 5); a reimplementation differs at ~1e-12 and lead "
                                      "has ruled that difference is itself RED"}
        print(json.dumps(rec["rebuild"], indent=1)[:1200])

    json.dump(rec, open(a.out, "w"), indent=1)
    print(f"receipt -> {a.out}  sha256={sha(a.out)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
