"""build_umask.py — universe masks + BTC realised-vol series for the live-form health check (PREREG_live_form_health_check_2026-09-05 §0 row 1; §2 slices).
Read-only inputs: 5m cache /workspace/data/dlnative_5m_wide829_f16_ext.npz (channels per pod_fea_ext.py CHN: ret5, range, cpos, log_qv, log_cnt, log_avgsz, tbf;
log_qv = log1p of the 5m quote volume = the channel the meta builder averages into qvk), panel /workspace/data/wide_panel_4h_v2ext.npz (ts grid + the 829 symbols the
device asserts against), meta /workspace/data/wide_fea_v2ext_meta.npz (E_ts, qvk, y4 for the tradeable-count diagnostic), syms450.txt (449 live names, copied from ~/wide_shadow/syms450.txt).
U-PIT   : at the first panel anchor of each calendar month, symbols ranked by trailing-30-day quote volume = Σ expm1(log_qv) over the 8640 5m bars strictly before the anchor,
          among symbols listed >= 30 days (listing = first 5m bar with finite ret5) with positive volume; top 449; the mask is held fixed for every anchor of that month. Strictly causal.
U-FROZEN: the 449 names of syms450.txt at every anchor (today's list projected back; look-ahead selection => upper bound only).
Outputs (masks/): umask_UPIT.npz, umask_UFROZEN.npz {ts=panel ts, symbols, mask bool [n_ts x 829]} (device format, cf. pod_umask_build.py); btc_rv30.npz {ts, rv30_ann_pct, nbars};
          listing.json; mask_summary.json. Prints yearly mean allowed / tradeable counts per mask (tradeable = mask & qv4h>=2.5e5 & finite y4 on the meta grid) and the overlap."""
import numpy as np, json, time
t0 = time.time()
ROOT = "/workspace/review_scratch/health_check"
CACHE = "/workspace/data/dlnative_5m_wide829_f16_ext.npz"; PANEL = "/workspace/data/wide_panel_4h_v2ext.npz"; META = "/workspace/data/wide_fea_v2ext_meta.npz"
Z = np.load(CACHE, allow_pickle=True)
CTS = Z["ts"].astype(np.int64); CSYM = [str(s) for s in Z["symbols"]]; CH = [str(c) for c in Z["ch"]]
print("cache channels", CH, "n5m", len(CTS), "range", time.strftime("%Y-%m-%d %H:%M", time.gmtime(int(CTS[0]))), time.strftime("%Y-%m-%d %H:%M", time.gmtime(int(CTS[-1]))), "syms", len(CSYM), flush=True)
iq = CH.index("log_qv"); ir = CH.index("ret5")
D = Z["data"]; print("data", D.shape, D.dtype, f"loaded {time.time()-t0:.0f}s", flush=True)
P = np.load(PANEL, allow_pickle=True); PTS = P["ts"].astype(np.int64); PSYM = [str(s) for s in P["symbols"]]
assert PSYM == CSYM, "panel/cache symbol order differs"
NW = len(PSYM); col = {s: j for j, s in enumerate(PSYM)}
ret5 = D[:, :, ir].astype(np.float32); fin = np.isfinite(ret5)
has = fin.any(0); first_idx = np.argmax(fin, 0)
_lq_fin = np.isfinite(D[:, :, iq]); _fi_lq0 = np.argmax(_lq_fin, 0)
# listing bar = first finite log_qv bar (= one bar before the first finite ret5, which needs a prior close); the cache's bar 0 (2022-01-01 00:00) is all-NaN,
# so names with data within the first 3 bars were listed at or before the cache start ⇒ listing = cache start (2022-01-01 00:00)
first_ts = np.where(has, np.where(_fi_lq0 <= 2, CTS[0], CTS[np.clip(_fi_lq0, 0, len(CTS) - 1)]), 2**62)
lq = D[:, :, iq].astype(np.float32); lq_fin_first = np.where(np.isfinite(lq).any(0), CTS[np.clip(np.argmax(np.isfinite(lq), 0), 0, len(CTS) - 1)], 2**62)
_fi_lq = np.argmax(np.isfinite(lq), 0); _off = (_fi_lq - first_idx)[has]; _u, _c = np.unique(_off, return_counts=True); _o = np.argsort(-_c)[:6]
print("listing check: (first finite log_qv bar - first finite ret5 bar) top counts:", {int(_u[k]): int(_c[k]) for k in _o}, "| log_qv 2 bars before first ret5 for a 2025 listing:", [float(lq[max(first_idx[j] - 2, 0), j]) for j in np.where(has & (first_ts > 1735689600))[0][:3]], flush=True)
qv5 = np.expm1(np.clip(np.nan_to_num(lq, nan=0.0), 0, 30)).astype(np.float64); del lq
cs = np.zeros((len(CTS) + 1, NW), np.float64); np.cumsum(qv5, axis=0, out=cs[1:]); del qv5
print(f"cumsum done {time.time()-t0:.0f}s", flush=True)
BARS30 = 30 * 288
pos = {int(t): k for k, t in enumerate(CTS)}
mstart = {}
for j, t in enumerate(PTS):
    tm = time.gmtime(int(t)); key = (tm.tm_year, tm.tm_mon)
    if key not in mstart: mstart[key] = j
