"""W3 执行器口径全史回放(E-0825-A 修正装置, 2026-08-25)。同跑双账: 文件口径(必须与 pod_backup 逐元素相等=原路径无扰动证明)
+ 执行器口径(每锚 reshape_after_withhold 语义: 非零集均匀移位 redemean + L1 恢复原 gross; 蓝本 dl_quant_live/signal/legs.py:124;
近似=无历史 withhold 集, 持仓演化按 reshaped 序列 HR, 换手按 trr)。读法冻结先于数字: 主读 = net_ex/sharpe_ex 2024on 与逐年 vs 文件口径,
Δ=净多溢价+换手差; funding 3.1× 靶向检验另行。原 W2 头注:
 W2 两书配置装置 · 宽书逐锚序列生成器 @jpline(2026-08-22, Session 6737834a-W2)。
书构造 = pod_stop_arms_v3.py(devices_2026-08-21, 权威构造 = pod_legweight_arms 逐字同构)逐字移植, 输入改指 jpline 上的 pod 备份
/mnt/storage/private/work_hsy/pod_backup_2026-08-21/(META=wide_fea_hist_meta.npz, PANEL=wide_panel_4h_hist_v2.npz(正确 carry: f_fund_iv/f_fund_ema_v1),
KING=slow_pred_hist_oos.npy 按年扩张 OOS 折 2022-26)。臂: S0 无止损 / d30_n2_c42(止损层)。
新增逐锚仪器(不改书): 毛 pnl / carry / 成本 / gross_total(|sm| 全向量合计, 与 §J-bis 口径同) / gross_member(当锚成员内) / gross_sel /
nsel / 成员数 / 当锚触发数 / 三腿贡献(LEGC 同式) / w3 腿权; 权重向量 sm(float32)供重叠名核算。
复现收据: d30_n2_c42 的 net 必须与 pod_backup/nets_histv2_-30_2_42.npy 逐元素相等(maxabs<1e-6), S0 同 nets_histv2_0_0_0.npy。
输出: probe_artifacts/w10_ablation_series.npz + w10_ablation_summary.json。只读数据, 不碰实盘仓。
"""
import json, time, sys, os
LOOK = int(os.environ.get("LOOK", "900"))          # 腿权重回看窗(锚)
WRULE = os.environ.get("WRULE", "msharpe")            # msharpe | eq | iv
CAL = os.environ.get("CAL", "simple")                 # simple = 交易所记账(y -> expm1)
assert CAL in ("simple", "log"), (
    f"CAL 必须是 simple|log(收到 {CAL!r})。simple=交易所简单收益(expm1), log=对数收益(仅诊断用)。"
    "'exec' 不是有效值 —— E-0826-C: 曾被当作'执行器口径'传入, 实际落进对数分支, 污染 8 个臂并驱动一次错误撤回。")
