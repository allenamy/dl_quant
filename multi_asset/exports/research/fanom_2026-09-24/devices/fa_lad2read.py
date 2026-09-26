"""fa_lad2read.py — FRESH ladder TWO ENDS on the clean RN8 (R25-05) = the Q2 four cells.
Frozen rules: docs/PREREG_fresh_ladder_ends_cleanRN8_2026-09-26.md (committed together with this file, before any run).

Cells (model x RN8): N_old = NEW_S x fund_replay RN8, N_cln = NEW_S x NC legs 9ee5886f RN8, F_old / F_cln likewise.
  G_old = dbar(F_old - N_old), G_cln = dbar(F_cln - N_cln), dG = G_cln - G_old (== e_F - e_N, the Q2 interaction),
  e_N = dbar(N_cln - N_old), e_F = dbar(F_cln - F_old).
CALIBER: frozen news_stats.dbar / boot / seg_mask (7141ba42), imported and called; masks exactly as fa_ladread.py.
Every input series is checked against a LITERAL sha written below (not copied from a receipt at run time).

usage: env -i PATH=/usr/bin:/bin HOME=/root python -B fa_lad2read.py PATH,HOME,LC_CTYPE <out.json>
"""
import os, sys, json, hashlib, time, calendar, subprocess
import numpy as np

WL_ = set(sys.argv[1].split(",")); _x = sorted(set(os.environ) - WL_); assert not _x, f"env outside whitelist: {_x}"
OUT = sys.argv[2]
R = "/dev/shm/fanom_2026-09-24/receipts"
ENG = "/dev/shm/news_2026-09-23/engine"
FRESH = "/dev/shm/fresh_2026-09-23"
SCR = "/dev/shm/fanom_2026-09-24/lad2read"
NS_SHA = "7141ba42ab227b9f35b48acce62d5e2a2494f364fdf6a83189974cb2af67e03c"
LADREAD_SHA = "7600123b00e9340812c1e027b0ca7641cc6de20d9a311560e15defcd547197bc"
SIGMA = 1.0437
SEEDS = ("42", "2027")
ARMS = ("KZ", "WL", "F10", "KZWL")
SER = {  # literal expected shas (RECOVERY_INVENTORY_2026-09-26.json + FA_LADREAD.json series_sha256)
    ("N_old", "42"): ("SER_LAD_BASE_NEWS_s42X.npz", "1aa6a4cd08386859d855613eb159eb7b57bb312291d6f3fba688fd320fe10c45"),
    ("N_old", "2027"): ("SER_LAD_BASE_NEWS_s2027X.npz", "4d7dc7444b36de1a507a8a5271221c73a1a90f59b1564ae4646599ff3b7af2d4"),
    ("F_old", "42"): ("SER_LAD_BASE_FRESH_s42X.npz", "5244bf98969120be13b011c5219587623bf12493ddca75c0f0a4f89af3475ad5"),
    ("F_old", "2027"): ("SER_LAD_BASE_FRESH_s2027X.npz", "14162531e8eeb54455afbbea1dd0e1b60859b764a86cc970bcaeb52ad79502f1"),
    ("N_cln", "42"): ("SER_LAD2_CLEANRN8_NONE_s42.npz", "9ecf57b0fbb99c5f620f823dc12b243c14ef7636f8ca4200b80ffb29eb1f2c82"),
    ("N_cln", "2027"): ("SER_LAD2_CLEANRN8_NONE_s2027.npz", "eb9d2f04cf90ad1a4f01473de8e04b6a2330b5701b4c4f974a0769d4f72b279d"),
    ("F_cln", "42"): ("SER_LAD2_CLEANRN8_ALLNEW_s42.npz", "30649459b7ccb1ece44938918b8cf2373bb61c97a8e02b9d143da36961fd9ee5"),
    ("F_cln", "2027"): ("SER_LAD2_CLEANRN8_ALLNEW_s2027.npz", "881cbe030d359655008b1392d7ef917d1c750a8c7f043b9528b8cdb63d83be89"),
}
# base targets (old values). NEW_S: existing file at its pinned sha. FRESH: freed, so REGENERATED and must hit the pin.
BASE_TGT = {("N", "42"): ("/dev/shm/news_2026-09-23/targets/TARGETS_NEWS_s42.npz",
                          "1014579872f0471dae0eeb5377705b7b8fdc65a826c62e48f74de48c4f42f330"),
            ("N", "2027"): ("/dev/shm/news_2026-09-23/targets/TARGETS_NEWS_s2027.npz",
                            "ac329ad95fe03b71bb7e6938df7ee07e2038386d2003b91e36737cba5356d01a"),
            ("F", "42"): (f"{SCR}/BASE_FRESH_s42X/TARGETS.npz",
                          "5ee47aa2abca8ac2f03ae974e9c9fbeaf2c18c72343e2aa99b7081641224a027"),
            ("F", "2027"): (f"{SCR}/BASE_FRESH_s2027X/TARGETS.npz",
                            "88dd4d9aee35ace8ce66ff302173dd408a610074312b2ab2361c84e4d2524970")}
