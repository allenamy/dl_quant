"""W2 红队追加 A · 在役书逐锚【精确可加】腿归因 @jpline(2026-08-22, Session 6737834a-W2)。
书构造 = w2_live_replay.py(= cond_stop_tail.py 逐字, 实盘 legs.compose_book / apply_harvest_ema 原样 import)不变;
新增: 把持仓向量 w 精确分解为 king/s2/funding 三个分量, Σ分量 ≡ w(逐锚断言 <1e-9):
  ① compose_book 输出 target_w 与 legs_unit; 逐名按各腿对该名合成分的贡献份额拆 target: c_k = W_k·legs_unit_k;
     若 |Σc_k| ≥ 0.25·Σ|c_k|(各腿大致同向)用有符号份额 c_k/Σc_k(Σ=1, |份额|≤4); 否则(各腿互相抵消)用 |c_k|/Σ|c_k| 份额(Σ=1)。
     ⇒ 形状层(cap/去均值/风险预算 α.5λ1/再去均值/L1)是逐名单调变换, 以"各腿对该名的推力份额"分摊该名最终目标权重 = 精确可加的约定。
  ② 收割 EMA α0.05: 总量走实盘 apply_harvest_ema; 分量用同一递推(新名以自身分量 raw 起步)+ 同一去均值 + 【总量的】L1 归一化常数 ⇒ Σ分量 ≡ 总量。
  ③ 止损置零 / 带(用总量 |Δ|>b 的掩码, 逐分量同掩码, 交易名内去均值逐分量)⇒ Σ保持。
逐锚逐腿: 价格 pnl_k = w_k·Y4; carry_k = w_k·fund_now·4/iv(宽 v2 面板映射; 正 = 该腿【付出】funding, 负 = 收到); cost_k = Σ_名 4.137·|Δw_名| × |Δw_k,名|/Σ_j|Δw_j,名|; gross_k = |w_k|₁。
输出: probe_artifacts/w2_live_legattrib.npz(S0 / S1) + w2_live_legattrib_summary.json(含 net 与 net_S{0,1}.npy 逐元素相等的收据)。
"""
import sys, json, time, numpy as np
PD = "/mnt/storage/private/work_hsy/probe_artifacts"; sys.path.insert(0, PD)
MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
sys.path.insert(0, MA); sys.path.insert(0, MA + "/engine/live"); sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset")
sys.path.insert(0, PD)
import legs as LG
import engine.replay_fullhist as RF
B = "/mnt/storage/private/work_hsy/pod_backup_2026-08-21"
W = {"king": .5952380952380952, "s2": .20238095238095238, "funding": .20238095238095238, "size": 0.}
RB = {"alpha": .5, "lambda": 1.}; C1 = 4.137; BW = 0.002; COOL = 42; A_EMA = 0.05
LEGS = ("king", "s2", "funding")
t0 = time.time()
src = RF.get_src(None, f"{PD}/king_pred_newgen.npz", f"{PD}/s2_pred_newgen.npz")
a, yr = RF._all_anchors(src); N = src.N; n = len(a)
FI, RVI = src.fund_idx, src.ch.index("rvol_24h"); SYMS = [str(s) for s in src.symbols]
ts_all = np.asarray(src.ts); tss = ts_all // 1000 if (ts_all[1] - ts_all[0]) >= 3600 * 1000 else ts_all
ats = np.array([int(tss[int(t)]) for t in a], dtype=np.int64)
assert np.array_equal(np.load(f"{PD}/net_S1_ts.npy")[:, 0].astype(np.int64), ats)
PW = np.load(f"{B}/wide_panel_4h_hist_v2.npz", allow_pickle=True)
wsym = [str(s) for s in PW["symbols"]]; widx = {s: i for i, s in enumerate(wsym)}
pw_row = {int(t): j for j, t in enumerate(PW["ts"].astype(np.int64))}
FN = PW["f_fund_now"]; IV = PW["f_fund_iv"]
map_live = np.array([widx.get(s, -1) for s in SYMS]); mapped = map_live >= 0
# ---- precompute targets + components ----
TGT, TGTK, MSK, RET = [], {k: [] for k in LEGS}, [], []
held = {"k": np.full(N, np.nan), "s": np.full(N, np.nan), "f": np.full(N, np.nan)}
share_stats = {"signed": 0, "abs": 0, "zero": 0}
for i, t in enumerate(a):
    ti = int(t); m = np.asarray(src.tradeable(ti))
    if m.dtype == bool: m = np.where(m)[0]
    if i == 0 or ti % 8 == 0:
        v = np.full(N, np.nan); v[m] = src.king[ti, m]; held["k"] = v
    if i == 0 or ti % 24 == 0:
        v = np.full(N, np.nan); v[m] = src.s2[ti, m]; held["s"] = v
    if i == 0 or ti % 8 == 0:
        v = np.full(N, np.nan); v[m] = src.CH[ti, m, FI]; held["f"] = v
    r = LG.compose_book(held["k"][m], held["s"][m], held["f"][m], np.ones(len(m)), weights=W, rvol=src.CH[ti, m, RVI].astype(float), risk_budget=RB)
    tw = np.asarray(r["target_w"], float)
    ck = {k: W[k] * np.nan_to_num(np.asarray(r["legs_unit"][k], float)) for k in LEGS}
    csum = ck["king"] + ck["s2"] + ck["funding"]; cabs = np.abs(ck["king"]) + np.abs(ck["s2"]) + np.abs(ck["funding"])
    signed = np.abs(csum) >= 0.25 * cabs
    zero = cabs <= 1e-15
    share_stats["signed"] += int((signed & ~zero).sum()); share_stats["abs"] += int((~signed & ~zero).sum()); share_stats["zero"] += int(zero.sum())
    sk = {}
    with np.errstate(all="ignore"):
        for k in LEGS:
            s_signed = np.where(np.abs(csum) > 0, ck[k] / np.where(np.abs(csum) > 0, csum, 1.0), 0.0)
            s_abs = np.where(cabs > 0, np.abs(ck[k]) / np.where(cabs > 0, cabs, 1.0), 1.0 / 3)
            sk[k] = np.where(zero, 1.0 / 3, np.where(signed, s_signed, s_abs))
    w_tot = np.full(N, 0.0); w_tot[m] = tw; TGT.append(w_tot)
    for k in LEGS:
        wk = np.full(N, 0.0); wk[m] = tw * sk[k]; TGTK[k].append(wk)
    assert np.max(np.abs(sum(TGTK[k][-1] for k in LEGS) - w_tot)) < 1e-9
    MSK.append(m); RET.append(src.Y4[ti, m].astype(float))
    if i % 3000 == 0: print("precompute", i, "/", n, round(time.time() - t0, 1), "s", flush=True)