LEGS = os.environ.get("LEGS", "111")                  # 腿掩码 king/rev24/fund; 关掉的腿权重置零后在剩余腿上重归一
PHI = float(os.environ.get("PHI", "0.45"))            # 混合权重: blend = (1-PHI)*king + PHI*F10
FSEED = os.environ.get("FSEED", "42")                 # F10 种子(walk-forward OOS 预测)
import numpy as np
from scipy.stats import rankdata
B = "pod_backup_2026-08-21"; PD = "probe_artifacts"
W3FIX = os.environ.get("W3FIX")   # 固定席位口径(PREREG_universe_dyn §2), 白名单单值
if W3FIX is not None: assert W3FIX == "0.21,0,0.79", f"W3FIX 白名单外: {W3FIX}"
MEMBERS_TOPN = int(os.environ.get("MEMBERS_TOPN", "0"))   # >0: 按 qvk 逐锚重建 top-N 候选集(扩展臂); 0 = 用 meta members(正典, 逐位同)
assert MEMBERS_TOPN in (0, 300, 400, 500, 600, 829), f"MEMBERS_TOPN 白名单外: {MEMBERS_TOPN}"
FTRIM = os.environ.get("FTRIM", "off"); assert FTRIM in ("off", "zero"), FTRIM   # 部署态 FTRIM(pre-z 排除 rn8<=-10bp 空头, 两链), 与 w10_ftrim_band pre/zero/(-1.0,-0.0010] 同构
SEATNET = int(os.environ.get("SEATNET", "0")); assert SEATNET in (0, 1)
SEATF10 = int(os.environ.get("SEATF10", "0")); assert SEATF10 in (0, 1)   # T1: F10 链用 F10 自己的 msharpe 席位(四腿腿收益)
KTAIL = int(os.environ.get("KTAIL", "0")); assert KTAIL in (0, 1)         # T2: king 作尾部否决(fund 多尾中 king 秩底 20% / 空尾中 king 秩顶 20% 置零)
KMOD = float(os.environ.get("KMOD", "0")); assert KMOD in (0.0, 0.5)       # T3: z ×= (1 + KMOD·xz(king))
KMOD_AGREE = float(os.environ.get("KMOD_AGREE", "0")); assert KMOD_AGREE in (0.0, 0.5)
KMOD_F10 = float(os.environ.get("KMOD_F10", "0")); assert KMOD_F10 in (0.0, 0.5)   # T3c: z ×= (1 + KMOD_F10·xz(F10)) —— DL 作调节器(两链)
KMOD_L = float(os.environ.get("KMOD_L", "0.5")); assert KMOD_L in (0.25, 0.5, 1.0)   # T3 形状核: KMOD 的实际系数(预注册取 0.5; 0.25/1.0 只作形状检查, 不用于选型)   # T3b(一致性形): z += KMOD_AGREE·|z|·xz(king) —— king 同向放大、反向缩小   # X1(PREREG_legs_factors): 席位用净腿收益(纯价格 − 腿书 carry)
FUNDSCALE = int(os.environ.get("FUNDSCALE", "0")); assert FUNDSCALE in (0, 1)   # X3: fund z × clip(σ_fund/σ_ref, 0.5, 1)(信息臂)
FEMAT_NPZ = os.environ.get("FEMAT_NPZ")   # X2: fund 腿分矩阵注入(ts×symbols 对齐断言), 替代 f_fund_ema_v1
TRADE_TOPN = int(os.environ.get("TRADE_TOPN", "0"))   # >0: 成交集限于当锚 qvk 排名前 N(z 归一基仍为 members): 分离"归一基变宽"与"可交易名增加"两条通道
assert TRADE_TOPN in (0, 400), f"TRADE_TOPN 白名单外: {TRADE_TOPN}"
REF_SKIP = int(os.environ.get("REF_SKIP", "0")); assert REF_SKIP in (0, 1)   # combo_recheck 2026-09-04: 1 = skip pod_backup reference parity (port stubs are 144-byte placeholders); self-reported in _CFG
_CFG = {"REF_SKIP": REF_SKIP, "KMOD_F10": KMOD_F10, "KMOD_L": KMOD_L, "KMOD_AGREE": KMOD_AGREE, "SEATF10": SEATF10, "KTAIL": KTAIL, "KMOD": KMOD, "SEATNET": SEATNET, "FUNDSCALE": FUNDSCALE, "FEMAT_NPZ": FEMAT_NPZ, "SLOW_NPY": os.environ.get("SLOW_NPY"), "W3FIX": W3FIX, "MEMBERS_TOPN": MEMBERS_TOPN, "TRADE_TOPN": TRADE_TOPN, "FTRIM": FTRIM, "UMASK_NPZ": os.environ.get("UMASK_NPZ"), "LOOK": LOOK, "WRULE": WRULE, "CAL": CAL, "LEGS": LEGS, "PHI": PHI, "FSEED": FSEED,
        "FPRED": os.environ.get("FPRED", "(default f10_V2MAIN_s{FSEED})")}
print("CONFIG " + json.dumps(_CFG), flush=True)   # E-0826-C/D: 装置必须自报全部生效配置
t0 = time.time()
MT = np.load(f"{B}/wide_fea_hist_meta.npz", allow_pickle=True)
E_ts = MT["E_ts"].astype(np.int64); members = MT["members"]; y4 = MT["y4"]; qvk = MT["qvk"]
if MEMBERS_TOPN > 0:   # 扩展臂: 逐锚按当锚 qvk 排名取前 N(era-synchronous: 只用当锚已知的报价额), 与 meta 排序口径同源
    _mem2 = np.empty(len(E_ts), dtype=object)
    for _i in range(len(E_ts)):
        _q = np.nan_to_num(qvk[_i], nan=-1.0); _ord = np.argsort(-_q); _ord = _ord[_q[_ord] > -0.5]
        _mem2[_i] = np.sort(_ord[:MEMBERS_TOPN]).astype(np.int64)
    members = _mem2
    print(f"MEMBERS_TOPN={MEMBERS_TOPN}: members rebuilt from qvk ranking", flush=True)
