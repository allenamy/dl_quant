"""seat_compare.py — 附加: 席位路径 (team-lead addendum 2026-09-05). Read-only; writes results/seat_compare.json and prints.
Inputs: live_rows_aligned.json (the producer's rolling 950-row leg window, every row assigned to its book anchor by align_live_rows.py on the Mac, with the proof that the producer's own w3 is
reproduced at every shadow_log signal anchor), signal_w3.json (the producer's w3 per anchor, 08-16 -> 09-05, read-only extraction), /workspace/shadow_bundle_v3/leg_returns.npz (the v3 package's
own leg rows, 2022-01-08 -> 2026-08-30; NOT what the producer's window holds), and the device artifacts (rec w3_king = the device's dynamic seat; legs_* = the device's seat inputs).
Seat rule everywhere: last 900 rows strictly before the anchor (>=300), shp = max(mean/std, 0) per leg (ddof=0), king/(king+fund) (== 3-leg normalise -> LEGS=101 mask -> renormalise)."""
import numpy as np, json, time
ROOT = "/workspace/review_scratch/health_check"; T4 = 14400; APY = 2190; CUT = 1786478400
def iso(t): return time.strftime("%Y-%m-%d %H:%M", time.gmtime(int(t)))
A = json.load(open(f"{ROOT}/live_rows_aligned.json")); rts = np.array(A["row_ts"], np.int64); ok = rts > 0
LV = {k: np.array(A[k], float)[ok] for k in ("king", "rev24", "fund")}; lts = rts[ok]; o = np.argsort(lts); lts = lts[o]; LV = {k: v[o] for k, v in LV.items()}
SIG = json.load(open(f"{ROOT}/signal_w3.json")); sig = {int(r["anchor_ts"]): r for r in SIG}; sig_ts = sorted(sig)
B = np.load("/workspace/shadow_bundle_v3/leg_returns.npz"); bts = B["ts"].astype(np.int64); BL = {k: B[k].astype(float) for k in ("king", "rev24", "fund")}
def seat2(k, f):
    if len(k) < 300: return np.nan
    r = np.stack([k[-900:], f[-900:]]); shp = np.maximum(r.mean(1) / (r.std(1) + 1e-9), 0.0); return float(shp[0] / shp.sum()) if shp.sum() > 0 else 0.5
def trail(k, f):
    r = np.stack([k[-900:], f[-900:]]); shp = r.mean(1) / (r.std(1) + 1e-9)
    return {"n": int(r.shape[1]), "king_mean_bps": round(float(r[0].mean()), 3), "king_std": round(float(r[0].std()), 2), "king_shp_per_anchor": round(float(shp[0]), 4), "fund_mean_bps": round(float(r[1].mean()), 3), "fund_std": round(float(r[1].std()), 2), "fund_shp_per_anchor": round(float(shp[1]), 4), "seat": round(float(max(shp[0], 0) / (max(shp[0], 0) + max(shp[1], 0))), 4) if max(shp[0], 0) + max(shp[1], 0) > 0 else 0.5}
out = {"alignment": A.get("alignment"), "proof_producer_w3_reproduced": A.get("proof"), "live_rows_used": int(ok.sum()), "live_rows_span": [iso(lts[0]), iso(lts[-1])], "file_sha256": A["file_sha256"]}
ARMS = {"m1": "M1_UPIT_prod_s42_ccal", "m1_s2027": "M1_UPIT_prod_s2027_ccal", "trade": "UPIT_prod_s42_ccal", "members": "MEM_UPIT_prod_s42_ccal", "fixed": "FIX_UPIT_prod_s42_ccal"}
DEV = {}
for nm, tag in ARMS.items():
    Z = np.load(f"{ROOT}/dev_alt/probe_artifacts/w10_ablation_series_{tag}.npz", allow_pickle=True); R = Z["d30_n2_c42_rec"]; ts = R[:, 0].astype(np.int64); w = R[:, 14]
    DEV[nm] = {"ts": ts, "w3": w, "legs": ({"ts": Z["legs_ts"].astype(np.int64), "king": Z["legs_king"].astype(float), "fund": Z["legs_fund"].astype(float)} if "legs_ts" in Z.files else None)}
    yrs = np.array([time.gmtime(int(t)).tm_year for t in ts])
    out.setdefault("device_seat", {})[nm] = {"tag": tag, "w3_king_yearly_mean": {str(y): round(float(w[yrs == y].mean()), 4) for y in (2024, 2025, 2026)}, "w3_king_2024H1_mean": round(float(w[(ts >= 1704067200) & (ts < 1719792000)].mean()), 4), "w3_king_2024H2_mean": round(float(w[(ts >= 1719792000) & (ts < 1735689600)].mean()), 4),
                                             "w3_king_at_cut_2026-08-10_20Z": round(float(w[ts == CUT][0]), 4) if (ts == CUT).any() else None, "w3_king_last_2026-08-30_20Z": round(float(w[-1]), 4)}
