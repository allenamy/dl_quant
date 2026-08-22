"""回撤阶梯 · 第二装置 = 实盘函数同构回放叠加 (DESIGN_optimization_path_2026-08-21 §4.2; Session 6737834a-L1; 2026-08-22)

★ 冻结判据(供 08-25 预注册; 先于数字写入, 本文件 SHA256 入 RESULT 文档首段):
    主臂 L6(−10%→m=0.5, 回到 −5% 恢复 m=1), 主口径 = 回撤基准【窗口起点】+ 成本 3.52 bps/单位换手 + 恒定杠杆 L=2 + 阶梯置于 EMA 之后(gross 层)
    + 带相对【目标 gross】(post_bandrel; v2 2026-08-22 01:xxZ: 主线在实盘仓核实 scheduler/anchor_loop.py:1433 band_notional = no_trade_band_w(0.002) × self.gross,
      target/positions 皆名义额 ⇒ 带随阶梯乘后 gross 缩放; v1 主口径 post=NAV 绝对单位带(回放装置写法)降为敏感, 判据文本与档位未动, 全部臂保留并列):
      G1  触线概率 P(−25% 自窗口起点) ≤ 静态 × 1/3
      G2  年均收益(255 窗均值) ≥ 静态 − 5pp
      G3  夏普(255 窗逐窗夏普均值) ≥ 静态 − 0.05
      G4  逐年(日历年块 2022/2023/2024/2025/2026H1, 回撤自年初起算) 中 ≥ 4/5 年 (L6 − 静态) ≥ −5pp
    四条全过 ⇒ 阶梯(L6)可进预注册; 任一不过 ⇒ 判负或改档(改档只许在 L5/L4 敏感臂中读, 不得新造档位)。
    只报主臂为判决; L5/L4/高水位基准/成本 4.137 与 0.32/EMA 前置/绝对带 均为敏感与诊断, 不参与判决(四关逐条对 L5/L4 与绝对带也算出并列, 供改档/敏感阅读)。

书构造 = w2_live_replay.py(devices_2026-08-21, SHA 9105e5fa…)逐字同构: 实盘 legs.compose_book 原样 import, W/RB/EMA α0.05/带 b0.002/
逐名止损(成本均价深度 −25%, 连续 2 锚, 冷却 42 锚) / 成本 C×换手。复现收据: 全史静态(C=4.137) net 必须与 probe_artifacts/net_S1.npy 逐元素相等。

阶梯作用位置(★ 关键口径): legs.apply_harvest_ema 输出经二次 demean 后 L1 归一为 1(代码 line ~293-296), 实盘随后由 to_notional(target_w, gross_usdt)
乘目标 gross(=L×NAV) 出名义 ⇒ 阶梯 m 乘在【EMA 之后的 gross 层】(gross_usdt = m×L×NAV), 再走 带/止损/成本。
"目标权重 ×m 再进 EMA" 在本函数下是 gross 无操作(EMA 把 L1 归回 1) —— 作为诊断臂 L6_preEMA 实测并留痕。
带的单位两种约定并报: post = 带 b=0.002 按 NAV 权重绝对单位(回放装置 deepsmooth/nband/w2 的写法); post_bandrel = 带相对【目标 gross】
(executor.plan() 的 |Δ|/gross_target 写法 ⇒ 1× 权重单位下阈值 b×m)。实盘 08-10 版带的真实单位需由主线在实盘仓核对后定主口径; 两者之差 = 管线效应主体。

窗口: 255 个滚动 1 年窗(2190 锚, 步 30), 起点 2022-01-01 → 2025-06-28; 每窗从全史静态 S1 路径在窗起点的【真实状态】热启动
(EMA 状态/持仓/止损成本均价/冷却 全部快照), 静态臂热启动后必须与全史切片逐元素相等(收据)。
权益: E_t = E_{t-1}×(1 + L×net_t/1e4), net_t = pnl_t − C×trn_t (1× 权重口径; 纸面叠加用的是 net/gross_t×L 恒定 gross, 两口径差在 static 上单列)。
回撤: 窗口起点 dd_t = E_{t-1}/E_0 − 1 (主, 与实盘 §4-4 自起点 TWR 同构); 高水位 dd_t = E_{t-1}/max_{s<t}E_s − 1 (info)。
阶梯: 档 k 在 dd ≤ th_k 进入; 处于档 k 时 dd ≥ (th_k + th_{k−1})/2 (th_0 = 0) 回退一档(单步档即"回到门槛一半处", 与纸面叠加逐位同则)。
触线: dd ≤ −25% ⇒ 当锚整书平仓(换手=|持仓|合计, 记 C 成本; 实盘为市价, 此处按 C 记, 对触线概率无影响), 窗口余下空仓(r=0 计入夏普)。

输入(只读): probe_artifacts/{king_pred_newgen.npz, s2_pred_newgen.npz, net_S1.npy, net_S1_ts.npy, legs.py}, engine/replay_fullhist.py(PanelSource 默认面板, 与 w2 同)。
输出: probe_artifacts/drawdown_ladder_livefn_2026-08-22.json + .log。不碰实盘仓/不碰 share/不调 API。
用法: conda activate hsy_v5push; python drawdown_ladder_livefn.py [--smoke] [--workers 24]
"""
import sys, os, json, time, hashlib, argparse
import numpy as np
import multiprocessing as mp