yrs = np.array([time.gmtime(int(t)).tm_year for t in E_ts]); nA = len(E_ts); NW = 829
PW = np.load(f"{B}/wide_panel_4h_hist_v2.npz", allow_pickle=True)
pw_row = {int(t): j for j, t in enumerate(PW["ts"].astype(np.int64))}
FN = PW["f_fund_now"]; IV = PW["f_fund_iv"] if "f_fund_iv" in PW else np.full_like(PW["f_fund_now"], 8.0); R24 = PW["f_rev_24h"]; FE = PW["f_fund_ema_v1"]
if FEMAT_NPZ:
    _fz = np.load(FEMAT_NPZ, allow_pickle=True)
    assert [str(x) for x in _fz["symbols"]] == [str(x) for x in PW["symbols"]], "FEMAT symbols mismatch"
    assert np.array_equal(_fz["ts"].astype(np.int64), PW["ts"].astype(np.int64)), "FEMAT ts mismatch"
    FE = np.asarray(_fz["mat"], dtype=float); print(f"FEMAT injected: {FEMAT_NPZ} finite {np.isfinite(FE).mean():.3f}", flush=True)
_IVf = np.where(np.isfinite(IV) & (IV > 0), IV, 8.0); _RN8 = np.nan_to_num(FN, nan=0.0) * (8.0 / _IVf)   # 8h 当量费率(全宽)
if FUNDSCALE:
    _sig = np.array([np.std(_RN8[j][np.isfinite(FN[j])]) if np.isfinite(FN[j]).sum() > 50 else np.nan for j in range(len(PW["ts"]))]) * 1e4
    _sref = np.array([np.nanmedian(_sig[max(0, j - 4380):j + 1]) if j >= 1000 else np.nan for j in range(len(_sig))])
    FUNDSCALE_ROW = np.clip(_sig / _sref, 0.5, 1.0); FUNDSCALE_ROW = np.where(np.isfinite(FUNDSCALE_ROW), FUNDSCALE_ROW, 1.0); print(f"FUNDSCALE: 均 {np.nanmean(FUNDSCALE_ROW):.3f}", flush=True)
_um = os.environ.get("UMASK_NPZ")
if _um:  # PREREG addendum §B: 宇宙臂 — 成员集按掩码收缩(只缩不扩, meta top-400 为天花板)
    _uz = np.load(_um, allow_pickle=True)
    assert [str(x) for x in _uz["symbols"]] == [str(x) for x in PW["symbols"]], "umask symbols mismatch"
    _umap = {int(t): k for k, t in enumerate(_uz["ts"].astype(np.int64))}
    _UM = np.asarray(_uz["mask"])
    _pwts_u = PW["ts"].astype(np.int64)
    UMASK_ROW = {}
    for _j, _t in enumerate(_pwts_u):
        _k = _umap.get(int(_t))
        if _k is not None: UMASK_ROW[_j] = _UM[_k]
    print(f"UMASK injected: {_um}", flush=True)
else:
    UMASK_ROW = None if "f_fund_ema_v1" in PW else PW["f_fund_ema"]
WSYM = [str(s) for s in PW["symbols"]]
SLOW_NPY = os.environ.get("SLOW_NPY")   # 滚动月度 OOS king 预测覆盖(RUNBOOK §8; PREREG_allweather 后续): 形状必须与 slow_pred_hist_oos 同, 否则拒绝
SLOW = np.load(f"{B}/slow_pred_hist_oos.npy") if not SLOW_NPY else np.load(SLOW_NPY)
if SLOW_NPY:
    _ref = np.load(f"{B}/slow_pred_hist_oos.npy", mmap_mode="r"); assert SLOW.shape == _ref.shape, f"SLOW_NPY 形状 {SLOW.shape} != 正典 {_ref.shape}"; print(f"SLOW override: {SLOW_NPY} finite {np.isfinite(SLOW).mean():.3f}", flush=True)
