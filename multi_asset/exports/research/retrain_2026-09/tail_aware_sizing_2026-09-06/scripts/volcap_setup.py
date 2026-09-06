"""volcap_setup.py — PREREG_tail_aware_sizing_2026-09-06 §1 device: w10_volcap.py = health_check/w10_health.py (sha 8684d9a9…, copied verbatim as
w10_health_orig.py) + ONE knob VOLCAP_GAMMA ∈ {0, 0.5, 1.0} and the per-name cap
    cap_i = capw · min(1, (σ_med/σ_i)^γ),  σ_i = sample std of the name's y4 over meta anchors t−42…t−1 (≥30 finite values, else σ_i := σ_med ⇒ ratio 1),
    σ_med = median of σ_i over the anchor's members with a valid σ_i,
inserted right after the flat clip of the kc book (w = np.clip(w, -capw, capw)) and of the F10 book (_wf = np.clip(_wf, -capw, capw)); the device's own
re-normalisation after the clip is unchanged. γ = 0 never enters any patched branch (bitwise identity, receipt = check_equiv_vc.py vs health_check
M1_UPIT_{prod,log}_s{42,2027}_ccal). Report-only per-anchor diagnostics (kc book target layer): n_capped (|w| > cap_i before the cap), gross share removed
by the cap (before renorm), N_eff after renorm, gross share of the high-σ tercile after renorm; plus σ and cap-ratio matrices (float16) for the judge.
Also reproduces health_check's dev/ (log caliber) and dev_alt/ (prod caliber) input layouts under ROOT (setup_trackC.sh recipe, readlink -f targets).
Writes only under /workspace/review_scratch/tail_aware_sizing/. Prints the diff and both device shas."""
import os, hashlib, difflib
ROOT = "/workspace/review_scratch/tail_aware_sizing"; HC = "/workspace/review_scratch/health_check"
os.makedirs(ROOT, exist_ok=True)
src = open(f"{HC}/w10_health.py").read(); open(f"{ROOT}/w10_health_orig.py", "w").write(src)
def rep(t, old, new):
    assert t.count(old) == 1, (t.count(old), old[:90]); return t.replace(old, new)
p = src
# knob + self-report
p = rep(p, '_CFG = {"COSTB_JSON": COSTB_JSON,',
        'VOLCAP_GAMMA = float(os.environ.get("VOLCAP_GAMMA", "0")); assert VOLCAP_GAMMA in (0.0, 0.5, 1.0), f"VOLCAP_GAMMA 白名单外: {VOLCAP_GAMMA}"   # PREREG_tail_aware_sizing_2026-09-06 §1: per-name cap capw·min(1,(σ_med/σ_i)^γ); 0 = bitwise-unchanged path\n'
           'VOLCAP_WIN = 42; VOLCAP_MIN_N = 30   # frozen: σ_i over meta anchors t−42…t−1 (7 days), ≥30 finite y4 values\n'
           '_CFG = {"VOLCAP_GAMMA": VOLCAP_GAMMA, "VOLCAP_WIN": VOLCAP_WIN, "VOLCAP_MIN_N": VOLCAP_MIN_N, "COSTB_JSON": COSTB_JSON,')
p = rep(p, 'print("CONFIG " + json.dumps(_CFG), flush=True)   # E-0826-C/D: 装置必须自报全部生效配置\n',
        '_CFG["VOLCAP"] = {"device": "w10_volcap.py = health_check w10_health.py (sha256 8684d9a9…) + VOLCAP_GAMMA per-name realised-vol cap after the flat clip of both books (kc L222 / F10 L260 form) + per-anchor diagnostics; γ=0 ⇒ bitwise-unchanged path", "device_sha256": _hl.sha256(open(__file__, "rb").read()).hexdigest()}\n'
           'print("CONFIG " + json.dumps(_CFG), flush=True)   # E-0826-C/D: 装置必须自报全部生效配置\n')
# σ_i matrix (causal rolling std of the device's own y4, whichever caliber's meta is mounted)
p = rep(p, 'yrs = np.array([time.gmtime(int(t)).tm_year for t in E_ts]); nA = len(E_ts); NW = 829\n',
        'yrs = np.array([time.gmtime(int(t)).tm_year for t in E_ts]); nA = len(E_ts); NW = 829\n'
        'VC_SIG = None; VC_RATIO = np.ones((nA, NW), np.float32); VC_DIAG = np.full((nA, 4), np.nan)   # diag cols: n_capped, gross_removed_share, neff_after_renorm, hivol_tercile_gross_share\n'
        'if VOLCAP_GAMMA > 0:   # σ_i(t) = sample std (ddof=1) of y4 over meta anchors t−VOLCAP_WIN … t−1, NaN if < VOLCAP_MIN_N finite values (causal: anchor t−1 label ends at E_t)\n'
        '    _yv = np.where(np.isfinite(y4), y4, 0.0).astype(np.float64); _fv = np.isfinite(y4).astype(np.int64)\n'
        '    _S1 = np.concatenate([np.zeros((1, NW)), np.cumsum(_yv, 0)]); _S2 = np.concatenate([np.zeros((1, NW)), np.cumsum(_yv * _yv, 0)]); _Nv = np.concatenate([np.zeros((1, NW), np.int64), np.cumsum(_fv, 0)])\n'
        '    VC_SIG = np.full((nA, NW), np.nan)\n'
        '    for _i in range(nA):\n'
        '        _lo = max(0, _i - VOLCAP_WIN); _n = _Nv[_i] - _Nv[_lo]; _s1 = _S1[_i] - _S1[_lo]; _s2 = _S2[_i] - _S2[_lo]\n'
        '        with np.errstate(invalid="ignore", divide="ignore"):\n'
        '            _var = (_s2 - _s1 * _s1 / np.maximum(_n, 1)) / np.maximum(_n - 1, 1)\n'
        '        VC_SIG[_i] = np.where(_n >= VOLCAP_MIN_N, np.sqrt(np.maximum(_var, 0.0)), np.nan)\n'
        '    print("VOLCAP_DEF " + json.dumps({"gamma": VOLCAP_GAMMA, "win": VOLCAP_WIN, "min_n": VOLCAP_MIN_N, "sigma_finite_share": round(float(np.isfinite(VC_SIG).mean()), 4), "sigma_median_bps_by_year": {int(y): round(float(np.nanmedian(VC_SIG[yrs == y]) * 1e4), 1) for y in sorted(set(yrs.tolist()))}}), flush=True)\n')
