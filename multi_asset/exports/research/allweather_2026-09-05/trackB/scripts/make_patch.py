"""make_patch.py — Track B (PREREG_allweather_programme §3 Track B): build pod_f10_train_dro.py from the VERBATIM copy of
/workspace/pod_f10_train_ext.py (sha256 93cc2cdf…) by exact-string edits only; every anchor must occur exactly once.
Two knobs: DRO_T (group-DRO over calendar half-year eras; "inf" = off) and SS_W (short-side weight; 0 = off).
With DRO_T=inf and SS_W=0 the training-loss line and the run_span call are the verbatim baseline lines (bitwise identity expected).
usage: python3 make_patch.py <verbatim pod_f10_train_ext.py> <out pod_f10_train_dro.py>"""
import sys, hashlib
src, dst = sys.argv[1], sys.argv[2]
S = open(src, encoding="utf-8").read()
assert hashlib.sha256(S.encode("utf-8")).hexdigest() == "93cc2cdf925a1dada9190a5d86664d28c811d9ba0ecf3eaf377d54fc554f2598", "verbatim trainer sha mismatch"
def rep(old, new):
    global S
    assert S.count(old) == 1, (S.count(old), old[:80])
    S = S.replace(old, new)
# (1) knobs (after LPP)
rep('LPP = float(os.environ.get("LPP", "0.0"))      # L2 持久罚: 惩罚 |u_t − u_{t−1}|\n',
    'LPP = float(os.environ.get("LPP", "0.0"))      # L2 持久罚: 惩罚 |u_t − u_{t−1}|\n'
    'DRO_T = float(os.environ.get("DRO_T", "inf"))  # Track B: group-DRO 时代温度(单位 = 训练窗净额 bps/锚); inf = 关(损失行逐字基线)\n'
    'SS_W = float(os.environ.get("SS_W", "0"))      # Track B: 空侧权重(PREREG_l1ss 简化定型, 两侧权重均值归一为 1); 0 = 关(损失行逐字基线)\n')
# (2) era ids (calendar half-years) next to the other causal context
rep('FLAGT = torch.from_numpy(FLAG)\n',
    'FLAGT = torch.from_numpy(FLAG)\n'
    'ERA = np.array([time.gmtime(int(t)).tm_year * 2 + (1 if time.gmtime(int(t)).tm_mon > 6 else 0) for t in E_ts])   # Track B: 日历半年时代 id\n')
# (3) self-report
rep('       "lr": LR, "win": WIN, "burn": BURN, "stride": STRIDE, "embargo": EMB,\n',
    '       "lr": LR, "win": WIN, "burn": BURN, "stride": STRIDE, "embargo": EMB, "dro_t": DRO_T, "ss_w": SS_W, "patch": "pod_f10_train_dro.py",\n')
# (4) run_span: optional per-window long-side net (per-name contribution split by the sign of the new weight; closed names by the old weight)
rep('def run_span(mdl, idx, mu, sd, tau, hard, w0=None, loss_span=None):\n',
    'def run_span(mdl, idx, mu, sd, tau, hard, w0=None, loss_span=None, sides=False):\n')
rep('    nets = []\n    for k, i in enumerate(idx):\n',
    '    nets = []; nls = []\n    for k, i in enumerate(idx):\n')
rep('        net = 1e4 * (wn * YT[i]).sum() - COST * dn\n',
    '        net = 1e4 * (wn * YT[i]).sum() - COST * dn\n'
    '        if sides:   # Track B SS_W: 逐名贡献 c_j = 1e4·wn_j·y_j − COST·|Δw_j|, 多头侧 = sign(wn_j)>0(wn_j=0 的名按旧权 w_j 归侧); 空头侧 = net − 多头侧\n'
    '            _sg = torch.where(wn != 0, wn, w); nl = (1e4 * (wn * YT[i]) - COST * torch.sqrt((wn - w) ** 2 + 1e-12))[_sg > 0].sum()\n')
