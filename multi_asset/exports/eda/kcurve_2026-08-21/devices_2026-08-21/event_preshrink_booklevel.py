"""§4.4 二审 · FOMC 16Z 锚事件前预缩 —— 书级装置 @jpline(2026-08-21, Session 6737834a-P2)
=========================================================================================
同构来源: probe_artifacts/w2_live_replay.py(cond_stop_tail.py 逐字同构, 实盘 legs.compose_book / apply_harvest_ema 原样 import,
  W king.595/s2.202/fund.202, RB α.5 λ1, EMA α0.05, 带 b0.002, S1 = 在役逐名止损 −25%×2 锚冷却 42)。**不改在役逻辑**;
  唯一改动 = 在事件锚把【最终下单权重】(EMA+带+止损之后)×m, 下一锚按实盘函数自然恢复(EMA 状态只依赖原始目标, 不受持仓影响;
  带 b0.002 决定哪些名字加回 —— 小权重名可能留在 m× 直到目标漂出带), 换手成本按实际 |Δw| 计(减仓 + 加回都在里面), 不另加回。
事件集: FOMC 决议前最近 1 锚 = 16:00Z 锚(36 次, 2022-01-26 → 2026-06-17; 决议 14:00 ET = 18Z 夏令/19Z 冬令, 落在 16Z 锚持仓窗 16→20Z 内),
  与一审 event_preshrink.py 同一集合(时间戳列表 EVENT_TS 内嵌并断言一致; 来源 docs/macro_event_calendar.md SHA 0d570cca…6bde)。
  前视: 预缩决定在 16:00Z 执行, 只用日历(决议日期提前数月公布), 不用 16Z 之后任何数据 ⇒ 无前视。
口径(同一审): net_pg = (pnl − trn×C − carry)/S0_gross × 2 = bps of NAV @gross2, C=4.137(主) / 3.52(T1 实测, 敏感); 年化 √(6×365)。
★ 冻结判据(跑前写定; 主臂 m=0.75, C=4.137, 全样本 9821 锚):
  E1 净额均值 ≥ 基线;  E2 事件锚(36 个 16Z 锚)方差 ↓ ≥20%;  E3 夏普 ≥ 基线 +0.03;
  E4 换手增量成本 Δcost = Σ(trn'−trn)×C(主口径) 不得吃掉 >1/3 的税前增益: Δcost ≤ 1/3 × (Δnet + Δcost)。
  全过 ⇒ 二审通过(仍需用户裁定 + 预注册才可上线); 任一不过 ⇒ 判负。
  纸面 vs 书级: |Δmean_book − Δmean_paper(+0.0522)| / 0.0522 > 30% ⇒ 纸面数作废(一审文档已声明)。
敏感: m=0.5 / 0.9; C=3.52; 探索臂 reduce_only(事件锚只许减不许加, §A 留档形态, 不在判据内);
  ★ restore 变体(run3 追加): 下一锚【强制加回】(带只绕过一次, 换手照常计费) —— 分离"自然恢复"形态里小权重名卡在 m× 的带再播种拖累。
通道分解(红队): 止损的成本均价逻辑(减仓保均价、加回按现价摊)使"减 25% 再加回"刷新 25% 成本基准 ⇒ 事件后止损触发路径改变(书级副作用, 与
  Binance entryPrice 行为同构, 是真实的但不是事件本身的效应)。⇒ 同时跑 S0(无止损)底座的同一叠加(stop=False), Δ(S0 底座)=纯事件+EMA/带通道,
  Δ(S1)−Δ(S0 底座)≈止损稀释通道; 并报 Δ 的落点(事件锚/下 1 锚/下 2-6 锚/其余)与触发次数变化。随机安慰剂两底座都跑(安慰剂自动含止损稀释通道)。
安慰剂: 日历平移 ±1/±7 天(整书重放 4 次); 随机 36 个非事件日 16Z 锚 × B=2000(整书重放, fork 并行), 报实际 Δ 的分位。
事件自助: 以事件为界切块(36 块 + 首段), 重采块拼接, ΔSharpe/Δmean CI95。
输入: probe_artifacts/king_pred_newgen.npz, s2_pred_newgen.npz, net_S0.npy/net_S1.npy/net_S1_ts.npy(复现收据), pod_backup_2026-08-21/wide_panel_4h_hist_v2.npz(仅 carry)。
输出: probe_artifacts/event_preshrink_booklevel.npz(各臂逐锚序列) + event_preshrink_booklevel_server.json(全部读数)。只读数据, 不碰实盘仓。
"""
import sys, json, time, os, multiprocessing as mp
import numpy as np
PD = "/mnt/storage/private/work_hsy/probe_artifacts"; sys.path.insert(0, PD)
MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
sys.path.insert(0, MA); sys.path.insert(0, MA + "/engine/live"); sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset")
sys.path.insert(0, PD)
import legs as LG
import engine.replay_fullhist as RF
B_DIR = "/mnt/storage/private/work_hsy/pod_backup_2026-08-21"
W = {"king": .5952380952380952, "s2": .20238095238095238, "funding": .20238095238095238, "size": 0.}
RB = {"alpha": .5, "lambda": 1.}; C1 = 4.137; C_T1 = 3.52; BW = 0.002; COOL = 42; ANN = np.sqrt(6 * 365); G = 2.0
N_PLACEBO = int(os.environ.get("N_PLACEBO", "2000")); N_WORKERS = int(os.environ.get("N_WORKERS", "24"))
EVENT_TS = [1643212800, 1647446400, 1651680000, 1655308800, 1658937600, 1663776000, 1667404800, 1671033600, 1675267200, 1679500800, 1683129600, 1686758400,
            1690387200, 1695225600, 1698854400, 1702483200, 1706716800, 1710950400, 1714579200, 1718208000, 1722441600, 1726675200, 1730995200, 1734537600,
            1738166400, 1742400000, 1746633600, 1750262400, 1753891200, 1758124800, 1761753600, 1765382400, 1769616000, 1773849600, 1777478400, 1781712000]