END_TGT = {("N", "42"): ("/dev/shm/fanom_2026-09-24/ladder2/CLEANRN8_NONE_s42/TARGETS.npz",
                         "e7bac09f1f3fd79294486b763f75de22ef50136fd5931898780b8f58fd1a596d"),
           ("N", "2027"): ("/dev/shm/fanom_2026-09-24/ladder2/CLEANRN8_NONE_s2027/TARGETS.npz",
                           "682a25d7e4e9523d7dafbd0318a9ade8655c2fda4e19d43c8bd6921b475b4fc6"),
           ("F", "42"): ("/dev/shm/fanom_2026-09-24/ladder2/CLEANRN8_ALLNEW_s42/TARGETS.npz",
                         "486de816b45137212c9d827cb0ad2afcf92fbdc2ca2a13c8e4da04997d9d062a"),
           ("F", "2027"): ("/dev/shm/fanom_2026-09-24/ladder2/CLEANRN8_ALLNEW_s2027/TARGETS.npz",
                           "cbfe32221ddfb374edb4f204ca8d614589d6ac2bd9fc35f393971276ac2a7ab3")}
LEGS_OLD = ("/dev/shm/news_2026-09-23/work/legs.npz", "18999e169c6b68546271f8194fd74eaa79041d1967ba44df978f4cbea33d6bd5")
LEGS_CLN = ("/dev/shm/news2_2026-09-23/work/legs.npz", "9ee5886f37d1727c306d0fb692d2cad1e6400ae13f19d5cd4e280dc59f208f65")
sys.path.insert(0, ENG)


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


assert sha(os.path.join(ENG, "news_stats.py")) == NS_SHA, "news_stats.py is not the frozen caliber"
import news_stats as NS
import bt_tables as BT, bt_driver_lib as DL
NS.BT, NS.DL = BT, DL
iso = lambda t: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(t)))

rec = {"device": "fa_lad2read.py", "self_sha256": sha(os.path.abspath(__file__)), "argv": sys.argv,
       "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
       "prereg": "docs/PREREG_fresh_ladder_ends_cleanRN8_2026-09-26.md",
       "caliber": {"news_stats.py": NS_SHA}, "controls": {}, "seeds": {}}
FAIL = []


def load_series(key, seed):
    name, want = SER[(key, seed)]
    p = f"{R}/{name}"
    got = sha(p)
    if got != want: FAIL.append(f"C0 {key} s{seed}: series sha {got[:12]} != literal {want[:12]}")
    z = np.load(p)
    A = z["anchors"].astype(np.int64)
    return {"A": A, "paths": [{"A": A, "r": z["r_per_path"][k]} for k in range(z["r_per_path"].shape[0])],
            "ch": {k: z[k + "_per_path"] for k in ("r", "pnl", "car", "cst", "unk", "g", "tau", "hold", "halt")}}


def rows(z, pol):
    kind, off, idx, val = z[pol + "_kind"], z[pol + "_off"], z[pol + "_idx"], z[pol + "_val"]
    return kind, off, idx, val


def first_row_diff(za, zb):
    """first anchor index where either policy's target row differs bitwise; None if identical"""
    assert np.array_equal(za["anchor"], zb["anchor"]), "target anchor axes differ"
    first = None
    for pol in ("scaled", "lit"):
        ka, oa, ia, va = rows(za, pol); kb, ob, ib, vb = rows(zb, pol)
        for i in range(len(ka)):
            if first is not None and i >= first: break
            if (ka[i] != kb[i] or (oa[i + 1] - oa[i]) != (ob[i + 1] - ob[i])
                    or not np.array_equal(ia[oa[i]:oa[i + 1]], ib[ob[i]:ob[i + 1]])
                    or va[oa[i]:oa[i + 1]].tobytes() != vb[ob[i]:ob[i + 1]].tobytes()):
                first = i; break
    return first


