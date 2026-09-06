"""crash_phase0.py — PREREG_crash_risk_long_end_2026-09-06 §1 Phase 0: cohort C(t), targets T1/T2/T3, yearly base rates (cohort vs universe).
Cohort at meta anchor i (needs a panel row): members m; (a) fund_ema top 15% = the ceil(0.15·n_finite) members with the highest panel f_fund_ema_v1
(the live fund-leg score); (b) previous replay-book longs = names with w > 0 and |w| ≥ 0.5·capw in the most recent health_check M1_UPIT_prod_s42 book row
strictly before E (W normalised by its L1 = gross_total so |w| is comparable with capw = 2.5/nsel of that row; raw-W variant reported as sensitivity).
Targets from the 5m cache (row E = bar closing at the anchor; target rows E+1.. = accounting window, E-0905-J): R48 = Π(1+r5) rows E+1..E+48 − 1 (≥46 finite
bars else NaN), R144 = Π rows E+1..E+144 − 1 (≥138 finite); T1 = 1[R48 ≤ −10%], T2 = R48 (quantile target), T3 = 1[R144 ≤ −15%].
Outputs: data/phase0.npz (COH, COH_fund, COH_book, COH_book_raw, T1, T2, T3, E_ts, symbols), results/base_rates.json + base_rates.md.
env: ROOT"""
import os, sys, json, time, hashlib
import numpy as np
ROOT = os.environ.get("ROOT", "/workspace/review_scratch/crash_risk"); SELF = hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest()
sys.path.insert(0, "/workspace")
from zload import zload
Z = zload("/workspace/data/dlnative_5m_wide829_f16_ext.npz", allow_pickle=True); CTS = Z["ts"].astype(np.int64); T0 = int(CTS[0]); RET = np.asarray(Z["data"][:, :, 0], np.float32); SYMS = [str(s) for s in Z["symbols"]]; del Z
NW = len(SYMS); T = len(CTS)
MT = np.load("/workspace/data/wide_fea_v2ext_meta.npz", allow_pickle=True); E_ts = MT["E_ts"].astype(np.int64); members = MT["members"]; nA = len(E_ts)
PW = np.load("/workspace/data/wide_panel_4h_v2ext.npz", allow_pickle=True); assert [str(s) for s in PW["symbols"]] == SYMS
pw_row = {int(t): j for j, t in enumerate(PW["ts"].astype(np.int64))}; FE = PW["f_fund_ema_v1"]
ART = "/workspace/review_scratch/health_check/dev_alt/probe_artifacts/w10_ablation_series_M1_UPIT_prod_s42_ccal.npz"
z = np.load(ART, allow_pickle=True); cols = [str(c) for c in z["cols"]]; C = {k: i for i, k in enumerate(cols)}; R = np.asarray(z["d30_n2_c42_rec"], float); W = np.asarray(z["d30_n2_c42_W"], float)
assert [str(s) for s in z["symbols"]] == SYMS
bts = R[:, C["ts"]].astype(np.int64); l1 = np.abs(W).sum(1); WN = W / np.maximum(l1[:, None], 1e-12); CAPW = 2.5 / R[:, C["nsel"]]
Ei = (E_ts - T0) // 300; assert np.all(CTS[Ei] == E_ts)
# targets
fin = np.isfinite(RET); L = np.concatenate([np.zeros((1, NW)), np.cumsum(np.where(fin, np.log1p(np.clip(RET, -0.99, None)), 0.0), 0, dtype=np.float64)]); N = np.concatenate([np.zeros((1, NW), np.int64), np.cumsum(fin, 0)])
def win(a, b, need):
    s = L[Ei + b + 1] - L[Ei + a]; n = N[Ei + b + 1] - N[Ei + a]; return np.where(n >= need, np.expm1(s), np.nan).astype(np.float32)
assert Ei.max() + 144 < T, "12h target window beyond cache"
R48 = win(1, 48, 46); R144 = win(1, 144, 138)
T1 = np.where(np.isfinite(R48), R48 <= -0.10, False); T2 = R48; T3 = np.where(np.isfinite(R144), R144 <= -0.15, False)
# cohort
COH = np.zeros((nA, NW), bool); CF = np.zeros((nA, NW), bool); CB = np.zeros((nA, NW), bool); CBR = np.zeros((nA, NW), bool); MEM = np.zeros((nA, NW), bool)
n_no_panel = 0; n_no_book = 0
for i in range(nA):
    j = pw_row.get(int(E_ts[i])); m = members[i]; MEM[i, m] = True
    if j is None: n_no_panel += 1; continue
    fe = FE[j, m]; ok = np.isfinite(fe)
    if ok.sum() >= 10:
        k = int(np.ceil(0.15 * ok.sum())); top = m[ok][np.argsort(-fe[ok])[:k]]; CF[i, top] = True
    b = np.searchsorted(bts, int(E_ts[i]), side="left") - 1   # most recent book row strictly before E
    if b >= 0:
        CB[i] = (WN[b] > 0) & (WN[b] >= 0.5 * CAPW[b]); CBR[i] = (W[b] > 0) & (W[b] >= 0.5 * CAPW[b])
    else: n_no_book += 1