UPIT = np.zeros((len(PTS), NW), bool); rows = []; keys = sorted(mstart)
for n, key in enumerate(keys):
    j0 = mstart[key]; j1 = mstart[keys[n + 1]] if n + 1 < len(keys) else len(PTS)
    t = int(PTS[j0]); k = pos[t]; lo = max(0, k - BARS30)
    vol30 = cs[k] - cs[lo]
    age = (t - first_ts) / 86400.0
    elig = has & (age >= 30) & (vol30 > 0)
    order = np.argsort(-vol30); order = order[elig[order]]; top = order[:449]
    m = np.zeros(NW, bool); m[top] = True; UPIT[j0:j1] = m
    rows.append({"month": f"{key[0]}-{key[1]:02d}", "anchor": time.strftime("%Y-%m-%d %H:%M", time.gmtime(t)), "bars_used": int(k - lo), "n_listed": int((first_ts <= t).sum()),
                 "n_elig": int(elig.sum()), "n_top": int(len(top)), "vol30_449th_usd": (float(vol30[top[-1]]) if len(top) else None), "n_anchors": int(j1 - j0)})
print(f"U-PIT months {len(keys)}: first {rows[0]} last {rows[-1]}", flush=True)
S450 = [l.strip() for l in open(f"{ROOT}/syms450.txt") if l.strip()]
miss = [s for s in S450 if s not in col]; print("syms450 n", len(S450), "missing in panel", miss, flush=True)
fz = np.zeros(NW, bool); fz[[col[s] for s in S450 if s in col]] = True
UFRZ = np.tile(fz, (len(PTS), 1))
np.savez_compressed(f"{ROOT}/masks/umask_UPIT.npz", ts=PTS, symbols=np.array(PSYM), mask=UPIT)
np.savez_compressed(f"{ROOT}/masks/umask_UFROZEN.npz", ts=PTS, symbols=np.array(PSYM), mask=UFRZ)
# BTC 30-day realised vol at each panel anchor (5m simple returns, bars strictly before the anchor; annualised, %)
ib = col["BTCUSDT"]; r = np.where(fin[:, ib], ret5[:, ib].astype(np.float64), 0.0); f = fin[:, ib].astype(np.int64)
c1 = np.concatenate([[0.0], np.cumsum(r)]); c2 = np.concatenate([[0.0], np.cumsum(r * r)]); cn = np.concatenate([[0], np.cumsum(f)])
rv = np.full(len(PTS), np.nan); nb = np.zeros(len(PTS), int)
for j, t in enumerate(PTS):
    k = pos.get(int(t))
    if k is None: continue
    lo = max(0, k - BARS30); n = int(cn[k] - cn[lo]); nb[j] = n
    if n >= 0.9 * BARS30:
        mu = (c1[k] - c1[lo]) / n; v = (c2[k] - c2[lo]) / n - mu * mu; rv[j] = np.sqrt(max(v, 0.0)) * np.sqrt(288 * 365) * 100
