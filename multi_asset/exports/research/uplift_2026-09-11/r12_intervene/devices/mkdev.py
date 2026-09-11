"""Build w12_intervene.py = PINNED w10_sleeve.py + four env-gated intervention branches.
All branches OFF  =>  bitwise-identical rec/W (GATE P)."""
import hashlib, io, sys
SRC="/workspace/uplift_2026-09-11/w10_sleeve.py"
DST="/workspace/uplift_2026-09-11/r12_intervene/w12_intervene.py"
s=open(SRC).read()
assert hashlib.sha256(s.encode()).hexdigest().startswith("b88e35a46b93d712")

# ---- A. env parsing, inserted right after the SEATNET line ----
A_OLD='SEATNET = int(os.environ.get("SEATNET", "0")); assert SEATNET in (0, 1)\n'
A_NEW=A_OLD+'''# ---- r12 intervention layer (PREREG_r12 sha256 17dd2db7b116b262...); every default == OFF ----
CEM_Q = os.environ.get("CEM_Q", ""); assert CEM_Q in ("", "0.90", "0.95", "0.99"), CEM_Q          # I-1 carry emergency: causal trailing quantile of the projected carry bill
CEM_MODE = os.environ.get("CEM_MODE", "neutral"); assert CEM_MODE in ("neutral", "derisk"), CEM_MODE
BYP_STATE = os.environ.get("BYP_STATE", ""); assert BYP_STATE in ("", "rally", "rev", "either"), BYP_STATE   # I-3 smoothing bypass on state
BYP_Q = os.environ.get("BYP_Q", ""); assert BYP_Q in ("", "0.90", "0.95"), BYP_Q
BYP_A = os.environ.get("BYP_A", ""); assert BYP_A in ("", "1.00", "0.30"), BYP_A
assert (BYP_STATE == "") == (BYP_Q == "") == (BYP_A == ""), "BYP_* must be set together or not at all"
R12_TRAIL = 2190; R12_MINH = 900   # causal reference window / minimum history before any fire
'''
assert s.count(A_OLD)==1; s=s.replace(A_OLD,A_NEW)

# ---- A2. self-report the config ----
B_OLD='"SEATNET": SEATNET,'
B_NEW='"SEATNET": SEATNET, "CEM_Q": CEM_Q, "CEM_MODE": CEM_MODE, "BYP_STATE": BYP_STATE, "BYP_Q": BYP_Q, "BYP_A": BYP_A, "R12_TRAIL": R12_TRAIL, "R12_MINH": R12_MINH,'
assert s.count(B_OLD)==1; s=s.replace(B_OLD,B_NEW)
C_OLD='_CFG["UPLIFT"] = {"device": "w10_sleeve.py'
C_NEW='_CFG["R12"] = {"device": "w12_intervene.py = PINNED w10_sleeve.py (sha256 b88e35a46b93d712...) + {CEM_*, BYP_*}; all unset => bitwise-unchanged rec/W", "src_sha256": "b88e35a46b93d712422e6b6d60bf163b841be147d49278131b63f0f47a490650", "prereg_sha256": "17dd2db7b116b2625f6e7eacab7caf9eb025876e1a3f564f32429f31a2ea551f"}\n_CFG["UPLIFT"] = {"device": "w10_sleeve.py'
assert s.count(C_OLD)==1; s=s.replace(C_OLD,C_NEW)

# ---- B. per-run state inside run() ----
D_OLD='    rec = []; WS = []; _SG = []; _SP = []; _SC = []; _SK = []\n'
D_NEW=D_OLD+'    _cem_h = []; _mkt_h = []; _s6_h = []; _DG = []   # r12: causal monitor histories (append-only, never read ahead)\n'
assert s.count(D_OLD)==1; s=s.replace(D_OLD,D_NEW)

# ---- C. bypass decision + EMA step (king chain) ----
E_OLD='''        sm = H + 0.1 * (tgt - H); trade = sm - H
        sm = np.where(np.abs(trade) < 2.5e-4, H, sm); trade = sm - H
'''
E_NEW='''        # ---- r12 I-3: causal state detector; decides THIS anchor's EMA step and band ----
        _a_ema = 0.1; _byp_fire = 0; _s6 = float("nan"); _bq = float("nan")
        if BYP_STATE:
            if len(_mkt_h) >= 6:
                _s6 = float(np.sum(np.asarray(_mkt_h[-6:])))
                if len(_s6_h) >= R12_MINH:
                    _bq = float(np.quantile(np.abs(np.asarray(_s6_h[-R12_TRAIL:])), float(BYP_Q)))
                    _fire = (_s6 >= _bq) if BYP_STATE == "rally" else ((_s6 <= -_bq) if BYP_STATE == "rev" else (abs(_s6) >= _bq))
                    if _fire: _a_ema = float(BYP_A); _byp_fire = 1
                _s6_h.append(abs(_s6))
        sm = H + _a_ema * (tgt - H); trade = sm - H
        if not _byp_fire:
            sm = np.where(np.abs(trade) < 2.5e-4, H, sm); trade = sm - H
'''
assert s.count(E_OLD)==1; s=s.replace(E_OLD,E_NEW)

# ---- D. F10 chain EMA step ----
F_OLD='''                _smf = HF + 0.1 * (_tgtf - HF)
                _trf = _smf - HF
                _smf = np.where(np.abs(_trf) < 2.5e-4, HF, _smf)
'''
F_NEW='''                _smf = HF + _a_ema * (_tgtf - HF)
                _trf = _smf - HF
                if not _byp_fire:
                    _smf = np.where(np.abs(_trf) < 2.5e-4, HF, _smf)
'''
assert s.count(F_OLD)==1; s=s.replace(F_OLD,F_NEW)

