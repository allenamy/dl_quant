"""judge_trackB.py — Track B frozen judge (PREREG_allweather_programme_2026-09-05 §3 "Track B", sha 8a02895c; written before any arm number was seen).
Artifacts: replay/dev_alt/probe_artifacts/w10_ablation_series_<TAG>.npz (health-check main-arm device, arm d30_n2_c42, prod caliber, U-PIT m1 FTRIM msharpe-900
PHI 0.45 live fee tiers). g = net_ex / gross_total (bps per anchor per unit gross). Windows: 2024 | 2025 | 2026≤cut (2026-08-10 20Z) | 2024→26≤cut (primary) |
2025→26≤cut | 2023 (info) | pre-2023 (exact 0 expected between same-seed arms: no F10 preds before the first fold).
Paired Δ by anchor vs the SAME-SEED ext baseline BASE_EXT_s<seed> (= 09-01 gate run f8_ext/preds truncated to the 0822 grid; same fold form, same data, same
trainer with knobs off) — primary; vs the device-default 0822 file BASE_s<seed> — secondary. UTC-day blocks, 2000, seed 20260905.
Frozen gate per arm: pass ⇔ (i) 2024→26 Δ CI95 lower > 0 OR (worst-year Δ (min over 2024/2025/2026 point estimates) ≥ +0.20 AND 2026 Δ ≥ −0.20), for BOTH seeds;
(ii) turnover/gross increase ≤ +10% (2024→26), both seeds; (iii) both seeds' 2024→26 Δ same sign; (iv) leak gate (results/leakcheck_*.json: ① future-side no peak
AND ③ out-of-fold leak 0) for both seeds. Structural cap stated in the RESULT: the DL leg rides φ=0.45 inside the model seat (~0.30) ⇒ book-level effects ≤ ~0.3× leg-level.
usage: judge_trackB.py  → results/judge_trackB.json + results/trackB_tables.md + stdout"""
import os, sys, json, time, calendar, hashlib, glob
import numpy as np
B = "/workspace/review_scratch/allweather_trackB"; PA = f"{B}/replay/dev_alt/probe_artifacts"; NB = 2000; SEED = 20260905; ARM = "d30_n2_c42"
CUT = calendar.timegm((2026, 8, 10, 20, 0, 0)); T23 = calendar.timegm((2023, 1, 1, 0, 0, 0)); T24 = calendar.timegm((2024, 1, 1, 0, 0, 0)); T25 = calendar.timegm((2025, 1, 1, 0, 0, 0)); T26 = calendar.timegm((2026, 1, 1, 0, 0, 0))
COLS = ["ts", "net", "pnl", "carry", "cost", "gross_total", "gross_member", "gross_sel", "nsel", "nmember", "fires", "leg_king", "leg_rev24", "leg_fund", "w3_king", "w3_rev24", "w3_fund", "turnover", "net_ex", "pnl_ex", "carry_ex", "cost_ex", "netlong"]
EXPECT = {"LEGS": "101", "CAL": "log", "LOOK": 900, "WRULE": "msharpe", "MEMBERS_TOPN": 829, "TRADE_TOPN": 0, "FTRIM": "zero", "UMASK_SCOPE": "m1", "W3FIX": None, "SLOW_NPY": "/workspace/shadow_bundle_v3/slow_pred_pinned.npy"}
def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()
def iso(t): return time.strftime("%Y-%m-%d %H:%M", time.gmtime(int(t)))
ARMS = {"BASE_s42": ("(default f10_V2MAIN_s{FSEED})", "42"), "BASE_s2027": ("(default f10_V2MAIN_s{FSEED})", "2027"), "BASE_EXT_s42": ("f10_trackB_EXT_s42.npy", "42"), "BASE_EXT_s2027": ("f10_trackB_EXT_s2027.npy", "2027"), "IDENT_s42": ("f10_trackB_IDENT_s42.npy", "42")}
for k in ("B1", "B2", "B3"):
    for s in ("42", "2027"): ARMS[f"{k}_s{s}"] = (f"f10_trackB_{k}_s{s}.npy", s)