# ★★ 严格因果: 只用 walk-forward OOS 预测(四折 + 60 锚 embargo, 只写测试折)。
#    全史重训件 models/f10_live_s*.pt **不参与任何历史评估** —— 它见过全部历史。
F10P = np.full((nA, NW), np.nan, np.float32)
if PHI > 0:
    _R2 = "."
    _fp = os.environ.get("FPRED", f"f10_V2MAIN_s{FSEED}.npy")   # 可换任意 OOS 预测(如 LGBM 弹药档)
    _pd = np.load(f"{_R2}/f8_2026-08-22/preds/{_fp}")
    print(f"F10 leg source: {_fp}", flush=True)
    _TG = np.load(f"{_R2}/dlw_2026-08-22/data/dlw_targets.npz", allow_pickle=True)
    _dts = _TG["E_ts"].astype(np.int64); _dsy = [str(x) for x in _TG["symbols"]]
    _rmap = {int(t): k for k, t in enumerate(_dts)}
    _cmap = {s: k for k, s in enumerate(_dsy)}
    _cols = np.array([_cmap.get(s, -1) for s in WSYM], np.int64)     # 回放符号序 → dlw 列
    _okc = _cols >= 0
    _nrow = 0
    for _i in range(nA):
        _k = _rmap.get(int(E_ts[_i]))
        if _k is None:
            continue
        F10P[_i, _okc] = _pd[_k, _cols[_okc]]
        _nrow += 1
    print(f"F10 OOS preds aligned: rows {_nrow}/{nA}, cols {_okc.sum()}/{NW}, "
          f"finite {np.isfinite(F10P).mean():.4f}", flush=True)
def xz(v):
    ok = np.isfinite(v); out = np.full(len(v), np.nan)
    if ok.sum() >= 10: out[ok] = rankdata(v[ok]) / max(ok.sum() - 1, 1) - 0.5
    return out
COST_B = [(-0.25, 5.0, 0.85), (0.5, 6.0, 0.75), (2.0, 8.0, 0.55)]
def tier_of(q):
    t = np.full(len(q), 2, np.int8); t[q >= 1e6] = 1; t[q >= 5e6] = 0
    return t
def legs(SLOW):
    LR = {l: [] for l in ("king", "rev24", "fund", "f10")}; idx = []
    for i in range(nA):
        j = pw_row.get(int(E_ts[i]))
        if j is None: continue
        m = members[i]
        if UMASK_ROW is not None:
            _mk = UMASK_ROW.get(j)
            if _mk is not None: m = m[_mk[m]]
        sc = {"king": SLOW[i, m], "rev24": -R24[j, m], "fund": FE[j, m], "f10": (F10P[i, m] if SEATF10 else np.full(len(m), np.nan))}
        ok = np.isfinite(y4[i, m])
        for leg in LR:
            z = np.nan_to_num(xz(sc[leg])); z = np.where(ok, z, 0.0); z -= z[ok].mean() if ok.sum() else 0
            g = np.abs(z).sum()
            _yy = np.nan_to_num(y4[i, m], nan=0.0)
            if CAL == "simple":
                _yy = np.expm1(_yy)
            _lr = float((z / g * _yy).sum() * 1e4) if g > 1e-9 else 0.0
            if SEATNET and g > 1e-9:   # X1: 减去该腿单位 gross 书的 4h carry(多头付正费率), bps
                _lr -= float((z / g * np.nan_to_num(FN[j, m], nan=0.0) * (4.0 / _IVf[j, m])).sum() * 1e4)
            LR[leg].append(_lr)
        idx.append(i)
    return {k: np.array(v) for k, v in LR.items()}, {int(i): p for p, i in enumerate(idx)}
