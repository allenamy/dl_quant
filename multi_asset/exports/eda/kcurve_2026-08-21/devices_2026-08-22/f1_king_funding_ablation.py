"""F-1 · 宽书 king 剥离 funding 输入(ablation)+ 三腿配权归因 装置(2026-08-22, Session 6737834a-F1)。
预注册: multi_asset/exports/eda/PREREG_RESULT_F1_king_funding_ablation_2026-08-22.md §P(冻结段 SHA 710b9aee…a646, commit 213ebb1, 先于任何数字)。
SHA256: 脚本自身 SHA 与全部输入 SHA 运行时写入结果 JSON(`self_sha256` / `input_sha256`)。

【链 / 记账】宽书 W-b 链 = WA 装置 `wide_full_caliber_audit.py`(SHA 9792ecd0…808b)run_chain 语义; 本文件以带 w3 钩子的逐语句副本实现
  (新增 w3_mode: equal / fixed_45_45_10 / equal_nofund / king_only / rev24_only / fund_only; base/no_fund/half_fund 逐位不动);
  记账/读数函数(account / summarize / series_block / 块自助 / 五分位)直接 import WA 模块。收据 R1: K0 base d30 权重 ≡ probe_artifacts/wa/wa_weights_Wb_d30.npz
  (逐锚逐名 max|Δw| < 1e-6)且净@2 锚级夏普(2022-01..2026-06)= 1.668; no_fund = 0.664。
【king 重训】协议 = pod_slow_hist_folds.py 逐字(逐年扩张折 YV∈2022..2026, train = 年<YV ≥20k 行; LGBM 400/0.05/63/0.8/0.8), 唯一改动 = 特征列表 + random_state=0;
  特征 = pod_fea_wide_hist.py 逐字在本装置重建的 2020 起 hist 5m 缓存上重算(缓存 = [2020-01→2021-12 自 vision 月度 5m zip, 通道定义 pod_build_wide_ext.py 逐字]
  ⊕ [jpline dlnative_5m_wide829_f16.npz 2022-01→2026-08-11], 边界行 2022-01-01 00:00 ret5 重算); 锚/成员/y4/qvk = pod hist meta 原样(截到 2026-08-10 20:00)。
  臂: K0 = pod slow_pred_hist_oos.npy(只读) / K1 = 基线重训 78 列 / K2 = 去 fund_ema、fund_now 76 列 / K3 = K2 分数逐锚对 [xz(f_fund_ema_v1), xz(f_fund_now×8/iv)] 截面 OLS 残差。
【阶段】cache → fea → train → book(all = 依次)。用法 @jpline: python f1_king_funding_ablation.py cache|fea|train|book|all
"""
import os, sys, io, json, time, math, glob, zipfile, hashlib, datetime as dt
import numpy as np

T0 = time.time()
def log(*a): print(f"[{time.time()-T0:8.1f}s]", *a, flush=True)
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 24), b""): h.update(chunk)
    return h.hexdigest()
def fmt(t): return time.strftime("%Y-%m-%d %H:%M", time.gmtime(int(t)))
def yr_of(ts): return np.array([time.gmtime(int(t)).tm_year for t in ts])
HERE = os.path.dirname(os.path.abspath(__file__)); SELF_SHA = sha(os.path.abspath(__file__))
ON_JP = os.path.exists("/mnt/storage/private/work_hsy")
ROOT = "/mnt/storage/private/work_hsy"
PD = f"{ROOT}/probe_artifacts"; B = f"{ROOT}/pod_backup_2026-08-21"; WA = f"{PD}/wa"; F1 = f"{PD}/f1"; KL = f"{F1}/klines5m"
JPCACHE = f"{ROOT}/w3lane/kcurve/data/dlnative_5m_wide829_f16.npz"
HIST_CACHE = f"{F1}/dlnative_5m_wide829_f16_hist_f1.npz"
FEA_OUT = f"{F1}/wide_fea_hist_f1.npy"; META_OUT = f"{F1}/wide_fea_hist_f1_meta.npz"
for cand in (HERE, os.path.join(HERE, "wa"), f"{PD}/wa"):
    if os.path.exists(os.path.join(cand, "wide_full_caliber_audit.py")):
        sys.path.insert(0, cand); WA_PATH = os.path.join(cand, "wide_full_caliber_audit.py"); break
import wide_full_caliber_audit as WAM
from wide_full_caliber_audit import (xz, sharpe_a, sharpe_d, boot_sharpe_ci, boot_delta_sharpe, quintile_table, summarize, series_block, account, maxdd, anchors_grid, A_T0, A_T1, H4, H1, COST_MAIN)
WA_SHA = sha(WA_PATH)
if ON_JP: os.makedirs(F1, exist_ok=True)
T_CUT = int(dt.datetime(2026, 8, 10, 20, tzinfo=dt.timezone.utc).timestamp())          # 本装置缓存可完整覆盖的最后锚
T_END_MAIN = int(dt.datetime(2026, 6, 30, 23, tzinfo=dt.timezone.utc).timestamp())
CHN = ["ret5", "range", "cpos", "log_qv", "log_cnt", "log_avgsz", "tbf"]; WINS = (48, 288, 864, 2016, 8640)
STOP = (-0.30, 2, 42)
LGB_PARAMS = dict(n_estimators=400, learning_rate=0.05, num_leaves=63, subsample=0.8, colsample_bytree=0.8, n_jobs=24, verbose=-1, random_state=0)
FAMILIES = {"FUND": lambda n: n in ("fund_ema", "fund_now"), "RET": lambda n: n.startswith("ret5_sum_"), "VOL": lambda n: n.startswith("vol_"), "RANGE": lambda n: n.startswith("range_mean_"),
            "CPOS": lambda n: n.startswith("cpos_mean_"), "LIQ": lambda n: n.startswith("log_qv_mean_") or n.startswith("log_cnt_mean_") or n.startswith("log_avgsz_mean_"), "TBF": lambda n: n.startswith("tbf_mean_")}

# ───────────────────────────────────────────── stage cache: 2020-01 → 2022-01-01 00:00 自建 + jpline 2022+ 缓存拼接
def _read_zip_pd(path):
    import pandas as pd
    try:
        with zipfile.ZipFile(path) as z: raw = z.read(z.namelist()[0])
        return pd.read_csv(io.BytesIO(raw), header=0 if raw[:1].isalpha() else None).iloc[:, :11]
    except Exception:
        return None
def _build_2020_21(sym):
    """pod_build_wide_ext.build 逐字(仅 IDX 端点与目录不同)."""
    import pandas as pd
    IDX = pd.date_range('2020-01-01', '2022-01-01 00:00', freq='5min')
    ks = []
    for f in sorted(glob.glob(f'{KL}/{sym}/*.zip')):
        d = _read_zip_pd(f)
        if d is None or len(d) == 0: continue
        d.columns = ['open_time', 'o', 'h', 'l', 'c', 'v', 'close_time', 'qv', 'cnt', 'tbv', 'tbqv'][:d.shape[1]]
        ks.append(d)
    if not ks: return sym, None
    k = pd.concat(ks)
    k['ts'] = pd.to_datetime(k.open_time.astype(np.int64), unit='ms') + pd.Timedelta('5min')
    k = k.drop_duplicates('ts').set_index('ts').sort_index().reindex(IDX)
    A = np.full((len(IDX), 7), np.nan, np.float16)
    A[:, 0] = np.clip(k.c.pct_change(fill_method=None), -0.3, 0.3)
    A[:, 1] = np.clip((k.h - k.l) / k.c, 0, 0.5)
    A[:, 2] = ((k.c - k.l) / (k.h - k.l)).clip(0, 1)
    A[:, 3] = np.log1p(k.qv).clip(0, 25); A[:, 4] = np.log1p(k.cnt).clip(0, 20)
    A[:, 5] = np.log((k.qv / k.cnt.replace(0, np.nan))).clip(-5, 15)
    A[:, 6] = (k.tbqv / k.qv).clip(0, 1)
    return sym, A
