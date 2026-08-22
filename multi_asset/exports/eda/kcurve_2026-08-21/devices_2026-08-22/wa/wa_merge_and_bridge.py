"""WA 附件: 合并 run/shadow/followup 结果为 results/wide_full_caliber_audit_2026-08-22.json, 并做两条桥接读数(本机, 只读 wa_series.npz):
(1) 同一 W-a d30 权重上, 成本/carry 口径替换桥: {影子分层b 成本 + ×4/iv 预测 carry} → {3.52 成本 + 实现 carry} 的 @实际 gross 夏普逐步变化(对接 WS 已发表 1hsim d30 2.218);
(2) 幻影尾巴(无收益数据的退市名冻结残量)占 gross 份额逐年, 以及以"真实 gross"(扣幻影)重标的净@2 均值/夏普敏感.
(3) 影子对账分解(宇宙外冻结尾巴 / 宇宙内残差)写入.
"""
import json, os, hashlib, time, numpy as np
D = os.path.dirname(os.path.abspath(__file__)); RES = os.path.join(os.path.dirname(D), "results")
ANN = np.sqrt(2190)
def sha(p):
    h = hashlib.sha256(); h.update(open(p, "rb").read()); return h.hexdigest()
def sharpe(x): s = x.std(ddof=1); return float(x.mean() / s * ANN) if s > 0 else float("nan")
def yr_of(ts): return np.array([time.gmtime(int(t)).tm_year for t in ts])
run = json.load(open(f"{RES}/wide_full_caliber_audit_run_2026-08-22.json")); shd = json.load(open(f"{RES}/wide_full_caliber_audit_shadow_2026-08-22.json"))
fu = json.load(open(f"{RES}/wa_followup_capacity.json")) if os.path.exists(f"{RES}/wa_followup_capacity.json") else None
Z = np.load(f"{RES}/wa_series.npz", allow_pickle=True)
out = {"session": "6737834a-WA", "created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
       "parts_sha256": {"run_json": sha(f"{RES}/wide_full_caliber_audit_run_2026-08-22.json"), "shadow_json": sha(f"{RES}/wide_full_caliber_audit_shadow_2026-08-22.json"),
                        "series_npz": sha(f"{RES}/wa_series.npz"), "device": sha(os.path.join(os.path.dirname(D), "wide_full_caliber_audit.py"))},
       "run": run, "shadow": shd, "followup_capacity": fu}
# ---- (1) bridge on Wa_d30, common window 2022-01..2026-06
ts = Z["Wa_d30__ts"].astype(np.int64); m26 = ts <= 1782856800  # 2026-06-30 23:00
pnl = Z["Wa_d30__pnl"][m26]; car = Z["Wa_d30__carry"][m26]; carp = Z["Wa_d30__carry_pred"][m26]; ctb = Z["Wa_d30__cost_tierb"][m26]; c352 = Z["Wa_d30__cost_c3.52"][m26]; g = Z["Wa_d30__gross"][m26]
steps = {"A_pnl_only": pnl, "B_minus_pred_carry": pnl - carp, "C_minus_pred_carry_minus_tierb_cost(=WS caliber on my returns)": pnl - carp - ctb, "D_minus_realized_carry_minus_tierb": pnl - car - ctb,
         "E_minus_realized_carry_minus_c3.52(=WA main)": pnl - car - c352, "F_minus_pred_carry_minus_c3.52": pnl - carp - c352}
out["bridge_Wa_d30_actual_gross_2022_06"] = {k: {"mean_bps": round(float(v.mean()), 4), "sharpe_anchor": round(sharpe(v), 3)} for k, v in steps.items()}
out["bridge_Wa_d30_actual_gross_2022_06"]["note"] = "同一权重(W-a d30)、同一 1h 简单收益; 逐步替换 carry(预测×4/iv→实现逐结算)与成本(影子分层b→3.52×换手); WS 已发表 1hsim d30 共同锚夏普 2.218 对应 C 行口径(其收益源为 W2b 立方体, 本行为本装置 1h 网格)"
# ---- (2) phantom tails (names with NaN return) and real-gross restatement, Wb_d30
for nm in ("Wb_d30", "Wb_S0", "Wa_d30"):
    ts = Z[f"{nm}__ts"].astype(np.int64); yr = yr_of(ts); gross = Z[f"{nm}__gross"]; unc = Z[f"{nm}__unc_ret"]; net = Z[f"{nm}__net"]; uncc = Z[f"{nm}__unc_carry"]
    real = np.maximum(gross - unc, 1e-9); m26 = ts <= 1782856800
    g2 = 2 * net / np.maximum(gross, 1e-9); g2r = 2 * net / real
    out[f"phantom_{nm}"] = {"phantom_gross_share_mean": round(float((unc / np.maximum(gross, 1e-9)).mean()), 4), "by_year": {int(y): round(float((unc / np.maximum(gross, 1e-9))[yr == y].mean()), 4) for y in sorted(set(yr.tolist()))},
                            "unc_carry_share_by_year": {int(y): round(float((uncc / np.maximum(gross, 1e-9))[yr == y].mean()), 4) for y in sorted(set(yr.tolist()))},
                            "net_g2_mean_2022_06": round(float(g2[m26].mean()), 4), "net_g2_realgross_mean_2022_06": round(float(g2r[m26].mean()), 4), "sharpe_g2_2022_06": round(sharpe(g2[m26]), 3), "sharpe_g2_realgross_2022_06": round(sharpe(g2r[m26]), 3),
                            "gross_mean": round(float(gross.mean()), 4), "real_gross_mean": round(float(real.mean()), 4)}
