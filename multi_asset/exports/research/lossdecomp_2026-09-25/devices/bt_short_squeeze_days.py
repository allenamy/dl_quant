#!/usr/bin/env python3
"""How common is a short squeeze like the NC window's in the extended-axis backtest (X config, s42)? (lead 2026-09-25 item 3). Runs on pod2,
READ-ONLY, CPU-light (a few hundred MB), no engine, no GPU. Inputs (sha printed into the output):
  TARGETS  /dev/shm/news2_2026-09-23/targets/TARGETS_NEWS2_s42.npz   — the s42X run's target book (RUN_CONFIG_NEWS2_s42X runs[0].targets),
           "scaled" reading, CSR (scaled_off / scaled_idx / scaled_val) on the 829 panel symbols; kind 0/other rows without entries = HOLD ⇒
           the previous published weights are carried (the engine holds).
  PANEL    /workspace/axis_0919/x0918r/panels/wide_panel_4h_rawbuild_x0918r.npz — Y4[t] = the forward 4 h return of the anchor t (the same
           alignment fa_window_legs.py uses with the leg z at t; PANEL CALIBER, not the live 5 m rr).
  LEGS     /dev/shm/news2_2026-09-23/work/legs.npz — ZFD (fund-leg z) per anchor.
  SER      /dev/shm/fanom_2026-09-24/receipts/SER_EXT_NEWS2_s42X.npz — the engine's per-anchor book return per path (r_per_path, 32 paths).
Definitions (per anchor t, on the panel's forward 4 h return y):
  book short side  s_t = sum_{w<0} w*y / sum_{w<0}|w|   (return per unit of short notional; NEGATIVE = the shorted names rose = a loss)
  book long side   l_t = sum_{w>0} w*y / sum_{w>0}|w|
  fund-leg short   f_t = sum_{z<0} z*y / sum_{z<0}|z| with z = ZFD demeaned over names finite in z and y (the leg-return recipe of
                   shadow_loop_v3 / fa_window_legs), short side = z < 0.
  day = UTC date, a day counts only with all 6 anchors present; daily value = the SUM of the 6 anchor values (per-unit-notional, simple).
Outputs: the daily distributions over 2023-07-01 .. 2026-09-18 (percentiles), the percentile of each supplied live value (--live name=value,...
in percent, e.g. window=-4.18), the squeeze days (book short daily <= --threshold, default -4.18 %) with the book's forward 3 d / 7 d return
(SER mean over paths, compounded over the next 18 / 42 anchors after the day's last anchor) vs the unconditional forward returns.
usage: /workspace/venv/bin/python bt_short_squeeze_days.py <out json> [--threshold -4.18] [--live k=v,...] [--live-ls k=v,...] [--live-fund k=v,...]   (percent)"""
import hashlib, json, os, sys, time, calendar, collections
import numpy as np

TARGETS = "/dev/shm/news2_2026-09-23/targets/TARGETS_NEWS2_s42.npz"
PANEL = "/workspace/axis_0919/x0918r/panels/wide_panel_4h_rawbuild_x0918r.npz"
LEGS = "/dev/shm/news2_2026-09-23/work/legs.npz"
SER = "/dev/shm/fanom_2026-09-24/receipts/SER_EXT_NEWS2_s42X.npz"
T0 = calendar.timegm(time.strptime("2023-07-01", "%Y-%m-%d")); T1 = calendar.timegm(time.strptime("2026-09-18T20:00", "%Y-%m-%dT%H:%M"))


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


