"""W2b · B 信号级融合首读 @jpline(2026-08-22, Session 6737834a-W2b; DESIGN_optimization_path §3.1 二读)。
用法: python w2_signal_blend.py   (须先跑 w2_merged_book_replay.py: 读其 probe_artifacts/w2b_merged_book_2026-08-22.json / w2b_merged_series.npz 作 A 对照)

============================== 先验与冻结判据(先于数字) ==============================
先验(派工原文): 两 king 几乎不相关(0.05), 信号级通常不优于权重级; 它的机会只在 ~110 个重叠名字。
构造: 在役逐锚合成分 = legs.compose_book 的 `combined`(king/s2/funding 三腿单位 gross 加权和, 未整形) 在在役成员上秩中心化 xz_L;
      宽逐锚合成分 = slow-LGBM 三腿 w3 加权秩和 z 在 sel 上秩中心化 xz_W; 并集宇宙上: 重叠名 s = xz(0.5·xz_L + 0.5·xz_W)(主; 二次秩中心化使重叠名与单书名同尺度)
      或 走前 msharpe(两书【分数排序单位 gross 截面收益】的 900 锚滚动夏普, 取正归一; <900 锚默认 0.5/0.5); 只在一本书有分的名用该书的 xz。
整形: B1(主) 并集去均值 → L1 → cap 2.5/n → L1(宽书整形, 不需 rvol); B2(敏感) compose_book 同构: 99% 分位截尾 → 去均值 → 风险预算 α.5 λ1(σ = 宽面板 f_vol_7d 中位归一) → 去均值 → L1。
管线: 同 A(实盘函数 apply_harvest_ema α0.05 → 在役逐名止损 −25%×2 锚冷却 42(FORCED 出场) → 带 b ∈ {0.002(主), 0.0005, 0.00025} → 成本 3.52×换手 → carry)。
口径同 A: 每单位目标 gross × G=2, 在役时钟, 共同锚 9821。
判据(冻结): 同 A 的四关对 装置纸面 P0 / 在役 L_dev 评定(信息); **B 优于 A 的判定 = ΔSharpe(B_b − A_b, 同带) ≥ +0.10 且 配对块自助 CI95 下界 > 0 且 逐年 B ≥ A ≥ 4/5 且 换手 B ≤ A**; 否则 A(权重级)维持为参照。
额外报告: 混合分 秩 IC(并集 / 重叠名)vs 两单书分 IC; 权重级合成目标(0.3/0.7)作为"分数"的 IC 同表; 各分组(重叠/仅在役/仅宽) gross 份额(隐含配比)。
=====================================================================================
输入 SHA256: 与 A 同一 pins 文件(probe_artifacts/w2b_input_pins.json)逐文件核验 + A 的结果 json/npz 的 SHA 记入输出。只读数据, 写 probe_artifacts/w2b_*。
"""
import os, sys, json, time, numpy as np
from scipy.stats import spearmanr
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import w2b_common as C
PD, B = C.PD, C.B; G = 2.0; COST_MAIN = 3.52; LOOK = 900
t0 = time.time()
def log(*a): print(*a, round(time.time() - t0, 1), "s", flush=True)
pins = json.load(open(f"{PD}/w2b_input_pins.json"))
for p, s in pins.items():
    got = C.sha(p); assert got == s, f"SHA mismatch {p}"
