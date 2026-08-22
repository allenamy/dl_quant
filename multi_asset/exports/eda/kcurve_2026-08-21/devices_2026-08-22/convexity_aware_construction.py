"""CX · 凸性感知的组合构造装置(2026-08-22, Session 6737834a-CX)。
预注册: multi_asset/exports/eda/PREREG_RESULT_convexity_aware_construction_2026-08-22.md §P(冻结段 SHA 1d1f080b…a8c, 先于任何数字)。
SHA256: 脚本自身 SHA 与全部输入 SHA 运行时写入结果 JSON(`self_sha256` / `input_sha256`)。

【对象 / 链】宽书 W-b 链 = WA 装置 `wide_full_caliber_audit.py`(SHA 9792ecd0…808b)的 run_chain 语义, 本文件以带钩子的副本实现
  (基线分支逐语句同 WA; 收据 R1: A0 权重 ≡ `probe_artifacts/wa/wa_weights_Wb_d30.npz` 逐锚逐名 max|Δw| < 1e-6, 且 A0 净@2 夏普 2022-01..2026-06 = 1.668)。
  记账/读数函数(account 语义, summarize, series_block, 块自助, 五分位)直接 import WA 模块(同一函数读同一量 ⇒ 数字可直接与 WA 表并列)。
【冻结定义】(复述预注册 P.2–P.5, 以预注册为准)
- σ̂²_i(T) = 过去 L 个 4h 窗对数收益平方的均值(原始二阶矩; 窗 (T−4h·n, T−4h·(n−1)], n=1..L; 最后一窗止于 T), L=30 主 / 90 敏感; 有限样本 ≥ ⌈2L/3⌉ 否则取当锚成员内截面中位数; c_i = ½σ̂²_i·1e4 bps.
- 标定(走前 900 锚, 不含当锚, ≥300 才用): 每锚 sel 内去均值量的乘积和; β_log1 = Σs·r_log/Σs²; (β_sim2, γ_sim2) = r_sim ~ s + c 二元 OLS; 诊断 β_sim1, γ_log2; 所用 β ≤ 0 ⇒ 该锚不调整.
- 臂: A0 基线 | A1(k) e = β_log1·s + k·c(k ∈ {0.5, 1.0}; 主 = 1.0, L=30) | A1γ e = β_sim2·s + clip(γ_sim2,0,2)·c | A1(k=1,L=90) | A4 xz(e) 重排 |
      A2(q) 空头 |tgt|·σ̂ 封顶于空头侧 p80/p90 分位, 空头侧缩放回 Σ_short = Σ_long, L1 再归一 | A3 多×1.2 空×0.8(仅敏感) |
      C1 全书 vol-target 对照(A0 恒定 gross2 权重 × clip(σ*/σ̂42, .5, 1.5), 权重原样记账) | C2 纯方差倾斜书 xz(c)(无止损) | 情景 no_fund(A0, A1 k=1) | 次对象 在役 S1 A2(p80) 持仓级 overlay.
- 判据(主臂 A1 k=1.0 vs A0, 净@2, 2022-01..2026-06): G1 Δ夏普 ≥ +0.10 · G2 逐年 Δ≥0 ≥4/5 · G3 市场五分位最差档 ≥ 基线 且 |市场| 最高档 ≥ 基线 · G4 换手 ≤ 1.2× · G5 no_fund Δ夏普 ≥ +0.05;
  五门全过 PASS / G1 不过 判负 / 其余 敏感. 次要臂同五门并报, 不授予晋升.
v2(05:5xZ, 看到 v1 读数后): 加 POST-HOC 臂 A1n(A1 + 帽后恢复中性), 非预注册, 仅诊断; 预注册臂逐位不变(v1 JSON 留存 `_v1_prereg_only.json`).
用法 @jpline: python convexity_aware_construction.py run [n_workers]
"""
import os, sys, json, time, math, hashlib, datetime as dt
import numpy as np

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
for cand in (HERE, os.path.join(HERE, "..", "wa"), (f"{PD}/wa" if PD else HERE)):
    if os.path.exists(os.path.join(cand, "wide_full_caliber_audit.py")):
        sys.path.insert(0, cand); WA_PATH = os.path.join(cand, "wide_full_caliber_audit.py"); break
import wide_full_caliber_audit as WAM
from wide_full_caliber_audit import (xz, sharpe_a, sharpe_d, boot_sharpe_ci, boot_delta_sharpe, quintile_table, summarize, series_block, yr_of, fmt, maxdd, anchors_grid, A_T0, A_T1, H4, COST_MAIN, COST_ARMS)
WA_SHA = sha(WA_PATH)
if ON_JP:
    B = "/mnt/storage/private/work_hsy/pod_backup_2026-08-21"; WA = f"{PD}/wa"; CX = f"{PD}/cx"; os.makedirs(CX, exist_ok=True)
STOP = (-0.30, 2, 42); LOOK = 900; CAL_MIN = 300
LEGS = ("king", "rev24", "fund", "tilt")
T_END_MAIN = int(dt.datetime(2026, 6, 30, 23, tzinfo=dt.timezone.utc).timestamp())

# ───────────────────────────────────────────── σ̂² (causal, trailing L anchors of squared log returns)
def trailing_sig2(LRET, L):
    """LRET (nA, NW) 对数 4h 收益(行 = 锚 T 的前向窗 (T,T+4h]). 返回 sig2 (nA, NW): 行 ai = 过去 L 行 [ai−L, ai) 的平方均值(窗止于 T 的 L 个窗), 样本 < ceil(2L/3) ⇒ NaN."""
    nA, NW = LRET.shape
    x2 = np.where(np.isfinite(LRET), LRET ** 2, 0.0); fin = np.isfinite(LRET).astype(np.int32)
    S2 = np.vstack([np.zeros((1, NW)), np.cumsum(x2, 0)]); CN = np.vstack([np.zeros((1, NW), np.int32), np.cumsum(fin, 0)])
    lo = np.maximum(np.arange(nA) - L, 0)
    num = S2[np.arange(nA)] - S2[lo]; cnt = CN[np.arange(nA)] - CN[lo]
    need = int(math.ceil(2 * L / 3))
    with np.errstate(all="ignore"):
        sig2 = np.where(cnt >= need, num / np.maximum(cnt, 1), np.nan)
    return sig2