D = {}; META = {}
for key, (fpred, fseed) in ARMS.items():
    p = f"{PA}/w10_ablation_series_{key}.npz"
    if not os.path.exists(p): print(f"MISSING {key}: {p}"); continue
    z = np.load(p, allow_pickle=True); cfg = json.loads(str(z["config_json"])); assert [str(c) for c in z["cols"]] == COLS
    for k, v in EXPECT.items(): assert cfg.get(k) == v, (key, k, cfg.get(k), v)
    assert cfg["FPRED"] == fpred and cfg["FSEED"] == fseed and abs(cfg["PHI"] - 0.45) < 1e-12 and cfg["COSTB_JSON"] and cfg["UMASK_NPZ"] and cfg.get("PHIDYN", 0) == 0, (key, cfg["FPRED"], cfg["FSEED"], cfg["PHI"])
    Rr = z[f"{ARM}_rec"]; D[key] = {c: Rr[:, i] for i, c in enumerate(COLS)}; META[key] = {"artifact": p, "sha256": sha(p)[:16], "FPRED": fpred, "FSEED": fseed, "n": int(len(Rr)), "device": cfg.get("HEALTH", {}).get("device_sha256", "")[:16]}
keys = list(D); ts0 = D[keys[0]]["ts"].astype(np.int64)
for k in keys: assert np.array_equal(D[k]["ts"].astype(np.int64), ts0), ("ts mismatch", k)
days = ts0 // 86400; months = np.array([time.gmtime(int(t)).tm_year * 100 + time.gmtime(int(t)).tm_mon for t in ts0])
WIN = {"pre-2023": ts0 < T23, "2023": (ts0 >= T23) & (ts0 < T24), "2024": (ts0 >= T24) & (ts0 < T25), "2025": (ts0 >= T25) & (ts0 < T26), "2026<=cut": (ts0 >= T26) & (ts0 <= CUT), "2024->26<=cut": (ts0 >= T24) & (ts0 <= CUT), "2025->26<=cut": (ts0 >= T25) & (ts0 <= CUT), "2026-postcut": ts0 > CUT}
PW = "2024->26<=cut"; YW = ("2024", "2025", "2026<=cut")
G_ = {k: D[k]["net_ex"] / D[k]["gross_total"] for k in keys}; TPG = {k: D[k]["turnover"] / D[k]["gross_total"] for k in keys}
rng = np.random.default_rng(SEED)
def boot(x, m):
    v = x[m]; d = days[m]; ud, inv = np.unique(d, return_inverse=True); nd = len(ud)
    s = np.bincount(inv, weights=v, minlength=nd); c = np.bincount(inv, minlength=nd); idx = rng.integers(0, nd, size=(NB, nd)); means = s[idx].sum(1) / c[idx].sum(1)
    return {"n": int(m.sum()), "n_days": int(nd), "mean": float(v.mean()), "lo": float(np.percentile(means, 2.5)), "hi": float(np.percentile(means, 97.5)), "P>0": float((means > 0).mean()), "pct_gross_yr": float(v.mean() * 2190 / 100), "nav_pct_yr_2x": float(v.mean() * 43.8)}
def sharpe(x): return float(x.mean() / x.std(ddof=1) * np.sqrt(2190)) if len(x) > 2 and x.std(ddof=1) > 0 else float("nan")
def maxdd(x): c = np.cumsum(x); return float(np.max(np.maximum.accumulate(c) - c)) if len(x) else float("nan")
LEAK = {}
for p in sorted(glob.glob(f"{B}/results/leakcheck_*.json")):
    for k, v in json.load(open(p))["files"].items(): LEAK[k] = {"pass": v["leak_gate_pass_c1_and_c3"], "c1": v["c1_future_no_peak_full"], "c3": v["c3_pass"], "max_abs_future": v["max_abs_future_full"], "k0": v["spectrum_own_full"]["0"] if "0" in v["spectrum_own_full"] else v["spectrum_own_full"][0], "file": os.path.basename(p)}
