"""judge_rebuild.py — G5 judge, adapted from rolling_king judge.py (sha 926d5c62…; same bootstrap, Sharpe, maxDD, σ_fund definitions).
Adaptations (layout/arms only): ROOT; kings {pinned (re-indexed onto the hist grid), hist (rebuilt 2020-start OOS king)}; arms F1/F2/F3;
yearly windows 2022..2026 plus 2024->26, 2025->26, 2022->26; per-window worst calendar month; three columns reported:
  net_ex (executor caliber, bps/anchor at device gross), net (file caliber), pg = net/gross_total (per-gross, the 08-21 comparison unit).
Δ = hist − pinned, paired by anchor ts (pairs aligned on common ts), UTC-day block bootstrap NB=2000 seed 20260905, CI95, P(Δ>0).
σ_fund terciles as in judge.py L95-112 but from the rebuilt meta/panel. No admission decision (prereg: 本轴只诊断)."""
import os, sys, json, time, hashlib
import numpy as np
ROOT = os.environ.get("JR_ROOT", "/workspace/review_scratch/jpline_rebuild")   # JR_ROOT only for the dry-test harness
ARM = "d30_n2_c42"; NB = 2000; SEED = 20260905
CALS = {"log": "dev", "prod": "dev_alt"}
CAL_DESC = {"log": "raw Σ-simple y4 over [E,E+47] (rebuilt meta), CAL=log = no transform", "prod": "Π(1+r5)-1 over [E+1,E+48] (meta_hist_newprod swap), CAL=log"}
ARMS = {"F1": ["s42"], "F2": ["s42", "s2027"], "F3": ["s42", "s2027"]}
ARM_DESC = {"F1": "08-21 three-leg LEGS=111 PHI=0 dynamic msharpe LOOK=900", "F2": "in-service fixed seats LEGS=101 PHI=0.45 W3FIX=0.21,0,0.79 MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero", "F3": "F2 without W3FIX (dynamic seats)"}
KING_NPY = {"pinned": f"{ROOT}/data/slow_pred_pinned_on_hist.npy", "hist": f"{ROOT}/data/slow_pred_hist_oos_rebuilt.npy"}
EXPECT = {"F1": {"LEGS": "111", "PHI": 0.0, "W3FIX": None, "MEMBERS_TOPN": 0, "TRADE_TOPN": 0, "FTRIM": "off"},
          "F2": {"LEGS": "101", "PHI": 0.45, "W3FIX": "0.21,0,0.79", "MEMBERS_TOPN": 829, "TRADE_TOPN": 400, "FTRIM": "zero"},
          "F3": {"LEGS": "101", "PHI": 0.45, "W3FIX": None, "MEMBERS_TOPN": 829, "TRADE_TOPN": 400, "FTRIM": "zero"}}
COLS = ["net_ex", "net", "pg"]
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 24), b""): h.update(ch)
    return h.hexdigest()
def iso(t): return time.strftime("%Y-%m-%d %H:%M", time.gmtime(int(t)))
def tag(arm, king, cal, seed): return f"F1_{king}_{cal}" if arm == "F1" else f"{arm}_{king}_{cal}_{seed}"
def path(arm, king, cal, seed): return f"{ROOT}/{CALS[cal]}/probe_artifacts/w10_ablation_series_{tag(arm, king, cal, seed)}.npz"
KINGS = [k for k in ("pinned", "hist") if os.path.exists(path("F1", k, "log", "s42"))]
D = {}; CFG = {}; SHA = {}
for arm, seeds in ARMS.items():
    for seed in seeds:
        for cal in CALS:
            for king in KINGS:
                p = path(arm, king, cal, seed)
                if not os.path.exists(p): print(f"MISSING {p}"); continue
                z = np.load(p, allow_pickle=True); cols = [str(c) for c in z["cols"]]; cfg = json.loads(str(z["config_json"])); R = z[f"{ARM}_rec"]
                assert cfg["LOOK"] == 900 and cfg["WRULE"] == "msharpe" and cfg["CAL"] == "log" and cfg["REF_SKIP"] == 0, (p, cfg)
                assert cfg["SLOW_NPY"] == KING_NPY[king], (p, cfg["SLOW_NPY"])
                if arm != "F1": assert cfg["FSEED"] == seed[1:], (p, cfg["FSEED"])
                for kk, vv in EXPECT[arm].items(): assert cfg[kk] == vv, (p, kk, cfg[kk], vv)
                d = {c: R[:, i] for i, c in enumerate(cols)}; d["pg"] = d["net"] / d["gross_total"]; d["ts"] = d["ts"].astype(np.int64)
                D[(arm, seed, cal, king)] = d; CFG[(arm, seed, cal, king)] = cfg; SHA[tag(arm, king, cal, seed)] = sha(p)
