"""label_verdict.py — PREREG_king_label_alignment_2026-09-06 §4 frozen reading, applied literally to ALT_SUM (primary; ALT_ACC report-only):
 (A) adopt-candidate: both seeds Δ_book(2024->26) point >= -0.02 AND CI95 lower > -0.05; both seeds exec-window IC Δ (2024->26) >= 0; turnover <= +10%.
 (B) reject: any seed Δ_book CI95 upper < 0, OR any seed exec-window IC Δ CI95 upper < 0.
 (C) UNDECIDED: otherwise.
Also: yearly Δ_book, turnover change, seat trajectory (w3_king / w3_fund yearly means and at the last anchor <= 2026-08-10 20:00Z) from the LA_* artifacts.
Inputs: label_alignment/results/la_paired_<ARM>_s<seed>.json, label_eval.json, rider/dev_alt/probe_artifacts/w10_ablation_series_LA_*.npz."""
import os, json, time, calendar, hashlib
import numpy as np
ROOT = "/workspace/review_scratch/allweather_trackA"; L = f"{ROOT}/label_alignment"; SELF = hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest()
COLS = ["ts", "net", "pnl", "carry", "cost", "gross_total", "gross_member", "gross_sel", "nsel", "nmember", "fires", "leg_king", "leg_rev24", "leg_fund", "w3_king", "w3_rev24", "w3_fund", "turnover", "net_ex", "pnl_ex", "carry_ex", "cost_ex", "netlong"]
C = {k: i for i, k in enumerate(COLS)}; CUT = calendar.timegm(time.strptime("2026-08-10", "%Y-%m-%d")) + 20 * 3600
EV = json.load(open(f"{L}/results/label_eval.json"))
def seats(tag):
    z = np.load(f"{ROOT}/rider/dev_alt/probe_artifacts/w10_ablation_series_{tag}.npz", allow_pickle=True); R = np.asarray(z["d30_n2_c42_rec"], float); ts = R[:, C["ts"]].astype(np.int64)
    yrs = np.array([time.gmtime(int(t)).tm_year for t in ts]); out = {}
    for y in (2024, 2025, 2026):
        m = yrs == y; out[str(y)] = {"w3_king_mean": round(float(R[m, C["w3_king"]].mean()), 4), "w3_fund_mean": round(float(R[m, C["w3_fund"]].mean()), 4), "turnover_per_gross_mean": round(float((R[m, C["turnover"]] / R[m, C["gross_total"]]).mean()), 5)}
    i = np.where(ts <= CUT)[0][-1]; out["at_cut_2026-08-10_20Z"] = {"ts": time.strftime("%F %H:%M", time.gmtime(int(ts[i]))), "w3_king": round(float(R[i, C["w3_king"]]), 4), "w3_rev24": round(float(R[i, C["w3_rev24"]]), 4), "w3_fund": round(float(R[i, C["w3_fund"]]), 4)}
    return out
res = {"self_sha256": SELF, "rule": {"A": "both seeds Δ_book(2024->26) >= -0.02 AND CI95 lower > -0.05; both seeds exec-window IC Δ >= 0; turnover <= +10%", "B": "any seed Δ_book CI95 upper < 0 OR any seed exec-window IC Δ CI95 upper < 0", "C": "otherwise"}, "arms": {}}
for arm in ("ALT_SUM", "ALT_ACC"):
    a = {"seeds": {}}
    for s in (42, 2027):
        P = json.load(open(f"{L}/results/la_paired_{arm}_s{s}.json")); w = P["windows"]["2024->26"]
        e = EV["delta_vs_BASE"][f"{arm}_s{s}"]["exec25_prod"]["2024->26"]
        a["seeds"][str(s)] = {"delta_book_2024_26": w["delta_mean"], "ci95": w["delta_ci95"], "turnover_change": w["turnover_change"], "base_mean": w["base_mean_bps_anchor_per_gross"], "new_mean": w["new_mean"], "base_sharpe": w["base_sharpe"], "new_sharpe": w["new_sharpe"],
                             "yearly_delta": {y: P["windows"][y]["delta_mean"] for y in ("2024", "2025", "2026->cut") if y in P["windows"]}, "yearly_ci": {y: P["windows"][y]["delta_ci95"] for y in ("2024", "2025", "2026->cut") if y in P["windows"]},
                             "exec_ic_delta_2024_26": e["mean"], "exec_ic_delta_ci95": e["ci95"], "exec_ic_delta_by_year": {y: EV["delta_vs_BASE"][f"{arm}_s{s}"]["exec25_prod"][y]["mean"] for y in ("2024", "2025", "2026")},
                             "seats_BASE": seats(f"LA_BASE_s{s}"), "seats_ARM": seats(f"LA_{arm}_s{s}")}
    S = a["seeds"]
    condA = all(S[s]["delta_book_2024_26"] >= -0.02 and S[s]["ci95"][0] > -0.05 and S[s]["exec_ic_delta_2024_26"] >= 0 and S[s]["turnover_change"] <= 0.10 for s in S)
    condB = any(S[s]["ci95"][1] < 0 or S[s]["exec_ic_delta_ci95"][1] < 0 for s in S)
    a["reading"] = "A_adopt_candidate" if condA else ("B_reject" if condB else "C_UNDECIDED"); a["condA"] = bool(condA); a["condB"] = bool(condB); a["role"] = "primary" if arm == "ALT_SUM" else "report-only"
    res["arms"][arm] = a
    for s in S: print(f"[{arm} s{s}] Δ_book 2024->26 {S[s]['delta_book_2024_26']:+.4f} CI {S[s]['ci95']} turnover {S[s]['turnover_change']:+.1%} | exec IC Δ {S[s]['exec_ic_delta_2024_26']:+.4f} CI {S[s]['exec_ic_delta_ci95']} | yearly Δ_book {S[s]['yearly_delta']} | seat king at cut BASE {S[s]['seats_BASE']['at_cut_2026-08-10_20Z']['w3_king']} ARM {S[s]['seats_ARM']['at_cut_2026-08-10_20Z']['w3_king']}", flush=True)
    print(f"{arm} ({a['role']}): condA {condA} condB {condB} -> {a['reading']}", flush=True)
json.dump(res, open(f"{L}/results/label_verdict.json", "w"), indent=1); print("LABEL_VERDICT_DONE", flush=True)
