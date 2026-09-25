#!/usr/bin/env python3
"""Live counterpart of bt_short_squeeze_days.py with the SAME definitions (lead 2026-09-25 item 3). Mac, READ-ONLY, pooled, no venue.
Per anchor A (4 h grid) of the production target book: w = state/target_live/A.json weights (the published target — paper, not fills);
y = the forward return over (A, A+4h] per name from the latest snapshot's rolling cache (nc_contract.rr_from_ch0, compounded 5 m);
  book short s_A = sum_{w<0} w*y / sum_{w<0}|w|; book long l_A likewise; fund-leg short f_A with z = aux.prev_rec.legz["fund"] of snapshot A
  (members only; demeaned over names finite in z and y; short side z < 0) — only where the snapshot exists.
day = UTC date with all 6 anchors priced; daily = sum of the 6 anchor values. A partial day is printed with its anchor count, never scaled.
usage: ~/wide_shadow/venv/bin/python live_short_side_daily.py <out json> [--from 2026-09-16]"""
import calendar, collections, glob, hashlib, json, os, sys, time
import numpy as np

HOME = os.path.expanduser("~"); WS = f"{HOME}/wide_shadow"
sys.path.insert(0, f"{WS}/fea171"); import nc_contract as NC
sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()


def main():
    out = sys.argv[1]; d0 = sys.argv[sys.argv.index("--from") + 1] if "--from" in sys.argv else "2026-09-16"
    t0 = calendar.timegm(time.strptime(d0, "%Y-%m-%d"))
    snaps = sorted(int(x) for x in os.listdir(f"{WS}/state/snap") if x.isdigit()); last = snaps[-1]
    Z = np.load(f"{WS}/state/snap/{last}/rolling.npz"); B = np.load(f"{WS}/state/snap/{last}/boundary_raw.npz"); ts = Z["ts"].astype(np.int64)
    RR = NC.rr_from_ch0(ts, Z["data"][:, :, 0], B["ts"], B["col"], B["raw"]).astype(np.float64)
    syms = json.load(open(f"{WS}/shadow_bundle/config.json"))["symbols_panel"]; col = {s: j for j, s in enumerate(syms)}
    LP = np.vstack([np.zeros((1, RR.shape[1])), np.cumsum(np.log1p(np.nan_to_num(RR)), axis=0)])
    fin = np.isfinite(RR)
    def fwd(A):
        i0 = int(np.searchsorted(ts, A, side="right")) - 1; i1 = int(np.searchsorted(ts, A + 14400, side="right")) - 1
        if ts[i1] != A + 14400 or ts[i0] != A: return None
        y = np.expm1(LP[i1 + 1] - LP[i0 + 1]); y[fin[i0 + 1:i1 + 1].sum(0) < 40] = np.nan; return y
    rec = {"device_sha256": sha(os.path.abspath(__file__)), "price_snapshot": last, "rolling_sha256": sha(f"{WS}/state/snap/{last}/rolling.npz"), "anchors": []}
    for p in sorted(glob.glob(f"{WS}/state/target_live/17*.json")):
        A = int(os.path.basename(p)[:-5])
        if A < t0 or A % 14400: continue
        y = fwd(A)
        if y is None: continue
        W = json.load(open(p))["weights"]
        w = np.zeros(len(syms))
        for s, v in W.items():
            if s in col: w[col[s]] = v
        ok = np.isfinite(y); sh = (w < 0) & ok; lo = (w > 0) & ok
        row = {"A": A, "utc": time.strftime("%m-%dT%H:%MZ", time.gmtime(A)),
               "book_short": float((w[sh] * y[sh]).sum() / np.abs(w[sh]).sum()) if sh.any() else None,
               "book_long": float((w[lo] * y[lo]).sum() / np.abs(w[lo]).sum()) if lo.any() else None, "fund_short": None,
               "unpriced_weight_share": float(np.abs(w[~ok]).sum() / max(np.abs(w).sum(), 1e-12))}
        sp = f"{WS}/state/snap/{A}/aux.json"
        if os.path.exists(sp):
            pr = json.load(open(sp))["prev_rec"]
            if pr.get("anchor_ts") == A:
                m = np.array(pr["members"]); z = np.array(pr["legz"]["fund"], float); yy = y[m]; okz = np.isfinite(z) & np.isfinite(yy)
                if okz.sum() >= 50:
                    zz = np.where(okz, z - z[okz].mean(), 0.0); fs = okz & (zz < 0)
                    row["fund_short"] = float((zz[fs] * yy[fs]).sum() / np.abs(zz[fs]).sum())
        rec["anchors"].append(row)
    day = collections.defaultdict(list)
    for r in rec["anchors"]: day[time.strftime("%Y-%m-%d", time.gmtime(r["A"]))].append(r)
    rec["days"] = []
    for d, rows in sorted(day.items()):
        e = {"day": d, "n_anchors": len(rows), "complete": len(rows) == 6,
             "book_short_pct": sum(r["book_short"] for r in rows) * 100, "book_long_pct": sum(r["book_long"] for r in rows) * 100,
             "fund_short_pct": (sum(r["fund_short"] for r in rows) * 100 if all(r["fund_short"] is not None for r in rows) else None),
             "n_fund_short_anchors": sum(r["fund_short"] is not None for r in rows)}
        e["book_ls_pct"] = e["book_short_pct"] + e["book_long_pct"]; rec["days"].append(e)
        print(f"{d} anchors {len(rows)}{'' if e['complete'] else ' (PARTIAL)'}  book short {e['book_short_pct']:7.3f}%  book long {e['book_long_pct']:7.3f}%  "
              f"long+short {e['book_ls_pct']:7.3f}%  fund-leg short {('%.3f%%' % e['fund_short_pct']) if e['fund_short_pct'] is not None else 'n/a (' + str(e['n_fund_short_anchors']) + '/6 snapshots)'}")
    json.dump(rec, open(out, "w"), indent=1)


if __name__ == "__main__":
    main()
