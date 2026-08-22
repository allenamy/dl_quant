"""F2 · basis/溢价载体腿录取装置(2026-08-22, Session 6737834a-F2)。预注册 = PREREG_RESULT_F2_basis_leg_admission_2026-08-22.md §P(冻结段 SHA e3abbd11…, commit c022855, 先于数字)。
SHA256: 脚本自身 / WA 模块 / 全部输入 在运行时写入结果 JSON(`self_sha256` / `wa_module_sha256` / `input_sha256`); 文档引用以 JSON 为准。

【对象】宽书 W-b 链(WA `wide_full_caliber_audit.py` run_chain 语义)推广到 K 腿(`run_chain_k`): 腿 = king / rev24 / fund / basis(第四槽);
  w 模式: base(三腿走前 msharpe, basis=0; ≡ WA) · fix(三腿 (1−w4)×msharpe 份额, basis=w4) · ms4(四腿走前 msharpe)
          nofund(WA 同式: msharpe 三腿后 fund 置 0 重归一) · nofund_fix((1−w4)×nofund 份额 + basis w4) · nofund_ms(msharpe over king,rev24,basis)
  其余(去均值/L1/cap 2.5/n/止损 d30_n2_c42/EMA α0.1/带 2.5e-4/记账/夏普/CI)逐字继承 WA。
【候选】PREM(open=T−1h 的 1h bar close); 形态 OK(⟂fund_ema,fund_now,king; 主) / OF(⟂fund_ema) / RAW / OK_ema24 / OK_chg24 / OK_z168; sign −1 固定; 4h 刷新(主), 8h 保持臂对照; 同槽位安慰剂种子 0-4。
【门】S1 = FF s1_gate 逐字(0.7/0.3 z 混合 dIC, 逐年≥0 且年均≥+0.003; U400); S2 = RC gfam 逐字(Δ净@4.137 5 锚块 CI>0 ∧ Δ@6.23≥0 ∧ 逐年≥4/5 ∧ 夏普不降; 净@2 序列); G0/G1 尺子(腿录取门 v2)。
【收据】R1 base 链权重 ≡ wa_weights_Wb_d30.npz(max|Δw|<1e-6)且净@2 夏普 2022-01..2026-06 = 1.668; R2 vision premium vs fapi basis_premium_1h(140) 重叠格 Pearson/|Δ| 中位; R3 fix w4=0 ≡ base。
用法 @jpline: python f2_basis_leg_admission.py run [--smoke N] [--nw 12]
"""
import os, sys, json, time, hashlib, math, datetime as dt
import numpy as np
import pandas as pd
from scipy.stats import rankdata, spearmanr

T0 = time.time()
def log(*a): print(f"[{time.time()-T0:8.1f}s]", *a, flush=True)
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 24), b""): h.update(chunk)
    return h.hexdigest()
HERE = os.path.dirname(os.path.abspath(__file__)); SELF_SHA = sha(os.path.abspath(__file__))
ON_JP = os.path.exists("/mnt/storage/private/work_hsy")
PD = "/mnt/storage/private/work_hsy/probe_artifacts" if ON_JP else None
WA_PATH = None
for cand in (HERE, os.path.join(HERE, "..", "wa"), (f"{PD}/wa" if PD else HERE)):
    if os.path.exists(os.path.join(cand, "wide_full_caliber_audit.py")):
        sys.path.insert(0, cand); WA_PATH = os.path.join(cand, "wide_full_caliber_audit.py"); break
import wide_full_caliber_audit as WAM
from wide_full_caliber_audit import (xz, sharpe_a, sharpe_d, boot_sharpe_ci, boot_delta_sharpe, quintile_table, summarize, yr_of, fmt, maxdd, anchors_grid, A_T0, A_T1, H4, COST_MAIN)
WA_SHA = sha(WA_PATH)
if "c6.23" not in WAM.COST_ARMS: WAM.COST_ARMS["c6.23"] = 6.23          # G 族高档(RC), 追加到 WA 成本臂
COST_ARMS = WAM.COST_ARMS
if ON_JP:
    B = "/mnt/storage/private/work_hsy/pod_backup_2026-08-21"; WA = f"{PD}/wa"; F2 = f"{PD}/f2"; os.makedirs(F2, exist_ok=True)
PREREG_SHA = "e3abbd11c33e9d3a76abe79f8b7a2b05f0912586c1ecb60dcf8fe4dc7fd5d035"
STOP = (-0.30, 2, 42); LOOK = 900; H1 = 3600
T_END_MAIN = int(dt.datetime(2026, 6, 30, 23, tzinfo=dt.timezone.utc).timestamp())
T_END_FULL = int(dt.datetime(2026, 7, 31, 23, tzinfo=dt.timezone.utc).timestamp())      # premium 月度 zip 覆盖到 2026-07; FULL 截到此
LEGS = ("king", "rev24", "fund", "basis")
C_MAIN, C_T1, C_HI = 4.137, 3.52, 6.23
ANN = math.sqrt(2190)

# ───────────────────────────────────────────── small helpers (FF verbatim)
def xrank(v):
    ok = np.isfinite(v); out = np.full(len(v), np.nan)
    if ok.sum() >= 2: out[ok] = rankdata(v[ok]) / ok.sum() - 0.5 - 0.5 / ok.sum()
    return out
def rank_center(v):
    """秩中心化 ∈ (−0.5, 0.5), NaN 保持."""
    ok = np.isfinite(v); out = np.full(len(v), np.nan)
    if ok.sum() >= 2: out[ok] = (rankdata(v[ok]) - (ok.sum() + 1) / 2) / max(ok.sum() - 1, 1)
    return out
def zsc(v):
    ok = np.isfinite(v); out = np.full(len(v), np.nan)
    if ok.sum() >= 2 and np.nanstd(v[ok]) > 1e-12: out[ok] = (v[ok] - v[ok].mean()) / v[ok].std()
    return out
def spear(x, y, mn=10):
    ok = np.isfinite(x) & np.isfinite(y)
    if ok.sum() < mn: return np.nan
    return float(np.corrcoef(rankdata(x[ok]), rankdata(y[ok]))[0, 1])
def tstat(x, k=1):
    x = np.asarray(x, float); x = x[np.isfinite(x)]
    if len(x) < 3: return np.nan
    return float(x.mean() / (x.std(ddof=1) + 1e-30) * np.sqrt(len(x) / k))
def summ_ic(x, yr, k=1):
    """FF summ 逐字."""
    x = np.asarray(x, float)
    d = {"n": int(np.isfinite(x).sum()), "mean": float(np.nanmean(x)), "t": tstat(x, k), "sharpe": float(np.nanmean(x) / (np.nanstd(x, ddof=1) + 1e-30) * ANN), "by_year": {}}
    for y in sorted(set(yr.tolist())):
        s = x[yr == y]
        d["by_year"][int(y)] = {"mean": float(np.nanmean(s)) if np.isfinite(s).any() else None, "t": tstat(s, k), "n": int(np.isfinite(s).sum()), "sharpe": float(np.nanmean(s) / (np.nanstd(s, ddof=1) + 1e-30) * ANN) if np.isfinite(s).sum() > 2 else None}
    return d