OUT = {"arm": ARM, "n_anchors": int(len(ts0)), "first": iso(ts0[0]), "last": iso(ts0[-1]), "cut": iso(CUT), "windows": {w: int(m.sum()) for w, m in WIN.items()}, "arms": META, "units": "g = net_ex/gross_total bps per anchor per unit gross; %/gross/yr = mean*2190/100; NAV %/yr @2x = mean*43.8; 2xDD %NAV = maxDD_bps*2/100",
       "bootstrap": {"blocks": "UTC day", "n": NB, "seed": SEED}, "levels": {}, "deltas": {}, "judge": {}, "leak": LEAK}
T = []
def p(s=""): T.append(s); print(s)
p(f"LOADED {len(D)} arms n={len(ts0)} {iso(ts0[0])}→{iso(ts0[-1])}; windows " + ", ".join(f"{w}={int(m.sum())}" for w, m in WIN.items())); print("ARMS " + json.dumps(META))
p(f"\n## L · Levels per gross (bps/anchor; VERIFIED judge_trackB.json levels); window {PW} unless stated; NAV %/yr @2× = mean × 43.8; 2×DD %NAV = maxDD × 2/100")
p("| arm | FPRED | seed | 2024 | 2025 | 2026≤cut | **2024→26** [CI95] | %/gross/yr | NAV %/yr @2× | Sharpe | maxDD bps (2×DD %NAV) | turn/gross | cost/gross | carry/gross | gross | w_king | 2023 (info) |")
p("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
for k in keys:
    row = {}
    for w, m in WIN.items():
        if m.sum() < 12: continue
        x = G_[k][m]; d = D[k]
        row[w] = {"n": int(m.sum()), "mean": float(x.mean()), "sharpe": sharpe(x), "maxDD_bps": maxdd(x), "pct_gross_yr": float(x.mean() * 2190 / 100), "nav_pct_yr_2x": float(x.mean() * 43.8), "gross": float(d["gross_total"][m].mean()), "w_king": float(d["w3_king"][m].mean()),
                  "turn_per_gross": float(TPG[k][m].mean()), "cost_per_gross": float((d["cost_ex"][m] / d["gross_total"][m]).mean()), "carry_per_gross": float((d["carry_ex"][m] / d["gross_total"][m]).mean())}
        if w in (PW, "2025->26<=cut") + YW: row[w]["boot"] = boot(G_[k], m)
    OUT["levels"][k] = row; q = row[PW]
    p(f"| {k} | {META[k]['FPRED']} | {META[k]['FSEED']} | " + " | ".join(f"{row[w]['mean']:+.3f} (S{row[w]['sharpe']:+.2f})" for w in YW) + f" | **{q['mean']:+.3f}** [{q['boot']['lo']:+.3f}, {q['boot']['hi']:+.3f}] | {q['pct_gross_yr']:+.1f}% | {q['nav_pct_yr_2x']:+.1f}% | {q['sharpe']:+.2f} | {q['maxDD_bps']:.0f} ({q['maxDD_bps']*2/100:.1f}%) | {q['turn_per_gross']:.5f} | {q['cost_per_gross']:.3f} | {q['carry_per_gross']:+.3f} | {q['gross']:.3f} | {q['w_king']:.3f} | {row['2023']['mean']:+.3f} |")
PAIRS = []
for k in keys:
    if k.startswith("B") and not k.startswith("BASE"):
        s = META[k]["FSEED"]; PAIRS += [(k, f"BASE_EXT_s{s}", f"{k} − BASE_EXT_s{s} [primary]"), (k, f"BASE_s{s}", f"{k} − BASE_s{s} [secondary]")]
PAIRS += [("IDENT_s42", "BASE_EXT_s42", "IDENT_s42 − BASE_EXT_s42 [identity, exact 0 expected]"), ("BASE_EXT_s42", "BASE_s42", "BASE_EXT_s42 − BASE_s42 [ext data vs 0822 data, same trainer]"), ("BASE_EXT_s2027", "BASE_s2027", "BASE_EXT_s2027 − BASE_s2027 [ext vs 0822]")]
DW = ("pre-2023", "2023", "2024", "2025", "2026<=cut", PW, "2025->26<=cut", "2026-postcut")
p(f"\n## D · Paired Δ per gross (Δg = g_x − g_ref by anchor; UTC-day-block bootstrap {NB}, seed {SEED}; cells Δ [CI95] P(Δ>0); VERIFIED judge_trackB.json deltas)")
p("| pair | pre-2023 | 2023 | 2024 | 2025 | 2026≤cut | **2024→26≤cut** | 2025→26 | worst-year Δ | ΔSharpe 24→26 | Δturn% | maxDD ref→x | months + | best month (share) | Δ w/o best month |")
p("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
for kx, ky, name in PAIRS:
    if kx not in D or ky not in D: print(f"skip {name}"); continue
    dg = G_[kx] - G_[ky]; res = {}
    for w in DW:
        m = WIN[w]
        if m.sum() < 12: continue
        b = boot(dg, m); b["exact_zero"] = bool(np.all(dg[m] == 0)); b["maxabs"] = float(np.max(np.abs(dg[m]))); res[w] = b
    tx = float(TPG[kx][WIN[PW]].mean()); ty = float(TPG[ky][WIN[PW]].mean()); dturn = (tx / ty - 1) * 100 if ty > 0 else float("nan")
    dsh = {w: sharpe(G_[kx][WIN[w]]) - sharpe(G_[ky][WIN[w]]) for w in (PW,) + YW}
    mc = {}
    for mo in sorted(set(months[WIN[PW]].tolist())):
        mm = (months == mo) & WIN[PW]; mc[str(mo)] = {"n": int(mm.sum()), "sum_bps": float(dg[mm].sum())}
    tot = sum(v["sum_bps"] for v in mc.values()); best = max(mc, key=lambda q: mc[q]["sum_bps"]); drop = boot(dg, WIN[PW] & (months != int(best)))
    worst_year = min(res[w]["mean"] for w in YW); worst_year_name = min(YW, key=lambda w: res[w]["mean"])
    OUT["deltas"][name] = {"x": kx, "ref": ky, "windows": res, "dturn_pct_primary": dturn, "turn_ref": ty, "turn_x": tx, "dSharpe": dsh, "maxDD_ref": maxdd(G_[ky][WIN[PW]]), "maxDD_x": maxdd(G_[kx][WIN[PW]]), "worst_year_delta": worst_year, "worst_year": worst_year_name,
                         "monthly_contrib": mc, "total_bps": tot, "best_month": best, "best_month_share": (mc[best]["sum_bps"] / tot if abs(tot) > 1e-9 else None), "n_months_pos": int(sum(1 for v in mc.values() if v["sum_bps"] > 0)), "n_months": len(mc), "drop_best_month": drop}
    f = lambda w: (f"{res[w]['mean']:+.3f} [{res[w]['lo']:+.3f},{res[w]['hi']:+.3f}] P{res[w]['P>0']:.2f}" + (" (=0)" if res[w]["exact_zero"] else "")) if w in res else "n/a"
    p(f"| {name} | {f('pre-2023')} | {f('2023')} | {f('2024')} | {f('2025')} | {f('2026<=cut')} | **{f(PW)}** | {f('2025->26<=cut')} | {worst_year:+.3f} ({worst_year_name}) | {dsh[PW]:+.3f} | {dturn:+.1f}% | {maxdd(G_[ky][WIN[PW]]):.0f}→{maxdd(G_[kx][WIN[PW]]):.0f} | {OUT['deltas'][name]['n_months_pos']}/{len(mc)} | {best} {mc[best]['sum_bps']:+.0f} bps ({(mc[best]['sum_bps']/tot*100 if abs(tot)>1e-9 else float('nan')):+.0f}%) | {drop['mean']:+.3f} [{drop['lo']:+.3f},{drop['hi']:+.3f}] |")
# ── frozen gate ──
p("\n## J · Frozen gate (PREREG §3 Track B; VERIFIED judge_trackB.json judge)")
p("| arm | seed | Δ 2024→26 [CI95] | (i-a) CI lower>0 | worst-year Δ | 2026 Δ | (i-b) worst≥+0.20 ∧ 2026≥−0.20 | (i) | Δturn% | (ii) ≤+10% | leak ① ③ | (iv) | per-seed pass |")
p("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
J = {}
for k in ("B1", "B2", "B3"):
    per = {}
    for s in ("42", "2027"):
        nm = f"{k}_s{s} − BASE_EXT_s{s} [primary]"
        if nm not in OUT["deltas"]: continue
        d = OUT["deltas"][nm]; pw = d["windows"][PW]; d26 = d["windows"]["2026<=cut"]["mean"]; wy = d["worst_year_delta"]
        ia = pw["lo"] > 0; ib = (wy >= 0.20) and (d26 >= -0.20); i_ = ia or ib; ii = d["dturn_pct_primary"] <= 10.0; lk = LEAK.get(f"{k}_s{s}"); iv = bool(lk and lk["pass"])
        per[s] = {"delta": pw["mean"], "CI": [pw["lo"], pw["hi"]], "i_a_CI_lower>0": bool(ia), "worst_year_delta": wy, "worst_year": d["worst_year"], "delta_2026": d26, "i_b": bool(ib), "i": bool(i_), "dturn_pct": d["dturn_pct_primary"], "ii_turn<=+10%": bool(ii), "leak": lk, "iv_leak_pass": iv, "seed_pass": bool(i_ and ii and iv)}
        p(f"| {k} | {s} | {pw['mean']:+.3f} [{pw['lo']:+.3f}, {pw['hi']:+.3f}] | {ia} | {wy:+.3f} ({d['worst_year']}) | {d26:+.3f} | {ib} | {i_} | {d['dturn_pct_primary']:+.1f}% | {ii} | {(str(lk['c1']) + ' ' + str(lk['c3'])) if lk else 'n/a'} | {iv} | {per[s]['seed_pass']} |")
    if len(per) == 2:
        same = np.sign(per["42"]["delta"]) == np.sign(per["2027"]["delta"]); ok = per["42"]["seed_pass"] and per["2027"]["seed_pass"] and bool(same)
        J[k] = {"seeds": per, "iii_same_sign": bool(same), "verdict": "PASS" if ok else "FAIL"}
        p(f"| **{k}** | both | — | — | — | — | — | — | — | — | — | (iii) same sign {bool(same)} | **{J[k]['verdict']}** |")
    else: J[k] = {"seeds": per, "iii_same_sign": None, "verdict": "INCOMPLETE (one seed)"}
OUT["judge"] = J
for k, v in J.items(): print(f"===== JUDGE Track B [{k}]: {v['verdict']} | " + " ; ".join(f"s{s}: Δ {q['delta']:+.4f} [{q['CI'][0]:+.4f},{q['CI'][1]:+.4f}] i={q['i']} (a {q['i_a_CI_lower>0']} b {q['i_b']}: worst {q['worst_year_delta']:+.3f} {q['worst_year']}, 2026 {q['delta_2026']:+.3f}) ii={q['ii_turn<=+10%']} ({q['dturn_pct']:+.1f}%) iv={q['iv_leak_pass']}" for s, q in v["seeds"].items()) + f" | iii same sign {v['iii_same_sign']}")
json.dump(OUT, open(f"{B}/results/judge_trackB.json", "w"), indent=1, default=float); open(f"{B}/results/trackB_tables.md", "w").write("\n".join(T) + "\n")
print(f"\nwrote {B}/results/judge_trackB.json and trackB_tables.md"); print("JUDGE_DONE", flush=True)
