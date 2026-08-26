"""COMBO-STAGE(候选形态前向影子, 2026-08-26) = sidecar_blend 全文 + 文末追加 combo 计算。
原侧车职责不变; 新增: 去rev24∧混V2MAIN φ0.45 的目标向量, 只写 state/target_combo/(无读者, 零风险)。
判据装置 = w10 LEGS=101 CAL=simple PHI=0.45(docs/PREREG_leg_ablation_2026-08-26.md §T5)。
原头注: 侧车双跑器 v1(dry-run) @Mac。规格: REVIEW §11 冻结。只读影子状态; 输出到 target_blend/(live 不读)。
步骤: 上锚 prev_rec(members/legz/sm) → ① king 书链复算自平价 → ② 171 管线+numpy 推理 → F-10 书 → ③ 0.55/0.45 权重混合落盘。"""
import os, sys, json, glob, time, subprocess, shutil, hashlib
import numpy as np
from scipy.stats import rankdata
HOME = os.path.expanduser("~"); WS = f"{HOME}/wide_shadow"; HERE = f"{WS}/fea171"
T0 = time.time()
def log(*a): print(f"[{time.time()-T0:6.1f}s]", *a, flush=True)
cfg = json.load(open(f"{WS}/shadow_bundle/config.json")); P = cfg["params"]
aux = json.load(open(f"{WS}/state/aux.json")); pr = aux["prev_rec"]
A = int(pr["anchor_ts"]); pm = np.array(pr["members"], np.int64)
legz = {k: np.array(v, np.float64) for k, v in pr["legz"].items()}
sm_ref = np.array(pr["sm"], np.float64); smi_ref = np.array(pr["sm_idx"], np.int64)
log(f"anchor {time.strftime('%m-%d %H:%M', time.gmtime(A))} members {len(pm)}")
R = np.load(f"{WS}/state/rolling.npz", allow_pickle=True)
rts = R["ts"].astype(np.int64); RD = R["data"]
ai = int(np.searchsorted(rts, A, side="right")) - 1
assert rts[ai] <= A < rts[ai] + 300, "锚未对齐滚动缓存"
NW = RD.shape[1]
# H_prev: 上上锚权重文件
wf = f"{WS}/state/weights/{A-14400}.npz"
H = np.zeros(NW)
if os.path.exists(wf):
    z = np.load(wf); H[z["idx"].astype(np.int64)] = z["val"].astype(np.float64)
# w3 msharpe(900)
LR = json.load(open(f"{WS}/state/leg_returns_live.json"))
look = P["msharpe_look"]
if len(LR["king"]) >= look:
    r = np.stack([np.array(LR[k][-look:], np.float64) for k in ("king", "rev24", "fund")])
    shp = r.mean(1) / (r.std(1) + 1e-9); shp = np.maximum(shp, 0)
    w3 = shp / shp.sum() if shp.sum() > 0 else np.array([1/3]*3)
else:
    w3 = np.array([1/3]*3)
# sel: qv4h 门(与 run_anchor 同式)
CDf = RD.astype(np.float32)
qseg = CDf[max(ai + 1 - 2016, 0):ai + 1, :, 3]; finq = np.isfinite(qseg)
qvm = np.where(finq, qseg, 0).sum(0) / np.maximum(finq.sum(0), 1)
qv4h = np.expm1(np.clip(qvm[pm], 0, 30)) * 48
sel = qv4h >= P["qv4h_min"]

_tl = f"{WS}/state/target_live/{A}.json"
KEEP_NAMES = set((json.load(open(_tl)).get("universe") or [])) if os.path.exists(_tl) else set()
LIVE_MASK = np.array([str(x) in KEEP_NAMES for x in np.load(f"{HERE}/xfer_ref.npz", allow_pickle=True)["symbols"]]) if KEEP_NAMES else None


