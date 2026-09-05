#!/usr/bin/env python
"""c4_frontier.py — Track C · C3 (seat_round2 B1 maximin re-read) + C4 all-weather frontier table across EXISTING archived device artifacts (no reruns; read-only on every source).
One uniform metric function for every arm: g = net_ex/gross_total [bps/anchor per unit gross] from the d30_n2_c42_rec array of each w10_ablation_series_*.npz; windows 2024 | 2025 | 2026→cut (2026-08-10 20:00Z)
| 2024→26; anchor Sharpe = mean/std(ddof=1)×√2190; maxDD at 2× over 2024→26 from Π(1+2g/1e4); worst-year Sharpe = min over {2024, 2025, 2026→cut}; turnover = rec turnover/gross_total (2024→26 mean).
NAV %/yr at 2× (arithmetic) = mean g × 6 × 365 × 2 / 1e4 × 100. Form columns are read from each artifact's self-reported config_json (device sha, universe mask, cost source, seat rule, φ, FTRIM, legs, king source, seed)
— arms whose form differs from the health_check main arm (M1 rank base · U-PIT · live fee tiers · dynamic seat · φ 0.45 · FTRIM zero · LEGS 101 · pinned king) are flagged, and their numbers are NOT comparable
to the main arm at the ±0.05 bps resolution (different cost vectors / rank base / trade set). C2 overlay rows come from c2/c2_voltarget.json. Sorted by worst-year Sharpe. No admission claim.
usage: c4_frontier.py → c4/c4_frontier.json, c4/c4_frontier.md, c4/c3_seat_round2_B1.md"""
import numpy as np, json, time, os, glob, hashlib, calendar
ROOT = "/workspace/review_scratch/allweather_trackC"; RS = "/workspace/review_scratch"
APY = 2190; L = 2.0
def T(s): return int(calendar.timegm(time.strptime(s, "%Y-%m-%d")))
CUT = T("2026-08-10") + 20 * 3600
WIN = {"2024": (T("2024-01-01"), T("2025-01-01")), "2025": (T("2025-01-01"), T("2026-01-01")), "2026->cut": (T("2026-01-01"), CUT + 1), "2024->26": (T("2024-01-01"), CUT + 1), "2025->26": (T("2025-01-01"), CUT + 1)}
YEARS = ("2024", "2025", "2026->cut")
COLS = ["ts", "net", "pnl", "carry", "cost", "gross_total", "gross_member", "gross_sel", "nsel", "nmember", "fires", "leg_king", "leg_rev24", "leg_fund", "w3_king", "w3_rev24", "w3_fund", "turnover", "net_ex", "pnl_ex", "carry_ex", "cost_ex", "netlong"]
C = {k: i for i, k in enumerate(COLS)}
def r4(v): return None if v is None or (isinstance(v, float) and not np.isfinite(v)) else round(float(v), 4)
def sharpe(x): return float(x.mean() / x.std(ddof=1) * np.sqrt(APY)) if len(x) > 2 and x.std(ddof=1) > 0 else float("nan")
def maxdd(g):
    nav = np.cumprod(1.0 + L * g / 1e4); return float((1.0 - nav / np.maximum.accumulate(nav)).max() * 100)
