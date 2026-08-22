"""W2b 共享模块 @jpline(2026-08-22, Session 6737834a-W2b): 两书目标权重构造(逐字取自 w2_live_replay.py / w2_wide_replay.py)、
实盘函数管线引擎(legs.apply_harvest_ema 原样 import + 在役带/止损语义)、宽书自有管线(pod_stop_arms_v3 逐字移植, 参数化收益源/成本)、
收益立方体(同一时钟, w2b_build_return_cube.py)、指标与触线概率(与 two_book_allocation.py 同式)。
被 w2_merged_book_replay.py(A)与 w2_signal_blend.py(B)import。只读数据; 写 probe_artifacts/w2b_* 缓存。

时钟(见 w2b_build_return_cube.py 头): 全部装置臂在【在役时钟】— 行标 T 的决策点 = T+1h; 在役目标用行标 T 的面板(特征至 T+1h, 与在役回放完全一致);
宽目标用 E=T 的宽面板(特征 <T, 对决策点陈旧 1h, 因果无前视); 逐名收益 R_live = T+1h→T+5h(1h kline)。
"""
import os, sys, json, time, hashlib, numpy as np
from scipy.stats import rankdata
PD = "/mnt/storage/private/work_hsy/probe_artifacts"; B = "/mnt/storage/private/work_hsy/pod_backup_2026-08-21"
MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
for p in (PD, MA, MA + "/engine/live", "/mnt/storage/private/work_hsy/quant_research_multi_asset", PD):
    sys.path.insert(0, p)
import legs as LG                      # 实盘函数(compose_book / apply_harvest_ema), probe_artifacts/legs.py = 实盘副本
import engine.replay_fullhist as RF
ANN = np.sqrt(6 * 365); NY = 2190
W_LIVE = {"king": .5952380952380952, "s2": .20238095238095238, "funding": .20238095238095238, "size": 0.}
RB = {"alpha": .5, "lambda": 1.}
COST_B = [(-0.25, 5.0, 0.85), (0.5, 6.0, 0.75), (2.0, 8.0, 0.55)]
RATE = np.array([fr * mk + (1 - fr) * tk for (mk, tk, fr) in COST_B])      # 0.5375 / 1.875 / 4.7 bps per unit traded
def sha(p):
    h = hashlib.sha256(); h.update(open(p, "rb").read()); return h.hexdigest()
def tier_of(q):
    t = np.full(len(q), 2, np.int8); fin = np.isfinite(q)
    t[fin & (q >= 1e6)] = 1; t[fin & (q >= 5e6)] = 0
    return t
def xz(v):
    ok = np.isfinite(v); out = np.full(len(v), np.nan)
    if ok.sum() >= 10: out[ok] = rankdata(v[ok]) / max(ok.sum() - 1, 1) - 0.5
    return out

# ---------------------------------------------------------------- data
class Data:
    pass