PD = "/mnt/storage/private/work_hsy/probe_artifacts"; sys.path.insert(0, PD)
MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
sys.path.insert(0, MA); sys.path.insert(0, MA + "/engine/live"); sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset")
sys.path.insert(0, PD)
import legs as LG
import engine.replay_fullhist as RF

W = {"king": .5952380952380952, "s2": .20238095238095238, "funding": .20238095238095238, "size": 0.}
RB = {"alpha": .5, "lambda": 1.}; BW = 0.002; COOL = 42; EMA_A = 0.05; STOP_DEPTH = -0.25; STOP_N = 2
ANN = np.sqrt(6 * 365)
NY = 2190; STEP = 30; L_LEV = 2.0; KILL = -0.25
C_MAIN = 3.52; C_PAPER = 4.137; C_LOW = 0.32
LADDERS = {"static": [], "L6": [(-0.10, 0.5)], "L5": [(-0.06, 0.5)], "L4": [(-0.12, 0.5), (-0.18, 0.25)]}
FROZEN = {"G1_trip_ratio_max": 1 / 3, "G2_ret_pp_min": -5.0, "G3_sharpe_min": -0.05, "G4_years_min": 4, "G4_year_pp_min": -5.0,
          "main": {"arm": "L6", "basis": "ws", "C": C_MAIN, "L": L_LEV, "placement": "post_bandrel"},
          "caliber_history": "v1 (00:35Z) main placement=post (absolute NAV-unit band, replay convention); v2 (01:xxZ) main=post_bandrel after team-lead verified the live band is relative to target gross (anchor_loop.py:1433). Thresholds/arms/rule unchanged; both placements reported."}

ap = argparse.ArgumentParser(); ap.add_argument("--smoke", action="store_true"); ap.add_argument("--workers", type=int, default=24)
ap.add_argument("--out", default=f"{PD}/drawdown_ladder_livefn_2026-08-22.json")
ARGS = ap.parse_args()
t0 = time.time()
def log(*a):
    print(*a, flush=True)

def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 20), b""): h.update(ch)
    return h.hexdigest()
INPUTS = {os.path.basename(p): sha(p) for p in [f"{PD}/king_pred_newgen.npz", f"{PD}/s2_pred_newgen.npz", f"{PD}/net_S1.npy", f"{PD}/net_S1_ts.npy",
                                                 f"{PD}/legs.py", f"{MA}/engine/replay_fullhist.py", os.path.abspath(__file__)]}
log("INPUT SHA256", json.dumps(INPUTS, indent=0))