print("share_stats", share_stats, flush=True)

def run(mode):
    state = None; stk = {k: {} for k in LEGS}
    prev = np.zeros(N); prevk = {k: np.zeros(N) for k in LEGS}
    Pi = np.ones(N); sh = np.zeros(N); cb = np.zeros(N); cnt = np.zeros(N, int); su = np.full(N, -1)
    rec = []; maxerr = 0.0
    for i in range(n):
        m = MSK[i]; syms = [SYMS[j] for j in m]
        out = LG.apply_harvest_ema(TGT[i][m], syms, state, A_EMA); state = out["state"]
        tgt = np.asarray(out["target_w"], float)
        cur_tot = np.array([state[s] for s in syms], float); s_tot = float(np.abs(cur_tot - cur_tot.mean()).sum())
        tgtk = {}
        for k in LEGS:
            rawk = TGTK[k][i][m]; prevd = stk[k]
            curk = np.array([(1.0 - A_EMA) * float(prevd.get(s, rawk[q])) + A_EMA * rawk[q] for q, s in enumerate(syms)], float)
            ok_ = curk - curk.mean(); tgtk[k] = ok_ / s_tot if s_tot > 1e-12 else ok_
            stk[k] = {s: float(v) for s, v in zip(syms, curk)}
        err = float(np.max(np.abs(tgtk["king"] + tgtk["s2"] + tgtk["funding"] - tgt))); maxerr = max(maxerr, err)
        if mode != "S0":
            bs = set(np.where(su > i)[0].tolist())
            if bs:
                for k2, j in enumerate(m):
                    if j in bs:
                        tgt[k2] = 0.0
                        for k in LEGS: tgtk[k][k2] = 0.0
        nonm = [j for j in range(N) if j not in set(m)]
        w = prev.copy(); w[nonm] = 0.0
        d = tgt - w[m]; T = np.abs(d) > BW
        wm = w[m].copy(); wm[T] = tgt[T]
        if T.any(): wm[T] -= wm.sum() / T.sum()
        w[m] = wm
        wk = {}
        for k in LEGS:
            wk_ = prevk[k].copy(); wk_[nonm] = 0.0; wmk = wk_[m].copy(); wmk[T] = tgtk[k][T]
            if T.any(): wmk[T] -= wmk.sum() / T.sum()
            wk_[m] = wmk; wk[k] = wk_
        err2 = float(np.max(np.abs(wk["king"] + wk["s2"] + wk["funding"] - w))); maxerr = max(maxerr, err2)
        y = RET[i]; ok = np.isfinite(y); idx = m[ok]
        yfull = np.zeros(N); yfull[idx] = y[ok]
        pnl = float((w * yfull).sum() * 1e4); pnlk = {k: float((wk[k] * yfull).sum() * 1e4) for k in LEGS}
        # carry
        j = pw_row.get(int(ats[i]))
        fc = np.zeros(N)
        if j is not None:
            fnv = FN[j, map_live[mapped]]; ivv = IV[j, map_live[mapped]]
            fin = np.isfinite(fnv); fnv = np.where(fin, fnv, 0.0); ivv = np.where(np.isfinite(ivv) & (ivv > 0), ivv, 8.0)
            fc[mapped] = fnv * (4.0 / ivv)
        carry = float((w * fc).sum() * 1e4); carryk = {k: float((wk[k] * fc).sum() * 1e4) for k in LEGS}
        # cost: per-name |Δw|·C1, split by component |Δw_k| shares
        dw = np.abs(w - prev); den = sum(np.abs(wk[k] - prevk[k]) for k in LEGS)
        with np.errstate(all="ignore"):
            costk = {k: float((dw * C1 * np.where(den > 0, np.abs(wk[k] - prevk[k]) / np.where(den > 0, den, 1.0), 1.0 / 3)).sum()) for k in LEGS}
        cost = float(dw.sum() * C1)
        row = [int(ats[i]), pnl, carry, cost, float(np.abs(w).sum())]
        for k in LEGS: row += [pnlk[k], carryk[k], costk[k], float(np.abs(wk[k]).sum())]
        rec.append(row)
        # stop bookkeeping (totals; identical to cond_stop_tail)
        nsh = np.where(Pi > 1e-12, w / Pi, 0.0)
        same = np.sign(nsh) == np.sign(sh); add = same & (np.abs(nsh) > np.abs(sh))
        red = same & (~add) & (np.abs(nsh) > 1e-12); new = (~same) | (np.abs(sh) < 1e-12)
        cb = np.where(add, cb + (nsh - sh) * Pi, cb)
        with np.errstate(all="ignore"):
            ratio = np.where(np.abs(sh) > 1e-12, nsh / np.where(np.abs(sh) > 1e-12, sh, 1.0), 0.0)
        cb = np.where(red, cb * ratio, cb); cb = np.where(new, nsh * Pi, cb); cb = np.where(np.abs(nsh) < 1e-12, 0.0, cb)
        sh = nsh
        with np.errstate(all="ignore"):
            avg = np.where(np.abs(sh) > 1e-12, cb / sh, np.nan)
            dep = np.where(np.isfinite(avg) & (Pi > 0), np.sign(sh) * (1.0 - avg / Pi), 0.0)
        if mode != "S0":
            cand = (np.abs(sh) > 1e-12) & (dep <= -0.25) & (su <= i)
            cnt = np.where(cand, cnt + 1, 0); fire = cnt >= 2
            if fire.any(): su[fire] = i + COOL; cnt[fire] = 0
        prev = w; prevk = wk; Pi = Pi * (1.0 + yfull)
        if i % 3000 == 0: print(mode, i, "/", n, round(time.time() - t0, 1), "s", flush=True)
    return np.array(rec), maxerr
