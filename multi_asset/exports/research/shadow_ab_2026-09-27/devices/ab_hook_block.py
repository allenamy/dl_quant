# ═══ SHADOW_AB HOOK (fresh 2026-09-27; inserted ONLY into the SANDBOX copy of combo_stage.py, right after the ④ COMBO log line) ═══
# Computes the shadow arm books with the stage's OWN objects (legz, zf, w3m, rn8_m, FTRIM_HI, chain, exec_reshape, H_kc_prev, H_fc_prev,
# sm_kc, sm_fc, combo) so no arithmetic is re-implemented. Each arm carries its OWN kc/fc EMA state (read from SHADOW_AB_IN, else
# warm-started from the live state this stage loaded, recorded). Writes only under SHADOW_AB_OUT (inside the sandbox). The live
# computation above is not modified; H is restored afterwards.
if os.environ.get("SHADOW_AB_IN") and os.environ.get("SHADOW_AB_OUT"):
    import json as _abj
    _ABI, _ABO = os.environ["SHADOW_AB_IN"], os.environ["SHADOW_AB_OUT"]
    os.makedirs(_ABO, exist_ok=True)
    _ab_H_saved = H
    _k = np.nan_to_num(legz["king"]); _f = np.nan_to_num(legz["fund"]); _zfa = np.nan_to_num(zf)
    _wk, _wf = float(w3m[0]), float(w3m[2])
    _wkh = 0.5 * _wk; _sh = _wkh + _wf
    _wkh, _wfh = ((_wkh / _sh, _wf / _sh) if _sh > 1e-12 else (0.5, 0.5))
    # arm -> (z_kc before FTRIM, z_fc before FTRIM, seats actually used, mechanism)
    _AB_ARMS = {
        "NOKING":   (_wf * _f,               _wk * _zfa + _wf * _f,   [0.0, 0.0, _wf],   "King score removed from the King book; F10 book unchanged"),
        "KHALF":    (_wkh * _k + _wfh * _f,  _wkh * _zfa + _wfh * _f, [_wkh, 0.0, _wfh], "model seat halved (King and F10 both via the seat), renormalised"),
        "FUNDONLY": (_f.copy(),              _f.copy(),               [0.0, 0.0, 1.0],   "funding leg only in both books"),
    }

    def _ab_band(z):
        return (z < 0) & np.isfinite(rn8_m) & (rn8_m <= FTRIM_HI)

    def _ab_load(arm, book, fallback):
        p = os.path.join(_ABI, f"{arm}_{book}.npz")
        if os.path.exists(p):
            zz = np.load(p)
            if int(zz["anchor"]) == A - 14400:
                v = np.zeros(NW); v[zz["idx"].astype(np.int64)] = zz["val"].astype(np.float64)
                return v, "own"
            return fallback.copy(), f"warmstart_live(state anchor {int(zz['anchor'])} != {A - 14400})"
        return fallback.copy(), "warmstart_live(no arm state)"

    def _ab_save(p, anchor, vec, extra=None):
        vec = np.zeros(NW) if vec is None else vec
        nz = np.where(np.abs(vec) > 1e-9)[0]
        _hb = io.BytesIO(); np.savez(_hb, anchor=anchor, idx=nz, val=vec[nz], **(extra or {}))
        with open(p, "wb") as _fh: _fh.write(_hb.getvalue()); _fh.flush(); os.fsync(_fh.fileno())

    _ab_meta = {"anchor": int(A), "w3m": [float(x) for x in w3m], "names": list(syms), "arms": {}}
    _ab_save(os.path.join(_ABO, "LIVE_REPLAY_combo.npz"), A, combo)
    _ab_save(os.path.join(_ABO, "LIVE_REPLAY_kc.npz"), A, sm_kc); _ab_save(os.path.join(_ABO, "LIVE_REPLAY_fc.npz"), A, sm_fc)
    _ab_meta["arms"]["LIVE_REPLAY"] = {"seats": [float(w3m[0]), 0.0, float(w3m[2])], "kc_src": kc_src, "fc_src": fc_src,
                                       "gross": float(np.abs(combo).sum()), "mechanism": "in-service combo recomputed (identity control)"}
    for _arm, (_zk, _zc, _seats, _mech) in _AB_ARMS.items():
        _bk, _bc = _ab_band(_zk), _ab_band(_zc)
        _zk = np.where(_bk, 0.0, _zk); _zc = np.where(_bc, 0.0, _zc)
        _Hk, _srck = _ab_load(_arm, "kc", H_kc_prev); _Hc, _srcc = _ab_load(_arm, "fc", H_fc_prev)
        H = _Hk; _smk = chain(_zk)
        H = _Hc; _smc = chain(_zc)
        H = _ab_H_saved
        if _smk is None or _smc is None:
            _ab_meta["arms"][_arm] = {"UNDEFINED": "chain returned None (zero gross)", "kc_none": _smk is None, "fc_none": _smc is None}
            continue
        _cmb = exec_reshape(0.55 * _smk + 0.45 * _smc)
        _ab_save(os.path.join(_ABO, f"{_arm}_combo.npz"), A, _cmb)
        _ab_save(os.path.join(_ABO, f"{_arm}_kc.npz"), A, _smk); _ab_save(os.path.join(_ABO, f"{_arm}_fc.npz"), A, _smc)
        _ab_meta["arms"][_arm] = {"seats": _seats, "kc_src": _srck, "fc_src": _srcc, "ftrim_n_kc": int(_bk.sum()), "ftrim_n_fc": int(_bc.sum()),
                                  "gross": float(np.abs(_cmb).sum()), "n": int((np.abs(_cmb) > 1e-9).sum()), "mechanism": _mech}
    H = _ab_H_saved
    with open(os.path.join(_ABO, "AB_META.json"), "w") as _fh:
        _abj.dump(_ab_meta, _fh, indent=1); _fh.flush(); os.fsync(_fh.fileno())
    log(f"SHADOW_AB hook: arms {list(_ab_meta['arms'])} written to {_ABO}")
# ═══ END SHADOW_AB HOOK ═══