A_JSON = f"{PD}/w2b_merged_book_2026-08-22.json"; A_NPZ = f"{PD}/w2b_merged_series.npz"
A = json.load(open(A_JSON)); AS = np.load(A_NPZ, allow_pickle=True); a_sha = {"A_json": C.sha(A_JSON), "A_npz": C.sha(A_NPZ)}
D = C.load_all(); n, NW, yr = D.n, D.NW, D.yr; yrs = sorted(set(yr.tolist()))
log("loaded")
# ---------------------------------------------------------------- scores
XZ_L = np.full((n, NW), np.nan, np.float32); XZ_W = np.full((n, NW), np.nan, np.float32)
rL = np.zeros(n); rW = np.zeros(n)
UNI_L = [np.sort(D.lmap[m]) for m in D.MSK_L]; UNI_W = [np.sort(np.asarray(u)) for u in D.UNI_W]; UNI_M = [np.union1d(a, b) for a, b in zip(UNI_L, UNI_W)]
for i in range(n):
    m = D.MSK_L[i]; cl = np.asarray(D.COMBO_L[i, m], float); z = C.xz(cl); XZ_L[i, D.lmap[m]] = z
    y = np.nan_to_num(np.asarray(D.R[i, D.lmap[m]], float)); zz = np.nan_to_num(z); g = np.abs(zz).sum(); rL[i] = (zz / g * y).sum() * 1e4 if g > 0 else 0.0
    sel = D.SEL_W[i]; zw = np.asarray(D.ZW[i], float); idx = np.where(sel & np.isfinite(zw))[0]; z2 = C.xz(zw[idx]); XZ_W[i, idx] = z2
    y2 = np.nan_to_num(np.asarray(D.R[i, idx], float)); zz2 = np.nan_to_num(z2); g2 = np.abs(zz2).sum(); rW[i] = (zz2 / g2 * y2).sum() * 1e4 if g2 > 0 else 0.0
log("scores done")
def msharpe_w(i):
    if i < LOOK: return 0.5, 0.5
    a = rL[i - LOOK:i]; b = rW[i - LOOK:i]
    sa = max(a.mean() / (a.std() + 1e-9), 0.0); sb = max(b.mean() / (b.std() + 1e-9), 0.0)
    return (0.5, 0.5) if sa + sb <= 0 else (sa / (sa + sb), sb / (sa + sb))
def blended_scores(mode):
    S = np.full((n, NW), np.nan, np.float32); WB = np.zeros((n, 2)); grp_share = np.zeros((n, 3))
    for i in range(n):
        wl, ww = (0.5, 0.5) if mode == "fixed" else msharpe_w(i); WB[i] = (wl, ww)
        l = XZ_L[i]; w = XZ_W[i]; both = np.isfinite(l) & np.isfinite(w); onlyl = np.isfinite(l) & ~np.isfinite(w); onlyw = np.isfinite(w) & ~np.isfinite(l)
        s = np.full(NW, np.nan)
        if both.sum() >= 10: s[both] = C.xz(wl * l[both] + ww * w[both])
        elif both.any(): s[both] = wl * l[both] + ww * w[both]
        s[onlyl] = l[onlyl]; s[onlyw] = w[onlyw]
        S[i] = s
    return S, WB
def shape_B1(s):
    """并集去均值 → L1 → cap 2.5/n → L1 (宽书整形)."""
    ok = np.isfinite(s); w = np.where(ok, s, 0.0); nn = int(ok.sum())
    if nn < 10: return np.zeros(NW)
    w[ok] -= w[ok].mean(); g = np.abs(w).sum()
    if g < 1e-12: return np.zeros(NW)
    w /= g; capw = 2.5 / nn; w = np.clip(w, -capw, capw); g2 = np.abs(w).sum()
    return w / g2 if g2 > 1e-12 else w
def shape_B2(s, sig):
    """compose_book 同构: 99% 截尾 → 去均值 → RB α.5 λ1(σ=f_vol_7d 中位归一) → 去均值 → L1."""
    ok = np.isfinite(s); idx = np.where(ok)[0]
    if len(idx) < 10: return np.zeros(NW)
    mag = s[idx].astype(float); lo, hi = np.percentile(mag, 1), np.percentile(mag, 99); mag = np.clip(mag, lo, hi); shaped = mag - mag.mean()
    sg = np.asarray(sig[idx], float); fin = np.isfinite(sg) & (sg > 0)
    if fin.any():
        med = float(np.median(sg[fin])); sg = np.where(fin, sg, med)
        if med > 0:
            w_ = np.sign(shaped) * np.abs(shaped) ** 0.5 / (sg / med); shaped = w_ - w_.mean()
    out = np.zeros(NW); g = np.abs(shaped).sum(); out[idx] = shaped / g if g > 1e-12 else 0.0
    return out
# ---------------------------------------------------------------- IC report (rank IC of scores vs R on same clock)
def ic_series(S, UNI):
    ic = np.full(n, np.nan)
    for i in range(n):
        u = UNI[i]; s = S[i, u]; y = D.R[i, u]; ok = np.isfinite(s) & np.isfinite(y)
        if ok.sum() >= 10: ic[i] = spearmanr(s[ok], y[ok]).correlation
    return ic