def load_all(verbose=True):
    """Loads cube + live src + wide inputs; builds (or loads cached) per-anchor targets for both books on the 9821 common anchors."""
    D = Data(); t0 = time.time()
    Z = np.load(f"{PD}/w2b_ret_cube.npz", allow_pickle=True)
    D.ts = Z["ts"].astype(np.int64); D.WSYM = [str(s) for s in Z["symbols"]]; D.NW = len(D.WSYM)
    D.R = Z["R_live"].astype(np.float32); D.R_wide = Z["R_wide"].astype(np.float32); D.cube_meta = json.loads(str(Z["meta"]))
    D.n = len(D.ts); D.yr = np.array([time.gmtime(int(t)).tm_year for t in D.ts])
    D.widx = {s: i for i, s in enumerate(D.WSYM)}
    # ---- live source
    D.src = src = RF.get_src(None, f"{PD}/king_pred_newgen.npz", f"{PD}/s2_pred_newgen.npz")
    a, yr = RF._all_anchors(src); D.a = a; D.N = src.N; D.LSYM = [str(s) for s in src.symbols]
    ts_all = np.asarray(src.ts); tss = ts_all // 1000 if (ts_all[1] - ts_all[0]) >= 3600 * 1000 else ts_all
    ats = np.array([int(tss[int(t)]) for t in a], dtype=np.int64)
    assert np.array_equal(ats, D.ts), "cube ts != live anchors"
    D.lmap = np.array([D.widx[s] for s in D.LSYM]); assert (D.lmap >= 0).all()
    D.FI, D.RVI = src.fund_idx, src.ch.index("rvol_24h")
    # ---- wide inputs
    MT = np.load(f"{B}/wide_fea_hist_meta.npz", allow_pickle=True)
    D.E_ts = MT["E_ts"].astype(np.int64); D.members = MT["members"]; D.y4m = MT["y4"]; D.qvk = MT["qvk"]
    PW = np.load(f"{B}/wide_panel_4h_hist_v2.npz", allow_pickle=True)
    assert [str(s) for s in PW["symbols"]] == D.WSYM
    D.pw_row = {int(t): j for j, t in enumerate(PW["ts"].astype(np.int64))}
    D.FN = PW["f_fund_now"]; D.IV = PW["f_fund_iv"]; D.R24 = PW["f_rev_24h"]; D.FE = PW["f_fund_ema_v1"]; D.VOL7 = PW["f_vol_7d"]
    D.SLOW = np.load(f"{B}/slow_pred_hist_oos.npy")
    D.wpos = {int(t): j for j, t in enumerate(D.E_ts)}
    D.wj = np.array([D.wpos[int(t)] for t in D.ts])            # wide meta row per common anchor
    D.pj = np.array([D.pw_row[int(t)] for t in D.ts])          # wide panel row per common anchor
    cache = f"{PD}/w2b_targets.npz"
    if os.path.exists(cache):
        C = np.load(cache, allow_pickle=True)
        for k in C.files: setattr(D, k, C[k])
        D.MSK_L = list(D.MSK_L); D.UNI_W = list(D.UNI_W)
        if verbose: print("targets cache loaded", cache, round(time.time() - t0, 1), "s", flush=True)
    else:
        build_targets(D, verbose);
        np.savez_compressed(cache, TGT_L=D.TGT_L, COMBO_L=D.COMBO_L, MSK_L=np.array(D.MSK_L, dtype=object), Y4_L=D.Y4_L, RVOL_L=D.RVOL_L,
                            TGT_W=D.TGT_W, ZW=D.ZW, SEL_W=D.SEL_W, UNI_W=np.array(D.UNI_W, dtype=object), W3=D.W3, QV=D.QV, FC=D.FC, FCOV=D.FCOV, Y4_Wm=D.Y4_Wm, VOL7A=D.VOL7A)
        if verbose: print("targets built+cached", round(time.time() - t0, 1), "s", flush=True)
    return D