def _btcv_series(rts, RD, e_rows):
    """E-0825-C 修复: btcv = BTC 5m 收益 2016 根(7天)滚动 std。配方由与 xfer_ref 的精确对照确定
    (corr=1.0000000, 比值=1.0000, n=111 重叠锚); 此前此处硬编码为 zeros ⇒ 5 个模型输入长期恒零。
    自检: 与 xfer_ref 重叠锚 corr>0.999 且比值∈[0.99,1.01], 否则抛错(不静默降级)。"""
    _sy = [str(s) for s in np.load(f"{HERE}/xfer_syms.npz", allow_pickle=True)["symbols"]]
    _jb = _sy.index("BTCUSDT")
    _r5 = RD[:, _jb, 0].astype(np.float64)
    W = 2016
    _v = np.full(len(_r5), np.nan)
    for i in range(W, len(_r5)):
        _v[i] = np.nanstd(_r5[i - W:i])          # 只用满窗(短窗值与配方不符, 自检会拦)
    _full = np.isfinite(_v)
    if _full.any():
        _v[:np.argmax(_full)] = _v[_full][0]      # 早期不足 7 天的行: 显式回填首个满窗值(近似, 只影响 causal_z 的早期统计)
    out = _v[np.asarray(e_rows, int)].astype(np.float32)
    _fullmask = np.asarray(e_rows, int) >= W
    _ref = np.load(f"{HERE}/xfer_ref.npz", allow_pickle=True)
    _m = {int(t): k for k, t in enumerate(rts[np.asarray(e_rows, int)])}
    _pairs = [(out[_m[int(t)]], float(b)) for t, b in zip(_ref["E_ts"].astype(np.int64), _ref["btcv"])
              if int(t) in _m and _fullmask[_m[int(t)]]]
    if len(_pairs) >= 30:
        _a = np.array([p[0] for p in _pairs]); _b = np.array([p[1] for p in _pairs])
        _ok = np.isfinite(_a) & np.isfinite(_b) & (_b > 0)
        _c = float(np.corrcoef(_a[_ok], _b[_ok])[0, 1]); _ratio = float(np.median(_a[_ok] / _b[_ok]))
        assert _c > 0.999 and 0.99 < _ratio < 1.01, f"btcv 重建自检失败 corr={_c:.5f} ratio={_ratio:.4f}"
    assert np.isfinite(out).all() and out.std() > 0, "btcv 序列退化(恒定或含 NaN)"
    return out


def chain(zc):
    w = np.where(sel, zc, 0.0)
    # ★ E-0825-B: 与生产者 shadow_loop_v3.py 逐字同构(集合一致的去均值)
    w = np.where(sel, w - (w[sel].mean() if sel.any() else 0), w)
    g = np.abs(w).sum()
    if g < 1e-9: return None
    w = w / g
    capw = P["cap_mult"] / max(int(sel.sum()), 1)
    w = np.clip(w, -capw, capw)
    g2 = np.abs(w).sum()
    if g2 > 1e-9: w = w / g2
    tgt = np.zeros(NW); tgt[pm] = w
    smv = H + P["alpha"] * (tgt - H)
    trade = smv - H
    smv = np.where(np.abs(trade) < P["band"], H, smv)
    # ★ E-0825-B 二阶段: 与生产者逐字同构 —— 流动性出场集独立于 LIVE_MASK 是否可用
    _keep_liq = np.zeros(NW, bool); _keep_liq[pm[sel]] = True
    keep = (LIVE_MASK.copy() if LIVE_MASK is not None else np.ones(NW, bool))
    if LIVE_MASK is not None:
        _mm = np.zeros(NW, bool); _mm[pm] = True
        keep &= _mm
    keep &= _keep_liq
    leave = (~keep) & (np.abs(smv) > 1e-12)
    smv = np.where(leave, 0.0, smv)
    return smv

# ① 自平价
z_king = w3[0]*np.nan_to_num(legz["king"]) + w3[1]*np.nan_to_num(legz["rev24"]) + w3[2]*np.nan_to_num(legz["fund"])
sm_rep = chain(z_king)
ref = np.zeros(NW); ref[smi_ref] = sm_ref
d = np.abs(sm_rep - ref)
self_par = float(np.max(d))
log(f"① king 书自平价 max|Δw|={self_par:.2e} (EXIT 已复算, 零豁免)")
# ② 171 + F-10 分(全尾管线复用 mac_parity 的 mini 产物: 若最新锚未算则重跑管线)
MINI = f"{HERE}/mini"
f89p = f"{MINI}/data/f8_fea89.npz"
need = True
if os.path.exists(f89p):
    T9 = np.load(f"{MINI}/data/dlw_targets.npz", allow_pickle=True)
    if int(T9["E_ts"].astype(np.int64)[-1]) >= A: need = False