COH = CF | CB
yrs = np.array([time.gmtime(int(t)).tm_year for t in E_ts])
def rate(mask, X):
    v = X[mask]; v = v[np.isfinite(v)] if X.dtype.kind == "f" else v; return (float(np.mean(v)) if len(v) else float("nan")), int(len(v))
rows = {}
for y in sorted(set(yrs.tolist())):
    r = yrs == y; has = r & np.array([pw_row.get(int(t)) is not None for t in E_ts])
    cm = COH & has[:, None]; um = MEM & has[:, None]; fm = CF & has[:, None]; bm = CB & has[:, None]; brm = CBR & has[:, None]
    fin48 = np.isfinite(T2); fin144 = np.isfinite(R144)
    d = {"n_anchors": int(has.sum()), "cohort_size_mean": round(float(cm.sum(1)[has].mean()), 1), "fund_top15_mean": round(float(fm.sum(1)[has].mean()), 1), "book_longs_mean(normW)": round(float(bm.sum(1)[has].mean()), 1), "book_longs_mean(rawW)": round(float(brm.sum(1)[has].mean()), 1), "members_mean": round(float(um.sum(1)[has].mean()), 1),
         "T1_rate_cohort": round(float(T1[cm & fin48].mean()), 4), "T1_rate_universe": round(float(T1[um & fin48].mean()), 4), "T1_events_cohort": int(T1[cm & fin48].sum()), "T1_events_universe": int(T1[um & fin48].sum()),
         "T3_rate_cohort": round(float(T3[cm & fin144].mean()), 4), "T3_rate_universe": round(float(T3[um & fin144].mean()), 4), "T3_events_cohort": int(T3[cm & fin144].sum()),
         "T2_mean_bps_cohort": round(float(np.nanmean(T2[cm]) * 1e4), 1), "T2_mean_bps_universe": round(float(np.nanmean(T2[um]) * 1e4), 1), "T2_q05_bps_cohort": round(float(np.nanpercentile(T2[cm], 5) * 1e4), 1), "T2_q05_bps_universe": round(float(np.nanpercentile(T2[um], 5) * 1e4), 1),
         "n_rows_cohort": int((cm & fin48).sum())}
    rows[str(y)] = d; print(y, json.dumps(d), flush=True)
allm = COH & np.isfinite(T2); alu = MEM & np.isfinite(T2)
tot = {"T1_rate_cohort": round(float(T1[allm].mean()), 4), "T1_rate_universe": round(float(T1[alu].mean()), 4), "T3_rate_cohort": round(float(T3[COH & np.isfinite(R144)].mean()), 4), "T3_rate_universe": round(float(T3[MEM & np.isfinite(R144)].mean()), 4), "n_rows_cohort": int(allm.sum()), "n_rows_universe": int(alu.sum()), "cohort_overlap_fund_and_book_share": round(float((CF & CB).sum() / max(COH.sum(), 1)), 4)}
res = {"self_sha256": SELF, "artifact": ART, "definitions": {"cohort": "fund_ema top 15% of members ∪ previous M1_UPIT_prod_s42 book longs with w_norm ≥ 0.5·capw (w_norm = W/L1, capw = 2.5/nsel of that book row)", "T1": "Π(1+r5) rows E+1..E+48 − 1 ≤ −0.10 (≥46 finite bars)", "T2": "same 4h return (quantile α .05 target)", "T3": "Π rows E+1..E+144 − 1 ≤ −0.15 (≥138 finite)"}, "n_anchors": int(nA), "anchors_without_panel_row": n_no_panel, "anchors_without_prior_book": n_no_book, "by_year": rows, "all": tot}
json.dump(res, open(f"{ROOT}/results/base_rates.json", "w"), indent=1)
np.savez_compressed(f"{ROOT}/data/phase0.npz", COH=COH, COH_fund=CF, COH_book=CB, COH_book_raw=CBR, MEM=MEM, T1=T1, T2=T2, T3=T3, R144=R144, E_ts=E_ts, symbols=np.array(SYMS), self_sha256=SELF)
md = ["| year | anchors | cohort/anchor (fund top15 + book longs normW / rawW) | T1 rate cohort / universe (events) | T3 rate cohort / universe | T2 mean bps cohort / universe | T2 q05 bps cohort / universe |", "|---|---|---|---|---|---|---|"]
for y, d in rows.items(): md.append(f"| {y} | {d['n_anchors']} | {d['cohort_size_mean']} ({d['fund_top15_mean']} + {d['book_longs_mean(normW)']} / {d['book_longs_mean(rawW)']}) | {d['T1_rate_cohort']:.4f} / {d['T1_rate_universe']:.4f} ({d['T1_events_cohort']}) | {d['T3_rate_cohort']:.4f} / {d['T3_rate_universe']:.4f} | {d['T2_mean_bps_cohort']:+.1f} / {d['T2_mean_bps_universe']:+.1f} | {d['T2_q05_bps_cohort']:+.0f} / {d['T2_q05_bps_universe']:+.0f} |")
md.append(f"| all | {nA} | – | {tot['T1_rate_cohort']:.4f} / {tot['T1_rate_universe']:.4f} | {tot['T3_rate_cohort']:.4f} / {tot['T3_rate_universe']:.4f} | – | – |")
open(f"{ROOT}/results/base_rates.md", "w").write("\n".join(md) + "\n"); print("\n".join(md)); print("PHASE0_DONE", json.dumps(tot), flush=True)