# ───────────────────────────────────────────── chain with hooks (base branch verbatim from WA.run_chain)
def run_chain_cx(D, RET, LRET, SIG2, arm, stop=STOP, w3_mode="base", tag="", record_from=None):
    """arm: dict(kind ∈ {base, adj, adjg, rerank, scap, asym, tilt}, k, q, lf, sf). SIG2 (nA, NW) 已按 arm L 选好.
    返回 ts, W (n,NW), WL (n,4,NW) [king,rev24,fund,tilt], w3, diag(逐记录锚: beta_used, gamma_used, tilt_share, adjusted flag, beta_log1, beta_sim1, beta_sim2, gamma_sim2, gamma_log2)."""
    NW = D["NW"]; alpha = 0.1; band = 2.5e-4; capm = 2.5; look = LOOK
    depth, need, cool = stop if stop else (None, 0, 0)
    kind = arm["kind"]; kfix = arm.get("k", 0.0)
    H = np.zeros(NW); HL = np.zeros((4, NW)); Pi = np.ones(NW); sh = np.zeros(NW); cb = np.zeros(NW); cnt = np.zeros(NW, int); su = np.full(NW, -1)
    LR = {"king": [], "rev24": [], "fund": []}
    # calibration cumulative sums (entries appended per processed anchor; window = last `look` entries BEFORE current)
    nE = len(D["E_ts"]); CUM = np.zeros((9, nE + 1)); pc = 0   # rows: Sss, Ssc, Scc, Ssr_sim, Scr_sim, Ssr_log, Scr_log, n, (unused)
    recs = []; W = []; WL = []; W3 = []; skipped = 0; nfires = 0; fires_ts = []
    DG = {k: [] for k in ("beta_used", "gamma_used", "tilt_share", "adjusted", "beta_log1", "beta_sim1", "beta_sim2", "gamma_sim2", "gamma_log2", "n_cal", "cap_frac_short_gross", "cap_n")}
    E_ts = D["E_ts"]; rf = 0 if record_from is None else record_from
    for j in range(nE):
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
        qv4h = np.expm1(np.clip(D["qvk"][j, m], 0, 30)) * 48
        sel = ok & (qv4h >= 2.5e5)
        zk = np.stack([wk * np.nan_to_num(xz(sc[l])) for wk, l in zip(w3, ("king", "rev24", "fund"))])      # (3, nm)
        # ---- calibration window (past anchors only) and σ̂ for members
        nc = min(pc, look); beta_log1 = beta_sim1 = beta_sim2 = gamma_sim2 = gamma_log2 = np.nan
        if nc >= CAL_MIN:
            S = CUM[:, pc] - CUM[:, pc - nc]
            Sss, Ssc, Scc, Ssr, Scr, Ssl, Scl = S[0], S[1], S[2], S[3], S[4], S[5], S[6]
            if Sss > 0:
                beta_log1 = Ssl / Sss; beta_sim1 = Ssr / Sss
                det = Sss * Scc - Ssc * Ssc
                if det > 1e-12 * max(Sss * Scc, 1e-30):
                    beta_sim2 = (Scc * Ssr - Ssc * Scr) / det; gamma_sim2 = (Sss * Scr - Ssc * Ssr) / det
                    gamma_log2 = (Sss * Scl - Ssc * Ssl) / det
        s2m = SIG2[ai, m].astype(float)
        if np.isfinite(s2m).any():
            med = np.nanmedian(s2m[np.isfinite(s2m) & sel]) if (np.isfinite(s2m) & sel).any() else np.nanmedian(s2m)
            s2m = np.where(np.isfinite(s2m), s2m, med)
        else:
            s2m = np.full(len(m), np.nan)
        c_m = 0.5 * s2m * 1e4                         # bps
        sig_m = np.sqrt(np.maximum(s2m, 0.0))
        beta_used = np.nan; gamma_used = np.nan; tilt_share = 0.0; adjusted = 0; cap_frac = 0.0; cap_n = 0
        if sel.sum() < 80:
            skipped += 1; tgt_k = np.zeros((4, NW)); do_trade = False       # 无目标: 持仓不动
            s_comp = None
        else:
            do_trade = True
            zk = np.where(sel[None, :], zk, 0.0); zk = zk - np.where(sel[None, :], zk[:, sel].mean(1, keepdims=True), 0.0)
            w = zk.sum(0); g = np.abs(w).sum()
            s_comp = w.copy()                          # composite (rank-z units, demeaned over sel) — used for calibration sums
            c_dm = np.where(sel, c_m - (c_m[sel].mean() if np.isfinite(c_m[sel]).all() else np.nanmean(c_m[sel])), 0.0)
            c_dm = np.nan_to_num(c_dm)
            rows = None
            if kind in ("adj", "adjg", "rerank", "tilt"):
                if kind == "tilt":
                    comp = np.nan_to_num(xz(np.where(sel, c_m, np.nan))); comp = np.where(sel, comp, 0.0); comp -= comp[sel].mean()
                    rows = np.zeros((4, len(m))); rows[3] = comp; adjusted = 1
                else:
                    b = beta_log1 if kind in ("adj", "rerank") else beta_sim2
                    kk = kfix if kind in ("adj", "rerank") else (min(max(gamma_sim2, 0.0), 2.0) if np.isfinite(gamma_sim2) else np.nan)
                    if np.isfinite(b) and b > 0 and np.isfinite(kk) and g > 1e-9:
                        beta_used = float(b); gamma_used = float(kk); adjusted = 1
                        if kind == "rerank":
                            e = b * w + kk * c_dm
                            comp = np.nan_to_num(xz(np.where(sel, e, np.nan))); comp = np.where(sel, comp, 0.0); comp -= comp[sel].mean()
                            rows = np.zeros((4, len(m))); rows[3] = comp
                        else:
                            rows = np.vstack([b * zk, (kk * c_dm)[None, :]])
                        tilt_share = float(np.abs(kk * c_dm).sum() / max(np.abs(b * w).sum() + np.abs(kk * c_dm).sum(), 1e-12))
            if rows is None:
                rows = np.vstack([zk, np.zeros((1, len(m)))])       # baseline path (also for scap/asym before their hook)
            w = rows.sum(0); g = np.abs(w).sum()
            if g < 1e-9: skipped += 1; do_trade = False; tgt_k = np.zeros((4, NW))
            else:
                rows = rows / g; w = w / g; capw = capm / max(int(sel.sum()), 1); wc = np.clip(w, -capw, capw)
                with np.errstate(all="ignore"):
                    f = np.where(np.abs(w) > 1e-15, wc / w, 1.0)
                rows = rows * f[None, :]; g2 = np.abs(wc).sum()
                if g2 > 1e-9: rows = rows / g2
                if arm.get("neutral"):          # POST-HOC(非预注册) 2026-08-22 05:5xZ: 帽后恢复中性 Σ_short = Σ_long, L1 再归一 — 诊断 A1 的"帽只咬多头侧 ⇒ 净空"伪影
                    tg = rows.sum(0); lng = tg > 0; shrt = tg < 0; Lg = tg[lng].sum(); Sg = np.abs(tg[shrt]).sum()
                    if Lg > 1e-12 and Sg > 1e-12:
                        fs = np.ones(len(m)); fs[shrt] = Lg / Sg; rows = rows * fs[None, :]; gg = np.abs(rows.sum(0)).sum()
                        if gg > 1e-12: rows = rows / gg
                if kind == "scap":
                    tg = rows.sum(0); shrt = tg < 0; lng = tg > 0
                    if shrt.sum() >= 5 and lng.any():
                        v = np.abs(tg) * sig_m; vs = v[shrt]
                        qv = np.percentile(vs[np.isfinite(vs)], arm["q"]) if np.isfinite(vs).any() else np.inf
                        over = shrt & np.isfinite(v) & (v > qv)
                        fct = np.ones(len(m)); fct[over] = qv / v[over]
                        cap_n = int(over.sum()); cap_frac = float((np.abs(tg[over]) * (1 - fct[over])).sum() / max(np.abs(tg[shrt]).sum(), 1e-12))
                        rows = rows * fct[None, :]; tg = rows.sum(0)
                        Lg = tg[lng].sum(); Sg = np.abs(tg[shrt]).sum()
                        if Sg > 1e-12:
                            fs = np.ones(len(m)); fs[shrt] = Lg / Sg; rows = rows * fs[None, :]; tg = rows.sum(0)
                        gg = np.abs(tg).sum()
                        if gg > 1e-12: rows = rows / gg
                        adjusted = 1
                elif kind == "asym":
                    tg = rows.sum(0); fa = np.where(tg > 0, arm["lf"], np.where(tg < 0, arm["sf"], 1.0)); rows = rows * fa[None, :]; adjusted = 1
                tgt_k = np.zeros((4, NW)); tgt_k[:, m] = rows
        # ---- append calibration sums for THIS anchor (usable from next anchor on)
        if s_comp is not None and np.isfinite(c_m[sel]).any():
            r_sim = np.where(ok, yv_m, 0.0) * 1e4; r_log = np.nan_to_num(LRET[ai, m].astype(float)) * 1e4
            rs = np.where(sel, r_sim - r_sim[sel].mean(), 0.0); rl = np.where(sel, r_log - r_log[sel].mean(), 0.0)
            ss = np.where(sel, s_comp, 0.0); cc = c_dm
            add = np.array([(ss * ss).sum(), (ss * cc).sum(), (cc * cc).sum(), (ss * rs).sum(), (cc * rs).sum(), (ss * rl).sum(), (cc * rl).sum(), float(sel.sum()), 0.0])
        else:
            add = np.zeros(9)
        CUM[:, pc + 1] = CUM[:, pc] + add; pc += 1
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
            for k_, v_ in (("beta_used", beta_used), ("gamma_used", gamma_used), ("tilt_share", tilt_share), ("adjusted", adjusted), ("beta_log1", beta_log1), ("beta_sim1", beta_sim1), ("beta_sim2", beta_sim2), ("gamma_sim2", gamma_sim2), ("gamma_log2", gamma_log2), ("n_cal", nc), ("cap_frac_short_gross", cap_frac), ("cap_n", cap_n)):
                DG[k_].append(v_)
        # 止损记账(成本均价深度, 价格路径 = RET 全名) — verbatim WA
        yfull = np.nan_to_num(RET[ai].astype(float))
        nsh = np.where(Pi > 1e-12, H / Pi, 0.0)
        same = np.sign(nsh) == np.sign(sh); add_ = same & (np.abs(nsh) > np.abs(sh))
        red = same & (~add_) & (np.abs(nsh) > 1e-12); new = (~same) | (np.abs(sh) < 1e-12)
        cb = np.where(add_, cb + (nsh - sh) * Pi, cb)
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
        if j % 4000 == 0: log(tag, "chain", j, "/", nE)
    W = np.stack(W); WL = np.stack(WL)
    assert np.abs(WL.sum(1) - W).max() < 1e-5, "leg decomposition not additive"
    return {"ts": np.array(recs, np.int64), "W": W, "WL": WL, "w3": np.array(W3), "skipped": skipped, "fires": nfires, "diag": {k: np.array(v, float) for k, v in DG.items()}}

