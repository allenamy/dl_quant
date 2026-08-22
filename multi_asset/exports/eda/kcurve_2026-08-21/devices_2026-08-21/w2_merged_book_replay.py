"""W2b · A 权重级融合走实盘函数管线 @jpline(2026-08-22, Session 6737834a-W2b; DESIGN_optimization_path §3.1 二读)。
用法: python w2_merged_book_replay.py [--arms main|all]   (输出 probe_artifacts/w2b_merged_*.{json,npz}; 再由本机入 git results/)

============================== 冻结判据(先于数字; team-lead 派工原文 + 本装置的读法约定) ==============================
主臂 M0 = 合成目标 0.3×在役单位 gross 目标 + 0.7×宽单位 gross 目标(同名相加, 反向自然抵消) → 实盘函数管线:
          legs.apply_harvest_ema α=0.05(EMA→二次 demean→L1) → 逐名止损(在役条款: 成本均价深度 ≤−25% 连续 2 锚 ⇒ 置零并冷却 42 锚; 出场 FORCED 不受带)
          → 中性免交易带 b=0.002(权重口径, 残差只摊已交易集; 出宇宙名即平) → 成本 3.52 bps×换手(全口径实测) → carry = Σw·fund_now·4/iv(正=付)。
对照 P0(装置内纸面相加) = 0.3×在役书(同管线, 单独)+ 0.7×宽书(其自有管线: α0.1 / 带 2.5e-4 / d30_n2_c42 / 同 3.52 成本)— 同一收益源、同一时钟、同一成本 ⇒ 差值 = 纯管线损耗。
口径: 每单位【目标】gross 净额 × 恒定 G=2.0(在役时钟; 宽自有管线臂的主口径沿用 W2 约定 = 除以无止损孪生臂的持有 gross_total, 并同时报每单位目标 gross); 年化 √(6×365); 共同锚 9821(2022-01-01→2026-06-29)。
判据(冻结): c1 夏普(M0) ≥ 夏普(P0) − 0.10(管线损耗 ≤ 0.10); c2 夏普(M0) ≥ 夏普(在役 L_dev) + 0.15; c3 逐年夏普 M0 ≥ 在役 ≥ 4/5(读法 B; 读法 A "≥两单书较优者" 并报);
          c4 换手(M0, 单位目标 gross, 同 G) ≤ 0.3×换手(L_dev) + 0.7×换手(W_dev_own)。PASS ⇔ c1∧c2∧c3∧c4。
不过时的读法(先声明): 若 M0 不过但【预先声明】的带缩放臂(b ∈ {0.0005, 0.00025}, 其余同 M0)有一臂过 c1–c4 ⇒ 结论 = "需重设计(带按名数缩放)";
          若无一臂过 ⇒ "配置不成立(实盘函数管线下)"。敏感臂(0.5/0.5, 风险平价 0.4/0.6, d30 止损, α0.1, 无止损, 成本 4.137/0.32/分层)只作注记, 不参与判决, 不事后选臂。
统计锁: ΔSharpe 配对块自助(42 锚 ×2000)CI; 触线概率(恒定 gross 2.0, 块 180×2000, 起点 −25% 与峰值回撤 −25%, 回放/折让 0.55)。
============================================================================================================

输入 SHA256(`--pin` 一次写入 probe_artifacts/w2b_input_pins.json, 其后每次运行逐文件核验, 不符即停; 副本入 git results/w2b_input_pins.json):
  见 INPUTS 列表(king/s2 预测 npz, 实盘 legs.py 副本, net_S0/S1 收据, 宽 meta/v2 面板/slow OOS 预测/nets_histv2 收据, W2 一审两序列, 收益立方体 w2b_ret_cube.npz);
  立方体自身的 zip 清单 SHA 记于 cube_meta。
复现收据(脚本内断言): L_native 臂 net 与 probe_artifacts/net_S1.npy 逐元素相等(maxabs<1e-6); W_native 臂 net 与 pod_backup/nets_histv2_-30_2_42.npy 相等(maxabs<1e-6)。
只读数据; 写 probe_artifacts/w2b_*; 不碰 ~/dl_quant_live / share / 交易 API。
"""
import os, sys, json, time, hashlib, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import w2b_common as C
PD, B = C.PD, C.B
PIN_FILE = f"{PD}/w2b_input_pins.json"       # written once by `--pin`, then verified on every run
INPUTS = [f"{PD}/king_pred_newgen.npz", f"{PD}/s2_pred_newgen.npz", f"{PD}/legs.py", f"{PD}/net_S1.npy", f"{PD}/net_S0.npy",
          f"{B}/wide_fea_hist_meta.npz", f"{B}/wide_panel_4h_hist_v2.npz", f"{B}/slow_pred_hist_oos.npy", f"{B}/nets_histv2_-30_2_42.npy", f"{B}/nets_histv2_0_0_0.npy",
          f"{PD}/w2_live_series.npz", f"{PD}/w2_wide_series.npz", f"{PD}/w2b_ret_cube.npz"]
