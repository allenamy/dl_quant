"""COMBO-STAGE(候选形态前向影子, 2026-08-26) = sidecar_blend 全文 + 文末追加 combo 计算。
原侧车职责不变; 新增: 去rev24∧混V2MAIN φ0.45 的目标向量, 只写 state/target_combo/(无读者, 零风险)。
判据装置 = w10 LEGS=101 CAL=simple PHI=0.45(docs/PREREG_leg_ablation_2026-08-26.md §T5)。
原头注: 侧车双跑器 v1(dry-run) @Mac。规格: REVIEW §11 冻结。只读影子状态; 输出到 target_blend/(live 不读)。
步骤: 上锚 prev_rec(members/legz/sm) → ① king 书链复算自平价 → ② 171 管线+numpy 推理 → F-10 书 → ③ 0.55/0.45 权重混合落盘。"""
import os, sys, json, glob, time, subprocess, shutil, hashlib, io, tempfile
import numpy as np
from scipy.stats import rankdata
from feature_cache_identity import capture_producer_inputs, verify_source_snapshot
import nc_contract as NC   # NC: shared with the producer and the training replay
import durable_io as DIO   # C: durable state writes (imported here, before any executor path is put on sys.path)
import prev_state as PS    # gap class fix 2026-09-26: previous state = most recent valid state before A, named source
HOME = os.path.expanduser("~")
def _runtime_roots(env, home):
    default_ws = os.path.realpath(os.path.join(home, "wide_shadow"))
    default_exec = os.path.realpath(os.path.join(home, "dl_quant_live"))
    ws = os.path.realpath(env.get("WIDE_SHADOW_HOME", default_ws))
    executor = os.path.realpath(env.get("DL_QUANT_LIVE_ROOT", default_exec))
    custom = (ws, executor) != (default_ws, default_exec)
    if env.get("COMBO_LIVE", "0") == "1" and custom:
        out = env.get("COMBO_LIVE_DIR")
        if (not out or not os.path.isabs(out)
                or ws == default_ws or executor == default_exec
                or any(os.path.commonpath([candidate, production]) in (candidate, production)
                       for candidate in (ws, executor) for production in (default_ws, default_exec))
                or os.path.commonpath([os.path.realpath(out), os.path.join(ws, "state")]) != os.path.join(ws, "state")
                or os.path.realpath(out) == os.path.join(ws, "state/target_live")):
            raise RuntimeError("custom runtime roots require a separate explicit rehearsal directory")
        # Root checks are not a kernel sandbox, but reject known mutable child
        # directory aliases before inference can write any checkpoint.
        for relative in ("fea171", "state", "state/weights_combo", "state/target_blend",
                         "state/target_combo", "state/target_live", "state/target_live_king"):
            if os.path.commonpath([os.path.realpath(os.path.join(ws, relative)), ws]) != ws:
                raise RuntimeError("rehearsal mutable directory escapes its root")
        if os.path.commonpath([os.path.realpath(os.path.join(executor, "live")), executor]) != executor:
            raise RuntimeError("rehearsal executor directory escapes its root")
    return ws, executor
WS, EXECUTOR_ROOT = _runtime_roots(os.environ, HOME)
HERE = f"{WS}/fea171"
T0 = time.time()
def log(*a): print(f"[{time.time()-T0:6.1f}s]", *a, flush=True)
_source_snapshot = capture_producer_inputs(WS, HERE)
cfg = _source_snapshot["cfg"]; P = cfg["params"]
aux = _source_snapshot["aux"]; pr = aux["prev_rec"]
_symbols = _source_snapshot["symbols"]; _channels = _source_snapshot["channels"]
A = int(pr["anchor_ts"]); pm = np.array(pr["members"], np.int64)
legz = {k: np.array(v, np.float64) for k, v in pr["legz"].items()}
sm_ref = np.array(pr["sm"], np.float64); smi_ref = np.array(pr["sm_idx"], np.int64)
log(f"anchor {time.strftime('%m-%d %H:%M', time.gmtime(A))} members {len(pm)}")
rts = _source_snapshot["rts"]; RD = _source_snapshot["data"]
_bnd = _source_snapshot["boundary"]
RR = NC.rr_from_ch0(rts, _source_snapshot["ch0_storage_f16"], _bnd["ts"], _bnd["col"], _bnd["raw"])   # NC A3: the return channel every consumer reads
assert RR.shape == RD[:, :, 0].shape and np.array_equal(np.isnan(RR), np.isnan(RD[:, :, 0])) and np.array_equal(np.nan_to_num(RR), np.nan_to_num(RD[:, :, 0])),     "v2: capture_producer_inputs' channel 0 is not rr"   # DESIGN_ret5_single_accessor_2026-09-24 §3-1
_mh = _source_snapshot["members_hist"]
MEMBERS_HIST = {int(_mh["anchors"][k]): _mh["idx"][_mh["off"][k]:_mh["off"][k + 1]] for k in range(len(_mh["anchors"]))}   # NC A2
ai = int(np.searchsorted(rts, A, side="right")) - 1
assert rts[ai] <= A < rts[ai] + 300, "锚未对齐滚动缓存"
NW = RD.shape[1]
# H_prev: 生产者上一份权重文件。gap 类修复(2026-09-26): anchor<A 的最近一份有效文件 —— 生产者 st.H 跨缺锚同样承接最近一次计算,
# 原先恰好 A-14400 的取法在缺锚后给零向量(自平价①失真, 且作 kc/f10 回落源时 gross≈0.07 ⇒ 飞前中止并毒化后续锚)
STATE_LOOKUP = {}
_lk_w = PS.latest_state(f"{WS}/state/weights/{{a}}.npz", A, NW, anchor_key=False)
STATE_LOOKUP["weights"] = PS.record(_lk_w)
H = _lk_w["vec"] if _lk_w["vec"] is not None else np.zeros(NW)
# w3 msharpe(900)
LR = _source_snapshot["lr"]
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
LIVE_MASK = np.array([str(x) in KEEP_NAMES for x in _symbols]) if KEEP_NAMES else None