def lsq_resid_multi(y, X):
    """y (n,), X (n,k) 已含常数列; 对有限行做 LSQ, 返回残差(NaN 处保持 NaN)."""
    ok = np.isfinite(y) & np.all(np.isfinite(X), 1); r = np.full(len(y), np.nan)
    if ok.sum() < 5 + X.shape[1]: return r
    b, *_ = np.linalg.lstsq(X[ok], y[ok], rcond=None); r[ok] = y[ok] - X[ok] @ b
    return r
def boot_mean_ci(d, nb=2000, bl=5, seed=41):
    """RC gfam 同式: 5 锚块自助, 2000 次, Δ均值 CI95."""
    rng = np.random.default_rng(seed); L = len(d); k = int(np.ceil(L / bl)); o = np.empty(nb)
    for q in range(nb):
        st = rng.integers(0, max(L - bl, 1), size=k)
        ix = (st[:, None] + np.arange(bl)[None, :]).ravel()[:L]; ix = ix[ix < L]
        o[q] = d[ix].mean()
    return float(np.percentile(o, 2.5)), float(np.percentile(o, 97.5))
def gfam(p, t, p0, t0_, yr):
    """RC 逐字: G 族判据(Δ净@4.137 CI 下界>0 且 @6.23≥0 且 逐年≥4/5 且 夏普不降)+ 三档成本 Δ. p/t = 臂 (pnl−carry)@2 与 换手@2; p0/t0_ = 底座."""
    out = {}
    for c, tag in ((C_MAIN, "4.137"), (C_T1, "3.52"), (C_HI, "6.23")):
        d = (p - t * c) - (p0 - t0_ * c)
        out[f"dnet@{tag}"] = round(float(d.mean()), 4)
        if tag == "4.137":
            lo, hi = boot_mean_ci(d); out["dnet@4.137_CI95"] = [round(lo, 4), round(hi, 4)]
            dfy = pd.Series(d).groupby(yr).mean()
            out["dnet_by_year@4.137"] = {int(k): round(float(v), 4) for k, v in dfy.items()}
            out["n_years_nonneg"] = int((dfy >= 0).sum()); out["n_years"] = int(len(dfy))
            out["sharpe_arm@4.137"] = round(sharpe_a(p - t * c), 3); out["sharpe_base@4.137"] = round(sharpe_a(p0 - t0_ * c), 3)
    out["net_arm@4.137"] = round(float((p - t * C_MAIN).mean()), 4); out["net_base@4.137"] = round(float((p0 - t0_ * C_MAIN).mean()), 4)
    out["net_arm@3.52"] = round(float((p - t * C_T1).mean()), 4); out["net_base@3.52"] = round(float((p0 - t0_ * C_T1).mean()), 4)
    out["sharpe_arm@3.52"] = round(sharpe_a(p - t * C_T1), 3); out["sharpe_base@3.52"] = round(sharpe_a(p0 - t0_ * C_T1), 3)
    out["G_PASS"] = bool(out["dnet@4.137_CI95"][0] > 0 and out["dnet@6.23"] >= 0 and out["n_years_nonneg"] >= 4 and out["sharpe_arm@4.137"] >= out["sharpe_base@4.137"])
    return out

# ───────────────────────────────────────────── K-leg chain (WA.run_chain 逐语句推广; K=3 且 basis 权重 0 ⇒ 与 WA 逐位同)
def run_chain_k(D, RET, CAND, wmode="base", w4=0.0, stop=STOP, tag="", record_from=None):
    """D 同 WA(E_ts, members, SLOW, R24, FE, qvk, pw_row, NW, apos); CAND (nE, NW) 第四腿分数(已带符号, NaN=缺失) 或 None.
    wmode ∈ {base, fix, ms4, nofund, nofund_fix, nofund_ms}. 返回 ts/W/WL(K=4)/w4(权重序列)/skipped/fires."""
    NW = D["NW"]; alpha = 0.1; band = 2.5e-4; capm = 2.5; look = LOOK; K = 4
    depth, need, cool = stop if stop else (None, 0, 0)
    H = np.zeros(NW); HL = np.zeros((K, NW)); Pi = np.ones(NW); sh = np.zeros(NW); cb = np.zeros(NW); cnt = np.zeros(NW, int); su = np.full(NW, -1)
    LR = {l: [] for l in LEGS}
    recs = []; W = []; WL = []; WK = []; skipped = 0; nfires = 0; fires_ts = []
    E_ts = D["E_ts"]; rf = 0 if record_from is None else record_from
    for j in range(len(E_ts)):
        T = int(E_ts[j]); jp = D["pw_row"].get(T); ai = D["apos"].get(T)
        if jp is None or ai is None: continue
        m = D["members"][j]
        sc = {"king": D["SLOW"][j, m], "rev24": -D["R24"][jp, m], "fund": D["FE"][jp, m], "basis": (CAND[j, m] if CAND is not None else np.full(len(m), np.nan))}
        yv_m = RET[ai, m].astype(float)
        ok = np.isfinite(yv_m); yv0 = np.where(ok, yv_m, 0.0)
        for leg in LEGS:
            z = np.nan_to_num(xz(sc[leg])); z = np.where(ok, z, 0.0); z -= (z[ok].mean() if ok.sum() else 0.0); g = np.abs(z).sum()
            LR[leg].append(float((z / g * yv0).sum() * 1e4) if g > 1e-9 else 0.0)
        p = len(LR["king"]) - 1
        def msharpe(names):
            if p >= look:
                r = np.stack([np.array(LR[l][p - look:p]) for l in names]); shp = np.maximum(r.mean(1) / (r.std(1) + 1e-9), 0.0)
                return shp / shp.sum() if shp.sum() > 0 else np.full(len(names), 1.0 / len(names))
            return np.full(len(names), 1.0 / len(names))
        w3 = msharpe(("king", "rev24", "fund"))
        if wmode == "base":
            wk = np.array([w3[0], w3[1], w3[2], 0.0])
        elif wmode == "fix":
            wk = np.array([(1 - w4) * w3[0], (1 - w4) * w3[1], (1 - w4) * w3[2], w4])
        elif wmode == "ms4":
            w = msharpe(LEGS); wk = np.array(w)
        elif wmode in ("nofund", "nofund_fix"):
            wn = np.array([w3[0], w3[1], 0.0]); wn = wn / wn.sum() if wn.sum() > 0 else np.array([0.5, 0.5, 0.0])
            wk = np.array([wn[0], wn[1], 0.0, 0.0]) if wmode == "nofund" else np.array([(1 - w4) * wn[0], (1 - w4) * wn[1], 0.0, w4])
        elif wmode == "nofund_ms":
            w = msharpe(("king", "rev24", "basis")); wk = np.array([w[0], w[1], 0.0, w[2]])
        else:
            raise ValueError(wmode)
        qv4h = np.expm1(np.clip(D["qvk"][j, m], 0, 30)) * 48
        sel = ok & (qv4h >= 2.5e5)
        zk = np.stack([wkk * np.nan_to_num(xz(sc[l])) for wkk, l in zip(wk, LEGS)])      # (K, nm)
        if sel.sum() < 80:
            skipped += 1; tgt_k = np.zeros((K, NW)); do_trade = False
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
                tgt_k = np.zeros((K, NW)); tgt_k[:, m] = zk
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
            recs.append(T); W.append(H.astype(np.float32)); WL.append(HL.astype(np.float32)); WK.append(wk)
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
            if fire.any(): su[fire] = j + cool; cnt[fire] = 0; nfires += int(fire.sum()); fires_ts.append((T, int(fire.sum())))
        Pi = Pi * (1.0 + yfull)
    W = np.stack(W); WL = np.stack(WL)
    assert np.abs(WL.sum(1) - W).max() < 1e-5, "leg decomposition not additive"
    return {"ts": np.array(recs, np.int64), "W": W, "WL": WL, "wk": np.array(WK), "skipped": skipped, "fires": nfires}

