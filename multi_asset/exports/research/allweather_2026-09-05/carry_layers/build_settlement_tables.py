#!/usr/bin/env python
"""build_settlement_tables.py — carry_layers (PREREG_carry_layers_2026-09-05 §1 D / §2): per-(anchor, name, slot) settlement tables for the dodge layer.
Inputs (read-only): /workspace/fund_aug.json.gz (fapi/v1/fundingRate full history, 827 names, pulled 2026-09-01 by fund_pull_pod.py; all settlement times at :00),
  meta anchors E_ts (health_check dev_alt meta = same anchors as dev), /workspace/data/dlnative_5m_wide829_f16_ext.npz ch 'ret5' (5m simple returns of the bar STARTING at ts, i.e. [ts, ts+5m) — verified below: meta y4 = Σ ret5[E..E+47] exactly).
For each name k and each settlement S with anchor i s.t. E_i < S ≤ E_i + 4h: slot q = (S − E_i)/1h − 1 ∈ {0,1,2,3};
  R[i,k,q] = r_S (oracle, the rate settled at S); P[i,k,q] = r_prev (the name's immediately previous settlement rate — what is known at S−10m);
  DR[i,k,q] = Π(1+ret5) − 1 over the 7 bars starting at S−10m … S+20m (= price move over [S−10m, S+25m)); MISS[i,k,q] = number of non-finite bars among the 7 (missing ⇒ contribute 0).
Output: data/sett_tables.npz (float32/int8, NaN where no settlement) + data/sett_receipt.json. Writes only under carry_layers/data/."""
import numpy as np, json, gzip, time, os, hashlib, zipfile, io
ROOT = "/workspace/review_scratch/allweather_trackC/carry_layers"; FA = "/workspace/fund_aug.json.gz"; F5 = "/workspace/data/dlnative_5m_wide829_f16_ext.npz"
META = "/workspace/review_scratch/health_check/dev/pod_backup_2026-08-21/wide_fea_hist_meta.npz"; PANEL = "/workspace/data/wide_panel_4h_v2ext.npz"
t0 = time.time()
MT = np.load(META, allow_pickle=True); E = MT["E_ts"].astype(np.int64); y4 = MT["y4"]; nA = len(E)
PW = np.load(PANEL, allow_pickle=True); SY = [str(s) for s in PW["symbols"]]; NW = len(SY); kof = {s: k for k, s in enumerate(SY)}
d = json.load(gzip.open(FA, "rt")); R_ = d["rates"]
print(f"fund_aug syms {len(R_)}; panel syms {NW}; missing {[s for s in SY if s not in R_]}", flush=True)
z = zipfile.ZipFile(F5); ts5 = np.load(io.BytesIO(z.read("ts.npy"))).astype(np.int64); sy5 = [str(s) for s in np.load(io.BytesIO(z.read("symbols.npy")), allow_pickle=True)]; ch = [str(c) for c in np.load(io.BytesIO(z.read("ch.npy")), allow_pickle=True)]
assert sy5 == SY and ch[0] == "ret5" and np.all(np.diff(ts5) == 300), (ch, len(sy5))
print("loading 5m data (compressed 5.7 GB) …", flush=True)
D5 = np.load(F5)["data"]; ret5 = D5[:, :, 0].astype(np.float32); del D5; print(f"ret5 {ret5.shape} loaded {time.time()-t0:.0f}s finite {np.isfinite(ret5).mean():.4f}", flush=True)
row5 = {int(t): r for r, t in enumerate(ts5)}
# --- semantics check: meta y4 (dev meta = raw Σ-simple over [E, E+4h)) vs Σ ret5 rows E..E+47 (bar STARTING at ts convention) — the alternative (E+1..E+48) must be worse
chk = []; chk_alt = []
rng = np.random.default_rng(0)
for i in rng.choice(np.arange(500, nA - 100), 400, replace=False):
    r0 = row5.get(int(E[i]))
    if r0 is None: continue
    for k in rng.choice(NW, 3, replace=False):
        if np.isfinite(y4[i, k]) and np.isfinite(ret5[r0 + 1:r0 + 49, k]).all():
            chk.append((float(y4[i, k]), float(ret5[r0 + 1:r0 + 49, k].sum()))); chk_alt.append((float(y4[i, k]), float(ret5[r0:r0 + 48, k].sum())))