if need:
    log("② 触发 171 管线重跑(全尾)")
    # 构造 targets: 全尾 4h 锚, 成员=当前 pm(近似, 训练一致性>成员漂移)
    e_rows = [i for i in range(len(rts)) if rts[i] % 14400 == 0 and i >= 48]
    ms_arr = np.empty(len(e_rows), object)
    for i in range(len(e_rows)): ms_arr[i] = pm
    zz = np.zeros((len(e_rows), NW), np.float32)
    os.makedirs(f"{MINI}/data", exist_ok=True); os.makedirs(f"{MINI}/results", exist_ok=True); os.makedirs(f"{MINI}/preds", exist_ok=True)
    np.savez(f"{MINI}/cache.npz", ts=rts, data=RD, symbols=np.load(f"{HERE}/xfer_syms.npz", allow_pickle=True)["symbols"], ch=np.load(f"{HERE}/xfer_syms.npz", allow_pickle=True)["ch"])
    np.savez(f"{MINI}/data/dlw_targets.npz", E_row=np.array(e_rows), E_ts=rts[e_rows], members=ms_arr,
             y4s=zz, YR4s=zz, YRZ=zz, yrs=np.array([time.gmtime(int(t)).tm_year for t in rts[e_rows]]),
             qvk=zz, btcv=_btcv_series(rts, RD, e_rows), has_panel=np.ones(len(e_rows), bool),
             symbols=np.load(f"{HERE}/xfer_ref.npz", allow_pickle=True)["symbols"], y4old=zz, meta_json="{}")
    env = dict(os.environ)
    env.update({"F171_CACHE": f"{MINI}/cache.npz", "F171_TARGETS": f"{MINI}/data/dlw_targets.npz", "F171_OUT": MINI,
                "F171_FEA82": f"{MINI}/data/dlw_fea82.npz", "F171_PANEL": f"{HERE}/xfer_panel_live.npz"})
    # fund 面板: 用影子 fund ema 状态构造当前值, 历史锚回填 0(fund_ema/now 两列只在 82 列口径, F-10 mu/sd 会 z 化; dry-run 近似, 入档)
    fe = np.zeros((len(e_rows), NW), np.float32); fn = np.zeros((len(e_rows), NW), np.float32)
    syms_all = [str(x) for x in np.load(f"{HERE}/xfer_ref.npz", allow_pickle=True)["symbols"]]
    scol_of = {s_: j for j, s_ in enumerate(syms_all)}
    for s_, est in aux["ema"].items():
        j = scol_of.get(s_)
        if j is not None and isinstance(est, dict) and "acc" in est:
            fe[-1, j] = float(est["acc"])
    for s_, rows_ in aux["ledger_tail"].items():
        j = scol_of.get(s_)
        if j is not None and rows_:
            fn[-1, j] = float(rows_[-1][1])
    np.savez(f"{HERE}/xfer_panel_live.npz", ts=rts[e_rows], f_fund_ema=fe, f_fund_now=fn)
    PY = f"{WS}/venv/bin/python"
    r1 = subprocess.run([PY, f"{HERE}/dlw_features.py"], env=env, capture_output=True, text=True, cwd=HERE)
    assert r1.returncode == 0, r1.stderr[-500:]
    r2 = subprocess.run([PY, "-c", f"import os,sys; sys.path.insert(0,'{HERE}'); os.chdir('{HERE}'); import f8_higher_order_features as m; m.build()"], env=env, capture_output=True, text=True)
    assert r2.returncode == 0, r2.stderr[-500:]