G = 2.0; COST_MAIN = 3.52; COST_SENS = (4.137, 0.32)
ARMS_MODE = "all" if "--arms" not in sys.argv else sys.argv[sys.argv.index("--arms") + 1]
t0 = time.time()
def log(*a): print(*a, round(time.time() - t0, 1), "s", flush=True)
# ---------------------------------------------------------------- pins
if "--pin" in sys.argv:
    json.dump({p: C.sha(p) for p in INPUTS}, open(PIN_FILE, "w"), indent=1); print("pins written", PIN_FILE); sys.exit(0)
pins = json.load(open(PIN_FILE))
for p in INPUTS:
    got = C.sha(p); assert pins[p] == got, f"SHA mismatch {p}: {got} vs pinned {pins[p]}"
log("pins verified", len(INPUTS))
D = C.load_all()
n, NW, yr = D.n, D.NW, D.yr
log("data loaded; anchors", n, "first", time.strftime("%Y-%m-%d %H:%M", time.gmtime(int(D.ts[0]))), "last", time.strftime("%Y-%m-%d %H:%M", time.gmtime(int(D.ts[-1]))))
# ---------------------------------------------------------------- per-anchor inputs in 829-space
TGT_L829 = np.zeros((n, NW), np.float64); TGT_L829[:, D.lmap] = D.TGT_L
Y4_L829 = np.full((n, NW), np.nan, np.float64); Y4_L829[:, D.lmap] = D.Y4_L
UNI_L = [np.sort(D.lmap[m]) for m in D.MSK_L]
UNI_W = [np.sort(np.asarray(u)) for u in D.UNI_W]
UNI_M = [np.union1d(a, b) for a, b in zip(UNI_L, UNI_W)]
def merged_target(wl, ww):
    return (wl * TGT_L829 + ww * D.TGT_W.astype(np.float64))
# ---------------------------------------------------------------- arms (process pool; D inherited by fork)
from multiprocessing import Pool
RUNS = {}; SERIES = {}; META = {}
def add(tag, O, cost_main=COST_MAIN, note=""):
    net = O["pnl"] - O["carry"] - cost_main * O["trn"]
    SERIES[tag] = {k: np.asarray(O[k], float) for k in O if k != "W" and O[k] is not None}
    SERIES[tag]["net"] = net; META[tag] = note; RUNS[tag] = O
    log("ARM", tag, "mean net@1", round(float(net.mean()), 4), "sharpe", round(C.sharpe(net), 3), "trn", round(float(np.nanmean(O["trn"])), 5), "gross", round(float(np.nanmean(O["gross"])), 4))
GRID_W = {"w07": (0.3, 0.7), "w05": (0.5, 0.5), "w06": (0.4, 0.6)}
SPECS = [("L_native", "engine", dict(tgt="L", uni="L", ret="Y4L", alpha=0.05, band=0.002, stop=(-0.25, 2, 42), forced=False, keep=False), "receipt: W2 live config (live Y4 native, cost 4.137, band not forced) — equals net_S1.npy"),
         ("W_native", "wide", dict(ret=None, depth=-0.30, keep=False), "receipt: W2 wide config (meta y4 wide clock, tiered cost) — equals nets_histv2_-30_2_42"),
         ("L_dev", "engine", dict(tgt="L", uni="L", ret="R", alpha=0.05, band=0.002, stop=(-0.25, 2, 42), forced=True, keep=True), "live book, live pipeline, cube returns, forced stop exit"),
         ("L_dev_nostop", "engine", dict(tgt="L", uni="L", ret="R", alpha=0.05, band=0.002, stop=None, forced=True, keep=False), "live book no stop (denominator twin)"),
         ("W_dev_own", "wide", dict(ret="R", depth=-0.30, keep=True), "wide book, own pipeline (α0.1/b2.5e-4/d30), cube returns live clock, cost flat 3.52"),
         ("W_dev_own_nostop", "wide", dict(ret="R", depth=None, keep=False), "wide own pipeline no stop (denominator twin)")]