def _btcv_series(rts, RD, e_rows, RR):
    """E-0825-C 修复: btcv = BTC 5m 收益 2016 根(7天)滚动 std。配方由与 xfer_ref 的精确对照确定
    (corr=1.0000000, 比值=1.0000, n=111 重叠锚); 此前此处硬编码为 zeros ⇒ 5 个模型输入长期恒零。
    自检: 与 xfer_ref 重叠锚 corr>0.999 且比值∈[0.99,1.01], 否则抛错(不静默降级)。"""
    _sy = [str(s) for s in _symbols]
    _jb = _sy.index("BTCUSDT")
    _r5 = np.asarray(RR)[:, _jb].astype(np.float64)   # v2: RR required, no channel-0 fallback (DESIGN_ret5_single_accessor §3-2)
    W = 2016
    # NEW_S2 D9 (build_combo_inputs.py:156): window [i-W+1, i] INCLUDES the bar closing at i; finite
    # coverage < 95% -> NaN; the early rows are NOT backfilled with the first full-window value.
    _fin = np.isfinite(_r5)
    _z = np.where(_fin, _r5, 0.0)
    _csn = np.concatenate([[0.0], np.cumsum(_fin.astype(np.float64))])
    _csx = np.concatenate([[0.0], np.cumsum(_z)])
    _csx2 = np.concatenate([[0.0], np.cumsum(_z * _z)])
    _hi = np.arange(len(_r5)) + 1
    _lo = np.maximum(_hi - W, 0)
    _n = _csn[_hi] - _csn[_lo]
    _nn = np.maximum(_n, 1.0)
    _mu = (_csx[_hi] - _csx[_lo]) / _nn
    _v = np.sqrt(np.maximum((_csx2[_hi] - _csx2[_lo]) / _nn - _mu * _mu, 0.0))
    _v[_n < W * 0.95] = np.nan
    out = _v[np.asarray(e_rows, int)].astype(np.float32)
    _fullmask = np.asarray(e_rows, int) >= W
    _ref = _source_snapshot["reference"]
    _m = {int(t): k for k, t in enumerate(rts[np.asarray(e_rows, int)])}
    _pairs = [(out[_m[int(t)]], float(b)) for t, b in zip(_ref["E_ts"].astype(np.int64), _ref["btcv"])
              if int(t) in _m and _fullmask[_m[int(t)]]]
    if len(_pairs) >= 30:
        _a = np.array([p[0] for p in _pairs]); _b = np.array([p[1] for p in _pairs])
        _ok = np.isfinite(_a) & np.isfinite(_b) & (_b > 0)
        # NEW_S2 D9: btcv may now be NaN by design, so the overlap is counted AFTER the finite filter.
        if int(_ok.sum()) >= 30:
            _c = float(np.corrcoef(_a[_ok], _b[_ok])[0, 1]); _ratio = float(np.median(_a[_ok] / _b[_ok]))
            assert _c > 0.999 and 0.99 < _ratio < 1.01, f"btcv 重建自检失败 corr={_c:.5f} ratio={_ratio:.4f}"
    assert np.isfinite(out).any() and float(np.nanstd(out)) > 0, "btcv 序列退化(恒定或全 NaN)"
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
# ② Every invocation builds from its captured inputs in a private workspace.
from feature_cache_identity import FeatureCacheError, load_verified_feature_cache, verify_current_feature_cache, require_current_anchor_axis, fresh_feature_workspace
_feature_workspace = fresh_feature_workspace()
MINI = f"{_feature_workspace.name}/mini"
require_current_anchor_axis(rts, A)
need = True
if need:
    log("② 触发 171 管线重跑(全尾)")
    # 构造 targets: 全尾 4h 锚, 成员=当前 pm(近似, 训练一致性>成员漂移)
    e_rows = [i for i in range(len(rts)) if rts[i] % 14400 == 0 and i >= 48]
    ms_arr = np.empty(len(e_rows), object)
    # NC A2: as-of member history (state/members_hist.npz); an anchor without history (producer skipped it) has no members
    MH_MISSING = 0
    # gap 类修复(ACCEPTANCE AMENDMENT 2): 生产者没跑的锚在 members_hist 里无条目 ⇒ 用生产者成员规则(members_rule.py = shadow_loop_v3 L676-L701)
    # 在同一份滚动缓存上现算, fetch 名单取 A 时刻的(V2 实测: 事后重算平均 Jaccard 0.9987, carry-forward 0.9914); 历史齐全时本段不执行
    MH_RECOMPUTED, MH_RECOMPUTE_ERR = {}, {}
    _mh_need = [int(rts[e_rows[i]]) for i in range(len(e_rows)) if int(rts[e_rows[i]]) != A and int(rts[e_rows[i]]) not in MEMBERS_HIST]
    if _mh_need:
        import members_rule as MR, tradability as _TR
        _cr = json.load(open(f"{WS}/shadow_bundle/crypto_axis.json"))
        assert [str(x) for x in _cr["symbols"]] == [str(x) for x in _symbols], "crypto_axis.json axis differs from the producer axis"
        _crypto = np.array([bool(x) for x in _cr["crypto"]], bool)
        _cd16 = RD.astype(np.float16); _cd16[:, :, 0] = _source_snapshot["ch0_storage_f16"]   # the producer's st.cd (f16 storage, ch0 not rr)
        _fm = MR.fetch_mask_from_aux(aux, [str(x) for x in _symbols])
        for _t in _mh_need:
            try:
                MH_RECOMPUTED[_t] = MR.members_at(rts, _cd16, _t, _crypto, _fm, P, _TR, NC)
            except Exception as _me:                  # noqa: BLE001 — a failed recompute leaves the anchor memberless (named), never blocks
                MH_RECOMPUTE_ERR[_t] = f"{type(_me).__name__}: {str(_me)[:80]}"
        del _cd16
    for i in range(len(e_rows)):
        _ea = int(rts[e_rows[i]])
        if _ea == A:
            ms_arr[i] = pm
        elif _ea in MEMBERS_HIST:
            ms_arr[i] = np.asarray(MEMBERS_HIST[_ea], np.int64)
        elif _ea in MH_RECOMPUTED:
            ms_arr[i] = MH_RECOMPUTED[_ea]
        else:
            ms_arr[i] = np.zeros(0, np.int64); MH_MISSING += 1
    log(f"NC A2 member history: {len(e_rows) - MH_MISSING}/{len(e_rows)} window anchors have members (missing {MH_MISSING})")
    if _mh_need:
        log(f"MH_RECOMPUTED (gap class fix) {len(MH_RECOMPUTED)} anchors {sorted(MH_RECOMPUTED)[:12]} errors {MH_RECOMPUTE_ERR}")
    zz = np.zeros((len(e_rows), NW), np.float32)
    os.makedirs(f"{MINI}/data", exist_ok=True); os.makedirs(f"{MINI}/results", exist_ok=True); os.makedirs(f"{MINI}/preds", exist_ok=True)
    _mini_data = RD.astype(np.float16); _mini_data[:, :, 0] = np.nan   # v2: the mini cache carries no channel-0 values; ret5 lives in ret_f32 only
    np.savez(f"{MINI}/cache.npz", ts=rts, data=_mini_data, symbols=_symbols, ch=_channels, ret_f32=RR)   # NC A3: ret_f32 = rr
    np.savez(f"{MINI}/data/dlw_targets.npz", E_row=np.array(e_rows), E_ts=rts[e_rows], members=ms_arr,
             y4s=zz, YR4s=zz, YRZ=zz, yrs=np.array([time.gmtime(int(t)).tm_year for t in rts[e_rows]]),
             qvk=zz, btcv=_btcv_series(rts, RD, e_rows, RR), has_panel=np.ones(len(e_rows), bool),
             symbols=_symbols, y4old=zz, meta_json="{}")
    env = dict(os.environ)
    env.update({"F171_CACHE": f"{MINI}/cache.npz", "F171_TARGETS": f"{MINI}/data/dlw_targets.npz", "F171_OUT": MINI,
                "F171_FEA82": f"{MINI}/data/dlw_fea82.npz", "F171_PANEL": f"{_feature_workspace.name}/xfer_panel_live.npz",
                "F8_TREND_ROWS": "last"})   # NEW_S2 D7: declared here, not inherited from the environment
    # fund 面板: 用影子 fund ema 状态构造当前值, 历史锚回填 0(fund_ema/now 两列只在 82 列口径, F-10 mu/sd 会 z 化; dry-run 近似, 入档)
    fe = np.zeros((len(e_rows), NW), np.float32); fn = np.zeros((len(e_rows), NW), np.float32)
    syms_all = [str(x) for x in _symbols]
    scol_of = {s_: j for j, s_ in enumerate(syms_all)}
    # NC A5: the F10 fund panel = researcher funding_state as-of (12 h freshness, finite EMA, fn = raw rate); missing -> 0
    for s_, rows_ in aux["ledger_tail"].items():
        j = scol_of.get(s_)
        if j is not None and rows_:
            _fe, _fn, _iv, _r8 = NC.funding_asof(aux["ema"].get(s_), rows_[-1], A)
            if np.isfinite(_fe):
                fe[-1, j] = float(_fe); fn[-1, j] = float(_fn)
    np.savez(f"{_feature_workspace.name}/xfer_panel_live.npz", ts=rts[e_rows], f_fund_ema=fe, f_fund_now=fn)
    PY = f"{WS}/venv/bin/python"
    r1 = subprocess.run([PY, f"{HERE}/dlw_features.py"], env=env, capture_output=True, text=True, cwd=HERE)
    assert r1.returncode == 0, r1.stderr[-500:]
    r2 = subprocess.run([PY, "-c", f"import os,sys; sys.path.insert(0,'{HERE}'); os.chdir('{HERE}'); import f8_higher_order_features as m; m.build()"], env=env, capture_output=True, text=True)
    assert r2.returncode == 0, r2.stderr[-500:]