def stage_cache():
    import pandas as pd
    from concurrent.futures import ProcessPoolExecutor
    Z = np.load(JPCACHE, allow_pickle=True); ts_jp = Z["ts"].astype(np.int64); syms = [str(s) for s in Z["symbols"]]; ch = Z["ch"]
    log("jp cache ts", len(ts_jp), fmt(ts_jp[0]), "->", fmt(ts_jp[-1]))
    IDX = pd.date_range('2020-01-01', '2022-01-01 00:00', freq='5min'); ts_mine = np.array(IDX, dtype='datetime64[s]').astype(np.int64)
    assert ts_mine[-1] == ts_jp[0], (fmt(ts_mine[-1]), fmt(ts_jp[0]))
    res = {}; nwith = 0
    with ProcessPoolExecutor(max_workers=16) as ex:
        for i, (s, arr) in enumerate(ex.map(_build_2020_21, syms, chunksize=4)):
            res[s] = arr; nwith += arr is not None
            if (i + 1) % 100 == 0: log("build 2020-21", i + 1, "/", len(syms), "with data", nwith)
    mine = np.stack([res[s] if res[s] is not None else np.full((len(IDX), 7), np.nan, np.float16) for s in syms], axis=1)   # (n2, NW, 7)
    log("mine", mine.shape, "names with 2020-21 data", nwith, "finite frac ret5", float(np.isfinite(mine[:, :, 0]).mean()))
    data_jp = Z["data"]; log("jp data loaded", data_jp.shape, data_jp.dtype)
    assert data_jp.shape[1] == len(syms) and data_jp.shape[2] == 7
    # 边界行: jp 首行(2022-01-01 00:00)的 ret5 = NaN(pct_change 首行); 用本装置 2021-12-31 23:55 → 2022-01-01 00:00 的值补上
    r0 = mine[-1, :, 0].astype(np.float32); jp0 = data_jp[0, :, 0].astype(np.float32)
    n_patch = int((np.isfinite(r0) & ~np.isfinite(jp0)).sum()); n_conflict = int((np.isfinite(r0) & np.isfinite(jp0)).sum())
    data_hist = np.concatenate([mine[:-1], data_jp], axis=0)
    row0 = len(IDX) - 1
    data_hist[row0, :, 0] = np.where(np.isfinite(r0), r0, data_hist[row0, :, 0]).astype(np.float16)
    # 其余 6 通道在边界行: 本装置与 jp 同 bar 同公式, 应逐位同(收据)
    same6 = float(np.nanmax(np.abs(mine[-1, :, 1:].astype(np.float32) - data_jp[0, :, 1:].astype(np.float32)))) if np.isfinite(mine[-1, :, 1:].astype(np.float32)).any() else None
    ts_hist = np.concatenate([ts_mine[:-1], ts_jp])
    assert len(ts_hist) == data_hist.shape[0] and np.all(np.diff(ts_hist) == 300)
    np.savez(HIST_CACHE, ts=ts_hist, symbols=np.array(syms), ch=ch, data=data_hist)
    rep = {"n_syms": len(syms), "n_syms_with_2020_21_data": nwith, "hist_grid": [fmt(ts_hist[0]), fmt(ts_hist[-1]), int(len(ts_hist))], "boundary_row_ret5_patched": n_patch, "boundary_row_ret5_conflict(jp finite)": n_conflict,
           "boundary_other6_maxabs_diff_mine_vs_jp": same6, "jp_cache_sha256": sha(JPCACHE), "finite_frac_ret5_2020_21": float(np.isfinite(mine[:, :, 0]).mean()),
           "bars_with_data_2020": int(np.isfinite(mine[:105408, :, 0]).sum()), "bars_with_data_2021": int(np.isfinite(mine[105408:-1, :, 0]).sum())}
    json.dump(rep, open(f"{F1}/cache_report.json", "w"), indent=1); log("CACHE_DONE", rep)

# ───────────────────────────────────────────── stage fea: pod_fea_wide_hist 逐字(锚/成员 = pod meta 原样)
def _cs_pair(x, NW):
    fin = np.isfinite(x); xz_ = np.where(fin, x, 0).astype(np.float64)
    return (np.concatenate([np.zeros((1, NW)), np.cumsum(xz_, 0)]), np.concatenate([np.zeros((1, NW), np.int32), np.cumsum(fin, 0, dtype=np.int32)]))