def bn(p): return os.path.basename(p) if p else None
MAIN = {"UMASK_SCOPE": "m1", "mask": "umask_UPIT.npz", "cost": "costb_fee_steady.json", "W3FIX": None, "PHI": 0.45, "FTRIM": "zero", "LEGS": "101", "king": "slow_pred_pinned.npy", "TRADE_TOPN": 0, "MEMBERS_TOPN": 829}
def form_of(cfg):
    f = {"device_sha16": (cfg.get("HEALTH") or cfg.get("TRACKC") or cfg.get("SEAT2") or cfg.get("AXISB") or {}).get("device_sha256", "?")[:16] if isinstance((cfg.get("HEALTH") or cfg.get("TRACKC") or cfg.get("SEAT2") or cfg.get("AXISB")), dict) else "?",
         "UMASK_SCOPE": cfg.get("UMASK_SCOPE", "members(orig)"), "mask": bn(cfg.get("UMASK_NPZ")), "cost": bn(cfg.get("COSTB_JSON")) or "device-default", "W3FIX": cfg.get("W3FIX"), "PHI": cfg.get("PHI"), "FTRIM": cfg.get("FTRIM"), "LEGS": cfg.get("LEGS"),
         "king": bn(cfg.get("SLOW_NPY")) or "pod_backup slow_pred_hist_oos", "TRADE_TOPN": cfg.get("TRADE_TOPN", 0), "MEMBERS_TOPN": cfg.get("MEMBERS_TOPN"), "FSEED": cfg.get("FSEED"), "CAL": cfg.get("CAL")}
    for k in ("SEATF10", "SEATNET", "SEATCOST_BPS", "PHIDYN", "AGEW", "KMOD", "KTAIL", "FUNDSCALE", "AXISB"):
        if k in cfg and cfg[k] not in (0, 0.0, None, False): f[k] = cfg[k] if not isinstance(cfg[k], dict) else {kk: vv for kk, vv in cfg[k].items() if kk != "device"}
    if "AXISB" in cfg and isinstance(cfg["AXISB"], dict): f["AXISB"] = {kk: vv for kk, vv in cfg["AXISB"].items() if kk not in ("device", "device_sha256")}
    dev = [k for k in ("UMASK_SCOPE", "mask", "cost", "W3FIX", "PHI", "FTRIM", "LEGS", "king", "TRADE_TOPN", "MEMBERS_TOPN") if f.get(k) != MAIN[k]]
    f["form_matches_main"] = len(dev) == 0; f["deviations_from_main"] = dev
    return f
def metrics(R):
    ts = R[:, 0].astype(np.int64); g = R[:, C["net_ex"]] / R[:, C["gross_total"]]; tpg = R[:, C["turnover"]] / R[:, C["gross_total"]]; out = {}
    for wn, (lo, hi) in WIN.items():
        m = (ts >= lo) & (ts < hi)
        out[wn] = {"n": int(m.sum()), "mean": r4(g[m].mean()), "sharpe": r4(sharpe(g[m])), "maxdd_pct_at_2x": r4(maxdd(g[m])), "turnover_per_gross": r4(tpg[m].mean()), "gross_total": r4(R[m, C["gross_total"]].mean()), "w3_king": r4(R[m, C["w3_king"]].mean()), "nav_pct_yr_at_2x": r4(g[m].mean() * 6 * 365 * 2 / 1e4 * 100)}
    out["worst_year_sharpe"] = r4(min(out[y]["sharpe"] for y in YEARS)); out["worst_year"] = min(YEARS, key=lambda y: out[y]["sharpe"]); out["worst_year_mean"] = out[out["worst_year"]]["mean"]
    out["n_negative_years"] = int(sum(out[y]["mean"] < 0 for y in YEARS)); return out
def rows_from_dir(family, d, pattern, label):
    rows = []
    for p in sorted(glob.glob(f"{d}/{pattern}")):
        Z = np.load(p, allow_pickle=True)
        if [str(c) for c in Z["cols"]] != COLS or "d30_n2_c42_rec" not in Z.files: print("SKIP layout", p); continue
        cfg = json.loads(str(Z["config_json"])); R = Z["d30_n2_c42_rec"]; tag = os.path.basename(p).replace("w10_ablation_series_", "").replace(".npz", "")
        cal = "prod" if "/dev_alt/" in p else "log"
        rows.append({"family": family, "arm": label(tag), "tag": tag, "caliber": cal, "artifact": p, "sha16": hashlib.sha256(open(p, "rb").read()).hexdigest()[:16], "form": form_of(cfg), "m": metrics(R), "n_anchors": int(R.shape[0])})
    return rows
