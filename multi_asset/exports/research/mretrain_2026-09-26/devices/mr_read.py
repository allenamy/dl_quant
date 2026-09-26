"""mr_read.py — reading device of the King monthly-retrain family. It applies docs/DECISION_RULE_king_monthly_retrain_2026-09-26.md
(lead, 1f2f5c4e9) mechanically; it adds NO threshold of its own. Committed before any engine series of the family existed.

  mode red    : §0.4 red control (RED_m0 vs A0_m0, both F10 seeds) + engine-reproducibility control (A0_m0 series == the in-service
                NC X baseline series, bitwise). FAIL of either => the family stops.
  mode family : §1-§4 for arms A1 and A3 (and A2/A4 if their series exist), each judged independently against A0 member by member.

Caliber: frozen news_stats (7141ba42) dbar / seg_mask / full_days / boot constants (B, RNG), imported and called.
Named approximations (the saved per-path series hold 4h-anchor returns only):
  - maxDD is computed on the 4h-anchor compounded NAV of each path (news_stats uses a 5-minute maxDD from the full cell);
  - R-P touches = paths whose 4h NAV from 2023-06-30T04Z ever falls to <= -25 % (news_stats' R-P threshold and base).
usage: env -i PATH=/usr/bin:/bin HOME=/root python -B mr_read.py PATH,HOME,LC_CTYPE red|family <out.json>
"""
import os, sys, json, glob, hashlib, time, calendar
import numpy as np

WL_ = set(sys.argv[1].split(",")); _x = sorted(set(os.environ) - WL_); assert not _x, f"env outside whitelist: {_x}"
MODE, OUT = sys.argv[2], sys.argv[3]
R = "/dev/shm/mretrain_2026-09-26"; S = f"{R}/series"; ENG = "/dev/shm/news_2026-09-23/engine"
NS_SHA = "7141ba42ab227b9f35b48acce62d5e2a2494f364fdf6a83189974cb2af67e03c"
EXT = {"42": ("/dev/shm/fanom_2026-09-24/receipts/SER_EXT_NEWS2_s42X.npz", "074e8fb25238e5a2b036bf98e105b33d7a7c6bd82a98a009320749e09b330564"),
       "2027": ("/dev/shm/fanom_2026-09-24/receipts/SER_EXT_NEWS2_s2027X.npz", "421ff513a07befd812ca285102de8693038bdf7da09790fcc762a84dbf13c039")}
SEEDS = ("42", "2027"); MEMBERS = tuple(range(8))
KING_A0_TRAIN_END = None   # filled from the A0_m0 King receipt (fold max_train_label_end)
sys.path.insert(0, ENG)


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


assert sha(f"{ENG}/news_stats.py") == NS_SHA
import news_stats as NS
import bt_tables as BT, bt_driver_lib as DL
NS.BT, NS.DL = BT, DL
iso = lambda t: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(t)))
ts = lambda s: calendar.timegm(time.strptime(s, "%Y-%m-%dT%H:%M:%SZ"))
rec = {"device": "mr_read.py", "self_sha256": sha(os.path.abspath(__file__)), "argv": sys.argv, "mode": MODE,
       "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "rule": "docs/DECISION_RULE_king_monthly_retrain_2026-09-26.md (1f2f5c4e9)",
       "inputs": {}, "controls": {}}


def load(lbl, seed):
    p = f"{S}/SER_{lbl}_s{seed}.npz"
    rec["inputs"][f"{lbl}_s{seed}"] = sha(p)
    z = np.load(p); A = z["anchors"].astype(np.int64)
    return {"A": A, "paths": [{"A": A, "r": z["r_per_path"][k]} for k in range(32)],
            "ch": {k: z[k + "_per_path"] for k in ("r", "pnl", "car", "cst", "unk", "g", "tau", "hold", "halt")}}


def masks_for(A):
    end = iso(A[-1])
    m = {"pre2026": NS.seg_mask(A, *NS.SEG["pre2026"]), "2026": NS.seg_mask(A, "2026-01-01T00:00:00Z", end),
         "2026_SEG_truncated": NS.seg_mask(A, *NS.SEG["2026"]), "2023H2": NS.seg_mask(A, *NS.SEG["2023H2"]),
         "2024": NS.seg_mask(A, *NS.SEG["2024"]), "2025": NS.seg_mask(A, *NS.SEG["2025"])}
    return m, {k: NS.full_days(A, v) for k, v in m.items()}