def ic_stats(ic):
    ok = np.isfinite(ic); x = ic[ok]; yy = yr[ok]
    return {"mean": round(float(x.mean()), 5), "t": round(float(x.mean() / x.std(ddof=1) * np.sqrt(len(x))), 2), "n": int(len(x)), "by_year": {int(y): round(float(x[yy == y].mean()), 5) for y in yrs}}
S_fixed, WB_fixed = blended_scores("fixed"); S_ms, WB_ms = blended_scores("msharpe")
OVL = [np.where(np.isfinite(XZ_L[i]) & np.isfinite(XZ_W[i]))[0] for i in range(n)]
TGT_L829 = np.zeros((n, NW), np.float32); TGT_L829[:, D.lmap] = D.TGT_L
MERGED_TGT = 0.3 * TGT_L829 + 0.7 * D.TGT_W
IC = {"blend_fixed_union": ic_stats(ic_series(S_fixed, UNI_M)), "blend_msharpe_union": ic_stats(ic_series(S_ms, UNI_M)),
      "live_score_on_live_names": ic_stats(ic_series(XZ_L, UNI_L)), "wide_score_on_sel_names": ic_stats(ic_series(XZ_W, [np.where(np.isfinite(XZ_W[i]))[0] for i in range(n)])),
      "overlap: live_score": ic_stats(ic_series(XZ_L, OVL)), "overlap: wide_score": ic_stats(ic_series(XZ_W, OVL)), "overlap: blend_fixed": ic_stats(ic_series(S_fixed, OVL)), "overlap: blend_msharpe": ic_stats(ic_series(S_ms, OVL)),
      "weight_level_merged_target_0.3/0.7_as_score_union": ic_stats(ic_series(np.where(MERGED_TGT != 0, MERGED_TGT, np.nan), UNI_M)),
      "n_overlap_mean": round(float(np.mean([len(o) for o in OVL])), 1), "msharpe_w_wide_mean_by_year": {int(y): round(float(WB_ms[yr == y, 1].mean()), 3) for y in yrs}}
log("IC done", json.dumps(IC["blend_fixed_union"]), json.dumps(IC["overlap: blend_fixed"]))
# ---------------------------------------------------------------- targets + arms
def build_targets(S, shaping):
    T = np.zeros((n, NW), np.float32); gs = np.zeros((n, 3))
    for i in range(n):
        w = shape_B1(S[i]) if shaping == "B1" else shape_B2(S[i], D.VOL7A[i])
        T[i] = w; aw = np.abs(w); g = aw.sum()
        if g > 0:
            l = np.isfinite(XZ_L[i]); ww = np.isfinite(XZ_W[i])
            gs[i] = (aw[l & ww].sum() / g, aw[l & ~ww].sum() / g, aw[ww & ~l].sum() / g)
    return T, gs
SER = {}; X = {}; STATS = {}; GS = {}
plan = [("B_fixed_B1_b0.002", "fixed", "B1", 0.002), ("B_fixed_B1_b0.0005", "fixed", "B1", 0.0005), ("B_fixed_B1_b0.00025", "fixed", "B1", 0.00025),
        ("B_ms_B1_b0.002", "msharpe", "B1", 0.002), ("B_ms_B1_b0.0005", "msharpe", "B1", 0.0005), ("B_ms_B1_b0.00025", "msharpe", "B1", 0.00025),
        ("B_fixed_B2_b0.0005", "fixed", "B2", 0.0005)]
cacheT = {}
for tag, mode, shp, b in plan:
    key = (mode, shp)
    if key not in cacheT: cacheT[key] = build_targets(S_fixed if mode == "fixed" else S_ms, shp)
    T, gs = cacheT[key]; GS[tag] = {"overlap": round(float(gs[:, 0].mean()), 4), "live_only": round(float(gs[:, 1].mean()), 4), "wide_only": round(float(gs[:, 2].mean()), 4)}
    O = C.engine(D, T, UNI_M, D.R, alpha=0.05, band=b, stop=(-0.25, 2, 42), forced_exit=True, keep_W=(tag == "B_fixed_B1_b0.002"), tag=tag)
    SER[tag] = {k: np.asarray(O[k], float) for k in O if k != "W" and O[k] is not None}
    X[tag] = O["pnl"] - O["carry"] - COST_MAIN * O["trn"]
    log("ARM", tag, "sharpe", round(C.sharpe(X[tag]), 3), "trn", round(float(O["trn"].mean()), 5), "gross", round(float(O["gross"].mean()), 4), "gs", GS[tag])
    if tag == "B_fixed_B1_b0.002": np.savez_compressed(f"{PD}/w2b_signal_W.npz", ts=D.ts, symbols=np.array(D.WSYM), W=O["W"])
