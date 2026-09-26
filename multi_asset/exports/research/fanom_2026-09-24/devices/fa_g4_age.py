"""fa_g4_age.py — G4 test: does FRESH's King advantage grow with the annual King's age? Frozen rules:
docs/PREREG_G4_king_age_test_2026-09-26.md (committed with this file, before any run). Read-only.
usage: env -i PATH=/usr/bin:/bin HOME=/root python -B fa_g4_age.py PATH,HOME,LC_CTYPE <out.json>"""
import os, sys, json, hashlib, time, calendar
import numpy as np
WL_ = set(sys.argv[1].split(",")); _x = sorted(set(os.environ) - WL_); assert not _x, f"env outside whitelist: {_x}"
OUT = sys.argv[2]
R = "/dev/shm/fanom_2026-09-24/receipts"; ENG = "/dev/shm/news_2026-09-23/engine"
NS_SHA = "7141ba42ab227b9f35b48acce62d5e2a2494f364fdf6a83189974cb2af67e03c"
LADREAD_SHA = "7600123b00e9340812c1e027b0ca7641cc6de20d9a311560e15defcd547197bc"
KREC = ("/dev/shm/news_2026-09-23/work/king/TRAIN_RECEIPT.json", "decd5b1de03f8fe83f399a3832ed78a7f145b539392ece4e4c96b364e20fb1de")
sys.path.insert(0, ENG)


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


assert sha(f"{ENG}/news_stats.py") == NS_SHA and sha(f"{R}/FA_LADREAD.json") == LADREAD_SHA and sha(KREC[0]) == KREC[1]
import news_stats as NS
import bt_tables as BT, bt_driver_lib as DL
NS.BT, NS.DL = BT, DL
LR = json.load(open(f"{R}/FA_LADREAD.json"))
folds = sorted((f["score_start"], f["max_train_label_end"]) for f in json.load(open(KREC[0]))["folds"])
iso = lambda t: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(t)))


BASE_SHA = {"SER_LAD_BASE_NEWS_s42X.npz": "1aa6a4cd08386859d855613eb159eb7b57bb312291d6f3fba688fd320fe10c45",
            "SER_LAD_BASE_NEWS_s2027X.npz": "4d7dc7444b36de1a507a8a5271221c73a1a90f59b1564ae4646599ff3b7af2d4",
            "SER_LAD_BASE_FRESH_s42X.npz": "5244bf98969120be13b011c5219587623bf12493ddca75c0f0a4f89af3475ad5",
            "SER_LAD_BASE_FRESH_s2027X.npz": "14162531e8eeb54455afbbea1dd0e1b60859b764a86cc970bcaeb52ad79502f1"}


def age_days(day):
    k = max(i for i, (s, _) in enumerate(folds) if s <= day)
    return (day - folds[k][1]) / 86400.0


def slope(x, y):
    xm = x - x.mean(); return float((xm * (y - y.mean())).sum() / (xm * xm).sum())


def boot_slope(x, y, block=30):
    idx = BT.mbb_indices(len(x), block, NS.B, NS.RNG)
    s = np.array([slope(x[i], y[i]) for i in idx]); return [float(np.percentile(s, 2.5)), float(np.percentile(s, 97.5))]


def boot_diff(x, y, block=30):
    idx = BT.mbb_indices(len(x), block, NS.B, NS.RNG); out = []
    for i in idx:
        hi = x[i] >= 183
        if hi.any() and (~hi).any(): out.append(y[i][hi].mean() - y[i][~hi].mean())
    return [float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5))], len(out)


rec = {"device": "fa_g4_age.py", "self_sha256": sha(os.path.abspath(__file__)), "argv": sys.argv,
       "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "prereg": "docs/PREREG_G4_king_age_test_2026-09-26.md",
       "folds_NEW_S_king": [{"score_start": iso(s), "max_train_label_end": iso(e)} for s, e in folds], "controls": {}, "seeds": {}}
