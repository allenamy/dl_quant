"""F-8 · P2 特征数量标度曲线臂 @jpline CPU(2026-08-22, Session 6737834a-F8)。
预注册: PREREG_RESULT_F8_higher_order_features_2026-08-22.md §P2(冻结段 2 SHA256 f2a5b9f5…b76e7, commit 64c945e, 先于任何数字)。
语法(§P2.1, 嵌套前缀): base 82 | T1 更多窗口 64 | T2 时序阶(基窗)120 | T3 跨窗差+EMA 差 30 | T4 通道间二阶 56 | T5 三阶 64 | T6 横截面/状态 120 | T7 时序阶(新窗)64
档: S150 = base+T1 (146); S300 = base+T1+T2+T3 (296); S600 = 全部 (600); SX = base+T6+T4 (258)。
阶段: build → data/f8_scale518.npz; run → results/f8s_icpa_<model>.npz(+ preds 不存); judge → results/f8_scaling_curve_2026-08-22.json
模型: ridge_grid(α ∈ {0.1,1,10,100,1e3,1e4}, 内验证 = 训练锚最后 15%, 选后全训练重拟合; 块式 Gram 累加)/ ridge_fixed(α=1, 仅 base 对照)/ lgbm(dlw_g0 参数不调)。
读数: OOS 逐锚残差/原始秩 IC; 训练锚内 IC(过拟合度 = 训练 − OOS); 选中 α; 有效维数(30 万行标准化抽样 PCA 95%)+ 条件数; Δ vs 82(配对 t + 60 锚块自助 95% CI)。
用法: python -u f8_scaling_curve.py build|run|judge [--models ridge_grid,lgbm] [--arms base,S150,...]
"""
import os, sys, json, time, hashlib, argparse
import numpy as np
import pandas as pd
from scipy.stats import rankdata, spearmanr

ROOT = "/mnt/storage/private/work_hsy"
DLW = f"{ROOT}/dlw_2026-08-22"
CACHE = f"{ROOT}/w3lane/kcurve/data/dlnative_5m_wide829_f16.npz"
TARGETS = f"{DLW}/data/dlw_targets.npz"; FEA82 = f"{DLW}/data/dlw_fea82.npz"; G0JSON = f"{DLW}/results/dlw_g0.json"
OUT = f"{ROOT}/f8_2026-08-22"
PREREG2_SHA = "f2a5b9f5c296ab8e264786d8ee9888b459f601e03f423e9faab00347a36b76e7"; PREREG2_COMMIT = "64c945e"
YEARS = (2023, 2024, 2025, 2026); EMBARGO = 60; NJOBS = 8
ALPHAS = (0.1, 1.0, 10.0, 100.0, 1000.0, 10000.0); VAL_FRAC = 0.15
LGB_PARAMS = dict(n_estimators=400, learning_rate=0.05, num_leaves=63, subsample=0.8, colsample_bytree=0.8, random_state=0, n_jobs=NJOBS, verbose=-1)
CHN = ["ret5", "range", "cpos", "log_qv", "log_cnt", "log_avgsz", "tbf"]
STATS = CHN + ["vol"]                       # 8 基统计: ret5 窗和 / 其余窗均 / vol
W0 = (48, 288, 864, 2016, 8640); W1 = (24, 96, 576, 4320)
CHUNK = 64; ROWBLK = 200000
T0 = time.time()


def log(*a):
    print(f"[{time.time()-T0:7.1f}s]", *a, flush=True)


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 24), b""):
            h.update(ch)
    return h.hexdigest()


def spear(x, y, nmin=30):
    ok = np.isfinite(x) & np.isfinite(y)
    if ok.sum() < nmin:
        return np.nan
    return spearmanr(x[ok], y[ok]).correlation


def nanmean(a):
    a = np.asarray(a, float)
    return float(np.nanmean(a)) if np.isfinite(a).any() else float("nan")


