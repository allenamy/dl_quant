"""DLW · D2 多视界多任务臂的辅助目标 y12 @jpline(2026-08-22, Session 6737834a-DLW)。
预注册: multi_asset/exports/eda/PREREG_RESULT_DLW_multihorizon_2026-08-22.md §P(冻结段 SHA 见该文/commit)。
与 dlw_targets.npz 同锚同成员(断言 E_ts 逐位相等; 成员/y4s/YR4s/YRZ 一律沿用原文件, 本文件只追加 12h 量):
  y12s  = Π_{k=1..144}(1 + ret5[E+k]) − 1(持仓窗 (N, N+12h] 简单持有收益; 缺 bar 记 0; 有数 bar < 138 ⇒ NaN; E+144 ≤ TT−1 否则 NaN)
  YR12s = y12s − X β(X = 同一锚行六因子 xsec 秩 z, 岭 1e-3, ≥60 成员; 与 YR4s 同基同锚)
  YRZ12 = 成员内 YR12s 秩 → [−0.5, 0.5](辅助头标签)。
产物: data/dlw_targets_y12.npz(E_ts / y12s / YR12s / YRZ12 / meta_json)+ results/dlw_targets_y12_report.json。
用法 @jpline: python dlw_targets_y12.py
"""
import os, json, time, hashlib
import numpy as np
from scipy.stats import rankdata, spearmanr

ROOT = "/mnt/storage/private/work_hsy"
CACHE = f"{ROOT}/w3lane/kcurve/data/dlnative_5m_wide829_f16.npz"
PANEL = f"{ROOT}/w3lane/kcurve/data/wide_panel_4h_v1.npz"
OUT = f"{ROOT}/dlw_2026-08-22"
FWD12 = 144; MIN_FIN12 = 138
F6_KEYS = ["f_rev_4h", "f_rev_24h", "f_vol_7d", "f_range_24h", "f_mom_7d", "f_fund_ema"]; LAM = 1e-3; MIN_RES = 60
T0 = time.time()


def log(*a):
    print(f"[{time.time()-T0:7.1f}s]", *a, flush=True)


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 24), b""):
            h.update(ch)
    return h.hexdigest()


def xz(v):
    ok = np.isfinite(v); out = np.zeros(len(v), np.float64); n = int(ok.sum())
    if n >= 10:
        r = rankdata(v[ok]); out[ok] = (r - (n + 1) / 2) / max(n - 1, 1)
    return out


def main():
    TG = np.load(f"{OUT}/data/dlw_targets.npz", allow_pickle=True)
    E = TG["E_row"].astype(np.int64); E_ts = TG["E_ts"].astype(np.int64); MS = list(TG["members"]); syms = [str(s) for s in TG["symbols"]]
    y4s = TG["y4s"]; nA = len(E); NW = len(syms)
    Z = np.load(CACHE, allow_pickle=True)
    CD = Z["data"]; CTS = Z["ts"].astype(np.int64)
    assert [str(s) for s in Z["symbols"]] == syms and np.array_equal(CTS[E], E_ts)
    TT = CD.shape[0]
    r5 = CD[:, :, 0].astype(np.float32); fin = np.isfinite(r5); r5z = np.where(fin, r5, 0).astype(np.float64)
    del CD
    z1 = np.zeros((1, NW))
    CS_f = np.concatenate([z1.astype(np.int32), np.cumsum(fin, 0, dtype=np.int32)])
    CS_L = np.concatenate([z1, np.cumsum(np.log1p(r5z), 0)])
    del r5, fin, r5z
    lo = E + 1; hi = np.minimum(E + FWD12 + 1, TT)                 # rows [E+1, E+144]
    valid = (E + FWD12 <= TT - 1)
    y12n = CS_f[hi] - CS_f[lo]
    y12s = np.expm1(CS_L[hi] - CS_L[lo]).astype(np.float32)
    y12s[(y12n < MIN_FIN12) | (~valid)[:, None]] = np.nan
    del CS_f, CS_L
    # 只保留成员格(与 y4s 同掩码), 其余 NaN
    mask = np.zeros((nA, NW), bool)
    for i in range(nA):
        mask[i, MS[i]] = True
    y12s[~mask] = np.nan
    PW = np.load(PANEL, allow_pickle=True)
    pw_row = {int(t): j for j, t in enumerate(PW["ts"].astype(np.int64))}
    F6 = [PW[k].astype(np.float32) for k in F6_KEYS]
    YR12s = np.full((nA, NW), np.nan, np.float32); YRZ12 = np.full((nA, NW), np.nan, np.float32); n_res = 0
    for i in range(nA):
        j = pw_row.get(int(E_ts[i]))
        if j is None:
            continue
        m = MS[i]; y = y12s[i, m].astype(np.float64)
        X = np.stack([xz(F6[c][j, m]) for c in range(6)], 1)
        okrow = np.isfinite(y)
        if okrow.sum() < MIN_RES:
            continue
        Xo, yo = X[okrow], y[okrow]
        beta = np.linalg.solve(Xo.T @ Xo + LAM * np.eye(6), Xo.T @ yo)
        res = yo - Xo @ beta
        YR12s[i, m[okrow]] = res.astype(np.float32); n_res += 1
        rr = rankdata(res); YRZ12[i, m[okrow]] = ((rr - (len(rr) + 1) / 2) / max(len(rr) - 1, 1)).astype(np.float32)
    # 自检: y12s 与 y4s 同锚同名秩相关应为正且 < 1; 与 y4s 相关 ≈ sqrt(4/12) 量级
    cs = [spearmanr(y12s[i, MS[i]], y4s[i, MS[i]], nan_policy="omit").correlation for i in range(0, nA, max(nA // 200, 1))]
    meta = dict(n_anchors=int(nA), n_res12=int(n_res), FWD12=FWD12, MIN_FIN12=MIN_FIN12, n_valid_anchors=int(valid.sum()),
                spearman_y12_vs_y4_median=float(np.nanmedian(cs)), targets_sha256=sha(f"{OUT}/data/dlw_targets.npz"), cache_sha256=sha(CACHE), panel_sha256=sha(PANEL),
                self_sha256=sha(os.path.abspath(__file__)), target12_row_window="[E+1, E+144]")
    np.savez(f"{OUT}/data/dlw_targets_y12.npz", E_ts=E_ts, y12s=y12s, YR12s=YR12s, YRZ12=YRZ12, meta_json=json.dumps(meta))
    meta["y12_sha256"] = sha(f"{OUT}/data/dlw_targets_y12.npz")
    json.dump(meta, open(f"{OUT}/results/dlw_targets_y12_report.json", "w"), indent=1)
    log("TARGETS12_DONE", json.dumps(meta))


if __name__ == "__main__":
    main()