def stage_fea():
    from scipy.stats import rankdata
    Z = np.load(HIST_CACHE, allow_pickle=True); CTS = Z["ts"].astype(np.int64); CD = Z["data"]; syms = [str(s) for s in Z["symbols"]]; NW = len(syms); TT = CD.shape[0]
    log("hist cache", CD.shape, fmt(CTS[0]), "->", fmt(CTS[-1]))
    MT = np.load(f"{B}/wide_fea_hist_meta.npz", allow_pickle=True); E_ts_all = MT["E_ts"].astype(np.int64); names = [str(n) for n in MT["names"]]
    keep_a = E_ts_all <= T_CUT; E_ts = E_ts_all[keep_a]; members = MT["members"][keep_a]; y4p = MT["y4"][keep_a]; qvkp = MT["qvk"][keep_a]
    cpos = {int(t): i for i, t in enumerate(CTS)}; E = np.array([cpos[int(t)] for t in E_ts]); assert (E >= 8640).all() and (E + 48 <= TT).all()
    log("anchors", len(E), fmt(E_ts[0]), "->", fmt(E_ts[-1]))
    # ret5 channel: sums/counts/r2 (y4 / members / vol 需要)
    s_r, f_r = _cs_pair(CD[:, :, 0].astype(np.float32), NW); r2s, r2f = _cs_pair((CD[:, :, 0].astype(np.float64)) ** 2, NW)
    y4n = f_r[E + 48] - f_r[E]; y4m = (s_r[E + 48] - s_r[E]).astype(np.float32); y4m[y4n < 46] = np.nan
    VAL = []; val_names = []
    for nm_i, nm in enumerate(CHN):
        s_, f_ = (s_r, f_r) if nm == "ret5" else _cs_pair(CD[:, :, nm_i].astype(np.float32), NW)
        if nm == "log_qv": qv_s, qv_f = s_, f_
        for w in WINS:
            nf = np.maximum(f_[E] - f_[E - w], 1)
            if nm == "ret5": VAL.append(((s_[E] - s_[E - w])).astype(np.float32)); val_names.append(f"{nm}_sum_{w}")
            else: VAL.append(((s_[E] - s_[E - w]) / nf).astype(np.float32)); val_names.append(f"{nm}_mean_{w}")
        log("channel", nm, "done")
        if nm != "ret5" and nm != "log_qv": del s_, f_
    for w in WINS:
        nf = np.maximum(f_r[E] - f_r[E - w], 1); mm = (s_r[E] - s_r[E - w]) / nf
        vv = np.sqrt(np.maximum((r2s[E] - r2s[E - w]) / nf - mm ** 2, 0)); VAL.append(vv.astype(np.float32)); val_names.append(f"vol_{w}")
    # R0(b): 成员重算(pod 筛选逐字)
    n7 = np.maximum(qv_f[E] - qv_f[E - 2016], 1); covr = (f_r[E] - f_r[np.maximum(E - 2016, 0)]) / 2016; qvm = (qv_s[E] - qv_s[E - 2016]) / n7
    m7 = (s_r[E] - s_r[E - 2016]); v7 = np.sqrt(np.maximum((r2s[E] - r2s[E - 2016]) / n7 - (m7 / n7) ** 2, 0))
    same_m = np.zeros(len(E), bool); jacc = np.zeros(len(E))
    for i in range(len(E)):
        ok = (covr[i] >= 0.95) & (v7[i] >= 1e-4) & np.isfinite(y4m[i]); m = np.where(ok)[0]
        if len(m) > 400: m = np.sort(m[np.argsort(-qvm[i, m])[:400]])
        mp = np.asarray(members[i]); same_m[i] = (len(m) == len(mp)) and np.array_equal(m, mp)
        a, b_ = set(m.tolist()), set(mp.tolist()); jacc[i] = len(a & b_) / max(len(a | b_), 1)
    del r2s, r2f
    yrs = yr_of(E_ts)
    # R0(a): y4 重算 vs pod y4(成员内)
    dy = []; dy_yr = {}
    for i in range(len(E)):
        m = np.asarray(members[i]); a = y4m[i, m]; b_ = y4p[i, m]; ok = np.isfinite(a) & np.isfinite(b_); d = np.abs(a[ok] - b_[ok]); dy.append(d)
        dy_yr.setdefault(int(yrs[i]), []).append(d)
        if (np.isfinite(a) != np.isfinite(b_)).any(): dy_yr.setdefault(f"{int(yrs[i])}_finite_mismatch", []).append(np.array([float((np.isfinite(a) != np.isfinite(b_)).sum())]))
    dy_all = np.concatenate(dy)
    R0 = {"n_anchors": int(len(E)), "y4_maxabs_diff": float(dy_all.max()), "y4_frac_lt_1e-6": float((dy_all < 1e-6).mean()), "y4_mean_abs_diff": float(dy_all.mean()),
          "y4_by_year": {str(k): {"maxabs": float(np.concatenate(v).max()), "frac_lt_1e-6": float((np.concatenate(v) < 1e-6).mean()), "n": int(len(np.concatenate(v)))} for k, v in dy_yr.items() if isinstance(k, int)},
          "y4_finite_mismatch_cells_by_year": {k.split("_")[0]: int(sum(float(x[0]) for x in v)) for k, v in dy_yr.items() if not isinstance(k, int)},
          "members_identical_frac": float(same_m.mean()), "members_identical_by_year": {int(y): float(same_m[yrs == y].mean()) for y in sorted(set(yrs.tolist()))},
          "members_jaccard_mean_by_year": {int(y): float(jacc[yrs == y].mean()) for y in sorted(set(yrs.tolist()))}}
    log("R0", R0)
    # FEA fill(pod 逐字): 值(clip ±1e4, nan→0) + 成员内秩; 末两列 funding(hist v1 面板 行 T, nan→0)
    PW = np.load(f"{B}/wide_panel_4h_hist.npz", allow_pickle=True); assert [str(s) for s in PW["symbols"]] == syms
    pw_row = {int(t): j for j, t in enumerate(PW["ts"].astype(np.int64))}; FUND = [PW["f_fund_ema"], PW["f_fund_now"]]
    NVAL = len(VAL); NF = NVAL * 2 + len(FUND); assert NF == len(names) and [n + s for n in val_names for s in ("_v", "_r")] + ["fund_ema", "fund_now"] == names
    FEA = np.full((len(E), NW, NF), np.nan, np.float16); t1 = time.time(); n_nofund = 0
    for i in range(len(E)):
        m = np.asarray(members[i]); col = 0
        for v in VAL:
            x = v[i, m]
            FEA[i, m, col] = np.clip(np.nan_to_num(x, nan=0), -1e4, 1e4); col += 1
            ok = np.isfinite(x); rr = np.zeros(len(m), np.float32)
            if ok.sum() >= 10: rr[ok] = rankdata(x[ok]) / max(ok.sum() - 1, 1) - 0.5
            FEA[i, m, col] = rr; col += 1
        j = pw_row.get(int(E_ts[i]))
        if j is not None:
            for fv in FUND:
                FEA[i, m, col] = np.nan_to_num(fv[j, m], nan=0); col += 1
        else: n_nofund += 1
        if i % 2000 == 0: log("fea", i, "/", len(E), round(time.time() - t1), "s")
    np.save(FEA_OUT, FEA)
    np.savez_compressed(META_OUT, E_ts=E_ts, members=members, y4=y4p, y4_mine=y4m, qvk=qvkp, names=np.array(names), val_names=np.array(val_names))
    rep = {"FEA_shape": list(FEA.shape), "anchors_without_panel_row": n_nofund, "R0": R0, "fea_sha256": sha(FEA_OUT), "hist_cache_sha256": sha(HIST_CACHE)}
    json.dump(rep, open(f"{F1}/fea_report.json", "w"), indent=1); log("FEA_DONE", FEA.shape, "sha", rep["fea_sha256"][:16])

# ───────────────────────────────────────────── stage train
def _ic_rows(p, y, A):
    """逐锚 Spearman(p, y) 均值(行按 A 分组; 每锚 ≥30 有效)."""
    from scipy.stats import rankdata
    out = {}; order = np.argsort(A, kind="stable"); A2 = A[order]; p2 = p[order]; y2 = y[order]
    bounds = np.flatnonzero(np.diff(A2)) + 1; starts = np.concatenate([[0], bounds]); ends = np.concatenate([bounds, [len(A2)]])
    for s, e in zip(starts, ends):
        pp = p2[s:e]; yy = y2[s:e]; ok = np.isfinite(pp) & np.isfinite(yy)
        if ok.sum() < 30: out[int(A2[s])] = np.nan; continue
        rp = rankdata(pp[ok]); ry = rankdata(yy[ok]); out[int(A2[s])] = float(np.corrcoef(rp, ry)[0, 1])
    return out
def _load_ret_1h(E_ts, syms):
    """WA 1h 网格 → 锚 T 的 (T,T+4h] 简单收益 (nE, NW)."""
    Z = np.load(f"{WA}/close1h_829.npz", allow_pickle=True); hts = Z["ts"].astype(np.int64); C = Z["close"]; assert [str(s) for s in Z["symbols"]] == syms
    hpos = {int(t): i for i, t in enumerate(hts)}; i0 = np.array([hpos.get(int(t), -1) for t in E_ts]); okk = (i0 >= 0) & (i0 + 4 < len(hts)); i1 = i0 + 4
    RET = np.full((len(E_ts), C.shape[1]), np.nan, np.float64)
    with np.errstate(all="ignore"):
        RET[okk] = (C[i1[okk]] / C[i0[okk]] - 1.0).astype(np.float64)      # 2020 锚不在 WA 1h 网格(2021-01 起)⇒ NaN(只影响交易口径 IC, 测试年 ≥2022 不受影响)
    RET[~np.isfinite(RET)] = np.nan; return RET
