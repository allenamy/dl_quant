"""DLW · 目标 / 锚 / 成员 唯一真相源 @jpline(2026-08-22, Session 6737834a-DLW)。
预注册: multi_asset/exports/eda/PREREG_RESULT_DLW_xattn_2026-08-22.md §P.1(冻结段 SHA256 33f066c9…64577, commit 7acda02, 先于任何数字)。
产物: /mnt/storage/private/work_hsy/dlw_2026-08-22/data/dlw_targets.npz
      (E_ts / E_row / members(object) / y4s / YR4s / YRZ / yrs / qvk / btcv / has_panel / symbols / meta_json)
      + results/dlw_targets_report.json(常数、输入 SHA、锚数、对齐自检、结构断言)。
冻结约定(P.1):
  缓存 ts = bar 收盘时刻; 锚行 E = ts % 14400 == 0 且 E ≥ 576 且 E + 48 ≤ TT − 1。
  成员统计窗(覆盖/波动/量能/BTC 波动) rows [max(E−2016, 0), E)(旧装置 pod_kcurve.py 逐字, 使成员集与 K 曲线装置同构)。
  目标 y4s = Π_{k=1..48}(1 + ret5[E+k]) − 1 = 持仓窗 (N, N+4h] 简单持有收益(缺 bar 记 0, 有数 bar < 46 ⇒ NaN)。
  残差 YR4s = y4s − X β: X = 六因子 {f_rev_4h, f_rev_24h, f_vol_7d, f_range_24h, f_mom_7d, f_fund_ema} 在 wide_panel_4h_v1 锚行的成员内秩 z
  (缺失 ⇒ 0), 岭 λ=1e-3, 有数成员 ≥ 60 才回归(DESIGN_wide_book_v1 §5 逐字)。
  标签 YRZ = 成员内 YR4s 秩线性缩放到 [−0.5, 0.5]。
结构断言: 目标行窗 = [E+1, E+48](min_target_row_offset = +1); 输入行窗(由 dlw_features.py / dlw_train.py 各自断言)≤ E。
用法 @jpline: python dlw_targets.py
"""
import os, sys, json, time, hashlib
import numpy as np
from scipy.stats import rankdata, spearmanr

ROOT = "/mnt/storage/private/work_hsy"
CACHE = os.environ.get("DLWT_CACHE", "/workspace/data/dlnative_5m_wide829_f16_ext.npz")  # EXT_ENV
PANEL = os.environ.get("DLWT_PANEL", "/workspace/data/wide_panel_4h_v2ext.npz")  # EXT_ENV
OUT = os.environ.get("DLWT_OUT", "/workspace/dlw_ext")  # EXT_ENV
W = 576; FWD = 48; TRAIL = 2016; NTOP = 400; MIN_MEM = 50; MIN_FIN = 46
F6_KEYS = ["f_rev_4h", "f_rev_24h", "f_vol_7d", "f_range_24h", "f_mom_7d", "f_fund_ema"]; LAM = 1e-3; MIN_RES = 60
CHN_EXPECT = ["ret5", "range", "cpos", "log_qv", "log_cnt", "log_avgsz", "tbf"]
T0 = time.time()


def log(*a):
    print(f"[{time.time()-T0:7.1f}s]", *a, flush=True)


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 24), b""):
            h.update(ch)
    return h.hexdigest()


def spear(x, y):
    ok = np.isfinite(x) & np.isfinite(y)
    return spearmanr(x[ok], y[ok]).correlation if ok.sum() >= 10 else np.nan


def xz(v):
    """成员内秩 z ∈ [−0.5, 0.5], 缺失 ⇒ 0(中性)。"""
    ok = np.isfinite(v); out = np.zeros(len(v), np.float64); n = int(ok.sum())
    if n >= 10:
        r = rankdata(v[ok]); out[ok] = (r - (n + 1) / 2) / max(n - 1, 1)
    return out, ok