for b in (0.002, 0.0005, 0.00025):
    SPECS.append((f"W_livefn_b{b}", "engine", dict(tgt="W", uni="W", ret="R", alpha=0.05, band=b, stop=(-0.25, 2, 42), forced=True, keep=False), f"wide book alone through LIVE pipeline, band {b}"))
if ARMS_MODE == "main":
    plan = [("M_w07_b0.002", (0.3, 0.7), 0.05, 0.002, (-0.25, 2, 42)), ("M_w07_b0.0005", (0.3, 0.7), 0.05, 0.0005, (-0.25, 2, 42)), ("M_w07_b0.00025", (0.3, 0.7), 0.05, 0.00025, (-0.25, 2, 42))]
else:
    plan = []
    for wn, ws in GRID_W.items():
        for b in (0.002, 0.0005, 0.00025): plan.append((f"M_{wn}_b{b}", ws, 0.05, b, (-0.25, 2, 42)))
    for b in (0.002, 0.0005):
        plan.append((f"M_w07_b{b}_d30", (0.3, 0.7), 0.05, b, (-0.30, 2, 42)))
        plan.append((f"M_w07_b{b}_a0.1", (0.3, 0.7), 0.1, b, (-0.25, 2, 42)))
        plan.append((f"M_w07_b{b}_nostop", (0.3, 0.7), 0.05, b, None))
for tag, (wl, ww), al, b, st in plan:
    SPECS.append((tag, "engine", dict(tgt=("M", wl, ww), uni="M", ret="R", alpha=al, band=b, stop=st, forced=True, keep=tag in ("M_w07_b0.002", "M_w07_b0.0005", "M_w07_b0.00025")), f"merged target {wl}/{ww}, live pipeline α{al} b{b} stop{st}"))
# ---- diagnostic ladder (declared BEFORE numbers; explanatory only, never a candidate): one pipeline element at a time between the wide book's own pipeline and the live function,
#      plus clock/source decomposition (R_wide = 1h-kline wide clock). Not part of the frozen verdict.
LADDER = [("W_own_Rwide", "wide", dict(ret="RW", depth=-0.30, keep=False, alpha=0.1, band=2.5e-4), "wide own pipeline, 1h-kline returns on WIDE clock (source effect; vs W_native=meta y4)"),
          ("W_own_a0.05", "wide", dict(ret="R", depth=-0.30, keep=False, alpha=0.05, band=2.5e-4), "wide own pipeline with EMA α0.05 (live speed)"),
          ("W_own_b0.002", "wide", dict(ret="R", depth=-0.30, keep=False, alpha=0.1, band=0.002), "wide own pipeline with band 0.002 on EMA increment"),
          ("W_own_stop25", "wide", dict(ret="R", depth=-0.25, keep=False, alpha=0.1, band=2.5e-4), "wide own pipeline with live stop depth −25%"),
          ("W_livefn_b0.002_a0.1", "engine", dict(tgt="W", uni="W", ret="R", alpha=0.1, band=0.002, stop=(-0.25, 2, 42), forced=True, keep=False), "wide through live fn, α0.1"),
          ("W_livefn_b0.002_preEMAstop", "engine", dict(tgt="W", uni="W", ret="R", alpha=0.05, band=0.002, stop=(-0.25, 2, 42), forced=True, keep=False, pre=True), "wide through live fn, stop pre-EMA slow exit (wide semantics)"),
          ("W_livefn_b0.002_decay", "engine", dict(tgt="W", uni="W", ret="R", alpha=0.05, band=0.002, stop=(-0.25, 2, 42), forced=True, keep=False, leav=True), "wide through live fn, leavers decay via EMA (wide semantics)"),
          ("W_livefn_b0.002_pre_decay_a0.1", "engine", dict(tgt="W", uni="W", ret="R", alpha=0.1, band=0.002, stop=(-0.25, 2, 42), forced=True, keep=False, pre=True, leav=True), "wide through live fn, α0.1 + pre-EMA stop + leaver decay"),
          ("M_w07_b0.002_preEMAstop", "engine", dict(tgt=("M", 0.3, 0.7), uni="M", ret="R", alpha=0.05, band=0.002, stop=(-0.25, 2, 42), forced=True, keep=False, pre=True), "merged, stop pre-EMA slow exit"),
          ("M_w07_b0.002_decay", "engine", dict(tgt=("M", 0.3, 0.7), uni="M", ret="R", alpha=0.05, band=0.002, stop=(-0.25, 2, 42), forced=True, keep=False, leav=True), "merged, leavers decay"),
          ("M_w07_b0.002_pre_decay", "engine", dict(tgt=("M", 0.3, 0.7), uni="M", ret="R", alpha=0.05, band=0.002, stop=(-0.25, 2, 42), forced=True, keep=False, pre=True, leav=True), "merged, pre-EMA stop + leaver decay")]