print(f"LOADED {len(D)} artifacts; kings {KINGS}; anchor counts: " + ", ".join(f"{tag(*k[0:1], k[3], k[2], k[1])}={len(v['ts'])}" for k, v in D.items()), flush=True)
def sharpe(x): return float(x.mean() / x.std(ddof=1) * np.sqrt(2190)) if len(x) > 2 and x.std(ddof=1) > 0 else float("nan")
def maxdd(x): c = np.cumsum(x); return float(np.max(np.maximum.accumulate(c) - c)) if len(x) else float("nan")
def worst_month(ts, x):
    mo = np.array([time.strftime("%Y-%m", time.gmtime(int(t))) for t in ts]); um, inv = np.unique(mo, return_inverse=True); s = np.bincount(inv, weights=x)
    j = int(np.argmin(s)); return float(s[j]), str(um[j])
def windows(ts):
    yrs = np.array([time.gmtime(int(t)).tm_year for t in ts])
    return {"2022": yrs == 2022, "2023": yrs == 2023, "2024": yrs == 2024, "2025": yrs == 2025, "2026": yrs == 2026, "2024->26": yrs >= 2024, "2025->26": yrs >= 2025, "2022->26": yrs >= 2022}
WNAMES = ["2022", "2023", "2024", "2025", "2026", "2024->26", "2025->26", "2022->26"]
rng = np.random.default_rng(SEED)
def boot(delta, days, m):
    x = delta[m]; dd = days[m]; ud, inv = np.unique(dd, return_inverse=True); nd = len(ud)
    sums = np.bincount(inv, weights=x, minlength=nd); cnts = np.bincount(inv, minlength=nd)
    idx = rng.integers(0, nd, size=(NB, nd)); means = sums[idx].sum(1) / cnts[idx].sum(1)
    return float(x.mean()), float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5)), float((means > 0).mean()), int(nd)
OUT = {"arm": ARM, "kings": KINGS, "artifact_sha256": SHA, "columns": {"net_ex": "executor caliber net, bps/anchor at device gross", "net": "file caliber net, bps/anchor at device gross", "pg": "net/gross_total = bps/anchor per unit gross (08-21 comparison unit; x2190/100 = %/gross/yr)"},
       "levels": {}, "deltas": {}, "sigma_fund": {}}
MD = []   # markdown tables
# ───────── levels ─────────
for col in COLS:
    for cal in CALS:
        MD.append(f"\n### Levels — column `{col}` — caliber {cal} [{CAL_DESC[cal]}] — arm {ARM}\n")
        MD.append("| arm | seed | king | n | " + " | ".join(WNAMES) + " | gross 24→26 | w_king 24→26 | turn 24→26 |")
        MD.append("|---|---|---|---|" + "---|" * len(WNAMES) + "---|---|---|")
        print(f"\n===== LEVELS column={col} caliber={cal}: per window mean S=Sharpe DD=maxDD(bps) WM=worst month(bps)", flush=True)
        for arm, seeds in ARMS.items():
            for seed in seeds:
                for king in KINGS:
                    k = (arm, seed, cal, king)
                    if k not in D: continue
                    d = D[k]; W = windows(d["ts"]); row = {}
                    for w, m in W.items():
                        x = d[col][m]; wm, wmo = worst_month(d["ts"][m], x) if m.sum() else (float("nan"), "")
                        row[w] = {"n": int(m.sum()), "mean": round(float(x.mean()), 4) if m.sum() else None, "sharpe": round(sharpe(x), 3), "maxDD": round(maxdd(x), 1), "worst_month": round(wm, 1), "worst_month_id": wmo,
                                  "gross": round(float(d["gross_total"][m].mean()), 4) if m.sum() else None, "w_king": round(float(d["w3_king"][m].mean()), 4) if m.sum() else None, "w_fund": round(float(d["w3_fund"][m].mean()), 4) if m.sum() else None,
                                  "turn": round(float(d["turnover"][m].mean()), 5) if m.sum() else None, "carry": round(float(d["carry_ex"][m].mean()), 4) if m.sum() else None, "cost": round(float(d["cost_ex"][m].mean()), 4) if m.sum() else None}
                    OUT["levels"][f"{col}/{cal}/{arm}/{seed}/{king}"] = row; r24 = row["2024->26"]
                    cell = lambda w: (f"{row[w]['mean']:+.3f} S{row[w]['sharpe']:+.2f} DD{row[w]['maxDD']:.0f} WM{row[w]['worst_month']:.0f}" if row[w]["mean"] is not None else "—")
                    print(f"{arm:3s} {seed:6s} {king:7s} n={len(d['ts'])} | " + " | ".join(cell(w) for w in WNAMES) + f" | gross {r24['gross']} w_king {r24['w_king']} turn {r24['turn']}", flush=True)
                    MD.append(f"| {arm} | {seed} | {king} | {len(d['ts'])} | " + " | ".join(cell(w) for w in WNAMES) + f" | {r24['gross']} | {r24['w_king']} | {r24['turn']} |")