def main():
    os.makedirs(f"{OUT}/data", exist_ok=True); os.makedirs(f"{OUT}/results", exist_ok=True)
    rep = {"self_sha256": sha(os.path.abspath(__file__)), "const": dict(W=W, FWD=FWD, TRAIL=TRAIL, NTOP=NTOP, MIN_MEM=MIN_MEM, MIN_FIN=MIN_FIN,
           F6_KEYS=F6_KEYS, LAM=LAM, MIN_RES=MIN_RES, target_row_window="[E+1, E+48]", member_stat_window="[max(E-2016,0), E)",
           prereg_sha="33f066c9460587864866e4f31afb72c24ae93c98183fc779c12aa0af70764577", prereg_commit="7acda02")}
    log("sha256 inputs ..."); rep["input_sha256"] = {"cache": sha(CACHE), "panel": sha(PANEL)}
    Z = np.load(CACHE, allow_pickle=True)
    CTS = Z["ts"].astype(np.int64); CD = Z["data"]; syms = [str(s) for s in Z["symbols"]]; ch = [str(c) for c in Z["ch"]]
    assert ch == CHN_EXPECT, ch
    NW = len(syms); TT = CD.shape[0]; BTC_T = syms.index("BTCUSDT")
    log(f"cache {TT}x{NW}x{CD.shape[2]} ts {CTS[0]}..{CTS[-1]}")
    assert np.all(np.diff(CTS) == 300), "缓存 ts 非等距 300s"
    r5 = CD[:, :, 0].astype(np.float32)
    fin = np.isfinite(r5)
    r5z = np.where(fin, r5, 0).astype(np.float32)
    qvz = np.where(np.isfinite(CD[:, :, 3]), CD[:, :, 3], 0).astype(np.float32)
    z1 = np.zeros((1, NW))
    CS_f = np.concatenate([z1.astype(np.int32), np.cumsum(fin, 0, dtype=np.int32)])
    CS_r = np.concatenate([z1, np.cumsum(r5z, 0, dtype=np.float64)])
    CS_r2 = np.concatenate([z1, np.cumsum(r5z.astype(np.float64) ** 2, 0)])
    CS_L = np.concatenate([z1, np.cumsum(np.log1p(r5z.astype(np.float64)), 0)])
    CS_q = np.concatenate([z1, np.cumsum(qvz, 0, dtype=np.float64)])
    del r5, r5z, qvz, fin
    log("cumsums done")
    grid = np.where(CTS % 14400 == 0)[0]
    grid = grid[(grid >= W) & (grid + FWD <= TT - 1)]
    E = grid; S = np.maximum(E - TRAIL, 0)
    nfin = np.maximum(CS_f[E] - CS_f[S], 1)
    covr = (CS_f[E] - CS_f[S]) / np.maximum(E - S, 1)[:, None]
    qvm = (CS_q[E] - CS_q[S]) / nfin
    rs_ = CS_r[E] - CS_r[S]
    vstd = np.sqrt(np.maximum((CS_r2[E] - CS_r2[S]) / nfin - (rs_ / nfin) ** 2, 0))
    nb = np.maximum(E - S, 1).astype(np.float64)
    btcv = np.sqrt(np.maximum((CS_r2[E, BTC_T] - CS_r2[S, BTC_T]) / nb - ((CS_r[E, BTC_T] - CS_r[S, BTC_T]) / nb) ** 2, 0))
    # ---- 目标: 行 [E+1, E+48] 复利(结构断言: 起点 E+1)
    lo_t = E + 1; hi_t = E + FWD + 1          # CS 半开区间 [lo_t, hi_t) = rows E+1..E+48
    assert int(lo_t.min() - E.min()) == 1 and np.all(hi_t - 1 - E == FWD) and hi_t.max() <= TT
    y4n = CS_f[hi_t] - CS_f[lo_t]
    y4s = np.expm1(CS_L[hi_t] - CS_L[lo_t]).astype(np.float32)
    y4s[y4n < MIN_FIN] = np.nan
    # 旧口径 y4(对照/对齐自检用, 不入任何训练): rows [E, E+47] 简单和
    y4old = (CS_r[E + FWD] - CS_r[E]).astype(np.float32); y4old[(CS_f[E + FWD] - CS_f[E]) < MIN_FIN] = np.nan
    del CS_f, CS_r, CS_r2, CS_L, CS_q, rs_
    MS, keep = [], []
    for i in range(len(E)):
        ok = (covr[i] >= 0.95) & (vstd[i] >= 1e-4) & np.isfinite(y4s[i])
        m = np.where(ok)[0]
        if len(m) > NTOP:
            m = np.sort(m[np.argsort(-qvm[i, m])[:NTOP]])
        if len(m) >= MIN_MEM:
            MS.append(m); keep.append(i)
    keep = np.array(keep)
    E = E[keep]; y4s = y4s[keep]; y4old = y4old[keep]; qvk = qvm[keep].astype(np.float32); btcv = btcv[keep].astype(np.float32)
    E_ts = CTS[E]
    yrs = np.array([time.gmtime(int(t)).tm_year for t in E_ts])
    nA = len(E); memn = np.array([len(m) for m in MS])
    log(f"anchors {nA} 平均成员 {memn.mean():.0f} (≥360: {(memn>=360).sum()}) 年份 {dict(zip(*np.unique(yrs, return_counts=True)))}")
    # ---- 残差目标(六因子, 面板锚行 ts = N)
    PW = np.load(PANEL, allow_pickle=True)
    assert [str(s) for s in PW["symbols"]] == syms, "面板符号顺序 ≠ 缓存"
    pw_ts = PW["ts"].astype(np.int64); pw_row = {int(t): j for j, t in enumerate(pw_ts)}
    F6 = [PW[k].astype(np.float32) for k in F6_KEYS]; PY4 = PW["Y4"].astype(np.float32)
    YR4s = np.full((nA, NW), np.nan, np.float32); YRZ = np.full((nA, NW), np.nan, np.float32)
    has_panel = np.zeros(nA, bool); n_res = 0; r2s = []
    for i in range(nA):
        j = pw_row.get(int(E_ts[i]))
        if j is None:
            continue
        has_panel[i] = True
        m = MS[i]; y = y4s[i, m].astype(np.float64)
        X = np.zeros((len(m), 6))
        for c in range(6):
            X[:, c], _ = xz(F6[c][j, m])
        okrow = np.isfinite(y)
        if okrow.sum() < MIN_RES:
            continue
        Xo, yo = X[okrow], y[okrow]
        beta = np.linalg.solve(Xo.T @ Xo + LAM * np.eye(6), Xo.T @ yo)
        res = yo - Xo @ beta
        YR4s[i, m[okrow]] = res.astype(np.float32); n_res += 1
        vy = yo.var(); r2s.append(1 - res.var() / vy if vy > 0 else np.nan)
        rr = rankdata(res); YRZ[i, m[okrow]] = ((rr - (len(rr) + 1) / 2) / max(len(rr) - 1, 1)).astype(np.float32)
    log(f"YR4s 完成 {n_res}/{nA} 锚(有面板行 {has_panel.sum()}), 六因子值空间 R² 中位 {np.nanmedian(r2s):.4f}")
    # ---- 对齐自检: 本装置 y4s(窗 (N,N+4h]) vs 面板 Y4(旧窗 [N−5m,N+3h55m] 对数和) 在同行应 ≫ 相邻行
    chk = {-1: [], 0: [], 1: []}
    for i in range(60, nA - 60, max(nA // 200, 1)):
        j = pw_row.get(int(E_ts[i]))
        if j is None or j - 1 < 0 or j + 1 >= len(pw_ts):
            continue
        m = MS[i]
        for off in (-1, 0, 1):
            chk[off].append(spear(y4s[i, m], PY4[j + off, m]))
    c0, cm, cp = (float(np.nanmedian(chk[o])) for o in (0, -1, 1))
    log(f"对齐自检(y4s vs 面板旧 Y4): @0 {c0:+.3f} @-1 {cm:+.3f} @+1 {cp:+.3f} (n={len(chk[0])})")
    assert c0 > 0.8 and c0 > cm and c0 > cp, "对齐自检 FAIL"
    # 新旧目标差(同锚同名): 量级记录
    d = (y4s - y4old)
    rep["target_vs_old"] = {"median_abs_diff_bps": float(np.nanmedian(np.abs(d)) * 1e4), "mean_diff_bps": float(np.nanmean(d) * 1e4),
                            "spearman_same_row_median": c0, "spearman_prev_row": cm, "spearman_next_row": cp}
    meta = dict(rep["const"], n_anchors=int(nA), mean_members=float(memn.mean()), n_has_panel=int(has_panel.sum()), n_res=int(n_res),
                years={str(k): int(v) for k, v in zip(*np.unique(yrs, return_counts=True))}, cache=CACHE, panel=PANEL)
    np.savez(f"{OUT}/data/dlw_targets.npz", E_ts=E_ts, E_row=E, members=np.array(MS, dtype=object), y4s=y4s, YR4s=YR4s, YRZ=YRZ,
             yrs=yrs, qvk=qvk, btcv=btcv, has_panel=has_panel, symbols=np.array(syms), y4old=y4old, meta_json=json.dumps(meta))
    rep.update(meta); rep["targets_sha256"] = sha(f"{OUT}/data/dlw_targets.npz")
    rep["assert"] = {"min_target_row_offset": 1, "max_target_row_offset": FWD, "ts_step_300": True, "align_check_pass": True}
    json.dump(rep, open(f"{OUT}/results/dlw_targets_report.json", "w"), indent=1)
    log("TARGETS_DONE", json.dumps({k: rep[k] for k in ("n_anchors", "mean_members", "n_res", "years", "target_vs_old")}))


if __name__ == "__main__":
    main()