if ARMS_MODE != "main": SPECS += LADDER
def _worker(spec):
    tag, kind, P, note = spec
    if kind == "wide":
        RC = {"R": D.R, "RW": D.R_wide, None: None}[P["ret"]]
        O = C.wide_native(D, RET_common=RC, depth=P["depth"], keep_W=P["keep"], tag=tag, verbose=False, alpha=P.get("alpha", 0.1), band=P.get("band", 2.5e-4))
    else:
        if P["tgt"] == "L": T = TGT_L829
        elif P["tgt"] == "W": T = D.TGT_W
        else: T = merged_target(P["tgt"][1], P["tgt"][2])
        U = {"L": UNI_L, "W": UNI_W, "M": UNI_M}[P["uni"]]; R_ = Y4_L829 if P["ret"] == "Y4L" else D.R
        O = C.engine(D, T, U, R_, alpha=P["alpha"], band=P["band"], stop=P["stop"], forced_exit=P["forced"], keep_W=P["keep"], tag=tag, verbose=False, stop_pre_ema=P.get("pre", False), keep_leavers=P.get("leav", False))
    return tag, O
NPROC = int(os.environ.get("W2B_NPROC", "10"))
with Pool(NPROC) as pool:
    for tag, O in pool.imap_unordered(_worker, SPECS):
        note = [s for s in SPECS if s[0] == tag][0][3]
        if tag == "L_native":
            net_native = O["pnl"] - 4.137 * O["trn"]; ref = np.load(f"{PD}/net_S1.npy"); d_live = float(np.max(np.abs(net_native - ref)))
            log("RECEIPT L_native maxabs vs net_S1.npy =", d_live); add("L_native", O, cost_main=4.137, note=note)
        elif tag == "W_native":
            net_wn = O["pnl"] - O["carry"] - O["cost_tier"]; refw = np.load(f"{B}/nets_histv2_-30_2_42.npy"); wts = refw[:, 0].astype(np.int64); wp = {int(t): k for k, t in enumerate(wts)}
            refn = np.array([refw[wp[int(t)], 1] for t in D.ts]); d_wide = float(np.max(np.abs(net_wn - refn)))
            log("RECEIPT W_native maxabs vs nets_histv2_-30_2_42 =", d_wide)
            SERIES["W_native"] = {k: np.asarray(O[k], float) for k in O if k != "W" and O[k] is not None}; SERIES["W_native"]["net"] = net_wn; META["W_native"] = note
        else:
            add(tag, O, note=note)
assert d_live < 1e-6, f"live receipt failed {d_live}"; assert d_wide < 1e-6, f"wide receipt failed {d_wide}"
# ---- exchange-netting variant: two books run separately on one account (positions net at the venue)
WL = RUNS["L_dev"]["W"]; WW = RUNS["W_dev_own"]["W"]
gL0 = SERIES["L_dev_nostop"]["gross"]; gW0 = SERIES["W_dev_own_nostop"]["gross"]
for wn, (wl, ww) in GRID_W.items():
    # W2-convention per-unit-held-gross scaling for the wide native positions (deployment normalisation layer, §J-bis), live positions ≈ unit gross
    pos = np.zeros((n, NW), np.float32)
    for i in range(n):
        pos[i] = wl * WL[i] / max(gL0[i], 1e-9) + ww * WW[i] / max(gW0[i], 1e-9)
    prev = np.zeros(NW); trn = np.zeros(n); gross = np.zeros(n); pnl = np.zeros(n); carry = np.zeros(n)
    for i in range(n):
        w = pos[i].astype(float); y = np.nan_to_num(D.R[i].astype(float))
        pnl[i] = (w * y).sum() * 1e4; carry[i] = (w * D.FC[i]).sum() * 1e4; trn[i] = np.abs(w - prev).sum(); gross[i] = np.abs(w).sum(); prev = w
    SERIES[f"NET_{wn}"] = {"pnl": pnl, "carry": carry, "trn": trn, "gross": gross, "net": pnl - carry - COST_MAIN * trn}
    META[f"NET_{wn}"] = f"exchange netting of separately-run books {wl}/{ww} (positions summed after each own pipeline; turnover of the netted position)"
    log("ARM", f"NET_{wn}", "sharpe", round(C.sharpe(SERIES[f"NET_{wn}"]["net"]), 3), "trn", round(float(trn.mean()), 5), "gross", round(float(gross.mean()), 4))