# live seat (reconstructed from the producer's own rows) and the producer's printed w3
anchors = list(range(1767225600, int(sig_ts[-1]) + 1, T4))   # 2026-01-01 .. last signal anchor
live_seat = {t: seat2(LV["king"][lts < t], LV["fund"][lts < t]) for t in anchors}
prod_seat = {t: (sig[t]["w3"][0] / (sig[t]["w3"][0] + sig[t]["w3"][2])) for t in sig_ts}
v3_seat = {t: seat2(BL["king"][bts < t], BL["fund"][bts < t]) for t in anchors}
out["live_seat"] = {"first_anchor_with_>=300_rows": iso(min(t for t in anchors if np.isfinite(live_seat[t]))), "at_2026-08-10_20Z": round(live_seat.get(CUT, np.nan), 4), "at_2026-08-30_20Z": round(live_seat.get(int(bts[-1]), np.nan), 4), "at_last_signal_anchor": {"anchor": iso(sig_ts[-1]), "reconstructed": round(live_seat[sig_ts[-1]], 4), "producer_printed": round(prod_seat[sig_ts[-1]], 4), "producer_w3_raw": sig[sig_ts[-1]]["w3"]},
                    "producer_monthly_mean": {}, "v3_bundle_rows_seat_at_2026-08-30_20Z": round(v3_seat.get(int(bts[-1]), np.nan), 4)}
mon = lambda t: time.strftime("%Y-%m", time.gmtime(int(t))); tab = {}
for t in anchors:
    if t < 1772323200: continue
    e = tab.setdefault(mon(t), {})
    for nm, v in (("producer_w3", prod_seat.get(t)), ("live_rows_reconstructed", live_seat[t]), ("v3_bundle_rows", v3_seat[t])):
        if v is not None and np.isfinite(v): e.setdefault(nm, []).append(float(v))
    for nm in DEV:
        k = np.where(DEV[nm]["ts"] == t)[0]
        if len(k): e.setdefault("device_" + nm, []).append(float(DEV[nm]["w3"][k[0]]))
out["monthly_seat"] = {m: {k: round(float(np.mean(v)), 4) for k, v in e.items()} for m, e in tab.items()}; out["monthly_seat_n"] = {m: {k: len(v) for k, v in e.items()} for m, e in tab.items()}
out["live_seat"]["producer_monthly_mean"] = {m: e.get("producer_w3") for m, e in out["monthly_seat"].items()}
# per-leg statistics over common windows
def legstats(k, f): return {"n": int(len(k)), "king_mean_bps": round(float(k.mean()), 3), "king_sharpe_ann": round(float(k.mean() / (k.std() + 1e-9)) * np.sqrt(APY), 3), "fund_mean_bps": round(float(f.mean()), 3), "fund_sharpe_ann": round(float(f.mean() / (f.std() + 1e-9)) * np.sqrt(APY), 3)}
def window(lo, hi):
    res = {}; mL = (lts >= lo) & (lts <= hi); res["live_rows"] = legstats(LV["king"][mL], LV["fund"][mL]); lk, lf = LV["king"][mL], LV["fund"][mL]; lt_ = lts[mL]
    mB = (bts >= lo) & (bts <= hi); res["v3_bundle_rows"] = legstats(BL["king"][mB], BL["fund"][mB])
    for nm in ("m1", "members"):
        g = DEV[nm]["legs"]; mm = (g["ts"] >= lo) & (g["ts"] <= hi); res["device_" + nm] = legstats(g["king"][mm], g["fund"][mm])
        common = np.intersect1d(g["ts"][mm], lt_)
        if len(common) > 30:
            ik = {int(t): i for i, t in enumerate(g["ts"])}; il = {int(t): i for i, t in enumerate(lts)}
            gk = np.array([g["king"][ik[t]] for t in common]); gf = np.array([g["fund"][ik[t]] for t in common]); vk = np.array([LV["king"][il[t]] for t in common]); vf = np.array([LV["fund"][il[t]] for t in common])
            res["device_" + nm]["corr_king_vs_live_rows"] = round(float(np.corrcoef(gk, vk)[0, 1]), 3); res["device_" + nm]["corr_fund_vs_live_rows"] = round(float(np.corrcoef(gf, vf)[0, 1]), 3); res["device_" + nm]["n_common"] = int(len(common))
    return res
out["leg_stats_2026-03-01..08-30"] = window(1772323200, int(bts[-1]))
out["leg_stats_live_rows_full_span"] = window(int(lts[0]), int(lts[-1]))
# trailing-900 decomposition of the seat at the last common anchor (08-30 20Z -> seat used at 08-31 00Z) and at the last live row
t_end = int(bts[-1]) + T4
out["trailing900_at_2026-08-31_00Z"] = {"live_rows": trail(LV["king"][lts < t_end], LV["fund"][lts < t_end]), "v3_bundle_rows": trail(BL["king"][bts < t_end], BL["fund"][bts < t_end])}
for nm in ("m1", "members"):
    g = DEV[nm]["legs"]; mm = g["ts"] < t_end; out["trailing900_at_2026-08-31_00Z"]["device_" + nm] = trail(g["king"][mm], g["fund"][mm])
t_last = int(sig_ts[-1]); out["trailing900_at_last_signal_anchor"] = {"anchor": iso(t_last), "live_rows": trail(LV["king"][lts < t_last], LV["fund"][lts < t_last])}
for k in ("alignment", "proof_producer_w3_reproduced", "live_seat", "device_seat", "monthly_seat", "leg_stats_2026-03-01..08-30", "trailing900_at_2026-08-31_00Z", "trailing900_at_last_signal_anchor"): print(k.upper(), json.dumps(out[k]), flush=True)
json.dump(out, open(f"{ROOT}/results/seat_compare.json", "w"), indent=1); print("SEAT_COMPARE_DONE")