FAIL = []
for seed in ("42", "2027"):
    S = LR["seeds"][seed]
    zb = f"{R}/SER_LAD_BASE_NEWS_s{seed}X.npz"; assert sha(zb) == BASE_SHA[os.path.basename(zb)]; A = np.load(zb)["anchors"].astype(np.int64)
    base = [{"A": A, "r": r} for r in np.load(zb)["r_per_path"]]
    end = iso(A[-1])
    masks = {"pre2026": NS.seg_mask(A, *NS.SEG["pre2026"]), "2026_to_axis_end": NS.seg_mask(A, "2026-01-01T00:00:00Z", end),
             "fullwin_to_axis_end": NS.seg_mask(A, NS.SEG["2023H2"][0], end)}
    days = {k: NS.full_days(A, m) for k, m in masks.items()}
    arms = {"KZ": f"SER_LAD_KZ_s{seed}.npz", "KZWL": f"SER_LAD_KZWL_s{seed}.npz", "G_FRESH": f"SER_LAD_BASE_FRESH_s{seed}X.npz"}
    s_out = {}
    for arm, fn in arms.items():
        want = BASE_SHA.get(fn) or S["arms"][arm]["series_sha256"]
        if sha(f"{R}/{fn}") != want: FAIL.append(f"sha {fn}"); continue
        z = np.load(f"{R}/{fn}"); assert np.array_equal(z["anchors"].astype(np.int64), A)
        x = [{"A": A, "r": r} for r in z["r_per_path"]]
        a_out = {}
        for key in ("pre2026", "2026_to_axis_end", "fullwin_to_axis_end"):
            db, _ = NS.dbar(x, base, masks[key], days[key]); y = 1e4 * db
            ag = np.array([age_days(int(d)) for d in days[key]])
            if key in ("pre2026", "2026_to_axis_end"):
                filed = (S["G"][key]["frozen_dbar_bps_per_day"] if arm == "G_FRESH" else S["arms"][arm][key]["d_bps_per_day"])
                ok = abs(y.mean() - filed) <= 1e-9
                rec["controls"][f"C0_{arm}_s{seed}_{key}"] = {"mean": float(y.mean()), "filed": filed, "PASS": ok}
                if not ok: FAIL.append(f"C0 {arm} s{seed} {key}")
            syn = 0.02 * ag / 100
            c1 = abs(slope(ag, syn) - 0.0002) <= 1e-12
            if not c1: FAIL.append(f"C1 {arm} {key}")
            sl = slope(ag, y) * 100
            ci = [v * 100 for v in boot_slope(ag, y)]
            dci, nd = boot_diff(ag, y)
            hi = ag >= 183
            a_out[key] = {"n_days": int(len(y)), "mean_d": float(y.mean()), "age_range_days": [float(ag.min()), float(ag.max())],
                          "slope_bps_per_day_per_100d": sl, "slope_ci95": ci,
                          "old_minus_young_mean": float(y[hi].mean() - y[~hi].mean()) if hi.any() and (~hi).any() else None,
                          "old_minus_young_ci95": dci, "n_old_days": int(hi.sum()), "n_young_days": int((~hi).sum())}
        s_out[arm] = a_out
    rec["seeds"][seed] = s_out
rec["controls"]["C1_known_answer"] = "PASS" if not any(f.startswith("C1") for f in FAIL) else "FAIL"
rec["controls_failed"] = FAIL


def reading(arm):
    fw = [rec["seeds"][s][arm]["fullwin_to_axis_end"] for s in ("42", "2027")]
    seg = [(rec["seeds"][s][arm]["pre2026"]["slope_bps_per_day_per_100d"], rec["seeds"][s][arm]["2026_to_axis_end"]["slope_bps_per_day_per_100d"]) for s in ("42", "2027")]
    segci = [(rec["seeds"][s][arm]["pre2026"]["slope_ci95"], rec["seeds"][s][arm]["2026_to_axis_end"]["slope_ci95"]) for s in ("42", "2027")]
    if all(f["slope_ci95"][0] > 0 for f in fw) and all(a > 0 and b > 0 for a, b in seg): return "SUPPORTS_H_R"
    if any(f["slope_ci95"][1] < 0 for f in fw): return "AGAINST_H_R"
    if all((a > 0) != (b > 0) and (ca[0] > 0 or ca[1] < 0) and (cb[0] > 0 or cb[1] < 0) for (a, b), (ca, cb) in zip(seg, segci)): return "AGAINST_H_R"
    return "UNRESOLVED"


rec["READING"] = {"KZ": reading("KZ"), "KZWL_report_only": reading("KZWL"), "G_report_only": reading("G_FRESH")}
rec["STATUS"] = "UNAVAILABLE" if FAIL else "OK"
json.dump(rec, open(OUT + ".tmp", "w"), indent=1); os.replace(OUT + ".tmp", OUT)
print("FA_G4_AGE STATUS=%s sha=%s FAIL=%s" % (rec["STATUS"], sha(OUT), FAIL))
for s in ("42", "2027"):
    for arm, a in rec["seeds"][s].items():
        for k, v in a.items():
            print("  s%-4s %-7s %-20s mean %+7.3f slope/100d %+7.3f %s  old-young %s %s  ages %s"
                  % (s, arm, k, v["mean_d"], v["slope_bps_per_day_per_100d"], [round(c, 2) for c in v["slope_ci95"]],
                     None if v["old_minus_young_mean"] is None else round(v["old_minus_young_mean"], 3),
                     [round(c, 2) for c in v["old_minus_young_ci95"]], [round(c) for c in v["age_range_days"]]))
print("  READING", rec["READING"])
