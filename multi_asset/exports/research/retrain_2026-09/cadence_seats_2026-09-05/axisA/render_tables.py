"""render_tables.py — render REPORT tables (markdown) from the JSON products in cadence_seats/axisA. Read-only; prints markdown."""
import json, os, time
ROOT = "/workspace/review_scratch/cadence_seats/axisA"
def J(p):
    p = f"{ROOT}/{p}"; return json.load(open(p)) if os.path.exists(p) else None
def iso(t): return time.strftime("%Y-%m-%d %H:%M", time.gmtime(int(t)))
F = {"d1": J("folds_d1.json"), "rollm1": J("folds_rollm1.json"), "rollw1": J("folds_rollw1.json")}
C = J("d1_curve.json"); NF = J("noise_floor.json"); IL = J("ic_legs_seat.json"); JG = J("judge.json"); CW = J("d1w_curve.json")
KL = {"pinned": "K0 pinned", "rollm": "K1 rollm60", "rollm1": "K2 rollm1", "rollw1": "K3 rollw1", "k1rep": "K1 replicate"}
# ── folds ──
for tag, title in (("d1", "D1 retrain of the K1 monthly folds (embargo 60, same seeds)"), ("rollm1", "K2 monthly, embargo 1 anchor"), ("rollw1", "K3 weekly (Monday 00:00Z), embargo 1 anchor")):
    f = F[tag]
    if f is None: print(f"\n### Folds — {title}: NOT RUN\n"); continue
    cfg = f["config"]; folds = f["folds"]
    print(f"\n### Folds — {title}: `{os.path.basename(f['output'])}` sha256 `{f['sha256']}`; script sha256 `{cfg['self_sha256']}`; train_rule = `{cfg['train_rule']}`; assert = `{cfg['assert']}`; finite-mask equal to pinned = **{f['finite_mask_equal_pinned']}**; all asserts True = **{f['all_asserts_true']}**; folds {len(folds)}; total fit {f['total_fit_s']:.0f}s, wall {f['wall_s']:.0f}s")
    if tag == "d1": print(f"D1 receipts: stitched test-fold predictions == K1 `slow_pred_rollm.npy` (array_equal, equal_nan) = **{f['stitched_equal_k1']}**, max|Δ| {f['stitched_maxabs_vs_k1']:.3e}; boosters bitwise equal to K1 = **{sum(x['booster_equal_k1'] for x in folds)}/{len(folds)}**; train_rows equal to K1 = {sum(x['train_rows_equal_k1'] for x in folds)}/{len(folds)}")
    full = (tag != "rollw1")
    if full:
        print("\n| fold | test key | seed | train rows | train span | test anchors (rows) | test span | ASSERT | gap (anchors) | fit s | rank-IC raw | " + ("booster == K1 |" if tag == "d1" else ""))
        print("|---|---|---|---|---|---|---|---|---|---|---|" + ("---|" if tag == "d1" else ""))
        for x in folds:
            print(f"| {x['fold']} | {x['key']} | {x['seed']} | {x['train_rows']:,} | {iso(x['train_first'])[:10]}..{iso(x['train_last'])} | {x['test_anchors_with_rows']}/{x['test_anchors_in_fold']} ({x['test_rows']:,}) | {iso(x['test_first'])}..{iso(x['test_last'])} | {x['assert_lhs']} ({iso(x['assert_lhs'])}) {x['assert_cmp']} {x['assert_rhs']} ({iso(x['assert_rhs'])}) → **{x['assert_ok']}** | {x['gap_anchors']:.0f} | {x['fit_s']} | {x['rankIC_raw_y4']:+.4f} |" + (f" {x['booster_equal_k1']} |" if tag == "d1" else ""))
    else:
        gaps = sorted(set(round(x["gap_anchors"], 2) for x in folds)); ok = all(x["assert_ok"] for x in folds)
        print(f"\n{len(folds)} weekly folds; every fold printed `ASSERT ... -> True` (all True = **{ok}**); gap between last training label end and (first test anchor − 1 anchor) ∈ {gaps} anchors; train rows {min(x['train_rows'] for x in folds):,}..{max(x['train_rows'] for x in folds):,}; fit s min/median/max {min(x['fit_s'] for x in folds)}/{sorted(x['fit_s'] for x in folds)[len(folds)//2]}/{max(x['fit_s'] for x in folds)}; per-fold rank-IC (raw) mean {sum(x['rankIC_raw_y4'] for x in folds)/len(folds):+.4f}, min {min(x['rankIC_raw_y4'] for x in folds):+.4f}, max {max(x['rankIC_raw_y4'] for x in folds):+.4f}")
        print("\n| fold | week (Mon) | seed | train rows | train last | test anchors | test span | ASSERT ok | gap | fit s | rank-IC raw |")
        print("|---|---|---|---|---|---|---|---|---|---|---|")
        for x in folds:
            if x["fold"] % 10 == 0 or x["fold"] == len(folds) - 1:
                print(f"| {x['fold']} | {x['key']} | {x['seed']} | {x['train_rows']:,} | {iso(x['train_last'])} | {x['test_anchors_with_rows']}/{x['test_anchors_in_fold']} | {iso(x['test_first'])}..{iso(x['test_last'])} | {x['assert_ok']} | {x['gap_anchors']:.0f} | {x['fit_s']} | {x['rankIC_raw_y4']:+.4f} |")
        print("(every 10th fold shown; the full per-fold table is `folds_rollw1.json` / `logs/weekly1.log`)")