# ---------------------------------------------------------------- C1 prep: regenerate FRESH base targets (old value)
for seed in SEEDS:
    p, want = BASE_TGT[("F", seed)]
    d = os.path.dirname(p); os.makedirs(d, exist_ok=True)
    spec = f"{FRESH}/configs/ADAPTER_SPEC_FRESH_s{seed}.json"
    cmd = ["/workspace/venv/bin/python", "-B", "ovn_adapter.py", "PATH,HOME,LC_CTYPE", spec, p, p[:-4] + ".json"]
    if not os.path.exists(p):
        pr = subprocess.run(cmd, cwd=f"{FRESH}/engine", env={"PATH": "/usr/bin:/bin", "HOME": "/root"},
                            capture_output=True, text=True)
        rec["controls"][f"C1_regen_FRESH_s{seed}"] = {"cmd": cmd, "cwd": f"{FRESH}/engine", "rc": pr.returncode,
                                                       "stdout_tail": pr.stdout[-300:], "stderr_tail": pr.stderr[-300:]}
        if pr.returncode != 0 or "Traceback" in pr.stderr: FAIL.append(f"C1 regen FRESH s{seed}: rc {pr.returncode}")
    got = sha(p) if os.path.exists(p) else None
    ok = got == want
    rec["controls"].setdefault(f"C1_regen_FRESH_s{seed}", {})
    rec["controls"][f"C1_regen_FRESH_s{seed}"].update({"sha256": got, "pinned": want, "reproduces_old_targets_bitwise": ok})
    if not ok: FAIL.append(f"C1 FRESH s{seed}: regenerated targets {str(got)[:12]} != pinned {want[:12]}")

# ---------------------------------------------------------------- first RN8-differing anchor (legs axis)
assert sha(LEGS_OLD[0]) == LEGS_OLD[1] and sha(LEGS_CLN[0]) == LEGS_CLN[1], "legs sha"
lo, lc = np.load(LEGS_OLD[0]), np.load(LEGS_CLN[0])
assert np.array_equal(lo["E_ts"], lc["E_ts"]) and np.array_equal(lo["symbols"], lc["symbols"]), "legs axes differ"
a, b = lo["RN8"], lc["RN8"]
diff = ~((a == b) | (np.isnan(a) & np.isnan(b)))
rn8_rows = np.where(diff.any(1))[0]
rn8_first_ts = int(lo["E_ts"][rn8_rows[0]])
rec["rn8"] = {"cells_differing": int(diff.sum()), "first_ts": iso(rn8_first_ts),
              "n_rows_differing": int(len(rn8_rows))}
if int(diff.sum()) != 639: FAIL.append(f"RN8 differing cells {int(diff.sum())} != 639 reported by fa_ladder")

# ---------------------------------------------------------------- load series, C0
S = {(k, s): load_series(k, s) for (k, s) in SER}
A = S[("N_old", "42")]["A"]
for v in S.values():
    assert np.array_equal(v["A"], A), "series axes differ"
rec["axis"] = {"n": int(len(A)), "first": iso(A[0]), "last": iso(A[-1])}
end = iso(A[-1])
masks = {"pre2026": NS.seg_mask(A, *NS.SEG["pre2026"]),
         "2026_to_axis_end": NS.seg_mask(A, "2026-01-01T00:00:00Z", end),
         "2026_SEG_truncated": NS.seg_mask(A, *NS.SEG["2026"]),
         "fullwin_to_axis_end": NS.seg_mask(A, NS.SEG["2023H2"][0], end)}
days = {k: NS.full_days(A, m) for k, m in masks.items()}


def dbar(x, y, key):
    db, _ = NS.dbar(x["paths"], y["paths"], masks[key], days[key])
    return db