def paired(d):
    d = np.asarray(d, float); d = d[np.isfinite(d)]
    if len(d) < 3:
        return {"mean": float("nan"), "t": float("nan"), "n": int(len(d))}
    return {"mean": float(d.mean()), "t": float(d.mean() / (d.std(ddof=1) / np.sqrt(len(d)) + 1e-12)), "n": int(len(d))}


def cs(a):
    return np.concatenate([np.zeros((1, a.shape[1])), np.cumsum(a, 0, dtype=np.float64)])


def anchor_rank_block(V):
    V = np.asarray(V, np.float64); ok = np.isfinite(V); nok = ok.sum(0)
    R = rankdata(V, axis=0, nan_policy="omit")
    Z = (R - (nok + 1) / 2) / np.maximum(nok - 1, 1); Z[~ok] = 0.0; Z[:, nok < 10] = 0.0
    return Z.astype(np.float32)


def load_targets():
    TG = np.load(TARGETS, allow_pickle=True)
    return dict(E=TG["E_row"].astype(np.int64), E_ts=TG["E_ts"].astype(np.int64), MS=list(TG["members"]), yrs=TG["yrs"].astype(int),
                YRZ=TG["YRZ"], YR4s=TG["YR4s"], y4s=TG["y4s"], btcv=TG["btcv"].astype(np.float64), syms=[str(s) for s in TG["symbols"]])


def load_fea82():
    FE = np.load(FEA82, allow_pickle=True)
    return FE["X"], FE["pair_a"].astype(np.int64), FE["pair_s"].astype(np.int64), [str(n) for n in FE["names"]]


def causal_z(x, win=180, minn=30):
    s = pd.Series(x); mu = s.shift(1).rolling(win, min_periods=minn).mean().values; sd = s.shift(1).rolling(win, min_periods=minn).std().values
    return np.clip(np.nan_to_num((x - mu) / (sd + 1e-12), nan=0.0), -5, 5)


