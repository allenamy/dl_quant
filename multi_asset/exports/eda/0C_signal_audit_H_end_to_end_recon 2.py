#!/usr/bin/env /usr/bin/python3
"""0C signal-side audit — item H: independent end-to-end reconciliation of the shipped factors.

For three symbols, pull the RAW fapi endpoints directly (plain urllib — not the repo's client),
recompute `funding_ema` (normfix caliber) and `dvol30` from first principles with arithmetic
written here rather than imported, and reconcile against the values in state/preds_latest.json
that the anchor actually traded on.

The only thing deliberately taken from the repo is `config/funding_span_table.json` — the EMA span
is a frozen MODEL ARTEFACT (derived from full-history median settlement interval), not something a
40-day live window can re-derive; re-deriving it here would be reconciling against a different
definition and would fail for a correct system.

Read-only. ~10 public requests, weight ~35 against a 2400/min cap.
"""
import json
import os
import sys
import time
import urllib.parse
import urllib.request

import numpy as np

LIVE = os.path.expanduser("~/dl_quant_live")
PREDS = os.path.join(LIVE, "state", "preds_latest.json")
SPAN = os.path.join(LIVE, "config", "funding_span_table.json")
BASE = "https://fapi.binance.com"
OUT = os.path.expanduser(
    "~/Desktop/quant_research/multi_asset/exports/eda/0C_signal_audit_H_end_to_end_recon.json")

DVOL30_HOURS = 24 * 30
MIN_PERIODS = 24 * 5


def get(path, **params):
    url = f"{BASE}{path}?" + urllib.parse.urlencode(params)
    for a in range(3):
        try:
            with urllib.request.urlopen(url, timeout=15) as r:
                return json.loads(r.read().decode())
        except Exception as e:
            if a == 2:
                raise
            time.sleep(1.5 * (a + 1))


def dvol30_by_hand(qvol, anchor_ts, ts):
    """Trailing-30d MEAN HOURLY quote volume at the anchor, NaN-skipping, min_periods=120.
    Written out longhand: no pandas, no shared helper."""
    j = int(np.where(ts == anchor_ts)[0][0])
    lo = max(0, j - DVOL30_HOURS + 1)
    w = qvol[lo:j + 1]
    w = w[np.isfinite(w)]
    if w.size < MIN_PERIODS:
        return None
    return float(w.sum() / w.size)


def interval_h_by_hand(fts, interval_now):
    """Per-settlement interval in hours: rounded backward diffs, 3-point median, snapped."""
    allowed = np.array([1., 2., 3., 4., 6., 8., 12., 24.])
    f = np.asarray(fts, float)
    n = len(f)
    dt = np.round(np.diff(f) / 3_600_000.0)
    b = np.empty(n)
    b[0] = dt[0]
    b[1:] = dt
    b = np.where((b > 0) & (b <= 24), b, 8.0)
    med = np.empty(n)
    for i in range(n):
        med[i] = np.median(b[max(0, i - 1):min(n, i + 2)])
    med = allowed[np.argmin(np.abs(med[:, None] - allowed[None, :]), axis=1)]
    if interval_now:                       # authoritative for the current regime
        j = n - 1
        while j > 0 and med[j - 1] == med[-1]:
            j -= 1
        med[j:] = float(interval_now)
    return med


def funding_ema_by_hand(rates, ivs, span):
    """EMA(adjust=False) over rate x (8/interval_h), normalised PER ROW before smoothing."""
    alpha = 2.0 / (span + 1.0)
    ema = None
    for r, iv in zip(rates, ivs):
        v = r * (8.0 / iv)
        ema = v if ema is None else alpha * v + (1 - alpha) * ema
    return float(ema)