# ---------------- precompute targets (verbatim w2_live_replay) ----------------
src = RF.get_src(None, f"{PD}/king_pred_newgen.npz", f"{PD}/s2_pred_newgen.npz")
a, yr = RF._all_anchors(src); N = src.N; n = len(a); yr = np.asarray(yr)
FI, RVI = src.fund_idx, src.ch.index("rvol_24h"); SYMS = [str(s) for s in src.symbols]
ts_all = np.asarray(src.ts)
tss = ts_all // 1000 if (ts_all[1] - ts_all[0]) >= 3600 * 1000 else ts_all
ats = np.array([int(tss[int(t)]) for t in a], dtype=np.int64)
ref_ts = np.load(f"{PD}/net_S1_ts.npy")[:, 0].astype(np.int64)
assert np.array_equal(ref_ts, ats), "anchor ts mismatch vs net_S1_ts.npy"
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
    if i % 2000 == 0: log("precompute", i, "/", n, round(time.time() - t0, 1), "s")
NONMEM = [np.array([j for j in range(N) if j not in set(m)], int) for m in MSK]
log("precompute done", round(time.time() - t0, 1), "s; n", n, "N", N)

# ---------------- the book step (verbatim mechanics of w2_live_replay.run, S1 = with stop) ----------------
def book_step(i, S, m_mult=1.0, placement="post"):
    """One anchor of the in-role book. S = mutable state dict. Returns (pnl_bps, trn, gross, fires)."""
    m = MSK[i]; syms = [SYMS[j] for j in m]
    raw = TGT[i][m]
    if placement == "pre":
        raw = raw * m_mult   # diagnostic: EMA renormalises L1 -> no-op on gross
    out = LG.apply_harvest_ema(raw, syms, S["ema"], EMA_A); S["ema"] = out["state"]
    tgt = np.asarray(out["target_w"], float)
    if placement in ("post", "post_bandrel"):
        tgt = tgt * m_mult   # gross layer (to_notional gross_usdt = m×L×NAV)
    su = S["su"]; prev = S["prev"]
    bs = set(np.where(su > i)[0].tolist())
    if bs:
        for k2, j in enumerate(m):
            if j in bs: tgt[k2] = 0.0
    w = prev.copy(); w[NONMEM[i]] = 0.0
    bw = BW * m_mult if placement == "post_bandrel" else BW   # bandrel: band relative to TARGET gross (executor plan(): |Δ|/gross_target)
    d = tgt - w[m]; T = np.abs(d) > bw
    wm = w[m].copy(); wm[T] = tgt[T]
    if T.any(): wm[T] -= wm.sum() / T.sum()
    w[m] = wm
    y = RET[i]; ok = np.isfinite(y); idx = m[ok]
    pnl = float((w[idx] * y[ok]).sum() * 1e4)
    trn = float(np.abs(w - prev).sum()); gross = float(np.abs(w).sum())
    # per-name stop bookkeeping (cost-basis depth)
    Pi, sh, cb, cnt = S["Pi"], S["sh"], S["cb"], S["cnt"]
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
    cand = (np.abs(sh) > 1e-12) & (dep <= STOP_DEPTH) & (su <= i)
    cnt = np.where(cand, cnt + 1, 0)
    fire = cnt >= STOP_N; nf = 0
    if fire.any(): su = su.copy(); su[fire] = i + COOL; cnt[fire] = 0; nf = int(fire.sum())
    upd = np.zeros(N); upd[idx] = y[ok]; Pi = Pi * (1.0 + upd)
    S.update(prev=w, Pi=Pi, sh=sh, cb=cb, cnt=cnt, su=su)
    return pnl, trn, gross, nf

def fresh_state():
    return dict(ema=None, prev=np.zeros(N), Pi=np.ones(N), sh=np.zeros(N), cb=np.zeros(N), cnt=np.zeros(N, int), su=np.full(N, -1))