assert sha(f"{R}/FA_LADREAD.json") == LADREAD_SHA, "FA_LADREAD.json is not the committed reading"
LR = json.load(open(f"{R}/FA_LADREAD.json"))
d_old = {}
for seed in SEEDS:
    g = 1e4 * dbar(S[("F_old", seed)], S[("N_old", seed)], "pre2026").mean()
    want = LR["seeds"][seed]["G"]["pre2026"]["frozen_dbar_bps_per_day"]
    rec["controls"][f"C0_G_old_s{seed}"] = {"recomputed": g, "filed": want, "absdiff": abs(g - want)}
    if abs(g - want) > 1e-9: FAIL.append(f"C0 G_old s{seed}: {g} vs filed {want}")
    for arm in ARMS:
        f = f"{R}/SER_LAD_{arm}_s{seed}.npz"
        wsha = LR["seeds"][seed]["arms"][arm]["series_sha256"]
        if sha(f) != wsha: FAIL.append(f"C0 arm {arm} s{seed}: series sha != filed"); continue
        z = np.load(f); Aa = z["anchors"].astype(np.int64); assert np.array_equal(Aa, A)
        x = {"paths": [{"A": Aa, "r": z["r_per_path"][k]} for k in range(z["r_per_path"].shape[0])]}
        d_old[(arm, seed)] = {k: float(1e4 * dbar(x, S[("N_old", seed)], k).mean()) for k in ("pre2026", "2026_to_axis_end")}
        fw = LR["seeds"][seed]["arms"][arm]["pre2026"]["d_bps_per_day"]
        if abs(d_old[(arm, seed)]["pre2026"] - fw) > 1e-9: FAIL.append(f"C0 d_old {arm} s{seed}")
        fw26 = LR["seeds"][seed]["arms"][arm]["2026_to_axis_end"]["d_bps_per_day"]
        if abs(d_old[(arm, seed)]["2026_to_axis_end"] - fw26) > 1e-9: FAIL.append(f"C0 d_old26 {arm} s{seed}")

# ---------------------------------------------------------------- C1 / C2 causality
for side, key_old, key_cln in (("N", "N_old", "N_cln"), ("F", "F_old", "F_cln")):
    for seed in SEEDS:
        c = {}
        pb, wb = BASE_TGT[(side, seed)]; pe, we = END_TGT[(side, seed)]
        okb, oke = os.path.exists(pb) and sha(pb) == wb, sha(pe) == we
        c["base_targets_sha_ok"], c["end_targets_sha_ok"] = okb, oke
        if not (okb and oke):
            FAIL.append(f"C1 {side} s{seed}: target sha (base {okb}, end {oke})"); rec["controls"][f"C1C2_{side}_s{seed}"] = c; continue
        zb, ze = np.load(pb), np.load(pe)
        ft = first_row_diff(zb, ze)
        c["first_target_diff"] = None if ft is None else {"index": int(ft), "ts": iso(zb["anchor"][ft])}
        if ft is None:
            FAIL.append(f"C1 {side} s{seed}: targets identical (vacuous swap)"); c["C1"] = "FAIL"
        elif rn8_first_ts < int(zb["anchor"][0]):
            c["C1"] = "VACUOUS (first RN8 difference %s precedes the engine axis %s)" % (iso(rn8_first_ts), iso(zb["anchor"][0]))
        else:
            c["C1"] = "PASS" if int(zb["anchor"][ft]) >= rn8_first_ts else "FAIL"
            if c["C1"] == "FAIL": FAIL.append(f"C1 {side} s{seed}: targets differ before the first RN8 difference")
        ro, rc_ = S[(key_old, seed)]["ch"]["r"], S[(key_cln, seed)]["ch"]["r"]
        neq = np.any(ro.view(np.uint64) != rc_.view(np.uint64), axis=0)
        fs = int(np.argmax(neq)) if neq.any() else None
        c["first_series_diff"] = None if fs is None else {"index": fs, "ts": iso(A[fs])}
        if ft is None or fs is None:
            c["C2"] = "FAIL"; FAIL.append(f"C2 {side} s{seed}: no difference")
        else:
            c["C2"] = "PASS" if fs >= ft else "FAIL"
            c["C2_power_note"] = f"series identical on the {fs} anchors before the first difference; target first diff at {ft}"
            if fs < ft: FAIL.append(f"C2 {side} s{seed}: series differ at {fs} before targets differ at {ft}")
        rec["controls"][f"C1C2_{side}_s{seed}"] = c

# ---------------------------------------------------------------- C3 known answer
for seed in SEEDS:
    x = S[("F_cln", seed)]; m = masks["pre2026"]; dlt = 1e-5
    y = {"paths": [{"A": p["A"], "r": p["r"] + np.where(m, dlt, 0.0)} for p in x["paths"]]}
    base = 1e4 * dbar(x, S[("N_cln", seed)], "pre2026").mean()
    shifted = 1e4 * dbar(y, S[("N_cln", seed)], "pre2026").mean()
    expect = 6 * dlt * 1e4       # 6 anchors per full UTC day; first order in dlt (the r*dlt cross terms are ~1e-3 of it)
    zero = dbar(S[("N_old", seed)], S[("N_old", seed)], "pre2026")
    anti = dbar(S[("F_old", seed)], S[("N_old", seed)], "pre2026") + dbar(S[("N_old", seed)], S[("F_old", seed)], "pre2026")
    c = {"shift_bps": shifted - base, "expected_approx_bps": expect,
         "within_5pct": bool(abs((shifted - base) - expect) <= 0.05 * expect), "increases": bool(shifted > base),
         "self_difference_exactly_zero": bool(np.all(zero == 0.0)), "antisymmetric": bool(np.all(anti == 0.0))}
    rec["controls"][f"C3_s{seed}"] = c
    if not (c["within_5pct"] and c["increases"] and c["self_difference_exactly_zero"] and c["antisymmetric"]):
        FAIL.append(f"C3 s{seed}: {c}")