# ---- (3) shadow decomposition (computed in-session; numbers from the diagnostic run)
out["shadow_decomposition_27_anchors"] = {"out_of_universe_frozen_tails": {"n_names": 296, "gross": 0.250, "gross_share_of_1.38": round(0.25 / 1.38, 3), "shadow_scores_them_as": 0.0, "my_pnl_bps_per_anchor_mean": 2.23, "sd": 4.11, "sum_27": 60.3},
                                           "in_universe_450": {"gross": 1.130, "non_member_tail_gross": 0.081, "mine_1hcc_minus_shadow_sum5m_mean": -0.366, "sd": 1.714, "max_abs": 5.42},
                                           "note": "影子 rolling 缓存只含 450 名; 权重文件含 746 名(其余 296 名 = bundle H 引导带入、带冻结、无数据 ⇒ 目标 0 且 |0.1·H|<2.5e-4 永不交易、影子记 0 盈亏); 本装置用 fapi 1h 重算其真实盈亏"}

# ---- (4) stop-layer delta by sub-span (Wb d30 - Wb S0, net@2), paired block bootstrap
def boot_delta(x, y, Lb=42, reps=2000, seed=7):
    rng = np.random.RandomState(seed); n = min(len(x), len(y)); nb = n // Lb; d = []
    for _ in range(reps):
        idx = rng.randint(0, nb, nb); sel = (idx[:, None] * Lb + np.arange(Lb)[None, :]).ravel(); d.append(sharpe(x[sel]) - sharpe(y[sel]))
    d = np.array(d); return {"mean": round(float(d.mean()), 3), "CI95": [round(float(np.percentile(d, 2.5)), 3), round(float(np.percentile(d, 97.5)), 3)]}
tsd = Z["Wb_d30__ts"].astype(np.int64); tss = Z["Wb_S0__ts"].astype(np.int64); assert np.array_equal(tsd, tss)
yr = yr_of(tsd); xd = Z["Wb_d30__net_g2"]; xs = Z["Wb_S0__net_g2"]
out["stop_delta_subspans_Wb"] = {"2022-23": boot_delta(xd[yr <= 2023], xs[yr <= 2023]), "2024-26": boot_delta(xd[yr >= 2024], xs[yr >= 2024]),
                                 "by_year_sharpe_d30_vs_S0": {int(y): [round(sharpe(xd[yr == y]), 3), round(sharpe(xs[yr == y]), 3)] for y in sorted(set(yr.tolist()))}}
# ---- (5) wide vs inrole delta by sub-span 2022-23
ti = Z["inrole_S1__ts"].astype(np.int64); xi = Z["inrole_S1__net_g2"]; cm = np.intersect1d(tsd, ti); a = xd[np.searchsorted(tsd, cm)]; b = xi[np.searchsorted(ti, cm)]; yc = yr_of(cm)
out["wide_minus_inrole_subspans"] = {"2022-23": boot_delta(a[yc <= 2023], b[yc <= 2023]), "2024-26": boot_delta(a[yc >= 2024], b[yc >= 2024]), "sharpe_wide_22_23": round(sharpe(a[yc <= 2023]), 3), "sharpe_inrole_22_23": round(sharpe(b[yc <= 2023]), 3)}

json.dump(out, open(f"{RES}/wide_full_caliber_audit_2026-08-22.json", "w"), indent=1, ensure_ascii=False, default=float)
print(json.dumps({k: out[k] for k in out if k.startswith("bridge") or k.startswith("phantom") or k.startswith("stop_delta") or k.startswith("wide_minus")}, indent=1, ensure_ascii=False))
print("merged ->", f"{RES}/wide_full_caliber_audit_2026-08-22.json")
