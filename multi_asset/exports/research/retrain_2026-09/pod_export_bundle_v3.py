"""影子 bundle v3 导出 @pod — 2026-09 首次月度重训(RUNBOOK_monthly_retrain_2026-09 步骤3-4)。
基底 = runpod_scripts/workspace_mirror/pod_export_shadow_bundle.py(08-16 在役代装置)逐字, 记档修正:
  Δ1 OUT/shadow_bundle_v3 + tar shadow_bundle_v3.tar.gz(RUNBOOK 不覆盖铁律; arcname 不变=本机换装即插);
  Δ2 基线改读 /workspace/slow_scorer_v3base.json: 2024/2025=scorer装置记录(mirror slow_scorer.json, git),
     2026=在役 bundle provenance.pinned_ic2026=0.0571(同装置同口径 08-16);
  Δ3 新增门②(RUNBOOK): 2024/2025 折 IC vs 上一代 |Δ|<=0.004, 红即停;
  Δ4 symbols_live 改读 live_pins.json 钉死 450(原 glob funding 目录数; 09-01 目录已 829,
     原样跑=宇宙刷新静默搭车, 违 PREREG_retrain_addendum §B 分离部署裁定);
  Δ5 keep 列断言 == 在役 keep_names 逐位(布 booster 特征序一致性);
  Δ6 ledger/ema_state 循环限定钉死 450。
门③(ic26 ±0.006)与守卫带(2.27..2.57)沿用原装置硬编码, 不动。
用法: python3 pod_export_bundle_v3.py
"""
import os, io, csv, json, time, glob, gzip, zipfile, hashlib, tarfile
import numpy as np
import sys; sys.path.insert(0, "/workspace")
from scipy.stats import rankdata, spearmanr
from zload import zload

OUT = "/workspace/shadow_bundle_v3"
os.makedirs(OUT, exist_ok=True)
PINS = json.load(open("/workspace/live_pins.json"))          # Δ4/Δ5
BASE = json.load(open("/workspace/slow_scorer_v3base.json"))  # Δ2

# ── ① 重训并保存 booster ──
FEA = np.load("/workspace/data/wide_fea_v2ext.npy")
MT = np.load("/workspace/data/wide_fea_v2ext_meta.npz", allow_pickle=True)
E_ts = MT["E_ts"].astype(np.int64); members = MT["members"]; y4 = MT["y4"]; qvk = MT["qvk"]
names = [str(n) for n in MT["names"]]
yrs = np.array([time.gmtime(int(t)).tm_year for t in E_ts])
nA = len(E_ts); NW = 829
keep = [k for k, nm in enumerate(names) if not (nm.startswith("ret5_sum_48") or nm.startswith("ret5_sum_288"))]
assert [names[k] for k in keep] == PINS["keep_names"], "keep_names 与在役不一致"  # Δ5
def sp(a, b):
    ok = np.isfinite(a) & np.isfinite(b)
    if ok.sum() < 30: return np.nan
    r = spearmanr(a[ok], b[ok]); return r.correlation if hasattr(r, "correlation") else r[0]
rows_X, rows_y, rows_a = [], [], []
for i in range(nA):
    m = members[i]
    yv = y4[i, m]; ok = np.isfinite(yv)
    if ok.sum() < 50: continue
    rr = rankdata(yv[ok]) / max(ok.sum() - 1, 1) - 0.5
    rows_X.append(FEA[i, m[ok]][:, keep].astype(np.float32))
    rows_y.append(rr.astype(np.float32)); rows_a.append(np.full(ok.sum(), i, np.int32))
X = np.concatenate(rows_X); Y = np.concatenate(rows_y); A = np.concatenate(rows_a)
YRA = yrs[A]
import lightgbm as lgb
tr = YRA < 2026; te = YRA == 2026
gbm = lgb.LGBMRegressor(n_estimators=400, learning_rate=0.05, num_leaves=63,
                        subsample=0.8, colsample_bytree=0.8, n_jobs=100, verbose=-1).fit(X[tr], Y[tr])