def build_targets(D, verbose=True):
    src = D.src; n = D.n; N = D.N; NW = D.NW; t0 = time.time()
    # ---- live (逐字 = w2_live_replay.py 预计算段)
    TGT_L = np.zeros((n, N), np.float64); COMBO_L = np.full((n, N), np.nan, np.float32); MSK_L = []; Y4_L = np.full((n, N), np.nan, np.float64); RVOL_L = np.full((n, N), np.nan, np.float32)
    held = {"k": np.full(N, np.nan), "s": np.full(N, np.nan), "f": np.full(N, np.nan)}
    for i, t in enumerate(D.a):
        ti = int(t); m = np.asarray(src.tradeable(ti))
        if m.dtype == bool: m = np.where(m)[0]
        if i == 0 or ti % 8 == 0:
            v = np.full(N, np.nan); v[m] = src.king[ti, m]; held["k"] = v
        if i == 0 or ti % 24 == 0:
            v = np.full(N, np.nan); v[m] = src.s2[ti, m]; held["s"] = v
        if i == 0 or ti % 8 == 0:
            v = np.full(N, np.nan); v[m] = src.CH[ti, m, D.FI]; held["f"] = v
        rv = src.CH[ti, m, D.RVI].astype(float)
        r = LG.compose_book(held["k"][m], held["s"][m], held["f"][m], np.ones(len(m)), weights=W_LIVE, rvol=rv, risk_budget=RB)
        TGT_L[i, m] = np.asarray(r["target_w"], float); COMBO_L[i, m] = np.nan_to_num(np.asarray(r["combined"], float))
        MSK_L.append(m); Y4_L[i, m] = src.Y4[ti, m]; RVOL_L[i, m] = rv
        if verbose and i % 3000 == 0: print("live targets", i, "/", n, round(time.time() - t0, 1), "s", flush=True)
    D.TGT_L, D.COMBO_L, D.MSK_L, D.Y4_L, D.RVOL_L = TGT_L, COMBO_L, MSK_L, Y4_L, RVOL_L
    # ---- wide (逐字 = w2_wide_replay.py legs()/run() 的目标构造段; w3 走前 900 锚按宽书自身全锚序列)
    LRa, pos = wide_legs(D)
    TGT_W = np.zeros((n, NW), np.float32); ZW = np.full((n, NW), np.nan, np.float32); SEL_W = np.zeros((n, NW), bool); UNI_W = []; W3 = np.zeros((n, 3)); QV = np.full((n, NW), np.nan, np.float32)
    FC = np.zeros((n, NW), np.float32); FCOV = np.zeros((n, NW), bool); Y4_Wm = np.full((n, NW), np.nan, np.float32); VOL7A = np.full((n, NW), np.nan, np.float32)
    for i in range(n):
        j = D.wj[i]; jp = D.pj[i]; m = D.members[j]
        sc = {"king": D.SLOW[j, m], "rev24": -D.R24[jp, m], "fund": D.FE[jp, m]}
        w3 = wide_w3_at(LRa, pos, j); W3[i] = w3
        z = w3[0] * np.nan_to_num(xz(sc["king"])) + w3[1] * np.nan_to_num(xz(sc["rev24"])) + w3[2] * np.nan_to_num(xz(sc["fund"]))
        ok = np.isfinite(D.y4m[j, m]); qv4h = np.expm1(np.clip(D.qvk[j, m], 0, 30)) * 48
        sel = ok & (qv4h >= 2.5e5)
        assert sel.sum() >= 80, f"anchor {i}: nsel {sel.sum()} < 80 (W2 wide replay skipped such anchors; not expected on common set)"
        w = np.where(sel, z, 0.0); w -= w[sel].mean(); g = np.abs(w).sum(); assert g > 1e-9
        w /= g; capw = 2.5 / max(int(sel.sum()), 1); w = np.clip(w, -capw, capw); g2 = np.abs(w).sum()
        if g2 > 1e-9: w /= g2
        TGT_W[i, m] = w; ZW[i, m] = np.where(sel, z, np.nan); SEL_W[i, m] = sel; UNI_W.append(np.asarray(m))
        qall = np.expm1(np.clip(D.qvk[j], 0, 30)) * 48; QV[i] = np.where(np.isfinite(D.qvk[j]), qall, np.nan)
        fn = D.FN[jp]; iv = D.IV[jp]; fin = np.isfinite(fn); ivv = np.where(np.isfinite(iv) & (iv > 0), iv, 8.0)
        FC[i] = np.where(fin, fn, 0.0) * (4.0 / ivv); FCOV[i] = fin
        Y4_Wm[i, m] = D.y4m[j, m]; VOL7A[i] = D.VOL7[jp]
        if verbose and i % 3000 == 0: print("wide targets", i, "/", n, round(time.time() - t0, 1), "s", flush=True)
    D.TGT_W, D.ZW, D.SEL_W, D.UNI_W, D.W3, D.QV, D.FC, D.FCOV, D.Y4_Wm, D.VOL7A = TGT_W, ZW, SEL_W, UNI_W, W3, QV, FC, FCOV, Y4_Wm, VOL7A

def wide_legs(D):
    """逐字 = w2_wide_replay.legs(): 三腿单位 gross 截面收益(宽时钟 meta y4), 全宽锚序列, 供走前 msharpe w3."""
    LR = {l: [] for l in ("king", "rev24", "fund")}; idx = []
    for j in range(len(D.E_ts)):
        jp = D.pw_row.get(int(D.E_ts[j]))
        if jp is None: continue
        m = D.members[j]
        sc = {"king": D.SLOW[j, m], "rev24": -D.R24[jp, m], "fund": D.FE[jp, m]}
        ok = np.isfinite(D.y4m[j, m])
        for leg in LR:
            z = np.nan_to_num(xz(sc[leg])); z = np.where(ok, z, 0.0); z -= z[ok].mean() if ok.sum() else 0
            g = np.abs(z).sum()
            LR[leg].append(float((z / g * np.nan_to_num(D.y4m[j, m], nan=0.0)).sum() * 1e4) if g > 1e-9 else 0.0)
        idx.append(j)
    return {k: np.array(v) for k, v in LR.items()}, {int(j): p for p, j in enumerate(idx)}