# ───────────────────────────────────────────── accounting (WA.account 逐字, 腿名推广)
def account_k(W, ts, F, RET, LRET, WL=None, cost_c=COST_MAIN, leg_names=LEGS):
    n, NW = W.shape
    R = np.nan_to_num(RET); L = np.nan_to_num(LRET); finR = np.isfinite(RET)
    pnl = (W * R).sum(1) * 1e4; pnl_log = (W * L).sum(1) * 1e4
    conv = pnl - pnl_log; conv_long = (np.where(W > 0, W, 0) * (R - L)).sum(1) * 1e4; conv_short = (np.where(W < 0, W, 0) * (R - L)).sum(1) * 1e4
    unc_ret = (np.abs(W) * (~finR)).sum(1)
    FR = F["fr_sum"]; carry = (W * FR).sum(1) * 1e4
    lr = np.nan_to_num(F["last_rate"]); iv = np.where(np.isfinite(F["last_iv"]) & (F["last_iv"] > 0), F["last_iv"], 8.0); age = F["last_age_h"]
    fresh = np.isfinite(age) & (age <= 12.0)
    carry_pred = (W * np.where(fresh, lr, 0.0) * (4.0 / iv)).sum(1) * 1e4
    unc_carry = (np.abs(W) * (~F["cov"])).sum(1)
    Wp = np.vstack([np.zeros((1, NW), W.dtype), W[:-1]]); dW = np.abs(W - Wp); trn = dW.sum(1)
    gross = np.abs(W).sum(1); nheld = (np.abs(W) > 1e-9).sum(1)
    long_pnl = (np.where(W > 0, W, 0) * R).sum(1) * 1e4; short_pnl = (np.where(W < 0, W, 0) * R).sum(1) * 1e4
    out = {"ts": ts, "pnl": pnl, "pnl_log": pnl_log, "conv": conv, "conv_long": conv_long, "conv_short": conv_short, "carry": carry, "carry_pred": carry_pred, "unc_ret": unc_ret, "unc_carry": unc_carry,
           "trn": trn, "gross": gross, "nheld": nheld, "long_pnl": long_pnl, "short_pnl": short_pnl, "cost": cost_c * trn}
    for k, c in COST_ARMS.items(): out[f"cost_{k}"] = c * trn
    out["net"] = pnl - carry - out["cost"]
    with np.errstate(all="ignore"):
        g = np.where(gross > 1e-9, gross, np.nan)
    out["net_pg"] = np.nan_to_num(out["net"] / g); out["net_g2"] = 2.0 * out["net_pg"]
    out["pnl_g2"] = 2.0 * np.nan_to_num(pnl / g); out["carry_g2"] = 2.0 * np.nan_to_num(carry / g); out["cost_g2"] = 2.0 * np.nan_to_num(out["cost"] / g)
    out["p_g2"] = 2.0 * np.nan_to_num((pnl - carry) / g); out["t_g2"] = 2.0 * np.nan_to_num(trn / g)      # G 族输入: 价差扣 carry / 换手 @2
    if WL is not None:
        out["legs"] = {}
        dWL = np.abs(WL - np.concatenate([np.zeros((1,) + WL.shape[1:], WL.dtype), WL[:-1]]))
        with np.errstate(all="ignore"):
            share = np.where(dWL.sum(1, keepdims=True) > 1e-15, dWL / dWL.sum(1, keepdims=True), 1.0 / len(leg_names))
        for k, leg in enumerate(leg_names):
            Wk = WL[:, k, :]
            out["legs"][leg] = {"pnl": (Wk * R).sum(1) * 1e4, "carry": (Wk * FR).sum(1) * 1e4, "cost": cost_c * (share[:, k, :] * dW).sum(1), "gross": np.abs(Wk).sum(1), "conv": (Wk * (R - L)).sum(1) * 1e4}
            out["legs"][leg]["net"] = out["legs"][leg]["pnl"] - out["legs"][leg]["carry"] - out["legs"][leg]["cost"]
    return out

# ───────────────────────────────────────────── S1 (FF s1_gate 逐字; 年份 ≥100 锚)
def s1_gate(cand, K, U, R, yr, A):
    n = len(A); dic = np.full(n, np.nan); icr = np.full(n, np.nan); ick = np.full(n, np.nan); icc = np.full(n, np.nan); cov = np.full(n, np.nan)
    for i in range(n):
        u = U[i]
        if u.sum() == 0: continue
        cov[i] = float(np.isfinite(cand[i][u]).mean())
        m = u & np.isfinite(K[i]) & np.isfinite(cand[i]) & np.isfinite(R[i])
        if m.sum() < 30: continue
        zk = zsc(np.where(m, K[i], np.nan)); zc = zsc(np.where(m, cand[i], np.nan))
        if not (np.isfinite(zk[m]).all() and np.isfinite(zc[m]).all()): continue
        b = 0.7 * zk + 0.3 * zc
        ick[i] = spear(zk[m], R[i][m]); icc[i] = spear(zc[m], R[i][m]); dic[i] = spear(b[m], R[i][m]) - ick[i]
        x = xrank(np.where(m, K[i], np.nan))[m]; y = xrank(np.where(m, R[i], np.nan))[m]
        beta = float(np.dot(x, y) / (np.dot(x, x) + 1e-30)); icr[i] = spear(cand[i][m], y - beta * x)
    yrs_ok = [y for y in sorted(set(yr.tolist())) if np.isfinite(dic[yr == y]).sum() >= 100]
    by = {int(y): float(np.nanmean(dic[yr == y])) for y in yrs_ok}
    mean = float(np.nanmean([v for v in by.values()])) if by else np.nan
    reg = {"2022-23": float(np.nanmean(dic[yr <= 2023])) if np.isfinite(dic[yr <= 2023]).any() else None, "2024-26": float(np.nanmean(dic[yr >= 2024])) if np.isfinite(dic[yr >= 2024]).any() else None}
    return {"dIC_blend_0.7_0.3": summ_ic(dic, yr), "dIC_year_mean_of_years": mean, "dIC_by_year": by, "dIC_regime": reg,
            "pass": bool(by and mean >= 0.003 and all(v >= 0 for v in by.values())),
            "ic_king": summ_ic(ick, yr), "ic_cand": summ_ic(icc, yr), "ic_cand_on_king_resid": summ_ic(icr, yr), "years_evaluated": yrs_ok,
            "cand_coverage_of_U400_mean": float(np.nanmean(cov)), "cand_coverage_by_year": {int(y): float(np.nanmean(cov[yr == y])) for y in sorted(set(yr.tolist()))}, "series": {"dic": dic, "icc": icc, "icr": icr, "ick": ick}}