rec["controls_failed"] = FAIL
if FAIL:
    rec["STATUS"] = "UNAVAILABLE"
    json.dump(rec, open(OUT + ".tmp", "w"), indent=1, default=float); os.replace(OUT + ".tmp", OUT)
    print("FA_LAD2READ UNAVAILABLE", FAIL, flush=True); sys.exit(3)

# ---------------------------------------------------------------- readings
def verdict(d, G):
    if G != 0 and d / G >= 0.5 and abs(d) >= 2 * SIGMA: return "CARRIES_MOST_OF_THE_GAP"
    if abs(d) <= SIGMA: return "DOES_NOT_CARRY"
    return "INDISTINGUISHABLE"


def boundary_distance(d, G):
    pts = [SIGMA, -SIGMA, 2 * SIGMA, -2 * SIGMA, 0.5 * G]
    return float(min(abs(d - p) for p in pts))


KEYS = ("pre2026", "2026_to_axis_end", "2026_SEG_truncated", "fullwin_to_axis_end")
REJ = []
for seed in SEEDS:
    s = {"quantities": {}, "channels": {}, "means": {}, "arms": {}}
    for key in KEYS:
        dG_old = dbar(S[("F_old", seed)], S[("N_old", seed)], key)
        dG_cln = dbar(S[("F_cln", seed)], S[("N_cln", seed)], key)
        de_N = dbar(S[("N_cln", seed)], S[("N_old", seed)], key)
        de_F = dbar(S[("F_cln", seed)], S[("F_old", seed)], key)
        q = {"G_old": 1e4 * dG_old.mean(), "G_cln": 1e4 * dG_cln.mean(), "dG": 1e4 * (dG_cln - dG_old).mean(),
             "e_N": 1e4 * de_N.mean(), "e_F": 1e4 * de_F.mean(), "n_days": int(len(dG_old))}
        q["identity_dG_minus_(e_F-e_N)"] = q["dG"] - (q["e_F"] - q["e_N"])
        if key in ("pre2026", "2026_to_axis_end"):
            q["boot30"] = {"G_cln": NS.boot(dG_cln, 30)["ci95_bps"], "dG": NS.boot(dG_cln - dG_old, 30)["ci95_bps"],
                           "e_N": NS.boot(de_N, 30)["ci95_bps"], "e_F": NS.boot(de_F, 30)["ci95_bps"]}
        s["quantities"][key] = q
        if abs(q["identity_dG_minus_(e_F-e_N)"]) > 1e-9: FAIL.append(f"identity {key} s{seed}")
    for key in ("pre2026", "2026_to_axis_end"):
        m = masks[key]; ch = {}
        for pair, (x, y) in {"N_cln-N_old": ("N_cln", "N_old"), "F_cln-F_old": ("F_cln", "F_old"),
                             "F_old-N_old": ("F_old", "N_old"), "F_cln-N_cln": ("F_cln", "N_cln")}.items():
            cx, cy = S[(x, seed)]["ch"], S[(y, seed)]["ch"]
            c = {k: float(1e4 * (cx[k].mean(0)[m] - cy[k].mean(0)[m]).sum()) for k in ("pnl", "car", "cst", "unk", "g")}
            c["NET_price_minus_funding_paid"] = c["pnl"] - c["car"]
            ch[pair] = c
        s["channels"][key] = ch
        s["means"][key] = {cell: {k: float(S[(cell, seed)]["ch"][k][:, m].mean()) for k in ("tau", "hold", "halt")}
                           for cell in ("N_old", "N_cln", "F_old", "F_cln")}
    q = s["quantities"]["pre2026"]; q26 = s["quantities"]["2026_to_axis_end"]
    B = abs(q["e_N"]) + max(abs(q["e_N"]), abs(q["e_F"]))
    B26 = abs(q26["e_N"]) + max(abs(q26["e_N"]), abs(q26["e_F"]))
    s["B_pre2026"], s["B_2026"] = B, B26
    for arm in ARMS:
        d = d_old[(arm, seed)]["pre2026"]; d26 = d_old[(arm, seed)]["2026_to_axis_end"]
        filed = LR["seeds"][seed]["arms"][arm]["VERDICT"]
        v_old = verdict(d, q["G_old"]); v_R1 = verdict(d, q["G_cln"])
        grid = np.concatenate([[d - B, d + B], np.linspace(d - B, d + B, 4001)])
        vs = sorted({verdict(float(x), q["G_cln"]) for x in grid})
        a = {"d_old": d, "d_old_2026": d26, "filed_verdict": filed, "verdict_recomputed_G_old": v_old,
             "R1_verdict_with_G_cln": v_R1, "R1_changes": v_R1 != filed,
             "R2_band": [d - B, d + B], "R2_verdicts_over_band": vs, "R2_changes": len(vs) > 1,
             "ratio_old": d / q["G_old"], "ratio_with_G_cln": d / q["G_cln"],
             "boundary_distance_G_old": boundary_distance(d, q["G_old"]),
             "boundary_distance_G_cln": boundary_distance(d, q["G_cln"]),
             "2026_sign_margin": (abs(d26) - B26), "2026_sign_robust_under_A1": bool(abs(d26) - B26 > 0),
             "note": "a configuration the pipeline cannot produce; this arm is a measuring instrument only"}
        if v_old != filed: FAIL.append(f"verdict recompute {arm} s{seed}")
        if a["R1_changes"]: REJ.append({"arm": arm, "seed": seed, "rule": "R1"})
        if a["R2_changes"]: REJ.append({"arm": arm, "seed": seed, "rule": "R2 (under A1)"})
        s["arms"][arm] = a
    if d_old[("KZ", seed)]["2026_to_axis_end"] - B26 <= 0:
        REJ.append({"arm": "KZ", "seed": seed, "rule": "R4 (section 6 conclusion 4, 2026 sign)"})
    rec["seeds"][seed] = s