def copy_state(S):
    return dict(ema=(dict(S["ema"]) if S["ema"] is not None else None), prev=S["prev"].copy(), Pi=S["Pi"].copy(), sh=S["sh"].copy(),
                cb=S["cb"].copy(), cnt=S["cnt"].copy(), su=S["su"].copy())

# ---------------- full-history static S1 run + snapshots at window starts ----------------
STARTS = list(range(0, n - NY + 1, STEP))
YEARS = sorted(set(yr.tolist())); YBLK = {int(y_): (int(np.where(yr == y_)[0][0]), int(np.where(yr == y_)[0][-1]) + 1) for y_ in YEARS}
SNAP = {}
S = fresh_state(); FH = dict(pnl=np.zeros(n), trn=np.zeros(n), gross=np.zeros(n), fires=np.zeros(n, int))
for i in range(n):
    if i in STARTS or any(i == b[0] for b in YBLK.values()): SNAP[i] = copy_state(S)
    FH["pnl"][i], FH["trn"][i], FH["gross"][i], FH["fires"][i] = book_step(i, S)
    if i % 2000 == 0: log("fullhist static", i, "/", n, round(time.time() - t0, 1), "s")
net_fh_paper = FH["pnl"] - FH["trn"] * C_PAPER
ref = np.load(f"{PD}/net_S1.npy"); RECEIPT = {}
RECEIPT["fullhist_static_vs_net_S1_maxabs"] = float(np.max(np.abs(ref - net_fh_paper)))
RECEIPT["fullhist_static_C4137"] = dict(mean=round(float(net_fh_paper.mean()), 4), sharpe=round(float(net_fh_paper.mean() / net_fh_paper.std(ddof=1) * ANN), 3),
                                        fires=int(FH["fires"].sum()), gross_mean=round(float(FH["gross"].mean()), 4), turnover_mean=round(float(FH["trn"].mean()), 5))
log("RECEIPT fullhist", json.dumps(RECEIPT))
assert RECEIPT["fullhist_static_vs_net_S1_maxabs"] < 1e-9, "full-history static does not reproduce net_S1.npy"

# ---------------- ladder helpers (paper-identical rule) ----------------
def level_update(lvl, dd, ladder):
    new = lvl
    for k, (th, mu) in enumerate(ladder):
        if dd <= th: new = max(new, k + 1)
    if new == lvl and lvl > 0:
        up = ladder[lvl - 2][0] if lvl >= 2 else 0.0
        if dd >= (ladder[lvl - 1][0] + up) / 2: new = lvl - 1
    return new
def m_of(lvl, ladder):
    return 1.0 if lvl == 0 else ladder[lvl - 1][1]

# ---------------- one window in the live function ----------------
def run_window(i0, nlen, ladder, basis, C, placement="post", L=L_LEV):
    S = copy_state(SNAP[i0]); E = 1.0; peak = 1.0; lvl = 0; m = 1.0; dead = False
    rs = np.zeros(nlen); trn_tot = 0.0; ndel = 0; events = []; mn = 0.0; fires = 0; gross_sum = 0.0; pnl_tot = 0.0; nalive = 0
    for k in range(nlen):
        i = i0 + k
        if dead: ndel += 1; continue
        ref_ = 1.0 if basis == "ws" else peak
        dd = E / ref_ - 1.0
        if dd <= KILL:
            dead = True; trn = float(np.abs(S["prev"]).sum()); net = -C * trn; trn_tot += trn
            events.append((i, m, 0.0)); m = 0.0; S["prev"] = np.zeros(N)
            rs[k] = L * net / 1e4; E *= 1 + rs[k]; mn = min(mn, E - 1); ndel += 1; continue
        lvl = level_update(lvl, dd, ladder); newm = m_of(lvl, ladder)
        if newm != m: events.append((i, m, newm)); m = newm
        pnl, trn, gross, nf = book_step(i, S, m, placement)
        net = pnl - C * trn; trn_tot += trn; fires += nf; gross_sum += gross; pnl_tot += pnl; nalive += 1
        rs[k] = L * net / 1e4; E *= 1 + rs[k]; peak = max(peak, E); mn = min(mn, E - 1)
        if m < 1.0: ndel += 1
    sd = rs.std(ddof=1)
    return dict(ret=E - 1.0, sharpe=(rs.mean() / sd * ANN) if sd > 0 else 0.0, trip=dead, minfs=mn, time_delev=ndel / nlen,
                trn=trn_tot, trn_base=float(FH["trn"][i0:i0 + nlen].sum()), pnl=pnl_tot, fires=fires, gross_mean=gross_sum / max(1, nalive),
                n_delev=sum(1 for e in events if e[2] < e[1] and e[2] > 0), n_recov=sum(1 for e in events if e[2] > e[1]),
                events=[(int(e[0]), float(e[1]), float(e[2])) for e in events])