gbm.booster_.save_model(f"{OUT}/slow2026.txt")
# 钉死预测: 2026 折用本 booster; 2024/2025 折照旧训练(仅历史腿收益用, 不进影子)
PRED = np.full((nA, NW), np.nan, np.float32)
fold_ic = {}
for YV in (2024, 2025):
    tr_ = YRA < YV; te_ = YRA == YV
    g2 = lgb.LGBMRegressor(n_estimators=400, learning_rate=0.05, num_leaves=63,
                           subsample=0.8, colsample_bytree=0.8, n_jobs=100, verbose=-1).fit(X[tr_], Y[tr_])
    pv = g2.predict(X[te_]); a_te = A[te_]
    ics_ = []
    for a in np.unique(a_te):
        sel = a_te == a; m = members[a]; okm = np.isfinite(y4[a, m])
        PRED[a, m[okm]] = pv[sel]
        ics_.append(sp(pv[sel], y4[a, m[okm]]))
    fold_ic[YV] = float(np.nanmean(ics_))
    d = fold_ic[YV] - float(BASE["ic"][str(YV)])
    print(f"fold {YV} IC {fold_ic[YV]:+.4f} (base {float(BASE['ic'][str(YV)]):+.4f} Δ{d:+.4f})", flush=True)
    if abs(d) > 0.004:  # Δ3 门②
        print(f"BUNDLE_FAIL fold_gate_{YV}", flush=True); sys.exit(3)
pv = gbm.predict(X[te]); a_te = A[te]
ics = []
for a in np.unique(a_te):
    sel = a_te == a; m = members[a]; okm = np.isfinite(y4[a, m])
    PRED[a, m[okm]] = pv[sel]
    ics.append(sp(pv[sel], y4[a, m[okm]]))
ic26 = float(np.nanmean(ics))
orig26 = float(BASE["ic"]["2026"])  # Δ2
print(f"pinned booster 2026 IC {ic26:+.4f} (orig {orig26:+.4f})", flush=True)
if abs(ic26 - orig26) > 0.006:
    print("BUNDLE_FAIL ic_gate", flush=True); sys.exit(3)
np.save(f"{OUT}/slow_pred_pinned.npy", PRED)

# ── ② v1iv 基线重跑(钉死预测) + 逐锚信号导出(08-01 起, 供 A2 平价) ──
PW = np.load("/workspace/data/wide_panel_4h_v2ext.npz", allow_pickle=True)
pw_row = {int(t): j for j, t in enumerate(PW["ts"].astype(np.int64))}
FN = PW["f_fund_now"]; IV = PW["f_fund_iv"]; R24 = PW["f_rev_24h"]; FE = PW["f_fund_ema_v1"]
def xz(v):
    ok = np.isfinite(v); out = np.full(len(v), np.nan)
    n = ok.sum()
    if n >= 10: out[ok] = rankdata(v[ok]) / max(n - 1, 1) - 0.5
    return out
COST_B = [(-0.25, 5.0, 0.85), (0.5, 6.0, 0.75), (2.0, 8.0, 0.55)]
def tier_of(q):
    t = np.full(len(q), 2, np.int8); t[q >= 1e6] = 1; t[q >= 5e6] = 0
    return t
LR = {leg: [] for leg in ("king", "rev24", "fund")}
idx = []
for i in range(nA):
    j = pw_row.get(int(E_ts[i]))
    if j is None: continue
    sc = {"king": PRED[i, members[i]], "rev24": -R24[j, members[i]], "fund": FE[j, members[i]]}
    m = members[i]
    ok = np.isfinite(y4[i, m])
    for leg in LR:
        z = np.nan_to_num(xz(sc[leg]))
        z = np.where(ok, z, 0.0); z -= z[ok].mean() if ok.sum() else 0
        g = np.abs(z).sum()
        LR[leg].append(float((z / g * np.nan_to_num(y4[i, m], nan=0.0)).sum() * 1e4) if g > 1e-9 else 0.0)
    idx.append(i)
LRa = {k: np.array(v) for k, v in LR.items()}
pos = {int(i): p for p, i in enumerate(idx)}
def msharpe_w(i_pos):
    look = 900
    if i_pos < look: return (1/3, 1/3, 1/3)
    sl = slice(i_pos - look, i_pos)
    r = np.stack([LRa["king"][sl], LRa["rev24"][sl], LRa["fund"][sl]])
    shp = r.mean(1) / (r.std(1) + 1e-9); shp = np.maximum(shp, 0.0)
    return tuple(shp / shp.sum() if shp.sum() > 0 else np.array([1/3]*3))