def daily_d(x, y, m, days):
    db, _ = NS.dbar(x["paths"], y["paths"], m, days); return db


def mbb(x):
    """(SE of the mean, MBB95 [lo, hi]) of a daily series with the frozen block 30, B and RNG"""
    idx = BT.mbb_indices(len(x), 30, NS.B, NS.RNG); mb = x[idx].mean(1)
    return float(1e4 * mb.std(ddof=1)), [float(1e4 * np.percentile(mb, 2.5)), float(1e4 * np.percentile(mb, 97.5))]


def maxdd_mean(ser, m):
    out = []
    for r in ser["ch"]["r"]:
        nav = np.cumprod(1.0 + r[m]); peak = np.maximum.accumulate(nav); out.append(float((1.0 - nav / peak).max()))
    return float(np.mean(out))


def rp_touches(ser):
    base = ts("2023-06-30T04:00:00Z"); m = ser["A"] >= base; n = 0
    for r in ser["ch"]["r"]:
        nav = np.cumprod(1.0 + r[m]); n += int((nav - 1.0 <= -0.25).any())
    return n


FAIL = []
if MODE == "red":
    per = {}; A = None
    for s in SEEDS:
        a0, red = load("A0_m0", s), load("RED_m0", s)
        ext_p, ext_sha = EXT[s]
        ok_sha = sha(ext_p) == ext_sha; ze = np.load(ext_p)
        rep = ok_sha and np.array_equal(ze["anchors"].astype(np.int64), a0["A"]) and ze["r_per_path"].tobytes() == a0["ch"]["r"].tobytes()
        rec["controls"][f"engine_reproduces_in_service_X_s{s}"] = {"PASS": bool(rep), "reference": ext_p, "reference_sha_ok": ok_sha}
        if not rep: FAIL.append(f"A0_m0 s{s} series != in-service X baseline")
        m, d = masks_for(a0["A"])
        per[s] = {k: daily_d(red, a0, m[k], d[k]) for k in ("pre2026", "2026")}
    out = {}
    for k in ("pre2026", "2026"):
        x = np.mean([per[s][k] for s in SEEDS], axis=0); se, ci = mbb(x)
        out[k] = {"D_bar": float(1e4 * x.mean()), "per_seed": {s: float(1e4 * per[s][k].mean()) for s in SEEDS}, "MBB_SE": se, "MBB95": ci,
                  "PASS": bool(1e4 * x.mean() < 0 and ci[1] < 0)}
    rec["red_control"] = out
    rec["RED_CONTROL_PASS"] = bool(all(v["PASS"] for v in out.values()))
    if not rec["RED_CONTROL_PASS"]: FAIL.append("red control: expected D<0 with MBB95 upper <0 in both segments")
    rec["controls_failed"] = FAIL; rec["FAMILY_MAY_CONTINUE"] = not FAIL