# ───────── deltas hist − pinned ─────────
if "hist" in KINGS and "pinned" in KINGS:
    for col in ("net_ex", "pg"):
        for cal in CALS:
            MD.append(f"\n### Δ(hist − pinned) — column `{col}` — caliber {cal} — paired by anchor, UTC-day block bootstrap NB={NB} seed={SEED}; cells: Δ [CI95] P(Δ>0)\n")
            MD.append("| arm | seed | n common | " + " | ".join(WNAMES) + " | ΔSharpe 24→26 | Δturn% 24→26 | maxDD pinned/hist 24→26 |")
            MD.append("|---|---|---|" + "---|" * len(WNAMES) + "---|---|---|")
            print(f"\n===== DELTAS column={col} caliber={cal}: Δ = hist − pinned", flush=True)
            for arm, seeds in ARMS.items():
                for seed in seeds:
                    kx = (arm, seed, cal, "hist"); ky = (arm, seed, cal, "pinned")
                    if kx not in D or ky not in D: continue
                    tx, ty = D[kx]["ts"], D[ky]["ts"]; common = np.intersect1d(tx, ty); ix = np.searchsorted(tx, common); iy = np.searchsorted(ty, common)
                    delta = D[kx][col][ix] - D[ky][col][iy]; days = np.array([time.strftime("%Y-%m-%d", time.gmtime(int(t))) for t in common]); W = windows(common); res = {}
                    for w in WNAMES:
                        if W[w].sum() == 0: res[w] = None; continue
                        mu, lo, hi, p, nd = boot(delta, days, W[w]); res[w] = {"mean": round(mu, 4), "lo": round(lo, 4), "hi": round(hi, 4), "P>0": round(p, 4), "n_days": nd, "n": int(W[w].sum())}
                    m24 = W["2024->26"]; xs = D[kx][col][ix]; ys = D[ky][col][iy]
                    dsh = {w: round(sharpe(xs[W[w]]) - sharpe(ys[W[w]]), 3) for w in ("2024->26", "2025->26", "2022->26")}
                    tx_ = float(D[kx]["turnover"][ix][m24].mean()); ty_ = float(D[ky]["turnover"][iy][m24].mean()); dturn = (tx_ / ty_ - 1) * 100
                    ddx = maxdd(xs[m24]); ddy = maxdd(ys[m24])
                    OUT["deltas"][f"{col}/{cal}/{arm}/{seed}/hist-pinned"] = {"n_common": int(len(common)), "n_hist_only": int(len(tx) - len(common)), "n_pinned_only": int(len(ty) - len(common)), "windows": res, "dSharpe": dsh, "turn_pinned": round(ty_, 5), "turn_hist": round(tx_, 5), "dturn_pct": round(dturn, 2), "maxDD_pinned": round(ddy, 1), "maxDD_hist": round(ddx, 1)}
                    f = lambda w: (f"{res[w]['mean']:+.3f} [{res[w]['lo']:+.3f},{res[w]['hi']:+.3f}] {res[w]['P>0']:.3f}" if res[w] else "—")
                    print(f"{arm:3s} {seed:6s} n={len(common)} | " + " | ".join(f(w) for w in WNAMES) + f" | ΔS {dsh['2024->26']:+.2f} Δturn {dturn:+.1f}% DD {ddy:.0f}/{ddx:.0f}", flush=True)
                    MD.append(f"| {arm} | {seed} | {len(common)} | " + " | ".join(f(w) for w in WNAMES) + f" | {dsh['2024->26']:+.2f} | {dturn:+.1f}% | {ddy:.0f}/{ddx:.0f} |")
# ───────── σ_fund terciles (judge.py L95-112 definition, rebuilt meta/panel) ─────────
MT = np.load(f"{ROOT}/data/wide_fea_hist_meta_rebuilt.npz", allow_pickle=True); E_ts = MT["E_ts"].astype(np.int64); members = MT["members"]
PW = np.load(f"{ROOT}/data/wide_panel_4h_hist_v2_rebuilt.npz", allow_pickle=True); pw_row = {int(t): j for j, t in enumerate(PW["ts"].astype(np.int64))}; FN = PW["f_fund_now"]; IV = PW["f_fund_iv"]
sig_map = {}
for i in range(len(E_ts)):
    j = pw_row.get(int(E_ts[i]))
    if j is None: continue
    m = members[i]; f = FN[j, m]; iv = IV[j, m]; ivf = np.where(np.isfinite(iv) & (iv > 0), iv, 8.0); ok = np.isfinite(f)
    sig_map[int(E_ts[i])] = float(np.std(f[ok] * 8.0 / ivf[ok]) * 1e4) if ok.sum() >= 50 else np.nan
