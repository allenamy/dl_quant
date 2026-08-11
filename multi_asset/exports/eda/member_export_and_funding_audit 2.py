"""(a) Export the REAL point-in-time MEMBER110 roster for the venue-overlap agent.
(b) Audit the 4h-vs-8h funding-settlement split: is our funding factor unit-consistent?

(b) matters because the engine rank-centres funding CROSS-SECTIONALLY. FUND_EMA stores the EMA of
the PER-INTERVAL rate. If a 4h-settled coin's per-interval rate is compared directly against an
8h-settled coin's, the 4h coin looks ~2x less crowded than it is -> a systematic ranking bias, not
a scale nuisance (rank-centring does NOT wash out a group-dependent unit).

Out: exports/eda/member110_roster.json (+ .csv), exports/eda/funding_interval_audit.json
"""
import json, os, sys, glob
import numpy as np
import pandas as pd

MA = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # .../multi_asset
MA = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # .../multi_asset
REPO = os.path.dirname(MA)
sys.path.insert(0, MA)
from engine.panel_source import PanelSource

WIDE = REPO + "/data/wide"


def export_roster():
    src = PanelSource()
    syms = src.symbols
    ts = src.ts
    dt = pd.to_datetime(ts, unit="ms", utc=True)
    last_t = int(np.where(src.member.any(1))[0][-1])
    one_yr = last_t - 365 * 24
    win = src.member[max(0, one_yr):last_t + 1]
    frac = win.mean(0)
    latest = src.member[last_t]

    rows = []
    for j, s in enumerate(syms):
        if frac[j] > 0 or latest[j]:
            rows.append({"symbol": s, "member_frac_last365d": round(float(frac[j]), 4),
                         "member_latest": bool(latest[j])})
    rows.sort(key=lambda d: -d["member_frac_last365d"])

    out = {
        "as_of": str(dt[last_t]),
        "window_for_frac": f"{dt[max(0,one_yr)]} .. {dt[last_t]}",
        "definition": ("MEMBER110 = point-in-time top-110 by DVOL30 (trailing-30d mean HOURLY "
                       "quote volume), refreshed on 30-day blocks at block start. Built by "
                       "data/build_wide_dl.py L102-114. NOT a static list."),
        "n_latest_snapshot": int(latest.sum()),
        "n_ever_member_last365d": int((frac > 0).sum()),
        "n_always_member_last365d": int((frac >= 0.999).sum()),
        "latest_snapshot": sorted([syms[j] for j in np.where(latest)[0]]),
        "always_member_last365d": sorted([syms[j] for j in np.where(frac >= 0.999)[0]]),
        "stable_member_last365d_ge80pct": sorted([syms[j] for j in np.where(frac >= 0.8)[0]]),
        "ever_member_last365d": sorted([syms[j] for j in np.where(frac > 0)[0]]),
        "per_symbol": rows,
        "note_for_overlap_agent": ("Use `latest_snapshot` (110 names) for a point-estimate "
                                   "overlap, or `stable_member_last365d_ge80pct` for a "
                                   "churn-robust one. Panel symbols are Binance USDT-perp "
                                   "tickers; 1000X-prefixed names correspond to Hyperliquid's "
                                   "kX naming (1000PEPEUSDT <-> kPEPE)."),
    }
    with open(MA + "/exports/eda/member110_roster.json", "w") as f:
        json.dump(out, f, indent=1)
    pd.DataFrame(rows).to_csv(MA + "/exports/eda/member110_roster.csv", index=False)
    print(f"[roster] latest {out['n_latest_snapshot']} | ever-in-365d "
          f"{out['n_ever_member_last365d']} | always {out['n_always_member_last365d']}", flush=True)
    print("[roster] latest snapshot:", " ".join(out["latest_snapshot"]), flush=True)
    return out