# ---------------------------------------------------------------- per-unit series (primary caliber) + paper
def pg_live(tag, cost=COST_MAIN):                       # per unit TARGET gross (=1)
    S = SERIES[tag]; return S["pnl"] - S["carry"] - cost * S["trn"]
def pg_wide_own(tag, cost=COST_MAIN, held=True):          # W2 convention: ÷ no-stop held gross_total; held=False ⇒ per unit target gross
    S = SERIES[tag]; net = S["pnl"] - S["carry"] - cost * S["trn"]
    return net / gW0 if held else net
X = {}
X["L_dev"] = pg_live("L_dev"); X["L_dev_nostop"] = pg_live("L_dev_nostop")
X["W_dev_own"] = pg_wide_own("W_dev_own"); X["W_dev_own_tgt"] = pg_wide_own("W_dev_own", held=False); X["W_dev_own_nostop"] = pg_wide_own("W_dev_own_nostop")
for tag in SERIES:
    if tag.startswith("M_") or tag.startswith("W_livefn") or tag.startswith("NET_"): X[tag] = pg_live(tag)
    elif tag.startswith("W_own_"): X[tag] = pg_wide_own(tag); X[tag + "_tgt"] = pg_wide_own(tag, held=False)
for wn, (wl, ww) in GRID_W.items():
    X[f"P_{wn}"] = wl * X["L_dev"] + ww * X["W_dev_own"]                    # device paper (same clock/returns/cost)
    X[f"P_{wn}_tgt"] = wl * X["L_dev"] + ww * X["W_dev_own_tgt"]