def main():
    preds = json.load(open(PREDS))
    span_tab = json.load(open(SPAN))["table"]
    anchor = int(preds["anchor_ts_ms"])
    members = preds["symbols"]

    iv_now = {r["symbol"]: float(r.get("fundingIntervalHours", 8) or 8)
              for r in get("/fapi/v1/fundingInfo")}

    # one 8h name, one 4h name (exercises the x8/iv correction), one small-cap
    by_dvol = sorted(members, key=lambda s: preds["dvol30"][s])
    four_h = [s for s in members if iv_now.get(s, 8.0) <= 4.0]
    picks = [s for s in ["BTCUSDT", (four_h or members)[0], by_dvol[0]] if s in members]
    picks = list(dict.fromkeys(picks))

    res = {"anchor_ts_ms": anchor,
           "anchor_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(anchor / 1000)),
           "preds_computed_ts": preds["computed_ts"],
           "preds_age_h_at_audit": round((time.time() - preds["computed_ts"]) / 3600, 2),
           "funding_leg_caliber_stamped": preds["panel"]["funding_leg_caliber"],
           "symbols": {}}

    for s in picks:
        # ── klines: 720 closed hourly bars ending AT the anchor ─────────────────────────────
        rows = []
        cursor = anchor - (DVOL30_HOURS - 1) * 3_600_000
        while cursor <= anchor:
            got = get("/fapi/v1/klines", symbol=s, interval="1h", startTime=int(cursor),
                      endTime=int(anchor), limit=1000)
            if not got:
                break
            rows.extend(got)
            nxt = int(got[-1][0]) + 3_600_000
            if nxt <= cursor:
                break
            cursor = nxt
        ts = np.array([int(k[0]) for k in rows], np.int64)
        qv = np.array([float(k[7]) for k in rows], float)
        dv_mine = dvol30_by_hand(qv, anchor, ts) if len(ts) else None
        dv_theirs = float(preds["dvol30"][s])

        # ── funding: the most recent 1000 settlements, NO time window ───────────────────────
        fr = get("/fapi/v1/fundingRate", symbol=s, limit=1000)
        fr = [r for r in fr if int(r["fundingTime"]) <= anchor]
        fts = np.array([int(r["fundingTime"]) for r in fr], np.int64)
        rate = np.array([float(r["fundingRate"]) for r in fr], float)
        ivs = interval_h_by_hand(fts, iv_now.get(s))
        span = int(span_tab[s]["span"]) if s in span_tab else max(2, round(24 / np.median(ivs)))
        fe_mine = funding_ema_by_hand(rate, ivs, span)
        fe_theirs = float(preds["funding_ema"][s])
        # the same series WITHOUT the x8/iv correction — proves the shipped leg really is normfix
        fe_uncorrected = funding_ema_by_hand(rate, np.full_like(ivs, 8.0), span)

        res["symbols"][s] = {
            "n_klines_fetched": int(len(ts)),
            "last_kline_ts_ms": int(ts[-1]) if len(ts) else None,
            "kline_index_gaps_in_720h": int((np.diff(ts) != 3_600_000).sum()) if len(ts) else None,
            "dvol30": {"independent": dv_mine, "shipped": dv_theirs,
                       "rel_err": (None if not dv_mine else abs(dv_mine / dv_theirs - 1)),
                       "match": (dv_mine is not None and abs(dv_mine / dv_theirs - 1) < 1e-9)},
            "funding": {
                "settlement_interval_now_h": iv_now.get(s),
                "n_settlements": int(len(fts)),
                "span_used_from_frozen_table": span,
                "span_in_table": s in span_tab,
                "frac_4h_rows": float((ivs <= 4.0).mean()),
                "ema_independent_normfix": fe_mine,
                "ema_shipped": fe_theirs,
                "abs_err": abs(fe_mine - fe_theirs),
                "rel_err": abs(fe_mine - fe_theirs) / max(abs(fe_theirs), 1e-12),
                "match_1e-9_rel": bool(abs(fe_mine - fe_theirs) <= 1e-9 * max(abs(fe_theirs), 1e-12)
                                       or abs(fe_mine - fe_theirs) < 1e-12),
                "ema_if_uncorrected_as_trained": fe_uncorrected,
                "shipped_is_closer_to": ("normfix" if abs(fe_mine - fe_theirs)
                                         <= abs(fe_uncorrected - fe_theirs) else "as_trained"),
            }}

    ok = all(v["dvol30"]["match"] and v["funding"]["match_1e-9_rel"]
             for v in res["symbols"].values())
    res["verdict"] = ("RECONCILED — every shipped factor value reproduces from raw fapi to 1e-9"
                      if ok else "MISMATCH — see per-symbol rel_err")
    json.dump(res, open(OUT, "w"), indent=1, default=str)
    print(json.dumps(res, indent=1, default=str))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