Bmax = max(rec["seeds"][s]["B_pre2026"] for s in SEEDS)
rec["R3"] = {"max_B_pre2026": Bmax, "sigma": SIGMA, "fires": bool(Bmax >= SIGMA)}
if rec["R3"]["fires"]:
    REJ = [{"arm": a, "seed": s, "rule": "R3 (all arms)"} for a in ARMS for s in SEEDS] + REJ
rec["RE_JUDGE"] = REJ
rec["assumption_A1"] = ("R2/R4 keep a verdict only if a mixed arm's RN8 effect is no larger than max(|e_N|,|e_F|); "
                        "NOT verified")
rec["controls_failed"] = FAIL
rec["STATUS"] = "UNAVAILABLE" if FAIL else "OK"
json.dump(rec, open(OUT + ".tmp", "w"), indent=1, default=float); os.replace(OUT + ".tmp", OUT)
back = json.load(open(OUT)); assert back["STATUS"] == rec["STATUS"] and back["self_sha256"] == rec["self_sha256"]
print("FA_LAD2READ STATUS=%s receipt_sha256=%s" % (rec["STATUS"], sha(OUT)), flush=True)
for seed in SEEDS:
    for key in ("pre2026", "2026_to_axis_end"):
        q = rec["seeds"][seed]["quantities"][key]
        print("  s%-4s %-17s G_old %+8.4f  G_cln %+8.4f  dG %+8.4f %s  e_N %+8.4f  e_F %+8.4f"
              % (seed, key, q["G_old"], q["G_cln"], q["dG"], [round(x, 2) for x in q.get("boot30", {}).get("dG", [])],
                 q["e_N"], q["e_F"]), flush=True)
    print("        B_pre2026 %.4f  B_2026 %.4f" % (rec["seeds"][seed]["B_pre2026"], rec["seeds"][seed]["B_2026"]))
    for arm, a in rec["seeds"][seed]["arms"].items():
        print("        %-5s d %+8.4f  ratio %.3f->%.3f  filed %-24s R1 %-24s R2 %s  2026 d %+.4f margin %+.4f"
              % (arm, a["d_old"], a["ratio_old"], a["ratio_with_G_cln"], a["filed_verdict"], a["R1_verdict_with_G_cln"],
                 a["R2_verdicts_over_band"], a["d_old_2026"], a["2026_sign_margin"]), flush=True)
print("  R3", rec["R3"]); print("  RE_JUDGE", REJ); print("  FAIL", FAIL)
