#!/usr/bin/env python3
"""judge_warm_replication.py — PREREG_dl_warmstart_replication_2026-09-06 §2 的判官, 读法逐字取自该预注册(写于任何复验数字之前):
  复验成立 ⇔ ARM_s2027 − R0_s2027 CI95 下界 > 0 且 ARM_s2027 − yearly_s2027 Δ ≥ −0.05(CI ∋ 0 或下界 > 0)
  复验失败 ⇔ ARM_s2027 − yearly_s2027 CI95 上界 < 0; 其余 UNDECIDED
装置/口径与 judge_replication.py(§5 早停复验)完全一致: d30_n2_c42_rec, g = net_ex/gross_total, 逐锚配对,
UTC 日块 bootstrap 2000 种子 20260905, 冻结主窗 2025-03→2026-08-10 为主判, 全窗并列。"""
import os, json, time, calendar, hashlib
import numpy as np
B = "/workspace/review_scratch/allweather_trackB"; G = "/workspace/review_scratch/dl_monthly_gate"; PA = f"{B}/replay/dev_alt/probe_artifacts"
NB, SEED = 2000, 20260905
COLS = ["ts","net","pnl","carry","cost","gross_total","gross_member","gross_sel","nsel","nmember","fires","leg_king","leg_rev24","leg_fund","w3_king","w3_rev24","w3_fund","turnover","net_ex","pnl_ex","carry_ex","cost_ex","netlong"]
C = {k: i for i, k in enumerate(COLS)}
CUT = calendar.timegm((2026, 8, 10, 20, 0, 0)); T25 = calendar.timegm((2025, 1, 1, 0, 0, 0)); T2503 = calendar.timegm((2025, 3, 1, 0, 0, 0))
WIN = {"FROZEN 2025-03->cut": (T2503, CUT + 1), "FULL 2025-01->cut": (T25, CUT + 1)}
ARMS = {"yearly_s2027": f"{G}/replay/dev_alt/probe_artifacts/w10_ablation_series_BASE_s2027.npz",
        "R0_s2027": f"{PA}/w10_ablation_series_G_mE1s2027_R0_spl27.npz",
        "W1_s2027": f"{PA}/w10_ablation_series_G_mE1w1s27_R0_spl27.npz",
        "W2_s2027": f"{PA}/w10_ablation_series_G_mE1w2s27_R0_spl27.npz",
        "FLOOR5_s2027": f"{PA}/w10_ablation_series_G_mE1cF5s27_R0_spl27.npz"}
def load(p):
    z = np.load(p, allow_pickle=True); assert [str(c) for c in z["cols"]] == COLS, p
    R = np.asarray(z["d30_n2_c42_rec"], float)
    return R[:, C["ts"]].astype(np.int64), R[:, C["net_ex"]] / R[:, C["gross_total"]], R[:, C["turnover"]] / R[:, C["gross_total"]], hashlib.sha256(open(p, "rb").read()).hexdigest()[:16]
def boot(d, ts):
    days = ts // 86400; ud, inv = np.unique(days, return_inverse=True); nd = len(ud)
    s1 = np.bincount(inv, d); c = np.bincount(inv).astype(float)
    rng = np.random.default_rng(SEED); ii = rng.integers(0, nd, size=(NB, nd)); m = s1[ii].sum(1) / c[ii].sum(1)
    return float(d.mean()), float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5)), float((m > 0).mean())
D = {}
for k, p in ARMS.items():
    if os.path.exists(p): D[k] = load(p)
    else: print("MISSING", k, p)
ts0 = D["R0_s2027"][0]
OUT = {"prereg": "PREREG_dl_warmstart_replication_2026-09-06 §2 (读法写于数字之前)", "arms": {k: {"artifact": ARMS[k], "sha16": v[3]} for k, v in D.items()},
       "bootstrap": {"blocks": "UTC day", "n": NB, "seed": SEED}, "levels": {}, "deltas": {}, "reading": {}}
for k, (ts, g, t, _) in D.items():
    assert np.array_equal(ts, ts0), k
    OUT["levels"][k] = {w: {"g": float(g[(ts >= lo) & (ts < hi)].mean()), "turn": float(t[(ts >= lo) & (ts < hi)].mean())} for w, (lo, hi) in WIN.items()}
PAIRS = [("W1_s2027", "R0_s2027"), ("W1_s2027", "yearly_s2027"), ("W2_s2027", "R0_s2027"), ("W2_s2027", "yearly_s2027"),
         ("W2_s2027", "FLOOR5_s2027"), ("W1_s2027", "W2_s2027")]
for a, b in PAIRS:
    if a not in D or b not in D: continue
    OUT["deltas"][f"{a} − {b}"] = {}
    for w, (lo, hi) in WIN.items():
        m = (ts0 >= lo) & (ts0 < hi)
        mu, l, h, p = boot((D[a][1] - D[b][1])[m], ts0[m])
        OUT["deltas"][f"{a} − {b}"][w] = {"delta": mu, "ci": [l, h], "p_gt0": p}
for w in WIN:
    r = {}
    for arm in ("W1_s2027", "W2_s2027"):
        if f"{arm} − R0_s2027" not in OUT["deltas"]: continue
        r0 = OUT["deltas"][f"{arm} − R0_s2027"][w]; y = OUT["deltas"][f"{arm} − yearly_s2027"][w]
        ok_r0 = r0["ci"][0] > 0
        ok_y = (y["delta"] >= -0.05) and (y["ci"][0] <= 0 <= y["ci"][1] or y["ci"][0] > 0)
        fail_y = y["ci"][1] < 0
        v = "复验成立" if (ok_r0 and ok_y) else ("复验失败" if fail_y else "UNDECIDED")
        r[arm] = {"vs_R0_s2027": [r0["delta"], *r0["ci"]], "vs_yearly_s2027": [y["delta"], *y["ci"]],
                  "R0_CI_lower_gt0": ok_r0, "yearly_ok": ok_y, "yearly_CI_upper_lt0": fail_y, "verdict": v}
    OUT["reading"][w] = r
json.dump(OUT, open(f"{B}/warmstart/results/judge_warm_replication.json", "w"), indent=1, default=float)
for w, r in OUT["reading"].items():
    for arm, v in r.items():
        print(f"===== §2 WARM REPLICATION [{w}] {arm}: −R0_s2027 {v['vs_R0_s2027'][0]:+.4f} [{v['vs_R0_s2027'][1]:+.4f},{v['vs_R0_s2027'][2]:+.4f}] | −yearly_s2027 {v['vs_yearly_s2027'][0]:+.4f} [{v['vs_yearly_s2027'][1]:+.4f},{v['vs_yearly_s2027'][2]:+.4f}] ⇒ {v['verdict']}")
print("\n水平(冻结主窗 g bps/锚 per gross | turn):")
for k in ("R0_s2027", "yearly_s2027", "FLOOR5_s2027", "W1_s2027", "W2_s2027"):
    if k in OUT["levels"]: print(f"  {k:>14}: {OUT['levels'][k]['FROZEN 2025-03->cut']['g']:+.4f} | {OUT['levels'][k]['FROZEN 2025-03->cut']['turn']:.5f}")
for k in ("W2_s2027 − FLOOR5_s2027", "W1_s2027 − W2_s2027"):
    if k in OUT["deltas"]:
        d = OUT["deltas"][k]["FROZEN 2025-03->cut"]; print(f"  只报 {k}: {d['delta']:+.4f} [{d['ci'][0]:+.4f}, {d['ci'][1]:+.4f}]")
print("\nWARM_REPLICATION_JUDGE_DONE")