# ---- E. carry emergency, applied to the blended book right after FTPOS, before any accounting ----
G_OLD='''        _smk = sm                     # ★ king 书自己的 sm 必须留住: 它的 EMA 态独立推进
        sm = smb                      # 此后一切记账(盈亏/成本/carry/深度)都在混合书上
'''
G_NEW='''        _smk = sm                     # ★ king 书自己的 sm 必须留住: 它的 EMA 态独立推进
        sm = smb                      # 此后一切记账(盈亏/成本/carry/深度)都在混合书上
        # ---- r12 I-1: carry emergency.  Monitor = the projected carry bill of the book we are about
        #      to hold, on the SAME FN/iv panel row the deployed FTRIM already reads at decision time.
        #      Threshold = causal trailing quantile (history is the PRE-intervention bill).  Action =
        #      greedy zero of the worst payers until bill <= theta.  Position-level, like FTPOS: the
        #      EMA states are untouched, so next anchor pays the re-entry trade (in-book marginal).
        _cem_fire = 0; _cem_n = 0; _cth = float("nan")
        _fn_c = np.nan_to_num(FN[j, m], nan=0.0)
        _iv_c = IV[j, m]; _iv_c = np.where(np.isfinite(_iv_c) & (_iv_c > 0), _iv_c, 8.0)
        _c = sm[m] * _fn_c * (4.0 / _iv_c) * 1e4
        _Sg = float(np.abs(sm).sum()); _Sc = float(_c.sum())
        _bill0 = (_Sc / _Sg) if _Sg > 1e-9 else 0.0
        _bill1 = _bill0
        if CEM_Q:
            if len(_cem_h) >= R12_MINH:
                _cth = float(np.quantile(np.asarray(_cem_h[-R12_TRAIL:]), float(CEM_Q)))
                if _bill0 > _cth:
                    _cem_fire = 1
                    _o = np.argsort(-_c)
                    _cs = np.cumsum(_c[_o]); _gs = np.cumsum(np.abs(sm[m])[_o])
                    _bk = (_Sc - _cs) / np.maximum(_Sg - _gs, 1e-12)
                    _pay = (_c[_o] > 0)
                    _hit = np.where(_pay & (_bk <= _cth))[0]
                    _cem_n = int(_hit[0]) + 1 if len(_hit) else int(_pay.sum())
                    if _cem_n > 0:
                        _kill = np.zeros(NW, bool); _kill[m[_o[:_cem_n]]] = True
                        sm = np.where(_kill, 0.0, sm)
                        _g1 = float(np.abs(sm).sum())
                        if CEM_MODE == "neutral" and _g1 > 1e-9: sm = sm * (_Sg / _g1)
                        _c2 = sm[m] * _fn_c * (4.0 / _iv_c) * 1e4; _g2 = float(np.abs(sm).sum())
                        _bill1 = (float(_c2.sum()) / _g2) if _g2 > 1e-9 else 0.0
            _cem_h.append(_bill0)
'''
assert s.count(G_OLD)==1; s=s.replace(G_OLD,G_NEW)

# ---- F. record the monitor history + diagnostics (market state appended AFTER use) ----
H_OLD='''        WS.append(sm.astype(np.float32))
'''
H_NEW='''        WS.append(sm.astype(np.float32))
        _yv_ok = np.isfinite(y4[i, m])
        _mkt_h.append(float(np.median(yv[_yv_ok])) if _yv_ok.sum() >= 30 else 0.0)   # realised at anchor i, read only at i+1..
        _DG.append((int(E_ts[i]), _bill0, _bill1, float(_cem_fire), float(_cem_n), _cth,
                    float(_byp_fire), _a_ema, _s6, _bq, _mkt_h[-1]))
'''
assert s.count(H_OLD)==1; s=s.replace(H_OLD,H_NEW)

I_OLD='    return np.array(rec), np.stack(WS), ((np.array(_SG)'
I_NEW='    globals()["R12_DIAG_LAST"] = np.array(_DG, float)\n'+I_OLD
assert s.count(I_OLD)==1; s=s.replace(I_OLD,I_NEW)

J_OLD='    save[f"{nm}_rec"] = R\n'
J_NEW=J_OLD+'    save[f"{nm}_DIAG"] = globals()["R12_DIAG_LAST"]\n'
assert s.count(J_OLD)==1; s=s.replace(J_OLD,J_NEW)

K_OLD='COLS = ["ts", "net",'
K_NEW='R12_DIAG_COLS = ["ts", "bill_pre", "bill_post", "cem_fire", "cem_n", "cem_th", "byp_fire", "a_ema", "s6", "byp_q", "mkt_med"]\nCOLS = ["ts", "net",'
assert s.count(K_OLD)==1; s=s.replace(K_OLD,K_NEW)
L_OLD='np.savez_compressed(f"{PD}/w10_ablation_series{_OT}.npz", cols=np.array(COLS),'
L_NEW='np.savez_compressed(f"{PD}/w10_ablation_series{_OT}.npz", diag_cols=np.array(R12_DIAG_COLS), cols=np.array(COLS),'
assert s.count(L_OLD)==1; s=s.replace(L_OLD,L_NEW)

open(DST,"w").write(s)
print("WROTE",DST,"sha256",hashlib.sha256(s.encode()).hexdigest())
print("lines",len(s.splitlines()),"(pinned had",len(open(SRC).read().splitlines()),")")