# ───────────────────────────────────────────── accounting (WA.account semantics; generic legs; + σ-profile)
def account_cx(W, ts, F, RET, LRET, SIG2, WL=None, cost_c=COST_MAIN, leg_names=LEGS):
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
    # σ-profile: gross-weighted mean σ̂ of long / short side; expected convexity Σ w·½σ̂² vs realized conv
    S2 = np.where(np.isfinite(SIG2), SIG2, np.nan); sig = np.sqrt(np.maximum(np.nan_to_num(S2), 0))
    wl = np.where(W > 0, W, 0); ws = np.where(W < 0, -W, 0)
    with np.errstate(all="ignore"):
        out["sig_long"] = np.nan_to_num((wl * sig).sum(1) / np.maximum(wl.sum(1), 1e-12)); out["sig_short"] = np.nan_to_num((ws * sig).sum(1) / np.maximum(ws.sum(1), 1e-12))
    out["conv_expected"] = (W * np.nan_to_num(S2) * 0.5).sum(1) * 1e4
    out["long_gross"] = wl.sum(1); out["short_gross"] = ws.sum(1)
    if WL is not None:
        out["legs"] = {}
        dWL = np.abs(WL - np.concatenate([np.zeros((1,) + WL.shape[1:], WL.dtype), WL[:-1]]))
        with np.errstate(all="ignore"):
            share = np.where(dWL.sum(1, keepdims=True) > 1e-15, dWL / dWL.sum(1, keepdims=True), 1 / WL.shape[1])
        for k, leg in enumerate(leg_names):
            Wk = WL[:, k, :]
            out["legs"][leg] = {"pnl": (Wk * R).sum(1) * 1e4, "carry": (Wk * FR).sum(1) * 1e4, "cost": cost_c * (share[:, k, :] * dW).sum(1), "gross": np.abs(Wk).sum(1), "conv": (Wk * (R - L)).sum(1) * 1e4}
            out["legs"][leg]["net"] = out["legs"][leg]["pnl"] - out["legs"][leg]["carry"] - out["legs"][leg]["cost"]
    return out