# W2 一审 paper (wide clock; primary caliber of two_book_allocation.py) for reference
Lw2 = np.load(f"{PD}/w2_live_series.npz", allow_pickle=True); Ww2 = np.load(f"{PD}/w2_wide_series.npz", allow_pickle=True)
cols = [str(c) for c in Ww2["cols"]]; Cc = {c: k for k, c in enumerate(cols)}; RW = Ww2["d30_n2_c42_rec"]; RW0 = Ww2["S0_rec"]
wpos2 = {int(t): j for j, t in enumerate(RW[:, Cc["ts"]].astype(np.int64))}; wi = np.array([wpos2[int(t)] for t in D.ts])
assert np.array_equal(Lw2["ts"].astype(np.int64), D.ts)
Lx2 = (Lw2["S1_net"].astype(float) - np.nan_to_num(Lw2["S1_carry"].astype(float))) / Lw2["S0_gross"].astype(float)
Wx2 = RW[wi, Cc["net"]] / RW0[wi, Cc["gross_total"]]
for wn, (wl, ww) in GRID_W.items(): X[f"W2first_P_{wn}"] = wl * Lx2 + ww * Wx2
X["W2first_L"] = Lx2; X["W2first_W"] = Wx2
mkt = Lw2["mkt_ew"].astype(float); btc = Lw2["btc4"].astype(float)
# ---------------------------------------------------------------- metrics
Q = C.q4_masks(X["L_dev"], mkt, btc, yr)
yrs = sorted(set(yr.tolist()))
def full_stats(tag):
    x = X[tag]; s = C.series_stats(x, yr, G)
    s["Q4_mean_at_G"] = {k: round(float(x[m].mean() * G), 3) for k, m in Q.items()}
    if tag in SERIES:
        S = SERIES[tag]
        s["turnover_unit_mean"] = round(float(np.nanmean(S["trn"])), 5); s["turnover_at_G_mean"] = round(float(np.nanmean(S["trn"]) * G), 5)
        s["gross_held_mean"] = round(float(np.nanmean(S["gross"])), 4); s["gross_held_by_year"] = {int(y): round(float(np.nanmean(S["gross"][yr == y])), 4) for y in yrs}
        if "gross_pre" in S: s["gross_pre_ema_mean"] = round(float(np.nanmean(S["gross_pre"])), 4); s["gross_pre_ema_by_year"] = {int(y): round(float(np.nanmean(S["gross_pre"][yr == y])), 4) for y in yrs}
        if "maxw" in S: s["maxw_mean"] = round(float(np.nanmean(S["maxw"])), 5); s["maxw_p95"] = round(float(np.nanpercentile(S["maxw"], 95)), 5); s["maxw_max"] = round(float(np.nanmax(S["maxw"])), 5)
        if "nheld" in S: s["nheld_mean"] = round(float(np.nanmean(S["nheld"])), 1)
        if "fires" in S: s["stop_fires_total"] = int(np.nansum(S["fires"]))
        if "ntraded" in S: s["ntraded_mean"] = round(float(np.nanmean(S["ntraded"])), 1)
        s["carry_mean_at_G"] = round(float(np.nanmean(S["carry"]) * G), 4); s["cost_main_at_G"] = round(float(np.nanmean(S["trn"]) * COST_MAIN * G), 4)
        if "cost_tier" in S: s["cost_tier_at_G"] = round(float(np.nanmean(S["cost_tier"]) * G), 4)
        s["gross_pnl_at_G"] = round(float(np.nanmean(S["pnl"]) * G), 4)
        s["sharpe_cost_sens"] = {str(c): round(C.sharpe(S["pnl"] - S["carry"] - c * S["trn"]), 3) for c in COST_SENS}
        if "cost_tier" in S: s["sharpe_cost_tiered"] = round(C.sharpe(S["pnl"] - S["carry"] - S["cost_tier"]), 3)
        s["mean_cost_sens_at_G"] = {str(c): round(float((S["pnl"] - S["carry"] - c * S["trn"]).mean() * G), 4) for c in COST_SENS}
        # capacity
        for g_ in (30800, 50000):
            if f"cap_nred_{g_}" in S:
                s[f"cap_{g_}"] = {"n_red_mean": round(float(np.nanmean(S[f"cap_nred_{g_}"])), 2), "n_red_last500": round(float(np.nanmean(S[f"cap_nred_{g_}"][-500:])), 2),
                                  "share_red_mean": round(float(np.nanmean(S[f"cap_sred_{g_}"])), 4), "share_red_last500": round(float(np.nanmean(S[f"cap_sred_{g_}"][-500:])), 4),
                                  "share_red_by_year": {int(y): round(float(np.nanmean(S[f"cap_sred_{g_}"][yr == y])), 4) for y in yrs},
                                  "share_below_5usdt_mean": round(float(np.nanmean(S[f"cap_sfloor5_{g_}"])), 4), "share_below_5usdt_last500": round(float(np.nanmean(S[f"cap_sfloor5_{g_}"][-500:])), 4),
                                  "share_below_20usdt_last500": round(float(np.nanmean(S[f"cap_sfloor20_{g_}"][-500:])), 4), "share_qv_unknown_mean": round(float(np.nanmean(S[f"cap_sunk_{g_}"])), 4)}
    return s