def wide_w3_at(LRa, pos, j, look=900):
    p = pos.get(int(j), 0)
    if p < look: return np.array([1 / 3] * 3)
    sl = slice(p - look, p)
    r = np.stack([LRa["king"][sl], LRa["rev24"][sl], LRa["fund"][sl]])
    shp = np.maximum(r.mean(1) / (r.std(1) + 1e-9), 0.0)
    return shp / shp.sum() if shp.sum() > 0 else np.array([1 / 3] * 3)

# ---------------------------------------------------------------- live-function pipeline engine
def engine(D, TGT, UNI, RET, alpha=0.05, band=0.002, stop=(-0.25, 2, 42), forced_exit=True, keep_W=False, nav_scen=(15400.0 * 2, 25000.0 * 2), tag="", verbose=True, stop_pre_ema=False, keep_leavers=False):
    """在役实盘管线: apply_harvest_ema(α, 原样 import: EMA→二次 demean→L1) → 逐名止损置零(成本均价深度, 连续 need 锚, 冷却 cool; 出场 FORCED 不受带)
    → 中性免交易带 b(|Δw|≤b 不交易, 残差只摊已交易集; 出宇宙名即平) → pnl/carry/换手/分层成本/持仓统计/容量统计。
    TGT: (n, NW) 目标(单位 gross 或其线性组合, 宇宙外 0); UNI: 每锚宇宙索引; RET: (n, NW) 收益(NaN→0)。
    诊断开关(默认关 = 在役语义): stop_pre_ema=True ⇒ 止损置零施于 EMA 之前的原始目标且不强制出场(宽书自有管线语义, 慢退出);
    keep_leavers=True ⇒ 离开宇宙的名不即平, 以目标 0 留在宇宙内经 EMA 衰减退出(宽书语义)。
    返回 dict of per-anchor arrays(+ W 若 keep_W)。"""
    n, NW = D.n, D.NW; t0 = time.time()
    state = None; prev = np.zeros(NW); Pi = np.ones(NW); sh = np.zeros(NW); cb = np.zeros(NW); cnt = np.zeros(NW, int); su = np.full(NW, -1)
    cols = ["pnl", "carry", "trn", "cost_tier", "gross", "gross_pre", "nheld", "fires", "maxw", "ntraded", "unc"]
    for g_ in nav_scen: cols += [f"cap_nred_{int(g_)}", f"cap_sred_{int(g_)}", f"cap_sfloor5_{int(g_)}", f"cap_sfloor20_{int(g_)}", f"cap_sunk_{int(g_)}"]
    O = {c: np.zeros(n) for c in cols}; O["fires"] = np.zeros(n, int); O["nheld"] = np.zeros(n, int); O["ntraded"] = np.zeros(n, int)
    WS = np.zeros((n, NW), np.float32) if keep_W else None
    depth, need, cool = stop if stop else (None, 0, 0)
    for i in range(n):
        uni = UNI[i]
        if keep_leavers: uni = np.union1d(uni, np.where(np.abs(prev) > 1e-12)[0])
        syms = [D.WSYM[j] for j in uni]
        raw = np.nan_to_num(np.asarray(TGT[i][uni], float)); O["gross_pre"][i] = np.abs(raw).sum()
        bl = su > i; bl_u = bl[uni]
        if stop is not None and stop_pre_ema and bl_u.any(): raw[bl_u] = 0.0
        out = LG.apply_harvest_ema(raw, syms, state, alpha); state = out["state"]; tgt = np.asarray(out["target_w"], float)
        if stop is not None and not stop_pre_ema and bl_u.any(): tgt[bl_u] = 0.0
        inu = np.zeros(NW, bool); inu[uni] = True
        w = prev.copy(); w[~inu] = 0.0
        d = tgt - w[uni]; T = np.abs(d) > band
        if stop is not None and forced_exit and not stop_pre_ema: T |= (bl_u & (np.abs(w[uni]) > 1e-12))
        wm = w[uni].copy(); wm[T] = tgt[T]
        if T.any(): wm[T] -= wm.sum() / T.sum()
        w[uni] = wm
        y = np.nan_to_num(np.asarray(RET[i], float))
        O["pnl"][i] = float((w * y).sum() * 1e4); O["carry"][i] = float((w * D.FC[i]).sum() * 1e4); O["unc"][i] = float(np.abs(w[~D.FCOV[i]]).sum())
        dw = np.abs(w - prev); O["trn"][i] = float(dw.sum()); O["cost_tier"][i] = float((dw * RATE[tier_of(D.QV[i])]).sum())
        aw = np.abs(w); gr = float(aw.sum()); O["gross"][i] = gr; O["nheld"][i] = int((aw > 1e-12).sum()); O["maxw"][i] = float(aw.max()) if gr > 0 else 0.0; O["ntraded"][i] = int(T.sum())
        if gr > 0:
            qv = D.QV[i]; held = aw > 1e-12
            for g_ in nav_scen:
                notion = aw * g_; red = held & np.isfinite(qv) & (notion > 0.01 * qv); unk = held & ~np.isfinite(qv)
                O[f"cap_nred_{int(g_)}"][i] = int(red.sum()); O[f"cap_sred_{int(g_)}"][i] = float(aw[red].sum() / gr); O[f"cap_sunk_{int(g_)}"][i] = float(aw[unk].sum() / gr)
                O[f"cap_sfloor5_{int(g_)}"][i] = float(aw[held & (notion < 5.0)].sum() / gr); O[f"cap_sfloor20_{int(g_)}"][i] = float(aw[held & (notion < 20.0)].sum() / gr)
        if keep_W: WS[i] = w.astype(np.float32)
        # ---- stop bookkeeping (逐字 = cond_stop_tail / w2_live_replay)
        nsh = np.where(Pi > 1e-12, w / Pi, 0.0)
        same = np.sign(nsh) == np.sign(sh); add = same & (np.abs(nsh) > np.abs(sh))
        red_ = same & (~add) & (np.abs(nsh) > 1e-12); new = (~same) | (np.abs(sh) < 1e-12)
        cb = np.where(add, cb + (nsh - sh) * Pi, cb)
        with np.errstate(all="ignore"):
            ratio = np.where(np.abs(sh) > 1e-12, nsh / np.where(np.abs(sh) > 1e-12, sh, 1.0), 0.0)
        cb = np.where(red_, cb * ratio, cb); cb = np.where(new, nsh * Pi, cb); cb = np.where(np.abs(nsh) < 1e-12, 0.0, cb)
        sh = nsh
        with np.errstate(all="ignore"):
            avg = np.where(np.abs(sh) > 1e-12, cb / sh, np.nan)
            dep = np.where(np.isfinite(avg) & (Pi > 0), np.sign(sh) * (1.0 - avg / Pi), 0.0)
        if stop is not None:
            cand = (np.abs(sh) > 1e-12) & (dep <= depth) & (su <= i)
            cnt = np.where(cand, cnt + 1, 0); fire = cnt >= need
            if fire.any(): su[fire] = i + cool; cnt[fire] = 0; O["fires"][i] = int(fire.sum())
        prev = w; Pi = Pi * (1.0 + y)
        if verbose and i % 3000 == 0: print(tag, i, "/", n, round(time.time() - t0, 1), "s", flush=True)
    O["W"] = WS
    return O