def gates(acc_arm, acc_base, ts, mkt, mask, key="net_g2", nofund_delta=None):
    x = acc_arm[key][mask]; y = acc_base[key][mask]; t = ts[mask]; yr = yr_of(t); yrs = sorted(set(yr.tolist()))
    d_sh = sharpe_a(x) - sharpe_a(y)
    by_year = {int(v): round(sharpe_a(x[yr == v]) - sharpe_a(y[yr == v]), 3) for v in yrs}
    n_ok = sum(1 for v in by_year.values() if v >= 0)
    mk = mkt[mask]
    qa = quintile_table(x, mk); qb = quintile_table(y, mk); aa = quintile_table(x, np.abs(mk)); ab = quintile_table(y, np.abs(mk))
    trn_ratio = float(acc_arm["trn"][mask].mean() / max(acc_base["trn"][mask].mean(), 1e-12))
    G = {"G1_delta_sharpe": round(float(d_sh), 4), "G1_pass": bool(d_sh >= 0.10), "G1_CI95_paired_blk42": boot_delta_sharpe(x, y),
         "G2_by_year_delta_sharpe": by_year, "G2_n_years_ge0": n_ok, "G2_pass": bool(n_ok >= 4),
         "G3_mkt_quintiles_arm": qa, "G3_mkt_quintiles_base": qb, "G3_worst_arm": min(qa), "G3_worst_base": min(qb), "G3_absmkt_top_arm": aa[4], "G3_absmkt_top_base": ab[4],
         "G3_pass": bool(min(qa) >= min(qb) and aa[4] >= ab[4]),
         "G4_turnover_ratio": round(trn_ratio, 4), "G4_pass": bool(trn_ratio <= 1.20),
         "sharpe_arm": round(sharpe_a(x), 4), "sharpe_base": round(sharpe_a(y), 4), "mean_arm": round(float(x.mean()), 4), "mean_base": round(float(y.mean()), 4),
         "sharpe_daily_arm": round(sharpe_d(x, t), 4), "sharpe_daily_base": round(sharpe_d(y, t), 4), "corr": round(float(np.corrcoef(x, y)[0, 1]), 4)}
    if nofund_delta is not None:
        G["G5_nofund_delta_sharpe"] = round(float(nofund_delta), 4); G["G5_pass"] = bool(nofund_delta >= 0.05)
        allp = G["G1_pass"] and G["G2_pass"] and G["G3_pass"] and G["G4_pass"] and G["G5_pass"]
        G["verdict"] = "PASS" if allp else ("判负" if not G["G1_pass"] else "敏感(方向性, 不采纳)")
    else:
        allp = G["G1_pass"] and G["G2_pass"] and G["G3_pass"] and G["G4_pass"]
        G["verdict_G1-4"] = "PASS(G1-4)" if allp else ("判负" if not G["G1_pass"] else "敏感")
    return G

# ───────────────────────────────────────────── jobs
JOBS = {
    "A0":              dict(kind="base", L=30, w3="base", stop=STOP),
    "A1_k0.5":         dict(kind="adj", k=0.5, L=30, w3="base", stop=STOP),
    "A1_k1.0":         dict(kind="adj", k=1.0, L=30, w3="base", stop=STOP),     # MAIN
    "A1g":             dict(kind="adjg", L=30, w3="base", stop=STOP),
    "A1_k1.0_L90":     dict(kind="adj", k=1.0, L=90, w3="base", stop=STOP),
    "A4_k1.0":         dict(kind="rerank", k=1.0, L=30, w3="base", stop=STOP),
    "A2_p80":          dict(kind="scap", q=80, L=30, w3="base", stop=STOP),
    "A2_p90":          dict(kind="scap", q=90, L=30, w3="base", stop=STOP),
    "A3_asym":         dict(kind="asym", lf=1.2, sf=0.8, L=30, w3="base", stop=STOP),
    "C2_tilt":         dict(kind="tilt", L=30, w3="base", stop=None),
    "A0_nofund":       dict(kind="base", L=30, w3="no_fund", stop=STOP),
    "A1_k1.0_nofund":  dict(kind="adj", k=1.0, L=30, w3="no_fund", stop=STOP),
    # ---- POST-HOC arms (added after v1 readings; NOT pre-registered; reported as diagnostics only)
    "A1n_k1.0":        dict(kind="adj", k=1.0, L=30, w3="base", stop=STOP, neutral=True, posthoc=True),
    "A1n_k0.5":        dict(kind="adj", k=0.5, L=30, w3="base", stop=STOP, neutral=True, posthoc=True),
    "A1n_k1.0_nofund": dict(kind="adj", k=1.0, L=30, w3="no_fund", stop=STOP, neutral=True, posthoc=True),
}
POSTHOC = [k for k, v in JOBS.items() if v.get("posthoc")]
_G = {}
def _job(name):
    a = JOBS[name]; SIG2 = _G["SIG2_30"] if a["L"] == 30 else _G["SIG2_90"]
    t0 = time.time()
    out = run_chain_cx(_G["D"], _G["RET"], _G["LRET"], SIG2, a, stop=a["stop"], w3_mode=a["w3"], tag=name, record_from=_G["rec_from"])
    out["secs"] = time.time() - t0
    return name, out