np.savez_compressed(f"{ROOT}/masks/btc_rv30.npz", ts=PTS, rv30_ann_pct=rv, nbars=nb)
# diagnostics on the meta anchor grid (= the device's evaluation grid)
M = np.load(META, allow_pickle=True); E = M["E_ts"].astype(np.int64); qvk = M["qvk"]; y4 = M["y4"]
prow = {int(t): j for j, t in enumerate(PTS)}
qv4h = np.expm1(np.clip(np.nan_to_num(qvk, nan=0.0), 0, 30)) * 48
liq = (qv4h >= 2.5e5) & np.isfinite(y4)
yrs = np.array([time.gmtime(int(t)).tm_year for t in E]); YS = sorted(set(yrs.tolist()))
JJ = np.array([prow.get(int(t), -1) for t in E]); okrow = JJ >= 0
summ = {"masks": {}, "overlap": {}, "months": rows}
for nm, MK in (("UPIT", UPIT), ("UFROZEN", UFRZ)):
    allowed = np.full(len(E), np.nan); trad = np.full(len(E), np.nan)
    allowed[okrow] = MK[JJ[okrow]].sum(1); trad[okrow] = (MK[JJ[okrow]] & liq[okrow]).sum(1)
    summ["masks"][nm] = {str(y): {"allowed_mean": round(float(np.nanmean(allowed[yrs == y])), 1), "tradeable_mean": round(float(np.nanmean(trad[yrs == y])), 1), "n_anchors": int(okrow[yrs == y].sum())} for y in YS}
    print(nm, json.dumps(summ["masks"][nm]), flush=True)
liq_all = np.full(len(E), np.nan); liq_all[okrow] = liq[okrow].sum(1)
summ["masks"]["NO_MASK_829"] = {str(y): {"tradeable_mean": round(float(np.nanmean(liq_all[yrs == y])), 1)} for y in YS}
both = np.full(len(E), np.nan); both_tr = np.full(len(E), np.nan)
both[okrow] = (UPIT[JJ[okrow]] & UFRZ[JJ[okrow]]).sum(1); both_tr[okrow] = (UPIT[JJ[okrow]] & UFRZ[JJ[okrow]] & liq[okrow]).sum(1)
summ["overlap"] = {str(y): {"allowed_both_mean": round(float(np.nanmean(both[yrs == y])), 1), "allowed_both_over_449": round(float(np.nanmean(both[yrs == y])) / 449, 3), "tradeable_both_mean": round(float(np.nanmean(both_tr[yrs == y])), 1)} for y in YS}
print("OVERLAP", json.dumps(summ["overlap"]), flush=True)
pyrs = np.array([time.gmtime(int(t)).tm_year for t in PTS])
summ["btc_rv30_yearly_mean_pct"] = {str(y): round(float(np.nanmean(rv[pyrs == y])), 1) for y in sorted(set(pyrs.tolist()))}
ly = np.array([time.gmtime(int(t)).tm_year for t in first_ts[has]]); summ["listing_by_year"] = {str(int(y)): int(n) for y, n in zip(*np.unique(ly, return_counts=True))}
summ["definitions"] = {"UPIT": "first panel anchor of each calendar month: top-449 by sum of expm1(log_qv) over the 8640 5m bars strictly before the anchor, among names listed >=30d (listing = first finite log_qv bar; names with data within the first 3 cache bars = listed at cache start 2022-01-01) with vol>0; held for the month",
                       "UFROZEN": "syms450.txt (449) at every anchor", "tradeable": "mask & qv4h>=2.5e5 & finite y4 on the meta grid (qv4h = expm1(clip(qvk,0,30))*48 as in the device)",
                       "btc_rv30": "std of BTCUSDT 5m simple returns over the 8640 bars strictly before the anchor (>=90% finite), * sqrt(288*365) * 100"}
json.dump(summ, open(f"{ROOT}/masks/mask_summary.json", "w"), indent=1)
json.dump({s: (time.strftime("%Y-%m-%d", time.gmtime(int(first_ts[j]))) if has[j] else None) for j, s in enumerate(PSYM)}, open(f"{ROOT}/masks/listing.json", "w"), indent=0)
print("BTC rv30 yearly mean %", summ["btc_rv30_yearly_mean_pct"]); print("listing by year", summ["listing_by_year"])
print(f"UMASK_DONE {time.time()-t0:.0f}s", flush=True)