F82 = np.load(f"{MINI}/data/dlw_fea82.npz", allow_pickle=True)
F89 = np.load(f"{MINI}/data/f8_fea89.npz", allow_pickle=True)
T9 = np.load(f"{MINI}/data/dlw_targets.npz", allow_pickle=True)
ets = T9["E_ts"].astype(np.int64); a_i = int(np.where(ets == A)[0][0])
pa2 = F82["pair_a"].astype(np.int64); ps2 = F82["pair_s"].astype(np.int64)
rowm = (pa2 == a_i)
X171 = np.concatenate([F82["X"][rowm].astype(np.float32), F89["X"][rowm]], 1)
scol = ps2[rowm]
M = np.load(f"{HERE}/f10_live_s42_np.npz")
from scipy.special import erf
def gelu(x): return 0.5*x*(1+erf(x/np.sqrt(2)))
# E-0826(NaN序修复): 训练是 标准化→clip→NaN置0(标准化空间), 服务端必须同序;
# 旧写法 nan_to_num 在前会让 NaN 变 −mu/sd(非零)。当前锚实测 0 个 NaN ⇒ 今日行为不变, 修的是未来。
xz_in = np.nan_to_num(np.clip((X171 - M["mu"]) / M["sd_"], -5, 5))
h = gelu(xz_in @ M["w0"].T + M["b0"]); h = gelu(h @ M["w1"].T + M["b1"])
f10 = (h @ M["w2"].T + M["b2"]).squeeze(-1)
# 对齐到 pm 序
pos_in_pm = {int(s): j for j, s in enumerate(pm)}
f10_pm = np.full(len(pm), np.nan)
for v, s_ in zip(f10, scol):
    j = pos_in_pm.get(int(s_))
    if j is not None: f10_pm[j] = v
okf = np.isfinite(f10_pm)
zf = np.full(len(pm), np.nan); zf[okf] = rankdata(f10_pm[okf]) / max(okf.sum() - 1, 1) - 0.5
z_f10book = w3[0]*np.nan_to_num(zf) + w3[1]*np.nan_to_num(legz["rev24"]) + w3[2]*np.nan_to_num(legz["fund"])
# F-10 书自持 H 状态
# E-0825-D 修复: 状态按锚命名 ⇒ 重跑同锚幂等; 回落到 king 书的仓位不再静默
h_source = "king_fallback"
hf_prev = f"{HERE}/state_H_f10_{A - 14400}.npz"
hf_p = f"{HERE}/state_H_f10_{A}.npz"
H_f10_prev = H.copy()
if os.path.exists(hf_prev):
    zz2 = np.load(hf_prev)
    if int(zz2["anchor"]) == A - 14400:
        H_f10_prev = np.zeros(NW); H_f10_prev[zz2["idx"].astype(np.int64)] = zz2["val"]
        h_source = "own"
elif os.path.exists(f"{HERE}/state_H_f10.npz"):          # 一次性迁移: 旧的单文件形态
    zz2 = np.load(f"{HERE}/state_H_f10.npz")
    if int(zz2["anchor"]) == A - 14400:
        H_f10_prev = np.zeros(NW); H_f10_prev[zz2["idx"].astype(np.int64)] = zz2["val"]
        h_source = "own_legacy"
Hsave = H; H = H_f10_prev
sm_f10 = chain(z_f10book)
H = Hsave
nz = np.where(np.abs(sm_f10) > 1e-9)[0]
np.savez(hf_p, anchor=A, idx=nz, val=sm_f10[nz])
# ③ 混合 + E-0825-A 执行器口径 reshape(蓝本 dl_quant_live/signal/legs.py:124 redemean+rescale; 自平价仍文件口径)
def exec_reshape(w):
    nz_ = np.abs(w) > 1e-12
    o = w.copy()
    if nz_.any():
        o[nz_] -= o[nz_].mean()
        g0 = np.abs(w).sum(); g1 = np.abs(o).sum()
        if g1 > 1e-9:
            o *= g0 / g1
    return o
blend_raw = 0.55 * ref + 0.45 * sm_f10
blend = exec_reshape(blend_raw)
ref_ex = exec_reshape(ref)
os.makedirs(f"{WS}/state/target_blend", exist_ok=True)
syms = [str(s) for s in np.load(f"{HERE}/xfer_ref.npz", allow_pickle=True)["symbols"]]
wnz = {syms[int(j)]: round(float(blend[j]), 8) for j in np.where(np.abs(blend) > 1e-9)[0]}
json.dump({"schema": "wide_target_blend_v2_execcal", "anchor_ts": A, "phi": 0.45, "weights": wnz,
           "caliber": "exec_reshape_v1(E-0825-A)+btcv_fix(E-0825-C)", "h_source": h_source,
           "net_before": round(float(blend_raw.sum()), 6),
           "ref_net_before": round(float(ref.sum()), 6), "ref_ex_gross": round(float(np.abs(ref_ex).sum()), 6),
           "self_parity_maxdw": self_par, "n_f10_scored": int(okf.sum()),
           "rho_f10_vs_king": round(float(np.corrcoef(zf[okf & np.isfinite(legz['king'])], legz["king"][okf & np.isfinite(legz['king'])])[0, 1]), 4)},
          open(f"{WS}/state/target_blend/{A}.json", "w"), indent=1)