def stage_run(nw=12):
    R = {"session": "6737834a-CX", "created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "self_sha256": SELF_SHA, "wa_module_sha256": WA_SHA, "prereg_section_sha256": "1d1f080b835a787bd1a66658c20cd6bfe7938e8237ba7787b4ea23cc261e8a8c"}
    INPUTS = {"close1h": f"{WA}/close1h_829.npz", "funding": f"{WA}/funding_829.npz", "meta": f"{B}/wide_fea_hist_meta.npz", "panel_v2": f"{B}/wide_panel_4h_hist_v2.npz", "slow_pred": f"{B}/slow_pred_hist_oos.npy",
              "wa_weights_Wb_d30": f"{WA}/wa_weights_Wb_d30.npz", "wa_series": f"{WA}/wa_series.npz", "inrole_sr_npz": f"{PD}/inrole_sr/inrole_simple_return_rerun_jp_2026-08-22.npz"}
    R["input_sha256"] = {k: (sha(v) if os.path.exists(v) else None) for k, v in INPUTS.items()}; log("input shas done")
    Z = np.load(INPUTS["close1h"], allow_pickle=True); hts = Z["ts"].astype(np.int64); syms = [str(s) for s in Z["symbols"]]; C = Z["close"]; NW = len(syms)
    hpos = {int(t): i for i, t in enumerate(hts)}
    A = anchors_grid(int(dt.datetime(2021, 1, 1, tzinfo=dt.timezone.utc).timestamp()), A_T1); nA = len(A); apos = {int(t): i for i, t in enumerate(A)}
    i0 = np.array([hpos[int(t)] for t in A]); i1 = i0 + 4
    with np.errstate(all="ignore"):
        RET = (C[i1] / C[i0] - 1.0).astype(np.float64); LRET = np.log(C[i1] / C[i0])
    RET[~np.isfinite(RET)] = np.nan; LRET[~np.isfinite(LRET)] = np.nan
    SIG2_30 = trailing_sig2(LRET, 30); SIG2_90 = trailing_sig2(LRET, 90)
    log("returns grid", RET.shape, "sig2_30 finite frac", round(float(np.isfinite(SIG2_30).mean()), 3))
    FZ = np.load(INPUTS["funding"], allow_pickle=True); assert np.array_equal(FZ["anchors"].astype(np.int64), A) and [str(s) for s in FZ["symbols"]] == syms
    F = {k: FZ[k] for k in ("fr_sum", "nset", "last_rate", "last_iv", "last_age_h", "cov")}
    MT = np.load(INPUTS["meta"], allow_pickle=True); E_ts = MT["E_ts"].astype(np.int64); members = MT["members"]; qvk = MT["qvk"]
    PW = np.load(INPUTS["panel_v2"], allow_pickle=True); assert [str(s) for s in PW["symbols"]] == syms
    pw_row = {int(t): j for j, t in enumerate(PW["ts"].astype(np.int64))}
    D = {"E_ts": E_ts, "members": members, "SLOW": np.load(INPUTS["slow_pred"]), "R24": PW["f_rev_24h"], "FE": PW["f_fund_ema_v1"], "qvk": qvk, "pw_row": pw_row, "NW": NW, "apos": apos}
    mrow = {int(t): j for j, t in enumerate(E_ts)}
    mkt = np.full(nA, np.nan)
    for i, t in enumerate(A):
        j = mrow.get(int(t))
        if j is None: continue
        v = RET[i, members[j]]; v = v[np.isfinite(v)]
        if len(v): mkt[i] = v.mean() * 1e4
    rec_from = int(np.searchsorted(E_ts, A_T0))
    _G.update({"D": D, "RET": RET, "LRET": LRET, "SIG2_30": SIG2_30, "SIG2_90": SIG2_90, "rec_from": rec_from})
    # ---- run chains in parallel (fork shares arrays)
    from multiprocessing import get_context
    t0 = time.time(); chains = {}
    with get_context("fork").Pool(min(nw, len(JOBS))) as pool:
        for name, out in pool.imap_unordered(_job, list(JOBS.keys())):
            chains[name] = out; log("chain done", name, round(out["secs"], 1), "s", "skipped", out["skipped"], "fires", out["fires"])
    log("all chains", round(time.time() - t0, 1), "s")
    R["chain_meta"] = {k: {"n_rec": int(len(v["ts"])), "skipped": int(v["skipped"]), "fires": int(v["fires"]), "w3_mean": [round(float(x), 4) for x in v["w3"].mean(0)],
                           "adjusted_frac": round(float(np.nanmean(v["diag"]["adjusted"])), 4), "tilt_share_mean": round(float(np.nanmean(v["diag"]["tilt_share"])), 4),
                           "beta_used_median": (round(float(np.nanmedian(v["diag"]["beta_used"])), 3) if np.isfinite(v["diag"]["beta_used"]).any() else None),
                           "gamma_used_median": (round(float(np.nanmedian(v["diag"]["gamma_used"])), 3) if np.isfinite(v["diag"]["gamma_used"]).any() else None),
                           "cap_n_mean": round(float(np.nanmean(v["diag"]["cap_n"])), 2), "cap_frac_short_gross_mean": round(float(np.nanmean(v["diag"]["cap_frac_short_gross"])), 4)} for k, v in chains.items()}
    # ---- R1 receipt: A0 ≡ WA Wb_d30 weights
    WZ = np.load(INPUTS["wa_weights_Wb_d30"], allow_pickle=True); wts = WZ["ts"].astype(np.int64); WaW = WZ["W"]
    a0 = chains["A0"]; assert np.array_equal(a0["ts"], wts), "A0 anchors differ from WA"
    dw = np.abs(a0["W"].astype(np.float64) - WaW.astype(np.float64))
    R["receipt_R1_weights"] = {"n_anchors": int(len(wts)), "maxabs_dw": float(dw.max()), "mean_abs_dw": float(dw.mean()), "bitwise_equal": bool(np.array_equal(a0["W"], WaW)), "pass_lt_1e-6": bool(dw.max() < 1e-6)}
    log("RECEIPT R1 weights", R["receipt_R1_weights"])
    # ---- accounting
    def align(ts):
        ai = np.array([apos.get(int(t), -1) for t in ts]); ok = ai >= 0; return ai, ok
    ACC = {}; AIX = {}; KEEP = {}
    for nm, v in chains.items():
        ai, ok = align(v["ts"]); keep = ok & (v["ts"] >= A_T0); ai = ai[keep]; ts_ = v["ts"][keep]; W_ = v["W"][keep]; WL_ = v["WL"][keep]; KEEP[nm] = keep
        Fsub = {k2: F[k2][ai] for k2 in F}
        SIG2u = SIG2_30 if JOBS[nm]["L"] == 30 else SIG2_90
        ACC[nm] = account_cx(W_, ts_, Fsub, RET[ai], LRET[ai], SIG2u[ai], WL=WL_)
        AIX[nm] = ai
    ts0 = ACC["A0"]["ts"]
    for nm in ACC: assert np.array_equal(ACC[nm]["ts"], ts0), f"anchor mismatch {nm}"
    ai0 = AIX["A0"]; mkt0 = mkt[ai0]
    mask_main = ts0 <= T_END_MAIN; mask_full = np.ones(len(ts0), bool); mask_2223 = mask_main & (yr_of(ts0) <= 2023); mask_2426 = mask_main & (yr_of(ts0) >= 2024)
    # R1 sharpe receipt vs WA series
    WS = np.load(INPUTS["wa_series"], allow_pickle=True); wa_ts = WS["Wb_d30__ts"].astype(np.int64); wa_g2 = WS["Wb_d30__net_g2"]
    assert np.array_equal(wa_ts, ts0)
    R["receipt_R1_sharpe"] = {"A0_net_g2_sharpe_2022_06": round(sharpe_a(ACC["A0"]["net_g2"][mask_main]), 4), "WA_Wb_d30_net_g2_sharpe_2022_06": round(sharpe_a(wa_g2[mask_main]), 4),
                              "maxabs_diff_net_g2_bps": float(np.abs(ACC["A0"]["net_g2"] - wa_g2).max()), "expected_1.668": True}
    log("RECEIPT R1 sharpe", R["receipt_R1_sharpe"])
    # ---- summaries (WA.summarize) per arm per span
    SUMM = {}
    for nm, acc in ACC.items():
        SUMM[nm] = {"2022-01..2026-06": summarize(acc, ts0, mkt0, nm, yr_mask=mask_main), "FULL": summarize(acc, ts0, mkt0, nm), "2022-23": summarize(acc, ts0, mkt0, nm, yr_mask=mask_2223), "2024-26": summarize(acc, ts0, mkt0, nm, yr_mask=mask_2426)}
        for span in SUMM[nm]:
            mk = {"2022-01..2026-06": mask_main, "FULL": mask_full, "2022-23": mask_2223, "2024-26": mask_2426}[span]
            SUMM[nm][span]["sigma_profile"] = {"sig_long_mean": round(float(acc["sig_long"][mk].mean()), 5), "sig_short_mean": round(float(acc["sig_short"][mk].mean()), 5),
                                               "conv_expected_mean_actual": round(float(acc["conv_expected"][mk].mean()), 4), "conv_realized_mean_actual": round(float(acc["conv"][mk].mean()), 4),
                                               "long_gross_mean": round(float(acc["long_gross"][mk].mean()), 4), "short_gross_mean": round(float(acc["short_gross"][mk].mean()), 4)}
        log("summarized", nm, "net@2 sharpe 22-06", SUMM[nm]["2022-01..2026-06"]["net_at_gross2"]["sharpe_anchor"], "FULL", SUMM[nm]["FULL"]["net_at_gross2"]["sharpe_anchor"])
    R["summary"] = SUMM
    # ---- gates (main + all arms) on main span; also FULL and 2024-26 / 2022-23 for G1 direction
    nf_delta = sharpe_a(ACC["A1_k1.0_nofund"]["net_g2"][mask_main]) - sharpe_a(ACC["A0_nofund"]["net_g2"][mask_main])
    R["G5_nofund"] = {"A1_k1.0_nofund_sharpe": round(sharpe_a(ACC["A1_k1.0_nofund"]["net_g2"][mask_main]), 4), "A0_nofund_sharpe": round(sharpe_a(ACC["A0_nofund"]["net_g2"][mask_main]), 4), "delta": round(float(nf_delta), 4),
                      "delta_CI95": boot_delta_sharpe(ACC["A1_k1.0_nofund"]["net_g2"][mask_main], ACC["A0_nofund"]["net_g2"][mask_main]),
                      "FULL_delta": round(sharpe_a(ACC["A1_k1.0_nofund"]["net_g2"]) - sharpe_a(ACC["A0_nofund"]["net_g2"]), 4)}
    R["gates"] = {}
    nfn_delta = sharpe_a(ACC["A1n_k1.0_nofund"]["net_g2"][mask_main]) - sharpe_a(ACC["A0_nofund"]["net_g2"][mask_main])
    R["posthoc_arms"] = POSTHOC; R["G5_nofund_posthoc_A1n"] = {"delta": round(float(nfn_delta), 4), "A1n_k1.0_nofund_sharpe": round(sharpe_a(ACC["A1n_k1.0_nofund"]["net_g2"][mask_main]), 4)}
    for nm in ("A1_k1.0", "A1_k0.5", "A1g", "A1_k1.0_L90", "A4_k1.0", "A2_p80", "A2_p90", "A3_asym", "C2_tilt", "A1n_k1.0", "A1n_k0.5"):
        R["gates"][nm] = {"main_2022_06": gates(ACC[nm], ACC["A0"], ts0, mkt0, mask_main, nofund_delta=(nf_delta if nm == "A1_k1.0" else (nfn_delta if nm == "A1n_k1.0" else None))),
                          "FULL": gates(ACC[nm], ACC["A0"], ts0, mkt0, mask_full), "2022-23": gates(ACC[nm], ACC["A0"], ts0, mkt0, mask_2223), "2024-26": gates(ACC[nm], ACC["A0"], ts0, mkt0, mask_2426),
                          "role": "MAIN" if nm == "A1_k1.0" else ("POSTHOC(非预注册)" if nm in POSTHOC else "secondary")}
        # cost sensitivity & actual-gross
        for ck in ("c4.137", "c6.64"):
            xa = 2 * np.nan_to_num((ACC[nm]["pnl"] - ACC[nm]["carry"] - ACC[nm][f"cost_{ck}"]) / np.where(ACC[nm]["gross"] > 1e-9, ACC[nm]["gross"], np.nan))[mask_main]
            xb = 2 * np.nan_to_num((ACC["A0"]["pnl"] - ACC["A0"]["carry"] - ACC["A0"][f"cost_{ck}"]) / np.where(ACC["A0"]["gross"] > 1e-9, ACC["A0"]["gross"], np.nan))[mask_main]
            R["gates"][nm][f"delta_sharpe_{ck}"] = round(sharpe_a(xa) - sharpe_a(xb), 4)
        R["gates"][nm]["delta_sharpe_actual_gross"] = round(sharpe_a(ACC[nm]["net"][mask_main]) - sharpe_a(ACC["A0"]["net"][mask_main]), 4)
        log("GATES", nm, {k: R["gates"][nm]["main_2022_06"][k] for k in ("G1_delta_sharpe", "G1_pass", "G2_n_years_ge0", "G3_pass", "G4_turnover_ratio")}, R["gates"][nm]["main_2022_06"].get("verdict", R["gates"][nm]["main_2022_06"].get("verdict_G1-4")))
    R["verdict_main"] = R["gates"]["A1_k1.0"]["main_2022_06"]["verdict"]
    # ---- A3 market beta (sensitivity caveat)
    for nm in ("A3_asym", "A0", "A1_k1.0", "C2_tilt"):
        x = ACC[nm]["pnl_g2"][mask_main]; mk = mkt0[mask_main]; okm = np.isfinite(mk)
        bta = float(np.cov(x[okm], mk[okm])[0, 1] / np.var(mk[okm], ddof=1)); R.setdefault("mkt_beta_pnl_g2", {})[nm] = round(bta, 4)
    # ---- calibration diagnostics from A0 chain (β/γ series)
    dg = chains["A0"]["diag"]; yrs_rec = yr_of(chains["A0"]["ts"])
    R["calibration_A0"] = {k: {"median": (round(float(np.nanmedian(dg[k])), 4) if np.isfinite(dg[k]).any() else None), "p5": (round(float(np.nanpercentile(dg[k], 5)), 4) if np.isfinite(dg[k]).any() else None), "p95": (round(float(np.nanpercentile(dg[k], 95)), 4) if np.isfinite(dg[k]).any() else None),
                                "by_year_median": {int(y): (round(float(np.nanmedian(dg[k][yrs_rec == y])), 4) if np.isfinite(dg[k][yrs_rec == y]).any() else None) for y in sorted(set(yrs_rec.tolist()))}} for k in ("beta_log1", "beta_sim1", "beta_sim2", "gamma_sim2", "gamma_log2")}
    R["calibration_A0"]["frac_beta_log1_le0"] = round(float(np.mean(np.nan_to_num(dg["beta_log1"], nan=1.0) <= 0)), 4)
    R["calibration_A0"]["n_cal_median"] = float(np.nanmedian(dg["n_cal"]))
    R["tilt_share"] = {nm: {"mean": round(float(np.nanmean(chains[nm]["diag"]["tilt_share"])), 4), "p95": round(float(np.nanpercentile(chains[nm]["diag"]["tilt_share"], 95)), 4)} for nm in chains if JOBS[nm]["kind"] in ("adj", "adjg")}
    # ---- C1 vol-target control on A0 (constant-gross-2 weights × m_T), actual-gross accounting
    a0W = chains["A0"]["W"][KEEP["A0"]].astype(np.float64); ts_c = ts0; g0 = np.abs(a0W).sum(1); Wc2 = (2.0 * a0W / np.where(g0 > 1e-9, g0, np.nan)[:, None]); Wc2 = np.nan_to_num(Wc2)
    ng2 = ACC["A0"]["net_g2"]; sd42 = np.full(len(ng2), np.nan)
    for i in range(42, len(ng2)): sd42[i] = ng2[i - 42:i].std(ddof=1)
    sstar = np.full(len(ng2), np.nan)
    for i in range(42, len(ng2)): sstar[i] = np.nanmedian(sd42[42:i + 1])
    with np.errstate(all="ignore"):
        mT = np.clip(np.where(np.isfinite(sd42) & np.isfinite(sstar) & (sd42 > 0), sstar / sd42, 1.0), 0.5, 1.5)
    Wvt = Wc2 * mT[:, None]
    Fsub0 = {k2: F[k2][ai0] for k2 in F}
    accC2 = account_cx(Wc2, ts0, Fsub0, RET[ai0], LRET[ai0], SIG2_30[ai0]); accVT = account_cx(Wvt, ts0, Fsub0, RET[ai0], LRET[ai0], SIG2_30[ai0])
    gC1 = gates(accVT, accC2, ts0, mkt0, mask_main, key="net")
    gC1.update({"m_T_mean": round(float(mT[mask_main].mean()), 4), "m_T_frac_at_floor": round(float((mT[mask_main] <= 0.5).mean()), 4), "m_T_frac_at_cap": round(float((mT[mask_main] >= 1.5).mean()), 4),
                "gross_vt_mean": round(float(accVT["gross"][mask_main].mean()), 4), "gross_c2_mean": round(float(accC2["gross"][mask_main].mean()), 4), "note": "C1 = whole-book vol-target control on A0 (actual-gross accounting, cost on Δ(m_T·W_c2)); expected NOT to pass"})
    R["C1_voltarget_control"] = {"main_2022_06": gC1, "FULL": gates(accVT, accC2, ts0, mkt0, mask_full, key="net"), "2024-26": gates(accVT, accC2, ts0, mkt0, mask_2426, key="net")}
    log("C1 control", {k: gC1[k] for k in ("G1_delta_sharpe", "G2_n_years_ge0", "G3_pass", "G4_turnover_ratio", "sharpe_arm", "sharpe_base")})
    # ---- C2 pure tilt: simple vs log sharpe (mechanism)
    c2 = ACC["C2_tilt"]; gq = np.where(c2["gross"] > 1e-9, c2["gross"], np.nan)
    R["C2_tilt_mechanism"] = {"sharpe_pnl_simple_g2": round(sharpe_a(c2["pnl_g2"][mask_main]), 4), "sharpe_pnl_log_g2": round(sharpe_a((2 * np.nan_to_num(c2["pnl_log"] / gq))[mask_main]), 4),
                              "mean_pnl_simple_g2": round(float(c2["pnl_g2"][mask_main].mean()), 4), "mean_pnl_log_g2": round(float((2 * np.nan_to_num(c2["pnl_log"] / gq))[mask_main].mean()), 4),
                              "mean_conv_g2": round(float((2 * np.nan_to_num(c2["conv"] / gq))[mask_main].mean()), 4), "net_g2_sharpe": round(sharpe_a(c2["net_g2"][mask_main]), 4), "net_g2_mean": round(float(c2["net_g2"][mask_main].mean()), 4),
                              "by_year_net_g2_mean": {int(y): round(float(c2["net_g2"][mask_main][yr_of(ts0[mask_main]) == y].mean()), 3) for y in sorted(set(yr_of(ts0[mask_main]).tolist()))},
                              "corr_with_A0_net_g2": round(float(np.corrcoef(c2["net_g2"][mask_main], ACC["A0"]["net_g2"][mask_main])[0, 1]), 4), "turnover_mean": round(float(c2["trn"][mask_main].mean()), 5)}
    # ---- secondary object: in-role S1 with A2(p80) post-hoc overlay on held weights
    try:
        SR = np.load(INPUTS["inrole_sr_npz"], allow_pickle=True); ats = SR["mine_p3_SIM_ats"].astype(np.int64); WS1 = SR["mine_p3_SIM_W_S1"].astype(np.float64); lsym = [str(s) for s in SR["symbols"]]
        lmap = np.array([syms.index(s) for s in lsym]); ail, okl = align(ats); assert okl.all()
        Wl = np.zeros((len(ats), NW)); Wl[:, lmap] = WS1
        sigl = np.sqrt(np.maximum(np.nan_to_num(SIG2_30[ail]), 0))
        Wo = Wl.copy(); capfr = []
        for i in range(len(ats)):
            w = Wo[i]; shrt = w < 0; lng = w > 0
            if shrt.sum() < 5 or not lng.any(): capfr.append(0.0); continue
            v = np.abs(w) * sigl[i]; vs = v[shrt]; qv = np.percentile(vs, 80)
            over = shrt & (v > qv); fct = np.ones(NW); fct[over] = qv / np.where(v > 0, v, 1)[over]
            capfr.append(float((np.abs(w[over]) * (1 - fct[over])).sum() / max(np.abs(w[shrt]).sum(), 1e-12)))
            w2 = w * fct; Lg = w2[lng].sum(); Sg = np.abs(w2[shrt]).sum()
            if Sg > 1e-12: w2[shrt] *= Lg / Sg
            g1 = np.abs(w).sum(); g2_ = np.abs(w2).sum()
            if g2_ > 1e-12: w2 *= g1 / g2_
            Wo[i] = w2
        Fl = {k2: F[k2][ail] for k2 in F}
        accL0 = account_cx(Wl, ats, Fl, RET[ail], LRET[ail], SIG2_30[ail]); accL2 = account_cx(Wo, ats, Fl, RET[ail], LRET[ail], SIG2_30[ail])
        mkl = mkt[ail]; mL = ats <= T_END_MAIN
        R["inrole_S1_A2p80_overlay"] = {"note": "post-hoc overlay on SR mine_p3_SIM_W_S1 held weights (EMA/stop path not re-run) — 对照, 不裁", "gates_main": gates(accL2, accL0, ats, mkl, mL), "gates_2024_26": gates(accL2, accL0, ats, mkl, mL & (yr_of(ats) >= 2024)),
                                        "cap_frac_short_gross_mean": round(float(np.mean(capfr)), 4), "base_sharpe_expected_0.433": round(sharpe_a(accL0["net_g2"][mL]), 4),
                                        "conv_base": {"total": round(float(accL0["conv"][mL].mean()), 4), "short": round(float(accL0["conv_short"][mL].mean()), 4), "long": round(float(accL0["conv_long"][mL].mean()), 4)},
                                        "conv_overlay": {"total": round(float(accL2["conv"][mL].mean()), 4), "short": round(float(accL2["conv_short"][mL].mean()), 4), "long": round(float(accL2["conv_long"][mL].mean()), 4)},
                                        "sig_short_base_vs_overlay": [round(float(accL0["sig_short"][mL].mean()), 5), round(float(accL2["sig_short"][mL].mean()), 5)]}
        log("inrole overlay", {k: R["inrole_S1_A2p80_overlay"]["gates_main"][k] for k in ("G1_delta_sharpe", "sharpe_arm", "sharpe_base", "G4_turnover_ratio")})
    except Exception as e:
        import traceback; R["inrole_overlay_error"] = traceback.format_exc()[-1200:]; log("inrole overlay error", repr(e))
    # ---- main-arm attribution: tilt component own net; per-leg table
    for nm in ("A1_k1.0", "A1_k0.5", "A1g", "A4_k1.0", "A2_p80", "A0", "A1n_k1.0", "A1n_k0.5"):
        R.setdefault("legs_main_span", {})[nm] = SUMM[nm]["2022-01..2026-06"].get("legs")
    # ---- save
    np.savez_compressed(f"{CX}/cx_series.npz", **{f"{nm}__{k}": v for nm, acc in ACC.items() for k, v in acc.items() if not isinstance(v, dict)},
                        **{f"{nm}__diag_{k}": v for nm, ch in chains.items() for k, v in ch["diag"].items()}, **{f"{nm}__w3": ch["w3"] for nm, ch in chains.items()},
                        C1_vt__net=accVT["net"], C1_c2__net=accC2["net"], C1_mT=mT, inrole_overlay_net_g2=(accL2["net_g2"] if "accL2" in dir() else np.zeros(1)), ts=ts0, mkt=mkt0, anchors=A)
    np.savez_compressed(f"{CX}/cx_weights_A1_k1.npz", ts=chains["A1_k1.0"]["ts"], W=chains["A1_k1.0"]["W"], WL=chains["A1_k1.0"]["WL"], symbols=np.array(syms))
    json.dump(R, open(f"{CX}/convexity_aware_construction_2026-08-22.json", "w"), indent=1, ensure_ascii=False, default=float)
    log("run DONE ->", f"{CX}/convexity_aware_construction_2026-08-22.json", "VERDICT main", R["verdict_main"])

if __name__ == "__main__":
    st = sys.argv[1] if len(sys.argv) > 1 else "run"
    nw = int(sys.argv[2]) if len(sys.argv) > 2 else 12
    {"run": lambda: stage_run(nw)}[st]()
