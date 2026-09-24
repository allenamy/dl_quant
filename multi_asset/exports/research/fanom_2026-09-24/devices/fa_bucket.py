"""fa_bucket.py — PREREG 427d76f34 / AMENDMENT 2 953df1489 §3.3: per-anchor price-channel bucketing, D vs A.
Read-only. Cuts are the ones FROZEN in amendment 2 before any of this was seen.
"""
import os, sys, json, time, hashlib, calendar
import numpy as np
WL_ = set(sys.argv[1].split(",")); _x = sorted(set(os.environ) - WL_); assert not _x, f"env outside whitelist: {_x}"
OUT = sys.argv[2]
ENG = "/dev/shm/fresh_2026-09-23/engine"; sys.path.insert(0, ENG)
import bt_tables as BT, bt_driver_lib as DL
F = "/dev/shm/fresh_2026-09-23"; N = "/dev/shm/news_2026-09-23"
CELL_D = f"{F}/runs/FRESH_s42_scaled_rule_raw_UAFE"; CELL_A = f"{N}/runs/NEWS_s42_scaled_rule_raw_UAFE"
Q33, Q67 = 0.5725596881282329, 0.7810047984528542          # FROZEN in AMENDMENT 2 §3.3
PRE = ("2023-06-30T04:00:00Z", "2025-12-31T20:00:00Z")
H4 = 14400; NP = 32

def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()
def ts(s): return calendar.timegm(time.strptime(s, "%Y-%m-%dT%H:%M:%SZ"))

def load(cell, tag):
    out = []
    for k in range(NP):
        s = f"{cell}/PATH_{tag}_seed_{k:02d}"
        J = json.load(open(s + ".json")); assert J["npz_sha256"] == sha(s + ".npz")
        assert DL.audits_clean(J["audits"]) and int(J["seed"]) == k
        out.append(BT.series_from_path(np.load(s + ".npz")))
    return out

def main():
    rec = {"device": "fa_bucket.py", "self_sha256": sha(os.path.abspath(__file__)),
           "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "prereg": {"path": "docs/PREREG_fresh_book_anomaly_2026-09-24.md", "commit": "427d76f34",
                      "amendment_2": "953df1489"},
           "frozen_cuts": {"seat_q33": Q33, "seat_q67": Q67, "source": "AMENDMENT 2 §3.3, frozen before these numbers existed"}}
    D = load(CELL_D, os.path.basename(CELL_D)); A = load(CELL_A, os.path.basename(CELL_A))
    ax = D[0]["A"]
    for p in D + A: assert np.array_equal(p["A"], ax), "engine anchor axis differs"
    pD = np.mean([p["pnl"] for p in D], axis=0)      # bps per anchor, mean over the 32 paired paths
    pA = np.mean([p["pnl"] for p in A], axis=0)
    d = pD - pA
    pre = (ax >= ts(PRE[0])) & (ax <= ts(PRE[1]))
    den = float(np.nansum(d[pre]))
    rec["denominator"] = {"segment": "pre2026", "quantity": "sum over anchors of (D - A) price channel, path-mean",
                          "value_bps": den, "unit": "bps summed over anchors", "n_anchors": int(pre.sum()),
                          "mean_bps_per_anchor": float(np.nanmean(d[pre]))}
    # seats and fold boundaries, mapped onto the ENGINE anchor axis
    leg = np.load(f"{F}/work/legs.npz"); le = leg["E_ts"].astype(np.int64)
    pos = {int(t): i for i, t in enumerate(le)}
    idx = np.array([pos.get(int(t), -1) for t in ax])
    assert (idx >= 0).all(), "an engine anchor is absent from the legs axis"
    seat = leg["WL"][idx, 0].astype(np.float64)
    KR = json.load(open(f"{F}/work/king/TRAIN_RECEIPT.json"))
    bset = {int(f["score_start"]) for f in KR["folds"]}
    dist = np.full(len(ax), 10**6, np.int64); last = -10**6
    for i, t in enumerate(ax):
        if int(t) in bset: last = i
        if last >= 0: dist[i] = i - last
    def table(name, labels, assign):
        rows = {}; tot = 0.0; n = 0
        for lab in labels:
            m = pre & assign(lab); s = float(np.nansum(d[m])); tot += s; n += int(m.sum())
            rows[lab] = {"n_anchors": int(m.sum()), "sum_bps": s,
                         "mean_bps_per_anchor": float(np.nanmean(d[m])) if m.any() else None,
                         "share_of_denominator": float(s / den) if den else None}
        closes = abs(tot - den) <= 1e-9 * max(1.0, abs(den)) and n == int(pre.sum())
        return {"rows": rows, "sum_of_shares": float(tot / den) if den else None,
                "population_anchors": int(pre.sum()), "bucketed_anchors": n, "CLOSES": bool(closes)}
    B = {}
    B["seat_tercile_frozen_cuts"] = table("seat", ["low", "mid", "high"],
        lambda l: {"low": seat <= Q33, "mid": (seat > Q33) & (seat <= Q67), "high": seat > Q67}[l])
    B["anchors_past_king_fold_boundary"] = table("dist", ["0-5", "6-20", "21-60", "61+"],
        lambda l: {"0-5": dist <= 5, "6-20": (dist > 5) & (dist <= 20), "21-60": (dist > 20) & (dist <= 60), "61+": dist > 60}[l])
    for k, v in B.items(): assert v["CLOSES"], f"bucket {k} does not close: shares {v['sum_of_shares']}, {v['bucketed_anchors']}/{v['population_anchors']}"
    rec["buckets"] = B
    rec["inputs"] = {"D_cell": CELL_D, "A_cell": CELL_A, "legs_FRESH": sha(f"{F}/work/legs.npz")}
    json.dump(rec, open(OUT + ".tmp", "w"), indent=1, default=float); os.replace(OUT + ".tmp", OUT)
    st = B["seat_tercile_frozen_cuts"]["rows"]; bd = B["anchors_past_king_fold_boundary"]["rows"]
    print(f"FA_BUCKET denominator={den:+.2f}bps over {int(pre.sum())} anchors ({rec['denominator']['mean_bps_per_anchor']:+.4f} bps/anchor) | "
          f"seat_shares={{low:{st['low']['share_of_denominator']:.3f}, mid:{st['mid']['share_of_denominator']:.3f}, high:{st['high']['share_of_denominator']:.3f}}} | "
          f"boundary_shares={{0-5:{bd['0-5']['share_of_denominator']:.3f}, 6-20:{bd['6-20']['share_of_denominator']:.3f}, 21-60:{bd['21-60']['share_of_denominator']:.3f}, 61+:{bd['61+']['share_of_denominator']:.3f}}} | "
          f"closes={{ {', '.join(k+':'+str(v['CLOSES']) for k,v in B.items())} }} receipt={sha(OUT)}", flush=True)


if __name__ == "__main__":
    main()
    # a device that produced no receipt must NOT exit 0: rc 0 with no product is the "green means nothing ran"
    # failure, and it is exactly what happened on the first invocation of this file.
    assert os.path.exists(OUT), f"device finished without writing {OUT}"
    print("FA_BUCKET_RECEIPT_WRITTEN", OUT, sha(OUT), flush=True)