# ───────────────────────────────────────────── jobs
_G = {}
JOBS = {}
def _job(name):
    a = JOBS[name]; t0 = time.time()
    out = run_chain_k(_G["D"], _G["RET"], (_G["CAND"][a["cand"]] if a["cand"] else None), wmode=a["wmode"], w4=a.get("w4", 0.0), stop=a["stop"], tag=name, record_from=_G["rec_from"])
    out["secs"] = time.time() - t0
    return name, out

def stage_run(nw=12, smoke=0):
    R = {"session": "6737834a-F2", "created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "self_sha256": SELF_SHA, "wa_module_sha256": WA_SHA, "prereg_section_sha256": PREREG_SHA, "smoke": smoke}
    INPUTS = {"close1h": f"{WA}/close1h_829.npz", "funding": f"{WA}/funding_829.npz", "meta": f"{B}/wide_fea_hist_meta.npz", "panel_v2": f"{B}/wide_panel_4h_hist_v2.npz", "slow_pred": f"{B}/slow_pred_hist_oos.npy",
              "wa_weights_Wb_d30": f"{WA}/wa_weights_Wb_d30.npz", "wa_series": f"{WA}/wa_series.npz", "premium_829": f"{F2}/premium_1h_829.npz", "premium_829_report": f"{F2}/premium_1h_829_report.json",
              "basis_fapi_140": f"{PD}/basis_premium_1h.npz"}
    R["input_sha256"] = {k: (sha(v) if os.path.exists(v) else None) for k, v in INPUTS.items()}; log("input shas done")
    # ---- returns grid (WA verbatim)
    Z = np.load(INPUTS["close1h"], allow_pickle=True); hts = Z["ts"].astype(np.int64); syms = [str(s) for s in Z["symbols"]]; C = Z["close"]; NW = len(syms)
    hpos = {int(t): i for i, t in enumerate(hts)}
    A = anchors_grid(int(dt.datetime(2021, 1, 1, tzinfo=dt.timezone.utc).timestamp()), A_T1); nA = len(A); apos = {int(t): i for i, t in enumerate(A)}
    i0 = np.array([hpos[int(t)] for t in A]); i1 = i0 + 4
    with np.errstate(all="ignore"):
        RET = (C[i1] / C[i0] - 1.0).astype(np.float64); LRET = np.log(C[i1] / C[i0])
    RET[~np.isfinite(RET)] = np.nan; LRET[~np.isfinite(LRET)] = np.nan
    FZ = np.load(INPUTS["funding"], allow_pickle=True); assert np.array_equal(FZ["anchors"].astype(np.int64), A) and [str(s) for s in FZ["symbols"]] == syms
    F = {k: FZ[k] for k in ("fr_sum", "nset", "last_rate", "last_iv", "last_age_h", "cov")}
    MT = np.load(INPUTS["meta"], allow_pickle=True); E_ts = MT["E_ts"].astype(np.int64); members = MT["members"]; qvk = MT["qvk"]
    PW = np.load(INPUTS["panel_v2"], allow_pickle=True); assert [str(s) for s in PW["symbols"]] == syms
    pw_row = {int(t): j for j, t in enumerate(PW["ts"].astype(np.int64))}
    SLOW = np.load(INPUTS["slow_pred"]); FE_all = PW["f_fund_ema_v1"]; FN_all = PW["f_fund_now"]
    D = {"E_ts": E_ts, "members": members, "SLOW": SLOW, "R24": PW["f_rev_24h"], "FE": FE_all, "qvk": qvk, "pw_row": pw_row, "NW": NW, "apos": apos}
    mrow = {int(t): j for j, t in enumerate(E_ts)}
    mkt = np.full(nA, np.nan)
    for i, t in enumerate(A):
        j = mrow.get(int(t))
        if j is None: continue
        v = RET[i, members[j]]; v = v[np.isfinite(v)]
        if len(v): mkt[i] = v.mean() * 1e4
    rec_from = int(np.searchsorted(E_ts, A_T0))
    log("returns grid", RET.shape, "E_ts", len(E_ts), "rec_from", rec_from)
    # ---- premium (vision 829) + R2 vs fapi 140
    PZ = np.load(INPUTS["premium_829"], allow_pickle=True); pts = PZ["ts_hour"].astype(np.int64) // 1000; assert [str(s) for s in PZ["symbols"]] == syms
    assert np.array_equal(pts, hts), "premium grid != close1h grid"
    PREM = PZ["PREM"].astype(np.float64)        # 行 i = open time hts[i] 的 bar close(于 hts[i]+1h 已知)
    prep = json.load(open(INPUTS["premium_829_report"])) if os.path.exists(INPUTS["premium_829_report"]) else {}
    R["premium_report"] = {k: prep.get(k) for k in ("n_hours", "n_symbols", "symbols_with_data", "zips_total", "finite_frac", "dup_cells", "symbols_without_data")}
    BF = np.load(INPUTS["basis_fapi_140"], allow_pickle=True); bts = BF["ts_hour"].astype(np.int64) // 1000; bsym = [str(x) for x in BF["symbols"]]; BP = BF["PREM"].astype(np.float64)
    brow = {int(t): i for i, t in enumerate(bts)}; ri = np.array([brow.get(int(t), -1) for t in hts]); okr = ri >= 0; cj = np.array([syms.index(s) for s in bsym])
    Xv = PREM[np.ix_(np.where(okr)[0], cj)]; Xf = BP[ri[okr]]
    both = np.isfinite(Xv) & np.isfinite(Xf); d = np.abs(Xv[both] - Xf[both])
    R["receipt_R2_premium_vision_vs_fapi140"] = {"n_cells_both_finite": int(both.sum()), "pearson": float(np.corrcoef(Xv[both], Xf[both])[0, 1]) if both.sum() > 10 else None, "median_absdiff": float(np.median(d)) if len(d) else None,
                                                 "p99_absdiff": float(np.percentile(d, 99)) if len(d) else None, "maxabs": float(d.max()) if len(d) else None,
                                                 "frac_vision_finite_where_fapi_finite": float(np.isfinite(Xv[np.isfinite(Xf)]).mean()), "frac_fapi_finite_where_vision_finite": float(np.isfinite(Xf[np.isfinite(Xv)]).mean()),
                                                 "pass_pearson_ge_0.999_median_lt_1e-6": bool(both.sum() > 10 and np.corrcoef(Xv[both], Xf[both])[0, 1] >= 0.999 and np.median(d) < 1e-6)}
    log("RECEIPT R2", R["receipt_R2_premium_vision_vs_fapi140"])
    # ---- hourly-derived variants (pandas, ≤t)
    dfP = pd.DataFrame(PREM)
    EMA24 = dfP.ewm(span=24, adjust=False, ignore_na=True, min_periods=24).mean().to_numpy()
    CHG24 = (dfP - dfP.shift(24)).to_numpy()
    roll = dfP.rolling(168, min_periods=84); Z168 = ((dfP - roll.mean()) / roll.std()).to_numpy()
    del dfP, roll
    log("hourly variants done")
    # ---- anchor-level raw variables at open=T−1h (known at T); leak/stale diagnostics at open=T (future) and open=T−5h (stale 4h)
    nE = len(E_ts)
    def at_open(X, off_h):
        out = np.full((nE, NW), np.nan)
        for j, t in enumerate(E_ts):
            i = hpos.get(int(t) + off_h * H1)
            if i is not None: out[j] = X[i]
        return out
    B0 = at_open(PREM, -1); Bema = at_open(EMA24, -1); Bchg = at_open(CHG24, -1); Bz = at_open(Z168, -1); B0_lead = at_open(PREM, 0); B0_stale = at_open(PREM, -5)
    # ---- candidates (逐锚 LSQ 残差; domain = members ∩ qv≥2.5e5 ∩ 有限量)
    def build_cand(Bx, ortho, impute=False):
        """ortho ∈ {'OK','OF','RAW'}; 返回 (nE, NW) 带符号候选(−rank-center 残差), NaN=缺失; 以及覆盖率序列.
        impute=True(★非预注册并列臂 OK_imp): 回归元 fund_ema/fund_now 缺失的名以秩 0(截面中位)填补, 使有 basis 无 funding 数据的名仍进候选(宽面板 f_fund_* 只覆盖 s30 450 名)."""
        out = np.full((nE, NW), np.nan, np.float32); cov = np.full(nE, np.nan); covF = np.full(nE, np.nan); covBF = np.full(nE, np.nan)
        for j, t in enumerate(E_ts):
            jp = pw_row.get(int(t))
            if jp is None: continue
            m = members[j]; qv4h = np.expm1(np.clip(qvk[j, m], 0, 30)) * 48; mm = m[qv4h >= 2.5e5]
            if len(mm) < 10: continue
            b = Bx[j, mm]; cov[j] = float(np.isfinite(b).mean()); fe = FE_all[jp, mm]; covF[j] = float(np.isfinite(fe).mean()); covBF[j] = float((np.isfinite(b) & np.isfinite(fe)).mean())
            if ortho == "RAW":
                r = rank_center(b)
            else:
                y = rank_center(b); c1 = rank_center(fe); cols = [np.ones(len(mm)), (np.nan_to_num(c1) if impute else c1)]
                if ortho == "OK":
                    c2 = rank_center(FN_all[jp, mm]); c3 = rank_center(SLOW[j, mm])
                    cols += [(np.nan_to_num(c2) if impute else c2), (np.nan_to_num(c3) if impute else c3)]
                X = np.column_stack(cols); r = lsq_resid_multi(y, X)
            out[j, mm] = -1.0 * rank_center(r)
        return out, (cov, covF, covBF)
    CAND = {}; COV = {}
    for nm, Bx, ortho in (("OK", B0, "OK"), ("OF", B0, "OF"), ("RAW", B0, "RAW"), ("OK_ema24", Bema, "OK"), ("OK_chg24", Bchg, "OK"), ("OK_z168", Bz, "OK"), ("OK_lead1h_DIAG", B0_lead, "OK"), ("OK_stale4h_DIAG", B0_stale, "OK")):
        CAND[nm], COV[nm] = build_cand(Bx, ortho); log("cand", nm, "coverage mean", round(float(np.nanmean(COV[nm][0])), 3))
    CAND["OK_imp"], COV["OK_imp"] = build_cand(B0, "OK", impute=True); log("cand OK_imp (NON-PREREG parallel) coverage", round(float(np.nanmean(COV["OK_imp"][0])), 3))
    CAND["OK_pos"] = -CAND["OK"]
    yrE = yr_of(E_ts)
    R["coverage_of_sel_universe"] = {"PREM_finite_share_by_year": {int(y): round(float(np.nanmean(COV["OK"][0][yrE == y])), 4) for y in sorted(set(yrE.tolist())) if np.isfinite(COV["OK"][0][yrE == y]).any()},
                                     "fund_ema_finite_share_by_year": {int(y): round(float(np.nanmean(COV["OK"][1][yrE == y])), 4) for y in sorted(set(yrE.tolist())) if np.isfinite(COV["OK"][1][yrE == y]).any()},
                                     "PREM_and_fund_finite_share_by_year": {int(y): round(float(np.nanmean(COV["OK"][2][yrE == y])), 4) for y in sorted(set(yrE.tolist())) if np.isfinite(COV["OK"][2][yrE == y]).any()},
                                     "cand_OK_finite_share_by_year": {int(y): round(float(np.nanmean([np.isfinite(CAND["OK"][j][members[j]]).mean() for j in np.where(yrE == y)[0] if pw_row.get(int(E_ts[j])) is not None])), 4) for y in sorted(set(yrE.tolist()))},
                                     "note": "宽面板 f_fund_ema_v1/f_fund_now 只覆盖 s30 450 名 ⇒ 主臂(回归元须有限)候选只在 fund 覆盖名上定义; OK_imp 为非预注册并列臂(缺失回归元填秩 0)"}
    log("coverage", R["coverage_of_sel_universe"])
    # 8h 保持臂: 04/12/20Z 复用上一锚(T−4h)的候选行
    hrs = np.array([time.gmtime(int(t)).tm_hour for t in E_ts]); C8 = CAND["OK"].copy()
    for j in range(1, nE):
        if hrs[j] in (4, 12, 20) and E_ts[j] - E_ts[j - 1] == H4: C8[j] = C8[j - 1]
    CAND["OK_8h"] = C8
    # 同槽位安慰剂(种子 0-4): 逐锚把主臂候选在其有限名上随机置换
    for sd in range(5):
        rng = np.random.default_rng(sd); P = CAND["OK"].copy()
        for j in range(nE):
            idx = np.where(np.isfinite(P[j]))[0]
            if len(idx) > 1: P[j, idx] = P[j, rng.permutation(idx)]
        CAND[f"OK_plc{sd}"] = P
    # ---- S1 on U400 (FF def: members ∩ qv≥2.5e5 ∩ finite r4), main span anchors
    mainA = [t for t in E_ts if A_T0 <= t <= T_END_MAIN and int(t) in apos and int(t) in pw_row]
    if smoke: mainA = mainA[:smoke]
    mainA = np.array(mainA, np.int64); nM = len(mainA); yrM = yr_of(mainA)
    U400 = np.zeros((nM, NW), bool); Kp = np.full((nM, NW), np.nan); R4 = np.full((nM, NW), np.nan); rowsE = np.array([mrow[int(t)] for t in mainA]); rowsA = np.array([apos[int(t)] for t in mainA])
    for i, t in enumerate(mainA):
        j = rowsE[i]; m = np.asarray(members[j]); qv4h = np.expm1(np.clip(qvk[j, m], 0, 30)) * 48; r4 = RET[rowsA[i]]
        sel = m[(qv4h >= 2.5e5) & np.isfinite(r4[m])]; U400[i, sel] = True; Kp[i, m] = SLOW[j, m]; R4[i] = r4
    R["U400"] = {"n_anchors": int(nM), "size_mean": float(U400.sum(1).mean()), "size_p10": float(np.percentile(U400.sum(1), 10)), "size_p90": float(np.percentile(U400.sum(1), 90)), "span": [fmt(mainA[0]), fmt(mainA[-1])]}
    S1 = {}; S1SER = {}
    for nm in ("OK", "OF", "RAW", "OK_ema24", "OK_chg24", "OK_z168", "OK_pos", "OK_8h", "OK_lead1h_DIAG", "OK_stale4h_DIAG", "OK_plc0", "OK_imp"):
        o = s1_gate(CAND[nm][rowsE], Kp, U400, R4, yrM, mainA); S1SER[nm] = o.pop("series"); S1[nm] = o
        log("S1", nm, "pass", o["pass"], "dIC yrmean", round(o["dIC_year_mean_of_years"], 5), "by_year", {k: round(v, 5) for k, v in o["dIC_by_year"].items()}, "ic_cand", round(o["ic_cand"]["mean"], 5), "t", round(o["ic_cand"]["t"], 1))
    R["S1"] = S1
    # 候选间相关(逐锚横截面 Spearman 均值) + 与三腿分数相关(机制/关三前哨)
    def xcorr(Xa, Xb):
        v = []
        for i in range(nM):
            u = U400[i]; a_ = Xa[i][u]; b_ = Xb[i][u]; ok = np.isfinite(a_) & np.isfinite(b_)
            if ok.sum() >= 30: v.append(spearmanr(a_[ok], b_[ok]).correlation)
        return float(np.nanmean(v)) if v else None
    FEm = np.full((nM, NW), np.nan); FNm = np.full((nM, NW), np.nan); R24m = np.full((nM, NW), np.nan)
    for i, t in enumerate(mainA):
        jp = pw_row[int(t)]; FEm[i] = FE_all[jp]; FNm[i] = FN_all[jp]; R24m[i] = -PW["f_rev_24h"][jp]
    R["S1_xsec_corr"] = {"OK_vs_RAW": xcorr(CAND["OK"][rowsE], CAND["RAW"][rowsE]), "OK_vs_OF": xcorr(CAND["OK"][rowsE], CAND["OF"][rowsE]),
                         "RAW_vs_fund_ema": xcorr(CAND["RAW"][rowsE], FEm), "OK_vs_fund_ema": xcorr(CAND["OK"][rowsE], FEm), "OK_vs_fund_now": xcorr(CAND["OK"][rowsE], FNm), "OK_vs_king": xcorr(CAND["OK"][rowsE], Kp), "OK_vs_rev24": xcorr(CAND["OK"][rowsE], R24m),
                         "RAW_vs_king": xcorr(CAND["RAW"][rowsE], Kp), "RAW_vs_rev24": xcorr(CAND["RAW"][rowsE], R24m)}
    log("xsec corr", R["S1_xsec_corr"])
    # ---- S2 jobs
    JOBS.clear()
    JOBS["base_d30"] = {"cand": None, "wmode": "base", "stop": STOP}; JOBS["base_S0"] = {"cand": None, "wmode": "base", "stop": None}
    JOBS["OK_f15_w0_d30_R3"] = {"cand": "OK", "wmode": "fix", "w4": 0.0, "stop": STOP}
    for w4 in (0.10, 0.15, 0.20): JOBS[f"OK_f{int(w4*100):02d}_d30"] = {"cand": "OK", "wmode": "fix", "w4": w4, "stop": STOP}
    JOBS["OK_f15_S0"] = {"cand": "OK", "wmode": "fix", "w4": 0.15, "stop": None}
    JOBS["OK_ms4_d30"] = {"cand": "OK", "wmode": "ms4", "stop": STOP}; JOBS["OK_ms4_S0"] = {"cand": "OK", "wmode": "ms4", "stop": None}
    for nm in ("OF", "RAW", "OK_ema24", "OK_chg24", "OK_z168", "OK_8h", "OK_pos", "OK_imp"): JOBS[f"{nm}_f15_d30"] = {"cand": nm, "wmode": "fix", "w4": 0.15, "stop": STOP}
    JOBS["nfOK_imp_f15_d30"] = {"cand": "OK_imp", "wmode": "nofund_fix", "w4": 0.15, "stop": STOP}
    for sd in range(5): JOBS[f"OK_plc{sd}_f15_d30"] = {"cand": f"OK_plc{sd}", "wmode": "fix", "w4": 0.15, "stop": STOP}
    JOBS["nf_d30"] = {"cand": None, "wmode": "nofund", "stop": STOP}; JOBS["nf_S0"] = {"cand": None, "wmode": "nofund", "stop": None}
    for w4 in (0.10, 0.15, 0.20): JOBS[f"nfOK_f{int(w4*100):02d}_d30"] = {"cand": "OK", "wmode": "nofund_fix", "w4": w4, "stop": STOP}
    JOBS["nfOK_f15_S0"] = {"cand": "OK", "wmode": "nofund_fix", "w4": 0.15, "stop": None}
    JOBS["nfOK_ms_d30"] = {"cand": "OK", "wmode": "nofund_ms", "stop": STOP}
    for sd in range(5): JOBS[f"nfOK_plc{sd}_f15_d30"] = {"cand": f"OK_plc{sd}", "wmode": "nofund_fix", "w4": 0.15, "stop": STOP}
    if smoke:
        keep = ("base_d30", "OK_f15_w0_d30_R3", "OK_f15_d30", "nf_d30", "nfOK_f15_d30", "OK_plc0_f15_d30")
        for k in list(JOBS.keys()):
            if k not in keep: del JOBS[k]
        D = dict(D); D["E_ts"] = E_ts[: rec_from + smoke]
    _G.update({"D": D, "RET": RET, "CAND": CAND, "rec_from": rec_from})
    from multiprocessing import get_context
    t0 = time.time(); chains = {}
    with get_context("fork").Pool(min(nw, len(JOBS))) as pool:
        for name, out in pool.imap_unordered(_job, list(JOBS.keys())):
            chains[name] = out; log("chain done", name, round(out["secs"], 1), "s", "skipped", out["skipped"], "fires", out["fires"], "wk_mean", [round(float(x), 3) for x in out["wk"].mean(0)])
    log("all chains", round(time.time() - t0, 1), "s")
    R["chain_meta"] = {k: {"n_rec": int(len(v["ts"])), "skipped": int(v["skipped"]), "fires": int(v["fires"]), "wk_mean": [round(float(x), 4) for x in v["wk"].mean(0)], "secs": round(v["secs"], 1)} for k, v in chains.items()}
    # ---- R1: base_d30 ≡ WA Wb_d30 weights ; R3: fix w4=0 ≡ base
    WZ = np.load(INPUTS["wa_weights_Wb_d30"], allow_pickle=True); wts = WZ["ts"].astype(np.int64); WaW = WZ["W"]
    b0 = chains["base_d30"]; nn = min(len(b0["ts"]), len(wts))
    if not smoke: assert np.array_equal(b0["ts"], wts), "base anchors differ from WA"
    dw = np.abs(b0["W"][:nn].astype(np.float64) - WaW[:nn].astype(np.float64))
    R["receipt_R1_weights"] = {"n_anchors": int(nn), "maxabs_dw": float(dw.max()), "mean_abs_dw": float(dw.mean()), "bitwise_equal": bool(np.array_equal(b0["W"][:nn], WaW[:nn])), "pass_lt_1e-6": bool(dw.max() < 1e-6)}
    log("RECEIPT R1 weights", R["receipt_R1_weights"])
    d3 = np.abs(chains["OK_f15_w0_d30_R3"]["W"].astype(np.float64) - b0["W"].astype(np.float64))
    R["receipt_R3_fix_w0_equals_base"] = {"maxabs_dw": float(d3.max()), "bitwise_equal": bool(np.array_equal(chains["OK_f15_w0_d30_R3"]["W"], b0["W"]))}
    log("RECEIPT R3", R["receipt_R3_fix_w0_equals_base"])
    # ---- accounting
    def align(ts):
        ai = np.array([apos.get(int(t), -1) for t in ts]); ok = ai >= 0; return ai, ok
    ACC = {}; AIX = {}
    for nm, v in chains.items():
        ai, ok = align(v["ts"]); keep = ok & (v["ts"] >= A_T0); ai = ai[keep]; ts_ = v["ts"][keep]; W_ = v["W"][keep]; WL_ = v["WL"][keep]
        Fsub = {k2: F[k2][ai] for k2 in F}
        ACC[nm] = account_k(W_, ts_, Fsub, RET[ai], LRET[ai], WL=WL_); AIX[nm] = ai
    ts0 = ACC["base_d30"]["ts"]
    for nm in ACC: assert np.array_equal(ACC[nm]["ts"], ts0), f"anchor mismatch {nm}"
    ai0 = AIX["base_d30"]; mkt0 = mkt[ai0]; yr0 = yr_of(ts0)
    mask_main = ts0 <= T_END_MAIN; mask_full = ts0 <= T_END_FULL; mask_2223 = mask_main & (yr0 <= 2023); mask_2426 = mask_main & (yr0 >= 2024)
    if not smoke:
        WS = np.load(INPUTS["wa_series"], allow_pickle=True); wa_ts = WS["Wb_d30__ts"].astype(np.int64); wa_g2 = WS["Wb_d30__net_g2"]
        assert np.array_equal(wa_ts, ts0)
        R["receipt_R1_sharpe"] = {"base_d30_net_g2_sharpe_2022_06": round(sharpe_a(ACC["base_d30"]["net_g2"][mask_main]), 4), "WA_Wb_d30_net_g2_sharpe_2022_06": round(sharpe_a(wa_g2[mask_main]), 4),
                                  "maxabs_diff_net_g2_bps": float(np.abs(ACC["base_d30"]["net_g2"] - wa_g2).max()), "expected_1.668": True,
                                  "nf_d30_sharpe_2022_06": round(sharpe_a(ACC["nf_d30"]["net_g2"][mask_main]), 4), "WA_nofund_expected_0.664": True}
        log("RECEIPT R1 sharpe", R["receipt_R1_sharpe"])
    # ---- summaries
    SUMM = {}
    spans = {"2022-01..2026-06": mask_main, "FULL(..2026-07)": mask_full, "2022-23": mask_2223, "2024-26": mask_2426}
    spans = {k: v for k, v in spans.items() if v.sum() >= 100}
    for nm, acc in ACC.items():
        SUMM[nm] = {sp: summarize(acc, ts0, mkt0, nm, yr_mask=mk) for sp, mk in spans.items()}
        log("summarized", nm, "net@2 22-06", SUMM[nm]["2022-01..2026-06"]["net_at_gross2"]["mean_bps"], "sharpe", SUMM[nm]["2022-01..2026-06"]["net_at_gross2"]["sharpe_anchor"], "turn", SUMM[nm]["2022-01..2026-06"]["turnover_mean"])
    R["summary"] = SUMM
    # ---- G 族 + ΔSharpe + 腿级 + 关三(腿净额相关)
    def gate_block(arm, base, mask):
        a = ACC[arm]; b = ACC[base]
        g = gfam(a["p_g2"][mask], a["t_g2"][mask], b["p_g2"][mask], b["t_g2"][mask], yr0[mask])
        g["dSharpe_net_g2@3.52"] = round(sharpe_a(a["net_g2"][mask]) - sharpe_a(b["net_g2"][mask]), 4)
        g["dSharpe_CI95_blk42_paired"] = boot_delta_sharpe(a["net_g2"][mask], b["net_g2"][mask])
        g["sharpe_arm@3.52_CI95"] = boot_sharpe_ci(a["net_g2"][mask]); g["sharpe_base@3.52_CI95"] = boot_sharpe_ci(b["net_g2"][mask])
        g["turnover_arm"] = round(float(a["trn"][mask].mean()), 5); g["turnover_base"] = round(float(b["trn"][mask].mean()), 5)
        g["gross_pnl_g2_arm"] = round(float(a["pnl_g2"][mask].mean()), 4); g["gross_pnl_g2_base"] = round(float(b["pnl_g2"][mask].mean()), 4)
        g["carry_g2_arm"] = round(float(a["carry_g2"][mask].mean()), 4); g["carry_g2_base"] = round(float(b["carry_g2"][mask].mean()), 4)
        g["cost_g2_arm"] = round(float(a["cost_g2"][mask].mean()), 4); g["cost_g2_base"] = round(float(b["cost_g2"][mask].mean()), 4)
        g["G4_turnover_attribution"] = {"d_gross_pnl_g2": round(float((a["pnl_g2"] - b["pnl_g2"])[mask].mean()), 4), "d_carry_g2": round(float((a["carry_g2"] - b["carry_g2"])[mask].mean()), 4), "d_cost_g2@3.52": round(float((a["cost_g2"] - b["cost_g2"])[mask].mean()), 4)}
        mk = mkt0[mask]; ag = a["net_g2"][mask]; bg = b["net_g2"][mask]
        g["Q4"] = {"arm_mkt_quintiles": quintile_table(ag, mk), "base_mkt_quintiles": quintile_table(bg, mk), "arm_absmkt_quintiles": quintile_table(ag, np.abs(mk)), "base_absmkt_quintiles": quintile_table(bg, np.abs(mk))}
        if "legs" in a:
            with np.errstate(all="ignore"):
                gq = np.where(a["gross"][mask] > 1e-9, a["gross"][mask], np.nan)
            legs = {}; ln = {}
            for leg, dd in a["legs"].items():
                net2 = 2 * dd["net"][mask] / gq; ln[leg] = np.nan_to_num(net2)
                legs[leg] = {"gross_share": round(float((dd["gross"][mask] / np.maximum(a["gross"][mask], 1e-9)).mean()), 4), "net_g2": round(float(np.nanmean(net2)), 4), "net_sharpe": round(sharpe_a(np.nan_to_num(net2)), 3),
                             "pnl_g2": round(float(np.nanmean(2 * dd["pnl"][mask] / gq)), 4), "carry_g2": round(float(np.nanmean(2 * dd["carry"][mask] / gq)), 4), "cost_g2": round(float(np.nanmean(2 * dd["cost"][mask] / gq)), 4),
                             "by_year_net_g2": {int(y): round(float(np.nanmean(net2[yr0[mask] == y])), 3) for y in sorted(set(yr0[mask].tolist()))}}
            g["legs"] = legs
            if np.abs(ln["basis"]).sum() > 0:
                g["leg_net_corr_basis_vs"] = {l: round(float(np.corrcoef(ln["basis"], ln[l])[0, 1]), 4) for l in ("king", "rev24", "fund") if np.abs(ln[l]).sum() > 0}
        return g
    R["gates"] = {}
    pairs = [(nm, "base_d30") for nm in JOBS if nm.endswith("_d30") and not nm.startswith(("base", "nf"))] + [("OK_f15_S0", "base_S0"), ("OK_ms4_S0", "base_S0")] \
          + [(nm, "nf_d30") for nm in JOBS if nm.startswith("nf") and nm != "nf_d30" and nm.endswith("_d30")] + [("nfOK_f15_S0", "nf_S0")] + [("nfOK_f15_d30", "base_d30"), ("nfOK_ms_d30", "base_d30"), ("nf_d30", "base_d30")]
    for arm, base in pairs:
        if arm not in ACC or base not in ACC: continue
        R["gates"][f"{arm}__vs__{base}"] = {sp: gate_block(arm, base, mk) for sp, mk in spans.items()}
        g = R["gates"][f"{arm}__vs__{base}"]["2022-01..2026-06"]
        log("GATE", arm, "vs", base, "G_PASS", g["G_PASS"], "dnet@4.137", g["dnet@4.137"], g["dnet@4.137_CI95"], "@6.23", g["dnet@6.23"], "yrs", g["n_years_nonneg"], "sh", g["sharpe_arm@4.137"], "vs", g["sharpe_base@4.137"], "dSh", g["dSharpe_net_g2@3.52"], g["dSharpe_CI95_blk42_paired"])
    # ---- 尺子 G0/G1 (主臂 full 与 nofund)
    def ruler(real, plcs, base, mask):
        dS_real = sharpe_a(ACC[real]["net_g2"][mask]) - sharpe_a(ACC[base]["net_g2"][mask])
        dS_pl = [sharpe_a(ACC[p]["net_g2"][mask]) - sharpe_a(ACC[base]["net_g2"][mask]) for p in plcs if p in ACC]
        dn_pl = [float(((ACC[p]["p_g2"] - ACC[p]["t_g2"] * C_MAIN) - (ACC[base]["p_g2"] - ACC[base]["t_g2"] * C_MAIN))[mask].mean()) for p in plcs if p in ACC]
        ci = boot_delta_sharpe(ACC[real]["net_g2"][mask], ACC[base]["net_g2"][mask])
        G0 = bool(dS_pl and abs(float(np.mean(dS_pl))) < 0.10)
        G1 = bool(dS_pl and (dS_real - float(np.mean(dS_pl))) > 0 and ci["CI95"][0] > 0)
        return {"dSharpe_real": round(float(dS_real), 4), "dSharpe_real_CI95_blk42": ci, "dSharpe_placebo_by_seed": [round(float(x), 4) for x in dS_pl], "dSharpe_placebo_mean": round(float(np.mean(dS_pl)), 4) if dS_pl else None,
                "dnet@4.137_placebo_by_seed": [round(x, 4) for x in dn_pl], "G0_ruler_usable": G0, "G1_real_minus_placebo_gt0_and_CI_lb_gt0": G1, "real_minus_placebo_mean": round(float(dS_real - np.mean(dS_pl)), 4) if dS_pl else None}
    R["ruler"] = {}
    for sp, mk in spans.items():
        R["ruler"][sp] = {"full_OK_f15_d30": ruler("OK_f15_d30", [f"OK_plc{s}_f15_d30" for s in range(5)], "base_d30", mk), "nofund_OK_f15_d30": ruler("nfOK_f15_d30", [f"nfOK_plc{s}_f15_d30" for s in range(5)], "nf_d30", mk)}
    log("RULER main", R["ruler"]["2022-01..2026-06"])
    # ---- 判决(§P.5 逐字)
    if not smoke:
        gm = R["gates"]["OK_f15_d30__vs__base_d30"]["2022-01..2026-06"]; ru = R["ruler"]["2022-01..2026-06"]["full_OK_f15_d30"]
        s1 = R["S1"]["OK"]["pass"]; g_pass = gm["G_PASS"]; g0 = ru["G0_ruler_usable"]; g1 = ru["G1_real_minus_placebo_gt0_and_CI_lb_gt0"]
        nfg = R["gates"]["nfOK_f15_d30__vs__nf_d30"]["2022-01..2026-06"]; nfs = SUMM["nfOK_f15_d30"]["2022-01..2026-06"]["net_at_gross2"]
        yrs_nonneg = sum(1 for v in nfs["by_year_mean"].values() if v >= 0)
        R["verdict"] = {"S1_main_pass": s1, "G_family_main_pass": g_pass, "G0_ruler_usable": g0, "G1_pass": g1,
                        "ADMITTED(S1+G+G0+G1)": bool(s1 and g_pass and g0 and g1),
                        "wording": ("录取(进影子)" if (s1 and g_pass and g0 and g1) else ("排序有、净额无(第五例)" if (s1 and not (g_pass and g1)) else ("判负" if not s1 else "尺子不可用, 不出具判定"))),
                        "nofund_question": {"nofund_sharpe": SUMM["nf_d30"]["2022-01..2026-06"]["net_at_gross2"]["sharpe_anchor"], "nofund_plus_basis_sharpe": nfs["sharpe_anchor"], "nofund_plus_basis_CI95": nfs["sharpe_CI95_blk42"],
                                            "dSharpe_vs_nofund": nfg["dSharpe_net_g2@3.52"], "dSharpe_CI95": nfg["dSharpe_CI95_blk42_paired"], "G_PASS_vs_nofund": nfg["G_PASS"],
                                            "years_nonneg": int(yrs_nonneg), "stage_target_ge_1.0_and_4of5": bool(nfs["sharpe_anchor"] >= 1.0 and yrs_nonneg >= 4),
                                            "vs_base_with_fund": R["gates"]["nfOK_f15_d30__vs__base_d30"]["2022-01..2026-06"]["dSharpe_net_g2@3.52"]}}
        log("VERDICT", R["verdict"])
    # ---- save
    tag = "_smoke" if smoke else ""
    outj = f"{F2}/f2_basis_leg_admission_2026-08-22{tag}.json"
    def clean(o):
        if isinstance(o, dict): return {str(k): clean(v) for k, v in o.items()}
        if isinstance(o, (list, tuple)): return [clean(v) for v in o]
        if isinstance(o, (np.floating, float)): return None if not np.isfinite(o) else float(o)
        if isinstance(o, (np.integer,)): return int(o)
        if isinstance(o, np.ndarray): return clean(o.tolist())
        if isinstance(o, (np.bool_,)): return bool(o)
        return o
    json.dump(clean(R), open(outj, "w"), indent=1)
    ser = {"ts": ts0, "mkt": mkt0}
    for nm, acc in ACC.items():
        for k in ("net_g2", "p_g2", "t_g2", "pnl_g2", "carry_g2", "gross", "trn"): ser[f"{nm}__{k}"] = acc[k]
        if "legs" in acc:
            for leg, dd in acc["legs"].items(): ser[f"{nm}__leg_{leg}_net"] = dd["net"]; ser[f"{nm}__leg_{leg}_gross"] = dd["gross"]
    for nm, s in S1SER.items():
        for k, v in s.items(): ser[f"S1_{nm}__{k}"] = v
    ser["S1_anchors"] = mainA
    np.savez_compressed(f"{F2}/f2_series{tag}.npz", **ser)
    if not smoke:
        np.savez_compressed(f"{F2}/f2_weights_OK_f15_d30.npz", ts=chains["OK_f15_d30"]["ts"], W=chains["OK_f15_d30"]["W"], symbols=np.array(syms))
        np.savez_compressed(f"{F2}/f2_cand_OK.npz", E_ts=E_ts, CAND_OK=CAND["OK"], symbols=np.array(syms))
    log("DONE ->", outj)

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(); ap.add_argument("stage", nargs="?", default="run"); ap.add_argument("--smoke", type=int, default=0); ap.add_argument("--nw", type=int, default=12)
    a = ap.parse_args()
    if a.stage == "run": stage_run(nw=a.nw, smoke=a.smoke)