H = np.zeros(NW, np.float64)
rec = []; sig_export = {}
for i in range(nA):
    j = pw_row.get(int(E_ts[i]))
    if j is None: continue
    m = members[i]
    sc = {"king": PRED[i, m], "rev24": -R24[j, m], "fund": FE[j, m]}
    wk, wr, wf = msharpe_w(pos.get(int(i), 0))
    z = wk * np.nan_to_num(xz(sc["king"])) + wr * np.nan_to_num(xz(sc["rev24"])) + wf * np.nan_to_num(xz(sc["fund"]))
    ok = np.isfinite(y4[i, m])
    qv4h = np.expm1(np.clip(qvk[i, m], 0, 30)) * 48
    sel = ok & (qv4h >= 2.5e5)
    if sel.sum() < 80: continue
    w = np.where(sel, z, 0.0); w -= w[sel].mean()
    g = np.abs(w).sum()
    if g < 1e-9: continue
    w /= g
    capw = 2.5 / max(sel.sum(), 1)
    w = np.clip(w, -capw, capw)
    g2_ = np.abs(w).sum()
    if g2_ > 1e-9: w /= g2_
    tgt = np.zeros(NW); tgt[m] = w
    sm = H + 0.1 * (tgt - H)
    trade = sm - H
    sm = np.where(np.abs(trade) < 2.5e-4, H, sm)
    trade = sm - H
    qvf = np.expm1(np.clip(qvk[i, m], 0, 30)) * 48
    trm = tier_of(qvf); tabs = np.abs(trade[m])
    cb = sum(tabs[trm == tt].sum() * (fr * mk + (1 - fr) * tk) for tt, (mk, tk, fr) in enumerate(COST_B))
    yv = np.nan_to_num(y4[i, m], nan=0.0)
    fnow = np.nan_to_num(FN[j, m], nan=0.0)
    ivv = IV[j, m]; ivv = np.where(np.isfinite(ivv) & (ivv > 0), ivv, 8.0)
    car = (sm[m] * fnow * (4.0 / ivv)).sum() * 1e4
    net = float((sm[m] * yv).sum() * 1e4 - car - cb)
    rec.append((int(E_ts[i]), net))
    if int(E_ts[i]) >= 1785542400:  # 2026-08-01
        sig_export[str(int(E_ts[i]))] = {"w": {str(int(mm)): round(float(sm[mm]), 8) for mm in np.where(np.abs(sm) > 1e-9)[0]},
                                         "net_bps": round(net, 3)}
    H = sm
arr = np.array([n for t, n in rec if time.gmtime(t).tm_year >= 2024])
sh = float(arr.mean() / (arr.std() + 1e-12) * np.sqrt(6 * 365))
print(f"pinned v1iv full b: 净{arr.mean():.3f} 夏普{sh:.2f}", flush=True)
if not (2.27 <= sh <= 2.57):
    print("BUNDLE_FAIL baseline_guard", flush=True); sys.exit(3)
json.dump(sig_export, open(f"{OUT}/parity_signals_aug.json", "w"))
np.savez_compressed(f"{OUT}/leg_returns.npz", ts=E_ts[np.array(idx)], **LRa)

# ── ③ 缓存尾 + funding 账本 + EMA 状态 ──
Z = zload("/workspace/data/dlnative_5m_wide829_f16_ext.npz", allow_pickle=True)
CTS = Z["ts"].astype(np.int64); CD = Z["data"]; syms = [str(s) for s in Z["symbols"]]
TAIL = 11520  # 40d
np.savez_compressed(f"{OUT}/cache_tail_40d.npz", ts=CTS[-TAIL:], symbols=np.array(syms),
                    data=CD[-TAIL:].astype(np.float16))