# =====================================================================================
def build():
    T = load_targets(); E = T["E"]; E_ts = T["E_ts"]; nA = len(E); syms = T["syms"]; NW = len(syms)
    X82, pa, ps, n82 = load_fea82(); col = {n: i for i, n in enumerate(n82)}
    st = np.searchsorted(pa, np.arange(nA + 1)); n_pairs = len(pa)
    Z = np.load(CACHE, allow_pickle=True); CD = Z["data"]; CTS = Z["ts"].astype(np.int64)
    assert [str(s) for s in Z["symbols"]] == syms and [str(c) for c in Z["ch"]] == CHN and np.array_equal(CTS[E], E_ts)
    TT = CD.shape[0]; hi = E + 1
    log(f"cache {CD.shape}; pairs {n_pairs}")
    F = {}
    def put(name, arr, chunk):
        if name not in F:
            F[name] = np.full((nA, NW), np.nan, np.float32)
        F[name][:, chunk] = arr.astype(np.float32)
    LAGS = 8
    for c0 in range(0, NW, CHUNK):
        chunk = np.arange(c0, min(c0 + CHUNK, NW)); nc = len(chunk)
        X = {}; FIN = {}
        for ci, cn in enumerate(CHN):
            x = CD[:, chunk, ci].astype(np.float32); f = np.isfinite(x); X[cn] = np.where(f, x, 0).astype(np.float64); FIN[cn] = f
        CS = {cn: cs(X[cn]) for cn in CHN}; CSN = {cn: cs(FIN[cn].astype(np.float64)) for cn in CHN}
        CSr2 = cs(X["ret5"] ** 2)
        def stat_at(s, w, h):
            """统计 s 在窗 [h−w, h) 的值; h 可为任意(nA,) 行上界(半开); 窗不足 1/4 或越界 ⇒ NaN。"""
            lo = h - w; bad = (lo < 0)[:, None]; lo = np.maximum(lo, 0); hh = np.maximum(h, 0)
            if s == "vol":
                n = CSN["ret5"][hh] - CSN["ret5"][lo]; nn = np.maximum(n, 1)
                mu = (CS["ret5"][hh] - CS["ret5"][lo]) / nn; v = np.sqrt(np.maximum((CSr2[hh] - CSr2[lo]) / nn - mu ** 2, 0))
            else:
                n = CSN[s][hh] - CSN[s][lo]; nn = np.maximum(n, 1)
                v = (CS[s][hh] - CS[s][lo]) if s == "ret5" else (CS[s][hh] - CS[s][lo]) / nn
            v = np.where(bad | (n < max(w // 4, 1)), np.nan, v)
            return v
        # T1 值(W1 窗, 秩在 pair 空间做)
        for s in STATS:
            for w in W1:
                put(f"T1:{s}_{w}_v", stat_at(s, w, hi), chunk)
        # T2 / T7: d1, d2, rz
        for s in STATS:
            for w in W0 + W1:
                S0 = stat_at(s, w, hi); S1 = stat_at(s, w, hi - w); S2 = stat_at(s, w, hi - 2 * w)
                d1 = S0 - S1
                lagged = np.stack([stat_at(s, w, hi - k * w) for k in range(1, LAGS + 1)])   # (8, nA, nc)
                mu = np.nanmean(lagged, 0); sd = np.nanstd(lagged, 0); nv = np.isfinite(lagged).sum(0)
                rz = (S0 - mu) / np.maximum(sd, 1e-12); rz[nv < 5] = np.nan
                tier = "T2" if w in W0 else "T7"
                put(f"{tier}:{s}_{w}_d1", d1, chunk); put(f"{tier}:{s}_{w}_rz", rz, chunk)
                if w in W0:
                    put(f"T2:{s}_{w}_d2", d1 - (S1 - S2), chunk)
        # T3 跨窗差 + EMA 差
        for s in STATS:
            a, b = stat_at(s, 48, hi), stat_at(s, 2016, hi); c_, d_ = stat_at(s, 288, hi), stat_at(s, 8640, hi)
            if s == "vol":
                put("T3:vol_48v2016", np.log(np.maximum(a, 1e-12) / np.maximum(b, 1e-12)), chunk); put("T3:vol_288v8640", np.log(np.maximum(c_, 1e-12) / np.maximum(d_, 1e-12)), chunk)
            else:
                put(f"T3:{s}_48v2016", a - b, chunk); put(f"T3:{s}_288v8640", c_ - d_, chunk)
        for cn in CHN:
            df = pd.DataFrame(np.where(FIN[cn], X[cn], np.nan))
            em = {h: df.ewm(halflife=h, min_periods=max(h // 2, 1), ignore_na=True).mean().values[E] for h in (12, 144, 48, 576)}
            put(f"T3:{cn}_ema12v144", em[12] - em[144], chunk); put(f"T3:{cn}_ema48v576", em[48] - em[576], chunk)
            del df
        del X, FIN, CS, CSN, CSr2
        log(f"chunk {c0}-{chunk[-1]} done ({len(F)} feats)")
    del CD, Z
    # ---------- 秩形态列(T1 值→秩, T2, T3, T7)按语法顺序 ----------
    names_T1 = []
    for s in STATS:
        for w in W1:
            names_T1 += [f"T1:{s}_{w}_v", f"T1:{s}_{w}_r"]
    names_T2 = [f"T2:{s}_{w}_{k}" for s in STATS for w in W0 for k in ("d1", "d2", "rz")]
    names_T3 = [f"T3:{s}_48v2016" for s in STATS] + [f"T3:{s}_288v8640" for s in STATS] + [f"T3:{cn}_ema12v144" for cn in CHN] + [f"T3:{cn}_ema48v576" for cn in CHN]
    names_T7 = [f"T7:{s}_{w}_{k}" for s in STATS for w in W1 for k in ("d1", "rz")]
    rank_src = [n[:-2] + "_v" for n in names_T1 if n.endswith("_r")] + names_T2 + names_T3 + names_T7   # 源特征名(值), 目标列 = 秩
    raw_rank = np.stack([F[n][pa, ps] for n in rank_src], 1)   # (n_pairs, 246)
    XRK = np.zeros_like(raw_rank, dtype=np.float32)
    for i in range(nA):
        sl = slice(st[i], st[i + 1]); XRK[sl] = anchor_rank_block(raw_rank[sl])
    rk_index = {n: j for j, n in enumerate(rank_src)}
    T1_vals = np.stack([np.clip(np.nan_to_num(F[f"T1:{s}_{w}_v"][pa, ps], nan=0.0), -1e4, 1e4) for s in STATS for w in W1], 1).astype(np.float32)
    del raw_rank
    # 组装 T1(值/秩交错)
    T1 = np.zeros((n_pairs, 64), np.float32); j = 0
    for s in STATS:
        for w in W1:
            T1[:, j] = T1_vals[:, (STATS.index(s)) * 4 + W1.index(w)]; T1[:, j + 1] = XRK[:, rk_index[f"T1:{s}_{w}_v"]]; j += 2
    T2 = np.stack([XRK[:, rk_index[n]] for n in names_T2], 1)
    T3 = np.stack([XRK[:, rk_index[n]] for n in names_T3], 1)
    T7 = np.stack([XRK[:, rk_index[n]] for n in names_T7], 1)
    # ---------- T4 通道间二阶(w=288/2016 的 8 统计秩两两乘积) ----------
    def r82(s, w):
        nm = f"{s}_{w}_r" if s == "vol" else (f"ret5_sum_{w}_r" if s == "ret5" else f"{s}_mean_{w}_r")
        return X82[:, col[nm]].astype(np.float32)
    T4 = []; names_T4 = []
    for w in (288, 2016):
        R = {s: r82(s, w) for s in STATS}
        for i in range(8):
            for k in range(i + 1, 8):
                T4.append(R[STATS[i]] * R[STATS[k]]); names_T4.append(f"T4:{STATS[i]}x{STATS[k]}_{w}")
    T4 = np.stack(T4, 1)
    # ---------- T5 三阶(w=2016: 平方 + r_i² r_j) ----------
    R = {s: r82(s, 2016) for s in STATS}; T5 = []; names_T5 = []
    for s in STATS:
        T5.append(R[s] ** 2); names_T5.append(f"T5:{s}_sq_2016")
    for i in range(8):
        for k in range(8):
            if i != k:
                T5.append(R[STATS[i]] ** 2 * R[STATS[k]]); names_T5.append(f"T5:{STATS[i]}sq_x_{STATS[k]}_2016")
    T5 = np.stack(T5, 1)
    # ---------- T6 横截面/状态 ----------
    vnames = [n for n in n82 if n.endswith("_v")]; assert len(vnames) == 40
    V = X82[:, [col[n] for n in vnames]].astype(np.float64)
    XZ = np.zeros((n_pairs, 40), np.float32)
    for i in range(nA):
        sl = slice(st[i], st[i + 1]); v = V[sl]; mu = v.mean(0); sd = v.std(0) + 1e-12
        XZ[sl] = np.clip((v - mu) / sd, -5, 5)
    r24v = X82[:, col["ret5_sum_288_v"]].astype(np.float64)
    disp = np.array([np.nanstd(r24v[st[i]:st[i + 1]]) for i in range(nA)]); disp_z = causal_z(disp); btcv_z = causal_z(T["btcv"])
    rnames = [n for n in n82 if n.endswith("_r")]; assert len(rnames) == 40
    RK40 = X82[:, [col[n] for n in rnames]].astype(np.float32)
    T6 = np.concatenate([XZ, RK40 * disp_z[pa][:, None], RK40 * btcv_z[pa][:, None]], 1).astype(np.float32)
    names_T6 = [f"T6:xz_{n[:-2]}" for n in vnames] + [f"T6:{n[:-2]}_x_disp" for n in rnames] + [f"T6:{n[:-2]}_x_btcv" for n in rnames]
    names = names_T1 + names_T2 + names_T3 + names_T4 + names_T5 + names_T6 + names_T7
    Xall = np.clip(np.concatenate([T1, T2, T3, T4, T5, T6, T7], 1), -1e4, 1e4).astype(np.float32)
    assert Xall.shape == (n_pairs, 518) and len(names) == 518, (Xall.shape, len(names))
    tiers = {"T1": (0, 64), "T2": (64, 184), "T3": (184, 214), "T4": (214, 270), "T5": (270, 334), "T6": (334, 454), "T7": (454, 518)}
    arms = {"S150": list(range(0, 64)), "S300": list(range(0, 214)), "S600": list(range(0, 518)), "SX": list(range(334, 454)) + list(range(214, 270))}
    meta = dict(prereg2_sha=PREREG2_SHA, prereg2_commit=PREREG2_COMMIT, self_sha256=sha(os.path.abspath(__file__)), cache_sha256=sha(CACHE), targets_sha256=sha(TARGETS), fea82_sha256=sha(FEA82),
                n_pairs=int(n_pairs), names=names, tiers=tiers, arms_cols=arms, arm_sizes={k: 82 + len(v) for k, v in arms.items()},
                struct="all windows end at hi=E+1 (max row E); lags use hi-k*w; ewm causal; xsec z per anchor; state z shift(1).rolling(180)")
    np.savez(f"{OUT}/data/f8_scale518.npz", X=Xall, pair_a=pa.astype(np.int32), pair_s=ps.astype(np.int16), names=np.array(names), meta_json=json.dumps(meta))
    meta["scale_sha256"] = sha(f"{OUT}/data/f8_scale518.npz")
    json.dump(meta, open(f"{OUT}/results/f8s_build_report.json", "w"), indent=1)
    log("BUILD2_DONE", Xall.shape, meta["arm_sizes"])


# =====================================================================================
def gram_accumulate(X, rows, mu, sd, Y):
    """块式累加 Gram: 返回 G(p+1,p+1), b(p+1)。标准化 clip ±5 + 截距列。"""
    p = X.shape[1]; G = np.zeros((p + 1, p + 1)); b = np.zeros(p + 1)
    for k in range(0, len(rows), ROWBLK):
        idx = rows[k:k + ROWBLK]
        Xs = np.clip((X[idx].astype(np.float64) - mu) / sd, -5, 5); Xa = np.concatenate([Xs, np.ones((len(idx), 1))], 1)
        G += Xa.T @ Xa; b += Xa.T @ Y[idx].astype(np.float64)
    return G, b


def ridge_predict(X, rows, mu, sd, beta):
    out = np.zeros(len(rows), np.float32)
    for k in range(0, len(rows), ROWBLK):
        idx = rows[k:k + ROWBLK]
        Xs = np.clip((X[idx].astype(np.float64) - mu) / sd, -5, 5)
        out[k:k + ROWBLK] = (Xs @ beta[:-1] + beta[-1]).astype(np.float32)
    return out


def per_anchor_ic(P, anchors, YR4s, y4s):
    icr = np.full(len(P), np.nan); icy = np.full(len(P), np.nan)
    for i in anchors:
        icr[i] = spear(P[i], YR4s[i]); icy[i] = spear(P[i], y4s[i])
    return icr, icy


def eff_dim(X, rng):
    idx = np.sort(rng.choice(X.shape[0], min(300000, X.shape[0]), replace=False)); S = X[idx].astype(np.float64)
    S = (S - S.mean(0)) / (S.std(0) + 1e-9); C = S.T @ S / len(S)
    ev = np.sort(np.linalg.eigvalsh(C))[::-1]; ev = np.maximum(ev, 0); cum = np.cumsum(ev) / ev.sum()
    return {"n_cols": int(X.shape[1]), "n95": int(np.searchsorted(cum, 0.95) + 1), "n99": int(np.searchsorted(cum, 0.99) + 1), "cond": float(np.sqrt(ev[0] / max(ev[-1], 1e-12)))}


def run(models, only_arms=None):
    T = load_targets(); yrs = T["yrs"]; YRZ = T["YRZ"]; YR4s = T["YR4s"]; y4s = T["y4s"]; nA, NW = YRZ.shape
    X82, pa, ps, n82 = load_fea82()
    SC = np.load(f"{OUT}/data/f8_scale518.npz", allow_pickle=True); XS = SC["X"]; meta = json.loads(str(SC["meta_json"])); arms_cols = meta["arms_cols"]
    assert np.array_equal(SC["pair_a"].astype(np.int64), pa) and np.array_equal(SC["pair_s"].astype(np.int64), ps)
    Y = YRZ[pa, ps]; okrow = np.isfinite(Y)
    X82 = X82[okrow].astype(np.float32); XS = XS[okrow]; Y = Y[okrow].astype(np.float32); A = pa[okrow]; S = ps[okrow]; YRA = yrs[A]
    log(f"rows {len(Y)} X82 {X82.shape} XS {XS.shape}")
    arms = ["base", "S150", "S300", "S600", "SX"]
    if only_arms:
        arms = [a for a in arms if a in only_arms]
    rng = np.random.default_rng(0)
    for model in models:
        path = f"{OUT}/results/f8s_icpa_{model}.npz"
        R = {"icr": {}, "icy": {}, "icr_train": {}, "byfold": {}, "effdim": {}}
        if os.path.exists(path):
            old = np.load(path, allow_pickle=True); R = {k: dict(old[k].item()) for k in R}
        for arm in arms:
            if arm in R["icr"] and not only_arms:
                log(f"[{model}] skip {arm}"); continue
            X = X82 if arm == "base" else np.concatenate([X82, XS[:, arms_cols[arm]]], 1)
            if arm not in R["effdim"] or only_arms:
                R["effdim"][arm] = eff_dim(X, rng); log(f"[{model}] {arm} effdim {R['effdim'][arm]}")
            P = np.full((nA, NW), np.nan, np.float32); icr_tr = {}; byf = {}
            for YV in YEARS:
                t1 = time.time()
                te_anchor = np.where(yrs == YV)[0]; first_te = int(te_anchor[0])
                tr_ok = np.zeros(nA, bool); tr_ok[(yrs < YV) & (np.arange(nA) < first_te - EMBARGO)] = True
                tr_rows = np.where(tr_ok[A])[0]; te_rows = np.where(YRA == YV)[0]; tr_anchors = np.where(tr_ok)[0]
                if model.startswith("ridge"):
                    mu = X[tr_rows].mean(0); sd = X[tr_rows].std(0) + 1e-9
                    if model == "ridge_fixed":
                        G, b = gram_accumulate(X, tr_rows, mu, sd, Y); alpha = 1.0
                        G[:-1, :-1] += alpha * np.eye(X.shape[1]); beta = np.linalg.solve(G, b)
                    else:
                        nva = int(round(len(tr_anchors) * VAL_FRAC)); val_anchors = tr_anchors[-nva:]; fit_anchors = tr_anchors[:-nva]
                        va_mask = np.zeros(nA, bool); va_mask[val_anchors] = True
                        rows_fit = tr_rows[~va_mask[A[tr_rows]]]; rows_val = tr_rows[va_mask[A[tr_rows]]]
                        Gf, bf = gram_accumulate(X, rows_fit, mu, sd, Y); Gv, bv = gram_accumulate(X, rows_val, mu, sd, Y)
                        best = None
                        for al in ALPHAS:
                            Gi = Gf.copy(); Gi[:-1, :-1] += al * np.eye(X.shape[1]); bt = np.linalg.solve(Gi, bf)
                            pv = ridge_predict(X, rows_val, mu, sd, bt); Pv = np.full((nA, NW), np.nan, np.float32); Pv[A[rows_val], S[rows_val]] = pv
                            ic = nanmean([spear(Pv[i], YR4s[i]) for i in val_anchors])
                            if best is None or ic > best[1]:
                                best = (al, ic)
                        alpha = best[0]; G = Gf + Gv; G[:-1, :-1] += alpha * np.eye(X.shape[1]); beta = np.linalg.solve(G, bf + bv)
                    pv = ridge_predict(X, te_rows, mu, sd, beta); ptr = ridge_predict(X, tr_rows, mu, sd, beta)
                    byf[str(YV)] = {"alpha": alpha}
                else:
                    import lightgbm as lgb
                    gbm = lgb.LGBMRegressor(**LGB_PARAMS).fit(X[tr_rows], Y[tr_rows])
                    pv = gbm.predict(X[te_rows]).astype(np.float32); ptr = gbm.predict(X[tr_rows]).astype(np.float32); byf[str(YV)] = {}
                P[A[te_rows], S[te_rows]] = pv
                Ptr = np.full((nA, NW), np.nan, np.float32); Ptr[A[tr_rows], S[tr_rows]] = ptr
                ictr, _ = per_anchor_ic(Ptr, tr_anchors, YR4s, y4s); del Ptr
                icr_tr[str(YV)] = nanmean(ictr)
                ic_te = [spear(P[i], YR4s[i]) for i in te_anchor]
                byf[str(YV)].update({"ic_resid": nanmean(ic_te), "ic_train": icr_tr[str(YV)], "gap": icr_tr[str(YV)] - nanmean(ic_te), "sec": round(time.time() - t1, 1)})
                log(f"[{model}] {arm} {YV} OOS {nanmean(ic_te):+.4f} train {icr_tr[str(YV)]:+.4f} gap {icr_tr[str(YV)]-nanmean(ic_te):+.4f} {byf[str(YV)]}")
            icr, icy = per_anchor_ic(P, np.where(np.isin(yrs, YEARS))[0], YR4s, y4s)
            R["icr"][arm] = icr; R["icy"][arm] = icy; R["icr_train"][arm] = icr_tr; R["byfold"][arm] = byf
            np.savez(path, **{k: np.array(v, dtype=object) for k, v in R.items()})
            log(f"[{model}] {arm} DONE 年均 OOS {np.mean([v['ic_resid'] for v in byf.values()]):+.4f} train {np.mean(list(icr_tr.values())):+.4f}")
            del X, P
        log(f"RUN2_DONE_{model}")


# =====================================================================================
def block_boot_ci(d, nblk=60, B=2000, seed=0):
    d = np.asarray(d, float); d = d[np.isfinite(d)]; n = len(d)
    blocks = [d[k:k + nblk] for k in range(0, n, nblk)]; rng = np.random.default_rng(seed); nb = len(blocks)
    means = np.empty(B)
    for b in range(B):
        pick = rng.integers(0, nb, nb); means[b] = np.concatenate([blocks[j] for j in pick]).mean()
    return [float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))]


def judge():
    T = load_targets(); yrs = T["yrs"]; nA = len(yrs); test = np.isin(yrs, YEARS)
    out = {"prereg2_sha": PREREG2_SHA, "prereg2_commit": PREREG2_COMMIT, "self_sha256": sha(os.path.abspath(__file__)),
           "build_report": json.load(open(f"{OUT}/results/f8s_build_report.json")), "models": {}, "verdict": {}}
    out["build_report"].pop("names", None)
    for model in ("ridge_grid", "ridge_fixed", "lgbm"):
        path = f"{OUT}/results/f8s_icpa_{model}.npz"
        if not os.path.exists(path):
            continue
        Z = np.load(path, allow_pickle=True); R = {k: dict(Z[k].item()) for k in ("icr", "icy", "icr_train", "byfold", "effdim")}
        if "base" not in R["icr"]:
            continue
        base = R["icr"]["base"]; Aset = test & np.isfinite(base)
        for a in R["icr"]:
            Aset &= np.isfinite(R["icr"][a]) | ~test
        M = {"setA_n": int(Aset.sum()), "table": {}, "delta": {}, "gates": {}}
        for a in R["icr"]:
            r = {"ic_resid_A": nanmean(R["icr"][a][Aset]), "ic_raw_A": nanmean(R["icy"][a][Aset]), "by_year": {str(y): nanmean(R["icr"][a][Aset & (yrs == y)]) for y in YEARS},
                 "train_ic_by_fold": R["icr_train"][a], "train_ic_mean": float(np.mean(list(R["icr_train"][a].values()))),
                 "alpha_by_fold": {k: v.get("alpha") for k, v in R["byfold"][a].items()}, "effdim": R["effdim"].get(a)}
            r["overfit_gap"] = r["train_ic_mean"] - float(np.mean(list(r["by_year"].values())))
            M["table"][a] = r
            if a != "base":
                d = R["icr"][a] - base; pr = paired(d[Aset]); pr["by_year"] = {str(y): nanmean(d[Aset & (yrs == y)]) for y in YEARS}
                pr["n_pos_years"] = int(sum(v > 0 for v in pr["by_year"].values() if np.isfinite(v))); pr["ci95_block60"] = block_boot_ci(d[Aset])
                pr["raw_mean"] = nanmean((R["icy"][a] - R["icy"]["base"])[Aset])
                M["delta"][a] = pr
                M["gates"][a] = {"delta": pr["mean"], "pass_delta_0005": pr["mean"] >= 0.005, "n_pos_years": pr["n_pos_years"],
                                 "verdict": ("数量可推动" if pr["mean"] >= 0.005 and pr["n_pos_years"] == 4 else "条件(3/4)" if pr["mean"] >= 0.005 and pr["n_pos_years"] == 3 else "FAIL")}
        ds = {a: M["delta"][a]["mean"] for a in ("S150", "S300", "S600") if a in M["delta"]}
        if ds:
            if any(v >= 0.005 for v in ds.values()):
                shape = "数量可推动(至少一档过线)"
            elif all(abs(v) < 0.002 for v in ds.values()):
                shape = "饱和"
            elif any(v <= -0.002 for a, v in ds.items() if a in ("S300", "S600")):
                shape = "变差(列税/过拟合)"
            else:
                shape = "弱增, 不成跃升"
            M["curve_verdict"] = {"deltas": ds, "shape": shape, "SX_delta": M["delta"].get("SX", {}).get("mean")}
        out["models"][model] = M
    json.dump(out, open(f"{OUT}/results/f8_scaling_curve_2026-08-22.json", "w"), indent=1)
    for model, M in out["models"].items():
        print(f"\n===== 标度曲线 [{model}] 残差秩 IC(集 A n={M['setA_n']}) =====")
        print(f"{'arm':<7s}{'cols':>6s}{'n95':>5s}{'IC_A':>9s}{'Δ':>9s}{'t':>7s}{'CI95':>20s}{'同号':>5s}" + "".join(f"{y:>9d}" for y in YEARS) + f"{'trainIC':>9s}{'gap':>8s}  α/verdict")
        for a, r in M["table"].items():
            d = M["delta"].get(a); ed = r["effdim"] or {}
            if d is None:
                print(f"{a:<7s}{ed.get('n_cols',0):>6d}{ed.get('n95',0):>5d}{r['ic_resid_A']:>+9.4f}{'':>9s}{'':>7s}{'':>20s}{'':>5s}" + "".join(f"{r['by_year'][str(y)]:>+9.4f}" for y in YEARS) + f"{r['train_ic_mean']:>+9.4f}{r['overfit_gap']:>+8.4f}  {r['alpha_by_fold']}")
            else:
                print(f"{a:<7s}{ed.get('n_cols',0):>6d}{ed.get('n95',0):>5d}{r['ic_resid_A']:>+9.4f}{d['mean']:>+9.4f}{d['t']:>+7.1f}{str([round(x,4) for x in d['ci95_block60']]):>20s}{d['n_pos_years']:>4d}/4" + "".join(f"{d['by_year'][str(y)]:>+9.4f}" for y in YEARS) + f"{r['train_ic_mean']:>+9.4f}{r['overfit_gap']:>+8.4f}  {r['alpha_by_fold']} {M['gates'][a]['verdict']}")
        print("curve:", json.dumps(M.get("curve_verdict"), ensure_ascii=False))
    log("JUDGE2_DONE")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("stage", choices=["build", "run", "judge"]); ap.add_argument("--models", default="ridge_grid,ridge_fixed,lgbm"); ap.add_argument("--arms", default="")
    a = ap.parse_args()
    if a.stage == "build":
        build()
    elif a.stage == "run":
        run(a.models.split(","), [x for x in a.arms.split(",") if x] or None)
    else:
        judge()