# ---------------- paper overlay (same windows; two normalisations) ----------------
def paper_window(x, i0, nlen, ladder, basis, L=L_LEV, cost=4.0):
    seg = x[i0:i0 + nlen] / 1e4; E = 1.0; peak = 1.0; m = 1.0; lvl = 0; dead = False; c = 0.0; nd = 0; mn = 0.0; rs = np.zeros(nlen)
    for t in range(nlen):
        if dead: nd += 1; continue
        ref_ = 1.0 if basis == "ws" else peak
        dd = E / ref_ - 1
        if dd <= KILL: dead = True; m = 0.0; nd += 1; continue
        lvl = level_update(lvl, dd, ladder); newm = m_of(lvl, ladder)
        cc = cost * abs(newm - m) * L; c += cc; m = newm
        rs[t] = L * m * seg[t] - cc * 1e-4; E *= 1 + rs[t]; peak = max(peak, E); nd += (m < 1.0); mn = min(mn, E - 1)
    sd = rs.std(ddof=1)
    return dict(ret=E - 1, sharpe=(rs.mean() / sd * ANN) if sd > 0 else 0.0, trip=dead, minfs=mn, time_delev=nd / nlen, cost=c)

def summarise(rows):
    r = np.array([x["ret"] for x in rows]) * 100
    out = dict(n=len(rows), ret_mean=round(float(r.mean()), 2), ret_med=round(float(np.median(r)), 2), ret_p10=round(float(np.percentile(r, 10)), 2),
               sharpe_mean=round(float(np.mean([x["sharpe"] for x in rows])), 3), p_trip=round(100 * float(np.mean([x["trip"] for x in rows])), 2),
               n_trip=int(sum(x["trip"] for x in rows)), minfs_p10=round(100 * float(np.percentile([x["minfs"] for x in rows], 10)), 2),
               time_delev=round(100 * float(np.mean([x["time_delev"] for x in rows])), 2))
    if "trn" in rows[0]:
        ex = np.array([x["trn"] - x["trn_base"] for x in rows])
        out.update(extra_turnover_per_window=round(float(ex.mean()), 4), n_delev_mean=round(float(np.mean([x["n_delev"] for x in rows])), 3),
                   n_recov_mean=round(float(np.mean([x["n_recov"] for x in rows])), 3), fires_mean=round(float(np.mean([x["fires"] for x in rows])), 2),
                   gross_mean=round(float(np.mean([x["gross_mean"] for x in rows])), 4))
    if "cost" in rows[0]: out["cost_bps"] = round(float(np.mean([x["cost"] for x in rows])), 2)
    return out

# ---------------- task grid ----------------
# v2: main placement = post_bandrel (live band ∝ target gross, verified); post (absolute NAV-unit band) = sensitivity; pre = diagnostic no-op.
# static is placement-independent (m≡1) ⇒ run once per (C, basis) as "post".
CONFIGS = []
for C in (C_MAIN, C_PAPER, C_LOW):
    for basis in ("ws", "hwm"):
        CONFIGS.append(dict(arm="static", basis=basis, C=C, placement="post"))
        for plc in ("post_bandrel", "post"):
            for arm in ("L6", "L5", "L4"):
                CONFIGS.append(dict(arm=arm, basis=basis, C=C, placement=plc))