def audit_funding_intervals():
    src = PanelSource()
    syms = src.symbols
    W = np.load(MA + "/exports/wide_panel_full.npz", allow_pickle=True)
    FE = W["FUND_EMA"].astype(np.float64)
    files = {os.path.basename(p).replace("_funding.csv", ""): p
             for p in glob.glob(WIDE + "/*_funding.csv")}
    print(f"[fund] funding CSVs found: {len(files)}", flush=True)

    per = []
    for s in syms:
        p = files.get(s)
        if not p:
            per.append({"sym": s, "found": False})
            continue
        d = pd.read_csv(p)
        if "funding_interval_h" not in d or len(d) < 10:
            per.append({"sym": s, "found": True, "has_interval_col": False})
            continue
        iv = pd.to_numeric(d["funding_interval_h"], errors="coerce").dropna()
        vc = iv.value_counts()
        med = float(iv.median())
        # did it CHANGE over time? (Binance migrated many coins 8h -> 4h)
        first = float(iv.iloc[:max(1, len(iv) // 10)].median())
        last = float(iv.iloc[-max(1, len(iv) // 10):].median())
        per.append({"sym": s, "found": True, "has_interval_col": True,
                    "median_h": med, "first_decile_h": first, "last_decile_h": last,
                    "changed": bool(abs(first - last) > 0.5),
                    "n_rows": int(len(iv)),
                    "mix": {str(k): int(v) for k, v in vc.head(4).items()}})
    ok = [d for d in per if d.get("has_interval_col")]
    med_counts = pd.Series([d["median_h"] for d in ok]).value_counts().to_dict()
    changed = [d["sym"] for d in ok if d["changed"]]
    last_counts = pd.Series([d["last_decile_h"] for d in ok]).value_counts().to_dict()

    # ---- is there a LEVEL bias in FUND_EMA by interval group? ----
    last_t = int(np.where(src.member.any(1))[0][-1])
    recent = slice(max(0, last_t - 180 * 24), last_t + 1)
    g4 = [syms.index(d["sym"]) for d in ok if d["last_decile_h"] <= 4.5 and d["sym"] in syms]
    g8 = [syms.index(d["sym"]) for d in ok if d["last_decile_h"] >= 7.5 and d["sym"] in syms]
    mem = src.member[recent]
    fe = FE[recent]

    def grp_stats(idx):
        v = fe[:, idx][mem[:, idx]]
        v = v[np.isfinite(v)]
        return {"n_obs": int(v.size), "mean_bps": round(float(v.mean() * 1e4), 4),
                "median_bps": round(float(np.median(v) * 1e4), 4),
                "std_bps": round(float(v.std() * 1e4), 4)}

    # cross-sectional rank position of each group (the thing the engine actually consumes)
    ranks4, ranks8 = [], []
    for i in range(fe.shape[0]):
        m = np.where(mem[i] & np.isfinite(fe[i]))[0]
        if len(m) < 20:
            continue
        r = pd.Series(fe[i, m]).rank(pct=True).values
        s4 = np.array([k for k, j in enumerate(m) if j in set(g4)])
        s8 = np.array([k for k, j in enumerate(m) if j in set(g8)])
        if s4.size:
            ranks4.append(r[s4].mean())
        if s8.size:
            ranks8.append(r[s8].mean())

    out = {
        "question": ("Binance splits funding settlement across 4h and 8h coins. FUND_EMA stores "
                     "the EMA of the PER-INTERVAL rate. Does that leave a unit mismatch in the "
                     "cross-section the engine ranks?"),
        "smoothing_is_interval_aware": True,
        "smoothing_evidence": ("data/build_wide_panel.py L67-68: span = round(24/interval_h), so "
                               "8h -> span 3 and 4h -> span 6; both are 24h-equivalent EMAs. The "
                               "SMOOTHING window is correct per coin."),
        "n_coins_with_interval_col": len(ok),
        "median_interval_counts": {str(k): int(v) for k, v in med_counts.items()},
        "latest_interval_counts": {str(k): int(v) for k, v in last_counts.items()},
        "n_coins_that_changed_interval": len(changed),
        "coins_that_changed": sorted(changed),
        "level_by_group_last180d": {"interval_4h": grp_stats(g4) if g4 else None,
                                    "interval_8h": grp_stats(g8) if g8 else None,
                                    "n_coins_4h": len(g4), "n_coins_8h": len(g8)},
        "mean_xsec_pct_rank": {"interval_4h": (round(float(np.mean(ranks4)), 4) if ranks4 else None),
                               "interval_8h": (round(float(np.mean(ranks8)), 4) if ranks8 else None),
                               "note": ("0.5 = neutral. A systematic gap means the 4h/8h split "
                                        "biases WHERE each group sits in the ranking the engine "
                                        "trades, which rank-centring cannot remove.")},
        "per_symbol": per,
    }
    with open(MA + "/exports/eda/funding_interval_audit.json", "w") as f:
        json.dump(out, f, indent=1)
    print(f"[fund] latest interval counts: {out['latest_interval_counts']}", flush=True)
    print(f"[fund] coins that CHANGED interval: {len(changed)}", flush=True)
    print(f"[fund] level 4h vs 8h: {out['level_by_group_last180d']}", flush=True)
    print(f"[fund] mean xsec pct-rank 4h={out['mean_xsec_pct_rank']['interval_4h']} "
          f"8h={out['mean_xsec_pct_rank']['interval_8h']}", flush=True)
    return out


if __name__ == "__main__":
    export_roster()
    print()
    audit_funding_intervals()