STATS = {tag: full_stats(tag) for tag in X}
# criteria for every arm vs device paper / live
def crit(tag, wn="w07"):
    sM = STATS[tag]["sharpe"]; sP = STATS[f"P_{wn}"]["sharpe"]; sL = STATS["L_dev"]["sharpe"]; sW = STATS["W_dev_own"]["sharpe"]
    byM = STATS[tag]["by_year_sharpe"]; byL = STATS["L_dev"]["by_year_sharpe"]; byW = STATS["W_dev_own"]["by_year_sharpe"]
    wl, ww = GRID_W[wn]
    trM = STATS[tag].get("turnover_unit_mean", float("nan")); trP = wl * STATS["L_dev"]["turnover_unit_mean"] + ww * STATS["W_dev_own"]["turnover_unit_mean"]
    nB = sum(1 for y in yrs if byM[y] >= byL[y]); nA = sum(1 for y in yrs if byM[y] >= max(byL[y], byW[y])); nPos = sum(1 for y in yrs if STATS[tag]["by_year_mean_at_G"][y] > 0)
    c1 = sM >= sP - 0.10; c2 = sM >= sL + 0.15; c3 = nB >= 4; c4 = trM <= trP
    return {"sharpe": sM, "paper_sharpe": sP, "pipeline_loss(paper-merged)": round(sP - sM, 3), "live_sharpe": sL, "wide_own_sharpe": sW,
            "c1_sharpe_ge_paper_minus_0.10": bool(c1), "c2_sharpe_ge_live_plus_0.15": bool(c2), "c3_years_ge_live": f"{nB}/{len(yrs)}", "c3_pass": bool(c3), "years_ge_max_single(readingA)": f"{nA}/{len(yrs)}", "years_positive": f"{nPos}/{len(yrs)}",
            "c4_turnover_unit": round(trM, 5), "c4_paper_turnover_unit": round(trP, 5), "c4_pass": bool(c4), "PASS": bool(c1 and c2 and c3 and c4)}
CRIT = {}
for tag in X:
    if tag.startswith("M_") or tag.startswith("NET_") or tag.startswith("W_livefn"):
        wn = "w07" if "w07" in tag or tag.startswith("W_livefn") else ("w05" if "w05" in tag else "w06")
        CRIT[tag] = crit(tag, wn)
# ---- verdict (frozen rule)
main = "M_w07_b0.002"; scaled = ["M_w07_b0.0005", "M_w07_b0.00025"]
if CRIT[main]["PASS"]: verdict = "PASS: 合成书走实盘函数管线过四关"
elif any(CRIT[s]["PASS"] for s in scaled if s in CRIT): verdict = "FAIL(M0) but band-scaled arm PASS ⇒ 需重设计(带按名数缩放): " + ",".join(s for s in scaled if s in CRIT and CRIT[s]["PASS"])
else: verdict = "FAIL ⇒ 配置不成立(实盘函数管线下); 管线损耗过大"
# ---- bootstrap + trip
BOOT = {"M0_minus_P": C.boot_delta_sharpe(X[main], X["P_w07"]), "M0_minus_L": C.boot_delta_sharpe(X[main], X["L_dev"]),
        "P_minus_L": C.boot_delta_sharpe(X["P_w07"], X["L_dev"])}
for s in scaled:
    if s in X: BOOT[f"{s}_minus_P"] = C.boot_delta_sharpe(X[s], X["P_w07"]); BOOT[f"{s}_minus_L"] = C.boot_delta_sharpe(X[s], X["L_dev"])
if "NET_w07" in X: BOOT["NET_w07_minus_P"] = C.boot_delta_sharpe(X["NET_w07"], X["P_w07"])
TRIP = {}
for tag in ["L_dev", "W_dev_own", "P_w07", "P_w05", main] + [s for s in scaled if s in X] + ["W2first_P_w07", "W2first_L", "W2first_W"]:
    TRIP[tag] = {"replay": C.trip(X[tag], G, 1.0), "shrink0.55": C.trip(X[tag], G, 0.55)}
# ---- correlations (same clock) for the record
RHO = {"L_dev|W_dev_own(same clock)": round(float(np.corrcoef(X["L_dev"], X["W_dev_own"])[0, 1]), 4), "W2first L|W (1h offset)": round(float(np.corrcoef(Lx2, Wx2)[0, 1]), 4),
       "L_dev|L_W2first": round(float(np.corrcoef(X["L_dev"], Lx2)[0, 1]), 4), "W_dev_own|W_W2first": round(float(np.corrcoef(X["W_dev_own"], Wx2)[0, 1]), 4),
       "by_year_same_clock": {int(y): round(float(np.corrcoef(X["L_dev"][yr == y], X["W_dev_own"][yr == y])[0, 1]), 3) for y in yrs}}