W3FC = None
def run(SLOW, LRa, pos, depth, need, cool, look=900):
    def w3_at(i):
        if W3FIX is not None:
            return np.array([float(x) for x in W3FIX.split(",")])
        if WRULE == "eq":
            _e = np.array([1.0 if c == "1" else 0.0 for c in LEGS])
            return _e / max(_e.sum(), 1.0)
        p = pos.get(int(i), 0)
        if p < LOOK: return np.array([1/3]*3)
        sl = slice(p - LOOK, p)              # ★ 严格因果: 只用锚 i 之前的腿收益
        if SEATF10:   # T1: f10 腿的席位由它自己的腿收益决定; 返回 kc 三腿席位, fc 席位放入 W3FC 全局
            global W3FC
            r4 = np.stack([LRa["king"][sl], LRa["rev24"][sl], LRa["fund"][sl], LRa["f10"][sl]])
            shp4 = r4.mean(1) / (r4.std(1) + 1e-9); shp4 = np.maximum(shp4, 0.0)
            mk = np.array([1.0 if c == "1" else 0.0 for c in LEGS])
            wk = np.array([shp4[0], shp4[1], shp4[2]]) * mk; wk = wk / wk.sum() if wk.sum() > 0 else np.array([1/3]*3)
            wf = np.array([shp4[3], shp4[1], shp4[2]]) * mk; wf = wf / wf.sum() if wf.sum() > 0 else np.array([1/3]*3)
            W3FC = wf
            return wk
        r = np.stack([LRa["king"][sl], LRa["rev24"][sl], LRa["fund"][sl]])
        if WRULE == "iv":
            iv = 1.0 / (r.std(1) + 1e-9)
            return iv / iv.sum()
        shp = np.maximum(r.mean(1) / (r.std(1) + 1e-9), 0.0)
        w_ = shp / shp.sum() if shp.sum() > 0 else np.array([1/3] * 3)
        if LEGS != "111":
            msk = np.array([1.0 if c == "1" else 0.0 for c in LEGS])
            w_ = w_ * msk
            w_ = w_ / w_.sum() if w_.sum() > 1e-12 else msk / max(msk.sum(), 1.0)
        return w_
    H = np.zeros(NW); HR = np.zeros(NW); Pi = np.ones(NW); sh = np.zeros(NW); cb = np.zeros(NW)
    HF = np.zeros(NW); HB = np.zeros(NW)      # F10 书自己的 EMA 态 / 上一锚的混合书
    cnt = np.zeros(NW, int); su = np.full(NW, -1)
    rec = []; WS = []
    for i in range(nA):
        j = pw_row.get(int(E_ts[i]))
        if j is None: continue
        m = members[i]
        if UMASK_ROW is not None:
            _mk = UMASK_ROW.get(j)
            if _mk is not None: m = m[_mk[m]]
        sc = {"king": SLOW[i, m], "rev24": -R24[j, m], "fund": FE[j, m]}
        w3 = w3_at(i)
        _fs = (FUNDSCALE_ROW[j] if FUNDSCALE else 1.0)
        z = w3[0]*np.nan_to_num(xz(sc["king"])) + w3[1]*np.nan_to_num(xz(sc["rev24"])) + w3[2]*_fs*np.nan_to_num(xz(sc["fund"]))
        if KMOD > 0: z = z * (1.0 + KMOD_L * np.nan_to_num(xz(sc["king"])))   # T3 乘性调制(系数 KMOD_L, 默认 0.5)
        if KMOD_F10 > 0: z = z * (1.0 + KMOD_F10 * np.nan_to_num(xz(F10P[i, m])))   # T3c DL 调节
        if KMOD_AGREE > 0: z = z + KMOD_AGREE * np.abs(z) * np.nan_to_num(xz(sc["king"]))   # T3b 一致性调制
        if KTAIL:   # T2 king 尾部否决: 多尾(z 顶 20%)中 king 秩底 20% 与 空尾(z 底 20%)中 king 秩顶 20% 置零
            _zk = np.nan_to_num(xz(sc["king"])); _lo, _hi = np.quantile(z, [0.2, 0.8]); _klo, _khi = np.quantile(_zk, [0.2, 0.8])
            z = np.where(((z >= _hi) & (_zk <= _klo)) | ((z <= _lo) & (_zk >= _khi)), 0.0, z)
        if FTRIM == "zero":
            _fnp = FN[j, m] * (8.0 / np.where(IV[j, m] > 0, IV[j, m], 8.0)); _fnp = np.where(np.isfinite(_fnp), _fnp, 0.0)
            z = np.where((z < 0) & (_fnp <= -0.0010), 0.0, z)
        ok = np.isfinite(y4[i, m]); qv4h = np.expm1(np.clip(qvk[i, m], 0, 30)) * 48
        sel = ok & (qv4h >= 2.5e5)
        if TRADE_TOPN > 0:
            _qi = np.nan_to_num(qvk[i], nan=-1.0); _rk = np.empty(NW, int); _rk[np.argsort(-_qi)] = np.arange(NW); sel = sel & (_rk[m] < TRADE_TOPN)
        if sel.sum() < 80: continue
        w = np.where(sel, z, 0.0)
        w[sel] -= w[sel].mean()   # DEMEAN-FIX: 只在 sel 子集内去均值, 非 sel 保持 0(原代码把标量减到全部成员上, 使不合格名各得 -mu 形成等权多头篮)
        g = np.abs(w).sum()
        if g < 1e-9: continue
        w /= g; capw = 2.5 / max(int(sel.sum()), 1); w = np.clip(w, -capw, capw)
        g2 = np.abs(w).sum()
        if g2 > 1e-9: w /= g2
        tgt = np.zeros(NW); tgt[m] = w
        if depth is not None:
            bl = su > i
            if bl.any(): tgt[bl] = 0.0
        sm = H + 0.1 * (tgt - H); trade = sm - H
        sm = np.where(np.abs(trade) < 2.5e-4, H, sm); trade = sm - H
        # W6: 不合格流动性名强制出场(与 EXIT 同机制, 不受带约束) —— 只有目标层 demean 修复
        # 清不掉存量: 每名 EMA 步长 < 带阈 ⇒ 历史篮子被带永久冻结(G1 实测 15.7%→15.2%)。
        _nonsel = np.zeros(NW, bool); _nonsel[m[~sel]] = True
        sm = np.where(_nonsel, 0.0, sm); trade = sm - H
        # ★ F10 书: 同一条链(xz→sel→demean→L1→cap→L1→EMA→带→强制出场), 自己的 EMA 态 HF
        if PHI > 0:
            # ★★ 更正(2026-08-25): F10 书 = **同一本三腿书, 只把 king 腿换成 F10 分数**
            #    (与侧车 sidecar_blend.py:171 逐字同构: w3[0]*zf + w3[1]*rev24 + w3[2]*fund)。
            #    此前用纯 DL 分数单独建书 = 剥掉了它的 funding 与 rev24 腿 ⇒ carry 归零、换手翻倍,
            #    是装置错误不是模型缺陷。preds 存的是 mdl.f(x) 原始分数(f10_train.py:337), 必须
            #    自己补上另外两条腿。
            _w3f = (W3FC if (SEATF10 and W3FC is not None) else w3)
            _zf = (_w3f[0] * np.nan_to_num(xz(F10P[i, m]))
                   + _w3f[1] * np.nan_to_num(xz(sc["rev24"]))
                   + _w3f[2] * np.nan_to_num(xz(sc["fund"])))
            if KMOD > 0: _zf = _zf * (1.0 + KMOD_L * np.nan_to_num(xz(sc["king"])))
            if KMOD_F10 > 0: _zf = _zf * (1.0 + KMOD_F10 * np.nan_to_num(xz(F10P[i, m])))
            if KMOD_AGREE > 0: _zf = _zf + KMOD_AGREE * np.abs(_zf) * np.nan_to_num(xz(sc["king"]))
            if KTAIL:
                _zk = np.nan_to_num(xz(sc["king"])); _lo, _hi = np.quantile(_zf[np.isfinite(_zf)], [0.2, 0.8]); _klo, _khi = np.quantile(_zk, [0.2, 0.8])
                _zf = np.where(((_zf >= _hi) & (_zk <= _klo)) | ((_zf <= _lo) & (_zk >= _khi)), 0.0, _zf)
            if FTRIM == "zero":
                _zf = np.where((_zf < 0) & (_fnp <= -0.0010), 0.0, _zf)
            _wf = np.where(sel, _zf, 0.0)
            if sel.any():
                _wf[sel] -= _wf[sel].mean()
            _gf = np.abs(_wf).sum()
            if _gf > 1e-9:
                _wf = _wf / _gf
                _wf = np.clip(_wf, -capw, capw)
                _g2f = np.abs(_wf).sum()
                if _g2f > 1e-9:
                    _wf = _wf / _g2f
                _tgtf = np.zeros(NW); _tgtf[m] = _wf
                _smf = HF + 0.1 * (_tgtf - HF)
                _trf = _smf - HF
                _smf = np.where(np.abs(_trf) < 2.5e-4, HF, _smf)
                _smf = np.where(_nonsel, 0.0, _smf)
                if depth is not None:
                    _blf = su > i
                    if _blf.any(): _smf[_blf] = 0.0
            else:
                _smf = HF.copy()
            HF = _smf
            smb = (1.0 - PHI) * sm + PHI * _smf
        else:
            smb = sm
        _smk = sm                     # ★ king 书自己的 sm 必须留住: 它的 EMA 态独立推进
        sm = smb                      # 此后一切记账(盈亏/成本/carry/深度)都在混合书上
        trade = sm - HB
        nz = np.abs(sm) > 1e-12
        smr = sm.copy()
        if nz.any():
            smr[nz] -= smr[nz].mean()
            _g0 = np.abs(sm).sum(); _g1 = np.abs(smr).sum()
            if _g1 > 1e-9:
                smr *= _g0 / _g1
        trr = smr - HR
        tr = tier_of(qv4h); tabs = np.abs(trade[m])
        cbps = sum(tabs[tr == tt].sum() * (fr * mk + (1 - fr) * tk) for tt, (mk, tk, fr) in enumerate(COST_B))
        yv = np.nan_to_num(y4[i, m], nan=0.0)
        if CAL == "simple":
            yv = np.expm1(yv)
        fnow = np.nan_to_num(FN[j, m], nan=0.0); ivv = IV[j, m]; ivv = np.where(np.isfinite(ivv) & (ivv > 0), ivv, 8.0)
        car = (sm[m] * fnow * (4.0 / ivv)).sum() * 1e4
        pnl_raw = float((sm[m] * yv).sum() * 1e4)
        legc = []
        for leg in ("king", "rev24", "fund"):
            zz = np.nan_to_num(xz(sc[leg])); gl = np.abs(zz).sum()
            legc.append(float(w3[{"king": 0, "rev24": 1, "fund": 2}[leg]] * (zz / gl * yv).sum() * 1e4) if gl > 1e-9 else 0.0)
        fires_i = 0
        # 成本均价深度(全宇宙价格路径)
        yfull = np.zeros(NW); yfull[m] = yv
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
        if depth is not None:
            cand = (np.abs(sh) > 1e-12) & (dep <= depth) & (su <= i)
            cnt = np.where(cand, cnt + 1, 0); fr2 = cnt >= need
            if fr2.any(): su[fr2] = i + cool; cnt[fr2] = 0; fires_i = int(fr2.sum())
        pnl_r = float((smr[m] * yv).sum() * 1e4)
        car_r = float((smr[m] * fnow * (4.0 / ivv)).sum() * 1e4)
        tabs_r = np.abs(trr[m])
        cbps_r = sum(tabs_r[tr == tt].sum() * (fr * mk + (1 - fr) * tk) for tt, (mk, tk, fr) in enumerate(COST_B))
        netlong = float(sm.sum() / max(np.abs(sm).sum(), 1e-9))
        gm = float(np.abs(sm[m]).sum()); gsel = float(np.abs(sm[m][sel]).sum()); gt = float(np.abs(sm).sum())
        rec.append((int(E_ts[i]), float(pnl_raw - car - cbps), pnl_raw, float(car), float(cbps), gt, gm, gsel, int(sel.sum()), int(len(m)), fires_i,
                    legc[0], legc[1], legc[2], float(w3[0]), float(w3[1]), float(w3[2]), float(np.abs(trade).sum()),
                    float(pnl_r - car_r - cbps_r), pnl_r, car_r, float(cbps_r), netlong))
        WS.append(sm.astype(np.float32))
        H = _smk if PHI > 0 else sm      # king 书 EMA 态独立推进(φ=0 时二者同一)
        HB = sm; HR = smr; Pi = Pi * (1.0 + yfull)
        if i % 2000 == 0: print("run depth", depth, i, "/", nA, round(time.time() - t0, 1), "s", flush=True)
    return np.array(rec), np.stack(WS)