CONFIGS.append(dict(arm="L6", basis="ws", C=C_MAIN, placement="pre"))
WINS = STARTS if not ARGS.smoke else STARTS[::64]
TASKS = [(ci, i0, NY, "win") for ci, cfg in enumerate(CONFIGS) for i0 in WINS]
YB_CFG = [ci for ci, cfg in enumerate(CONFIGS) if cfg["basis"] == "ws" and cfg["placement"] != "pre"]
TASKS += [(ci, b0, b1 - b0, "yb") for ci in YB_CFG for y_, (b0, b1) in YBLK.items()]
log("configs", len(CONFIGS), "windows", len(WINS), "tasks", len(TASKS))

def work(task):
    ci, i0, nlen, kind = task; cfg = CONFIGS[ci]
    return ci, i0, kind, run_window(i0, nlen, LADDERS[cfg["arm"]], cfg["basis"], cfg["C"], cfg["placement"])

# receipt: static warm-start window == full-history slice (C=4.137)
r0 = run_window(STARTS[0], NY, [], "ws", C_PAPER); r1 = run_window(STARTS[100], NY, [], "ws", C_PAPER)
def slice_ret(i0, C):
    net = FH["pnl"][i0:i0 + NY] - C * FH["trn"][i0:i0 + NY]; return float(np.prod(1 + L_LEV * net / 1e4) - 1)
RECEIPT["warmstart_static_vs_slice"] = {"w0": [round(r0["ret"], 8), round(slice_ret(STARTS[0], C_PAPER), 8), bool(r0["trip"])],
                                        "w100": [round(r1["ret"], 8), round(slice_ret(STARTS[100], C_PAPER), 8), bool(r1["trip"])]}
log("RECEIPT warmstart", json.dumps(RECEIPT["warmstart_static_vs_slice"]))
for key in ("w0", "w100"):
    v = RECEIPT["warmstart_static_vs_slice"][key]
    if not v[2]: assert abs(v[0] - v[1]) < 1e-9, f"warm-start static window {key} != full-history slice"

# run grid (windows + calendar-year blocks) in one pool
t1 = time.time(); RES = {ci: {} for ci in range(len(CONFIGS))}; YBR = {ci: {} for ci in range(len(CONFIGS))}
with mp.get_context("fork").Pool(ARGS.workers) as pool:
    for k, (ci, i0, kind, r) in enumerate(pool.imap_unordered(work, TASKS, chunksize=4)):
        (RES if kind == "win" else YBR)[ci][i0] = r
        if k % 1000 == 0: log("grid", k, "/", len(TASKS), round(time.time() - t1, 1), "s")
log("grid done", round(time.time() - t1, 1), "s")

def ckey(cfg): return f"{cfg['arm']}|{cfg['basis']}|C{cfg['C']}|{cfg['placement']}"
# calendar-year blocks (dd from year start) — for G4 and regime trigger counts; key = arm|C|year|placement
YB = {}
for ci in YB_CFG:
    cfg = CONFIGS[ci]
    for y_, (b0, b1) in YBLK.items():
        r = YBR[ci][b0]
        YB[f"{cfg['arm']}|C{cfg['C']}|{y_}|{cfg['placement']}"] = dict(ret_pct=round(100 * r["ret"], 2), sharpe=round(r["sharpe"], 3), trip=bool(r["trip"]), minfs_pct=round(100 * r["minfs"], 2),
                                           time_delev=round(100 * r["time_delev"], 2), n_delev=r["n_delev"], n_recov=r["n_recov"],
                                           extra_turnover=round(r["trn"] - r["trn_base"], 4), n_anchors=b1 - b0,
                                           events=[(time.strftime("%Y-%m-%d %H:%M", time.gmtime(int(ats[e[0]]))), e[1], e[2]) for e in r["events"]])