# Always validate again after construction; never score a partial generation.
F82, F89, T9, _feature_identity = load_verified_feature_cache(MINI, A)
ets = T9["E_ts"].astype(np.int64); a_i = int(np.where(ets == A)[0][0])
pa2 = F82["pair_a"].astype(np.int64); ps2 = F82["pair_s"].astype(np.int64)
rowm = (pa2 == a_i)
X171 = np.concatenate([F82["X"][rowm].astype(np.float32), F89["X"][rowm]], 1)
scol = ps2[rowm]
with open(f"{HERE}/f10_live_s42_np.npz", "rb") as _f10_file:
    _f10_bytes = _f10_file.read()
M = np.load(io.BytesIO(_f10_bytes))
_F10_SHA = hashlib.sha256(_f10_bytes).hexdigest()   # Exactly the bytes loaded for this inference.
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
hf_p = f"{HERE}/state_H_f10_{A}.npz"
H_f10_prev = H.copy()
_lk_f10 = PS.latest_state(f"{HERE}/state_H_f10_{{a}}.npz", A, NW)   # gap 类修复: 最近一份有效状态(own / own_gap<m>[_rejected<n>][_beyond_bound])
STATE_LOOKUP["f10"] = PS.record(_lk_f10)
if _lk_f10["vec"] is not None:
    H_f10_prev = _lk_f10["vec"]
    h_source = _lk_f10["source"]
