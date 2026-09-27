"""rc_read.py — reading of the (3b) single-condition cells (King root cause; DESCRIPTIVE, no gate, no verdict). Same caliber as the
family's red reading (mr_read.py red): frozen news_stats (7141ba42) dbar per F10 seed vs A0_m0 of the same seed, mean over seeds,
MBB block 30 with the frozen B / RNG. Arms: RED_m0 (both conditions), SEAT_ONLY_m0 (RED seats, A0 King rank), COMP_ONLY_m0 (RED King
rank, A0 seats). Interaction = RED − SEAT_ONLY − COMP_ONLY (single replacements are NOT additive; the interaction is reported, never
dropped). Channels as rc_decomp.py: price pnl, funding PAID car (+ = paid), fee cst; NAV bps/day with g = pnl − car − cst.
usage: python rc_read.py <out.json>"""
import os, sys, json, hashlib, time
import numpy as np
R = "/dev/shm/mretrain_2026-09-26"; S = f"{R}/series"; ENG = "/dev/shm/news_2026-09-23/engine"; sys.path.insert(0, ENG)
NS_SHA = "7141ba42ab227b9f35b48acce62d5e2a2494f364fdf6a83189974cb2af67e03c"
OUT = sys.argv[1]; SEEDS = ("42", "2027"); DAY = 86400; ARMS = ("RED_m0", "SEAT_ONLY_m0", "COMP_ONLY_m0")
iso = lambda t: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(t)))
ym = lambda t: time.strftime("%Y-%m", time.gmtime(int(t)))


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


assert sha(f"{ENG}/news_stats.py") == NS_SHA
import news_stats as NS, bt_tables as BT, bt_driver_lib as DL
NS.BT, NS.DL = BT, DL
GM = float(BT.GM) if hasattr(BT, "GM") else float(DL.GM)
rec = {"device": "rc_read.py", "self_sha256": sha(os.path.abspath(__file__)), "utc": iso(time.time()), "status": "DESCRIPTIVE_NO_GATE", "GM": GM, "inputs": {}}
Z = {}
for lbl in ("A0_m0",) + ARMS:
    for s in SEEDS:
        p = f"{S}/SER_{lbl}_s{s}.npz"; rec["inputs"][p] = sha(p); Z[(lbl, s)] = np.load(p)
A = Z[("A0_m0", "42")]["anchors"].astype(np.int64)
for z in Z.values(): assert np.array_equal(z["anchors"].astype(np.int64), A)
paths = lambda lbl, s: [{"A": A, "r": Z[(lbl, s)]["r_per_path"][j]} for j in range(32)]
day = (A // DAY) * DAY
segs = {"pre2026": NS.seg_mask(A, *NS.SEG["pre2026"]), "2026": NS.seg_mask(A, "2026-01-01T00:00:00Z", iso(A[-1]))}
for y in ("2023H2", "2024", "2025"): segs[y] = NS.seg_mask(A, *NS.SEG[y])
for m in sorted({ym(t) for t in A[segs["2026"]]}): segs["2026-" + m[5:]] = np.array([ym(t) == m for t in A]) & segs["2026"]


def mbb(x):   # verbatim statistic of mr_read.mbb (frozen block 30, B, RNG)
    idx = BT.mbb_indices(len(x), 30, NS.B, NS.RNG); mb = x[idx].mean(1)
    return float(1e4 * mb.std(ddof=1)), [float(1e4 * np.percentile(mb, 2.5)), float(1e4 * np.percentile(mb, 97.5))]


def chan(lbl, c, m):
    """NAV bps/day of channel c, arm − A0, mean over seeds (paths averaged, full UTC days, × GM)"""
    days = NS.full_days(A, m); keep = m & np.isin(day, days); out = []
    for s in SEEDS:
        x = Z[(lbl, s)][c + "_per_path"].mean(0) - Z[("A0_m0", s)][c + "_per_path"].mean(0)
        out.append(GM * np.bincount(np.searchsorted(days, day[keep]), weights=x[keep], minlength=len(days)).mean())
    return float(np.mean(out))


res = {}
for k, m in segs.items():
    days = NS.full_days(A, m); row = {}
    for lbl in ARMS:
        per = {s: NS.dbar(paths(lbl, s), paths("A0_m0", s), m, days)[0] for s in SEEDS}
        x = np.mean([per[s] for s in SEEDS], axis=0)
        e = {"D_bar": float(1e4 * x.mean()), "per_seed": {s: float(1e4 * per[s].mean()) for s in SEEDS}, "n_days": int(len(days)),
             "channels_NAV_bps_day": {c: chan(lbl, c, m) for c in ("pnl", "car", "cst", "g")}}
        if k in ("pre2026", "2026", "2023H2", "2024", "2025"): e["MBB_SE"], e["MBB95"] = mbb(x)
        row[lbl] = e; row[lbl]["_daily"] = x
    inter = row["RED_m0"]["_daily"] - row["SEAT_ONLY_m0"]["_daily"] - row["COMP_ONLY_m0"]["_daily"]
    row["INTERACTION_RED_minus_SEAT_minus_COMP"] = {"D_bar": float(1e4 * inter.mean()),
                                                    "channels_NAV_bps_day": {c: row["RED_m0"]["channels_NAV_bps_day"][c] - row["SEAT_ONLY_m0"]["channels_NAV_bps_day"][c]
                                                                             - row["COMP_ONLY_m0"]["channels_NAV_bps_day"][c] for c in ("pnl", "car", "cst", "g")}}
    if "MBB_SE" in row["RED_m0"]: row["INTERACTION_RED_minus_SEAT_minus_COMP"]["MBB_SE"], row["INTERACTION_RED_minus_SEAT_minus_COMP"]["MBB95"] = mbb(inter)
    for lbl in ARMS: row[lbl].pop("_daily")
    res[k] = row
rec["segments"] = res
json.dump(rec, open(OUT + ".tmp", "w"), indent=1); os.replace(OUT + ".tmp", OUT)
back = json.load(open(OUT)); assert back["self_sha256"] == rec["self_sha256"]
print("RC_READ sha=%s" % sha(OUT), flush=True)
for k in ("pre2026", "2026"):
    print(" ", k, json.dumps({a: {kk: res[k][a][kk] for kk in ("D_bar", "MBB95")} for a in ARMS + ("INTERACTION_RED_minus_SEAT_minus_COMP",)}), flush=True)
