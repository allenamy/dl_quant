"""F-8 · 高阶 / 时序 / 交互特征是否有用 —— G0 级判决装置 @jpline CPU(2026-08-22, Session 6737834a-F8)。
预注册: multi_asset/exports/eda/PREREG_RESULT_F8_higher_order_features_2026-08-22.md §P(冻结段 SHA256 184bf281…9808, commit 44f1fdc, 先于任何数字)。
逐位复用 DLW 三件(不重建): dlw_targets.npz(锚/成员/目标/标签/折的唯一真相源)+ dlw_fea82.npz(82 列基线弹药)+ 5m 缓存 dlnative_5m_wide829_f16.npz(新列唯一原料)。
阶段:
  build : 10 族 89 列(§P.2, 因果 ≤ E; 结构断言写入 meta)→ data/f8_fea89.npz(长格式, 与 dlw_fea82 的 pair_a/pair_s 逐行对齐)
  run   : 臂 = base / +A..+J / +Hs / +ALL / PL_ALL_s0..4 / PL_I_s0..4 × 模型 {ridge, lgbm}(参数逐字 dlw_g0.py), 4 折(YV 2023–26, 训练 = 年<YV 且锚<首测锚−60)
          → results/f8_icpa_<model>.npz(逐臂逐锚残差/原始秩 IC)+ preds/f8_<model>_<arm>.npy(非安慰剂臂)
  judge : 表 / 配对 Δ / 逐年 / Q4 / 分段 / 安慰剂 / 门(§P.5)/ S1(对宽 king, 配对差 + 绝对 + 残差式)/ R1–R5 收据 → results/f8_higher_order_features_2026-08-22.json
用法 @jpline(conda hsy_v5push): python -u f8_higher_order_features.py build|run|judge [--models ridge,lgbm] [--arms a,b,...]
"""
import os, sys, json, time, hashlib, argparse
import numpy as np
import pandas as pd
from scipy.stats import rankdata, spearmanr, pearsonr

ROOT = "/mnt/storage/private/work_hsy"
DLW = f"{ROOT}/dlw_2026-08-22"
CACHE = f"{ROOT}/w3lane/kcurve/data/dlnative_5m_wide829_f16.npz"
TARGETS = f"{DLW}/data/dlw_targets.npz"
FEA82 = f"{DLW}/data/dlw_fea82.npz"
G0JSON = f"{DLW}/results/dlw_g0.json"
K0DIR = f"{ROOT}/pod_backup_2026-08-21"
OUT = f"{ROOT}/f8_2026-08-22"
PREREG_SHA = "184bf281be1d6ee16eef9aec40040d72ac8de8a002884cf937229552665c9808"; PREREG_COMMIT = "44f1fdc"
YEARS = (2023, 2024, 2025, 2026); EMBARGO = 60
RIDGE_ALPHA = 1.0; NJOBS = 8
LGB_PARAMS = dict(n_estimators=400, learning_rate=0.05, num_leaves=63, subsample=0.8, colsample_bytree=0.8, random_state=0, n_jobs=NJOBS, verbose=-1)
CHUNK = 64
FAMS = list("ABCDEFGHIJ")
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


def load_targets():
    TG = np.load(TARGETS, allow_pickle=True)
    return dict(E=TG["E_row"].astype(np.int64), E_ts=TG["E_ts"].astype(np.int64), MS=list(TG["members"]), yrs=TG["yrs"].astype(int),
                YRZ=TG["YRZ"], YR4s=TG["YR4s"], y4s=TG["y4s"], btcv=TG["btcv"].astype(np.float64), syms=[str(s) for s in TG["symbols"]])


def load_fea82():
    FE = np.load(FEA82, allow_pickle=True)
    return FE["X"], FE["pair_a"].astype(np.int64), FE["pair_s"].astype(np.int64), [str(n) for n in FE["names"]]


# =====================================================================================
# build
# =====================================================================================
def cs(a):
    """前导零行累积和(f64): CS[hi] − CS[lo] = Σ rows [lo, hi)。"""
    return np.concatenate([np.zeros((1, a.shape[1])), np.cumsum(a, 0, dtype=np.float64)])


def wsum(CS, hi, lo):
    return CS[hi] - CS[lo]


def anchor_rank_block(V):
    """锚内列向中心化秩 ∈ [−0.5, 0.5], NaN ⇒ 0。V: (n, k)。"""
    V = np.asarray(V, np.float64)
    ok = np.isfinite(V); nok = ok.sum(0)
    R = rankdata(V, axis=0, nan_policy="omit")
    Z = (R - (nok + 1) / 2) / np.maximum(nok - 1, 1)
    Z[~ok] = 0.0
    Z[:, nok < 10] = 0.0
    return Z.astype(np.float32)