# per-anchor ratio + kc cap (after the flat clip; renorm below unchanged)
p = rep(p, '        w /= g; capw = 2.5 / max(int(sel.sum()), 1); w = np.clip(w, -capw, capw)\n',
        '        w /= g; capw = 2.5 / max(int(sel.sum()), 1); w = np.clip(w, -capw, capw)\n'
        '        if VOLCAP_GAMMA > 0:   # PREREG_tail_aware_sizing §1: cap_i = capw·min(1,(σ_med/σ_i)^γ); names without a valid σ_i keep capw; ranking and gross untouched\n'
        '            _sg = VC_SIG[i, m]; _okg = np.isfinite(_sg) & (_sg > 0); _smed = float(np.median(_sg[_okg])) if _okg.any() else np.nan\n'
        '            _rat = np.ones(len(m))\n'
        '            if np.isfinite(_smed) and _smed > 0: _rat[_okg] = np.minimum(1.0, (_smed / _sg[_okg]) ** VOLCAP_GAMMA)\n'
        '            VC_RATIO[i, m] = _rat.astype(np.float32); _capi = capw * _rat; _wb = np.abs(w).copy()\n'
        '            w = np.clip(w, -_capi, _capi)\n'
        '            _wa = np.abs(w); _g2b = _wa.sum(); _wn = _wa / _g2b if _g2b > 1e-9 else _wa\n'
        '            _hi = np.zeros(len(m), bool)\n'
        '            if _okg.sum() >= 3: _hi[_okg] = _sg[_okg] >= np.percentile(_sg[_okg], 200.0 / 3)\n'
        '            VC_DIAG[i] = [float(((_wb > _capi + 1e-15) & sel).sum()), float(1.0 - _wa.sum() / _wb.sum()) if _wb.sum() > 1e-12 else np.nan, float(1.0 / np.sum(_wn ** 2)) if _g2b > 1e-9 else np.nan, float(_wn[_hi].sum())]\n')
# F10 book cap (same form, same _capi)
p = rep(p, '                _wf = np.clip(_wf, -capw, capw)\n',
        '                _wf = np.clip(_wf, -capw, capw)\n'
        '                if VOLCAP_GAMMA > 0: _wf = np.clip(_wf, -_capi, _capi)   # PREREG_tail_aware_sizing §1: F10 book, same per-name cap\n')
# save diagnostics (rec/W arrays unchanged)
p = rep(p, 'legs_king=LRa["king"], legs_rev24=LRa["rev24"], legs_fund=LRa["fund"], **save)',
        'legs_king=LRa["king"], legs_rev24=LRa["rev24"], legs_fund=LRa["fund"], **({"volcap_ratio": VC_RATIO.astype(np.float16), "volcap_sigma": VC_SIG.astype(np.float16), "volcap_diag": VC_DIAG, "volcap_meta_ts": E_ts} if VOLCAP_GAMMA > 0 else {}), **save)')
open(f"{ROOT}/w10_volcap.py", "w").write(p)
diff = "".join(difflib.unified_diff(src.splitlines(True), p.splitlines(True), fromfile="w10_health.py", tofile="w10_volcap.py")); open(f"{ROOT}/device.diff", "w").write(diff); print(diff)
for f in (f"{HC}/w10_health.py", f"{ROOT}/w10_health_orig.py", f"{ROOT}/w10_volcap.py"): print("SHA256", hashlib.sha256(open(f, "rb").read()).hexdigest(), f)
# dev layouts
for v in ("dev", "dev_alt"):
    d = f"{ROOT}/{v}"
    for sub in ("pod_backup_2026-08-21", "probe_artifacts", "logs"): os.makedirs(f"{d}/{sub}", exist_ok=True)
    for f in ("nets_histv2_0_0_0.npy", "nets_histv2_-30_2_42.npy", "slow_pred_hist_oos.npy", "wide_panel_4h_hist_v2.npz", "wide_fea_hist_meta.npz"):
        t = os.path.realpath(f"{HC}/{v}/pod_backup_2026-08-21/{f}"); l = f"{d}/pod_backup_2026-08-21/{f}"
        if os.path.islink(l): os.remove(l)
        os.symlink(t, l)
    for f in ("f8_2026-08-22", "dlw_2026-08-22"):
        t = os.path.realpath(f"{HC}/{v}/{f}"); l = f"{d}/{f}"
        if os.path.islink(l): os.remove(l)
        os.symlink(t, l)
    for f in ("pod_backup_2026-08-21/nets_histv2_0_0_0.npy", "pod_backup_2026-08-21/slow_pred_hist_oos.npy", "pod_backup_2026-08-21/wide_fea_hist_meta.npz", "pod_backup_2026-08-21/wide_panel_4h_hist_v2.npz", "f8_2026-08-22", "dlw_2026-08-22"):
        a = os.path.realpath(f"{d}/{f}"); b = os.path.realpath(f"{HC}/{v}/{f}"); print("SAME" if a == b else "DIFF", v, f, a)
print("VOLCAP_SETUP_DONE")