rep('        if loss_span is None or k >= loss_span:\n            nets.append(net)\n',
    '        if loss_span is None or k >= loss_span:\n            nets.append(net)\n            if sides:\n                nls.append(nl)\n')
rep('        w = wn\n    return torch.stack(nets), w\n',
    '        w = wn\n    if sides:\n        return torch.stack(nets), w, torch.stack(nls)\n    return torch.stack(nets), w\n')
# (5) per-fold DRO state
rep('    best_va, best_state, va_curve, alist = -1e9, None, [], []\n',
    '    best_va, best_state, va_curve, alist = -1e9, None, [], []\n'
    '    DRO_W, DRO_ACC, dro_log = {}, {}, []   # Track B: 时代权重 W_e(上一 epoch 的时代均值净额 → softmax(−mean/T)·n_eras; epoch 0 均匀)\n')
# (6) per-epoch era weights (from the previous epoch's window nets)
rep('        tau = 0.5 - (0.5 - 0.1) * ep / max(EPOCHS - 1, 1)\n',
    '        tau = 0.5 - (0.5 - 0.1) * ep / max(EPOCHS - 1, 1)\n'
    '        if math.isfinite(DRO_T):\n'
    '            if DRO_ACC:\n'
    '                _es = sorted(DRO_ACC); _m = np.array([float(np.mean(DRO_ACC[e])) for e in _es]); _x = -_m / DRO_T; _x = _x - _x.max(); _p = np.exp(_x); _p = _p / _p.sum()\n'
    '                DRO_W = {e: float(_p[j] * len(_es)) for j, e in enumerate(_es)}\n'
    '                dro_log.append({"ep": ep, "era_mean_net": {str(e): round(float(_m[j]), 4) for j, e in enumerate(_es)}, "era_n_windows": {str(e): len(DRO_ACC[e]) for e in _es}, "W": {str(e): round(DRO_W[e], 4) for e in _es}})\n'
    '                log(f"[{YV}] ep{ep} DRO eras " + " ".join(f"{e}:{_m[j]:+.2f}/W{DRO_W[e]:.2f}" for j, e in enumerate(_es)))\n'
    '            DRO_ACC = {}\n')
# (7) training loss
rep('            nets, _ = run_span(mdl, span, mu, sd, tau, hard=False, loss_span=BURN)\n            loss = -nets.mean() + LDD * es5(nets)\n',
    '            if SS_W > 0:\n'
    '                nets, _, nls = run_span(mdl, span, mu, sd, tau, hard=False, loss_span=BURN, sides=True)\n'
    '                mean_term = 2.0 * (nls.mean() + (1.0 + SS_W) * (nets - nls).mean()) / (2.0 + SS_W)   # 两侧权重 (2, 2(1+SS_W))/(2+SS_W), 均值 1 ⇒ SS_W=0 时 = mean(net)\n'
    '            else:\n'
    '                nets, _ = run_span(mdl, span, mu, sd, tau, hard=False, loss_span=BURN)\n'
    '                mean_term = None\n'
    '            if math.isfinite(DRO_T):\n'
    '                _e = int(ERA[span[BURN]]); DRO_ACC.setdefault(_e, []).append(float(nets.mean()))\n'
    '                loss = -(float(DRO_W.get(_e, 1.0)) * (mean_term if mean_term is not None else nets.mean())) + LDD * es5(nets)\n'
    '            elif SS_W > 0:\n'
    '                loss = -mean_term + LDD * es5(nets)\n'
    '            else:\n'
    '                loss = -nets.mean() + LDD * es5(nets)\n')
# (8) record DRO log per fold
rep('                             "turnover_mean": round(float(np.mean(trn_series)), 5)}\n',
    '                             "turnover_mean": round(float(np.mean(trn_series)), 5), "dro": dro_log}\n')
open(dst, "w", encoding="utf-8").write(S)
print("wrote", dst, "sha256", hashlib.sha256(S.encode("utf-8")).hexdigest())