log(f"③ blend 落盘 n={len(wnz)} gross={float(np.abs(blend).sum()):.4f} net={float(blend.sum()):+.5f} ρ(f10,king)={np.corrcoef(zf[okf], legz['king'][okf])[0,1]:.3f}")
log(f"SIDECAR_DRYRUN {'PASS' if self_par < 1e-6 else 'SELF_PARITY_' + ('SOFT' if self_par < 1e-3 else 'FAIL')}")

# ═══ COMBO STAGE(候选形态): 去rev24 ∧ 混V2MAIN φ0.45 ═══
# 两本书都去掉 rev24 腿(w3 掩码后在 king/fund 上重归一), 各走完整链条、各自 EMA 态(锚寻址, 幂等),
# 0.55/0.45 混合 → 执行器口径 reshape → state/target_combo/。首锚状态: king侧以实盘 H 暖启动,
# F10侧以侧车 f10 态暖启动(EMA α=0.1 ⇒ 暖启动差异半衰期 ~7 锚, 2-3 天内收敛; 来源字段入档)。
w3m = np.array([w3[0], 0.0, w3[2]])
w3m = w3m / w3m.sum() if w3m.sum() > 1e-12 else np.array([0.5, 0.0, 0.5])
z_kc = w3m[0] * np.nan_to_num(legz["king"]) + w3m[2] * np.nan_to_num(legz["fund"])
z_fc = w3m[0] * np.nan_to_num(zf) + w3m[2] * np.nan_to_num(legz["fund"])
def _load_state2(pth, fallback, tag):
    if os.path.exists(pth):
        zz = np.load(pth)
        if int(zz["anchor"]) == A - 14400:
            v = np.zeros(NW); v[zz["idx"].astype(np.int64)] = zz["val"].astype(np.float64)
            return v, "own"
    return fallback.copy(), tag
H_kc_prev, kc_src = _load_state2(f"{HERE}/state_H_kc_{A-14400}.npz", H, "warmstart_live_H")
H_fc_prev, fc_src = _load_state2(f"{HERE}/state_H_fc_{A-14400}.npz", H_f10_prev, "warmstart_f10_H")
_Hs2 = H
H = H_kc_prev; sm_kc = chain(z_kc)
H = H_fc_prev; sm_fc = chain(z_fc)
H = _Hs2
for _p, _sm in ((f"{HERE}/state_H_kc_{A}.npz", sm_kc), (f"{HERE}/state_H_fc_{A}.npz", sm_fc)):
    _nz = np.where(np.abs(_sm) > 1e-9)[0]
    np.savez(_p, anchor=A, idx=_nz, val=_sm[_nz])
combo_raw = 0.55 * sm_kc + 0.45 * sm_fc
combo = exec_reshape(combo_raw)
os.makedirs(f"{WS}/state/target_combo", exist_ok=True)
cnz = {syms[int(j)]: round(float(combo[j]), 8) for j in np.where(np.abs(combo) > 1e-9)[0]}
json.dump({"schema": "wide_target_combo_v1_execcal", "anchor_ts": A, "phi": 0.45,
           "book_form": "combo_v2main_norev24", "w3_masked": [round(float(x), 6) for x in w3m],
           "weights": cnz, "kc_state_source": kc_src, "fc_state_source": fc_src,
           "gross": round(float(np.abs(combo).sum()), 6), "net_after_reshape": round(float(combo.sum()), 8),
           "kc_gross": round(float(np.abs(sm_kc).sum()), 6), "fc_gross": round(float(np.abs(sm_fc).sum()), 6),
           "rho_kc_fc": round(float(np.corrcoef(sm_kc[np.abs(sm_kc)+np.abs(sm_fc)>1e-9], sm_fc[np.abs(sm_kc)+np.abs(sm_fc)>1e-9])[0,1]), 4) if (np.abs(sm_kc)+np.abs(sm_fc)>1e-9).sum()>10 else None,
           "n_f10_scored": int(okf.sum())},
          open(f"{WS}/state/target_combo/{A}.json", "w"), indent=1)
log(f"④ COMBO 落盘 n={len(cnz)} gross={float(np.abs(combo).sum()):.4f} kc_src={kc_src} fc_src={fc_src} w3m={np.round(w3m,4).tolist()}")

