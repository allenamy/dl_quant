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

# The producer's OWN funding contract: ema_step (the verbatim EMA arithmetic) and snap_interval. Imported and
# CALLED -- "using the frozen caliber" only holds when the code is called, and an EMA reimplementation differs at
# ~1e-12, which lead has ruled is itself RED.
NC_CONTRACT = os.environ.get("NC_CONTRACT", "/dev/shm/nc_2026-09-23/devices_arm/nc_contract.py")


def _load_nc():
    import importlib.util
    if not os.path.exists(NC_CONTRACT):
        raise ImportError(f"producer contract not found at {NC_CONTRACT}; set NC_CONTRACT. This device must "
                          "not reimplement ema_step.")
    spec = importlib.util.spec_from_file_location("nc_contract", NC_CONTRACT)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


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


class LedgerMs(MsLedger):
    """ledger_full_ms.npz -- the artifact lead designated as the truth source (revision 2/3).

    This is what the rebuild should read: it carries the FULL history (2020-01 onward, 2,633,108 rows), so the
    producer's EMA is warmed over the whole axis. My first run used a 6-month zip window instead, which starts
    the EMA cold in the middle of history and inflates UNRESOLVED_DECLARED_UNAVAILABLE -- a truncated event
    history is not a smaller version of the same computation, it is a different one.
    """
    name = "ledger_full_ms.npz"
    resolution = "MILLISECONDS"

    def __init__(self, path, pinned_sha=None):
        self.path, self.sha256 = path, sha(path)
        if pinned_sha:
            assert self.sha256.startswith(pinned_sha), ("not the pinned ledger", self.sha256, pinned_sha)
        Z = np.load(path, allow_pickle=True)
        assert "ft_ms" in Z.files, f"{path} has no ft_ms: this source must be millisecond-keyed"
        self.off = Z["off"].astype(np.int64)
        self.ft = Z["ft_ms"].astype(np.int64)
        self.rate = Z["rate"].astype(np.float64)
        self.zip_iv = Z["zip_iv"].astype(np.float64)
        self.syms = [str(x) for x in Z["symbols"]]
        self.idx = {x: j for j, x in enumerate(self.syms)}

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
            out.append((int(self.ft[k]), float(self.rate[k]), d if np.isfinite(d) else None))
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