def main():
    rows = []
    hc = f"{RS}/health_check"
    def hcl(t): return {"M1_UPIT": "HC main: dynamic seat · U-PIT · m1", "FIX_UPIT": "HC pinned seat 0.21 · U-PIT · m1", "M1_UFROZEN": "HC dynamic seat · U-FROZEN (look-ahead upper bound) · m1", "MEM_UPIT": "HC dynamic seat · U-PIT · members scope", "UPIT": "HC dynamic seat · U-PIT · trade scope", "UFROZEN": "HC dynamic · U-FROZEN · trade scope"}.get(t.rsplit("_", 3)[0] if t.count("_") >= 3 else t, t) + (" · cost=" + t.rsplit("_", 1)[1])
    for d in ("dev_alt", "dev"): rows += rows_from_dir("health_check", f"{hc}/{d}/probe_artifacts", "w10_ablation_series_*_c*.npz", hcl)
    sr = f"{RS}/seat_round2"
    def srl(t): return {"B0": "SR2 B0 = HC main rerun", "B1": "SR2 B1 F10 own seat (SEATF10)", "B2": "SR2 B2 seat input net of carry (SEATNET)", "B3": "SR2 B3 B2 + turnover cost 2.035 (SEATCOST)", "B4": "SR2 B4 dynamic φ_t (PHIDYN)", "B5": "SR2 B5 B1+B4", "B6": "SR2 B6 B3+B5"}[t.split("_")[0]]
    for d in ("dev_alt", "dev"): rows += rows_from_dir("seat_round2", f"{sr}/{d}/probe_artifacts", "w10_ablation_series_B*.npz", srl)
    rows += rows_from_dir("phi_grid", f"{RS}/phi_grid/dev_alt/probe_artifacts", "w10_ablation_series_prod_phi*.npz", lambda t: f"PHI φ={t.split('_')[1][3:4]}.{t.split('_')[1][4:]} (HC form)")
    ca = f"{RS}/cadence_seats/axisA"
    def cal_(t):
        seat, king = t.split("_")[0], t.split("_")[1]; K = {"pinned": "K0 pinned", "rollm": "K1 monthly rolling", "rollm1": "K2 monthly −1 anchor embargo", "rollw1": "K3 weekly −1", "k1rep": "K1 replicate"}[king]
        return f"CAD-A {K} · {'dynamic seat' if seat == 'Ldyn' else 'fixed seat 0.21'} (recheck device, default cost, T400)"
    for d in ("dev_alt", "dev"): rows += rows_from_dir("cadence_axisA", f"{ca}/{d}/probe_artifacts", "w10_ablation_series_L*.npz", cal_)
    cb = f"{RS}/cadence_seats/axisB"
    def cbl(t):
        r, king = t.split("_")[0], t.split("_")[1]; R_ = {"R0": "R0 msharpe-900 (live rule)", "R1": "R1 window 300", "R2": "R2 net-of-turnover κ", "R3": "R3 shrinkage", "R4": "R4 mean-cov", "R5": "R5 σ_fund-conditional"}[r]
        return f"CAD-B {R_} · king {'K0 pinned' if king == 'pinned' else 'K1 monthly'} (seats device, default cost, T400)"
    for d in ("dev_alt", "dev"): rows += rows_from_dir("cadence_axisB", f"{cb}/{d}/probe_artifacts", "w10_ablation_series_R*.npz", cbl)
    for d in ("dev_alt", "dev"): rows += rows_from_dir("trackC_C1", f"{ROOT}/{d}/probe_artifacts", "w10_ablation_series_A*.npz", lambda t: f"C1 AGEW={ {'A0': '0 (=HC main)', 'A05': '0.5', 'A10': '1.0', 'A20': '2.0'}[t.split('_')[0]] } (HC form)")
    # C2 overlays from json
    c2p = f"{ROOT}/c2/c2_voltarget.json"
    if os.path.exists(c2p):
        c2 = json.load(open(c2p))
        for cn, cell in c2["cells"].items():
            cal, s = cn.split("/")
            for an, a in cell["arms"].items():
                st = a["levels"]; m = {w: {"n": st[w]["n"], "mean": st[w]["mean"], "sharpe": st[w]["sharpe"], "maxdd_pct_at_2x": st[w]["maxdd_pct_at_2x"], "turnover_per_gross": None, "gross_total": None, "w3_king": None, "nav_pct_yr_at_2x": st[w]["nav_pct_yr_at_2x_arith"]} for w in WIN}
                m["worst_year_sharpe"] = st["worst_year_sharpe"]; m["worst_year"] = st["worst_year"]; m["worst_year_mean"] = st[st["worst_year"]]["mean"]; m["n_negative_years"] = int(sum(st[y]["mean"] < 0 for y in YEARS))
                rows.append({"family": "trackC_C2", "arm": f"C2 {'insurance' if a['form'] == 'ins' else 'symmetric control'} q={a['q']:.2f} overlay on HC main", "tag": f"C2_{an}_{cal}_{s}", "caliber": cal, "artifact": c2p, "sha16": hashlib.sha256(open(c2p, "rb").read()).hexdigest()[:16],
                             "form": {"form_matches_main": False, "deviations_from_main": ["paper overlay (gross gate) on HC main series; cost 3.92 bps/unit gross moved"], "FSEED": s[1:], "CAL": cal}, "m": m, "n_anchors": None})
    # cross-check against the archived health_check metrics json (2024 mean / Sharpe / 2024->26)
    ref = json.load(open(f"{hc}/results/M1_UPIT_prod_s42_ccal.json")); mine = next(r for r in rows if r["tag"] == "M1_UPIT_prod_s42_ccal")["m"]
    chk = {"2024_mean": (ref["windows"]["2024"]["per_gross"]["mean_bps_anchor"], mine["2024"]["mean"]), "2024_sharpe": (ref["windows"]["2024"]["per_gross"]["sharpe_anchor"], mine["2024"]["sharpe"]), "2024->26_mean": (ref["windows"]["2024->26"]["per_gross"]["mean_bps_anchor"], mine["2024->26"]["mean"]),
           "2024->26_maxdd_2x": (ref["windows"]["2024->26"]["by_L"]["2.0"]["maxdd_pct"], mine["2024->26"]["maxdd_pct_at_2x"]), "2025_sharpe": (ref["windows"]["2025"]["per_gross"]["sharpe_anchor"], mine["2025"]["sharpe"])}
    for k, (a, b) in chk.items(): assert abs(a - b) < 2e-3, (k, a, b)
    print("CROSSCHECK health_check results/M1_UPIT_prod_s42_ccal.json vs uniform metric: " + json.dumps(chk))
    rows.sort(key=lambda r: -(r["m"]["worst_year_sharpe"] if r["m"]["worst_year_sharpe"] is not None else -9))
    defs = sorted(set((r["family"], r["arm"]) for r in rows)); defs_prod = sorted(set((r["family"], r["arm"]) for r in rows if r["caliber"] == "prod"))
    out = {"prereg": "docs/PREREG_allweather_programme_2026-09-05.md §3 Track C C3/C4", "crosscheck": chk, "n_rows": len(rows), "n_rows_prod": sum(r["caliber"] == "prod" for r in rows), "n_distinct_arm_definitions": len(defs), "n_distinct_arm_definitions_prod": len(defs_prod), "rows": rows}
    json.dump(out, open(f"{ROOT}/c4/c4_frontier.json", "w"), indent=1, ensure_ascii=False)
    Lm = []; P = Lm.append
    P(f"## C4 · all-weather frontier over archived arms — prod caliber (记账口径), sorted by worst-year Sharpe. Rows {out['n_rows_prod']} (all calibers {out['n_rows']}); distinct arm definitions {out['n_distinct_arm_definitions_prod']} prod ({out['n_distinct_arm_definitions']} incl. log) = the multiple-comparison count. No admission claim.")
    P("g = bps/anchor per gross; S = anchor Sharpe; DD = maxDD at 2× over 2024→26; turn = turnover/gross 2024→26; NAV%/yr@2× = g×43.8. `form≠main` = not comparable to the main arm at ±0.05 bps (different cost vector / rank base / trade set / seat).")
    P("| # | family | arm | seed | worst-yr S (yr, g) | 2024 g S | 2025 g S | 2026→cut g S | 2024→26 g S | DD@2× | turn | neg yrs | form |")
    P("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    i = 0
    for r in rows:
        if r["caliber"] != "prod": continue
        i += 1; m = r["m"]; f = lambda w: f"{m[w]['mean']:+.2f} S{m[w]['sharpe']:.2f}"
        fm = "main" if r["form"].get("form_matches_main") else "≠main: " + ", ".join(str(x) for x in r["form"].get("deviations_from_main", []))[:60]
        P(f"| {i} | {r['family']} | {r['arm']} | {r['form'].get('FSEED')} | **{m['worst_year_sharpe']:.2f}** ({m['worst_year']}, {m['worst_year_mean']:+.2f}) | {f('2024')} | {f('2025')} | {f('2026->cut')} | {f('2024->26')} | {m['2024->26']['maxdd_pct_at_2x']:.1f}% | {m['2024->26']['turnover_per_gross'] if m['2024->26']['turnover_per_gross'] is not None else '—'} | {m['n_negative_years']} | {fm} |")
    P(f"\n## C4 · same table, log caliber (Σ-simple raw y4) — secondary")
    P("| # | family | arm | seed | worst-yr S (yr, g) | 2024 g S | 2025 g S | 2026→cut g S | 2024→26 g S | DD@2× | turn | neg yrs | form |")
    P("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    i = 0
    for r in rows:
        if r["caliber"] != "log": continue
        i += 1; m = r["m"]; f = lambda w: f"{m[w]['mean']:+.2f} S{m[w]['sharpe']:.2f}"
        fm = "main-form" if r["form"].get("form_matches_main") else "≠main: " + ", ".join(str(x) for x in r["form"].get("deviations_from_main", []))[:60]
        P(f"| {i} | {r['family']} | {r['arm']} | {r['form'].get('FSEED')} | **{m['worst_year_sharpe']:.2f}** ({m['worst_year']}, {m['worst_year_mean']:+.2f}) | {f('2024')} | {f('2025')} | {f('2026->cut')} | {f('2024->26')} | {m['2024->26']['maxdd_pct_at_2x']:.1f}% | {m['2024->26']['turnover_per_gross'] if m['2024->26']['turnover_per_gross'] is not None else '—'} | {m['n_negative_years']} | {fm} |")
    open(f"{ROOT}/c4/c4_frontier.md", "w").write("\n".join(Lm) + "\n")
    # C3: seat_round2 B1 vs B0 maximin re-read (uniform per-gross metric; the archived judge.json 'yearly' block is in device-book scale, quoted alongside)
    J = json.load(open(f"{sr}/judge.json")); L3 = []; P3 = L3.append
    P3("## C3 · seat_round2 B1 (F10 own seat) vs B0 under a maximin reading — uniform per-gross metric (this script) + archived judge.json yearly (device-book scale net_ex, NOT per gross)")
    P3("| cell | arm | worst-yr S (yr) | Δ worst-yr S vs B0 | worst-yr g | 2024 g S | 2025 g S | 2026→cut g S | 2024→26 g S DD | archived yearly sharpe 2024/2025/2026 (judge.json) | archived yearly mean net_ex 2024/2025/2026 |")
    P3("|---|---|---|---|---|---|---|---|---|---|---|")
    c3 = {}
    for cal in ("prod", "log"):
        for s in ("42", "2027"):
            b0 = next(r for r in rows if r["tag"] == f"B0_{cal}_s{s}")["m"]; b1 = next(r for r in rows if r["tag"] == f"B1_{cal}_s{s}")["m"]
            for nm, m in (("B0", b0), ("B1", b1)):
                jy = J["yearly"].get(f"{cal}/s{s}/{nm}", {}); f = lambda w: f"{m[w]['mean']:+.3f} S{m[w]['sharpe']:.2f}"
                P3(f"| {cal}/s{s} | {nm} | {m['worst_year_sharpe']:.2f} ({m['worst_year']}) | {(m['worst_year_sharpe'] - b0['worst_year_sharpe']):+.2f} | {m['worst_year_mean']:+.3f} | {f('2024')} | {f('2025')} | {f('2026->cut')} | {f('2024->26')} DD{m['2024->26']['maxdd_pct_at_2x']:.1f}% | {jy.get('2024', {}).get('sharpe')}/{jy.get('2025', {}).get('sharpe')}/{jy.get('2026', {}).get('sharpe')} | {jy.get('2024', {}).get('mean')}/{jy.get('2025', {}).get('mean')}/{jy.get('2026', {}).get('mean')} |")
                c3[f"{cal}/s{s}/{nm}"] = {"uniform": m, "archived_yearly": jy}
    open(f"{ROOT}/c4/c3_seat_round2_B1.md", "w").write("\n".join(L3) + "\n"); json.dump(c3, open(f"{ROOT}/c4/c3_seat_round2_B1.json", "w"), indent=1)
    print("\n".join(L3)); print("\n".join(Lm)); print(f"C4_DONE rows={out['n_rows']} prod_rows={out['n_rows_prod']} distinct_defs={out['n_distinct_arm_definitions']} distinct_defs_prod={out['n_distinct_arm_definitions_prod']}", flush=True)
if __name__ == "__main__": main()