def main():
    out = sys.argv[1]
    thr = float(sys.argv[sys.argv.index("--threshold") + 1]) / 100 if "--threshold" in sys.argv else -0.0418
    def kv(flag):
        o = {}
        if flag in sys.argv:
            for x in sys.argv[sys.argv.index(flag) + 1].split(","):
                k, v = x.split("="); o[k] = float(v) / 100
        return o
    live = kv("--live"); live_ls = kv("--live-ls"); live_fund = kv("--live-fund")   # rev 1: long+short and fund-leg live values
    T = np.load(TARGETS); P = np.load(PANEL, allow_pickle=True); L = np.load(LEGS, allow_pickle=True); S = np.load(SER)
    rec = {"device_sha256": sha(os.path.abspath(__file__)), "inputs": {p: sha(p) for p in (TARGETS, PANEL, LEGS, SER)},
           "window": ["2023-07-01", "2026-09-18T20:00Z"], "threshold_book_short_daily": thr}
    ta = T["anchor"].astype(np.int64); off = T["scaled_off"]; idx = T["scaled_idx"].astype(np.int64); val = T["scaled_val"]
    pt = P["ts"].astype(np.int64); Y4 = P["Y4"].astype(np.float64); psym = [str(s) for s in P["symbols"]]
    lt = L["E_ts"].astype(np.int64); ZFD = L["ZFD"].astype(np.float64); assert [str(s) for s in L["symbols"]] == psym, "legs / panel symbol axes differ"
    assert idx.max() < len(psym), "target index outside the panel symbol axis"
    prow = {int(t): i for i, t in enumerate(pt)}; lrow = {int(t): i for i, t in enumerate(lt)}
    sa = S["anchors"].astype(np.int64); rbook = np.nanmean(S["r_per_path"], axis=0); srow = {int(t): i for i, t in enumerate(sa)}
    N = len(psym); w = np.zeros(N); n_hold = n_pub = 0
    per = []                                                   # (t, s_t, l_t, f_t)
    for k, t in enumerate(ta):
        a, b = off[k], off[k + 1]
        if b > a:
            w = np.zeros(N); w[idx[a:b]] = val[a:b]; n_pub += 1
        else:
            n_hold += 1                                        # no entries: the engine holds the previous target
        if not (T0 <= t <= T1): continue
        i = prow.get(int(t))
        if i is None: continue
        y = Y4[i]; ok = np.isfinite(y)
        sh = (w < 0) & ok; lo = (w > 0) & ok
        s_t = float((w[sh] * y[sh]).sum() / np.abs(w[sh]).sum()) if sh.any() else np.nan
        l_t = float((w[lo] * y[lo]).sum() / np.abs(w[lo]).sum()) if lo.any() else np.nan
        f_t = np.nan; j = lrow.get(int(t))
        if j is not None:
            z = ZFD[j]; okz = np.isfinite(z) & ok
            if okz.sum() >= 50:
                zz = np.where(okz, z - z[okz].mean(), 0.0); fs = okz & (zz < 0)
                f_t = float((zz[fs] * y[fs]).sum() / np.abs(zz[fs]).sum()) if fs.any() else np.nan   # zz < 0: zz*y is already the short's signed P&L
        per.append((int(t), s_t, l_t, f_t))
    kinds = T["scaled_kind"]; has = (off[1:] - off[:-1]) > 0
    rec["targets_rows"] = {"published": n_pub, "held": n_hold, "anchors_in_window": len(per),
                           "kind_x_has_entries": {f"kind{int(k)}_{'entries' if h else 'empty'}": int(((kinds == k) & (has == h)).sum()) for k in np.unique(kinds) for h in (True, False)}}
    day = collections.defaultdict(list)
    for t, s_t, l_t, f_t in per: day[time.strftime("%Y-%m-%d", time.gmtime(t))].append((t, s_t, l_t, f_t))
    D = []
    for d, rows in sorted(day.items()):
        if len(rows) != 6 or any(not np.isfinite(r[1]) for r in rows): continue
        D.append({"day": d, "t_last": max(r[0] for r in rows), "book_short": sum(r[1] for r in rows), "book_long": sum(r[2] for r in rows),
                  "fund_short": sum(r[3] for r in rows) if all(np.isfinite(r[3]) for r in rows) else None})
    bs = np.array([x["book_short"] for x in D]); fsd = np.array([x["fund_short"] for x in D if x["fund_short"] is not None])
    pct = lambda arr: {str(q): float(np.percentile(arr, q) * 100) for q in (0.5, 1, 2, 5, 10, 25, 50, 75, 90)}
    rec["n_days"] = len(D); rec["book_short_daily_pct"] = pct(bs); rec["fund_short_daily_pct"] = pct(fsd) if len(fsd) else None
    ls = np.array([x["book_short"] + x["book_long"] for x in D])      # rev 1: long side + short side, per unit notional each (sign = P&L)
    rec["book_long_plus_short_daily_pct"] = pct(ls)
    rec["live_ls_percentiles"] = {k: {"value_pct": v * 100, "rank_pct": float((ls <= v).mean() * 100)} for k, v in live_ls.items()}
    rec["live_fund_short_percentiles"] = {k: {"value_pct": v * 100, "rank_pct": float((fsd <= v).mean() * 100)} for k, v in live_fund.items()}
    rec["live_value_percentiles"] = {k: {"value_pct": v * 100, "book_short_rank_pct": float((bs <= v).mean() * 100),
                                         "fund_short_rank_pct": float((fsd <= v).mean() * 100) if len(fsd) else None} for k, v in live.items()}
    def fwd(t_last, n):
        i = srow.get(int(t_last))
        if i is None or i + 1 + n > len(rbook): return None
        seg = rbook[i + 1:i + 1 + n]
        return float(np.expm1(np.log1p(seg).sum())) if np.isfinite(seg).all() else None
    for x in D: x["fwd3d"] = fwd(x["t_last"], 18); x["fwd7d"] = fwd(x["t_last"], 42)
    sq = [x for x in D if x["book_short"] <= thr]
    def stats(v):
        v = [a for a in v if a is not None]; return {"n": len(v), "mean_pct": float(np.mean(v) * 100) if v else None,
                                                    "median_pct": float(np.median(v) * 100) if v else None, "frac_positive": float(np.mean(np.array(v) > 0)) if v else None}
    rec["squeeze_days"] = {"n": len(sq), "per_year": dict(collections.Counter(x["day"][:4] for x in sq)),
                           "fwd3d": stats([x["fwd3d"] for x in sq]), "fwd7d": stats([x["fwd7d"] for x in sq]),
                           "days": [{"day": x["day"], "book_short_pct": x["book_short"] * 100, "book_long_pct": x["book_long"] * 100,
                                     "fund_short_pct": (x["fund_short"] * 100 if x["fund_short"] is not None else None),
                                     "fwd3d_pct": (x["fwd3d"] * 100 if x["fwd3d"] is not None else None), "fwd7d_pct": (x["fwd7d"] * 100 if x["fwd7d"] is not None else None)} for x in sq]}
    rec["unconditional"] = {"fwd3d": stats([x["fwd3d"] for x in D]), "fwd7d": stats([x["fwd7d"] for x in D])}
    rec["worst_book_short_days"] = [{"day": x["day"], "book_short_pct": x["book_short"] * 100} for x in sorted(D, key=lambda x: x["book_short"])[:15]]
    json.dump(rec, open(out + ".tmp", "w"), indent=1); os.replace(out + ".tmp", out)
    print(f"BT_SHORT_SQUEEZE days={len(D)} (targets published {n_pub}, held {n_hold}) kinds {rec['targets_rows']['kind_x_has_entries']}")
    print("book short daily percentiles (%):", {k: round(v, 3) for k, v in rec["book_short_daily_pct"].items()})
    if rec["fund_short_daily_pct"]: print("fund-leg short daily percentiles (%):", {k: round(v, 3) for k, v in rec["fund_short_daily_pct"].items()})
    for k, v in rec["live_value_percentiles"].items(): print(f"live {k} {v['value_pct']:.2f}%: book-short rank {v['book_short_rank_pct']:.2f} pct; fund-short rank {v['fund_short_rank_pct']}")
    print("book long+short daily percentiles (%):", {k: round(v, 3) for k, v in rec["book_long_plus_short_daily_pct"].items()})
    for k, v in rec["live_ls_percentiles"].items(): print(f"live long+short {k} {v['value_pct']:.2f}%: rank {v['rank_pct']:.2f} pct")
    for k, v in rec["live_fund_short_percentiles"].items(): print(f"live fund-leg short {k} {v['value_pct']:.2f}%: rank {v['rank_pct']:.2f} pct")
    s = rec["squeeze_days"]; print(f"squeeze days (book short daily <= {thr * 100:.2f}%): n={s['n']} per year {s['per_year']}; fwd3d {s['fwd3d']}; fwd7d {s['fwd7d']}")
    print("unconditional fwd3d", rec["unconditional"]["fwd3d"], "fwd7d", rec["unconditional"]["fwd7d"])
    print("worst 15 book-short days:", [(x["day"], round(x["book_short_pct"], 2)) for x in rec["worst_book_short_days"]])


if __name__ == "__main__":
    main()