def stage_train():
    import lightgbm as lgb
    from scipy.stats import rankdata
    MT = np.load(META_OUT, allow_pickle=True); E_ts = MT["E_ts"].astype(np.int64); members = MT["members"]; y4 = MT["y4"]; names = [str(n) for n in MT["names"]]
    FEA = np.load(FEA_OUT, mmap_mode="r"); nA = len(E_ts); NW = FEA.shape[1]; yrs = yr_of(E_ts)
    syms = [str(s) for s in np.load(f"{B}/wide_panel_4h_hist_v2.npz", allow_pickle=True)["symbols"]]
    RET1H = _load_ret_1h(E_ts, syms)
    keep_base = [k for k, nm in enumerate(names) if not (nm.startswith("ret5_sum_48") or nm.startswith("ret5_sum_288"))]
    keep_nof = [k for k in keep_base if names[k] not in ("fund_ema", "fund_now")]
    assert len(keep_base) == 78 and len(keep_nof) == 76
    rows_X, rows_y, rows_a, rows_ret, rows_y4, rows_m = [], [], [], [], [], []
    for i in range(nA):
        m = np.asarray(members[i]); yv = y4[i, m]; ok = np.isfinite(yv)
        if ok.sum() < 50: continue
        rr = rankdata(yv[ok]) / max(ok.sum() - 1, 1) - 0.5
        rows_X.append(np.asarray(FEA[i, m[ok]][:, keep_base], np.float32)); rows_y.append(rr.astype(np.float32)); rows_a.append(np.full(ok.sum(), i, np.int32))
        rows_ret.append(RET1H[i, m[ok]].astype(np.float32)); rows_y4.append(yv[ok].astype(np.float32)); rows_m.append(m[ok].astype(np.int32))
    X = np.concatenate(rows_X); Y = np.concatenate(rows_y); A = np.concatenate(rows_a); R1 = np.concatenate(rows_ret); Y4 = np.concatenate(rows_y4); MM = np.concatenate(rows_m); YRA = yrs[A]
    log("X", X.shape, "year rows", {int(y): int((YRA == y).sum()) for y in np.unique(YRA)})
    kb_names = [names[k] for k in keep_base]; col_nof = [j for j, nm in enumerate(kb_names) if nm not in ("fund_ema", "fund_now")]
    fam_cols = {fam: [j for j, nm in enumerate(kb_names) if fn(nm)] for fam, fn in FAMILIES.items()}; assert sum(len(v) for v in fam_cols.values()) == 78
    K0 = np.load(f"{B}/slow_pred_hist_oos.npy"); pod_E = np.load(f"{B}/wide_fea_hist_meta.npz", allow_pickle=True)["E_ts"].astype(np.int64)
    pod_row = {int(t): j for j, t in enumerate(pod_E)}; K0r = np.array([K0[pod_row[int(t)]] for t in E_ts])     # (nA, NW) 对齐本装置锚
    K0_rows = K0r[A, MM]
    arms = {"K1": (kb_names, list(range(78))), "K2": ([kb_names[j] for j in col_nof], col_nof)}
    PRED = {k: np.full((nA, NW), np.nan, np.float32) for k in arms}; OUT = {"arms": {}, "families": {f: [kb_names[j] for j in c] for f, c in fam_cols.items()}, "lgb_params": {k: v for k, v in LGB_PARAMS.items()}}
    rng_sub = np.random.RandomState(0)
    for arm, (anames, cols) in arms.items():
        Xa = X[:, cols]; res = {"ic_y4_by_year": {}, "ic_ret1h_by_year": {}, "train_rows": {}, "shap_family_share_by_fold": {}, "perm_dIC_by_fold": {}, "feat_gain_top15_by_fold": {}}
        shap_pool = {f: 0.0 for f in fam_cols}; shap_tot = 0.0; perm_pool = {f: [] for f in fam_cols}
        for YV in (2022, 2023, 2024, 2025, 2026):
            tr = YRA < YV; te = YRA == YV
            if te.sum() == 0 or tr.sum() < 20000: log(arm, "skip", YV, int(tr.sum())); continue
            t1 = time.time(); g = lgb.LGBMRegressor(**LGB_PARAMS).fit(Xa[tr], Y[tr]); pv = g.predict(Xa[te]).astype(np.float32)
            PRED[arm][A[te], MM[te]] = pv
            icy = _ic_rows(pv, Y4[te], A[te]); icr = _ic_rows(pv, R1[te], A[te])
            res["ic_y4_by_year"][str(YV)] = round(float(np.nanmean(list(icy.values()))), 4); res["ic_ret1h_by_year"][str(YV)] = round(float(np.nanmean(list(icr.values()))), 4); res["train_rows"][str(YV)] = int(tr.sum())
            imp = g.booster_.feature_importance(importance_type="gain"); top = np.argsort(-imp)[:15]; res["feat_gain_top15_by_fold"][str(YV)] = [(anames[j], round(float(imp[j] / imp.sum()), 4)) for j in top]
            # SHAP(pred_contrib)子样本
            te_idx = np.flatnonzero(te); sub = rng_sub.choice(te_idx, size=min(200000, len(te_idx)), replace=False)
            contrib = g.booster_.predict(Xa[sub], pred_contrib=True)[:, :-1]; mabs = np.abs(contrib).mean(0); tot = float(mabs.sum())
            fam_cols_arm = {f: [j for j, nm in enumerate(anames) if FAMILIES[f](nm)] for f in fam_cols}
            res["shap_family_share_by_fold"][str(YV)] = {f: round(float(mabs[c].sum() / tot), 4) if c else 0.0 for f, c in fam_cols_arm.items()}
            for f, c in fam_cols_arm.items(): shap_pool[f] += float(mabs[c].sum()) * len(sub)
            shap_tot += tot * len(sub)
            # 置换重要性(锚内联合同序置换, seeds 0/1/2)
            base_ic = float(np.nanmean(list(icy.values()))); Xte = Xa[te]; Ate = A[te]; Yte = Y4[te]
            order = np.argsort(Ate, kind="stable"); A2 = Ate[order]; bounds = np.flatnonzero(np.diff(A2)) + 1; starts = np.concatenate([[0], bounds]); ends = np.concatenate([bounds, [len(A2)]])
            res["perm_dIC_by_fold"][str(YV)] = {}
            for f, c in fam_cols_arm.items():
                if not c: continue
                dics = []
                for seed in (0, 1, 2):
                    rng = np.random.RandomState(seed); Xp = Xte.copy()
                    for s, e in zip(starts, ends):
                        idx = order[s:e]; perm = rng.permutation(len(idx)); Xp[idx[:, None], np.array(c)[None, :]] = Xte[idx[perm][:, None], np.array(c)[None, :]]
                    pp = g.predict(Xp); icp = _ic_rows(pp, Yte, Ate); dics.append(base_ic - float(np.nanmean(list(icp.values()))))
                res["perm_dIC_by_fold"][str(YV)][f] = round(float(np.mean(dics)), 4); perm_pool[f].append((float(np.mean(dics)), int(te.sum())))
            log(arm, "fold", YV, "rows", int(tr.sum()), "IC y4", res["ic_y4_by_year"][str(YV)], "IC ret1h", res["ic_ret1h_by_year"][str(YV)], "shap", res["shap_family_share_by_fold"][str(YV)], round(time.time() - t1), "s")
        res["shap_family_share_pooled"] = {f: round(v / shap_tot, 4) for f, v in shap_pool.items()}
        res["perm_dIC_pooled_rowweighted"] = {f: round(sum(d * n for d, n in v) / max(sum(n for _, n in v), 1), 4) for f, v in perm_pool.items() if v}
        ic_all_y4 = _ic_rows(PRED[arm][A, MM], Y4, A); ic_all_r = _ic_rows(PRED[arm][A, MM], R1, A)
        res["ic_y4_pooled_2022_26"] = round(float(np.nanmean([v for k, v in ic_all_y4.items() if yrs[k] >= 2022])), 4); res["ic_ret1h_pooled_2022_26"] = round(float(np.nanmean([v for k, v in ic_all_r.items() if yrs[k] >= 2022])), 4)
        OUT["arms"][arm] = res; np.save(f"{F1}/pred_{arm}.npy", PRED[arm]); log(arm, "DONE", res["ic_y4_by_year"], res["shap_family_share_pooled"])
    # 臂间相关 + K0 参考 IC(同口径同锚)
    def xcorr(P, Q):
        out = _ic_rows(P[A, MM], Q[A, MM], A); return {int(y): round(float(np.nanmean([v for k, v in out.items() if yrs[k] == y])), 4) for y in range(2022, 2027)}, round(float(np.nanmean([v for k, v in out.items() if yrs[k] >= 2022])), 4)
    ic0y = _ic_rows(K0_rows, Y4, A); ic0r = _ic_rows(K0_rows, R1, A)
    OUT["K0_reference"] = {"ic_y4_by_year": {int(y): round(float(np.nanmean([v for k, v in ic0y.items() if yrs[k] == y])), 4) for y in range(2022, 2027)}, "ic_ret1h_by_year": {int(y): round(float(np.nanmean([v for k, v in ic0r.items() if yrs[k] == y])), 4) for y in range(2022, 2027)},
                           "pod_slow_hist_folds_json": json.load(open(f"{B}/slow_hist_folds.json"))}
    OUT["cross_arm_spearman"] = {"K1_vs_K0": xcorr(PRED["K1"], K0r), "K2_vs_K0": xcorr(PRED["K2"], K0r), "K2_vs_K1": xcorr(PRED["K2"], PRED["K1"])}
    OUT["receipt_R2"] = {"K1_vs_K0_pooled_spearman": OUT["cross_arm_spearman"]["K1_vs_K0"][1],
                         "K1_minus_podjson_ic_by_year": {y: round(OUT["arms"]["K1"]["ic_y4_by_year"].get(y, float("nan")) - OUT["K0_reference"]["pod_slow_hist_folds_json"]["ic_by_year"].get(y, float("nan")), 4) for y in OUT["K0_reference"]["pod_slow_hist_folds_json"]["ic_by_year"]}}
    OUT["receipt_R2"]["pass"] = bool(OUT["receipt_R2"]["K1_vs_K0_pooled_spearman"] >= 0.90 and all(abs(v) <= 0.006 for v in OUT["receipt_R2"]["K1_minus_podjson_ic_by_year"].values() if np.isfinite(v)))
    OUT["n_rows"] = int(len(Y)); OUT["fea_sha256"] = sha(FEA_OUT)
    json.dump(OUT, open(f"{F1}/f1_train.json", "w"), indent=1); log("TRAIN_DONE", OUT["receipt_R2"], OUT["cross_arm_spearman"])