else:
    # ---------------------------------------------------------------- family
    kr = json.load(open(f"{R}/arms/A0_m0/work/king/TRAIN_RECEIPT.json"))
    a0_folds = sorted((f["score_start"], f["max_train_label_end"]) for f in kr["folds"])
    def a0_age(day):
        k = max(i for i, (st, _) in enumerate(a0_folds) if st <= day); return (day - a0_folds[k][1]) / 86400.0
    arms = [a for a in ("A1", "A3", "A2", "A4") if all(os.path.exists(f"{S}/SER_{a}_m{m}_s{s}.npz") for m in MEMBERS for s in SEEDS)]
    # A1 (main arm) and A0 must be complete; A3 is judged independently (rule §2) and was deferred by the lead until A1's verdict
    # exists (fresh2 2026-09-27, before any engine series of the family) -- it is read when all its series exist, never required
    missing = [f"{a}_m{m}_s{s}" for a in ("A1",) for m in MEMBERS for s in SEEDS if not os.path.exists(f"{S}/SER_{a}_m{m}_s{s}.npz")]
    missing += [f"A0_m{m}_s{s}" for m in MEMBERS for s in SEEDS if not os.path.exists(f"{S}/SER_A0_m{m}_s{s}.npz")]
    if missing:
        rec["STATUS"] = "INCOMPLETE"; rec["missing"] = missing
        json.dump(rec, open(OUT + ".tmp", "w"), indent=1); os.replace(OUT + ".tmp", OUT); print("MR_READ INCOMPLETE", len(missing)); sys.exit(4)
    A0 = {(m, s): load(f"A0_m{m}", s) for m in MEMBERS for s in SEEDS}
    A = A0[(0, "42")]["A"]; M, Dd = masks_for(A)
    rec["arms"] = {}
    for arm in arms:
        X = {(m, s): load(f"{arm}_m{m}", s) for m in MEMBERS for s in SEEDS}
        for v in X.values(): assert np.array_equal(v["A"], A)
        segs = {}
        daily = {}
        for k in ("pre2026", "2026", "2026_SEG_truncated", "2023H2", "2024", "2025"):
            dd = {ms: daily_d(X[ms], A0[ms], M[k], Dd[k]) for ms in X}
            daily[k] = dd
            dms = {f"m{m}_s{s}": float(1e4 * dd[(m, s)].mean()) for (m, s) in dd}
            vals = np.array(list(dms.values()))
            xbar = np.mean(list(dd.values()), axis=0)
            se_mbb, ci = mbb(xbar)
            se = max(se_mbb, float(vals.std(ddof=1) / np.sqrt(len(vals))))
            segs[k] = {"D_bar": float(vals.mean()), "SE": se, "SE_MBB30": se_mbb, "SE_members": float(vals.std(ddof=1) / np.sqrt(len(vals))),
                       "MBB95": ci, "n_positive": int((vals > 0).sum()), "n": int(len(vals)),
                       "seed_means": {s: float(np.mean([dms[f"m{m}_s{s}"] for m in MEMBERS])) for s in SEEDS}, "per_member_seed": dms}
        # guards
        g = {}
        for k in ("pre2026", "2026"):
            dd_arm = float(np.mean([maxdd_mean(X[ms], M[k]) for ms in X])); dd_a0 = float(np.mean([maxdd_mean(A0[ms], M[k]) for ms in X]))
            g[f"maxDD_{k}"] = {"arm": dd_arm, "A0": dd_a0, "worse_by_pp": 100 * (dd_arm - dd_a0), "PASS": bool(dd_arm - dd_a0 <= 0.03),
                               "note": "4h-anchor NAV maxDD (named approximation of the 5-minute maxDD)"}
        worst = {}
        for yr in ("2024", "2025"):
            worst[yr] = {"D_bar": segs[yr]["D_bar"], "MBB95": segs[yr]["MBB95"], "VETO": bool(segs[yr]["D_bar"] < 0 and segs[yr]["MBB95"][1] < 0)}
        g["worst_complete_year"] = {"years": worst, "PASS": not any(v["VETO"] for v in worst.values()),
                                    "partial_years_reported_only": {k: segs[k]["D_bar"] for k in ("2023H2", "2026")}}
        g["switch_anchor_parity"] = {"status": "PENDING (rule section 3: must be completed before any recommendation; not part of this device)"}
        guards_pass = all(v["PASS"] for kk, v in g.items() if kk != "switch_anchor_parity")
        s26, spre = segs["2026"], segs["pre2026"]
        improve = (s26["D_bar"] >= max(1.0, 3 * s26["SE"]) and s26["n_positive"] >= 12 and all(v > 0 for v in s26["seed_means"].values())
                   and spre["D_bar"] >= 0 and guards_pass)
        noninf = all(segs[k]["D_bar"] >= -max(0.5, 3.5 * segs[k]["SE"]) for k in ("pre2026", "2026")) and guards_pass
        reject = any(segs[k]["D_bar"] < 0 and segs[k]["MBB95"][1] < 0 for k in ("pre2026", "2026")) or not guards_pass
        # the rule lists IMPROVE / NON_INFERIOR / REJECT / UNDECIDED without saying which wins if NON_INFERIOR and REJECT both hold;
        # this device does not decide it: that case is reported as CONFLICT for the rule's author
        if improve: verdict = "IMPROVE"
        elif noninf and reject: verdict = "CONFLICT_NON_INFERIOR_AND_REJECT (rule author to rule)"
        elif reject: verdict = "REJECT"
        elif noninf: verdict = "NON_INFERIOR"
        else: verdict = "UNDECIDED"
        # required reports (descriptive)
        rep = {"channels_pre2026_and_2026": {}, "means": {}, "rp_touches": {}, "king_ic": {}}
        for k in ("pre2026", "2026"):
            m = M[k]
            rep["channels_pre2026_and_2026"][k] = {c: float(np.mean([1e4 * (X[ms]["ch"][c].mean(0)[m] - A0[ms]["ch"][c].mean(0)[m]).sum() for ms in X]))
                                                    for c in ("pnl", "car", "cst", "unk", "g")}
            rep["means"][k] = {c: {"arm": float(np.mean([X[ms]["ch"][c][:, m].mean() for ms in X])),
                                   "A0": float(np.mean([A0[ms]["ch"][c][:, m].mean() for ms in X]))} for c in ("tau", "hold", "halt")}
        rep["rp_touches"] = {"arm_mean_paths": float(np.mean([rp_touches(X[ms]) for ms in X])),
                             "A0_mean_paths": float(np.mean([rp_touches(A0[ms]) for ms in X]))}
        for m in MEMBERS:
            for lbl in (f"{arm}_m{m}", f"A0_m{m}"):
                pr = f"{R}/arms/{lbl}/work/king/TRAIN_RECEIPT.json"
                if os.path.exists(pr):
                    fr = json.load(open(pr))["folds"]; rep["king_ic"][lbl] = float(np.average([f["mean_cs_spearman"] for f in fr], weights=[f["n_cs_anchors"] for f in fr]))
        pubs = {}
        for m in MEMBERS:
            for s in SEEDS:
                for lbl in (f"{arm}_m{m}", f"A0_m{m}"):
                    tr = f"{R}/arms/{lbl}/work/combo_s{s}/TARGET_RECEIPT.json"
                    if os.path.exists(tr):
                        pol = json.load(open(tr))["policies"]["scaled_diagnostic"]["reasons"]; pubs[f"{lbl}_s{s}"] = pol.get("publish")
        rep["publish_anchors_scaled"] = pubs
        # staleness (rule §4 and §6): per-day d bucketed by A0 annual-model age, and by days since the arm's last refit
        stale = {}
        for k in ("pre2026", "2026"):
            xbar = np.mean(list(daily[k].values()), axis=0); days = Dd[k]
            age = np.array([a0_age(int(dy)) for dy in days])
            hi = age >= 183
            stale[k] = {"A0_age_ge183_minus_lt183": float(1e4 * (xbar[hi].mean() - xbar[~hi].mean())) if hi.any() and (~hi).any() else None,
                        "n_days_ge183": int(hi.sum()), "n_days_lt183": int((~hi).sum()),
                        "confound": "A0 age is collinear with month of year (G4 section 2)"}
            ar = json.load(open(f"{R}/arms/{arm}_m0/work/king/TRAIN_RECEIPT.json"))["folds"]
            starts = np.array(sorted(f["score_start"] for f in ar))
            since = np.array([(dy - starts[starts <= dy].max()) / 86400.0 for dy in days])
            bk = {"[0,10)": since < 10, "[10,20)": (since >= 10) & (since < 20), "[20,+)": since >= 20}
            stale[k]["by_days_since_arm_refit"] = {b: (float(1e4 * xbar[sel].mean()) if sel.any() else None) for b, sel in bk.items()}
        rep["staleness"] = stale
        rec["arms"][arm] = {"segments": segs, "guards": g, "VERDICT": verdict,
                            "tests": {"IMPROVE": bool(improve), "NON_INFERIOR": bool(noninf), "REJECT": bool(reject)}, "reports": rep}
    rec["STATUS"] = "OK"
json.dump(rec, open(OUT + ".tmp", "w"), indent=1, default=float); os.replace(OUT + ".tmp", OUT)
back = json.load(open(OUT)); assert back["self_sha256"] == rec["self_sha256"]
print("MR_READ mode=%s sha=%s FAIL=%s" % (MODE, sha(OUT), FAIL), flush=True)
if MODE == "red":
    for k, v in rec["red_control"].items(): print("  red", k, json.dumps(v))
else:
    for arm, v in rec["arms"].items():
        print("  %s VERDICT=%s" % (arm, v["VERDICT"]), json.dumps({k: {kk: v["segments"][k][kk] for kk in ("D_bar", "SE", "n_positive")} for k in ("pre2026", "2026")}))