# ---- decomposition of the wide book's Sharpe: W2 一审 (2.107) → source → clock → cost model → caliber
SW2 = SERIES["W_native"]; gW2_0 = RW0[wi, Cc["gross_total"]]          # W2 no-stop held gross (wide clock series)
DECOMP = {"W2first_wide_tiered_heldgross(meta y4, wide clock)": round(C.sharpe(Wx2), 3),
          "W_native_flat3.52_heldgross(meta y4, wide clock)": round(C.sharpe((SW2["pnl"] - SW2["carry"] - COST_MAIN * SW2["trn"]) / gW2_0), 3),
          "W_own_Rwide_flat3.52_heldgross(1h kline, wide clock)": round(C.sharpe(X["W_own_Rwide"]), 3) if "W_own_Rwide" in X else None,
          "W_dev_own_tiered_heldgross(1h kline, live clock)": round(C.sharpe((SERIES["W_dev_own"]["pnl"] - SERIES["W_dev_own"]["carry"] - SERIES["W_dev_own"]["cost_tier"]) / gW0), 3),
          "W_dev_own_flat3.52_heldgross(1h kline, live clock) = paper component": round(C.sharpe(X["W_dev_own"]), 3),
          "W_dev_own_flat3.52_targetgross": round(C.sharpe(X["W_dev_own_tgt"]), 3),
          "ladder_heldgross": {t: round(C.sharpe(X[t]), 3) for t in X if t.startswith("W_own_") and not t.endswith("_tgt")},
          "ladder_livefn_targetgross": {t: round(C.sharpe(X[t]), 3) for t in X if t.startswith("W_livefn")},
          "ladder_merged": {t: round(C.sharpe(X[t]), 3) for t in X if t.startswith("M_w07_b0.002")}}
# ---- analytic weights on same clock
sL, sW = X["L_dev"].std(ddof=1), X["W_dev_own"].std(ddof=1); w_rp = float((1 / sW) / (1 / sL + 1 / sW))
grid_same_clock = {str(round(w, 1)): round(C.sharpe((1 - w) * X["L_dev"] + w * X["W_dev_own"]), 3) for w in np.arange(0, 1.01, 0.1)}
# ---------------------------------------------------------------- save
RES = {"meta": {"created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "session": "6737834a-W2b", "G": G, "cost_main": COST_MAIN, "cost_sens": COST_SENS, "arms_mode": ARMS_MODE,
                "inputs_sha256": pins, "cube_meta": D.cube_meta, "receipts": {"L_native_maxabs_vs_net_S1": d_live, "W_native_maxabs_vs_nets_histv2_-30_2_42": d_wide},
                "clock_note": "all device arms on the LIVE clock (label T ⇒ decision T+1h, returns T+1h→T+5h from 1h klines for all 829 names); W2first_* = W2 一审 series (live label T vs wide E=T, 1h apart)",
                "caliber": "per unit TARGET gross × G for live-pipeline arms; wide own-pipeline arms ÷ no-stop held gross_total (W2 convention) with per-unit-target also reported (suffix _tgt)",
                "frozen_criteria": "c1 S(M0)>=S(P0)-0.10; c2 S(M0)>=S(L)+0.15; c3 years S(M0)>=S(L) >=4/5; c4 trn(M0)<=0.3trn(L)+0.7trn(W); PASS iff all; fallback rule: scaled-band arm pass ⇒ 需重设计"},
       "arm_notes": META, "stats": STATS, "criteria": CRIT, "verdict": verdict, "bootstrap": BOOT, "trip_probability": TRIP, "rho": RHO,
       "same_clock_weight_grid_paper": grid_same_clock, "decomposition": DECOMP, "risk_parity_w_wide_same_clock": round(w_rp, 4), "Q4_n": {k: int(m.sum()) for k, m in Q.items()}}
json.dump(RES, open(f"{PD}/w2b_merged_book_2026-08-22.json", "w"), indent=1, ensure_ascii=False)
np.savez_compressed(f"{PD}/w2b_merged_series.npz", ts=D.ts, yr=yr, **{f"{tag}__{k}": v for tag, S in SERIES.items() for k, v in S.items()}, **{f"X__{tag}": v for tag, v in X.items()})
np.savez_compressed(f"{PD}/w2b_merged_W.npz", ts=D.ts, symbols=np.array(D.WSYM), **{f"W__{tag}": RUNS[tag]["W"] for tag in RUNS if RUNS[tag].get("W") is not None})
print("VERDICT", verdict)
for tag in CRIT: print("CRIT", tag, json.dumps(CRIT[tag], ensure_ascii=False))
print("BOOT", json.dumps(BOOT, ensure_ascii=False))
print("RHO", json.dumps(RHO, ensure_ascii=False))
print("DONE", round(time.time() - t0), "s")