def build():
    os.makedirs(f"{OUT}/data", exist_ok=True); os.makedirs(f"{OUT}/results", exist_ok=True); os.makedirs(f"{OUT}/preds", exist_ok=True)
    T = load_targets(); E = T["E"]; E_ts = T["E_ts"]; MS = T["MS"]; nA = len(E); syms = T["syms"]; NW = len(syms)
    X82, pa, ps, n82 = load_fea82()
    assert np.all(np.diff(pa) >= 0), "pair_a 非单调"
    st = np.searchsorted(pa, np.arange(nA + 1))
    assert st[-1] == len(pa)
    col = {n: i for i, n in enumerate(n82)}
    Z = np.load(CACHE, allow_pickle=True)
    CTS = Z["ts"].astype(np.int64); CD = Z["data"]; assert [str(s) for s in Z["symbols"]] == syms
    assert [str(c) for c in Z["ch"]] == ["ret5", "range", "cpos", "log_qv", "log_cnt", "log_avgsz", "tbf"]
    assert np.array_equal(CTS[E], E_ts)
    TT = CD.shape[0]
    log(f"cache {CD.shape} anchors {nA} pairs {len(pa)}")
    hi = E + 1                                           # 半开上界 ⇒ 最后一行 = E
    def lo_of(w, h=None):
        h = hi if h is None else h
        return np.maximum(h - w, 0)
    tidx = np.arange(TT, dtype=np.float64)
    # ---- 输出容器 (nA, NW) f32
    F = {}
    def put(name, arr, chunk):
        if name not in F:
            F[name] = np.full((nA, NW), np.nan, np.float32)
        F[name][:, chunk] = arr.astype(np.float32)
    # 结构断言记录: 每族用到的最大行偏移(相对 E)
    max_off = {f: -10**9 for f in FAMS}
    def touch(fam, rows_max_minus_E):
        max_off[fam] = max(max_off[fam], int(rows_max_minus_E))
    # 同相位窗索引(E 族): W_j = [E+1−288j, E+48−288j], j=1..30 ⇒ CS 区间 [E+1−288j, E+49−288j)
    J = np.arange(1, 31)
    sp_lo = hi[None, :] - 288 * J[:, None]; sp_hi = sp_lo + 48
    sp_ok = sp_lo >= 0
    sp_lo_c = np.maximum(sp_lo, 0); sp_hi_c = np.maximum(sp_hi, 0)
    sp_max_off = int((sp_hi - hi[None, :]).max())          # 同相位窗最大行 = sp_hi−1 ⇒ 偏移 vs E = sp_hi − hi(j=1 ⇒ −240)
    touch("E", 0)                                          # E 族的基线项(mean_2016)用到 E 本行
    # 块索引(C 族 vr / upblk; J 族 lag)
    def blocks(bw, nb):   # 第 k 块(k=1..nb) = rows [hi − bw·k, hi − bw·(k−1))
        k = np.arange(1, nb + 1)
        b_hi = hi[None, :] - bw * (k[:, None] - 1); b_lo = b_hi - bw
        return np.maximum(b_lo, 0), np.maximum(b_hi, 0), (b_lo >= 0)
    for c0 in range(0, NW, CHUNK):
        chunk = np.arange(c0, min(c0 + CHUNK, NW)); nc = len(chunk)
        r = CD[:, chunk, 0].astype(np.float32); fin = np.isfinite(r); rz = np.where(fin, r, 0).astype(np.float64)
        rg = CD[:, chunk, 1].astype(np.float32); fing = np.isfinite(rg); rgz = np.where(fing, rg, 0).astype(np.float64)
        lq = CD[:, chunk, 3].astype(np.float32); finq = np.isfinite(lq); lqz = np.where(finq, lq, 0).astype(np.float64)
        tb = CD[:, chunk, 6].astype(np.float32); fint = np.isfinite(tb); tbz = np.where(fint, tb, 0).astype(np.float64)
        del r, rg, lq, tb
        m = fin.astype(np.float64)
        CSf = cs(m); CSr = cs(rz); CSr2 = cs(rz ** 2); CSr3 = cs(rz ** 3); CSr4 = cs(rz ** 4)
        CSr2dn = cs(rz ** 2 * (rz < 0)); CSabs = cs(np.abs(rz))
        rl = np.vstack([np.zeros((1, nc)), rz[:-1]]); fl = np.vstack([np.zeros((1, nc), bool), fin[:-1]])
        both = (fin & fl).astype(np.float64)
        CSbv = cs(np.abs(rz) * np.abs(rl) * both); CSrr1 = cs(rz * rl * both); CSboth = cs(both)
        # ---------- A 高阶矩 / 跳跃 ----------
        for w in (288, 2016):
            lo = lo_of(w); n = np.maximum(wsum(CSf, hi, lo), 1)
            m2 = wsum(CSr2, hi, lo) / n; m3 = wsum(CSr3, hi, lo) / n; m4 = wsum(CSr4, hi, lo) / n
            bad = wsum(CSf, hi, lo) < w // 4
            sk = m3 / np.maximum(m2, 1e-18) ** 1.5; ku = m4 / np.maximum(m2, 1e-18) ** 2
            sd = wsum(CSr2dn, hi, lo) / np.maximum(wsum(CSr2, hi, lo), 1e-18)
            bv = (np.pi / 2) * wsum(CSbv, hi, lo); rv = wsum(CSr2, hi, lo)
            jp = 1 - bv / np.maximum(rv, 1e-18)
            for nm, v in (("skew", sk), ("kurt", ku), ("semidn", sd), ("jump", jp)):
                v = np.where(bad | (m2 <= 0), np.nan, v); put(f"A:{nm}_{w}", v, chunk)
            touch("A", 0)
        # rolling max |r| (pandas)
        absr = pd.DataFrame(np.where(fin, np.abs(rz), np.nan))
        for w in (288, 2016):
            mx = absr.rolling(w, min_periods=max(w // 4, 1)).max().values[E]
            lo = lo_of(w); n = np.maximum(wsum(CSf, hi, lo), 1); vol = np.sqrt(np.maximum(wsum(CSr2, hi, lo) / n, 0))
            put(f"A:maxr_{w}", mx / np.maximum(vol, 1e-12), chunk)
        del absr
        # ---------- B 波动动态 ----------
        def vol_at(w, h):
            lo = lo_of(w, h); n = wsum(CSf, h, lo); v = np.sqrt(np.maximum(wsum(CSr2, h, lo) / np.maximum(n, 1), 0))
            return np.where(n >= max(w // 4, 1), v, np.nan)
        V = {w: vol_at(w, hi) for w in (48, 288, 2016, 8640)}
        put("B:vr_48_288", np.log(V[48] / V[288]), chunk); put("B:vr_288_2016", np.log(V[288] / V[2016]), chunk); put("B:vr_2016_8640", np.log(V[2016] / V[8640]), chunk)
        RVj = np.stack([wsum(CSr2, np.maximum(hi - 288 * j, 0), np.maximum(hi - 288 * (j + 1), 0)) for j in range(7)])   # (7, nA, nc)
        okj = (hi - 288 * 7 >= 0)
        vov = RVj.std(0) / np.maximum(RVj.mean(0), 1e-18); vov[~okj] = np.nan; put("B:vov_7d", vov, chunk)
        put("B:dvol_1d", np.log(V[288] / vol_at(288, np.maximum(hi - 288, 0))), chunk)
        put("B:dvol_4h", np.log(V[48] / vol_at(48, np.maximum(hi - 48, 0))), chunk)
        CSfg = cs(fing.astype(np.float64)); CSrg = cs(rgz)
        for w in (288, 2016):
            lo = lo_of(w); ng = np.maximum(wsum(CSfg, hi, lo), 1)
            put(f"B:rngvol_{w}", (wsum(CSrg, hi, lo) / ng) / np.maximum(V[w], 1e-12), chunk)
        touch("B", 0)
        # ---------- C 自相关 / 方差比 / 趋势 ----------
        for w in (288, 2016):
            lo = lo_of(w); num = wsum(CSrr1, hi, lo + 1); den = wsum(CSr2, hi, lo)
            ac = num / np.maximum(den, 1e-18); ac[wsum(CSboth, hi, lo + 1) < w // 4] = np.nan; put(f"C:ac1_{w}", ac, chunk)
        def var5m(w):
            lo = lo_of(w); n = np.maximum(wsum(CSf, hi, lo), 1)
            return np.maximum(wsum(CSr2, hi, lo) / n - (wsum(CSr, hi, lo) / n) ** 2, 1e-18), wsum(CSf, hi, lo) >= w // 2
        for bw, w, nm in ((12, 2016, "vr12_2016"), (48, 2016, "vr48_2016"), (48, 8640, "vr48_8640")):
            b_lo, b_hi, b_ok = blocks(bw, w // bw)
            BS = wsum(CSr, b_hi, b_lo)                           # (nb, nA, nc)
            v5, okw = var5m(w)
            vb = np.var(BS, axis=0)
            vr = vb / (bw * v5); vr[~okw] = np.nan
            vr[~b_ok.all(0), :] = np.nan
            put(f"C:{nm}", vr, chunk)
            if nm == "vr48_2016":
                up = (BS > 0).mean(0); up[~b_ok.all(0), :] = np.nan; put("C:upblk_2016", up, chunk)
            del BS
        # 趋势: 对数价格 p 对时间的带号 R²(p 预上市 NaN)
        p = np.cumsum(np.log1p(rz), 0)
        first = np.where(fin.any(0), fin.argmax(0), TT)
        pm = (np.arange(TT)[:, None] >= first[None, :])
        pz = np.where(pm, p, 0.0); pmf = pm.astype(np.float64)
        CSpm = cs(pmf); CSp = cs(pz); CSp2 = cs(pz ** 2); CSt = cs(tidx[:, None] * pmf); CSt2 = cs(tidx[:, None] ** 2 * pmf); CStp = cs(tidx[:, None] * pz)
        for w in (288, 2016):
            lo = lo_of(w); n = wsum(CSpm, hi, lo); nn = np.maximum(n, 1)
            Sp = wsum(CSp, hi, lo); Sp2 = wsum(CSp2, hi, lo); St = wsum(CSt, hi, lo); St2 = wsum(CSt2, hi, lo); Stp = wsum(CStp, hi, lo)
            cov = Stp / nn - (St / nn) * (Sp / nn); vt = St2 / nn - (St / nn) ** 2; vp = Sp2 / nn - (Sp / nn) ** 2
            rho = cov / np.sqrt(np.maximum(vt * vp, 1e-30)); rho = np.clip(rho, -1, 1)
            tr = np.sign(rho) * rho ** 2; tr[(n < w // 2) | (vp <= 1e-20)] = np.nan; put(f"C:trend_{w}", tr, chunk)
        del CSpm, CSp, CSp2, CSt, CSt2, CStp
        touch("C", 0)
        # ---------- D 路径 ----------
        pn = np.where(pm, p, np.nan)
        pdf = pd.DataFrame(pn)
        pE = pn[E]
        for w in (48, 288, 2016, 8640):
            mx = pdf.rolling(w, min_periods=max(w // 4, 1)).max().values[E]; put(f"D:dhi_{w}", pE - mx, chunk)
        for w in (288, 2016, 8640):
            mn = pdf.rolling(w, min_periods=max(w // 4, 1)).min().values[E]; put(f"D:dlo_{w}", pE - mn, chunk)
        for w in (288, 2016):
            rk = pdf.rolling(w, min_periods=max(w // 2, 1)).rank(pct=True).values[E]; put(f"D:ppct_{w}", rk, chunk)
        del pdf, pn, p, pz, pm, pmf
        touch("D", 0)
        # ---------- E 逐名日内相位季节性 ----------
        CSfq = cs(finq.astype(np.float64)); CSlq = cs(lqz); CSft = cs(fint.astype(np.float64)); CStb = cs(tbz)
        def sp_mean(CSx, CSn, jmax):
            num = CSx[sp_hi_c[:jmax]] - CSx[sp_lo_c[:jmax]]; den = CSn[sp_hi_c[:jmax]] - CSn[sp_lo_c[:jmax]]
            v = num / np.maximum(den, 1); v[(den < 24) | ~sp_ok[:jmax][..., None]] = np.nan
            return v                                         # (jmax, nA, nc)
        SR30 = CSr[sp_hi_c] - CSr[sp_lo_c]; SR30[~sp_ok[..., None].repeat(nc, 2)] = np.nan
        nv7 = np.isfinite(SR30[:7]).sum(0); nv30 = np.isfinite(SR30).sum(0)
        spr7 = np.nanmean(SR30[:7], 0); spr7[nv7 < 5] = np.nan; put("E:spr_7", spr7, chunk)
        spr30 = np.nanmean(SR30, 0); sd30 = np.nanstd(SR30, 0); spr30[nv30 < 15] = np.nan; put("E:spr_30", spr30, chunk)
        t30 = spr30 / np.maximum(sd30 / np.sqrt(np.maximum(nv30, 1)), 1e-12); put("E:spr_30_t", t30, chunk)
        def win_mean(CSx, CSn, w):
            lo = lo_of(w); n = wsum(CSn, hi, lo); v = wsum(CSx, hi, lo) / np.maximum(n, 1); v[n < w // 4] = np.nan; return v
        Q = sp_mean(CSlq, CSfq, 30)
        spq7 = np.nanmean(Q[:7], 0); spq7[np.isfinite(Q[:7]).sum(0) < 5] = np.nan; put("E:spq_7", spq7 - win_mean(CSlq, CSfq, 2016), chunk)
        spq30 = np.nanmean(Q, 0); spq30[np.isfinite(Q).sum(0) < 15] = np.nan; put("E:spq_30", spq30 - win_mean(CSlq, CSfq, 8640), chunk)
        G = sp_mean(CSrg, CSfg, 7); sprg7 = np.nanmean(G, 0); sprg7[np.isfinite(G).sum(0) < 5] = np.nan; put("E:sprg_7", sprg7 - win_mean(CSrg, CSfg, 2016), chunk)
        Tb = sp_mean(CStb, CSft, 7); spt7 = np.nanmean(Tb, 0); spt7[np.isfinite(Tb).sum(0) < 5] = np.nan; put("E:spt_7", spt7 - win_mean(CStb, CSft, 2016), chunk)
        del SR30, Q, G, Tb
        # ---------- F 量价交互 ----------
        qv = np.where(finq, np.exp(lqz), 0.0); CSqv = cs(qv)
        s = (2 * tbz - 1) * qv * fint; CSs = cs(s); CSs2 = cs(s ** 2); CSrs = cs(rz * s)
        CSlq2 = cs(lqz ** 2)
        dlq = np.vstack([np.zeros((1, nc)), lqz[1:] - lqz[:-1]]); jm = (finq & np.vstack([np.zeros((1, nc), bool), finq[:-1]]) & fin).astype(np.float64)
        dlq = dlq * jm; CSdlq = cs(dlq); CSdlq2 = cs(dlq ** 2); CSrdlq = cs(rz * dlq); CSdok = cs(jm); CSr_j = cs(rz * jm); CSr2_j = cs(rz ** 2 * jm)
        CSabs_lq = cs(np.abs(rz) * lqz * finq); CSabs_q = cs(np.abs(rz) * finq); CSabs2_q = cs(rz ** 2 * finq); CSlq_r = cs(lqz * fin * finq); CSlq2_r = cs(lqz ** 2 * fin * finq); CSn_rq = cs((fin & finq).astype(np.float64))
        up = (rz > 0) & finq; dn = (rz < 0) & finq
        CSlq_up = cs(lqz * up); CSn_up = cs(up.astype(np.float64)); CSlq_dn = cs(lqz * dn); CSn_dn = cs(dn.astype(np.float64))
        def amihud(w):
            lo = lo_of(w); a = wsum(CSabs, hi, lo) / np.maximum(wsum(CSqv, hi, lo), 1e-12); a[wsum(CSf, hi, lo) < w // 4] = np.nan; return a
        A288 = amihud(288); A2016 = amihud(2016)
        put("F:amihud_288", A288, chunk); put("F:amihud_2016", A2016, chunk); put("F:damihud", np.log(np.maximum(A288, 1e-30) / np.maximum(A2016, 1e-30)), chunk)
        for w in (288, 2016):
            lo = lo_of(w); k = wsum(CSrs, hi, lo) / np.maximum(wsum(CSs2, hi, lo), 1e-30); k[wsum(CSf, hi, lo) < w // 4] = np.nan; put(f"F:kyle_{w}", k, chunk)
        lo48 = lo_of(48); lo2016 = lo_of(2016)
        n48 = np.maximum(wsum(CSfq, hi, lo48), 1); n2016 = np.maximum(wsum(CSfq, hi, lo2016), 1)
        m48 = wsum(CSlq, hi, lo48) / n48; m2016 = wsum(CSlq, hi, lo2016) / n2016
        sd2016 = np.sqrt(np.maximum(wsum(CSlq2, hi, lo2016) / n2016 - m2016 ** 2, 1e-18))
        qz = (m48 - m2016) / sd2016; qz[(wsum(CSfq, hi, lo48) < 12) | (wsum(CSfq, hi, lo2016) < 504)] = np.nan; put("F:qvz_48", qz, chunk)
        lo = lo_of(288)
        n = np.maximum(wsum(CSdok, hi, lo), 1)
        mr = wsum(CSr_j, hi, lo) / n; md = wsum(CSdlq, hi, lo) / n
        cov = wsum(CSrdlq, hi, lo) / n - mr * md; vr_ = wsum(CSr2_j, hi, lo) / n - mr ** 2; vd = wsum(CSdlq2, hi, lo) / n - md ** 2
        cpv = cov / np.sqrt(np.maximum(vr_ * vd, 1e-30)); cpv[wsum(CSdok, hi, lo) < 72] = np.nan; put("F:corr_pv_288", np.clip(cpv, -1, 1), chunk)
        n = np.maximum(wsum(CSn_rq, hi, lo), 1)
        ma = wsum(CSabs_q, hi, lo) / n; ml = wsum(CSlq_r, hi, lo) / n
        cov = wsum(CSabs_lq, hi, lo) / n - ma * ml; va = wsum(CSabs2_q, hi, lo) / n - ma ** 2; vl = wsum(CSlq2_r, hi, lo) / n - ml ** 2
        caq = cov / np.sqrt(np.maximum(va * vl, 1e-30)); caq[wsum(CSn_rq, hi, lo) < 72] = np.nan; put("F:corr_aq_288", np.clip(caq, -1, 1), chunk)
        nu = wsum(CSn_up, hi, lo); nd = wsum(CSn_dn, hi, lo)
        ud = wsum(CSlq_up, hi, lo) / np.maximum(nu, 1) - wsum(CSlq_dn, hi, lo) / np.maximum(nd, 1); ud[(nu < 20) | (nd < 20)] = np.nan; put("F:udqv_288", ud, chunk)
        touch("F", 0)
        # ---------- G 主动买卖流动态 ----------
        for w in (48, 288, 2016):
            lo = lo_of(w); v = wsum(CSs, hi, lo) / np.maximum(wsum(CSqv, hi, lo), 1e-12); v[wsum(CSft, hi, lo) < w // 4] = np.nan; put(f"G:tbvw_{w}", v, chunk)
        def tbmean(w, h):
            lo = lo_of(w, h); n = wsum(CSft, h, lo); v = wsum(CStb, h, lo) / np.maximum(n, 1); v[n < w // 4] = np.nan; return v
        t0_ = tbmean(48, hi); t1_ = tbmean(48, np.maximum(hi - 48, 0)); t2_ = tbmean(48, np.maximum(hi - 96, 0))
        put("G:tbacc_48", (t0_ - t1_) - (t1_ - t2_), chunk)
        CStb2 = cs(tbz ** 2)
        tl = np.vstack([np.zeros((1, nc)), tbz[:-1]]); tboth = (fint & np.vstack([np.zeros((1, nc), bool), fint[:-1]])).astype(np.float64)
        CStt1 = cs(tbz * tl * tboth); CStboth = cs(tboth)
        lo = lo_of(288); n = np.maximum(wsum(CSft, hi, lo), 1); mt = wsum(CStb, hi, lo) / n; vt = wsum(CStb2, hi, lo) / n - mt ** 2
        n1 = np.maximum(wsum(CStboth, hi, lo + 1), 1)
        ac = (wsum(CStt1, hi, lo + 1) / n1 - mt ** 2) / np.maximum(vt, 1e-18); ac[wsum(CSft, hi, lo) < 72] = np.nan; put("G:tbac1_288", np.clip(ac, -1, 1), chunk)
        sdt = np.sqrt(np.maximum(vt, 0)); sdt[wsum(CSft, hi, lo) < 72] = np.nan; put("G:tbstd_288", sdt, chunk)
        lo2 = lo_of(2016); n2 = np.maximum(wsum(CSft, hi, lo2), 1); mt2 = wsum(CStb, hi, lo2) / n2; sd2 = np.sqrt(np.maximum(wsum(CStb2, hi, lo2) / n2 - mt2 ** 2, 1e-18))
        tz = (t0_ - mt2) / sd2; tz[wsum(CSft, hi, lo2) < 504] = np.nan; put("G:tbz_48", tz, chunk)
        CStr = cs(tbz * rz * fint * fin); CSn_tr = cs((fint & fin).astype(np.float64)); CSr_t = cs(rz * fint); CSr2_t = cs(rz ** 2 * fint); CStb_r = cs(tbz * fin); CStb2_r = cs(tbz ** 2 * fin)
        n = np.maximum(wsum(CSn_tr, hi, lo), 1); mtt = wsum(CStb_r, hi, lo) / n; mrr = wsum(CSr_t, hi, lo) / n
        cov = wsum(CStr, hi, lo) / n - mtt * mrr; v1 = wsum(CStb2_r, hi, lo) / n - mtt ** 2; v2 = wsum(CSr2_t, hi, lo) / n - mrr ** 2
        ctr = cov / np.sqrt(np.maximum(v1 * v2, 1e-30)); ctr[wsum(CSn_tr, hi, lo) < 72] = np.nan; put("G:corr_tr_288", np.clip(ctr, -1, 1), chunk)
        touch("G", 0)
        # ---------- J 锚间时序(缓存可算部分) ----------
        for k in range(2, 7):
            b_hi = np.maximum(hi - 48 * (k - 1), 0); b_lo = np.maximum(hi - 48 * k, 0)
            v = wsum(CSr, b_hi, b_lo); v[wsum(CSf, b_hi, b_lo) < 12] = np.nan; put(f"J:r4_lag_{k}", v, chunk)
        b_hi = np.maximum(hi - 288, 0); b_lo = np.maximum(hi - 576, 0)
        v = wsum(CSr, b_hi, b_lo); v[wsum(CSf, b_hi, b_lo) < 72] = np.nan; put("J:r24_lag1", v, chunk)
        q0 = wsum(CSlq, hi, lo48) / np.maximum(wsum(CSfq, hi, lo48), 1); h1 = np.maximum(hi - 48, 0); l1 = lo_of(48, h1)
        q1 = wsum(CSlq, h1, l1) / np.maximum(wsum(CSfq, h1, l1), 1)
        v = q0 - q1; v[(wsum(CSfq, hi, lo48) < 12) | (wsum(CSfq, h1, l1) < 12)] = np.nan; put("J:dqv_4h", v, chunk)
        touch("J", 0)                                       # dqv_4h 当前窗用到 E 本行; lag 块/锚间秩的偏移单独记录
        log(f"chunk {c0}-{chunk[-1]} done ({len(F)} features so far)")
    del CD, Z
    # ---------- 锚内秩形态列(A–G, J 的缓存列) ----------
    rank_fams = "ABCDEFGJ"
    rank_names = [n for n in F if n[0] in rank_fams]
    # 族内顺序按 §P.2 列表固定
    order = {
        "A": ["skew_288", "skew_2016", "kurt_288", "kurt_2016", "semidn_288", "semidn_2016", "jump_288", "jump_2016", "maxr_288", "maxr_2016"],
        "B": ["vr_48_288", "vr_288_2016", "vr_2016_8640", "vov_7d", "dvol_1d", "dvol_4h", "rngvol_288", "rngvol_2016"],
        "C": ["ac1_288", "ac1_2016", "vr12_2016", "vr48_2016", "vr48_8640", "trend_288", "trend_2016", "upblk_2016"],
        "D": ["dhi_48", "dhi_288", "dhi_2016", "dhi_8640", "dlo_288", "dlo_2016", "dlo_8640", "ppct_288", "ppct_2016"],
        "E": ["spr_7", "spr_30", "spr_30_t", "spq_7", "spq_30", "sprg_7", "spt_7"],
        "F": ["amihud_288", "amihud_2016", "damihud", "kyle_288", "kyle_2016", "qvz_48", "corr_pv_288", "corr_aq_288", "udqv_288"],
        "G": ["tbvw_48", "tbvw_288", "tbvw_2016", "tbacc_48", "tbac1_288", "tbstd_288", "tbz_48", "corr_tr_288"],
        "J": ["r4_lag_2", "r4_lag_3", "r4_lag_4", "r4_lag_5", "r4_lag_6", "r24_lag1", "dqv_4h", "drank_m7_1d", "drank_v7_1d", "drank_r24_1d"],
    }
    # J 的锚间秩动量: 该名 82 列秩(E) − 同名 24h 前锚(i−6, E_ts 差恰 86400, 且为成员)的秩
    def dense_rank(colname):
        D = np.full((nA, NW), np.nan, np.float32); D[pa, ps] = X82[:, col[colname]].astype(np.float32); return D
    for nm, cn in (("drank_m7_1d", "ret5_sum_2016_r"), ("drank_v7_1d", "vol_2016_r"), ("drank_r24_1d", "ret5_sum_288_r")):
        D = dense_rank(cn); out = np.full((nA, NW), np.nan, np.float32)
        ok = np.zeros(nA, bool); ok[6:] = (E_ts[6:] - E_ts[:-6]) == 86400
        out[ok] = D[ok] - D[np.where(ok)[0] - 6]
        F[f"J:{nm}"] = out
    all_rank_names = [f"{f}:{n}" for f in order for n in order[f]]
    for n in all_rank_names:
        assert n in F, n
    n_pairs = len(pa)
    XR = np.zeros((n_pairs, len(all_rank_names)), np.float32)
    raw = np.stack([F[n][pa, ps] for n in all_rank_names], 1)       # (n_pairs, k) 原值
    for i in range(nA):
        sl = slice(st[i], st[i + 1])
        XR[sl] = anchor_rank_block(raw[sl])
    finite_share = {n: float(np.isfinite(raw[:, j]).mean()) for j, n in enumerate(all_rank_names)}
    del raw
    # ---------- H 因子×状态 ----------
    r24v = X82[:, col["ret5_sum_288_v"]].astype(np.float64)
    disp = np.array([np.nanstd(r24v[st[i]:st[i + 1]]) for i in range(nA)])
    def causal_z(x, win=180, minn=30):
        z = np.full(len(x), np.nan)
        s = pd.Series(x)
        mu = s.shift(1).rolling(win, min_periods=minn).mean().values; sd = s.shift(1).rolling(win, min_periods=minn).std().values
        z = (x - mu) / (sd + 1e-12)
        return np.clip(np.nan_to_num(z, nan=0.0), -5, 5)
    disp_z = causal_z(disp); btcv_z = causal_z(T["btcv"])
    rk = {k: X82[:, col[c]].astype(np.float32) for k, c in (("r4", "ret5_sum_48_r"), ("r24", "ret5_sum_288_r"), ("m7", "ret5_sum_2016_r"), ("m30", "ret5_sum_8640_r"),
                                                              ("v7", "vol_2016_r"), ("q7", "log_qv_mean_2016_r"), ("t24", "tbf_mean_288_r"))}
    Hs = np.stack([disp_z[pa], btcv_z[pa]], 1).astype(np.float32)
    Hp = np.stack([rk[f] * Hs[:, j] for j in (0, 1) for f in ("r4", "r24", "m7", "v7")], 1).astype(np.float32)
    H_names = ["H:disp_z", "H:btcv_z"] + [f"H:{f}x{s_}" for s_ in ("disp", "btcv") for f in ("r4", "r24", "m7", "v7")]
    # ---------- I 因子二阶/三阶 ----------
    I = np.stack([rk["r24"] ** 2, rk["m7"] ** 2, rk["v7"] ** 2, rk["r24"] * rk["v7"], rk["r24"] * rk["q7"], rk["m7"] * rk["v7"], rk["r4"] * rk["t24"], rk["m7"] * rk["m30"],
                  rk["r24"] * rk["v7"] * rk["q7"], rk["m7"] * rk["v7"] * rk["q7"]], 1).astype(np.float32)
    I_names = ["I:r24_sq", "I:m7_sq", "I:v7_sq", "I:r24xv7", "I:r24xq7", "I:m7xv7", "I:r4xt24", "I:m7xm30", "I:r24xv7xq7", "I:m7xv7xq7"]
    names = all_rank_names + H_names + I_names
    X = np.clip(np.concatenate([XR, Hs, Hp, I], 1), -10, 10).astype(np.float32)
    assert X.shape == (n_pairs, 89), X.shape
    fam_cols = {f: [j for j, n in enumerate(names) if n.startswith(f + ":")] for f in FAMS}
    fam_cols["Hs"] = [names.index("H:disp_z"), names.index("H:btcv_z")]
    assert all(len(fam_cols[f]) == k for f, k in zip(FAMS, (10, 8, 8, 9, 7, 9, 8, 10, 10, 10)))
    max_off.update({"H": 0, "I": 0})
    meta = dict(prereg_sha=PREREG_SHA, prereg_commit=PREREG_COMMIT, self_sha256=sha(os.path.abspath(__file__)), cache_sha256=sha(CACHE), targets_sha256=sha(TARGETS), fea82_sha256=sha(FEA82),
                n_pairs=int(n_pairs), n_anchors=int(nA), names=names, fam_cols=fam_cols, max_row_offset_vs_E=max_off, finite_share_raw=finite_share,
                struct_assert={"all_families_max_row_le_E": all(v <= 0 for v in max_off.values()), "E_samephase_windows_max_offset": sp_max_off,
                               "E_samephase_right_end_le_E_minus_240": sp_max_off <= -240, "J_lag_block_offsets": {"r4_lag_k": "[E+1-48k, E+1-48(k-1)) k>=2 => max row E-48",
                               "r24_lag1": "max row E-288", "drank_*": "anchor i-6 (E_ts-86400)"}, "state_z_causal": "shift(1).rolling(180)"},
                form="A-G,J: anchor rank [-0.5,0.5] (NaN->0); H: state z raw + rank*state products; I: rank products; clip ±10")
    np.savez(f"{OUT}/data/f8_fea89.npz", X=X, pair_a=pa.astype(np.int32), pair_s=ps.astype(np.int16), names=np.array(names), meta_json=json.dumps(meta))
    meta["fea89_sha256"] = sha(f"{OUT}/data/f8_fea89.npz")
    json.dump(meta, open(f"{OUT}/results/f8_build_report.json", "w"), indent=1)
    log("BUILD_DONE", X.shape, "max_off", max_off)
    log("finite share (raw, min 5):", sorted(finite_share.items(), key=lambda kv: kv[1])[:5])


# =====================================================================================
# run
# =====================================================================================
def arm_list():
    arms = [("base", None, None)] + [(f"+{f}", f, None) for f in FAMS] + [("+Hs", "Hs", None), ("+ALL", "ALL", None)]
    arms += [(f"PL_ALL_s{s}", "ALL", s) for s in range(5)] + [(f"PL_I_s{s}", "I", s) for s in range(5)]
    return arms


def run(models, only_arms=None):
    T = load_targets(); yrs = T["yrs"]; YRZ = T["YRZ"]; YR4s = T["YR4s"]; y4s = T["y4s"]; nA, NW = YRZ.shape
    X82, pa, ps, n82 = load_fea82()
    F9 = np.load(f"{OUT}/data/f8_fea89.npz", allow_pickle=True)
    X89 = F9["X"]; assert np.array_equal(F9["pair_a"].astype(np.int64), pa) and np.array_equal(F9["pair_s"].astype(np.int64), ps)
    meta = json.loads(str(F9["meta_json"])); fam_cols = meta["fam_cols"]; fam_cols["ALL"] = list(range(89))
    Y = YRZ[pa, ps]; okrow = np.isfinite(Y)
    X82 = X82[okrow].astype(np.float32); X89 = X89[okrow]; Y = Y[okrow].astype(np.float32); A = pa[okrow]; S = ps[okrow]; YRA = yrs[A]
    st = np.searchsorted(A, np.arange(nA + 1))
    log(f"rows {len(Y)} X82 {X82.shape} X89 {X89.shape}")
    arms = arm_list()
    if only_arms:
        arms = [a for a in arms if a[0] in only_arms]
    folds = []
    for YV in YEARS:
        te_anchor = np.where(yrs == YV)[0]; first_te = int(te_anchor[0])
        tr_ok = np.zeros(nA, bool); tr_ok[(yrs < YV) & (np.arange(nA) < first_te - EMBARGO)] = True
        folds.append((YV, te_anchor, tr_ok[A], YRA == YV))
    for model in models:
        icpa_path = f"{OUT}/results/f8_icpa_{model}.npz"
        ICR = {}; ICY = {}; byyear = {}
        if os.path.exists(icpa_path):
            old = np.load(icpa_path, allow_pickle=True); ICR = dict(old["icr"].item()); ICY = dict(old["icy"].item()); byyear = dict(old["byyear"].item())
        for arm, fam, seed in arms:
            if arm in ICR and not only_arms:
                log(f"[{model}] skip {arm} (done)"); continue
            t_arm = time.time()
            if fam is None:
                X = X82
            else:
                Xn = X89[:, fam_cols[fam]]
                if seed is not None:   # 安慰剂: 每锚成员内随机置换(同一置换作用于整块列)
                    rng = np.random.default_rng(1000 + seed); Xn = Xn.copy()
                    for i in range(nA):
                        sl = slice(st[i], st[i + 1])
                        if st[i + 1] - st[i] > 1:
                            Xn[sl] = Xn[sl][rng.permutation(st[i + 1] - st[i])]
                X = np.concatenate([X82, Xn], 1)
            P = np.full((nA, NW), np.nan, np.float32)
            icr = np.full(nA, np.nan); icy = np.full(nA, np.nan); byy = {}
            for YV, te_anchor, tr, te in folds:
                t1 = time.time()
                if model == "ridge":
                    mu = X[tr].mean(0); sd = X[tr].std(0) + 1e-9
                    Xs = np.clip((X[tr] - mu) / sd, -5, 5).astype(np.float64)
                    Xa = np.concatenate([Xs, np.ones((Xs.shape[0], 1))], 1)
                    G = Xa.T @ Xa; G[:-1, :-1] += RIDGE_ALPHA * np.eye(Xs.shape[1])
                    beta = np.linalg.solve(G, Xa.T @ Y[tr].astype(np.float64))
                    del Xs, Xa, G
                    Xt = np.clip((X[te] - mu) / sd, -5, 5).astype(np.float64)
                    pv = (np.concatenate([Xt, np.ones((Xt.shape[0], 1))], 1) @ beta).astype(np.float32); del Xt
                else:
                    import lightgbm as lgb
                    gbm = lgb.LGBMRegressor(**LGB_PARAMS).fit(X[tr], Y[tr])
                    pv = gbm.predict(X[te]).astype(np.float32)
                P[A[te], S[te]] = pv
                for i in te_anchor:
                    icr[i] = spear(P[i], YR4s[i]); icy[i] = spear(P[i], y4s[i])
                byy[str(YV)] = {"ic_resid": nanmean(icr[te_anchor]), "ic_raw": nanmean(icy[te_anchor]), "sec": round(time.time() - t1, 1)}
                log(f"[{model}] {arm} {YV} resid {byy[str(YV)]['ic_resid']:+.4f} raw {byy[str(YV)]['ic_raw']:+.4f} ({time.time()-t1:.0f}s)")
            ICR[arm] = icr; ICY[arm] = icy; byyear[arm] = byy
            if seed is None:
                np.save(f"{OUT}/preds/f8_{model}_{arm.replace('+','p')}.npy", P)
            np.savez(icpa_path, icr=np.array(ICR, dtype=object), icy=np.array(ICY, dtype=object), byyear=np.array(byyear, dtype=object))
            log(f"[{model}] {arm} DONE 年均 resid {np.mean([v['ic_resid'] for v in byy.values()]):+.4f} ({time.time()-t_arm:.0f}s)")
            del X, P
        log(f"RUN_DONE_{model}")


# =====================================================================================
# judge
# =====================================================================================
def xz(v):
    ok = np.isfinite(v); out = np.full(len(v), np.nan); n = int(ok.sum())
    if n >= 10:
        out[ok] = (rankdata(v[ok]) - (n + 1) / 2) / max(n - 1, 1)
    return out


def judge():
    T = load_targets(); yrs = T["yrs"]; YR4s = T["YR4s"]; y4s = T["y4s"]; MS = T["MS"]; E_ts = T["E_ts"]; btcv = T["btcv"]; nA, NW = YR4s.shape
    out = {"prereg_sha": PREREG_SHA, "prereg_commit": PREREG_COMMIT, "self_sha256": sha(os.path.abspath(__file__)),
           "inputs_sha256": {"targets": sha(TARGETS), "fea82": sha(FEA82), "fea89": sha(f"{OUT}/data/f8_fea89.npz")},
           "build_report": json.load(open(f"{OUT}/results/f8_build_report.json")), "models": {}, "receipts": {}, "gates": {}, "S1": {}}
    g0 = json.load(open(G0JSON))
    test = np.isin(yrs, YEARS)
    models = [m for m in ("ridge", "lgbm") if os.path.exists(f"{OUT}/results/f8_icpa_{m}.npz")]
    for model in models:
        Z = np.load(f"{OUT}/results/f8_icpa_{model}.npz", allow_pickle=True)
        ICR = dict(Z["icr"].item()); ICY = dict(Z["icy"].item()); byy = dict(Z["byyear"].item())
        base = ICR["base"]; Aset = test & np.isfinite(base)
        for a in ICR:
            Aset &= np.isfinite(ICR[a]) | ~test
        A_idx = np.where(Aset)[0]
        qb = np.quantile(btcv[Aset], [0.2, 0.4, 0.6, 0.8]); qg = np.full(nA, -1); qg[Aset] = np.digitize(btcv[Aset], qb)
        M = {"setA_n": int(Aset.sum()), "setA_by_year": {str(y): int((Aset & (yrs == y)).sum()) for y in YEARS}, "table": {}, "delta": {}, "placebo": {}}
        for a in ICR:
            r = {"ic_resid_A": nanmean(ICR[a][Aset]), "ic_raw_A": nanmean(ICY[a][Aset]),
                 "ic_resid_by_year": {str(y): nanmean(ICR[a][Aset & (yrs == y)]) for y in YEARS},
                 "ic_raw_by_year": {str(y): nanmean(ICY[a][Aset & (yrs == y)]) for y in YEARS},
                 "q4": nanmean(ICR[a][Aset & (qg == 4)]), "seg_2325": nanmean(ICR[a][Aset & (yrs <= 2024)]), "seg_2526": nanmean(ICR[a][Aset & (yrs >= 2025)])}
            M["table"][a] = r
            if a != "base":
                d = ICR[a] - base; pr = paired(d[Aset])
                pr["by_year"] = {str(y): nanmean(d[Aset & (yrs == y)]) for y in YEARS}
                pr["n_pos_years"] = int(sum(v > 0 for v in pr["by_year"].values() if np.isfinite(v)))
                pr["raw_mean"] = nanmean((ICY[a] - ICY["base"])[Aset]); pr["q4_delta"] = nanmean(d[Aset & (qg == 4)])
                pr["seg_2325"] = nanmean(d[Aset & (yrs <= 2024)]); pr["seg_2526"] = nanmean(d[Aset & (yrs >= 2025)])
                M["delta"][a] = pr
        for fam in ("ALL", "I"):
            ks = [a for a in M["delta"] if a.startswith(f"PL_{fam}_s")]
            if ks:
                v = [M["delta"][a]["mean"] for a in ks]
                M["placebo"][fam] = {"arms": ks, "deltas": v, "mean": float(np.mean(v)), "sd": float(np.std(v, ddof=1)) if len(v) > 1 else None,
                                     "by_year_mean": {str(y): float(np.mean([M["delta"][a]["by_year"][str(y)] for a in ks])) for y in YEARS}}
        # 门 §P.5
        gates = {}
        for a in M["delta"]:
            if a.startswith("PL_"):
                continue
            d = M["delta"][a]
            ok_d = d["mean"] >= 0.003; ok_f = d["n_pos_years"] >= 3
            gates[a] = {"delta": d["mean"], "t": d["t"], "n_pos_years": d["n_pos_years"], "pass": bool(ok_d and ok_f),
                        "verdict": ("PASS" if ok_d and d["n_pos_years"] == 4 else "CONDITIONAL_PASS_3of4" if ok_d and ok_f else "FAIL"),
                        "delta_minus_placebo_ALL": (d["mean"] - M["placebo"]["ALL"]["mean"]) if "ALL" in M["placebo"] else None}
        pl_ok = ("ALL" not in M["placebo"]) or (M["placebo"]["ALL"]["mean"] < 0.003)
        M["gates"] = gates; M["placebo_valid"] = bool(pl_ok)
        # R1 基线复现 vs dlw_g0.json
        key = "R82" if model == "ridge" else "L82"
        diffs = {str(y): {"resid": byy["base"][str(y)]["ic_resid"] - g0["arms"][key]["ic_resid_by_year"][str(y)],
                          "raw": byy["base"][str(y)]["ic_raw"] - g0["arms"][key]["ic_raw_by_year"][str(y)]} for y in YEARS}
        maxd = max(abs(v[k]) for v in diffs.values() for k in ("resid", "raw"))
        M["R1_base_vs_dlw_g0"] = {"by_year_diff": diffs, "max_abs_diff": float(maxd), "pass": bool(maxd <= 1e-4)}
        out["models"][model] = M
    # ---- R3/R4 + S1 on +ALL preds
    K0 = np.load(f"{K0DIR}/slow_pred_hist_oos.npy"); MT = np.load(f"{K0DIR}/wide_fea_hist_meta.npz", allow_pickle=True)
    krow = {int(t): j for j, t in enumerate(MT["E_ts"].astype(np.int64))}
    for model in models:
        pA = f"{OUT}/preds/f8_{model}_pALL.npy"; pB = f"{OUT}/preds/f8_{model}_base.npy"
        if not (os.path.exists(pA) and os.path.exists(pB)):
            continue
        PA = np.load(pA); PB = np.load(pB)
        M = out["models"][model]
        Aset = test.copy()
        icr = np.full(nA, np.nan)
        for i in np.where(test)[0]:
            m = MS[i]; icr[i] = spear(PA[i, m], YR4s[i, m])
        Aset &= np.isfinite(icr); A_idx = np.where(Aset)[0]
        # R3 shuffle null(同年锚内置换目标)
        nulls = []
        for s in range(3):
            rs = np.random.default_rng(s); v = []
            for y in YEARS:
                ia = np.where(Aset & (yrs == y))[0]; perm = rs.permutation(ia)
                for i, j in zip(ia[::2], perm[::2]):
                    m = MS[i]; v.append(spear(PA[i, m], YR4s[j, m]))
            nulls.append(nanmean(v))
        se = float(np.nanstd(icr[Aset]) / np.sqrt(Aset.sum()))
        # R4 偏移谱
        spec = {}
        for k in range(-6, 7):
            v = []
            for i in A_idx[::4]:
                j = i + k
                if 0 <= j < nA:
                    m = MS[i]; v.append(spear(PA[i, m], YR4s[j, m]))
            spec[str(k)] = nanmean(v)
        peak = max(spec, key=lambda kk: spec[kk] if np.isfinite(spec[kk]) else -9)
        out["receipts"][model] = {"R3_shuffle_null": {"per_seed": nulls, "mean": float(np.mean(nulls)), "se_true": se, "pass": bool(abs(np.mean(nulls)) < 2 * se)},
                                  "R4_offset_spectrum": {"spec": spec, "peak_k": int(peak), "pass": int(peak) == 0}}
        # S1 对宽 king: 配对差 / 绝对 / 残差式
        s1 = {"n": 0}; blend_c, blend_c0, k_only, resid_ic, yy = [], [], [], [], []
        for i in A_idx:
            j = krow.get(int(E_ts[i]))
            if j is None:
                continue
            m = MS[i]; k = K0[j, m]; c = PA[i, m]; c0 = PB[i, m]; y = YR4s[i, m]
            ok = np.isfinite(k) & np.isfinite(c) & np.isfinite(c0) & np.isfinite(y)
            if ok.sum() < 30:
                continue
            zk = xz(np.where(ok, k, np.nan))[ok]; zc = xz(np.where(ok, c, np.nan))[ok]; zc0 = xz(np.where(ok, c0, np.nan))[ok]; yo = y[ok]
            blend_c.append(spear(0.7 * zk + 0.3 * zc, yo)); blend_c0.append(spear(0.7 * zk + 0.3 * zc0, yo)); k_only.append(spear(zk, yo))
            Xr = np.stack([np.ones(ok.sum()), zk, zc0], 1); beta = np.linalg.lstsq(Xr, zc, rcond=None)[0]
            resid_ic.append(spear(zc - Xr @ beta, yo)); yy.append(yrs[i])
        yy = np.array(yy); bc = np.array(blend_c); bc0 = np.array(blend_c0); ko = np.array(k_only); ri = np.array(resid_ic)
        d = bc - bc0; pr = paired(d); pr["by_year"] = {str(y): nanmean(d[yy == y]) for y in YEARS}
        s1 = {"n": int(len(yy)), "ic_K0": nanmean(ko), "blend_c_minus_K0": nanmean(bc - ko), "blend_c0_minus_K0": nanmean(bc0 - ko),
              "paired_delta_blend(c vs c0)": pr, "by_year_abs_c": {str(y): nanmean((bc - ko)[yy == y]) for y in YEARS},
              "by_year_abs_c0": {str(y): nanmean((bc0 - ko)[yy == y]) for y in YEARS},
              "resid_form_ic(c | 1,zK0,zc0)": nanmean(ri), "resid_by_year": {str(y): nanmean(ri[yy == y]) for y in YEARS},
              "pass": bool(pr["mean"] >= 0.003 and all(v >= 0 for v in pr["by_year"].values() if np.isfinite(v)))}
        out["S1"][model] = s1
    # ---- 总判
    verdict = {}
    for model in models:
        G = out["models"][model]["gates"]
        verdict[model] = {"families_pass": [a for a in G if a not in ("+ALL", "+Hs") and G[a]["pass"]], "ALL_pass": bool(G.get("+ALL", {}).get("pass", False)),
                          "Hs_pass": bool(G.get("+Hs", {}).get("pass", False)), "placebo_valid": out["models"][model]["placebo_valid"],
                          "S1_pass": bool(out["S1"].get(model, {}).get("pass", False)) if model in out["S1"] else None}
    if len(models) == 2:
        both = [a for a in verdict["ridge"]["families_pass"] if a in verdict["lgbm"]["families_pass"]]
        only_r = [a for a in verdict["ridge"]["families_pass"] if a not in verdict["lgbm"]["families_pass"]]
        only_l = [a for a in verdict["lgbm"]["families_pass"] if a not in verdict["ridge"]["families_pass"]]
        anyp = verdict["ridge"]["families_pass"] or verdict["lgbm"]["families_pass"] or verdict["ridge"]["ALL_pass"] or verdict["lgbm"]["ALL_pass"]
        if both and (verdict["ridge"]["ALL_pass"] or verdict["lgbm"]["ALL_pass"]) and (verdict["ridge"]["S1_pass"] or verdict["lgbm"]["S1_pass"]):
            form = "(a) 有用"
        elif not anyp:
            form = "(b) 无用(第四证)"
        else:
            form = "(c) 部分"
        verdict["three_way"] = {"form": form, "both_models": both, "ridge_only": only_r, "lgbm_only": only_l}
    out["verdict"] = verdict
    json.dump(out, open(f"{OUT}/results/f8_higher_order_features_2026-08-22.json", "w"), indent=1)
    # ---- 终端表
    for model in models:
        M = out["models"][model]
        print(f"\n===== F-8 [{model}] 残差秩 IC(集 A n={M['setA_n']}); Δ = 臂 − base(配对) =====")
        print(f"{'arm':<12s}{'IC_A':>9s}{'Δ':>9s}{'t':>7s}{'同号':>5s}" + "".join(f"{y:>9d}" for y in YEARS) + f"{'Q4Δ':>9s}{'rawΔ':>9s}  gate")
        b = M["table"]["base"]
        print(f"{'base':<12s}{b['ic_resid_A']:>+9.4f}{'':>9s}{'':>7s}{'':>5s}" + "".join(f"{b['ic_resid_by_year'][str(y)]:>+9.4f}" for y in YEARS))
        for a, d in M["delta"].items():
            g = M["gates"].get(a, {}).get("verdict", "")
            print(f"{a:<12s}{M['table'][a]['ic_resid_A']:>+9.4f}{d['mean']:>+9.4f}{d['t']:>+7.1f}{d['n_pos_years']:>4d}/4" + "".join(f"{d['by_year'][str(y)]:>+9.4f}" for y in YEARS) + f"{d['q4_delta']:>+9.4f}{d['raw_mean']:>+9.4f}  {g}")
        print("placebo:", json.dumps({k: {"mean": round(v["mean"], 5), "sd": None if v["sd"] is None else round(v["sd"], 5)} for k, v in M["placebo"].items()}))
        print("R1:", json.dumps(M["R1_base_vs_dlw_g0"]["max_abs_diff"]), "receipts:", json.dumps(out["receipts"].get(model, {}), default=str)[:400])
        print("S1:", json.dumps(out["S1"].get(model, {}), default=str)[:900])
    print("\nVERDICT:", json.dumps(verdict, ensure_ascii=False))
    log("JUDGE_DONE")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("stage", choices=["build", "run", "judge"]); ap.add_argument("--models", default="ridge,lgbm"); ap.add_argument("--arms", default="")
    a = ap.parse_args()
    if a.stage == "build":
        build()
    elif a.stage == "run":
        run(a.models.split(","), [x for x in a.arms.split(",") if x] or None)
    else:
        judge()
