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
B = "/mnt/storage/private/work_hsy/pod_backup_2026-08-21"; PD = "/mnt/storage/private/work_hsy/probe_artifacts"
_CFG = {"LOOK": LOOK, "WRULE": WRULE, "CAL": CAL, "LEGS": LEGS, "PHI": PHI, "FSEED": FSEED,
        "FPRED": os.environ.get("FPRED", "(default f10_V2MAIN_s{FSEED})")}
print("CONFIG " + json.dumps(_CFG), flush=True)   # E-0826-C/D: 装置必须自报全部生效配置
t0 = time.time()
MT = np.load(f"{B}/wide_fea_hist_meta.npz", allow_pickle=True)
E_ts = MT["E_ts"].astype(np.int64); members = MT["members"]; y4 = MT["y4"]; qvk = MT["qvk"]
yrs = np.array([time.gmtime(int(t)).tm_year for t in E_ts]); nA = len(E_ts); NW = 829
PW = np.load(f"{B}/wide_panel_4h_hist_v2.npz", allow_pickle=True)
pw_row = {int(t): j for j, t in enumerate(PW["ts"].astype(np.int64))}
FN = PW["f_fund_now"]; IV = PW["f_fund_iv"] if "f_fund_iv" in PW else np.full_like(PW["f_fund_now"], 8.0); R24 = PW["f_rev_24h"]; FE = PW["f_fund_ema_v1"]
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
SLOW = np.load(f"{B}/slow_pred_hist_oos.npy")
# ★★ 严格因果: 只用 walk-forward OOS 预测(四折 + 60 锚 embargo, 只写测试折)。
#    全史重训件 models/f10_live_s*.pt **不参与任何历史评估** —— 它见过全部历史。
F10P = np.full((nA, NW), np.nan, np.float32)
if PHI > 0:
    _R2 = "/mnt/storage/private/work_hsy"
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
    LR = {l: [] for l in ("king", "rev24", "fund")}; idx = []
    for i in range(nA):
        j = pw_row.get(int(E_ts[i]))
        if j is None: continue
        m = members[i]
        if UMASK_ROW is not None:
            _mk = UMASK_ROW.get(j)
            if _mk is not None: m = m[_mk[m]]
        sc = {"king": SLOW[i, m], "rev24": -R24[j, m], "fund": FE[j, m]}
        ok = np.isfinite(y4[i, m])
        for leg in LR:
            z = np.nan_to_num(xz(sc[leg])); z = np.where(ok, z, 0.0); z -= z[ok].mean() if ok.sum() else 0
            g = np.abs(z).sum()
            _yy = np.nan_to_num(y4[i, m], nan=0.0)
            if CAL == "simple":
                _yy = np.expm1(_yy)
            LR[leg].append(float((z / g * _yy).sum() * 1e4) if g > 1e-9 else 0.0)
        idx.append(i)
    return {k: np.array(v) for k, v in LR.items()}, {int(i): p for p, i in enumerate(idx)}
def run(SLOW, LRa, pos, depth, need, cool, look=900):
    def w3_at(i):
        if WRULE == "eq":
            _e = np.array([1.0 if c == "1" else 0.0 for c in LEGS])
            return _e / max(_e.sum(), 1.0)
        p = pos.get(int(i), 0)
        if p < LOOK: return np.array([1/3]*3)
        sl = slice(p - LOOK, p)              # ★ 严格因果: 只用锚 i 之前的腿收益
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
        z = w3[0]*np.nan_to_num(xz(sc["king"])) + w3[1]*np.nan_to_num(xz(sc["rev24"])) + w3[2]*np.nan_to_num(xz(sc["fund"]))
        ok = np.isfinite(y4[i, m]); qv4h = np.expm1(np.clip(qvk[i, m], 0, 30)) * 48
        sel = ok & (qv4h >= 2.5e5)
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
            _zf = (w3[0] * np.nan_to_num(xz(F10P[i, m]))
                   + w3[1] * np.nan_to_num(xz(sc["rev24"]))
                   + w3[2] * np.nan_to_num(xz(sc["fund"])))
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
    if WRULE == "msharpe" and LOOK == 900 and LEGS == "111":
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
json.dump(out, open(f"{PD}/w10_ablation_summary.json", "w"), indent=1, ensure_ascii=False)
np.savez_compressed(f"{PD}/w10_ablation_series.npz", cols=np.array(COLS), symbols=np.array(WSYM), config_json=np.array(json.dumps(_CFG)), **save)
print("DONE", round(time.time() - t0, 1), "s", flush=True)
