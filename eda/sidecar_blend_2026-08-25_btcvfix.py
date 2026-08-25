"""侧车双跑器 v1(dry-run) @Mac。规格: REVIEW §11 冻结。只读影子状态; 输出到 target_blend/(live 不读)。
步骤: 上锚 prev_rec(members/legz/sm) → ① king 书链复算自平价 → ② 171 管线+numpy 推理 → F-10 书 → ③ 0.55/0.45 权重混合落盘。"""
import os, sys, json, glob, time, subprocess
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
    w = w - (w[sel].mean() if sel.any() else 0)
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
    if LIVE_MASK is not None:
        keep = LIVE_MASK.copy()
        _mm = np.zeros(NW, bool); _mm[pm] = True
        keep &= _mm
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
xz_in = np.clip((np.nan_to_num(X171) - M["mu"]) / M["sd_"], -5, 5)
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