elif os.path.exists(f"{HERE}/state_H_f10.npz"):          # 一次性迁移: 旧的单文件形态
    zz2 = np.load(f"{HERE}/state_H_f10.npz")
    if int(zz2["anchor"]) == A - 14400:
        H_f10_prev = np.zeros(NW); H_f10_prev[zz2["idx"].astype(np.int64)] = zz2["val"]
        h_source = "own_legacy"
Hsave = H; H = H_f10_prev
sm_f10 = chain(z_f10book)
H = Hsave
nz = np.where(np.abs(sm_f10) > 1e-9)[0]
_F10_COLD = _lk_f10["vec"] is None and float(np.abs(H_f10_prev).sum()) < PS.MIN_STATE_GROSS   # gap 类修复: 冷启动 = 无有效状态且回落也是零
if not _F10_COLD:   # 冷启动绝不写状态(否则下一锚会把 ~0.1x 的书当作 own 承接, 约 5 锚后发布一本从零爬升的书)
    _hb = io.BytesIO(); np.savez(_hb, anchor=A, idx=nz, val=sm_f10[nz]); DIO.write_bytes_durable(hf_p, _hb.getvalue())   # C (durable, DESIGN_executor_durable_state_2026-09-25): memory bytes -> with-write -> fsync -> read-back byte compare -> os.replace; failure raises, target untouched
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
syms = [str(s) for s in _symbols]
wnz = {syms[int(j)]: round(float(blend[j]), 8) for j in np.where(np.abs(blend) > 1e-9)[0]}
DIO.write_json_durable(f"{WS}/state/target_blend/{A}.json", {"schema": "wide_target_blend_v2_execcal", "anchor_ts": A, "phi": 0.45, "weights": wnz,
           "caliber": "exec_reshape_v1(E-0825-A)+btcv_fix(E-0825-C)", "h_source": h_source,
           "net_before": round(float(blend_raw.sum()), 6),
           "ref_net_before": round(float(ref.sum()), 6), "ref_ex_gross": round(float(np.abs(ref_ex).sum()), 6),
           "self_parity_maxdw": self_par, "n_f10_scored": int(okf.sum()),
           "rho_f10_vs_king": round(float(np.corrcoef(zf[okf & np.isfinite(legz['king'])], legz["king"][okf & np.isfinite(legz['king'])])[0, 1]), 4)},
          indent=1)   # C (durable, DESIGN_executor_durable_state_2026-09-25): memory bytes -> with-write -> fsync -> read-back byte compare -> os.replace; failure raises, target untouched
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
# ★ FTRIM(PREREG_deploy_ftrim_2026-09-02, 用户字 09-02 "确认无误可立即部署"): 负费率空头 z 层排除 ——
#   当前 8h 归一化费率 rn8 = ledger 最新 rate×(8/iv) ≤ −0.0010 且 z<0 的名, 在去均值/L1/cap/EMA 之前把 z 置 0
#   (kc/fc 同点; 与判决装置 w10_ftrim_band.py pre 模式 L129-131 / L158-160 逐字同构; 缺费率名不排除)。
#   受据: 双口径(msharpe/W3FIX)双种子四门过, Δ +0.21~+0.23 bps/锚; 实盘反事实 S|S<−10bp sleeve −74U/35 锚。
FTRIM_HI = -0.0010
_col_of = {s_: j for j, s_ in enumerate(syms)}
rn8_full = np.full(NW, np.nan)
for _s, _rows in aux["ledger_tail"].items():
    _j = _col_of.get(_s)
    if _j is not None and _rows:
        rn8_full[_j] = NC.funding_asof(aux["ema"].get(_s), _rows[-1], A)[3]   # NC A5 (D13): fresh, known interval, rate*8/iv