# ---------------------------------------------------------------- wide book's own pipeline (pod_stop_arms_v3 逐字, 参数化收益源/成本记录)
def wide_native(D, RET_common=None, depth=-0.30, need=2, cool=42, keep_W=False, tag="W_native", verbose=True, alpha=0.1, band=2.5e-4):
    """宽书自有管线, 全宽锚序列(2021 起暖机, EMA α0.1 / 带 2.5e-4 / 止损置零于 EMA 之前 / 分层成本), 只返回共同锚(9821)的行。
    RET_common=None ⇒ 全程用 meta y4(宽时钟; 复现 W2 = nets_histv2_-30_2_42.npy); 否则共同锚用 RET_common(在役时钟), 暖机段仍 meta y4。"""
    LRa, pos = wide_legs(D); NW = D.NW; nA = len(D.E_ts); t0 = time.time()
    H = np.zeros(NW); Pi = np.ones(NW); sh = np.zeros(NW); cb = np.zeros(NW); cnt = np.zeros(NW, int); su = np.full(NW, -1)
    common_pos = {int(t): i for i, t in enumerate(D.ts)}
    cols = ["pnl", "carry", "trn", "cost_tier", "gross", "gross_member", "nheld", "fires", "maxw"]
    O = {c: np.full(D.n, np.nan) for c in cols}; WS = np.zeros((D.n, NW), np.float32) if keep_W else None
    for j in range(nA):
        jp = D.pw_row.get(int(D.E_ts[j]))
        if jp is None: continue
        m = D.members[j]
        sc = {"king": D.SLOW[j, m], "rev24": -D.R24[jp, m], "fund": D.FE[jp, m]}
        w3 = wide_w3_at(LRa, pos, j)
        z = w3[0] * np.nan_to_num(xz(sc["king"])) + w3[1] * np.nan_to_num(xz(sc["rev24"])) + w3[2] * np.nan_to_num(xz(sc["fund"]))
        ok = np.isfinite(D.y4m[j, m]); qv4h = np.expm1(np.clip(D.qvk[j, m], 0, 30)) * 48
        sel = ok & (qv4h >= 2.5e5)
        if sel.sum() < 80: continue
        w = np.where(sel, z, 0.0); w -= w[sel].mean(); g = np.abs(w).sum()
        if g < 1e-9: continue
        w /= g; capw = 2.5 / max(int(sel.sum()), 1); w = np.clip(w, -capw, capw); g2 = np.abs(w).sum()
        if g2 > 1e-9: w /= g2
        tgt = np.zeros(NW); tgt[m] = w
        if depth is not None:
            bl = su > j
            if bl.any(): tgt[bl] = 0.0
        sm = H + alpha * (tgt - H); trade = sm - H
        sm = np.where(np.abs(trade) < band, H, sm); trade = sm - H
        tr = tier_of(qv4h); tabs = np.abs(trade[m])
        cbps = sum(tabs[tr == tt].sum() * (fr * mk + (1 - fr) * tk) for tt, (mk, tk, fr) in enumerate(COST_B))
        ci = common_pos.get(int(D.E_ts[j]))
        # 记账逐字同 W2(只计成员名 m 的收益; EMA 尾巴名收益记 0): RET_common 模式仅换收益源/时钟, 不改记账范围
        if ci is not None and RET_common is not None:
            yv = np.nan_to_num(np.asarray(RET_common[ci][m], float))
        else:
            yv = np.nan_to_num(D.y4m[j, m], nan=0.0)
        yfull = np.zeros(NW); yfull[m] = yv
        fnow = np.nan_to_num(D.FN[jp, m], nan=0.0); ivv = D.IV[jp, m]; ivv = np.where(np.isfinite(ivv) & (ivv > 0), ivv, 8.0)
        car = (sm[m] * fnow * (4.0 / ivv)).sum() * 1e4
        pnl_raw = float((sm[m] * yv).sum() * 1e4)
        if ci is not None:
            O["pnl"][ci] = pnl_raw; O["carry"][ci] = float(car); O["trn"][ci] = float(np.abs(trade).sum()); O["cost_tier"][ci] = float(cbps)
            O["gross"][ci] = float(np.abs(sm).sum()); O["gross_member"][ci] = float(np.abs(sm[m]).sum()); O["nheld"][ci] = int((np.abs(sm) > 1e-12).sum()); O["maxw"][ci] = float(np.abs(sm).max())
            if keep_W: WS[ci] = sm.astype(np.float32)
        nsh = np.where(Pi > 1e-12, sm / Pi, 0.0)
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
        fires_i = 0
        if depth is not None:
            cand = (np.abs(sh) > 1e-12) & (dep <= depth) & (su <= j)
            cnt = np.where(cand, cnt + 1, 0); fr2 = cnt >= need
            if fr2.any(): su[fr2] = j + cool; cnt[fr2] = 0; fires_i = int(fr2.sum())
        if ci is not None: O["fires"][ci] = fires_i
        H = sm; Pi = Pi * (1.0 + yfull)
        if verbose and j % 3000 == 0: print(tag, j, "/", nA, round(time.time() - t0, 1), "s", flush=True)
    assert np.isfinite(O["pnl"]).all(), "wide native: some common anchors not produced"
    O["W"] = WS
    return O