LRa, pos = legs(SLOW); print("legs done", round(time.time() - t0, 1), "s", flush=True)
ARMS = [("S0", None, 0, 0, "nets_histv2_0_0_0.npy"), ("d30_n2_c42", -0.30, 2, 42, "nets_histv2_-30_2_42.npy")]
COLS = ["ts", "net", "pnl", "carry", "cost", "gross_total", "gross_member", "gross_sel", "nsel", "nmember", "fires", "leg_king", "leg_rev24", "leg_fund", "w3_king", "w3_rev24", "w3_fund", "turnover", "net_ex", "pnl_ex", "carry_ex", "cost_ex", "netlong"]
out = {}; save = {}
for nm, d, n_, c, reff in ARMS:
    R, WS = run(SLOW, LRa, pos, d, n_, c)
    ref = np.load(f"{B}/{reff}")
    if REF_SKIP:   # combo_recheck: reference parity skipped on request (REF_SKIP=1)
        print(f"NOTE {nm}: REF_SKIP=1, reference parity vs pod_backup skipped", flush=True); ref = None
    elif WRULE == "msharpe" and LOOK == 900 and LEGS == "111":
        # 参照平价只对基线配置有意义(它验的是"本装置能复现 pod_backup")
        assert ref.shape[0] == R.shape[0], f"{nm}: n {R.shape[0]} vs ref {ref.shape[0]}"
    elif ref.shape[0] != R.shape[0]:
        # 非基线臂锚数可合法不同(如 IV 把权重压到早期无数据的腿上 ⇒ 合成分数全零 ⇒ 整锚跳过)
        print(f"NOTE {nm}: arm anchors {R.shape[0]} vs ref {ref.shape[0]} (差 {ref.shape[0]-R.shape[0]}), 仅比较共同年份")
        ref = None
    if ref is not None:
        assert np.array_equal(ref[:, 0].astype(np.int64), R[:, 0].astype(np.int64)), f"{nm}: ts mismatch"
    dmax = float(np.max(np.abs(ref[:, 1] - R[:, 1]))) if ref is not None else float("nan")
    ts_ = R[:, 0].astype(np.int64); net = R[:, 1]; yy = np.array([time.gmtime(int(t)).tm_year for t in ts_]); a24 = net[yy >= 2024]
    gt = R[:, 5]; gm = R[:, 6]
    out[nm] = {"maxabs_diff_vs_pod_backup": dmax, "n": int(len(net)), "first": time.strftime("%Y-%m-%d %H:%M", time.gmtime(int(ts_[0]))), "last": time.strftime("%Y-%m-%d %H:%M", time.gmtime(int(ts_[-1]))),
               "net_all": round(float(net.mean()), 4), "net_2024on": round(float(a24.mean()), 4), "sharpe_2024on": round(float(a24.mean() / a24.std(ddof=1) * np.sqrt(2190)), 3),
               "by_year": {int(y): round(float(net[yy == y].mean()), 3) for y in sorted(set(yy.tolist()))},
               "carry_mean": round(float(R[:, 3].mean()), 4), "cost_mean": round(float(R[:, 4].mean()), 4), "fires_total": int(R[:, 10].sum()),
               "gross_total_by_year": {int(y): round(float(gt[yy == y].mean()), 4) for y in sorted(set(yy.tolist()))},
               "gross_member_by_year": {int(y): round(float(gm[yy == y].mean()), 4) for y in sorted(set(yy.tolist()))},
               "gross_total_last500": round(float(gt[-500:].mean()), 4), "nsel_last500": round(float(R[-500:, 8].mean()), 0), "turnover_mean": round(float(R[:, 17].mean()), 5)}
    nx = R[:, 18]; a24x = nx[yy >= 2024]
    outx = {"net_ex_all": round(float(nx.mean()), 4), "net_ex_2024on": round(float(a24x.mean()), 4),
            "sharpe_ex_2024on": round(float(a24x.mean() / a24x.std(ddof=1) * np.sqrt(2190)), 3),
            "by_year_ex": {int(y): round(float(nx[yy == y].mean()), 3) for y in sorted(set(yy.tolist()))},
            "carry_ex_mean": round(float(R[:, 20].mean()), 4), "cost_ex_mean": round(float(R[:, 21].mean()), 4),
            "turnover_ex_mean": round(float(np.abs(R[:, 21]).mean()), 5),
            "netlong_mean": round(float(R[:, 22].mean()), 4),
            "netlong_by_year": {int(y): round(float(R[:, 22][yy == y].mean()), 4) for y in sorted(set(yy.tolist()))}}
    out[nm].update(outx)
    print("RECEIPT", nm, json.dumps(out[nm]), flush=True)
    print("RECEIPT_EX", nm, json.dumps(outx), flush=True)
    save[f"{nm}_rec"] = R
    save[f"{nm}_W"] = WS
_OT = os.environ.get("OUT_TAG", "")   # 并行道输出隔离(PREREG_universe_dyn): 未设时文件名与旧装置同
_OT = f"_{_OT}" if _OT else ""
json.dump(out, open(f"{PD}/w10_ablation_summary{_OT}.json", "w"), indent=1, ensure_ascii=False)
np.savez_compressed(f"{PD}/w10_ablation_series{_OT}.npz", cols=np.array(COLS), symbols=np.array(WSYM), config_json=np.array(json.dumps(_CFG)), **save)
print("DONE", round(time.time() - t0, 1), "s", flush=True)