# ───────────────────────────────────────────── W-b 链(WA.run_chain 逐语句副本 + w3 钩子)
FIXED_W3 = {"equal": np.array([1 / 3, 1 / 3, 1 / 3]), "fixed_45_45_10": np.array([0.45, 0.45, 0.10]), "equal_nofund": np.array([0.5, 0.5, 0.0]),
            "king_only": np.array([1.0, 0.0, 0.0]), "rev24_only": np.array([0.0, 1.0, 0.0]), "fund_only": np.array([0.0, 0.0, 1.0])}
def run_chain_f1(D, RET, stop=None, w3_mode="base", tag="", record_from=None):
    NW = D["NW"]; alpha = 0.1; band = 2.5e-4; capm = 2.5; look = 900
    depth, need, cool = stop if stop else (None, 0, 0)
    H = np.zeros(NW); HL = np.zeros((3, NW)); Pi = np.ones(NW); sh = np.zeros(NW); cb = np.zeros(NW); cnt = np.zeros(NW, int); su = np.full(NW, -1)
    LR = {"king": [], "rev24": [], "fund": []}
    recs = []; W = []; WL = []; W3 = []; skipped = 0; nfires = 0
    E_ts = D["E_ts"]; rf = 0 if record_from is None else record_from
    for j in range(len(E_ts)):
        T = int(E_ts[j]); jp = D["pw_row"].get(T); ai = D["apos"].get(T)
        if jp is None or ai is None: continue
        m = D["members"][j]
        sc = {"king": D["SLOW"][j, m], "rev24": -D["R24"][jp, m], "fund": D["FE"][jp, m]}
        yv_m = RET[ai, m].astype(float)
        ok = np.isfinite(yv_m); yv0 = np.where(ok, yv_m, 0.0)
        for leg in LR:
            z = np.nan_to_num(xz(sc[leg])); z = np.where(ok, z, 0.0); z -= (z[ok].mean() if ok.sum() else 0.0); g = np.abs(z).sum()
            LR[leg].append(float((z / g * yv0).sum() * 1e4) if g > 1e-9 else 0.0)
        p = len(LR["king"]) - 1
        if p >= look:
            r = np.stack([np.array(LR[l][p - look:p]) for l in ("king", "rev24", "fund")]); shp = np.maximum(r.mean(1) / (r.std(1) + 1e-9), 0.0)
            w3 = shp / shp.sum() if shp.sum() > 0 else np.array([1 / 3] * 3)
        else:
            w3 = np.array([1 / 3] * 3)
        if w3_mode == "no_fund":
            w3 = np.array([w3[0], w3[1], 0.0]); w3 = w3 / w3.sum() if w3.sum() > 0 else np.array([0.5, 0.5, 0.0])
        elif w3_mode == "half_fund":
            w3 = np.array([w3[0], w3[1], 0.5 * w3[2]]); w3 = w3 / w3.sum()
        elif w3_mode in FIXED_W3:
            w3 = FIXED_W3[w3_mode].copy()
        qv4h = np.expm1(np.clip(D["qvk"][j, m], 0, 30)) * 48
        sel = ok & (qv4h >= 2.5e5)
        zk = np.stack([wk * np.nan_to_num(xz(sc[l])) for wk, l in zip(w3, ("king", "rev24", "fund"))])
        if sel.sum() < 80:
            skipped += 1; tgt_k = HL[:, :].copy() * 0; do_trade = False
        else:
            do_trade = True
            zk = np.where(sel[None, :], zk, 0.0); zk = zk - np.where(sel[None, :], zk[:, sel].mean(1, keepdims=True), 0.0)
            w = zk.sum(0); g = np.abs(w).sum()
            if g < 1e-9: skipped += 1; do_trade = False
            else:
                zk = zk / g; w = w / g; capw = capm / max(int(sel.sum()), 1); wc = np.clip(w, -capw, capw)
                with np.errstate(all="ignore"):
                    f = np.where(np.abs(w) > 1e-15, wc / w, 1.0)
                zk = zk * f[None, :]; g2 = np.abs(wc).sum()
                if g2 > 1e-9: zk = zk / g2
                tgt_k = np.zeros((3, NW)); tgt_k[:, m] = zk
        if do_trade:
            if depth is not None:
                bl = su > j
                if bl.any(): tgt_k[:, bl] = 0.0
            tgt = tgt_k.sum(0)
            sm = H + alpha * (tgt - H); trade = sm - H
            keep = np.abs(trade) < band
            sm = np.where(keep, H, sm)
            HLn = HL + alpha * (tgt_k - HL); HLn = np.where(keep[None, :], HL, HLn)
            H = sm; HL = HLn
        if j >= rf:
            recs.append(T); W.append(H.astype(np.float32)); WL.append(HL.astype(np.float32)); W3.append(w3)
        yfull = np.nan_to_num(RET[ai].astype(float))
        nsh = np.where(Pi > 1e-12, H / Pi, 0.0)
        same = np.sign(nsh) == np.sign(sh); add = same & (np.abs(nsh) > np.abs(sh))
        red = same & (~add) & (np.abs(nsh) > 1e-12); new = (~same) | (np.abs(sh) < 1e-12)
        cb = np.where(add, cb + (nsh - sh) * Pi, cb)
        with np.errstate(all="ignore"):
            ratio = np.where(np.abs(sh) > 1e-12, nsh / np.where(np.abs(sh) > 1e-12, sh, 1.0), 0.0)
        cb = np.where(red, cb * ratio, cb); cb = np.where(new, nsh * Pi, cb); cb = np.where(np.abs(nsh) < 1e-12, 0.0, cb)
        sh = nsh
        with np.errstate(all="ignore"):
            avg = np.where(np.abs(sh) > 1e-12, cb / sh, np.nan); dep = np.where(np.isfinite(avg) & (Pi > 0), np.sign(sh) * (1.0 - avg / Pi), 0.0)
        if depth is not None:
            cand = (np.abs(sh) > 1e-12) & (dep <= depth) & (su <= j)
            cnt = np.where(cand, cnt + 1, 0); fire = cnt >= need
            if fire.any(): su[fire] = j + cool; cnt[fire] = 0; nfires += int(fire.sum())
        Pi = Pi * (1.0 + yfull)
    W = np.stack(W); WL = np.stack(WL)
    assert np.abs(WL.sum(1) - W).max() < 1e-5, "leg decomposition not additive"
    return {"ts": np.array(recs, np.int64), "W": W, "WL": WL, "w3": np.array(W3), "skipped": skipped, "fires": nfires}