# ---------------------------------------------------------------- metrics
def sharpe(x): s = x.std(ddof=1); return float(x.mean() / s * ANN) if s > 0 else float("nan")
def maxdd_nav(x, g):
    nav = np.cumprod(1 + g * x / 1e4); return float(-(nav / np.maximum.accumulate(nav) - 1).min())
def es(x, q=0.05): k = max(1, int(len(x) * q)); return float(np.sort(x)[:k].mean())
def agg(x, k): m = (len(x) // k) * k; return x[:m].reshape(-1, k).sum(1)
def series_stats(x, yr, G=2.0):
    yrs = sorted(set(yr.tolist()))
    return {"mean_at_G": round(float(x.mean() * G), 4), "sd_pg": round(float(x.std(ddof=1)), 3), "sharpe": round(sharpe(x), 3),
            "by_year_sharpe": {int(y): round(sharpe(x[yr == y]), 3) for y in yrs}, "by_year_mean_at_G": {int(y): round(float(x[yr == y].mean() * G), 3) for y in yrs},
            "sharpe_2022_23": round(sharpe(x[yr <= 2023]), 3), "sharpe_2024_26": round(sharpe(x[yr >= 2024]), 3), "sharpe_ex2026": round(sharpe(x[yr <= 2025]), 3),
            "maxDD_nav_at_G": round(maxdd_nav(x, G), 4), "ES5_pg": round(es(x), 2), "ES1_pg": round(es(x, 0.01), 2),
            "sharpe_daily_agg": round(float(agg(x, 6).mean() / agg(x, 6).std(ddof=1) * np.sqrt(365)), 3), "sharpe_weekly_agg": round(float(agg(x, 42).mean() / agg(x, 42).std(ddof=1) * np.sqrt(365 / 7)), 3)}
def trip(x, g, shr=1.0, seed=11, Lb=180, reps=2000):
    x = x - x.mean() * (1 - shr); rng = np.random.RandomState(seed); nb = len(x) // Lb; nbk = NY // Lb + 1
    hp = 0; hs = 0; ann = []
    for _ in range(reps):
        idx = rng.randint(0, nb, nbk); path = np.concatenate([x[i * Lb:(i + 1) * Lb] for i in idx])[:NY] * g / 1e4
        cum = np.cumprod(1 + path); dd = cum / np.maximum.accumulate(cum) - 1
        hp += dd.min() <= -0.25; hs += cum.min() <= 0.75; ann.append(cum[-1] - 1)
    return {"P_peakDD_-25%": round(hp / reps, 4), "P_fromstart_-25%": round(hs / reps, 4), "ann_median": round(float(np.median(ann)), 3), "ann_p5": round(float(np.percentile(ann, 5)), 3)}
def q4_masks(Lx, mkt, btc, yr):
    """Q4 子样本(与 two_book_allocation.py 同定义): a 在役最坏五分位锚; b 在役 42 锚块最坏五分位; c 等权市场最差五分位; d 山寨−BTC 价差最高五分位; e |市场| 对在役最差档."""
    n = len(Lx); Q = {}
    Q["a_live_worst_quintile_anchor"] = Lx <= np.percentile(Lx, 20)
    bl = agg(Lx, 42); qb = np.percentile(bl, 20); mB = np.zeros(n, bool)
    for b, v in enumerate(bl):
        if v <= qb: mB[b * 42:(b + 1) * 42] = True
    Q["b_live_worst_quintile_weekly_block"] = mB
    spr = mkt - btc
    for nm, v in (("c_mkt_ew", mkt), ("d_alt_minus_btc_spread", spr), ("e_abs_mkt", np.abs(mkt))):
        v2 = np.where(np.isfinite(v), v, np.nan); edges = np.nanpercentile(v2, [20, 40, 60, 80]); qi = np.digitize(v2, edges)
        means = [float(Lx[qi == k].mean()) for k in range(5)]; worst = int(np.argmin(means))
        Q[f"{nm}_q{worst}_worst_for_live"] = (qi == worst)
    return Q
def boot_delta_sharpe(x, y, Lb=42, reps=2000, seed=7):
    """配对块自助 ΔSharpe(x − y)."""
    rng = np.random.RandomState(seed); n = len(x); nb = n // Lb; d = []
    for _ in range(reps):
        idx = rng.randint(0, nb, nb); sel = np.concatenate([np.arange(i * Lb, (i + 1) * Lb) for i in idx])
        d.append(sharpe(x[sel]) - sharpe(y[sel]))
    d = np.array(d)
    return {"mean": round(float(d.mean()), 3), "CI95": [round(float(np.percentile(d, 2.5)), 3), round(float(np.percentile(d, 97.5)), 3)], "P_gt_0": round(float((d > 0).mean()), 3), "P_ge_0.10": round(float((d >= 0.10).mean()), 3), "P_le_-0.10": round(float((d <= -0.10).mean()), 3)}