log("year blocks assembled", round(time.time() - t0, 1), "s")

# paper overlay on the same windows (A: L×net 1×-weight caliber; B: L×net/gross constant-gross caliber = published JSON)
PAPER = {}
xA = net_fh_paper; xB = net_fh_paper / np.maximum(FH["gross"], 1e-9)
xA352 = FH["pnl"] - C_MAIN * FH["trn"]
for nm, x in (("A_Lxnet_C4137", xA), ("B_Lxnet_over_gross_C4137", xB), ("A_Lxnet_C352", xA352)):
    for basis in ("ws", "hwm"):
        for arm in ("static", "L6", "L5", "L4"):
            PAPER[f"{nm}|{basis}|{arm}"] = summarise([paper_window(x, i0, NY, LADDERS[arm], basis) for i0 in WINS])
# paper A (C=3.52) calendar-year blocks — shows G4 failure exists without any pipeline
PAPER_YB = {}
for arm in ("static", "L6", "L5", "L4"):
    for y_, (b0, b1) in YBLK.items():
        r = paper_window(xA352, b0, b1 - b0, LADDERS[arm], "ws")
        PAPER_YB[f"{arm}|C3.52|{y_}"] = dict(ret_pct=round(100 * r["ret"], 2), time_delev=round(100 * r["time_delev"], 2), trip=bool(r["trip"]))
log("paper overlay done", round(time.time() - t0, 1), "s")

# ---------------- assemble ----------------
OUT = {"device": __doc__.split("\n")[0], "frozen_criteria": FROZEN, "inputs_sha256": INPUTS, "receipts": RECEIPT,
       "windows": {"n": len(WINS), "len": NY, "step": STEP, "first_start": time.strftime("%Y-%m-%d", time.gmtime(int(ats[WINS[0]]))),
                   "last_start": time.strftime("%Y-%m-%d", time.gmtime(int(ats[WINS[-1]])))},
       "livefn": {}, "livefn_by_start_year": {}, "events_by_year": {}, "paper": PAPER, "paper_year_blocks_A_C352": PAPER_YB, "year_blocks": YB}
for ci, cfg in enumerate(CONFIGS):
    key = ckey(cfg); rows = [RES[ci][i0] for i0 in WINS]
    OUT["livefn"][key] = summarise(rows)
    by = {}
    for i0, r in zip(WINS, rows):
        y_ = int(yr[i0]); by.setdefault(y_, []).append(r)
    OUT["livefn_by_start_year"][key] = {y_: summarise(v) for y_, v in by.items()}
    ev = {}
    for r in rows:
        for (ia, mf, mt) in r["events"]:
            y_ = int(yr[ia]); d = ev.setdefault(y_, {"delever": 0, "recover": 0, "kill": 0})
            if mt == 0.0: d["kill"] += 1
            elif mt < mf: d["delever"] += 1
            else: d["recover"] += 1
    OUT["events_by_year"][key] = ev
# per-window rows — livefn all configs + paper A_C352
PW = {}
for ci, cfg in enumerate(CONFIGS):
    key = ckey(cfg); rows = [RES[ci][i0] for i0 in WINS]
    PW[key] = {"start_idx": [int(i) for i in WINS], "start_date": [time.strftime("%Y-%m-%d", time.gmtime(int(ats[i]))) for i in WINS],
               "ret_pct": [round(100 * r["ret"], 4) for r in rows], "sharpe": [round(r["sharpe"], 4) for r in rows], "trip": [bool(r["trip"]) for r in rows],
               "minfs_pct": [round(100 * r["minfs"], 3) for r in rows], "time_delev": [round(r["time_delev"], 4) for r in rows],
               "extra_trn": [round(r["trn"] - r["trn_base"], 4) for r in rows], "n_delev": [r["n_delev"] for r in rows], "n_recov": [r["n_recov"] for r in rows],
               "fires": [r["fires"] for r in rows], "gross_mean": [round(r["gross_mean"], 4) for r in rows],
               "first_event": [(time.strftime("%Y-%m-%d %H:%M", time.gmtime(int(ats[r["events"][0][0]]))) if r["events"] else None) for r in rows]}