rn8_m = rn8_full[pm]
_band_kc = (z_kc < 0) & np.isfinite(rn8_m) & (rn8_m <= FTRIM_HI)
_band_fc = (z_fc < 0) & np.isfinite(rn8_m) & (rn8_m <= FTRIM_HI)
z_kc = np.where(_band_kc, 0.0, z_kc)
z_fc = np.where(_band_fc, 0.0, z_fc)
ftrim_rec = {"rule": "pre_zero_rn8_le_-10bp_8h", "hi": FTRIM_HI, "rn8_coverage": round(float(np.isfinite(rn8_m).mean()), 4),
             "n_kc": int(_band_kc.sum()), "n_fc": int(_band_fc.sum()),
             "names_kc": {syms[int(pm[k])]: round(float(rn8_m[k]), 7) for k in np.where(_band_kc)[0]},
             "names_fc": {syms[int(pm[k])]: round(float(rn8_m[k]), 7) for k in np.where(_band_fc)[0]}}
log(f"FTRIM 负费率空头排除: kc {ftrim_rec['n_kc']} 名 / fc {ftrim_rec['n_fc']} 名 (rn8 覆盖 {ftrim_rec['rn8_coverage']:.3f})")
def _load_state2(leg, fallback, tag):
    # gap 类修复(2026-09-26): 最近一份有效状态; 无任何有效状态才用具名回落(并页报)
    lk = PS.latest_state(f"{HERE}/state_H_{leg}_{{a}}.npz", A, NW)
    STATE_LOOKUP[leg] = PS.record(lk)
    if lk["vec"] is not None:
        return lk["vec"], lk["source"]
    STATE_LOOKUP[leg]["fallback"] = tag
    return fallback.copy(), tag
H_kc_prev, kc_src = _load_state2("kc", H, "warmstart_live_H")
H_fc_prev, fc_src = _load_state2("fc", H_f10_prev, "warmstart_f10_H")
COLD_START = sorted([leg for leg, lk_vec, prev in (("kc", STATE_LOOKUP["kc"].get("source"), H_kc_prev), ("fc", STATE_LOOKUP["fc"].get("source"), H_fc_prev))
                     if lk_vec is None and float(np.abs(prev).sum()) < PS.MIN_STATE_GROSS] + (["f10"] if _F10_COLD else []))
for _leg in COLD_START:
    STATE_LOOKUP.setdefault(_leg, {"source": None})["cold_start_refused"] = True
COLD_LIVE = [l for l in COLD_START if l in ("kc", "fc")]   # the two chains of the published book; an f10-only cold start touches target_blend only
_GAP_NONTRIVIAL = any(r.get("source") != "own" for r in STATE_LOOKUP.values())
_GAP_PAGE = [f"{k}: {r.get('source') or 'NO_VALID_STATE→' + str(r.get('fallback'))}"
             + (f" (used {r['anchor']}, gap {r['gap']})" if r.get("anchor") else "")
             + "".join(f"; rejected {os.path.basename(x['path'])}: {x['reason']}" for x in r.get("rejected", []))
             for k, r in STATE_LOOKUP.items() if r.get("source") is None or r.get("rejected") or r.get("beyond_bound")]
if _GAP_NONTRIVIAL:
    log(f"STATE_LOOKUP (gap class fix) {json.dumps({k: (r.get('source'), r.get('anchor')) for k, r in STATE_LOOKUP.items()})}")
_Hs2 = H
H = H_kc_prev; sm_kc = chain(z_kc)
H = H_fc_prev; sm_fc = chain(z_fc)
H = _Hs2
for _p, _sm in (((f"{HERE}/state_H_kc_{A}.npz", sm_kc), (f"{HERE}/state_H_fc_{A}.npz", sm_fc)) if not COLD_LIVE else ()):   # 冷启动不写状态
    _nz = np.where(np.abs(_sm) > 1e-9)[0]
    _hb = io.BytesIO(); np.savez(_hb, anchor=A, idx=_nz, val=_sm[_nz]); DIO.write_bytes_durable(_p, _hb.getvalue())   # C (durable, DESIGN_executor_durable_state_2026-09-25): memory bytes -> with-write -> fsync -> read-back byte compare -> os.replace; failure raises, target untouched