AUG = json.loads(gzip.open("/workspace/fund_aug.json.gz", "rt").read())
AUG_IV = {k: float(v) for k, v in (AUG.get("intervals") or {}).items() if v}
HL = 3 * 86400.0
ALLOWED = np.array([1.0, 2.0, 4.0, 6.0, 8.0])
ledger = {}; ema_state = {}
live450 = list(PINS["symbols_live"])  # Δ4/Δ6(原: glob funding 目录)
for s in live450:
    rows = []
    for zp in sorted(glob.glob(f"/workspace/wide_multisrc/funding/{s}/*.zip")):
        try:
            zf = zipfile.ZipFile(zp)
            with zf.open(zf.namelist()[0]) as fh:
                rd = csv.reader(io.TextIOWrapper(fh))
                for row in rd:
                    if not row or not row[0].strip().isdigit() and "time" in row[0].lower(): continue
                    try:
                        ts_ = int(row[0]); rate = float(row[-1]) if abs(float(row[-1])) < 0.2 else float(row[1])
                        iv = np.nan
                        if len(row) >= 3:
                            try:
                                cand = float(row[1])
                                if 1 <= cand <= 24 and abs(cand - round(cand)) < 1e-9 and abs(float(row[-1])) < 0.2: iv = cand
                            except Exception: pass
                        rows.append((ts_ // 1000, rate, iv))
                    except Exception: continue
        except Exception: continue
    for t_ms, rate in (AUG.get("rates") or {}).get(s, []):
        rows.append((int(t_ms) // 1000, float(rate), AUG_IV.get(s, np.nan)))
    if not rows: continue
    rows.sort()
    ded = {}
    for t_, r_, i_ in rows:
        if t_ not in ded or np.isfinite(i_): ded[t_] = (r_, i_)
    ft = sorted(ded)
    dv_prev = None; acc = None; prev_t = None
    tail_rows = []
    for k, t_ in enumerate(ft):
        r_, i_ = ded[t_]
        if not np.isfinite(i_):
            i_ = (t_ - ft[k-1]) / 3600.0 if k else 8.0
            i_ = float(ALLOWED[np.argmin(np.abs(ALLOWED - (i_ if 0 < i_ <= 24 else 8.0)))])
        rn = r_ * (8.0 / i_)
        if acc is None: acc = rn
        else:
            a = 1 - 0.5 ** (max(t_ - prev_t, 1) / HL)
            acc = acc + a * (rn - acc)
        prev_t = t_
        if t_ >= ft[-1] - 40 * 86400: tail_rows.append((t_, r_, i_))
    ledger[s] = tail_rows
    ema_state[s] = {"acc": float(acc), "last_ts": int(prev_t)}
with open(f"{OUT}/funding_ledger_seed.json", "w") as f:
    json.dump(ledger, f)
json.dump(ema_state, open(f"{OUT}/fund_ema_v1_state.json", "w"), indent=0)
json.dump({"symbols_panel": syms, "symbols_live": live450,
           "keep_idx": keep, "keep_names": [names[k] for k in keep],
           "params": {"NTOP": 400, "cov_min": 0.95, "vol_min": 1e-4, "qv4h_min": 2.5e5,
                      "cap_mult": 2.5, "alpha": 0.1, "band": 2.5e-4, "msharpe_look": 900,
                      "fund_caliber": "v1 normfix HL3d", "carry": "rate*4/iv", "cost_scen": "b",
                      "sel_min": 80, "anchor_offset_min": 6},
           "provenance": {"built_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                          "generation": "v3_2026-09", "base_ic": BASE["ic"],
                          "fold_ic_2024": round(fold_ic[2024], 4), "fold_ic_2025": round(fold_ic[2025], 4),
                          "pinned_ic2026": round(ic26, 4), "pinned_sharpe_full_b": round(sh, 2)}},
          open(f"{OUT}/config.json", "w"), indent=1)
man = {}
for f in sorted(os.listdir(OUT)):
    if f == "MANIFEST.json": continue
    man[f] = hashlib.sha256(open(f"{OUT}/{f}", "rb").read()).hexdigest()
json.dump(man, open(f"{OUT}/MANIFEST.json", "w"), indent=1)
with tarfile.open("/workspace/shadow_bundle_v3.tar.gz", "w:gz") as t:
    t.add(OUT, arcname="shadow_bundle")
print(f"BUNDLE_DONE files {len(man)} size {os.path.getsize('/workspace/shadow_bundle_v3.tar.gz')//1048576}MB", flush=True)