_G = {}
def _chain_job(args):
    king, mode, stopname = args
    D = dict(_G["D"]); D["SLOW"] = _G["KINGS"][king]
    r = run_chain_f1(D, _G["RET"], stop=(STOP if stopname == "d30" else None), w3_mode=mode, tag=f"{king}_{mode}_{stopname}", record_from=_G["rec_from"])
    return (king, mode, stopname), r

def _account_job(args):
    name, ts_, W_, WL_ = args
    G = _G; apos = G["apos"]; ai = np.array([apos.get(int(t), -1) for t in ts_]); ok = (ai >= 0) & (ts_ >= A_T0) & (ts_ <= T_CUT)
    ai = ai[ok]; ts_ = ts_[ok]; W_ = W_[ok]; WL_ = WL_[ok]
    Fsub = {k2: G["F"][k2][ai] for k2 in G["F"]}
    acc = account(W_, ts_, Fsub, G["RET"][ai], G["LRET"][ai], qv_tier=None, WL=WL_)
    m26 = ts_ <= T_END_MAIN; yr = yr_of(ts_)
    S = {"FULL(2022-01..2026-08-10)": summarize(acc, ts_, G["mkt"][ai], name), "2022-01..2026-06": summarize(acc, ts_, G["mkt"][ai], name, yr_mask=m26),
         "2024-26": summarize(acc, ts_, G["mkt"][ai], name, yr_mask=(yr >= 2024) & m26), "2022-23": summarize(acc, ts_, G["mkt"][ai], name, yr_mask=(yr <= 2023))}
    # 腿级(WA 可加分解)净@2 序列, 供 C 份额与 Δ
    with np.errstate(all="ignore"):
        gq = np.where(acc["gross"] > 1e-9, acc["gross"], np.nan)
    legs_g2 = {leg: np.nan_to_num(2 * acc["legs"][leg]["net"] / gq) for leg in ("king", "rev24", "fund")}
    return name, {"ts": ts_, "net_g2": acc["net_g2"], "net": acc["net"], "gross": acc["gross"], "trn": acc["trn"], "legs_g2": legs_g2, "summ": S}