FROZEN = {"main_arm_m": 0.75, "cost_main": C1, "cost_sens": C_T1, "E1": "mean >= base", "E2": "event-anchor var reduction >= 0.20", "E3": "d_sharpe >= 0.03",
          "E4": "d_cost_turnover <= 1/3 * (d_net + d_cost_turnover)", "paper_d_mean_ref": 0.0522, "paper_void_if_rel_diff_gt": 0.30, "arms_m": [0.75, 0.5, 0.9],
          "caliber": "(pnl - trn*C - carry)/S0_gross*2, ann sqrt(6*365)", "shrink_point": "final order weights after EMA+band+stop at the event anchor; next anchor recovers via live functions"}
t0 = time.time()
src = RF.get_src(None, f"{PD}/king_pred_newgen.npz", f"{PD}/s2_pred_newgen.npz")
a, yr = RF._all_anchors(src); N = src.N; n = len(a)
FI, RVI = src.fund_idx, src.ch.index("rvol_24h"); SYMS = [str(s) for s in src.symbols]
ts_all = np.asarray(src.ts)
tss = ts_all // 1000 if (ts_all[1] - ts_all[0]) >= 3600 * 1000 else ts_all
ats = np.array([int(tss[int(t)]) for t in a], dtype=np.int64)
ref_ts = np.load(f"{PD}/net_S1_ts.npy")[:, 0].astype(np.int64)
assert np.array_equal(ref_ts, ats), "anchor ts mismatch vs net_S1_ts.npy"
# ---- event set (must be identical to 一审) ----
pos_ev = np.searchsorted(ats, np.array(EVENT_TS, dtype=np.int64))
assert all(ats[p] == e for p, e in zip(pos_ev, EVENT_TS)), "event anchors not found in anchor grid"
assert all((e % 86400) // 3600 == 16 for e in EVENT_TS), "event anchors must be 16Z"
EV_IDX = np.array(sorted(pos_ev.tolist())); n_ev = len(EV_IDX)
hour = ((ats % 86400) // 3600).astype(int)
ev_day = np.zeros(n, bool)
for p in EV_IDX:
    d0 = (ats[p] // 86400) * 86400; ev_day |= (ats >= d0) & (ats < d0 + 86400)
# ---- carry map from wide hist v2 panel (same as W2) ----
PW = np.load(f"{B_DIR}/wide_panel_4h_hist_v2.npz", allow_pickle=True)
wsym = [str(s) for s in PW["symbols"]]; widx = {s: i for i, s in enumerate(wsym)}
pw_row = {int(t): j for j, t in enumerate(PW["ts"].astype(np.int64))}
FN = PW["f_fund_now"]; IV = PW["f_fund_iv"]
map_live = np.array([widx.get(s, -1) for s in SYMS]); mapped = map_live >= 0
CARRY_FN = np.zeros((n, N)); CARRY_IV = np.full((n, N), 8.0); CARRY_COV = np.zeros((n, N), bool); CARRY_HAS = np.zeros(n, bool)
for i in range(n):
    j = pw_row.get(int(ats[i]))
    if j is None: continue
    CARRY_HAS[i] = True
    fnv = FN[j, map_live[mapped]]; ivv = IV[j, map_live[mapped]]; fin = np.isfinite(fnv)
    CARRY_FN[i, mapped] = np.where(fin, fnv, 0.0); CARRY_COV[i, mapped] = fin
    CARRY_IV[i, mapped] = np.where(np.isfinite(ivv) & (ivv > 0), ivv, 8.0)
print("live syms mapped to wide panel:", int(mapped.sum()), "/", N, "| events", n_ev, "| carry rows", int(CARRY_HAS.sum()), flush=True)
# ---- precompute targets (full book only) ----
TGT, MSK, RET = [], [], []
held = {"k": np.full(N, np.nan), "s": np.full(N, np.nan), "f": np.full(N, np.nan)}
for i, t in enumerate(a):
    ti = int(t); m = np.asarray(src.tradeable(ti))
    if m.dtype == bool: m = np.where(m)[0]
    if i == 0 or ti % 8 == 0:
        v = np.full(N, np.nan); v[m] = src.king[ti, m]; held["k"] = v
    if i == 0 or ti % 24 == 0:
        v = np.full(N, np.nan); v[m] = src.s2[ti, m]; held["s"] = v
    if i == 0 or ti % 8 == 0:
        v = np.full(N, np.nan); v[m] = src.CH[ti, m, FI]; held["f"] = v
    rv = src.CH[ti, m, RVI].astype(float)
    r = LG.compose_book(held["k"][m], held["s"][m], held["f"][m], np.ones(len(m)), weights=W, rvol=rv, risk_budget=RB)
    w = np.full(N, 0.0); w[m] = np.asarray(r["target_w"], float)
    TGT.append(w); MSK.append(m); RET.append(src.Y4[ti, m].astype(float))
    if i % 2000 == 0: print("precompute", i, "/", n, round(time.time() - t0, 1), "s", flush=True)
MSK_SET = [set(m.tolist()) for m in MSK]
NOT_M = [np.array([j for j in range(N) if j not in MSK_SET[i]], dtype=int) for i in range(n)]


def run(stop, shrink=None, mfac=1.0, reduce_only=False, tag="", restore=False):
    """W2 run() 逐字同构 + 事件锚钩子. shrink: set of anchor indices; at those anchors final w ×= mfac
    (reduce_only=True: instead, names whose |w| would increase vs prev are held at prev; no scaling).
    restore=True: at the anchor right after a shrunk anchor, ALL names are traded to target (band bypassed once) =
    '强制加回' variant — isolates the band-reseeding drag (names stuck at m× until their target drifts out of the band)."""
    shrink = shrink or set()
    state = None; prev = np.zeros(N); Pi = np.ones(N); sh = np.zeros(N); cb = np.zeros(N)
    cnt = np.zeros(N, int); su = np.full(N, -1)
    pnl = np.zeros(n); trn = np.zeros(n); gross = np.zeros(n); carry = np.zeros(n); unc = np.zeros(n); fires = np.zeros(n, int); nheld = np.zeros(n, int)
    for i in range(n):
        m = MSK[i]; syms = [SYMS[j] for j in m]
        out = LG.apply_harvest_ema(TGT[i][m], syms, state, 0.05); state = out["state"]
        tgt = np.asarray(out["target_w"], float)
        if stop:
            bs = set(np.where(su > i)[0].tolist())
            if bs:
                for k2, j in enumerate(m):
                    if j in bs: tgt[k2] = 0.0
        w = prev.copy(); w[NOT_M[i]] = 0.0
        d = tgt - w[m]; T = np.abs(d) > BW
        if restore and (i - 1) in shrink: T = np.ones(len(m), bool)   # forced full add-back (turnover charged as usual)
        wm = w[m].copy(); wm[T] = tgt[T]
        if T.any(): wm[T] -= wm.sum() / T.sum()
        w[m] = wm
        if i in shrink:                               # ★ event hook on the FINAL order weights
            if reduce_only:
                inc = np.abs(w) > np.abs(prev) + 1e-15; w = np.where(inc, prev, w)
            else:
                w = w * mfac
        y = RET[i]; ok = np.isfinite(y); idx = m[ok]
        c = np.zeros(N); c[idx] = w[m][ok] * y[ok] * 1e4
        pnl[i] = c.sum(); trn[i] = float(np.abs(w - prev).sum()); gross[i] = float(np.abs(w).sum()); nheld[i] = int((np.abs(w) > 1e-12).sum())
        if CARRY_HAS[i]:
            carry[i] = float((w * CARRY_FN[i] * (4.0 / CARRY_IV[i])).sum() * 1e4); unc[i] = float(np.abs(w[~CARRY_COV[i]]).sum())
        else:
            carry[i] = np.nan; unc[i] = gross[i]
        nsh = np.where(Pi > 1e-12, w / Pi, 0.0)
        same = np.sign(nsh) == np.sign(sh); add = same & (np.abs(nsh) > np.abs(sh))
        red = same & (~add) & (np.abs(nsh) > 1e-12); new = (~same) | (np.abs(sh) < 1e-12)
        cb = np.where(add, cb + (nsh - sh) * Pi, cb)
        with np.errstate(all='ignore'):
            ratio = np.where(np.abs(sh) > 1e-12, nsh / np.where(np.abs(sh) > 1e-12, sh, 1.0), 0.0)
        cb = np.where(red, cb * ratio, cb); cb = np.where(new, nsh * Pi, cb); cb = np.where(np.abs(nsh) < 1e-12, 0.0, cb)
        sh = nsh
        with np.errstate(all='ignore'):
            avg = np.where(np.abs(sh) > 1e-12, cb / sh, np.nan)
            dep = np.where(np.isfinite(avg) & (Pi > 0), np.sign(sh) * (1.0 - avg / Pi), 0.0)
        if stop:
            thr = np.full(N, -0.25)
            cand = (np.abs(sh) > 1e-12) & (dep <= thr) & (su <= i)
            cnt = np.where(cand, cnt + 1, 0)
            fire = cnt >= 2
            if fire.any(): su[fire] = i + COOL; cnt[fire] = 0; fires[i] = int(fire.sum())
        prev = w; upd = np.zeros(N); upd[idx] = y[ok]; Pi = Pi * (1.0 + upd)
    return dict(pnl=pnl, trn=trn, gross=gross, carry=carry, unc=unc, fires=fires, nheld=nheld)


def sharpe(x):
    s = x.std(ddof=1); return float(x.mean() / s * ANN) if s > 0 else float("nan")


def net_pg(R, C, g0):
    return (R["pnl"] - R["trn"] * C - np.nan_to_num(R["carry"])) / g0 * G


# ---- baselines + receipts ----
R0 = run(False, tag="S0"); R1 = run(True, tag="S1")
rec = {}
for k, R, ref in (("S0", R0, "net_S0.npy"), ("S1", R1, "net_S1.npy")):
    d = float(np.max(np.abs(np.load(f"{PD}/{ref}") - (R["pnl"] - R["trn"] * C1))))
    rec[k] = {"maxabs_diff_vs_probe_artifacts_net": d, "mean": float((R["pnl"] - R["trn"] * C1).mean()), "fires": int(R["fires"].sum())}
    print("RECEIPT", k, rec[k], flush=True)
assert rec["S0"]["maxabs_diff_vs_probe_artifacts_net"] < 1e-9 and rec["S1"]["maxabs_diff_vs_probe_artifacts_net"] < 1e-9, "baseline replay does not reproduce net_S0/net_S1"
g0 = R0["gross"]; base = {C: net_pg(R1, C, g0) for C in (C1, C_T1)}; base0 = {C: net_pg(R0, C, g0) for C in (C1, C_T1)}
print("BASE S1+carry pg @4.137: mean %.4f sharpe %.4f | @3.52: mean %.4f sharpe %.4f | %.1fs" % (base[C1].mean(), sharpe(base[C1]), base[C_T1].mean(), sharpe(base[C_T1]), time.time() - t0), flush=True)
EVSET = set(EV_IDX.tolist())


def summarize(R, label, ev_idx=EV_IDX, full=True, Rb=None, bases=None):
    Rb = R1 if Rb is None else Rb; bases = base if bases is None else bases
    out = {"label": label, "fires": int(R["fires"].sum()), "fires_base": int(Rb["fires"].sum())}
    for C in (C1, C_T1):
        x = net_pg(R, C, g0); b = bases[C]
        dcost = float(((R["trn"] - Rb["trn"]) * C / g0 * G).sum()); dnet = float((x - b).sum()); dpnl = float(((R["pnl"] - Rb["pnl"]) / g0 * G).sum()); dcarry = float(((np.nan_to_num(R["carry"]) - np.nan_to_num(Rb["carry"])) / g0 * G).sum())
        s = {"mean": float(x.mean()), "sharpe": sharpe(x), "d_mean": float(x.mean() - b.mean()), "d_mean_per_year_bps": dnet / (n / 2190), "d_sharpe": sharpe(x) - sharpe(b),
             "event_var_base": float(b[ev_idx].var(ddof=1)), "event_var_alt": float(x[ev_idx].var(ddof=1)), "event_var_reduction": float(1 - x[ev_idx].var(ddof=1) / b[ev_idx].var(ddof=1)),
             "event_mean_base": float(b[ev_idx].mean()), "event_mean_alt": float(x[ev_idx].mean()),
             "sum_d_net_bps": dnet, "sum_d_pnl_bps": dpnl, "sum_d_carry_bps": -dcarry, "sum_d_cost_turnover_bps": dcost, "cost_share_of_pretax_gain": float(dcost / (dnet + dcost)) if (dnet + dcost) != 0 else None,
             "d_turnover_units_total": float((R["trn"] - Rb["trn"]).sum()), "d_turnover_units_per_event": float((R["trn"] - Rb["trn"]).sum() / max(1, len(ev_idx))),
             "event_anchor_turnover_base": float(Rb["trn"][ev_idx].mean()), "event_anchor_turnover_alt": float(R["trn"][ev_idx].mean()),
             "next_anchor_turnover_base": float(Rb["trn"][np.minimum(ev_idx + 1, n - 1)].mean()), "next_anchor_turnover_alt": float(R["trn"][np.minimum(ev_idx + 1, n - 1)].mean()),
             "gross_event_alt_over_base": float(R["gross"][ev_idx].mean() / Rb["gross"][ev_idx].mean()), "gross_next_alt_over_base": float(R["gross"][np.minimum(ev_idx + 1, n - 1)].mean() / Rb["gross"][np.minimum(ev_idx + 1, n - 1)].mean()),
             "gross_next2_alt_over_base": float(R["gross"][np.minimum(ev_idx + 2, n - 1)].mean() / Rb["gross"][np.minimum(ev_idx + 2, n - 1)].mean()),
             "d_fires_total": int(R["fires"].sum() - Rb["fires"].sum())}
        if full:
            s["by_year"] = {int(y_): {"d_mean": float(x[yr == y_].mean() - b[yr == y_].mean()), "base_sharpe": sharpe(b[yr == y_]), "alt_sharpe": sharpe(x[yr == y_])} for y_ in sorted(set(yr.tolist()))}
            # where does the Δ land: event anchor / next 1 / next 2-6 / rest
            dd = x - b; at_ev = float(dd[ev_idx].sum()); at_n1 = float(dd[np.minimum(ev_idx + 1, n - 1)].sum())
            n26 = np.unique(np.concatenate([np.minimum(ev_idx + k, n - 1) for k in range(2, 7)])); at_n26 = float(dd[n26].sum())
            s["d_net_location_bps"] = {"event_anchor": at_ev, "next1": at_n1, "next2_6": at_n26, "rest": dnet - at_ev - at_n1 - at_n26}
            e1 = s["d_mean"] >= 0; e2 = s["event_var_reduction"] >= 0.20; e3 = s["d_sharpe"] >= 0.03; e4 = (s["cost_share_of_pretax_gain"] is not None) and (s["cost_share_of_pretax_gain"] <= 1 / 3)
            s["criteria"] = {"E1_mean": bool(e1), "E2_event_var": bool(e2), "E3_sharpe": bool(e3), "E4_cost_share": bool(e4), "PASS": bool(e1 and e2 and e3 and e4)}
        out[f"C{C}"] = s
    return out


# ---- arms ----
ARMS = {}; SER = {"S0": R0, "S1": R1}
for mf in (0.75, 0.5, 0.9):
    R = run(True, EVSET, mf, tag=f"m{mf}"); SER[f"fomc_m{mf}"] = R; ARMS[f"fomc_m{mf}"] = summarize(R, f"FOMC pre1 ×{mf}")
    print("ARM", f"m{mf}", json.dumps({k: ARMS[f"fomc_m{mf}"]["C4.137"][k] for k in ("d_mean", "d_sharpe", "event_var_reduction", "sum_d_net_bps", "sum_d_cost_turnover_bps", "cost_share_of_pretax_gain", "criteria")}), round(time.time() - t0, 1), "s", flush=True)
for mf in (0.75, 0.5, 0.9):   # same overlay on the NO-STOP base (stop=False): pure event + EMA/band channel, no stop-dilution channel
    R = run(False, EVSET, mf, tag=f"S0_m{mf}"); SER[f"fomc_S0base_m{mf}"] = R; ARMS[f"fomc_S0base_m{mf}"] = summarize(R, f"FOMC pre1 ×{mf} on S0 base (no stop)", Rb=R0, bases=base0)
    print("ARM S0base", f"m{mf}", json.dumps({k: ARMS[f"fomc_S0base_m{mf}"]["C4.137"][k] for k in ("d_mean", "d_sharpe", "event_var_reduction", "sum_d_net_bps", "sum_d_cost_turnover_bps", "d_net_location_bps")}), flush=True)
for mf in (0.75, 0.5):           # forced-restore variants (band bypassed once at the add-back anchor)
    R = run(True, EVSET, mf, tag=f"m{mf}_restore", restore=True); SER[f"fomc_m{mf}_restore"] = R; ARMS[f"fomc_m{mf}_restore"] = summarize(R, f"FOMC pre1 ×{mf} + forced restore")
    print("ARM restore", f"m{mf}", json.dumps({k: ARMS[f"fomc_m{mf}_restore"]["C4.137"][k] for k in ("d_mean", "d_sharpe", "event_var_reduction", "sum_d_net_bps", "sum_d_cost_turnover_bps", "cost_share_of_pretax_gain", "d_net_location_bps", "criteria")}), flush=True)
    R = run(False, EVSET, mf, tag=f"S0_m{mf}_restore", restore=True); SER[f"fomc_S0base_m{mf}_restore"] = R; ARMS[f"fomc_S0base_m{mf}_restore"] = summarize(R, f"FOMC pre1 ×{mf} + forced restore on S0 base", Rb=R0, bases=base0)
    print("ARM S0base restore", f"m{mf}", json.dumps({k: ARMS[f"fomc_S0base_m{mf}_restore"]["C4.137"][k] for k in ("d_mean", "d_sharpe", "event_var_reduction", "sum_d_net_bps", "sum_d_cost_turnover_bps", "d_net_location_bps")}), flush=True)
R = run(True, EVSET, 1.0, reduce_only=True, tag="reduce_only"); SER["fomc_reduce_only"] = R; ARMS["fomc_reduce_only"] = summarize(R, "FOMC pre1 reduce-only (exploratory)")
print("ARM reduce_only", json.dumps({k: ARMS["fomc_reduce_only"]["C4.137"][k] for k in ("d_mean", "d_sharpe", "event_var_reduction", "sum_d_cost_turnover_bps")}), flush=True)
# ---- shifted-calendar placebos (main arm) ----
SHIFT = {}
for days in (-7, -1, 1, 7):
    idx = np.searchsorted(ats, np.array(EVENT_TS, dtype=np.int64) + days * 86400); idx = idx[(idx >= 2) & (idx < n)]
    R = run(True, set(idx.tolist()), 0.75, tag=f"shift{days}"); SER[f"shift_{days:+d}d"] = R
    SHIFT[f"shift_{days:+d}d"] = summarize(R, f"shift {days:+d}d", ev_idx=idx, full=False); SHIFT[f"shift_{days:+d}d"]["n"] = int(len(idx))
    R = run(False, set(idx.tolist()), 0.75, tag=f"shift{days}_S0"); SER[f"shift_{days:+d}d_S0base"] = R
    SHIFT[f"shift_{days:+d}d_S0base"] = summarize(R, f"shift {days:+d}d on S0 base", ev_idx=idx, full=False, Rb=R0, bases=base0)
    R = run(True, set(idx.tolist()), 0.75, tag=f"shift{days}_restore", restore=True); SER[f"shift_{days:+d}d_restore"] = R
    SHIFT[f"shift_{days:+d}d_restore"] = summarize(R, f"shift {days:+d}d + restore", ev_idx=idx, full=False)
    R = run(False, set(idx.tolist()), 0.75, tag=f"shift{days}_S0_restore", restore=True); SER[f"shift_{days:+d}d_S0base_restore"] = R
    SHIFT[f"shift_{days:+d}d_S0base_restore"] = summarize(R, f"shift {days:+d}d + restore on S0 base", ev_idx=idx, full=False, Rb=R0, bases=base0)
    print("SHIFT", days, {C: (round(SHIFT[f'shift_{days:+d}d'][f'C{C}']['d_mean'], 4), round(SHIFT[f'shift_{days:+d}d'][f'C{C}']['d_sharpe'], 4)) for C in (C1, C_T1)},
          "| S0base", round(SHIFT[f'shift_{days:+d}d_S0base']['C4.137']['d_mean'], 4), round(SHIFT[f'shift_{days:+d}d_S0base']['C4.137']['d_sharpe'], 4), flush=True)
# ---- event-delimited block bootstrap (main arm) ----
xm = net_pg(SER["fomc_m0.75"], C1, g0); bb = base[C1]
bounds = [0] + EV_IDX.tolist() + [n]; blocks = [(bounds[i], bounds[i + 1]) for i in range(len(bounds) - 1)]
rng = np.random.RandomState(31); BB = 4000; dS = np.empty(BB); dM = np.empty(BB)
for b_ in range(BB):
    pick = rng.randint(1, len(blocks), len(blocks) - 1); segs = [blocks[0]] + [blocks[p] for p in pick]
    xb = np.concatenate([xm[s:e] for s, e in segs]); bbb = np.concatenate([bb[s:e] for s, e in segs])
    dS[b_] = sharpe(xb) - sharpe(bbb); dM[b_] = xb.mean() - bbb.mean()
BOOT = {"B": BB, "d_sharpe_ci95": [float(np.percentile(dS, 2.5)), float(np.percentile(dS, 97.5))], "P_d_sharpe_ge_0.03": float((dS >= 0.03).mean()), "P_d_sharpe_gt_0": float((dS > 0).mean()),
        "d_mean_ci95": [float(np.percentile(dM, 2.5)), float(np.percentile(dM, 97.5))], "P_d_mean_gt_0": float((dM > 0).mean())}
xm0 = net_pg(SER["fomc_S0base_m0.75"], C1, g0); bb0 = base0[C1]; rng = np.random.RandomState(31); dS0 = np.empty(BB); dM0 = np.empty(BB)
for b_ in range(BB):
    pick = rng.randint(1, len(blocks), len(blocks) - 1); segs = [blocks[0]] + [blocks[p] for p in pick]
    xb = np.concatenate([xm0[s:e] for s, e in segs]); bbb = np.concatenate([bb0[s:e] for s, e in segs])
    dS0[b_] = sharpe(xb) - sharpe(bbb); dM0[b_] = xb.mean() - bbb.mean()
BOOT["S0base"] = {"d_sharpe_ci95": [float(np.percentile(dS0, 2.5)), float(np.percentile(dS0, 97.5))], "P_d_sharpe_ge_0.03": float((dS0 >= 0.03).mean()), "d_mean_ci95": [float(np.percentile(dM0, 2.5)), float(np.percentile(dM0, 97.5))], "P_d_mean_gt_0": float((dM0 > 0).mean())}
for key, arm, bser in (("restore", "fomc_m0.75_restore", bb), ("S0base_restore", "fomc_S0base_m0.75_restore", bb0)):
    xr = net_pg(SER[arm], C1, g0); rng = np.random.RandomState(31); dSr = np.empty(BB); dMr = np.empty(BB)
    for b_ in range(BB):
        pick = rng.randint(1, len(blocks), len(blocks) - 1); segs = [blocks[0]] + [blocks[p] for p in pick]
        xb = np.concatenate([xr[s:e] for s, e in segs]); bbb = np.concatenate([bser[s:e] for s, e in segs])
        dSr[b_] = sharpe(xb) - sharpe(bbb); dMr[b_] = xb.mean() - bbb.mean()
    BOOT[key] = {"d_sharpe_ci95": [float(np.percentile(dSr, 2.5)), float(np.percentile(dSr, 97.5))], "P_d_sharpe_ge_0.03": float((dSr >= 0.03).mean()), "d_mean_ci95": [float(np.percentile(dMr, 2.5)), float(np.percentile(dMr, 97.5))], "P_d_mean_gt_0": float((dMr > 0).mean())}
print("BOOT", BOOT, flush=True)
# ---- random-day placebos (full book replay, parallel) ----
CAND = np.where((hour == 16) & (~ev_day) & (np.arange(n) >= 2))[0]


def _placebo(seed):
    r = np.random.RandomState(seed); idx = np.sort(r.choice(CAND, n_ev, replace=False))
    R = run(True, set(idx.tolist()), 0.75)
    s = summarize(R, f"placebo{seed}", ev_idx=idx, full=False)
    R0p = run(False, set(idx.tolist()), 0.75)
    s0 = summarize(R0p, f"placebo{seed}_S0", ev_idx=idx, full=False, Rb=R0, bases=base0)
    Rr = run(True, set(idx.tolist()), 0.75, restore=True); sr = summarize(Rr, f"placebo{seed}_restore", ev_idx=idx, full=False)
    R0r = run(False, set(idx.tolist()), 0.75, restore=True); s0r = summarize(R0r, f"placebo{seed}_S0_restore", ev_idx=idx, full=False, Rb=R0, bases=base0)
    return {"seed": int(seed), "d_mean": s["C4.137"]["d_mean"], "d_sharpe": s["C4.137"]["d_sharpe"], "d_mean_352": s["C3.52"]["d_mean"], "event_mean_base": s["C4.137"]["event_mean_base"],
            "sum_d_cost": s["C4.137"]["sum_d_cost_turnover_bps"], "fires": s["fires"], "d_mean_S0base": s0["C4.137"]["d_mean"], "d_sharpe_S0base": s0["C4.137"]["d_sharpe"],
            "d_mean_restore": sr["C4.137"]["d_mean"], "d_sharpe_restore": sr["C4.137"]["d_sharpe"], "d_mean_S0base_restore": s0r["C4.137"]["d_mean"], "d_sharpe_S0base_restore": s0r["C4.137"]["d_sharpe"]}


PL = []
if N_PLACEBO > 0:
    ctx = mp.get_context("fork")
    with ctx.Pool(N_WORKERS) as pool:
        for k, res in enumerate(pool.imap_unordered(_placebo, range(N_PLACEBO), chunksize=4)):
            PL.append(res)
            if k % 100 == 0: print("placebo", k, "/", N_PLACEBO, round(time.time() - t0, 1), "s", flush=True)
    dm = np.array([p["d_mean"] for p in PL]); ds = np.array([p["d_sharpe"] for p in PL]); act = ARMS["fomc_m0.75"]["C4.137"]
    PLS = {"B": len(PL), "d_mean": {"p5": float(np.percentile(dm, 5)), "p50": float(np.percentile(dm, 50)), "p95": float(np.percentile(dm, 95)), "mean": float(dm.mean())},
           "d_sharpe": {"p5": float(np.percentile(ds, 5)), "p50": float(np.percentile(ds, 50)), "p95": float(np.percentile(ds, 95))},
           "actual_d_mean": act["d_mean"], "pct_rank_actual_d_mean": float((dm < act["d_mean"]).mean()), "actual_d_sharpe": act["d_sharpe"], "pct_rank_actual_d_sharpe": float((ds < act["d_sharpe"]).mean()),
           "frac_placebo_d_mean_positive": float((dm > 0).mean()), "mean_cost_bps": float(np.mean([p["sum_d_cost"] for p in PL]))}
    dm0 = np.array([p["d_mean_S0base"] for p in PL]); ds0 = np.array([p["d_sharpe_S0base"] for p in PL]); act0 = ARMS["fomc_S0base_m0.75"]["C4.137"]
    PLS["S0base"] = {"d_mean": {"p5": float(np.percentile(dm0, 5)), "p50": float(np.percentile(dm0, 50)), "p95": float(np.percentile(dm0, 95)), "mean": float(dm0.mean())},
                     "d_sharpe": {"p5": float(np.percentile(ds0, 5)), "p50": float(np.percentile(ds0, 50)), "p95": float(np.percentile(ds0, 95))},
                     "actual_d_mean": act0["d_mean"], "pct_rank_actual_d_mean": float((dm0 < act0["d_mean"]).mean()), "actual_d_sharpe": act0["d_sharpe"], "pct_rank_actual_d_sharpe": float((ds0 < act0["d_sharpe"]).mean()),
                     "frac_placebo_d_mean_positive": float((dm0 > 0).mean())}
    for key, arm in (("restore", "fomc_m0.75_restore"), ("S0base_restore", "fomc_S0base_m0.75_restore")):
        dmr = np.array([p[f"d_mean_{key}"] for p in PL]); dsr = np.array([p[f"d_sharpe_{key}"] for p in PL]); actr = ARMS[arm]["C4.137"]
        PLS[key] = {"d_mean": {"p5": float(np.percentile(dmr, 5)), "p50": float(np.percentile(dmr, 50)), "p95": float(np.percentile(dmr, 95)), "mean": float(dmr.mean()), "sd": float(dmr.std(ddof=1))},
                    "d_sharpe": {"p5": float(np.percentile(dsr, 5)), "p50": float(np.percentile(dsr, 50)), "p95": float(np.percentile(dsr, 95))},
                    "actual_d_mean": actr["d_mean"], "pct_rank_actual_d_mean": float((dmr < actr["d_mean"]).mean()), "actual_d_sharpe": actr["d_sharpe"], "pct_rank_actual_d_sharpe": float((dsr < actr["d_sharpe"]).mean()),
                    "frac_placebo_d_mean_positive": float((dmr > 0).mean())}
    print("PLACEBO", PLS, flush=True)
else:
    PLS = {"B": 0}
OUT = {"meta": {"created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "session": "6737834a-P2", "host": os.uname().nodename, "python": sys.version.split()[0], "numpy": np.__version__,
                "n_anchors": int(n), "n_events": int(n_ev), "event_ts": EVENT_TS, "frozen": FROZEN, "runtime_s": round(time.time() - t0, 1), "n_placebo": len(PL), "n_workers": N_WORKERS},
       "receipts": rec, "base": {f"C{C}": {"mean": float(base[C].mean()), "sharpe": sharpe(base[C]), "event_mean": float(base[C][EV_IDX].mean()), "event_var": float(base[C][EV_IDX].var(ddof=1))} for C in (C1, C_T1)},
       "base_S0": {f"C{C}": {"mean": float(base0[C].mean()), "sharpe": sharpe(base0[C]), "event_mean": float(base0[C][EV_IDX].mean())} for C in (C1, C_T1)},
       "arms": ARMS, "shifted_placebo": SHIFT, "event_block_bootstrap_main": BOOT, "random_placebo_main": PLS, "placebo_draws": PL}
json.dump(OUT, open(f"{PD}/event_preshrink_booklevel_server.json", "w"), indent=1, ensure_ascii=False)
np.savez_compressed(f"{PD}/event_preshrink_booklevel.npz", ts=ats, yr=yr, ev_idx=EV_IDX,  # S0_gross == S0_gross series below
                    **{f"{k}_{f}": SER[k][f] for k in SER for f in ("pnl", "trn", "gross", "carry", "fires", "nheld")})
print("DONE", round(time.time() - t0, 1), "s", flush=True)