for arm in ("static", "L6", "L5", "L4"):
    for basis in ("ws", "hwm"):
        rows = [paper_window(xA352, i0, NY, LADDERS[arm], basis) for i0 in WINS]
        PW[f"paperA_C352|{arm}|{basis}"] = {"ret_pct": [round(100 * r["ret"], 4) for r in rows], "sharpe": [round(r["sharpe"], 4) for r in rows], "trip": [bool(r["trip"]) for r in rows],
                                           "time_delev": [round(r["time_delev"], 4) for r in rows], "cost_bps": [round(r["cost"], 3) for r in rows]}
OUT["per_window"] = PW
# gate evaluation: every (arm, C, placement) at ws basis; main = L6|C3.52|post_bandrel
yrs = [int(y_) for y_ in YEARS]
def gates_for(arm, C, plc):
    st = OUT["livefn"][f"static|ws|C{C}|post"]; a = OUT["livefn"][f"{arm}|ws|C{C}|{plc}"]
    g4 = {y_: round(YB[f"{arm}|C{C}|{y_}|{plc}"]["ret_pct"] - YB[f"static|C{C}|{y_}|post"]["ret_pct"], 2) for y_ in yrs}
    n_ok = int(sum(v >= FROZEN["G4_year_pp_min"] for v in g4.values()))
    G = {"G1": {"value": [a["p_trip"], st["p_trip"]], "pass": bool(a["p_trip"] <= st["p_trip"] * FROZEN["G1_trip_ratio_max"] + 1e-12)},
         "G2": {"value": [a["ret_mean"], st["ret_mean"], round(a["ret_mean"] - st["ret_mean"], 2)], "pass": bool(a["ret_mean"] - st["ret_mean"] >= FROZEN["G2_ret_pp_min"])},
         "G3": {"value": [a["sharpe_mean"], st["sharpe_mean"], round(a["sharpe_mean"] - st["sharpe_mean"], 3)], "pass": bool(a["sharpe_mean"] - st["sharpe_mean"] >= FROZEN["G3_sharpe_min"])},
         "G4": {"value": g4, "n_ok": n_ok, "pass": bool(n_ok >= FROZEN["G4_years_min"])}}
    G["ALL"] = all(G[g]["pass"] for g in ("G1", "G2", "G3", "G4")); return G
OUT["gates"] = {f"{arm}|C{C}|{plc}": gates_for(arm, C, plc) for arm in ("L6", "L5", "L4") for C in (C_MAIN, C_PAPER, C_LOW) for plc in ("post_bandrel", "post")}
OUT["gates_main_arm_L6"] = OUT["gates"][f"L6|C{C_MAIN}|post_bandrel"]
OUT["gates_sensitivity_absband_L6"] = OUT["gates"][f"L6|C{C_MAIN}|post"]
OUT["runtime_s"] = round(time.time() - t0, 1)
json.dump(OUT, open(ARGS.out, "w"), indent=1, ensure_ascii=False, default=float)
log("GATES main L6 bandrel", json.dumps(OUT["gates_main_arm_L6"], ensure_ascii=False))
log("GATES sens L6 absband", json.dumps(OUT["gates_sensitivity_absband_L6"], ensure_ascii=False))
for k, v in OUT["gates"].items(): log("GATE", k, "ALL" if v["ALL"] else "fail:" + ",".join(g for g in ("G1", "G2", "G3", "G4") if not v[g]["pass"]), json.dumps({g: v[g]["value"] for g in ("G1", "G2", "G3", "G4")}))
for k, v in OUT["livefn"].items(): log("LIVEFN", k, json.dumps(v))
for k, v in PAPER.items(): log("PAPER", k, json.dumps(v))
log("DONE", round(time.time() - t0, 1), "s ->", ARGS.out)