COLS = ["ts", "pnl", "carry", "cost", "gross"]
for k in LEGS: COLS += [f"{k}_pnl", f"{k}_carry", f"{k}_cost", f"{k}_gross"]
C = {c: q for q, c in enumerate(COLS)}
out = {"share_stats": share_stats}; save = {"cols": np.array(COLS), "ts": ats, "yr": yr}
for mode in ("S0", "S1"):
    R, maxerr = run(mode)
    net = R[:, C["pnl"]] - R[:, C["cost"]]                       # 原生口径(不含 carry), 对账 net_S{mode}.npy
    ref = np.load(f"{PD}/net_{mode}.npy")
    sp = sum(R[:, C[f"{k}_pnl"]] for k in LEGS); sc_ = sum(R[:, C[f"{k}_carry"]] for k in LEGS); sco = sum(R[:, C[f"{k}_cost"]] for k in LEGS)
    out[mode] = {"n": int(len(R)), "maxabs_net_vs_probe_artifacts": float(np.max(np.abs(net - ref))), "max_component_sum_err_weights": maxerr,
                 "maxabs_sum_pnl_vs_book": float(np.max(np.abs(sp - R[:, C["pnl"]]))), "maxabs_sum_carry_vs_book": float(np.max(np.abs(sc_ - R[:, C["carry"]]))),
                 "maxabs_sum_cost_vs_book": float(np.max(np.abs(sco - R[:, C["cost"]]))),
                 "leg_means_bps": {k: {"pnl": round(float(R[:, C[f"{k}_pnl"]].mean()), 4), "carry_paid": round(float(R[:, C[f"{k}_carry"]].mean()), 4), "cost": round(float(R[:, C[f"{k}_cost"]].mean()), 4), "gross": round(float(R[:, C[f"{k}_gross"]].mean()), 4)} for k in LEGS},
                 "book_means_bps": {"pnl": round(float(R[:, C["pnl"]].mean()), 4), "carry_paid": round(float(R[:, C["carry"]].mean()), 4), "cost": round(float(R[:, C["cost"]].mean()), 4), "net_nocarry": round(float(net.mean()), 4), "net_with_carry": round(float((net - R[:, C["carry"]]).mean()), 4)},
                 "carry_sign_convention": "carry = Σ w·fund_now·4/iv ×1e4 (宽 v2 面板映射); 正 = 书/腿【付出】funding, 负 = 收到; net_with_carry = pnl − cost − carry"}
    print("RECEIPT", mode, json.dumps(out[mode]), flush=True)
    save[mode] = R
json.dump(out, open(f"{PD}/w2_live_legattrib_summary.json", "w"), indent=1, ensure_ascii=False)
np.savez_compressed(f"{PD}/w2_live_legattrib.npz", **save)
print("DONE", round(time.time() - t0, 1), flush=True)