# ---------------------------------------------------------------- compare with A
XA = {k[3:]: AS[k] for k in AS.files if k.startswith("X__")}
Lx = XA["L_dev"]; Px = XA["P_w07"]; Wx = XA["W_dev_own"]
Lw2 = np.load(f"{PD}/w2_live_series.npz", allow_pickle=True); Q = C.q4_masks(Lx, Lw2["mkt_ew"].astype(float), Lw2["btc4"].astype(float), yr)
def full_stats(tag, x):
    s = C.series_stats(x, yr, G); s["Q4_mean_at_G"] = {k: round(float(x[m].mean() * G), 3) for k, m in Q.items()}
    if tag in SER:
        S = SER[tag]; s["turnover_unit_mean"] = round(float(S["trn"].mean()), 5); s["gross_held_mean"] = round(float(S["gross"].mean()), 4)
        s["gross_held_by_year"] = {int(y): round(float(S["gross"][yr == y].mean()), 4) for y in yrs}; s["maxw_mean"] = round(float(S["maxw"].mean()), 5); s["maxw_max"] = round(float(S["maxw"].max()), 5)
        s["nheld_mean"] = round(float(S["nheld"].mean()), 1); s["stop_fires_total"] = int(S["fires"].sum()); s["carry_mean_at_G"] = round(float(S["carry"].mean() * G), 4)
        s["cost_main_at_G"] = round(float(S["trn"].mean() * COST_MAIN * G), 4); s["gross_pnl_at_G"] = round(float(S["pnl"].mean() * G), 4)
        s["sharpe_cost_sens"] = {str(c): round(C.sharpe(S["pnl"] - S["carry"] - c * S["trn"]), 3) for c in (4.137, 0.32)}; s["sharpe_cost_tiered"] = round(C.sharpe(S["pnl"] - S["carry"] - S["cost_tier"]), 3)
        for g_ in (30800, 50000):
            s[f"cap_{g_}"] = {"n_red_mean": round(float(S[f"cap_nred_{g_}"].mean()), 2), "n_red_last500": round(float(S[f"cap_nred_{g_}"][-500:].mean()), 2), "share_red_mean": round(float(S[f"cap_sred_{g_}"].mean()), 4),
                              "share_red_last500": round(float(S[f"cap_sred_{g_}"][-500:].mean()), 4), "share_below_5usdt_last500": round(float(S[f"cap_sfloor5_{g_}"][-500:].mean()), 4)}
        s["group_gross_share"] = GS[tag]
    return s
for tag in X: STATS[tag] = full_stats(tag, X[tag])
for tag in ("L_dev", "W_dev_own", "P_w07", "M_w07_b0.002", "M_w07_b0.0005", "M_w07_b0.00025"):
    if tag in XA: STATS[f"A:{tag}"] = A["stats"].get(tag, C.series_stats(XA[tag], yr, G))