def stage_book():
    from multiprocessing import Pool
    R = {"session": "6737834a-F1", "created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "self_sha256": SELF_SHA, "wa_module_sha256": WA_SHA, "stage": "book"}
    INPUTS = {"close1h": f"{WA}/close1h_829.npz", "funding": f"{WA}/funding_829.npz", "meta_pod": f"{B}/wide_fea_hist_meta.npz", "panel_v2": f"{B}/wide_panel_4h_hist_v2.npz", "slow_pred_K0": f"{B}/slow_pred_hist_oos.npy",
              "wa_weights_Wb_d30": f"{WA}/wa_weights_Wb_d30.npz", "pred_K1": f"{F1}/pred_K1.npy", "pred_K2": f"{F1}/pred_K2.npy", "meta_f1": META_OUT, "fea_f1": FEA_OUT, "train_json": f"{F1}/f1_train.json", "hist_cache": HIST_CACHE}
    R["input_sha256"] = {k: (sha(v) if os.path.exists(v) else None) for k, v in INPUTS.items()}; log("input shas done")
    Z = np.load(INPUTS["close1h"], allow_pickle=True); hts = Z["ts"].astype(np.int64); syms = [str(s) for s in Z["symbols"]]; C = Z["close"]; NW = len(syms)
    hpos = {int(t): i for i, t in enumerate(hts)}
    A = anchors_grid(int(dt.datetime(2021, 1, 1, tzinfo=dt.timezone.utc).timestamp()), A_T1); nA = len(A); apos = {int(t): i for i, t in enumerate(A)}
    i0 = np.array([hpos[int(t)] for t in A]); i1 = i0 + 4
    with np.errstate(all="ignore"):
        RET = (C[i1] / C[i0] - 1.0).astype(np.float64); LRET = np.log(C[i1] / C[i0])
    RET[~np.isfinite(RET)] = np.nan; LRET[~np.isfinite(LRET)] = np.nan
    FZ = np.load(INPUTS["funding"], allow_pickle=True); assert np.array_equal(FZ["anchors"].astype(np.int64), A) and [str(s) for s in FZ["symbols"]] == syms
    F = {k: FZ[k] for k in ("fr_sum", "nset", "last_rate", "last_iv", "last_age_h", "cov")}
    MT = np.load(INPUTS["meta_pod"], allow_pickle=True); E_all = MT["E_ts"].astype(np.int64); keep_a = E_all <= T_CUT
    E_ts = E_all[keep_a]; members = MT["members"][keep_a]; qvk = MT["qvk"][keep_a]
    PW = np.load(INPUTS["panel_v2"], allow_pickle=True); assert [str(s) for s in PW["symbols"]] == syms
    pw_row = {int(t): j for j, t in enumerate(PW["ts"].astype(np.int64))}
    D = {"E_ts": E_ts, "members": members, "R24": PW["f_rev_24h"], "FE": PW["f_fund_ema_v1"], "qvk": qvk, "pw_row": pw_row, "NW": NW, "apos": apos}
    mrow = {int(t): j for j, t in enumerate(E_ts)}
    mkt = np.full(nA, np.nan)
    for i, t in enumerate(A):
        j = mrow.get(int(t))
        if j is None: continue
        v = RET[i, members[j]]; v = v[np.isfinite(v)]
        if len(v): mkt[i] = v.mean() * 1e4
    # kings
    K0 = np.load(INPUTS["slow_pred_K0"])[keep_a]
    MF = np.load(INPUTS["meta_f1"], allow_pickle=True); assert np.array_equal(MF["E_ts"].astype(np.int64), E_ts)
    K1 = np.load(INPUTS["pred_K1"]); K2 = np.load(INPUTS["pred_K2"]); assert K1.shape == K0.shape == K2.shape
    # K3 = K2 逐锚对 funding 族截面 OLS 残差(成员内, ≤T)
    FN = PW["f_fund_now"]; IV = PW["f_fund_iv"]; FE = PW["f_fund_ema_v1"]
    K3 = np.full_like(K2, np.nan); k3_r2 = []
    for j, T in enumerate(E_ts):
        jp = pw_row.get(int(T)); m = members[j]
        if jp is None: continue
        s_ = K2[j, m].astype(float); fe = FE[jp, m].astype(float); ivv = IV[jp, m].astype(float); ivv = np.where(np.isfinite(ivv) & (ivv > 0), ivv, 8.0); fn = FN[jp, m].astype(float) * 8.0 / ivv
        ok = np.isfinite(s_)
        if ok.sum() < 30: continue
        ze = np.nan_to_num(xz(np.where(np.isfinite(fe), fe, np.nan))); zn = np.nan_to_num(xz(np.where(np.isfinite(fn), fn, np.nan)))
        Xo = np.column_stack([np.ones(ok.sum()), ze[ok], zn[ok]]); b_, *_ = np.linalg.lstsq(Xo, s_[ok], rcond=None); resid = s_[ok] - Xo @ b_
        out = np.full(len(m), np.nan); out[ok] = resid; K3[j, m] = out
        vs = s_[ok].var(); k3_r2.append((int(time.gmtime(int(T)).tm_year), 1 - resid.var() / vs if vs > 0 else np.nan))
    R["K3_funding_R2_mean"] = round(float(np.nanmean([v for _, v in k3_r2])), 4); R["K3_funding_R2_by_year"] = {y: round(float(np.nanmean([v for yy, v in k3_r2 if yy == y])), 4) for y in range(2022, 2027)}
    KINGS = {"K0": K0, "K1": K1, "K2": K2, "K3": K3}
    # rev24/fund 腿对 K2 的相关(逐锚 Spearman)亦报
    def leg_corr(P, Q):
        vals = []
        for j in range(len(E_ts)):
            jp = pw_row.get(int(E_ts[j])); m = members[j]
            if jp is None: continue
            a = P[j, m]; b_ = Q(jp, m); ok = np.isfinite(a) & np.isfinite(b_)
            if ok.sum() < 30: continue
            vals.append(np.corrcoef(np.argsort(np.argsort(a[ok])), np.argsort(np.argsort(b_[ok])))[0, 1])
        return round(float(np.nanmean(vals)), 4)
    R["king_vs_leg_spearman"] = {k: {"vs_fund_ema_v1": leg_corr(P, lambda jp, m: FE[jp, m]), "vs_rev24(-f_rev_24h)": leg_corr(P, lambda jp, m: -PW["f_rev_24h"][jp, m])} for k, P in KINGS.items()}
    log("king vs legs", R["king_vs_leg_spearman"])
    rec_from = int(np.searchsorted(E_ts, A_T0))
    _G.update({"D": D, "RET": RET, "LRET": LRET, "KINGS": KINGS, "rec_from": rec_from, "apos": apos, "F": F, "mkt": mkt})
    jobs = []
    for k in ("K0",): jobs += [(k, m, s) for m in ("base", "no_fund", "half_fund", "equal", "fixed_45_45_10", "equal_nofund", "king_only", "rev24_only", "fund_only") for s in ("d30", "S0")]
    for k in ("K1", "K3"): jobs += [(k, m, s) for m in ("base", "no_fund", "half_fund") for s in ("d30", "S0")]
    jobs += [("K2", m, s) for m in ("base", "no_fund", "half_fund", "equal", "fixed_45_45_10", "equal_nofund", "king_only") for s in ("d30", "S0")]
    t1 = time.time(); chains = {}
    with Pool(min(12, len(jobs))) as pool:
        for key, r in pool.imap_unordered(_chain_job, jobs):
            chains[key] = r; log("chain", key, len(r["ts"]), "skipped", r["skipped"], "fires", r["fires"], round(time.time() - t1), "s")
    R["chain_meta"] = {"_".join(k): {"n_rec": int(len(v["ts"])), "skipped": int(v["skipped"]), "fires": int(v["fires"]), "w3_mean": [round(float(x), 4) for x in v["w3"].mean(0)]} for k, v in chains.items()}
    # R1: K0 base d30 ≡ WA 权重
    WZ = np.load(INPUTS["wa_weights_Wb_d30"], allow_pickle=True); wts = WZ["ts"].astype(np.int64) if "ts" in WZ.files else WZ[WZ.files[0]]
    r0 = chains[("K0", "base", "d30")]; cm = np.intersect1d(r0["ts"], wts); wi = np.searchsorted(wts, cm); ci = np.searchsorted(r0["ts"], cm)
    Wwa = WZ["W"] if "W" in WZ.files else WZ[WZ.files[1]]
    dw = np.abs(Wwa[wi].astype(np.float64) - r0["W"][ci].astype(np.float64))
    R["receipt_R1"] = {"n_common": int(len(cm)), "maxabs_dw": float(dw.max()), "mean_abs_dw": float(dw.mean()), "wa_npz_keys": list(WZ.files)}
    log("RECEIPT R1 weights", R["receipt_R1"])
    # accounting
    ajobs = [("_".join(k), v["ts"], v["W"], v["WL"]) for k, v in chains.items()]
    ACC = {}
    with Pool(12) as pool:
        for name, a in pool.imap_unordered(_account_job, ajobs):
            ACC[name] = a; log("accounted", name, "net@2 sharpe main", a["summ"]["2022-01..2026-06"]["net_at_gross2"]["sharpe_anchor"])
    R["summary"] = {k: v["summ"] for k, v in ACC.items()}
    R["receipt_R1"]["K0_base_d30_sharpe_main"] = ACC["K0_base_d30"]["summ"]["2022-01..2026-06"]["net_at_gross2"]["sharpe_anchor"]
    R["receipt_R1"]["K0_no_fund_d30_sharpe_main"] = ACC["K0_no_fund_d30"]["summ"]["2022-01..2026-06"]["net_at_gross2"]["sharpe_anchor"]
    R["receipt_R1"]["pass"] = bool(R["receipt_R1"]["maxabs_dw"] < 1e-6 and abs(R["receipt_R1"]["K0_base_d30_sharpe_main"] - 1.668) < 0.005 and abs(R["receipt_R1"]["K0_no_fund_d30_sharpe_main"] - 0.664) < 0.005)
    log("RECEIPT R1", R["receipt_R1"])
    # deltas(配对块自助, 主跨度 2022-01..2026-06 与 FULL)
    def common(n1, n2, key="net_g2"):
        a = ACC[n1]; b_ = ACC[n2]; cm = np.intersect1d(a["ts"], b_["ts"]); return a[key][np.searchsorted(a["ts"], cm)], b_[key][np.searchsorted(b_["ts"], cm)], cm
    def delta(n1, n2):
        x, y, cm = common(n1, n2); m26 = cm <= T_END_MAIN; yr = yr_of(cm)
        out = {"n": int(len(cm)), "main_2022-01..2026-06": boot_delta_sharpe(x[m26], y[m26]), "FULL": boot_delta_sharpe(x, y), "2024-26": boot_delta_sharpe(x[(yr >= 2024) & m26], y[(yr >= 2024) & m26]),
               "sharpe_x_main": round(sharpe_a(x[m26]), 3), "sharpe_y_main": round(sharpe_a(y[m26]), 3), "corr_main": round(float(np.corrcoef(x[m26], y[m26])[0, 1]), 4),
               "by_year_delta_sharpe": {int(yy): round(sharpe_a(x[yr == yy]) - sharpe_a(y[yr == yy]), 3) for yy in sorted(set(yr.tolist()))}}
        return out
    R["deltas"] = {}
    pairs = [("K2_no_fund_d30", "K0_no_fund_d30"), ("K1_no_fund_d30", "K0_no_fund_d30"), ("K3_no_fund_d30", "K0_no_fund_d30"), ("K2_no_fund_d30", "K1_no_fund_d30"),
             ("K2_base_d30", "K0_base_d30"), ("K1_base_d30", "K0_base_d30"), ("K3_base_d30", "K0_base_d30"), ("K2_base_d30", "K1_base_d30"),
             ("K2_half_fund_d30", "K0_half_fund_d30"), ("K0_no_fund_d30", "K0_base_d30"), ("K2_no_fund_d30", "K2_base_d30"), ("K1_no_fund_d30", "K1_base_d30"), ("K3_no_fund_d30", "K3_base_d30"),
             ("K0_equal_d30", "K0_base_d30"), ("K0_fixed_45_45_10_d30", "K0_base_d30"), ("K0_equal_nofund_d30", "K0_equal_d30"), ("K0_equal_nofund_d30", "K0_fixed_45_45_10_d30"),
             ("K2_equal_d30", "K2_base_d30"), ("K2_equal_nofund_d30", "K2_equal_d30"), ("K2_equal_nofund_d30", "K2_fixed_45_45_10_d30"),
             ("K2_king_only_d30", "K0_king_only_d30"), ("K2_no_fund_S0", "K0_no_fund_S0"), ("K2_base_S0", "K0_base_S0"), ("K2_no_fund_d30", "K2_no_fund_S0"), ("K0_no_fund_d30", "K0_no_fund_S0")]
    for n1, n2 in pairs:
        if n1 in ACC and n2 in ACC: R["deltas"][f"{n1}__minus__{n2}"] = delta(n1, n2)
    # C: 配权归因 —— 腿份额(WA 可加分解) + w3_fund 逐年 + 去 fund 腿 Δ
    def leg_share(name, yrmask_fn):
        a = ACC[name]; yr = yr_of(a["ts"]); msk = yrmask_fn(yr) & (a["ts"] <= T_END_MAIN); tot = float(a["net_g2"][msk].sum())
        return {leg: round(float(a["legs_g2"][leg][msk].sum() / tot), 3) if abs(tot) > 1e-9 else None for leg in ("king", "rev24", "fund")} | {"book_net_g2_mean": round(float(a["net_g2"][msk].mean()), 4)}
    R["C_allocation"] = {}
    for king in ("K0", "K2"):
        for mode, nf in (("base", "no_fund"), ("equal", "equal_nofund"), ("fixed_45_45_10", "equal_nofund")):
            nm = f"{king}_{mode}_d30"; nfn = f"{king}_{nf}_d30"
            if nm not in ACC: continue
            ch = chains[(king, mode, "d30")]; w3 = ch["w3"]; yrw = yr_of(ch["ts"])
            R["C_allocation"][nm] = {"sharpe_main": ACC[nm]["summ"]["2022-01..2026-06"]["net_at_gross2"]["sharpe_anchor"], "by_year_sharpe": ACC[nm]["summ"]["2022-01..2026-06"]["net_at_gross2"]["by_year_sharpe"],
                                    "leg_share_2022_26": leg_share(nm, lambda y: y >= 2022), "leg_share_2024_26": leg_share(nm, lambda y: y >= 2024),
                                    "w3_mean_by_year": {int(y): [round(float(x), 3) for x in w3[yrw == y].mean(0)] for y in sorted(set(yrw.tolist()))}, "w3_fund_mean_2025_26": round(float(w3[yrw >= 2025, 2].mean()), 3),
                                    "delta_sharpe_nofund_minus_this": R["deltas"].get(f"{nfn}__minus__{nm}", {}).get("main_2022-01..2026-06")}
    # 冻结读法 C
    try:
        msh = R["C_allocation"]["K0_base_d30"]; eq = R["C_allocation"]["K0_equal_d30"]
        d_msh = msh["delta_sharpe_nofund_minus_this"]["mean"]; d_eq = eq["delta_sharpe_nofund_minus_this"]["mean"]
        R["C_verdict"] = {"w3_fund_2025_26_msharpe": msh["w3_fund_mean_2025_26"], "cond_i_w3fund_ge_0.40": bool(msh["w3_fund_mean_2025_26"] >= 0.40), "dS_nofund_msharpe": d_msh, "dS_nofund_equal": d_eq,
                          "cond_ii_equal_loss_le_half": bool(abs(d_eq) <= 0.5 * abs(d_msh)), "allocation_is_main_cause": bool(msh["w3_fund_mean_2025_26"] >= 0.40 and abs(d_eq) <= 0.5 * abs(d_msh))}
    except Exception as e:
        R["C_verdict_error"] = repr(e)
    # 阶段判据
    s2 = ACC["K2_no_fund_d30"]["summ"]["2022-01..2026-06"]["net_at_gross2"]; by = s2["by_year_sharpe"]; nn = sum(1 for v in by.values() if v >= 0)
    R["stage_criterion"] = {"arm": "K2_no_fund_d30 (ablated king + rev24, msharpe 两腿, d30, 净@2, 2022-01..2026-06)", "sharpe": s2["sharpe_anchor"], "sharpe_CI95": s2["sharpe_CI95_blk42"], "by_year_sharpe": by, "years_nonneg": nn,
                            "pass": bool(s2["sharpe_anchor"] >= 1.0 and nn >= 4), "gap_to_1.0": round(1.0 - s2["sharpe_anchor"], 3)}
    s3 = ACC["K3_no_fund_d30"]["summ"]["2022-01..2026-06"]["net_at_gross2"]; by3 = s3["by_year_sharpe"]
    R["stage_criterion_K3_secondary"] = {"sharpe": s3["sharpe_anchor"], "sharpe_CI95": s3["sharpe_CI95_blk42"], "by_year_sharpe": by3, "years_nonneg": sum(1 for v in by3.values() if v >= 0), "pass_two_gates": bool(s3["sharpe_anchor"] >= 1.0 and sum(1 for v in by3.values() if v >= 0) >= 4)}
    # 缺口分解
    S = lambda n: ACC[n]["summ"]["2022-01..2026-06"]["net_at_gross2"]["sharpe_anchor"]
    R["gap_decomposition"] = {"S_nofund_K2": S("K2_no_fund_d30"), "S_nofund_K0": S("K0_no_fund_d30"), "king_ablation_cost(S_nofund_K0 - S_nofund_K2)": round(S("K0_no_fund_d30") - S("K2_no_fund_d30"), 3),
                              "fund_leg_absence(S_base_K0 - S_nofund_K0)": round(S("K0_base_d30") - S("K0_no_fund_d30"), 3), "king_only_K0": S("K0_king_only_d30"), "king_only_K2": S("K2_king_only_d30"), "rev24_only": S("K0_rev24_only_d30"), "fund_only": S("K0_fund_only_d30"),
                              "S_base_K0": S("K0_base_d30"), "S_base_K2": S("K2_base_d30"), "S_base_K1": S("K1_base_d30"), "S_nofund_K1": S("K1_no_fund_d30"), "S_nofund_K3": S("K3_no_fund_d30"), "S_base_K3": S("K3_base_d30")}
    # 训练阶段结果并入
    R["train"] = json.load(open(INPUTS["train_json"])); R["fea_report"] = json.load(open(f"{F1}/fea_report.json")); R["cache_report"] = json.load(open(f"{F1}/cache_report.json"))
    json.dump(R, open(f"{F1}/f1_king_funding_ablation_2026-08-22.json", "w"), indent=1, default=lambda o: float(o) if isinstance(o, (np.floating, np.integer)) else str(o))
    np.savez_compressed(f"{F1}/f1_series.npz", **{f"{k}__ts": v["ts"] for k, v in ACC.items()}, **{f"{k}__net_g2": v["net_g2"].astype(np.float32) for k, v in ACC.items()},
                        **{f"{k}__legs_g2": np.stack([v["legs_g2"][l] for l in ("king", "rev24", "fund")]).astype(np.float32) for k, v in ACC.items()},
                        **{"_".join(k) + "__w3": v["w3"].astype(np.float32) for k, v in chains.items() if k[1] in ("base", "no_fund", "half_fund")}, **{"_".join(k) + "__w3ts": v["ts"] for k, v in chains.items() if k[1] in ("base", "no_fund", "half_fund")})
    log("BOOK_DONE", "stage_criterion", R["stage_criterion"], "C_verdict", R.get("C_verdict"), "gap", R["gap_decomposition"])

if __name__ == "__main__":
    st = sys.argv[1] if len(sys.argv) > 1 else "all"
    if st in ("cache", "all"): stage_cache()
    if st in ("fea", "all"): stage_fea()
    if st in ("train", "all"): stage_train()
    if st in ("book", "all"): stage_book()