combo_raw = 0.55 * sm_kc + 0.45 * sm_fc
combo = exec_reshape(combo_raw)
os.makedirs(f"{WS}/state/target_combo", exist_ok=True)
cnz = {syms[int(j)]: round(float(combo[j]), 8) for j in np.where(np.abs(combo) > 1e-9)[0]}
DIO.write_json_durable(f"{WS}/state/target_combo/{A}.json", {"schema": "wide_target_combo_v1_execcal", "anchor_ts": A, "phi": 0.45,
           "book_form": "combo_v2main_norev24", "w3_masked": [round(float(x), 6) for x in w3m],
           "weights": cnz, "kc_state_source": kc_src, "fc_state_source": fc_src,
           "gross": round(float(np.abs(combo).sum()), 6), "net_after_reshape": round(float(combo.sum()), 8),
           "kc_gross": round(float(np.abs(sm_kc).sum()), 6), "fc_gross": round(float(np.abs(sm_fc).sum()), 6),
           "rho_kc_fc": round(float(np.corrcoef(sm_kc[np.abs(sm_kc)+np.abs(sm_fc)>1e-9], sm_fc[np.abs(sm_kc)+np.abs(sm_fc)>1e-9])[0,1]), 4) if (np.abs(sm_kc)+np.abs(sm_fc)>1e-9).sum()>10 else None,
           "n_f10_scored": int(okf.sum()), "ftrim": ftrim_rec,
           **({"state_lookup": STATE_LOOKUP} if _GAP_NONTRIVIAL else {}), **({"cold_start_refused": COLD_START} if COLD_START else {}),
           **({"members_recomputed": {str(t): int(len(v)) for t, v in sorted(MH_RECOMPUTED.items())}, "members_recompute_errors": {str(t): e for t, e in MH_RECOMPUTE_ERR.items()}}
              if (MH_RECOMPUTED or MH_RECOMPUTE_ERR) else {})},
          indent=1)   # C (durable, DESIGN_executor_durable_state_2026-09-25): memory bytes -> with-write -> fsync -> read-back byte compare -> os.replace; failure raises, target untouched
log(f"④ COMBO 落盘 n={len(cnz)} gross={float(np.abs(combo).sum()):.4f} kc_src={kc_src} fc_src={fc_src} w3m={np.round(w3m,4).tolist()}")

