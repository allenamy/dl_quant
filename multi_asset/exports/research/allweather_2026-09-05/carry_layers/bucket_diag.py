"""bucket_diag.py — carry_layers DIAGNOSTIC (team-lead request 09-05; no replay, no new arm, no judge): per settlement-rate bucket × book position side, 2023→cut,
over ALL (anchor, held name, settlement-in-window) events of the baseline book B0_prod_s42 (weights W = the health_check main arm, bitwise) and the settlement tables
(data/sett_tables.npz: R = settled rate, DR = price move over [S−10m, S+25m)):
  funding paid per event (bps of the position's notional) = sign(w)·r_S·1e4 (+ = the position pays);  price move signed WITH the position = sign(w)·DR·1e4;
  implied per-event EV of the opposite "intensify" overlay (temporarily adding one unit of the same-signed position through the window) = move_with − funding_paid − 7.84 (round trip);
  bucket notional share of gross per anchor = mean over anchors of Σ|w| of the bucket's names (with a settlement in the window) / gross_total.
CI95 = UTC-day-block bootstrap (anchor day), 2000 resamples, seed 20260905. Output results/bucket_diag.{json,md}. Read-only on inputs."""
import numpy as np, json, time, calendar, hashlib
ROOT = "/workspace/review_scratch/allweather_trackC/carry_layers"; NB = 2000; SEED = 20260905
def T(s): return int(calendar.timegm(time.strptime(s, "%Y-%m-%d")))
CUT = T("2026-08-10") + 20 * 3600; LO = T("2023-01-01")
COLS = ["ts", "net", "pnl", "carry", "cost", "gross_total", "gross_member", "gross_sel", "nsel", "nmember", "fires", "leg_king", "leg_rev24", "leg_fund", "w3_king", "w3_rev24", "w3_fund", "turnover", "net_ex", "pnl_ex", "carry_ex", "cost_ex", "netlong"]
p = f"{ROOT}/dev_alt/probe_artifacts/w10_ablation_series_B0_prod_s42.npz"; Z = np.load(p, allow_pickle=True); assert [str(c) for c in Z["cols"]] == COLS
R_ = Z["d30_n2_c42_rec"]; W = Z["d30_n2_c42_W"].astype(np.float64); ts = R_[:, 0].astype(np.int64); gt = R_[:, 5]
ST = np.load(f"{ROOT}/data/sett_tables.npz"); SR = ST["R"].astype(np.float64); SDR = ST["DR"].astype(np.float64); E0 = ST["E_ts"].astype(np.int64); arow = {int(t): i for i, t in enumerate(E0)}
m = (ts >= LO) & (ts < CUT); idx = np.where(m)[0]
ev_w = []; ev_r = []; ev_d = []; ev_day = []; ev_a = []
for n in idx:
    i = arow[int(ts[n])]; w = W[n]; held = np.abs(w) > 1e-12
    if not held.any(): continue
    ks = np.where(held)[0]; Rk = SR[i, ks]; Dk = SDR[i, ks]; ok = np.isfinite(Rk)
    if not ok.any(): continue
    kk, qq = np.where(ok)
    ev_w.append(w[ks[kk]]); ev_r.append(Rk[kk, qq]); ev_d.append(np.nan_to_num(Dk[kk, qq], nan=0.0)); ev_day.append(np.full(len(kk), ts[n] // 86400)); ev_a.append(np.full(len(kk), n))
w = np.concatenate(ev_w); r = np.concatenate(ev_r) * 1e4; d = np.concatenate(ev_d) * 1e4; day = np.concatenate(ev_day); an = np.concatenate(ev_a)
sg = np.sign(w); fund = sg * r; move = sg * d; ev = move - fund - 7.84
def boot(x, days):
    ud, inv = np.unique(days, return_inverse=True); nd = len(ud)
    if nd < 5: return [None, None]
    s1 = np.bincount(inv, x); c = np.bincount(inv).astype(float); rng = np.random.default_rng(SEED); ii = rng.integers(0, nd, size=(NB, nd)); mm = s1[ii].sum(1) / c[ii].sum(1)
    return [round(float(np.percentile(mm, 2.5)), 2), round(float(np.percentile(mm, 97.5)), 2)]
B = [("< −30", -1e9, -30), ("−30..−15", -30, -15), ("−15..−10", -15, -10), ("−10..−6", -10, -6), ("−6..+6 (ref)", -6, 6), ("+6..+10", 6, 10), ("+10..+15", 10, 15), ("+15..+30", 15, 30), ("> +30", 30, 1e9)]
n_anchors = int(m.sum()); out = {"source": {"weights": p, "weights_sha16": hashlib.sha256(open(p, "rb").read()).hexdigest()[:16], "tables": "data/sett_tables.npz", "window": "2023-01-01 → 2026-08-10 20:00Z", "n_anchors": n_anchors, "n_events_all": int(len(w))},
       "definitions": {"funding_paid_bps": "sign(w)·r_S·1e4, + = position pays", "move_with_bps": "sign(w)·(price move over [S−10m,S+25m))·1e4, + = position gains", "intensify_ev_bps": "move_with − funding_paid − 7.84", "notional_share": "mean over anchors of Σ|w| of bucket names with a settlement in the window / gross_total", "ci": "UTC-day-block bootstrap of the event mean, 2000, seed 20260905", "diagnostic_only": True}, "rows": []}
for lab, lo, hi in B:
    for side, sm in (("long", sg > 0), ("short", sg < 0)):
        s = (r >= lo) & (r < hi) & sm
        if s.sum() == 0: out["rows"].append({"bucket": lab, "side": side, "n": 0}); continue
        share = np.bincount(an[s], np.abs(w[s]), minlength=len(ts)); share = float((share[idx] / gt[idx]).mean())
        pay_side = "pays" if ((lo >= 0 and side == "long") or (hi <= 0 and side == "short")) else ("receives" if (lo >= 0 or hi <= 0) else "mixed")
        out["rows"].append({"bucket": lab, "side": side, "role": pay_side, "n": int(s.sum()), "events_per_anchor": round(float(s.sum()) / n_anchors, 3), "funding_paid_mean_bps": round(float(fund[s].mean()), 2), "funding_paid_median_bps": round(float(np.median(fund[s])), 2),
                            "move_with_mean_bps": round(float(move[s].mean()), 2), "move_with_ci95": boot(move[s], day[s]), "move_with_median_bps": round(float(np.median(move[s])), 2),
                            "intensify_ev_mean_bps": round(float(ev[s].mean()), 2), "intensify_ev_ci95": boot(ev[s], day[s]), "notional_share_of_gross_per_anchor": round(share, 5)})
json.dump(out, open(f"{ROOT}/results/bucket_diag.json", "w"), indent=1)
L = []; P = L.append
P(f"## Diagnostic (no arm, no judge): settlement-window economics per settled-rate bucket × book side, 2023→cut, baseline B0_prod_s42 positions × all settlements in window (n events {len(w):,}, {n_anchors} anchors). Units: bps per event of the position's notional; CI95 = UTC-day-block bootstrap.")
P("| bucket (bps/settlement) | side (role) | n (per anchor) | funding paid mean / median | price move WITH position mean [CI95] / median | intensify EV = move − funding − 7.84, mean [CI95] | notional share of gross/anchor |")
P("|---|---|---|---|---|---|---|")
for x in out["rows"]:
    if x["n"] == 0: P(f"| {x['bucket']} | {x['side']} | 0 | | | | |"); continue
    P(f"| {x['bucket']} | {x['side']} ({x['role']}) | {x['n']:,} ({x['events_per_anchor']}) | {x['funding_paid_mean_bps']:+.2f} / {x['funding_paid_median_bps']:+.2f} | {x['move_with_mean_bps']:+.2f} [{x['move_with_ci95'][0]:+.2f},{x['move_with_ci95'][1]:+.2f}] / {x['move_with_median_bps']:+.2f} | {x['intensify_ev_mean_bps']:+.2f} [{x['intensify_ev_ci95'][0]:+.2f},{x['intensify_ev_ci95'][1]:+.2f}] | {x['notional_share_of_gross_per_anchor']:.4f} |")
open(f"{ROOT}/results/bucket_diag.md", "w").write("\n".join(L) + "\n"); print("\n".join(L)); print("BUCKET_DIAG_DONE")