chk = np.array(chk); chk_alt = np.array(chk_alt)
err_end = float(np.median(np.abs(chk[:, 0] - chk[:, 1]))); err_start = float(np.median(np.abs(chk_alt[:, 0] - chk_alt[:, 1])))
print(f"ret5 convention check n={len(chk)}: median|y4 − Σret5[E+1..E+48]| = {err_end:.3e} (bar-ending) vs median|y4 − Σret5[E..E+47]| = {err_start:.3e} (bar-starting)", flush=True)
assert err_start < err_end and err_start < 1e-6, "ret5 bar convention unexpected (expected bar-starting: y4 == Σ ret5[E..E+47])"
# --- tables
R = np.full((nA, NW, 4), np.nan, np.float32); P = np.full((nA, NW, 4), np.nan, np.float32); DR = np.full((nA, NW, 4), np.nan, np.float32); MISS = np.full((nA, NW, 4), -1, np.int8)
n_ev = 0; n_out = 0; n_slot_bad = 0; spacing = {}; n_miss_any = 0; n_no5m = 0
E_end = E[-1] + 4 * 3600
for s, rows in R_.items():
    k = kof.get(s)
    if k is None: continue
    t = np.array([r[0] for r in rows], np.int64) // 1000; v = np.array([r[1] for r in rows], np.float64)
    o = np.argsort(t); t = t[o]; v = v[o]
    for n in range(len(t)):
        S = int(t[n]); r = float(v[n]); rp = float(v[n - 1]) if n > 0 else np.nan
        if S <= E[0] or S > E_end: n_out += 1; continue
        i = int(np.searchsorted(E, S, side="left")) - 1   # largest E_i < S
        if i < 0 or i >= nA or not (E[i] < S <= E[i] + 4 * 3600): n_out += 1; continue
        dt = S - E[i]
        if dt % 3600 != 0: n_slot_bad += 1; continue
        q = dt // 3600 - 1
        if not (0 <= q <= 3): n_slot_bad += 1; continue
        R[i, k, q] = r; P[i, k, q] = rp; n_ev += 1
        if n > 0: sp = int((t[n] - t[n - 1]) // 3600); spacing[sp] = spacing.get(sp, 0) + 1
        r5 = row5.get(S)
        if r5 is None or r5 - 2 < 0 or r5 + 4 >= len(ts5): DR[i, k, q] = 0.0; MISS[i, k, q] = 7; n_no5m += 1; continue
        w = ret5[r5 - 2:r5 + 5, k]; ok = np.isfinite(w); m = int((~ok).sum())   # bars starting at S−10m, S−5m, S, S+5m, S+10m, S+15m, S+20m ⇒ [S−10m, S+25m)
        DR[i, k, q] = float(np.prod(1.0 + w[ok]) - 1.0) if ok.any() else 0.0; MISS[i, k, q] = m
        if m: n_miss_any += 1
print(f"events {n_ev} (outside anchor range {n_out}, bad slot {n_slot_bad}); events with ≥1 missing 5m bar {n_miss_any} ({n_miss_any/max(n_ev,1):.4f}); no 5m row {n_no5m}; spacing(h) {dict(sorted(spacing.items(), key=lambda x: -x[1])[:8])} {time.time()-t0:.0f}s", flush=True)
# --- panel consistency: f_fund_now at anchor row = last settled rate ≤ E (checked earlier by hand); here: share of anchors where the panel's f_fund_iv matches the slot count implied by our tables
pts = PW["ts"].astype(np.int64); prow = {int(t): j for j, t in enumerate(pts)}; IV = PW["f_fund_iv"]; FN = PW["f_fund_now"]
agree = []; prev_eq = []
for i in range(0, nA, 7):
    j = prow.get(int(E[i]))
    if j is None: continue
    ns = np.isfinite(R[i]).sum(1)   # settlements in window per name
    iv = IV[j]; okv = np.isfinite(iv) & (iv > 0)
    exp = np.where(iv[okv] <= 4, 4.0 / iv[okv], np.nan)   # 4h names: 1/window; 2h: 2; 1h: 4; 8h: 0 or 1 (skip)
    e_ok = np.isfinite(exp); agree.append((ns[okv][e_ok] == exp[e_ok]).mean() if e_ok.any() else np.nan)
    # prev rule for the FIRST settlement of the window must equal the panel's f_fund_now at E (last settled ≤ E) when that settlement exists
    q0 = np.isfinite(P[i, :, 0]) | np.isfinite(P[i, :, 1]) | np.isfinite(P[i, :, 2]) | np.isfinite(P[i, :, 3])
    for k in np.where(q0)[0][:50]:
        qq = int(np.argmax(np.isfinite(R[i, k]))); prev_eq.append(abs(float(P[i, k, qq]) - float(FN[j, k])) < 1e-12 if np.isfinite(FN[j, k]) else np.nan)
print(f"panel f_fund_iv vs table settlement count agreement (4h/2h/1h names): {np.nanmean(agree):.4f}; prev-rate == panel f_fund_now at E for the first settlement of the window: {np.nanmean(np.array(prev_eq, float)):.4f}", flush=True)
os.makedirs(f"{ROOT}/data", exist_ok=True)
np.savez_compressed(f"{ROOT}/data/sett_tables.npz", R=R, P=P, DR=DR, MISS=MISS, E_ts=E, symbols=np.array(SY))
rec = {"fund_aug": FA, "fund_aug_sha256": hashlib.sha256(open(FA, "rb").read()).hexdigest(), "f5": F5, "meta": META, "n_anchors": int(nA), "n_names": int(NW), "syms_missing_in_fund_aug": [s for s in SY if s not in R_], "events": n_ev, "events_outside_anchor_range": n_out, "bad_slot": n_slot_bad,
       "events_with_missing_5m_bar": n_miss_any, "events_missing_share": round(n_miss_any / max(n_ev, 1), 5), "events_no_5m_row": n_no5m, "spacing_hist_h": {str(k): v for k, v in sorted(spacing.items(), key=lambda x: -x[1])}, "ret5_convention_check": {"n": int(len(chk)), "median_abs_err_bar_ending": err_end, "median_abs_err_bar_starting": err_start},
       "panel_iv_agreement": float(np.nanmean(agree)), "prev_eq_panel_fnow": float(np.nanmean(np.array(prev_eq, float))), "drift_window": "7 five-minute bars starting at S−10m … S+20m = [S−10m, S+25m); ret5 = bar-starting convention (y4 == Σ ret5[E..E+47] verified)", "elapsed_s": round(time.time() - t0, 1)}
rec["sett_tables_sha256"] = hashlib.sha256(open(f"{ROOT}/data/sett_tables.npz", "rb").read()).hexdigest()
json.dump(rec, open(f"{ROOT}/data/sett_receipt.json", "w"), indent=1); print("SETT_RECEIPT " + json.dumps(rec)); print("BUILD_DONE", flush=True)