# ═══ COMBO_LIVE(2026-08-26, 用户令"现在切"): 把候选书写为执行器读取的 target_live ═══
# 安全设计(五层):
#   1) 硬截止 N+22:40 —— 绝不在执行器读取窗(N+23:00)内/后重写;
#   2) 先备份生产者 king 文件到 target_live_king/(回滚 = 拷回);
#   3) 飞前断言: F10打分覆盖≥380 / gross∈[0.4,1.2] / 名数≥150 / 宇宙名单与king文件逐字相同;
#   4) 写完立刻用【实盘执行器自己的校验代码】(external_book.verify_file+parse_target)验收本文件,
#      任何不过 ⇒ 自动回滚king文件 + HIGH 告警 ⇒ 本锚交易king形态(fail-open);
#   5) 全程状态入 state/combo_live_status.json; 失败路径全部 HIGH 页报。
if os.environ.get("COMBO_LIVE", "0") == "1":
    _now0 = time.time()
    _status = {"anchor": A, "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(_now0)), "ok": False, "step": "start"}
    def _page(sev, msg):
        try:
            sys.path.insert(0, f"{HOME}/dl_quant_live/live")
            import telegram_notify as _TN
            # 只从 .env 取 TELEGRAM 两项作构造参数; 绝不把 BINANCE 键装进环境(无钥匙纪律)
            _tok = _cid = None
            try:
                for _ln in open(f"{HOME}/dl_quant_live/.env"):
                    _ln = _ln.strip()
                    if _ln.startswith("TELEGRAM_BOT_TOKEN="): _tok = _ln.split("=", 1)[1].strip().strip('"')
                    elif _ln.startswith("TELEGRAM_CHAT_ID="): _cid = _ln.split("=", 1)[1].strip().strip('"')
            except Exception:
                pass
            _r = _TN.TelegramNotifier(token=_tok, chat_id=_cid).alarm(sev, msg)
            log(f"PAGE {sev} status={_r.get('status') if isinstance(_r, dict) else _r}")
        except Exception as _e:
            log("PAGE_FAIL", repr(_e)[:120])
    def _bail(why):
        _status.update(ok=False, why=why)
        json.dump(_status, open(f"{WS}/state/combo_live_status.json", "w"), indent=1)
        log(f"COMBO_LIVE ABORT: {why}")
        _page("HIGH", f"combo 换装写者中止 [{time.strftime('%m-%d %H:%M', time.gmtime(A))}锚]\n{why}\n本锚将交易 king 形态(生产者原文件仍在位)。")
        sys.exit(3)
    _outdir = os.environ.get("COMBO_LIVE_DIR", f"{WS}/state/target_live")
    _rehearsal = _outdir != f"{WS}/state/target_live"
    try:
        _deadline = A + 22 * 60 + 40
        if (not _rehearsal) and _now0 > _deadline:
            _bail(f"过硬截止 N+22:40(now−anchor={_now0-A:.0f}s), 拒绝在读取窗附近重写")
        _kp = f"{WS}/state/target_live/{A}.json"
        if not os.path.exists(_kp) or not os.path.exists(_kp + ".sha256"):
            _bail("生产者 king 文件或其 sha256 边车不存在")
        kdoc = json.load(open(_kp))
        # 飞前断言
        _status["step"] = "preflight"
        _g = float(np.abs(combo_raw).sum())
        _nz = np.where(np.abs(combo_raw) > 1e-9)[0]
        assert int(okf.sum()) >= 380, f"F10 打分覆盖 {int(okf.sum())}/400 < 380"
        assert 0.4 <= _g <= 1.2, f"combo gross {_g:.4f} 出界 [0.4,1.2]"
        assert len(_nz) >= 150, f"combo 名数 {len(_nz)} < 150"
        assert kdoc.get("schema") == "wide_target_v1" and int(kdoc["anchor_ts"]) == A, "king 文件锚/schema 异常"
        _uni = kdoc["universe"]
        # 备份 king
        _status["step"] = "backup"
        os.makedirs(f"{WS}/state/target_live_king", exist_ok=True)
        shutil.copy2(_kp, f"{WS}/state/target_live_king/{A}.json")
        shutil.copy2(_kp + ".sha256", f"{WS}/state/target_live_king/{A}.json.sha256")
        # combo 权重 npz 存档 + weights_sha(与生产者对 npz 取 sha 同法)
        _status["step"] = "write"
        os.makedirs(f"{WS}/state/weights_combo", exist_ok=True)
        _wnpz = f"{WS}/state/weights_combo/{A}.npz"
        _tmpn = _wnpz + ".tmp.npz"
        np.savez_compressed(_tmpn, anchor=A, idx=_nz, val=combo_raw[_nz].astype(np.float32))
        os.replace(_tmpn, _wnpz)
        with open(_wnpz, "rb") as _f:
            _wsha = hashlib.sha256(_f.read()).hexdigest()
        _weights = {syms[int(j)]: float(combo_raw[j]) for j in _nz}
        _doc = {"schema": "wide_target_v1", "anchor_ts": int(A), "weights": _weights,
                "gross_norm": float(sum(abs(v) for v in _weights.values())), "n_names": len(_weights),
                "universe": _uni, "universe_sha": kdoc["universe_sha"], "n_universe": len(_uni),
                "booster_sha": kdoc["booster_sha"], "weights_sha": _wsha,
                "written_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time())),
                "producer": "combo_stage_v1(kingLGBM 0.55 + V2MAIN 0.45, rev24 leg removed; base shadow_loop_v3)"}
        _raw = json.dumps(_doc).encode()
        _jp = f"{_outdir}/{A}.json"
        os.makedirs(_outdir, exist_ok=True)
        with open(_jp + ".tmp", "wb") as _f:
            _f.write(_raw)
        with open(_jp + ".sha256.tmp", "w") as _f:
            _f.write(hashlib.sha256(_raw).hexdigest() + "  " + os.path.basename(_jp) + "\n")
        os.replace(_jp + ".tmp", _jp)
        os.replace(_jp + ".sha256.tmp", _jp + ".sha256")
        # 用实盘执行器自己的校验代码验收
        _status["step"] = "self_validate_with_live_reader"
        sys.path.insert(0, f"{HOME}/dl_quant_live/live"); sys.path.insert(0, f"{HOME}/dl_quant_live")
        import external_book as _EB
        _vf = _EB.verify_file(_jp)
        assert _vf.get("ok"), f"verify_file: {_vf.get('reason')}: {_vf.get('detail')}"
        _cfgE = {"schema": "wide_target_v1", "require_anchor_match": True, "max_age_min": 10.0,
                 "universe_sha_pin": None, "booster_sha_pin": None}
        _pt = _EB.parse_target(_vf["raw"], _cfgE, A, time.time() if not _rehearsal else
                               time.mktime(time.strptime(_doc["written_utc"], "%Y-%m-%dT%H:%M:%SZ")) - time.timezone + 60)
        assert _pt.get("ok"), f"parse_target: {_pt.get('reason')}: {_pt.get('detail')}"
        assert _pt["gross_outside"] == 0.0, f"宇宙外权重 {_pt['gross_outside']}"
        assert _pt["n_in_universe"] >= 150 and _pt["gross_in"] > 0.4
        _status.update(ok=True, step="done", n=len(_weights), gross=_doc["gross_norm"],
                       reader_ok=True, n_in_universe=_pt["n_in_universe"], age_s=_pt["age_s"],
                       elapsed_s=round(time.time() - _now0, 1), rehearsal=_rehearsal)
        json.dump(_status, open(f"{WS}/state/combo_live_status.json", "w"), indent=1)
        log(f"⑤ COMBO_LIVE 写者完成 rehearsal={_rehearsal} n={len(_weights)} gross={_doc['gross_norm']:.4f} 读者验收 ok age={_pt['age_s']}s")
    except SystemExit:
        raise
    except Exception as _e:
        # 回滚: 把 king 备份拷回(若已覆盖)
        try:
            _bk = f"{WS}/state/target_live_king/{A}.json"
            if (not _rehearsal) and os.path.exists(_bk):
                shutil.copy2(_bk, f"{WS}/state/target_live/{A}.json")
                shutil.copy2(_bk + ".sha256", f"{WS}/state/target_live/{A}.json.sha256")
                log("已回滚为 king 文件")
        except Exception as _e2:
            log("ROLLBACK_FAIL", repr(_e2)[:160])
        _bail(f"{type(_e).__name__}: {str(_e)[:220]}")