# ── D1 curve ──
if C:
    print(f"\n### D1 — Table A: IC and king-leg by model age, full anchor set available at each age")
    print("\n| age (months) | n (raw) | rank-IC raw y4 | n (y4s) | rank-IC y4s | days since cutoff mean (min..max) | n leg | king leg raw (bps/gross/anchor) | S raw | king leg y4s | S y4s | months |")
    print("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for k in range(1, 13):
        r = C["full"][str(k)]
        print(f"| {k} | {r['n_raw']} | {r['IC_raw']:+.4f} | {r['n_y4s']} | {r['IC_y4s']:+.4f} | {r['days_mean']:.0f} ({r['days_min']:.0f}..{r['days_max']:.0f}) | {r['n_leg']} | {r['leg_raw']:+.3f} | {r['S_raw']:+.3f} | {r['leg_y4s']:+.3f} | {r['S_y4s']:+.3f} | {r['first_month']}..{r['last_month']} |")
    for t in ("raw", "y4s"):
        n = C["common"][f"{t}/n"]; mo = C["common"][f"{t}/months"]
        print(f"\n### D1 — Table B[{t}]: common anchor set (all 12 ages finite), n = {n} anchors, months {mo[0]}..{mo[1]}; paired Δ = IC(age 1) − IC(age k), s.e. over anchors, UTC-day-block bootstrap CI95 (2000, seed 20260905)")
        print("\n| age | rank-IC | Δ(1−k) | s.e. | CI95 | t | king leg (bps) | S | Δleg(1−k) | s.e. |")
        print("|---|---|---|---|---|---|---|---|---|---|")
        for k in range(1, 13):
            r = C["common"][f"{t}/{k}"]
            print(f"| {k} | {r['IC']:+.4f} | {r['delta_1_minus_k']:+.4f} | {r['se']:.4f} | [{r['ci_lo']:+.4f}, {r['ci_hi']:+.4f}] | {r['t']:.2f} | {r['leg']:+.3f} | {r['S']:+.3f} | {r['dleg_1_minus_k']:+.3f} | {r['dleg_se']:.3f} |")
    print(f"\n### D1 — Table C: paired Δ = IC(age 1) − IC(age k) on each age's own anchor set")
    print("\n| age | n raw | IC age1 | IC age k | Δ raw | s.e. | CI95 | n y4s | IC age1 | IC age k | Δ y4s | s.e. | CI95 |")
    print("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for k in range(2, 13):
        a = C["paired_own"][str(k)]["raw"]; b = C["paired_own"][str(k)]["y4s"]
        print(f"| {k} | {a['n']} | {a['IC1']:+.4f} | {a['ICk']:+.4f} | {a['delta']:+.4f} | {a['se']:.4f} | [{a['ci_lo']:+.4f}, {a['ci_hi']:+.4f}] | {b['n']} | {b['IC1']:+.4f} | {b['ICk']:+.4f} | {b['delta']:+.4f} | {b['se']:.4f} | [{b['ci_lo']:+.4f}, {b['ci_hi']:+.4f}] |")
    print(f"\n### D1 — Table D: all (model, anchor) pairs binned by days since the model's cutoff")
    print("\n| days since cutoff | pairs | rank-IC raw | rank-IC y4s | king leg raw | S raw |")
    print("|---|---|---|---|---|---|")
    for b, r in C["days_bins"].items(): print(f"| {b} | {r['pairs']} | {r['IC_raw']:+.4f} | {r['IC_y4s']:+.4f} | {r['leg_raw']:+.3f} | {r['S_raw']:+.3f} |")
    print(f"\n### D1 — Table E: common set split by calendar year (raw y4)")
    print("\n| year | n | age 1 | age 2 | age 3 | age 6 | age 9 | age 12 | Δ(1−12) | s.e. |")
    print("|---|---|---|---|---|---|---|---|---|---|")
    for y, r in C["by_year_common"].items(): print(f"| {y} | {r['n']} | {r['age1']:+.4f} | {r['age2']:+.4f} | {r['age3']:+.4f} | {r['age6']:+.4f} | {r['age9']:+.4f} | {r['age12']:+.4f} | {r['delta_1_12']:+.4f} | {r['se']:.4f} |")
    print(f"\n### D1 — Table F (auxiliary): K0 pinned by month-of-year (= age within its year fold), 2024-01..2026-08")
    print("\n| month | n | pinned IC raw | pinned IC y4s | pinned king leg raw | S | K1 age-1 IC raw on the same anchors |")
    print("|---|---|---|---|---|---|---|")
    for m, r in C["pinned_month_of_year"].items(): print(f"| {m} | {r['n']} | {r['IC_raw']:+.4f} | {r['IC_y4s']:+.4f} | {r['leg_raw']:+.3f} | {r['S_raw']:+.3f} | {r['K1_age1_IC_raw']:+.4f} |")
    h = C["pinned_halves"]; print(f"\npinned H1 (months 1–6) vs H2 (7–12) IC raw: {h['H1_IC_raw']:+.4f} (n {h['H1_n']}) vs {h['H2_IC_raw']:+.4f} (n {h['H2_n']}); diff {h['H1_minus_H2']:+.4f} ± {h['se_unpaired']:.4f} (unpaired)")
    d = C["decision"]; print(f"\n**D1 decision (frozen statistic):** paired IC(age 1) − IC(age 12), common set: raw **{d['raw_delta_1_12']:+.4f} ± {d['raw_se']:.4f}** CI95 [{d['raw_ci'][0]:+.4f}, {d['raw_ci'][1]:+.4f}]; y4s **{d['y4s_delta_1_12']:+.4f} ± {d['y4s_se']:.4f}** CI95 [{d['y4s_ci'][0]:+.4f}, {d['y4s_ci'][1]:+.4f}]; threshold {d['threshold']} ⇒ decay detectable = **{d['decay_detectable']}** ⇒ K3 **{d['K3']}**")
if CW:
    r = CW["receipt"]; ft = CW["fit_time"]
    print(f"\n### Weekly-resolution age curve (addendum; diagnostic only) — from the {ft['n_fits']} saved K3 weekly boosters; receipt: age-1 stitch from the saved boosters vs `slow_pred_rollw1.npy` array_equal = **{r['age1_equal_k3']}** (max|Δ| {r['age1_maxabs_vs_k3']:.3e}); rows predicted {r['predicted_rows']:,}. Fit time (n_jobs {ft['n_jobs']}): per fit min/median/max {ft['fit_s_min']}/{ft['fit_s_median']}/{ft['fit_s_max']} s, total fit {ft['fit_s_total']:.0f} s, wall {ft['wall_s_total']:.0f} s")
    print("\n#### Table W-A: full anchor set at each weekly age\n\n| age (weeks) | n raw | rank-IC raw | n y4s | rank-IC y4s | days since cutoff mean (min..max) | n leg | king leg raw | S raw | king leg y4s | S y4s |")
    print("|---|---|---|---|---|---|---|---|---|---|---|")
    for w in range(1, 9):
        x = CW["full"][str(w)]; print(f"| {w} | {x['n_raw']} | {x['IC_raw']:+.4f} | {x['n_y4s']} | {x['IC_y4s']:+.4f} | {x['days_mean']:.1f} ({x['days_min']:.1f}..{x['days_max']:.1f}) | {x['n_leg']} | {x['leg_raw']:+.3f} | {x['S_raw']:+.3f} | {x['leg_y4s']:+.3f} | {x['S_y4s']:+.3f} |")
    for t in ("raw", "y4s"):
        n = CW["common"][f"{t}/n"]; h = CW["common"][f"{t}/w1-4_minus_w5-8"]
        print(f"\n#### Table W-B[{t}]: common anchor set (all 8 weekly ages finite), n = {n}; paired Δ = IC(age 1 w) − IC(age w); weeks 1–4 vs 5–8: {h['mean_w1_4']:+.4f} vs {h['mean_w5_8']:+.4f}, paired Δ {h['delta']:+.4f} ± {h['se']:.4f}\n\n| age (weeks) | rank-IC | Δ(1−w) | s.e. | CI95 | king leg | S | Δleg(1−w) | s.e. |")
        print("|---|---|---|---|---|---|---|---|---|")
        for w in range(1, 9):
            x = CW["common"][f"{t}/{w}"]; print(f"| {w} | {x['IC']:+.4f} | {x['delta_1_minus_w']:+.4f} | {x['se']:.4f} | [{x['ci_lo']:+.4f}, {x['ci_hi']:+.4f}] | {x['leg']:+.3f} | {x['S']:+.3f} | {x['dleg_1_minus_w']:+.3f} | {x['dleg_se']:.3f} |")
    print("\n#### Table W-D: all (model, anchor) pairs by days since cutoff, 7-day bins\n\n| days | pairs | rank-IC raw | rank-IC y4s | king leg raw | S raw |\n|---|---|---|---|---|---|")
    for b, x in CW["days_bins"].items(): print(f"| {b} | {x['pairs']} | {x['IC_raw']:+.4f} | {x['IC_y4s']:+.4f} | {x['leg_raw']:+.3f} | {x['S_raw']:+.3f} |")
if NF:
    print(f"\n### Noise floor — K1 replicate (D1 retrain, same recipe and seeds, LightGBM bits differ) vs K1: n {NF['n_anchors']} anchors; per-anchor Spearman between the two prediction vectors mean {NF['pred_spearman_mean']:.4f} (5th pct {NF['pred_spearman_p5']:.4f}, min {NF['pred_spearman_min']:.4f}); ΔIC raw {NF['dIC_raw_mean']:+.5f} ± {NF['dIC_raw_se']:.5f} (per-anchor sd {NF['dIC_raw_sd']:.4f}); ΔIC y4s {NF['dIC_y4s_mean']:+.5f} ± {NF['dIC_y4s_se']:.5f}; Δking-leg raw {NF['dleg_raw_mean']:+.4f} ± {NF['dleg_raw_se']:.4f} bps/gross/anchor (sd {NF['dleg_raw_sd']:.3f}); Δking-leg y4s {NF['dleg_y4s_mean']:+.4f} ± {NF['dleg_y4s_se']:.4f}; IC raw K1 replicate {NF['IC_raw_k1rep']:+.4f} vs K1 {NF['IC_raw_k1']:+.4f}")
# ── IC / legs by king ──
if IL:
    kings = list(IL["kings"].keys()); WINS = ["2024", "2025", "2026<=08-10", "2026->08-30", "2024->26", "2025->26"]
    for tgt, desc in (("raw", "raw y4 = Σ 5m simple returns over [E, E+47] (meta; production label source)"), ("y4s", "dlw y4s = Π(1+r5)−1 over [E+1, E+48] (compounded holding-window target)")):
        print(f"\n### Yearly mean rank-IC vs {desc}; identical anchor set for all sources (2024+, finite IC for every source)")
        print("\n| window | n | " + " | ".join(KL[k] for k in kings) + " | " + " | ".join(f"Δ {KL[k]}−K0 (mean ± SE)" for k in kings if k != "pinned") + " |")
        print("|---|---|" + "---|" * len(kings) + "---|" * (len(kings) - 1))
        for w in WINS:
            r = IL["ic"][f"{tgt}/{w}"]
            print(f"| {w} | {r['n']} | " + " | ".join(f"{r[k]:+.4f}" for k in kings) + " | " + " | ".join(f"{r['d_'+k][0]:+.4f} ± {r['d_'+k][1]:.4f}" for k in kings if k != "pinned") + " |")
    for cal, desc in (("raw", "raw y4"), ("y4s", "compounded y4s (anchors with a dlw row, ≤ 2026-08-10 20:00Z)")):
        print(f"\n### King leg (production leg definition, bps per unit gross per anchor) — caliber {desc}; S = mean/std per anchor")
        print("\n| leg | " + " | ".join(WINS) + " | S/anchor 900 pre-0810 (seat window) | S/anchor last 900 |")
        print("|---|" + "---|" * (len(WINS) + 2))
        for name in [f"king[{k}]" for k in kings] + ["rev24", "fund"]:
            r = IL["legs"].get(f"{cal}/{name}")
            if r is None: continue
            print(f"| {name} | " + " | ".join(f"{r[w][0]:+.3f} (S {r[w][1]:+.3f}, n {r[w][2]})" for w in WINS) + f" | {r['S900pre']:+.4f} (mean {r['mean900pre']:+.3f}) | {r['S900last']:+.4f} (mean {r['mean900last']:+.3f}) |")
    print(f"\n### msharpe seat at 2026-08-10 20:00Z (production rule, LOOK=900; w101 = LEGS=101 mask = deployed combo seat)")
    print("\n| caliber | king | shp king/rev24/fund | w3 king/rev24/fund | w101 king/fund |")
    print("|---|---|---|---|---|")
    for cal in ("raw", "y4s"):
        for k in kings:
            r = IL["seat"][f"{cal}/{k}"]; print(f"| {cal} | {KL[k]} | {r['shp'][0]:+.4f}/{r['shp'][1]:+.4f}/{r['shp'][2]:+.4f} | {r['w3'][0]:.3f}/{r['w3'][1]:.3f}/{r['w3'][2]:.3f} | {r['w101'][0]:.3f}/{r['w101'][2]:.3f} |")
# ── book ──
if JG:
    kings = JG["kings"]; LW = ["2024", "2025", "2026<=08-10", "2026->08-30", "2024->26", "2025->26"]
    print(f"\n### Book levels — arm d30_n2_c42, L-fix (M829/T400/FTRIM zero, W3FIX 0.21/0/0.79, LEGS=101, LOOK=900, φ=0.45, FSEED=42), column net_ex (bps/anchor per unit NAV); n = {JG['n_anchors']} paired anchors; windows {JG['windows']}")
    for cal, desc in (("log", "raw Σ-simple y4, CAL=log = no transform"), ("prod", "compounded Π(1+r5)−1 target (meta_newprod swap), CAL=log")):
        print(f"\n**caliber {cal} = {desc}** — cells: mean bps/anchor (Sharpe; maxDD bps); %/gross/yr = mean × 2190 / 100")
        print("\n| king | " + " | ".join(LW) + " | %/gross/yr 2024 / 2025 / 2026(8m ann.) | worst month (bps) | gross 25on | turnover 25on | carry 25on | cost 25on |")
        print("|---|" + "---|" * (len(LW) + 5))
        for k in kings:
            r = JG["levels"][f"{cal}/{k}"]; r25 = r["2025->26"]
            print(f"| {KL[k]} | " + " | ".join(f"{r[w]['mean']:+.3f} (S {r[w]['sharpe']:+.2f}; DD {r[w]['maxDD']:.0f})" for w in LW) + f" | {r['2024']['pct_gross_yr']:+.1f} / {r['2025']['pct_gross_yr']:+.1f} / {r['2026->08-30']['pct_gross_yr']:+.1f} | {r['worst_month']['ym']} {r['worst_month']['sum_bps']:+.0f} | {r25['gross']:.3f} | {r25['turn']:.5f} | {r25['carry']:+.3f} | {r25['cost']:.3f} |")
    print(f"\n### Book deltas — paired by anchor, UTC-day-block bootstrap (2000, seed 20260905); cells: Δ bps/anchor [CI95] P(Δ>0)")
    for cal in ("log", "prod"):
        print(f"\n**caliber {cal}**")
        print("\n| pair | " + " | ".join(LW) + " | ΔSharpe 24on / 25on | Δturnover % 25on / 24on | maxDD ref / x (25on) |")
        print("|---|" + "---|" * (len(LW) + 3))
        for key, d in JG["deltas"].items():
            if not key.startswith(cal + "/"): continue
            name = key.split("/", 1)[1]; w = d["windows"]
            print(f"| {name} | " + " | ".join(f"{w[x]['mean']:+.3f} [{w[x]['lo']:+.3f}, {w[x]['hi']:+.3f}] {w[x]['P>0']:.3f}" for x in LW) + f" | {d['dSharpe']['2024->26']:+.2f} / {d['dSharpe']['2025->26']:+.2f} | {d['dturn']['2025->26']['dturn_pct']:+.1f} / {d['dturn']['2024->26']['dturn_pct']:+.1f} | {d['maxDD_ref_25on']:.0f} / {d['maxDD_x_25on']:.0f} |")
    sf = JG["sigma_fund"]; print(f"\n### σ_fund terciles of Δ (2024→26, auxiliary): cuts {sf['cuts_bps']} bps/8h, n per tercile {sf['n']}")
    print("\n| caliber | pair | low | mid | high |")
    print("|---|---|---|---|---|")
    for key, rec in sf.items():
        if "/" not in key: continue
        cal, name = key.split("/", 1)
        print(f"| {cal} | {name} | " + " | ".join(f"{rec[t]['mean']:+.3f} [{rec[t]['lo']:+.3f}, {rec[t]['hi']:+.3f}] (ref {rec[t]['ref_mean']:+.3f} → {rec[t]['x_mean']:+.3f})" for t in ("low", "mid", "high")) + " |")
    print(f"\n### Frozen decision (PREREG §1; primary 2025→26, both calibers; ADMIT iff both CI95 lower > 0 and Δturnover ≤ +15%; REJECT iff either CI95 upper < 0 or Δturnover > +25%; else UNDECIDED)")
    print("\n| candidate | caliber | Δ 2025→26 [CI95] | CI lower > 0 | CI upper < 0 | Δturnover % (25on) | turn ≤ +15% | turn > +25% | aux Δ 2024→26 [CI95] | yearly Δ 2024 / 2025 / 2026 | verdict |")
    print("|---|---|---|---|---|---|---|---|---|---|---|")
    for k, d in JG["decision"].items():
        if k == "embargo_cost_K2_minus_K1": continue
        for cal, c in d["checks"].items():
            print(f"| {KL[k]} | {cal} | {c['primary_2025->26_delta']:+.3f} [{c['primary_CI'][0]:+.3f}, {c['primary_CI'][1]:+.3f}] | {c['CI_lower>0']} | {c['CI_upper<0']} | {c['dturn_pct_25on']:+.1f} | {c['turn<=+15%']} | {c['turn>+25%']} | {c['aux_2024->26_delta']:+.3f} [{c['aux_2024->26_CI'][0]:+.3f}, {c['aux_2024->26_CI'][1]:+.3f}] | {c['yearly'][0]:+.3f} / {c['yearly'][1]:+.3f} / {c['yearly'][2]:+.3f} | **{d['verdict']}** |")
    e = JG["decision"].get("embargo_cost_K2_minus_K1")
    if e:
        print(f"\n**Embargo cost K2 − K1 (reported separately, not for selection):** " + "; ".join(f"{cal}: 2025→26 {e[cal]['2025->26']['mean']:+.3f} [{e[cal]['2025->26']['lo']:+.3f}, {e[cal]['2025->26']['hi']:+.3f}], 2024→26 {e[cal]['2024->26']['mean']:+.3f} [{e[cal]['2024->26']['lo']:+.3f}, {e[cal]['2024->26']['hi']:+.3f}], yearly {e[cal]['2024']['mean']:+.3f}/{e[cal]['2025']['mean']:+.3f}/{e[cal]['2026->08-30']['mean']:+.3f}" for cal in ("log", "prod")))