def rebuild(led, features_npz, ema_mode="d10_iv", anchors_filter=None):
    """The four columns on the member cell set.

    ★ THE fund_ema CONFLICT, surfaced rather than resolved unilaterally. lead requires (i) the interval to be
    interval_d10's exact spacing and (ii) fund_ema to come from the producer's own EMA code. Those two collide
    in `ingest_settlements`, whose L77 computes the interval ITSELF with snap_interval -- the very rule the D10
    rule replaces -- before calling ema_step. Calling that wrapper verbatim would put snapped intervals inside
    the EMA while iv/rn8 use interval_d10, i.e. two interval rules inside one artifact.

    Reading the code resolves it: `ema_step(state, ft, rate, iv)` IS the producer's verbatim EMA arithmetic
    (feature_contract L80-L88) and it takes iv as an ARGUMENT; `ingest_settlements` is only the wrapper that
    decides iv. So ema_mode="d10_iv" calls the producer's EMA with the D10 interval -- which is exactly what
    the October producer change is (swap snap_interval for interval_d10, leave ema_step alone).
    ema_mode="producer_snap" reproduces today's live behaviour for comparison. Default is d10_iv; lead confirms.

    ft is passed to ema_step in SECONDS, because its decay constant (3*86400) is in seconds and the producer
    passes seconds. Consequence, named: two settlements inside one second give ft - prev = 0, so decay = 1 and
    the second one does not move acc. That touches only the 18 sub-second events in the whole ledger.
    """
    NC = _load_nc()
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

    # per symbol: walk the ms events once, snapshotting (state, last_row) at every anchor boundary
    anchor_list = [int(x) for x in anchors]
    per_anchor_members = collections.defaultdict(list)
    for i in range(len(anchors)):
        for k in range(int(off[i]), int(off[i + 1])):
            per_anchor_members[syms[int(m[k])]].append((i, k))

    for s, cells in per_anchor_members.items():
        ev = led.events(s)
        if not ev:
            tiers["symbol_no_events"] += 1
            continue
        state = {"acc": None, "last_ts": None}
        prev_ft_ms = None
        last_row = None
        pos = 0
        for (i, k) in sorted(cells):
            A = anchor_list[i]
            A_ms = A * 1000
            # ★ THE AS-OF BOUNDARY IS THE WHOLE ANCHOR SECOND, not `<= anchor*1000`. Production:
            #   shadow_loop_v3.py:646-647  endTime = anchor * 1000 + 999
            #   and its own comment at L640-641: "本地过滤 `if ft > anchor: continue`(秒)本就允许
            #   '等于锚'的那次结算 ... +999 只是让 API 侧与本地侧对齐到同一个整秒边界."
            # My first version used `<= A_ms`, which silently DROPPED every settlement stamped 1-999 ms after
            # the round anchor second. 57.17% of settlements carry a non-zero ms part, so this moved the as-of
            # on 431,981 member cells -- the entire fund_now difference against the in-service features, in a
            # window where the event sets are provably identical. Re-keying to milliseconds changes where the
            # anchor boundary falls, and the boundary has to move with it.
            while pos < len(ev) and ev[pos][0] <= A_ms + 999:
                ft_ms, rate, decl = ev[pos]
                r = FI.interval_d10(None if prev_ft_ms is None else prev_ft_ms // 1000,
                                    ft_ms // 1000, decl)
                tiers[r["tier"]] += 1
                if ema_mode == "producer_snap":
                    iv_use = NC.snap_interval(ft_ms // 1000 - prev_ft_ms // 1000) if prev_ft_ms is not None else None
                else:
                    iv_use = r["iv"]
                state, _ = NC.ema_step(state, ft_ms // 1000, rate, iv_use)   # producer's verbatim arithmetic
                last_row = [ft_ms // 1000, rate, iv_use]
                prev_ft_ms = ft_ms
                pos += 1
            if last_row is None:
                tiers["no_asof"] += 1
                continue
            ema, rate, iv, rn = NC.funding_asof(state, last_row, A)          # producer's verbatim gate
            if not np.isfinite(rn):
                tiers["gated_nan"] += 1
                continue
            fund_now[k] = rate
            fund_ema[k] = ema
            iv_col[k] = iv
            rn8[i, int(m[k])] = np.float32(rn)
    return {"fund_now": fund_now, "fund_ema": fund_ema, "iv": iv_col, "rn8": rn8}, tiers, anchors, syms


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True, choices=["p2", "zipapi", "ledger_ms"])
    ap.add_argument("--ledger-ms", default="/workspace/ledger_ms_2026-09-26/ledger_full_ms.npz")
    ap.add_argument("--ledger-ms-sha", default="e179071d5955")
    ap.add_argument("--p2", default="/workspace/uplift_r2_2026-09-13/P2/work/ledger_full.npz")
    ap.add_argument("--allow-seconds", action="store_true", help="only if lead chooses option (c)")
    ap.add_argument("--zips-root", default=None)
    ap.add_argument("--months", default=None)
    ap.add_argument("--api-gz", default="/workspace/fund_aug.json.gz")
    ap.add_argument("--features", default=None)
    ap.add_argument("--interface-check", action="store_true")
    ap.add_argument("--ema-mode", default="d10_iv", choices=["d10_iv", "producer_snap"])
    ap.add_argument("--save", default=None, help="write the rebuilt columns to this npz")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    if a.source == "ledger_ms":
        led = LedgerMs(a.ledger_ms, a.ledger_ms_sha)
    elif a.source == "p2":
        led = P2Seconds(a.p2, allow_seconds=a.allow_seconds)
    else:
        assert a.zips_root and a.months, "--zips-root and --months are required for zipapi"
        led = ZipApiUnion(a.zips_root, [x.strip() for x in a.months.split(",") if x.strip()], a.api_gz)

    rec = {"device": os.path.basename(__file__), "self_sha256": sha(os.path.realpath(__file__)),
           "rule_module_sha256": sha(os.path.realpath(FI.__file__)),
           "criteria": "DECISION_RULE_D10_stage2_2026-09-26.md §1 + revision 1 (ms key)",
           "design": "docs/DESIGN_D10_lineD_prep_2026-09-26.md §1",
           "rule": "common/funding_interval.py interval_d10 -- IMPORTED, not reimplemented",
           "argv": sys.argv[1:], "source_provenance": None}

    rec["source_provenance"] = dict(led.provenance(), **({"sha256": led.sha256} if hasattr(led, "sha256") else {}))
    if a.interface_check:
        rec["interface_check"] = interface_check(led)
        print(json.dumps(rec["interface_check"], indent=1)[:1800])
        print("\n" + rec["interface_check"]["reading"])
    else:
        assert a.features, "--features is required for a rebuild"
        cols, tiers, anchors, syms = rebuild(led, a.features, ema_mode=a.ema_mode)
        if a.save:
            np.savez_compressed(a.save, anchors=anchors, symbols=np.array(syms),
                                fn_v=cols["fund_now"], fe_v=cols["fund_ema"], iv_v=cols["iv"],
                                RN8=cols["rn8"], off=np.load(a.features)["off"], m=np.load(a.features)["m"])
            rec["saved"] = {"path": a.save, "sha256": sha(a.save)}
        rec["rebuild"] = {"tiers": {k: int(v) for k, v in tiers.items()},
                          "anchors": int(len(anchors)), "symbols": len(syms),
                          "shapes": {k: list(np.shape(v)) for k, v in cols.items()},
                          "ema_mode": a.ema_mode,
                          "ema_source": f"{NC_CONTRACT} ema_step + funding_asof, CALLED not reimplemented",
                          "ema_conflict_note": (
                              "lead requires both the D10 interval and the producer's own EMA code; "
                              "ingest_settlements L77 computes the interval itself via snap_interval, so the "
                              "wrapper cannot be used verbatim without putting two interval rules in one "
                              "artifact. ema_step IS the producer's verbatim EMA arithmetic and takes iv as an "
                              "argument, so it is called with the D10 iv (mode d10_iv). producer_snap "
                              "reproduces today's live behaviour for comparison. lead to confirm.")}
        print(json.dumps(rec["rebuild"], indent=1)[:1200])

    json.dump(rec, open(a.out, "w"), indent=1)
    print(f"receipt -> {a.out}  sha256={sha(a.out)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