def crit(tag):
    x = X[tag]; sM = C.sharpe(x); sP = C.sharpe(Px); sL = C.sharpe(Lx); sW = C.sharpe(Wx)
    byM = STATS[tag]["by_year_sharpe"]; byL = {int(y): C.sharpe(Lx[yr == y]) for y in yrs}; byW = {int(y): C.sharpe(Wx[yr == y]) for y in yrs}
    trM = STATS[tag]["turnover_unit_mean"]; trP = 0.3 * A["stats"]["L_dev"]["turnover_unit_mean"] + 0.7 * A["stats"]["W_dev_own"]["turnover_unit_mean"]
    nB = sum(1 for y in yrs if byM[y] >= byL[y]); nA = sum(1 for y in yrs if byM[y] >= max(byL[y], byW[y]))
    b = tag.split("_b")[-1]; atag = f"M_w07_b{b}"; xa = XA.get(atag)
    out = {"sharpe": round(sM, 3), "paper_sharpe": round(sP, 3), "live_sharpe": round(sL, 3), "c1": bool(sM >= sP - 0.10), "c2": bool(sM >= sL + 0.15), "c3_years_ge_live": f"{nB}/{len(yrs)}", "years_ge_max_single": f"{nA}/{len(yrs)}",
           "c4_turnover": round(trM, 5), "c4_paper_turnover": round(trP, 5), "c4": bool(trM <= trP)}
    out["PASS_4gates"] = bool(out["c1"] and out["c2"] and nB >= 4 and out["c4"])
    if xa is not None:
        sA = C.sharpe(xa); byA = {int(y): C.sharpe(xa[yr == y]) for y in yrs}; nBA = sum(1 for y in yrs if byM[y] >= byA[y]); trA = A["stats"][atag]["turnover_unit_mean"]
        bt = C.boot_delta_sharpe(x, xa)
        out["vs_A_same_band"] = {"A_arm": atag, "A_sharpe": round(sA, 3), "delta_sharpe_B_minus_A": round(sM - sA, 3), "boot": bt, "years_B_ge_A": f"{nBA}/{len(yrs)}", "turnover_B": round(trM, 5), "turnover_A": round(trA, 5),
                                "B_preferred(Δ≥0.10 & CI>0 & years≥4/5 & trn_B≤trn_A)": bool((sM - sA >= 0.10) and (bt["CI95"][0] > 0) and nBA >= 4 and trM <= trA)}
    return out
CRIT = {tag: crit(tag) for tag in X}
RHO = {f"{tag}|A_{tag.split('_b')[-1]}": round(float(np.corrcoef(X[tag], XA[f"M_w07_b{tag.split('_b')[-1]}"])[0, 1]), 4) for tag in X if f"M_w07_b{tag.split('_b')[-1]}" in XA}
RHO.update({f"{tag}|L_dev": round(float(np.corrcoef(X[tag], Lx)[0, 1]), 4) for tag in X}); RHO.update({f"{tag}|W_dev_own": round(float(np.corrcoef(X[tag], Wx)[0, 1]), 4) for tag in X})
TRIP = {tag: {"replay": C.trip(X[tag], G, 1.0), "shrink0.55": C.trip(X[tag], G, 0.55)} for tag in ("B_fixed_B1_b0.002", "B_fixed_B1_b0.0005", "B_ms_B1_b0.0005")}
anyB = [t for t in CRIT if CRIT[t].get("vs_A_same_band", {}).get("B_preferred(Δ≥0.10 & CI>0 & years≥4/5 & trn_B≤trn_A)")]
verdict = ("B preferred over A in arms: " + ",".join(anyB)) if anyB else "B not better than A (no arm meets Δ≥0.10 & CI>0 & years & turnover) ⇒ 权重级(A)维持为参照"
RES = {"meta": {"created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "session": "6737834a-W2b", "G": G, "cost_main": COST_MAIN, "inputs_sha256": pins, "A_inputs_sha256": a_sha,
                "prior": "两 king ρ≈0.05-0.2; 信号级通常不优于权重级; 机会只在重叠名", "frozen_rule": "B preferred iff ΔS(B−A same band)≥0.10 & boot CI95 low>0 & years B≥A ≥4/5 & trn_B≤trn_A"},
       "IC": IC, "group_gross_share": GS, "stats": STATS, "criteria": CRIT, "rho": RHO, "trip_probability": TRIP, "verdict": verdict}
json.dump(RES, open(f"{PD}/w2b_signal_blend_2026-08-22.json", "w"), indent=1, ensure_ascii=False)
np.savez_compressed(f"{PD}/w2b_signal_series.npz", ts=D.ts, yr=yr, **{f"{tag}__{k}": v for tag, S in SER.items() for k, v in S.items()}, **{f"X__{tag}": v for tag, v in X.items()}, rL=rL, rW=rW, WB_ms=WB_ms)
print("VERDICT", verdict)
for tag in CRIT: print("CRIT", tag, json.dumps(CRIT[tag], ensure_ascii=False))
print("IC", json.dumps(IC, ensure_ascii=False))
print("DONE", round(time.time() - t0), "s")