OUT["sigma_fund"]["definition"] = "std over meta members (finite f_fund_now) of f_fund_now*8/ivf, *1e4 bps/8h; trailing 30-anchor mean (>=15 valid); terciles over the 2024->26 anchors of each pairing"
for col in ("net_ex", "pg"):
    for cal in CALS:
        MD.append(f"\n### σ_fund terciles (2024→26) — column `{col}` — caliber {cal}: per tercile pinned mean → hist mean, Δ [CI95] P(Δ>0)\n")
        MD.append("| arm | seed | tercile | n | σ_fund mean (bps/8h) | pinned | hist | Δ [CI95] P |")
        MD.append("|---|---|---|---|---|---|---|---|")
        for arm, seeds in ARMS.items():
            for seed in seeds:
                kx = (arm, seed, cal, "hist"); ky = (arm, seed, cal, "pinned")
                if ky not in D: continue
                ty = D[ky]["ts"]; ts0 = ty if kx not in D else np.intersect1d(D[kx]["ts"], ty)
                iy = np.searchsorted(ty, ts0); sig = np.array([sig_map.get(int(t), np.nan) for t in ts0]); roll = np.full(len(ts0), np.nan)
                for i in range(len(ts0)):
                    w = sig[max(0, i - 29):i + 1]; v = w[np.isfinite(w)]
                    if len(v) >= 15: roll[i] = v.mean()
                W = windows(ts0); m24 = W["2024->26"] & np.isfinite(roll); q1, q2 = np.nanpercentile(roll[m24], [100 / 3, 200 / 3])
                ter = np.full(len(ts0), -1); ter[m24 & (roll <= q1)] = 0; ter[m24 & (roll > q1) & (roll <= q2)] = 1; ter[m24 & (roll > q2)] = 2
                days = np.array([time.strftime("%Y-%m-%d", time.gmtime(int(t))) for t in ts0]); rec = {"cuts_bps": [round(float(q1), 3), round(float(q2), 3)]}
                for t, nm in enumerate(("low", "mid", "high")):
                    mt = ter == t; py = float(D[ky][col][iy][mt].mean()); r = {"n": int(mt.sum()), "sigma_mean": round(float(roll[mt].mean()), 3), "pinned_mean": round(py, 4)}
                    if kx in D:
                        ix = np.searchsorted(D[kx]["ts"], ts0); delta = D[kx][col][ix] - D[ky][col][iy]; mu, lo, hi, p, nd = boot(delta, days, mt)
                        r.update({"hist_mean": round(float(D[kx][col][ix][mt].mean()), 4), "delta": round(mu, 4), "lo": round(lo, 4), "hi": round(hi, 4), "P>0": round(p, 4)})
                    rec[nm] = r
                    MD.append(f"| {arm} | {seed} | {nm} | {r['n']} | {r['sigma_mean']} | {r['pinned_mean']:+.3f} | " + (f"{r['hist_mean']:+.3f} | {r['delta']:+.3f} [{r['lo']:+.3f},{r['hi']:+.3f}] {r['P>0']:.2f} |" if "hist_mean" in r else "— | — |"))
                OUT["sigma_fund"][f"{col}/{cal}/{arm}/{seed}"] = rec
                print(f"σ_fund {col} {cal} {arm} {seed}: cuts {rec['cuts_bps']} " + " | ".join(f"{nm}: n {rec[nm]['n']} pin {rec[nm]['pinned_mean']:+.3f}" + (f" hist {rec[nm]['hist_mean']:+.3f} Δ {rec[nm]['delta']:+.3f} [{rec[nm]['lo']:+.3f},{rec[nm]['hi']:+.3f}]" if "hist_mean" in rec[nm] else "") for nm in ("low", "mid", "high")), flush=True)
OUT["self_sha256"] = sha(os.path.abspath(__file__))
json.dump(OUT, open(f"{ROOT}/results/judge_rebuild.json", "w"), indent=1)
open(f"{ROOT}/results/REPORT_tables.md", "w").write("\n".join(MD) + "\n")
print(f"\nwrote results/judge_rebuild.json and results/REPORT_tables.md", flush=True)