# ═══ COMBO_LIVE(2026-08-26, 用户令"现在切"): 把候选书写为执行器读取的 target_live ═══
# 安全设计(五层):
#   1) 硬截止 N+22:40 —— 绝不在执行器读取窗(N+23:00)内/后重写;
#   2) 先备份生产者 king 文件到 target_live_king/(仅留档，不回写目标);
#   3) 飞前断言: F10打分覆盖≥380 / gross∈[0.4,1.2] / 名数≥150 / 宇宙名单与king文件逐字相同;
#   4) 发布前在私有临时目录用实盘读者 verify_file+parse_target 验收，失败只告警;
#      目标替换失败也不回写 King；当前读者对缺/未通过身份钉的目标 HOLD;
#   5) 全程状态入 state/combo_live_status.json; 失败路径全部 HIGH 页报。
if os.environ.get("COMBO_LIVE", "0") == "1":
    _now0 = time.time()
    _status = {"anchor": A, "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(_now0)), "ok": False, "step": "start",
               **({"state_lookup": STATE_LOOKUP, "state_lookup_page": _GAP_PAGE} if _GAP_NONTRIVIAL else {})}
    def _page(sev, msg):
        try:
            sys.path.insert(0, f"{EXECUTOR_ROOT}/live")
            import telegram_notify as _TN
            # 只从 .env 取 TELEGRAM 两项作构造参数; 绝不把 BINANCE 键装进环境(无钥匙纪律)
            _tok = _cid = None
            try:
                for _ln in open(f"{EXECUTOR_ROOT}/.env"):
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
        try:   # C (durable, DESIGN_executor_durable_state_2026-09-25): memory bytes -> with-write -> fsync -> read-back byte compare -> os.replace; failure raises, target untouched
            DIO.write_json_durable(f"{WS}/state/combo_live_status.json", _status, indent=1)
        except DIO.DurableWriteError as _se:   # the page below must still go out; the previous status file stays intact
            log(f"STATUS_WRITE_FAILED (durable write refused; previous combo_live_status.json kept intact): {_se}")
        log(f"COMBO_LIVE ABORT: {why}")
        _page("HIGH", f"combo 换装写者中止 [{time.strftime('%m-%d %H:%M', time.gmtime(A))}锚]\n{why}\n停止本次发布；当前执行器对缺失或未通过身份钉的目标 HOLD，不回退交易 King。")
        sys.exit(3)
    _outdir = os.environ.get("COMBO_LIVE_DIR", f"{WS}/state/target_live")
    _rehearsal = _outdir != f"{WS}/state/target_live"
    if COLD_LIVE:   # gap 类修复 设计原则: 承接最近一份有效状态; 一份都没有且回落为零 = 冷启动, 冷启动的书绝不发布(执行器会把它放大到满杠杆)
        _bail(f"冷启动拒绝发布: {COLD_LIVE} 无任何有效状态(≥{PS.MIN_STATE_GROSS} gross)且回落为零; 状态未写; 需要人恢复状态 | " + " | ".join(_GAP_PAGE))
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
        # ── M3(PREREG_m3_beta_overlay_executed_book_2026-09-23, 24c3f803f §5): 逐名 β 写入 target_live 新字段 `beta_overlay`,
        #    供执行器在 reshape+clamp 之后算 β_exec 下 BTC 叠加腿。只加字段, 不改任何既有字段与权重。
        #    ★ 绝不阻断发布: 计算失败 ⇒ 本锚不写该字段(执行器 on 时「缺失即不做」+ HIGH), 页报放在发布之后(不占截止余量)。
        #    ★ Everything M3 adds runs inside ONE try whose except cannot raise: no NameError, no log failure, nothing M3 does
        #      may reach the outer except (that path is _bail = "publication aborted"). Checked by re-running the 20260922
        #      release's publication-boundary tests against this file (their harness namespace has no rts/RD — the field is
        #      then simply omitted and the book publishes byte-identically).
        _status["step"] = "beta_overlay"
        _beta_field = None
        _beta_page = None
        try:
            _t_beta = time.time()
            import beta_overlay_producer as _BOP
            _beta_field = _BOP.compute(rts, RD[:, :, 0], [str(x) for x in _symbols], list(_uni), A)
            _status["beta_overlay"] = {"ok": True, "version": _beta_field["version"], "n_names": _beta_field["n_names"],
                                       "n_estimated": _beta_field["n_estimated"], "n_fallback": _beta_field["n_fallback"],
                                       "n_no_cache_column": _beta_field["n_no_cache_column"],
                                       "elapsed_s": round(time.time() - _t_beta, 3)}
            log(f"M3 beta_overlay: {_status['beta_overlay']}")
        except Exception as _be:                    # noqa: BLE001 — the book is published without the field
            _beta_field = None
            try:
                _status["beta_overlay"] = {"ok": False, "error": f"{type(_be).__name__}: {str(_be)[:200]}"}
                _beta_page = (f"combo 写者: beta_overlay 字段计算失败 [锚 {A}] {type(_be).__name__}: {str(_be)[:160]} — "
                              f"目标照常发布但不含该字段; 执行器 M3=on 时本锚不下对冲单(缺失即不做)。")
            except Exception:                        # noqa: BLE001
                _beta_page = "combo 写者: beta_overlay 字段计算失败(详情不可得) — 目标照常发布但不含该字段。"
        # 备份 king
        _status["step"] = "backup"
        os.makedirs(f"{WS}/state/target_live_king", exist_ok=True)
        shutil.copy2(_kp, f"{WS}/state/target_live_king/{A}.json")
        shutil.copy2(_kp + ".sha256", f"{WS}/state/target_live_king/{A}.json.sha256")
        # combo 权重 npz 存档 + weights_sha(与生产者对 npz 取 sha 同法)
        _status["step"] = "write"
        os.makedirs(f"{WS}/state/weights_combo", exist_ok=True)
        _wnpz = f"{WS}/state/weights_combo/{A}.npz"
        # C (durable, DESIGN_executor_durable_state_2026-09-25): memory bytes -> with-write -> fsync -> read-back byte compare -> os.replace; failure raises, target untouched
        _wb = io.BytesIO(); np.savez_compressed(_wb, anchor=A, idx=_nz, val=combo_raw[_nz].astype(np.float32))
        _wsha = DIO.write_bytes_durable(_wnpz, _wb.getvalue())   # weights_sha = sha256 of the VERIFIED in-memory bytes (E-0925-A)
        _weights = {syms[int(j)]: float(combo_raw[j]) for j in _nz}
        _doc = {"schema": "wide_target_v1", "anchor_ts": int(A), "weights": _weights,
                "gross_norm": float(sum(abs(v) for v in _weights.values())), "n_names": len(_weights),
                "universe": _uni, "universe_sha": kdoc["universe_sha"], "n_universe": len(_uni),
                "booster_sha": kdoc["booster_sha"], "weights_sha": _wsha,
                "f10_sha": _F10_SHA,   # FP2-6b: the executor pins this (config f10_sha_pin) once the field is live for one anchor
                "written_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time())),
                "producer": "combo_stage_v1(kingLGBM 0.55 + V2MAIN 0.45, rev24 leg removed; base shadow_loop_v3)"}
        if _beta_field is not None:
            _doc["beta_overlay"] = _beta_field     # M3: new field only; every other key/value above is unchanged
        _raw = json.dumps(_doc).encode()
        _jp = f"{_outdir}/{A}.json"
        os.makedirs(_outdir, exist_ok=True)
        # Same filesystem, private staging: invalid bytes never reach the live target.
        with tempfile.TemporaryDirectory(prefix=f".combo-{A}-", dir=_outdir) as _stage_dir:
            _candidate_path = f"{_stage_dir}/{A}.json"
            with open(_candidate_path, "wb") as _f:
                _f.write(_raw)
            with open(_candidate_path + ".sha256", "w") as _f:
                _f.write(hashlib.sha256(_raw).hexdigest() + "  " + os.path.basename(_jp) + "\n")
            # 在发布前用实盘执行器自己的校验代码验收
            _status["step"] = "prepublish_validate_with_live_reader"
            sys.path.insert(0, f"{EXECUTOR_ROOT}/live"); sys.path.insert(0, EXECUTOR_ROOT)
            import external_book as _EB
            _vf = _EB.verify_file(_candidate_path)
            assert _vf.get("ok"), f"verify_file: {_vf.get('reason')}: {_vf.get('detail')}"
            _cfgE = {"schema": "wide_target_v1", "require_anchor_match": True, "max_age_min": 10.0,
                     "universe_sha_pin": None, "booster_sha_pin": None, "f10_sha_pin": None}
            _pt = _EB.parse_target(_vf["raw"], _cfgE, A, time.time() if not _rehearsal else
                                   time.mktime(time.strptime(_doc["written_utc"], "%Y-%m-%dT%H:%M:%SZ")) - time.timezone + 60)
            assert _pt.get("ok"), f"parse_target: {_pt.get('reason')}: {_pt.get('detail')}"
            assert _pt["gross_outside"] == 0.0, f"宇宙外权重 {_pt['gross_outside']}"
            assert _pt["n_in_universe"] >= 150 and _pt["gross_in"] > 0.4
            # M3: the executor's own field validator on the bytes actually staged (record only — never blocks the book)
            if _beta_field is not None:
                try:
                    import beta_overlay as _BOX
                    _bv = _BOX.validate_field(json.loads(_vf["raw"].decode()).get("beta_overlay"), A)
                    _status["beta_overlay"]["reader_verdict"] = {"ok": _bv["ok"], "reason": _bv["reason"],
                                                                 "detail": (_bv.get("detail") or "")[:160],
                                                                 "betas_sha256": _bv.get("betas_sha256")}
                    if not _bv["ok"] and _beta_page is None:
                        _beta_page = (f"combo 写者: beta_overlay 字段被执行器校验器拒绝 [{time.strftime('%m-%d %H:%M', time.gmtime(A))}锚] "
                                      f"{_bv['reason']}: {(_bv.get('detail') or '')[:160]} — 执行器 M3=on 时本锚不下对冲单。")
                except ImportError:
                    _status["beta_overlay"]["reader_verdict"] = "executor tree predates M3 (no live/beta_overlay.py) — not checked"
                except Exception as _bve:            # noqa: BLE001
                    _status["beta_overlay"]["reader_verdict"] = f"validator raised {type(_bve).__name__}: {str(_bve)[:120]}"
            verify_source_snapshot(_source_snapshot["identity"])
            verify_current_feature_cache(MINI, _feature_identity)
            if (not _rehearsal) and time.time() > _deadline:
                _bail("发布前已过硬截止 N+22:40，拒绝替换目标文件")
            os.replace(_candidate_path, _jp)
            os.replace(_candidate_path + ".sha256", _jp + ".sha256")
        _status.update(ok=True, step="done", n=len(_weights), gross=_doc["gross_norm"],
                       reader_ok=True, n_in_universe=_pt["n_in_universe"], age_s=_pt["age_s"],
                       elapsed_s=round(time.time() - _now0, 1), rehearsal=_rehearsal)
        try:   # C (durable, DESIGN_executor_durable_state_2026-09-25): memory bytes -> with-write -> fsync -> read-back byte compare -> os.replace; failure raises, target untouched
            DIO.write_json_durable(f"{WS}/state/combo_live_status.json", _status, indent=1)
        except DIO.DurableWriteError as _se:   # the target is ALREADY published: a status-file failure must not become a reported abort
            log(f"STATUS_WRITE_FAILED after publication (durable write refused; previous combo_live_status.json kept intact): {_se}")
        log(f"⑤ COMBO_LIVE 写者完成 rehearsal={_rehearsal} n={len(_weights)} gross={_doc['gross_norm']:.4f} 读者验收 ok age={_pt['age_s']}s")
        if _beta_page is not None and not _rehearsal:
            try:                                      # M3: after publication (never spends the deadline margin), and a page
                _page("HIGH", _beta_page)             #     failure can never turn a published book into a reported abort
            except Exception:                         # noqa: BLE001
                pass
    except SystemExit:
        raise
    except Exception as _e:
        # Never restore King: this invocation may not have published, or the
        # deadline may have passed. A partial pair is rejected by the reader.
        _bail(f"{type(_e).__name__}: {str(_e)[:220]}")
    # gap 类修复: 状态来源需要人知道(被拒文件 / 越界 / 无有效状态)⇒ 发布之后 HIGH 页报(不占截止余量; 与 M3 同: 演练不发, 只记)
    if _GAP_PAGE:
        _gap_msg = (f"combo 写者: 上一锚状态非常规 [{time.strftime('%m-%d %H:%M', time.gmtime(A))}锚] 已发布, 来源如下(界 {PS.MAX_GAP_ANCHORS} 锚):\n"
                    + "\n".join(_GAP_PAGE))[:1500]
        log(f"GAP_PAGE {'(rehearsal: recorded, not sent)' if _rehearsal else 'HIGH'}: {_gap_msg.replace(chr(10), ' | ')}")   # one log line per event
        if not _rehearsal:
            try:
                _page("HIGH", _gap_msg)
            except Exception:                         # noqa: BLE001 — a page failure never turns a published book into an abort
                pass
