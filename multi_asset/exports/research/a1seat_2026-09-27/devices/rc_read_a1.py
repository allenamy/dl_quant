"""rc_read_a1.py — rc_read.py (3dd2d635, the (3b) reading) with ONLY the arm labels, members, series directory and MBB block made
parameters (fresh 2026-09-27, rule DECISION_RULE_A1_seat_decomp_2026-09-27.md b41ac9985; DESCRIPTIVE, no gate, no verdict here —
the verdict is applied by the lead). Everything else is rc_read.py verbatim: frozen news_stats (7141ba42) dbar per F10 seed vs the
control arm of the same member and seed, mean over (member, seed), MBB with the frozen B / RNG. Arms: FULL (both conditions),
SEAT_ONLY (FULL seats, control King rank), COMP_ONLY (FULL King rank, control seats). Interaction = FULL − SEAT_ONLY − COMP_ONLY
(single replacements are NOT additive; the interaction is reported, never dropped). Channels as rc_decomp.py: price pnl, funding
PAID car (+ = paid), fee cst; NAV bps/day with g = pnl − car − cst.
Identity control: with the (3b) configuration (--series /dev/shm/mretrain_2026-09-26/series --control A0 --full RED --seat SEAT_ONLY
--comp COMP_ONLY --members 0 --block 30) the "segments" of the output must equal RC_READ_hybrid.json (2e75f1b3) exactly.
usage: python rc_read_a1.py <out.json> --series DIR --control P --full P --seat P --comp P --members 0[,1,...] --block N"""
import os, sys, json, hashlib, time, argparse
import numpy as np
ENG = "/dev/shm/news_2026-09-23/engine"; sys.path.insert(0, ENG)
NS_SHA = "7141ba42ab227b9f35b48acce62d5e2a2494f364fdf6a83189974cb2af67e03c"
ap = argparse.ArgumentParser(); ap.add_argument("out"); ap.add_argument("--series", required=True); ap.add_argument("--control", required=True)
ap.add_argument("--full", required=True); ap.add_argument("--seat", required=True); ap.add_argument("--comp", required=True)
ap.add_argument("--members", required=True); ap.add_argument("--block", type=int, required=True); args = ap.parse_args()
OUT = args.out; S = args.series; SEEDS = ("42", "2027"); DAY = 86400; MEMBERS = [int(k) for k in args.members.split(",")]
MSFX = "_m%d" % MEMBERS[0] if len(MEMBERS) == 1 else "_m" + "-".join(map(str, MEMBERS))
ARMS = (args.full + MSFX, args.seat + MSFX, args.comp + MSFX); CTRL = args.control + MSFX; INTER = f"INTERACTION_{args.full}_minus_SEAT_minus_COMP"
PREFIX = {ARMS[0]: args.full, ARMS[1]: args.seat, ARMS[2]: args.comp, CTRL: args.control}
PAIRS = [(k, s) for k in MEMBERS for s in SEEDS]   # member-major, seed-minor: with one member this is rc_read.py's seed order
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
rec = {"device": "rc_read_a1.py", "self_sha256": sha(os.path.abspath(__file__)), "utc": iso(time.time()), "status": "DESCRIPTIVE_NO_GATE", "GM": GM,
       "config": vars(args), "inputs": {}}
Z = {}
for lbl in (CTRL,) + ARMS:
    for k, s in PAIRS:
        p = f"{S}/SER_{PREFIX[lbl]}_m{k}_s{s}.npz"; rec["inputs"][p] = sha(p); Z[(lbl, k, s)] = np.load(p)
A = Z[(CTRL, MEMBERS[0], "42")]["anchors"].astype(np.int64)
for z in Z.values(): assert np.array_equal(z["anchors"].astype(np.int64), A)
paths = lambda lbl, k, s: [{"A": A, "r": Z[(lbl, k, s)]["r_per_path"][j]} for j in range(32)]
day = (A // DAY) * DAY
segs = {"pre2026": NS.seg_mask(A, *NS.SEG["pre2026"]), "2026": NS.seg_mask(A, "2026-01-01T00:00:00Z", iso(A[-1]))}
for y in ("2023H2", "2024", "2025"): segs[y] = NS.seg_mask(A, *NS.SEG[y])
for m in sorted({ym(t) for t in A[segs["2026"]]}): segs["2026-" + m[5:]] = np.array([ym(t) == m for t in A]) & segs["2026"]


def mbb(x):   # verbatim statistic of mr_read.mbb (frozen B, RNG); block = --block (rc_read.py: 30)
    idx = BT.mbb_indices(len(x), args.block, NS.B, NS.RNG); mb = x[idx].mean(1)
    return float(1e4 * mb.std(ddof=1)), [float(1e4 * np.percentile(mb, 2.5)), float(1e4 * np.percentile(mb, 97.5))]


def chan(lbl, c, m):
    """NAV bps/day of channel c, arm − control, mean over (member, seed) (paths averaged, full UTC days, × GM)"""
    days = NS.full_days(A, m); keep = m & np.isin(day, days); out = []
    for k, s in PAIRS:
        x = Z[(lbl, k, s)][c + "_per_path"].mean(0) - Z[(CTRL, k, s)][c + "_per_path"].mean(0)
        out.append(GM * np.bincount(np.searchsorted(days, day[keep]), weights=x[keep], minlength=len(days)).mean())
    return float(np.mean(out))


pkey = lambda k, s: s if len(MEMBERS) == 1 else f"m{k}_s{s}"
res = {}
for seg, m in segs.items():
    days = NS.full_days(A, m); row = {}
    for lbl in ARMS:
        per = {(k, s): NS.dbar(paths(lbl, k, s), paths(CTRL, k, s), m, days)[0] for k, s in PAIRS}
        x = np.mean([per[p] for p in PAIRS], axis=0)
        e = {"D_bar": float(1e4 * x.mean()), "per_seed": {pkey(*p): float(1e4 * per[p].mean()) for p in PAIRS}, "n_days": int(len(days)),
             "channels_NAV_bps_day": {c: chan(lbl, c, m) for c in ("pnl", "car", "cst", "g")}}
        if seg in ("pre2026", "2026", "2023H2", "2024", "2025"): e["MBB_SE"], e["MBB95"] = mbb(x)
        row[lbl] = e; row[lbl]["_daily"] = x
    inter = row[ARMS[0]]["_daily"] - row[ARMS[1]]["_daily"] - row[ARMS[2]]["_daily"]
    row[INTER] = {"D_bar": float(1e4 * inter.mean()),
                  "channels_NAV_bps_day": {c: row[ARMS[0]]["channels_NAV_bps_day"][c] - row[ARMS[1]]["channels_NAV_bps_day"][c]
                                           - row[ARMS[2]]["channels_NAV_bps_day"][c] for c in ("pnl", "car", "cst", "g")}}
    if "MBB_SE" in row[ARMS[0]]: row[INTER]["MBB_SE"], row[INTER]["MBB95"] = mbb(inter)
    for lbl in ARMS: row[lbl].pop("_daily")
    res[seg] = row
rec["segments"] = res
json.dump(rec, open(OUT + ".tmp", "w"), indent=1); os.replace(OUT + ".tmp", OUT)
back = json.load(open(OUT)); assert back["self_sha256"] == rec["self_sha256"] and back["segments"] == json.loads(json.dumps(res))
print("RC_READ_A1 sha=%s" % sha(OUT), flush=True)
for seg in ("pre2026", "2026"):
    print(" ", seg, json.dumps({a: {kk: res[seg][a][kk] for kk in ("D_bar", "MBB95")} for a in ARMS + (INTER,)}), flush=True)
