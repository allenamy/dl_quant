## R. Receipts (device / equivalence / commands / artifacts)

### R.1 Device identity
| file | sha256 |
|---|---|
| w10_seat2.py | `5285f0049286d8964d10ee1d4ce9e428b9343af3048924e94f52ae55eda0b8f0` |
| w10_health_orig.py | `8684d9a9f43a8d15beaa559cd12bd8f2977a3d088b01b93835f60f2bbf98a53d` |
| device.diff | `2d7418dca79b03fa419630503f8779061b19e54e0775103f099005a77fb05a17` |
| check_equiv.py | `63b96c2855529acc5eae549cf142667888a8216d6906011695d294f287d64d09` |
| judge_seat2.py | `fef21eb752c10eb9df11495e71424fcd7a2efd1338d4e8cc0d56b9709c02c0b6` |
| run_arm.sh | `285522ce4e83483e057d685ca80530dfd463c828f9df073deeb159a07253d990` |
| chain_b0.sh | `619a00fb8b8ce8c597e9bcd984d799938aa49c5fa94501e944b59167badaf85e` |
| chain_arms.sh | `ebad1da04952259468620f2753f0ac05c0fe9954a5d2c14a054c65e4160799cc` |
| /workspace/review_scratch/health_check/w10_health.py | `8684d9a9f43a8d15beaa559cd12bd8f2977a3d088b01b93835f60f2bbf98a53d` |
| /workspace/review_scratch/health_check/masks/umask_UPIT.npz | `ccb7a0805be2a106898467b5ffef3a8fd4813a659e044492c0a437b0e5d7aece` |
| /workspace/review_scratch/health_check/calib/costb_fee_steady.json | `9349ca634747772dcfc9adfb7a42a5c7b5b34f60bc7f31bc6fd95c4ae5d0fc42` |
| /workspace/shadow_bundle_v3/slow_pred_pinned.npy | `158cd4ac8f8f30f7f41a5a6cba0bd19a450ce756727e4aeae3d4e4b0b67d0054` |
| /workspace/port_w10/f8_2026-08-22/preds/f10_V2MAIN_s42.npy | `baf747ceb31f10d614ffac79b9c969c499e1c3e9f82edfec246d7cfb0f353ace` |
| /workspace/port_w10/f8_2026-08-22/preds/f10_V2MAIN_s2027.npy | `c742ffaa1f4397aee55a31a5486aabfd89ae28624123bbda535a7d41851b2a0b` |
| /workspace/data/wide_fea_v2ext_meta.npz | `4b1b6047107d25573244a84df69d45bc987ada89b6731e826c867a230e247082` |
| /workspace/review_scratch/refute_C6_2/altrun/meta_newprod.npz | `831857dd6a2035235647158d26d0155d17c7e77d85fa248b2ae9a617658ddf13` |
| /workspace/data/wide_panel_4h_v2ext.npz | `5e67c0559daa904d8f0526b6e268e93dcb45aab89d82646cf79a794445481116` |

### R.2 Device diff (w10_health.py → w10_seat2.py)
```diff
--- w10_health_orig.py	2026-09-05 07:08:32.000000000 +0000
+++ w10_seat2.py	2026-09-05 07:17:29.000000000 +0000
@@ -31,6 +31,9 @@
 FTRIM = os.environ.get("FTRIM", "off"); assert FTRIM in ("off", "zero"), FTRIM   # 部署态 FTRIM(pre-z 排除 rn8<=-10bp 空头, 两链), 与 w10_ftrim_band pre/zero/(-1.0,-0.0010] 同构
 SEATNET = int(os.environ.get("SEATNET", "0")); assert SEATNET in (0, 1)
 SEATF10 = int(os.environ.get("SEATF10", "0")); assert SEATF10 in (0, 1)   # T1: F10 链用 F10 自己的 msharpe 席位(四腿腿收益)
+SEATCOST_BPS = float(os.environ.get("SEATCOST_BPS", "0")); assert SEATCOST_BPS in (0.0, 2.035), f"SEATCOST_BPS 白名单外: {SEATCOST_BPS}"   # seat_round2 B3 (PREREG_seat_round2 §1): seat input r_leg,t − SEATCOST_BPS·turn_leg,t, turn = Σ|z/g_t − z/g_{t−1}| of that leg's own unit-gross rank book (axisB R2 code, legs()); applied in w3_at only when > 0 ⇒ default path unchanged
+PHIDYN = int(os.environ.get("PHIDYN", "0")); assert PHIDYN in (0, 1)   # seat_round2 B4: per-anchor φ_t = shp_f10book/(shp_kingbook + shp_f10book), shp = mean/std (ddof 0, +1e-9, as msharpe) over the previous PHIDYN_LOOK recorded anchors strictly before t of each book's own OOS net return (price − carry − cost of that book's weights, per unit gross); negatives → 0; both 0 ⇒ PHI; clip [0.2, 0.8]; PHI until PHIDYN_LOOK rows exist
+PHIDYN_LOOK = 900; PHIDYN_CLIP = (0.2, 0.8)
 KTAIL = int(os.environ.get("KTAIL", "0")); assert KTAIL in (0, 1)         # T2: king 作尾部否决(fund 多尾中 king 秩底 20% / 空尾中 king 秩顶 20% 置零)
 KMOD = float(os.environ.get("KMOD", "0")); assert KMOD in (0.0, 0.5)       # T3: z ×= (1 + KMOD·xz(king))
 KMOD_AGREE = float(os.environ.get("KMOD_AGREE", "0")); assert KMOD_AGREE in (0.0, 0.5)
@@ -48,10 +51,12 @@
     assert len(_tiers) == 3, f"COSTB_JSON must give 3 tiers in device order (qv4h>=5e6, >=1e6, rest); got {len(_tiers)}"
     COST_B_OVERRIDE = [(float(t["maker_bps"]), float(t["taker_bps"]), float(t["maker_share"])) if isinstance(t, dict) else (float(t[0]), float(t[1]), float(t[2])) for t in _tiers]
 UMASK_SCOPE = os.environ.get("UMASK_SCOPE", "members"); assert UMASK_SCOPE in ("members", "trade", "m1"), UMASK_SCOPE   # m1 (team-lead refinement 2026-09-05) = live M1 semantics: members = universe ∩ listed for king/rev24/F10 and the trade set; fund z = rank within the 829 base (xz_in_base)   # members = original semantics (mask shrinks the member set = rank base AND trade set); trade = mask restricts only `sel` (rank base stays MEMBERS_TOPN) = PREREG §0 row 2 "MEMBERS_TOPN=829(秩基)+ UMASK(交易集)"
-_CFG = {"COSTB_JSON": COSTB_JSON, "COST_B": None, "UMASK_SCOPE": UMASK_SCOPE, "REF_SKIP": REF_SKIP, "KMOD_F10": KMOD_F10, "KMOD_L": KMOD_L, "KMOD_AGREE": KMOD_AGREE, "SEATF10": SEATF10, "KTAIL": KTAIL, "KMOD": KMOD, "SEATNET": SEATNET, "FUNDSCALE": FUNDSCALE, "FEMAT_NPZ": FEMAT_NPZ, "SLOW_NPY": os.environ.get("SLOW_NPY"), "W3FIX": W3FIX, "MEMBERS_TOPN": MEMBERS_TOPN, "TRADE_TOPN": TRADE_TOPN, "FTRIM": FTRIM, "UMASK_NPZ": os.environ.get("UMASK_NPZ"), "LOOK": LOOK, "WRULE": WRULE, "CAL": CAL, "LEGS": LEGS, "PHI": PHI, "FSEED": FSEED,
+_CFG = {"SEATCOST_BPS": SEATCOST_BPS, "PHIDYN": PHIDYN, "PHIDYN_LOOK": PHIDYN_LOOK, "PHIDYN_CLIP": list(PHIDYN_CLIP), "COSTB_JSON": COSTB_JSON, "COST_B": None, "UMASK_SCOPE": UMASK_SCOPE, "REF_SKIP": REF_SKIP, "KMOD_F10": KMOD_F10, "KMOD_L": KMOD_L, "KMOD_AGREE": KMOD_AGREE, "SEATF10": SEATF10, "KTAIL": KTAIL, "KMOD": KMOD, "SEATNET": SEATNET, "FUNDSCALE": FUNDSCALE, "FEMAT_NPZ": FEMAT_NPZ, "SLOW_NPY": os.environ.get("SLOW_NPY"), "W3FIX": W3FIX, "MEMBERS_TOPN": MEMBERS_TOPN, "TRADE_TOPN": TRADE_TOPN, "FTRIM": FTRIM, "UMASK_NPZ": os.environ.get("UMASK_NPZ"), "LOOK": LOOK, "WRULE": WRULE, "CAL": CAL, "LEGS": LEGS, "PHI": PHI, "FSEED": FSEED,
         "FPRED": os.environ.get("FPRED", "(default f10_V2MAIN_s{FSEED})")}
 import hashlib as _hl
 _CFG["HEALTH"] = {"device": "w10_health.py = w10_universe_recheck.py (sha256 5424aceb…, = port w10_universe.py + REF_SKIP) + COSTB_JSON cost-tier override + UMASK_SCOPE in {members (original), trade, m1 (fund z in the 829 base, other legs and trade set within the universe)} + legs() series saved; default path (all unset) bitwise-unchanged", "device_sha256": _hl.sha256(open(__file__, "rb").read()).hexdigest()}
+_CFG["SEAT2"] = {"device": "w10_seat2.py = w10_health.py (sha256 8684d9a9…) + SEATCOST_BPS (per-leg rank-book turnover recorded in legs() for king/rev24/fund/f10, deducted from the seat input in w3_at) + PHIDYN (per-book own net return per unit gross recorded every anchor; φ_t replaces PHI in the blend) + seat2 per-anchor series saved (phi_t, F10-book seat, per-book nets); default path (SEATCOST_BPS=0, PHIDYN=0) bitwise-unchanged in all four rec/W arrays",
+                 "device_sha256": _hl.sha256(open(__file__, "rb").read()).hexdigest(), "SEATCOST_BPS": SEATCOST_BPS, "PHIDYN": PHIDYN, "PHIDYN_LOOK": PHIDYN_LOOK, "PHIDYN_CLIP": list(PHIDYN_CLIP), "PHIDYN_FALLBACK": PHI}
 print("CONFIG " + json.dumps(_CFG), flush=True)   # E-0826-C/D: 装置必须自报全部生效配置
 t0 = time.time()
 MT = np.load(f"{B}/wide_fea_hist_meta.npz", allow_pickle=True)
@@ -133,6 +138,7 @@
     return t
 def legs(SLOW):
     LR = {l: [] for l in ("king", "rev24", "fund", "f10")}; idx = []
+    TURN = {l: [] for l in LR}; _prevb = {l: np.zeros(NW) for l in LR}   # seat_round2 (= axisB R2 code, extended to the f10 leg): per-leg unit-gross rank-book turnover
     for i in range(nA):
         j = pw_row.get(int(E_ts[i]))
         if j is None: continue
@@ -152,10 +158,17 @@
             if SEATNET and g > 1e-9:   # X1: 减去该腿单位 gross 书的 4h carry(多头付正费率), bps
                 _lr -= float((z / g * np.nan_to_num(FN[j, m], nan=0.0) * (4.0 / _IVf[j, m])).sum() * 1e4)
             LR[leg].append(_lr)
+            _zb = np.zeros(NW)   # axisB R2: turnover of this leg's own unit-gross rank book t-1 -> t (full 829-vector, non-members = 0; g<=1e-9 ⇒ empty book); _lr above is untouched
+            if g > 1e-9: _zb[m] = z / g
+            TURN[leg].append(float(np.abs(_zb - _prevb[leg]).sum())); _prevb[leg] = _zb
         idx.append(i)
-    return {k: np.array(v) for k, v in LR.items()}, {int(i): p for p, i in enumerate(idx)}
+    _out = {k: np.array(v) for k, v in LR.items()}
+    for l in TURN: _out["turn_" + l] = np.array(TURN[l])
+    return _out, {int(i): p for p, i in enumerate(idx)}
 W3FC = None
 def run(SLOW, LRa, pos, depth, need, cool, look=900):
+    global W3FC
+    W3FC = None   # seat_round2: reset per run — the health_check device left the S0 run's LAST (2026) W3FC in place, so the d30 run's first LOOK warm-up anchors (2022-01→07) under SEATF10=1 used a 2026 seat for the F10 book; now the warm-up falls back to the shared warm-up seat w3 (=1/3 each). Affects only anchors with p < LOOK (2022), outside every judged window; SEATF10=0 path untouched (W3FC never read).
     def w3_at(i):
         if W3FIX is not None:
             return np.array([float(x) for x in W3FIX.split(",")])
@@ -168,6 +181,7 @@
         if SEATF10:   # T1: f10 腿的席位由它自己的腿收益决定; 返回 kc 三腿席位, fc 席位放入 W3FC 全局
             global W3FC
             r4 = np.stack([LRa["king"][sl], LRa["rev24"][sl], LRa["fund"][sl], LRa["f10"][sl]])
+            if SEATCOST_BPS > 0: r4 = r4 - SEATCOST_BPS * np.stack([LRa["turn_king"][sl], LRa["turn_rev24"][sl], LRa["turn_fund"][sl], LRa["turn_f10"][sl]])   # seat_round2 B3/B6: net-of-turnover-fee seat input
             shp4 = r4.mean(1) / (r4.std(1) + 1e-9); shp4 = np.maximum(shp4, 0.0)
             mk = np.array([1.0 if c == "1" else 0.0 for c in LEGS])
             wk = np.array([shp4[0], shp4[1], shp4[2]]) * mk; wk = wk / wk.sum() if wk.sum() > 0 else np.array([1/3]*3)
@@ -175,6 +189,7 @@
             W3FC = wf
             return wk
         r = np.stack([LRa["king"][sl], LRa["rev24"][sl], LRa["fund"][sl]])
+        if SEATCOST_BPS > 0: r = r - SEATCOST_BPS * np.stack([LRa["turn_king"][sl], LRa["turn_rev24"][sl], LRa["turn_fund"][sl]])   # seat_round2 B3: r_leg − fee·turn_leg (bps) in place of r_leg, then the production msharpe algebra unchanged
         if WRULE == "iv":
             iv = 1.0 / (r.std(1) + 1e-9)
             return iv / iv.sum()
@@ -189,6 +204,8 @@
     HF = np.zeros(NW); HB = np.zeros(NW)      # F10 书自己的 EMA 态 / 上一锚的混合书
     cnt = np.zeros(NW, int); su = np.full(NW, -1)
     rec = []; WS = []
+    S2 = []; NK = []; NF = []   # seat_round2: per-anchor (phi_t, F10-book seat ×3, king-book net/ug, F10-book net/ug, gross_k, gross_f, phi_state); NK/NF = per-book own net return per unit gross (PHIDYN state)
+    _w3f = None; _smf = None; _HFprev = None; phi_t = PHI; _phis = 0   # _phis: 0 = warm-up/const, 1 = dynamic, 2 = both-shp-zero fallback, 3 = clipped
     for i in range(nA):
         j = pw_row.get(int(E_ts[i]))
         if j is None: continue
@@ -274,8 +291,21 @@
                     if _blf.any(): _smf[_blf] = 0.0
             else:
                 _smf = HF.copy()
+            _HFprev = HF
             HF = _smf
-            smb = (1.0 - PHI) * sm + PHI * _smf
+            if PHIDYN:   # seat_round2 B4: φ_t from the two books' own OOS net returns over the previous PHIDYN_LOOK recorded anchors (strictly before this one: NK/NF are appended after this anchor's accounting)
+                if len(NK) >= PHIDYN_LOOK:
+                    _rk = np.array(NK[-PHIDYN_LOOK:]); _rf = np.array(NF[-PHIDYN_LOOK:])
+                    _sk = max(float(_rk.mean() / (_rk.std() + 1e-9)), 0.0); _sf = max(float(_rf.mean() / (_rf.std() + 1e-9)), 0.0)
+                    if _sk + _sf > 0:
+                        _raw = _sf / (_sk + _sf); phi_t = float(min(max(_raw, PHIDYN_CLIP[0]), PHIDYN_CLIP[1])); _phis = 3 if phi_t != _raw else 1
+                    else:
+                        phi_t = PHI; _phis = 2
+                else:
+                    phi_t = PHI; _phis = 0
+            else:
+                phi_t = PHI; _phis = 0
+            smb = (1.0 - phi_t) * sm + phi_t * _smf
         else:
             smb = sm
         _smk = sm                     # ★ king 书自己的 sm 必须留住: 它的 EMA 态独立推进
@@ -297,6 +327,16 @@
         fnow = np.nan_to_num(FN[j, m], nan=0.0); ivv = IV[j, m]; ivv = np.where(np.isfinite(ivv) & (ivv > 0), ivv, 8.0)
         car = (sm[m] * fnow * (4.0 / ivv)).sum() * 1e4
         pnl_raw = float((sm[m] * yv).sum() * 1e4)
+        # seat_round2: each book's OWN OOS net return this anchor (price − carry − cost of its own weights/trades, same tier costs, members only as the blended accounting), per unit gross of that book
+        if PHI > 0:
+            _trk = _smk - H; _trfb = _smf - _HFprev
+            _ck = sum(np.abs(_trk[m])[tr == tt].sum() * (fr * mk + (1 - fr) * tk) for tt, (mk, tk, fr) in enumerate(COST_B))
+            _cf = sum(np.abs(_trfb[m])[tr == tt].sum() * (fr * mk + (1 - fr) * tk) for tt, (mk, tk, fr) in enumerate(COST_B))
+            _gk = float(np.abs(_smk).sum()); _gf_ = float(np.abs(_smf).sum())
+            _nk = float(((_smk[m] * yv).sum() * 1e4 - (_smk[m] * fnow * (4.0 / ivv)).sum() * 1e4 - _ck) / _gk) if _gk > 1e-9 else 0.0
+            _nf = float(((_smf[m] * yv).sum() * 1e4 - (_smf[m] * fnow * (4.0 / ivv)).sum() * 1e4 - _cf) / _gf_) if _gf_ > 1e-9 else 0.0
+        else:
+            _nk = _nf = _gk = _gf_ = 0.0
         legc = []
         for leg in ("king", "rev24", "fund"):
             zz = np.nan_to_num(FZ if leg == "fund" else xz(sc[leg])); gl = np.abs(zz).sum()
@@ -329,16 +369,31 @@
                     legc[0], legc[1], legc[2], float(w3[0]), float(w3[1]), float(w3[2]), float(np.abs(trade).sum()),
                     float(pnl_r - car_r - cbps_r), pnl_r, car_r, float(cbps_r), netlong))
         WS.append(sm.astype(np.float32))
+        _w3fr = (_w3f if (PHI > 0 and _w3f is not None) else np.array([np.nan] * 3))
+        S2.append((float(phi_t), float(_w3fr[0]), float(_w3fr[1]), float(_w3fr[2]), _nk, _nf, _gk, _gf_, float(_phis)))
+        NK.append(_nk); NF.append(_nf)   # appended AFTER this anchor's φ_t was fixed ⇒ φ_t uses anchors strictly before t
         H = _smk if PHI > 0 else sm      # king 书 EMA 态独立推进(φ=0 时二者同一)
         HB = sm; HR = smr; Pi = Pi * (1.0 + yfull)
         if i % 2000 == 0: print("run depth", depth, i, "/", nA, round(time.time() - t0, 1), "s", flush=True)
-    return np.array(rec), np.stack(WS)
+    return np.array(rec), np.stack(WS), np.array(S2)
 LRa, pos = legs(SLOW); print("legs done", round(time.time() - t0, 1), "s", flush=True)
 ARMS = [("S0", None, 0, 0, "nets_histv2_0_0_0.npy"), ("d30_n2_c42", -0.30, 2, 42, "nets_histv2_-30_2_42.npy")]
 COLS = ["ts", "net", "pnl", "carry", "cost", "gross_total", "gross_member", "gross_sel", "nsel", "nmember", "fires", "leg_king", "leg_rev24", "leg_fund", "w3_king", "w3_rev24", "w3_fund", "turnover", "net_ex", "pnl_ex", "carry_ex", "cost_ex", "netlong"]
+SEAT2_COLS = ["phi_t", "w3f_f10", "w3f_rev24", "w3f_fund", "netk_ug", "netf_ug", "gross_k", "gross_f", "phi_state"]
+_idxL = np.array(sorted(pos, key=pos.get)); _yrsL = yrs[_idxL]; _YL = sorted(set(_yrsL.tolist()))
+for _l in ("king", "rev24", "fund", "f10"):
+    _t = LRa["turn_" + _l]
+    print(f"SEAT2 turn_{_l} yearly mean (unit gross/anchor): " + " ".join(f"{int(y)}={_t[_yrsL == y].mean():.4f}" for y in _YL) + f" | all={_t.mean():.4f}"
+          + (f" | deduction {SEATCOST_BPS}·turn yearly (bps): " + " ".join(f"{int(y)}={SEATCOST_BPS * _t[_yrsL == y].mean():.4f}" for y in _YL) + f"; leg r mean {LRa[_l].mean():+.4f} -> net {(LRa[_l] - SEATCOST_BPS * _t).mean():+.4f}" if SEATCOST_BPS > 0 else ""), flush=True)
 out = {}; save = {}
 for nm, d, n_, c, reff in ARMS:
-    R, WS = run(SLOW, LRa, pos, d, n_, c)
+    R, WS, S2 = run(SLOW, LRa, pos, d, n_, c)
+    _yy2 = np.array([time.gmtime(int(t)).tm_year for t in R[:, 0].astype(np.int64)]); _Y2 = sorted(set(_yy2.tolist()))
+    _ph = S2[:, 0]; _sw = int((np.sign(_ph[1:] - 0.5) != np.sign(_ph[:-1] - 0.5)).sum()); _st = S2[:, 8]
+    print(f"SEAT2 {nm} yearly mean w3_king: " + " ".join(f"{y}={R[_yy2 == y, 14].mean():.3f}" for y in _Y2), flush=True)
+    print(f"SEAT2 {nm} yearly mean F10-book seat (f10/rev24/fund): " + " ".join(f"{y}={np.nanmean(S2[_yy2 == y, 1]):.3f}/{np.nanmean(S2[_yy2 == y, 2]):.3f}/{np.nanmean(S2[_yy2 == y, 3]):.3f}" for y in _Y2), flush=True)
+    print(f"SEAT2 {nm} yearly mean phi_t: " + " ".join(f"{y}={_ph[_yy2 == y].mean():.3f}" for y in _Y2) + f" | switches(sign(phi-0.5) flips) {_sw} | jumps(|Δphi|>=0.05) {int((np.abs(np.diff(_ph)) >= 0.05).sum())} | state counts warm/dyn/fallback/clipped = {[int((_st == s).sum()) for s in (0, 1, 2, 3)]} | min/max {_ph.min():.3f}/{_ph.max():.3f}", flush=True)
+    print(f"SEAT2 {nm} per-book net/ug (bps/anchor) yearly king-book / F10-book: " + " ".join(f"{y}={S2[_yy2 == y, 4].mean():+.3f}/{S2[_yy2 == y, 5].mean():+.3f}" for y in _Y2), flush=True)
     ref = np.load(f"{B}/{reff}")
     if REF_SKIP:   # combo_recheck: reference parity skipped on request (REF_SKIP=1)
         print(f"NOTE {nm}: REF_SKIP=1, reference parity vs pod_backup skipped", flush=True); ref = None
@@ -374,8 +429,10 @@
     print("RECEIPT_EX", nm, json.dumps(outx), flush=True)
     save[f"{nm}_rec"] = R
     save[f"{nm}_W"] = WS
+    save[f"{nm}_seat2"] = S2
 _OT = os.environ.get("OUT_TAG", "")   # 并行道输出隔离(PREREG_universe_dyn): 未设时文件名与旧装置同
 _OT = f"_{_OT}" if _OT else ""
 json.dump(out, open(f"{PD}/w10_ablation_summary{_OT}.json", "w"), indent=1, ensure_ascii=False)
-np.savez_compressed(f"{PD}/w10_ablation_series{_OT}.npz", cols=np.array(COLS), symbols=np.array(WSYM), config_json=np.array(json.dumps(_CFG)), legs_ts=E_ts[np.array(sorted(pos, key=pos.get))], legs_king=LRa["king"], legs_rev24=LRa["rev24"], legs_fund=LRa["fund"], **save)   # health_check: the seat inputs (legs() series) saved for the live-seat comparison; rec/W arrays unchanged
+np.savez_compressed(f"{PD}/w10_ablation_series{_OT}.npz", cols=np.array(COLS), symbols=np.array(WSYM), config_json=np.array(json.dumps(_CFG)), legs_ts=E_ts[np.array(sorted(pos, key=pos.get))], legs_king=LRa["king"], legs_rev24=LRa["rev24"], legs_fund=LRa["fund"],
+                    seat2_cols=np.array(SEAT2_COLS), legs_f10=LRa["f10"], seat2_turn=np.stack([LRa["turn_king"], LRa["turn_rev24"], LRa["turn_fund"], LRa["turn_f10"]]), **save)   # health_check: the seat inputs (legs() series) saved for the live-seat comparison; rec/W arrays unchanged. seat_round2: per-leg turnover (king/rev24/fund/f10 over the legs() sequence) + per-arm seat2 series
 print("DONE", round(time.time() - t0, 1), "s", flush=True)
```

### R.3 B0 bitwise-equivalence receipt (patched device, default path, vs health_check M1_UPIT_{cal}_s{seed}_ccal; all four arrays d30_n2_c42_rec / S0_rec / d30_n2_c42_W / S0_W + config minus self-report keys)
```
PASS [B0_log_s42 (w10_seat2.py default path) vs health_check M1_UPIT_log_s42_ccal] dev/probe_artifacts/w10_ablation_series_B0_log_s42.npz vs /workspace/review_scratch/health_check/dev/probe_artifacts/w10_ablation_series_M1_UPIT_log_s42_ccal.npz: arrays {'d30_n2_c42_rec': True, 'S0_rec': True, 'd30_n2_c42_W': True, 'S0_W': True} shapes {'d30_n2_c42_rec': ((10038, 23), (10038, 23)), 'S0_rec': ((10038, 23), (10038, 23)), 'd30_n2_c42_W': ((10038, 829), (10038, 829)), 'S0_W': ((10038, 829), (10038, 829))} nan_in_mine {'d30_n2_c42_rec': 0, 'S0_rec': 0, 'd30_n2_c42_W': 0, 'S0_W': 0} config_equal(minus self-report keys)=True sha(mine)=b78defb13dc3e208 sha(ref)=d0a51738b9c7cb1c
PASS [B0_log_s2027 (w10_seat2.py default path) vs health_check M1_UPIT_log_s2027_ccal] dev/probe_artifacts/w10_ablation_series_B0_log_s2027.npz vs /workspace/review_scratch/health_check/dev/probe_artifacts/w10_ablation_series_M1_UPIT_log_s2027_ccal.npz: arrays {'d30_n2_c42_rec': True, 'S0_rec': True, 'd30_n2_c42_W': True, 'S0_W': True} shapes {'d30_n2_c42_rec': ((10038, 23), (10038, 23)), 'S0_rec': ((10038, 23), (10038, 23)), 'd30_n2_c42_W': ((10038, 829), (10038, 829)), 'S0_W': ((10038, 829), (10038, 829))} nan_in_mine {'d30_n2_c42_rec': 0, 'S0_rec': 0, 'd30_n2_c42_W': 0, 'S0_W': 0} config_equal(minus self-report keys)=True sha(mine)=263e82efba1745b9 sha(ref)=10e64fdb56a62e37
PASS [B0_prod_s42 (w10_seat2.py default path) vs health_check M1_UPIT_prod_s42_ccal] dev_alt/probe_artifacts/w10_ablation_series_B0_prod_s42.npz vs /workspace/review_scratch/health_check/dev_alt/probe_artifacts/w10_ablation_series_M1_UPIT_prod_s42_ccal.npz: arrays {'d30_n2_c42_rec': True, 'S0_rec': True, 'd30_n2_c42_W': True, 'S0_W': True} shapes {'d30_n2_c42_rec': ((10038, 23), (10038, 23)), 'S0_rec': ((10038, 23), (10038, 23)), 'd30_n2_c42_W': ((10038, 829), (10038, 829)), 'S0_W': ((10038, 829), (10038, 829))} nan_in_mine {'d30_n2_c42_rec': 0, 'S0_rec': 0, 'd30_n2_c42_W': 0, 'S0_W': 0} config_equal(minus self-report keys)=True sha(mine)=025d43d425548fac sha(ref)=32bfecb9cf9c0e5c
PASS [B0_prod_s2027 (w10_seat2.py default path) vs health_check M1_UPIT_prod_s2027_ccal] dev_alt/probe_artifacts/w10_ablation_series_B0_prod_s2027.npz vs /workspace/review_scratch/health_check/dev_alt/probe_artifacts/w10_ablation_series_M1_UPIT_prod_s2027_ccal.npz: arrays {'d30_n2_c42_rec': True, 'S0_rec': True, 'd30_n2_c42_W': True, 'S0_W': True} shapes {'d30_n2_c42_rec': ((10038, 23), (10038, 23)), 'S0_rec': ((10038, 23), (10038, 23)), 'd30_n2_c42_W': ((10038, 829), (10038, 829)), 'S0_W': ((10038, 829), (10038, 829))} nan_in_mine {'d30_n2_c42_rec': 0, 'S0_rec': 0, 'd30_n2_c42_W': 0, 'S0_W': 0} config_equal(minus self-report keys)=True sha(mine)=467ad8e8ef277feb sha(ref)=a2c5ec76dfac990b
```
```
ATTEMPT1 (device sha 004386bf, equivalence 4/4 PASS after check_equiv key extension) archived to logs/attempt1/ 2026-09-05T07:17:33Z
5285f0049286d8964d10ee1d4ce9e428b9343af3048924e94f52ae55eda0b8f0  w10_seat2.py
8684d9a9f43a8d15beaa559cd12bd8f2977a3d088b01b93835f60f2bbf98a53d  w10_health_orig.py
ccb7a0805be2a106898467b5ffef3a8fd4813a659e044492c0a437b0e5d7aece  /workspace/review_scratch/health_check/masks/umask_UPIT.npz
9349ca634747772dcfc9adfb7a42a5c7b5b34f60bc7f31bc6fd95c4ae5d0fc42  /workspace/review_scratch/health_check/calib/costb_fee_steady.json
158cd4ac8f8f30f7f41a5a6cba0bd19a450ce756727e4aeae3d4e4b0b67d0054  /workspace/shadow_bundle_v3/slow_pred_pinned.npy
B0_EQUIV_ALL_PASS 2026-09-05T07:18:06Z
263e82efba1745b91ee1e81320b74f3e34c2e45532cb8d3be6143ae97d4e0fa4  dev/probe_artifacts/w10_ablation_series_B0_log_s2027.npz
b78defb13dc3e208a9e64fd3eb1c2cbeab95831d040a66e8fe8fe55cdd23f2e1  dev/probe_artifacts/w10_ablation_series_B0_log_s42.npz
467ad8e8ef277feb4b180358bfcde27a9daac33fceb2aeebd7b1c0bade526585  dev_alt/probe_artifacts/w10_ablation_series_B0_prod_s2027.npz
025d43d425548fac2e5425ba18174e64b6c6ee5c1555474dc2868ff5e2bec182  dev_alt/probe_artifacts/w10_ablation_series_B0_prod_s42.npz
CHAIN_B0_DONE 2026-09-05T07:18:06Z
```

### R.4 Commands (verbatim from logs/commands.txt; cwd shown; OMP/OPENBLAS/MKL threads = 4 via run_arm.sh)
```
CMD[B0_log_s42] (cwd=/workspace/review_scratch/seat_round2/dev) 2026-09-05T07:11:51Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero PHI=0.45 FSEED=42 UMASK_SCOPE=m1 UMASK_NPZ=/workspace/review_scratch/health_check/masks/umask_UPIT.npz COSTB_JSON=/workspace/review_scratch/health_check/calib/costb_fee_steady.json OUT_TAG=B0_log_s42 /workspace/venv/bin/python ../w10_seat2.py
CMD[B0_prod_s42] (cwd=/workspace/review_scratch/seat_round2/dev_alt) 2026-09-05T07:11:51Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero PHI=0.45 FSEED=42 UMASK_SCOPE=m1 UMASK_NPZ=/workspace/review_scratch/health_check/masks/umask_UPIT.npz COSTB_JSON=/workspace/review_scratch/health_check/calib/costb_fee_steady.json OUT_TAG=B0_prod_s42 /workspace/venv/bin/python ../w10_seat2.py
CMD[B0_prod_s2027] (cwd=/workspace/review_scratch/seat_round2/dev_alt) 2026-09-05T07:11:51Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero PHI=0.45 FSEED=2027 UMASK_SCOPE=m1 UMASK_NPZ=/workspace/review_scratch/health_check/masks/umask_UPIT.npz COSTB_JSON=/workspace/review_scratch/health_check/calib/costb_fee_steady.json OUT_TAG=B0_prod_s2027 /workspace/venv/bin/python ../w10_seat2.py
CMD[B0_log_s2027] (cwd=/workspace/review_scratch/seat_round2/dev) 2026-09-05T07:11:51Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero PHI=0.45 FSEED=2027 UMASK_SCOPE=m1 UMASK_NPZ=/workspace/review_scratch/health_check/masks/umask_UPIT.npz COSTB_JSON=/workspace/review_scratch/health_check/calib/costb_fee_steady.json OUT_TAG=B0_log_s2027 /workspace/venv/bin/python ../w10_seat2.py
END[B0_prod_s2027] rc=0 2026-09-05T07:12:19Z
END[B0_log_s2027] rc=0 2026-09-05T07:12:19Z
END[B0_log_s42] rc=0 2026-09-05T07:12:19Z
END[B0_prod_s42] rc=0 2026-09-05T07:12:19Z
CMD[B0_log_s2027] (cwd=/workspace/review_scratch/seat_round2/dev) 2026-09-05T07:17:33Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero PHI=0.45 FSEED=2027 UMASK_SCOPE=m1 UMASK_NPZ=/workspace/review_scratch/health_check/masks/umask_UPIT.npz COSTB_JSON=/workspace/review_scratch/health_check/calib/costb_fee_steady.json OUT_TAG=B0_log_s2027 /workspace/venv/bin/python ../w10_seat2.py
CMD[B0_log_s42] (cwd=/workspace/review_scratch/seat_round2/dev) 2026-09-05T07:17:33Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero PHI=0.45 FSEED=42 UMASK_SCOPE=m1 UMASK_NPZ=/workspace/review_scratch/health_check/masks/umask_UPIT.npz COSTB_JSON=/workspace/review_scratch/health_check/calib/costb_fee_steady.json OUT_TAG=B0_log_s42 /workspace/venv/bin/python ../w10_seat2.py
CMD[B0_prod_s42] (cwd=/workspace/review_scratch/seat_round2/dev_alt) 2026-09-05T07:17:33Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero PHI=0.45 FSEED=42 UMASK_SCOPE=m1 UMASK_NPZ=/workspace/review_scratch/health_check/masks/umask_UPIT.npz COSTB_JSON=/workspace/review_scratch/health_check/calib/costb_fee_steady.json OUT_TAG=B0_prod_s42 /workspace/venv/bin/python ../w10_seat2.py
CMD[B0_prod_s2027] (cwd=/workspace/review_scratch/seat_round2/dev_alt) 2026-09-05T07:17:33Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero PHI=0.45 FSEED=2027 UMASK_SCOPE=m1 UMASK_NPZ=/workspace/review_scratch/health_check/masks/umask_UPIT.npz COSTB_JSON=/workspace/review_scratch/health_check/calib/costb_fee_steady.json OUT_TAG=B0_prod_s2027 /workspace/venv/bin/python ../w10_seat2.py
END[B0_prod_s42] rc=0 2026-09-05T07:18:00Z
END[B0_log_s2027] rc=0 2026-09-05T07:18:00Z
END[B0_prod_s2027] rc=0 2026-09-05T07:18:00Z
END[B0_log_s42] rc=0 2026-09-05T07:18:00Z
CMD[B1_prod_s42] (cwd=/workspace/review_scratch/seat_round2/dev_alt) 2026-09-05T07:18:06Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero PHI=0.45 FSEED=42 UMASK_SCOPE=m1 UMASK_NPZ=/workspace/review_scratch/health_check/masks/umask_UPIT.npz COSTB_JSON=/workspace/review_scratch/health_check/calib/costb_fee_steady.json SEATF10=1 OUT_TAG=B1_prod_s42 /workspace/venv/bin/python ../w10_seat2.py
CMD[B1_prod_s2027] (cwd=/workspace/review_scratch/seat_round2/dev_alt) 2026-09-05T07:18:06Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero PHI=0.45 FSEED=2027 UMASK_SCOPE=m1 UMASK_NPZ=/workspace/review_scratch/health_check/masks/umask_UPIT.npz COSTB_JSON=/workspace/review_scratch/health_check/calib/costb_fee_steady.json SEATF10=1 OUT_TAG=B1_prod_s2027 /workspace/venv/bin/python ../w10_seat2.py
CMD[B1_log_s42] (cwd=/workspace/review_scratch/seat_round2/dev) 2026-09-05T07:18:06Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero PHI=0.45 FSEED=42 UMASK_SCOPE=m1 UMASK_NPZ=/workspace/review_scratch/health_check/masks/umask_UPIT.npz COSTB_JSON=/workspace/review_scratch/health_check/calib/costb_fee_steady.json SEATF10=1 OUT_TAG=B1_log_s42 /workspace/venv/bin/python ../w10_seat2.py
CMD[B1_log_s2027] (cwd=/workspace/review_scratch/seat_round2/dev) 2026-09-05T07:18:06Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero PHI=0.45 FSEED=2027 UMASK_SCOPE=m1 UMASK_NPZ=/workspace/review_scratch/health_check/masks/umask_UPIT.npz COSTB_JSON=/workspace/review_scratch/health_check/calib/costb_fee_steady.json SEATF10=1 OUT_TAG=B1_log_s2027 /workspace/venv/bin/python ../w10_seat2.py
END[B1_prod_s2027] rc=0 2026-09-05T07:18:34Z
END[B1_log_s2027] rc=0 2026-09-05T07:18:34Z
END[B1_prod_s42] rc=0 2026-09-05T07:18:34Z
END[B1_log_s42] rc=0 2026-09-05T07:18:34Z
CMD[B2_prod_s42] (cwd=/workspace/review_scratch/seat_round2/dev_alt) 2026-09-05T07:18:34Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero PHI=0.45 FSEED=42 UMASK_SCOPE=m1 UMASK_NPZ=/workspace/review_scratch/health_check/masks/umask_UPIT.npz COSTB_JSON=/workspace/review_scratch/health_check/calib/costb_fee_steady.json SEATNET=1 OUT_TAG=B2_prod_s42 /workspace/venv/bin/python ../w10_seat2.py
CMD[B2_log_s42] (cwd=/workspace/review_scratch/seat_round2/dev) 2026-09-05T07:18:34Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero PHI=0.45 FSEED=42 UMASK_SCOPE=m1 UMASK_NPZ=/workspace/review_scratch/health_check/masks/umask_UPIT.npz COSTB_JSON=/workspace/review_scratch/health_check/calib/costb_fee_steady.json SEATNET=1 OUT_TAG=B2_log_s42 /workspace/venv/bin/python ../w10_seat2.py
CMD[B2_prod_s2027] (cwd=/workspace/review_scratch/seat_round2/dev_alt) 2026-09-05T07:18:34Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero PHI=0.45 FSEED=2027 UMASK_SCOPE=m1 UMASK_NPZ=/workspace/review_scratch/health_check/masks/umask_UPIT.npz COSTB_JSON=/workspace/review_scratch/health_check/calib/costb_fee_steady.json SEATNET=1 OUT_TAG=B2_prod_s2027 /workspace/venv/bin/python ../w10_seat2.py
CMD[B2_log_s2027] (cwd=/workspace/review_scratch/seat_round2/dev) 2026-09-05T07:18:34Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero PHI=0.45 FSEED=2027 UMASK_SCOPE=m1 UMASK_NPZ=/workspace/review_scratch/health_check/masks/umask_UPIT.npz COSTB_JSON=/workspace/review_scratch/health_check/calib/costb_fee_steady.json SEATNET=1 OUT_TAG=B2_log_s2027 /workspace/venv/bin/python ../w10_seat2.py
END[B2_log_s42] rc=0 2026-09-05T07:19:01Z
END[B2_prod_s2027] rc=0 2026-09-05T07:19:01Z
END[B2_log_s2027] rc=0 2026-09-05T07:19:02Z
END[B2_prod_s42] rc=0 2026-09-05T07:19:02Z
CMD[B3_prod_s42] (cwd=/workspace/review_scratch/seat_round2/dev_alt) 2026-09-05T07:19:02Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero PHI=0.45 FSEED=42 UMASK_SCOPE=m1 UMASK_NPZ=/workspace/review_scratch/health_check/masks/umask_UPIT.npz COSTB_JSON=/workspace/review_scratch/health_check/calib/costb_fee_steady.json SEATNET=1 SEATCOST_BPS=2.035 OUT_TAG=B3_prod_s42 /workspace/venv/bin/python ../w10_seat2.py
CMD[B3_log_s42] (cwd=/workspace/review_scratch/seat_round2/dev) 2026-09-05T07:19:02Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero PHI=0.45 FSEED=42 UMASK_SCOPE=m1 UMASK_NPZ=/workspace/review_scratch/health_check/masks/umask_UPIT.npz COSTB_JSON=/workspace/review_scratch/health_check/calib/costb_fee_steady.json SEATNET=1 SEATCOST_BPS=2.035 OUT_TAG=B3_log_s42 /workspace/venv/bin/python ../w10_seat2.py
CMD[B3_prod_s2027] (cwd=/workspace/review_scratch/seat_round2/dev_alt) 2026-09-05T07:19:02Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero PHI=0.45 FSEED=2027 UMASK_SCOPE=m1 UMASK_NPZ=/workspace/review_scratch/health_check/masks/umask_UPIT.npz COSTB_JSON=/workspace/review_scratch/health_check/calib/costb_fee_steady.json SEATNET=1 SEATCOST_BPS=2.035 OUT_TAG=B3_prod_s2027 /workspace/venv/bin/python ../w10_seat2.py
CMD[B3_log_s2027] (cwd=/workspace/review_scratch/seat_round2/dev) 2026-09-05T07:19:02Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero PHI=0.45 FSEED=2027 UMASK_SCOPE=m1 UMASK_NPZ=/workspace/review_scratch/health_check/masks/umask_UPIT.npz COSTB_JSON=/workspace/review_scratch/health_check/calib/costb_fee_steady.json SEATNET=1 SEATCOST_BPS=2.035 OUT_TAG=B3_log_s2027 /workspace/venv/bin/python ../w10_seat2.py
END[B3_prod_s2027] rc=0 2026-09-05T07:19:29Z
END[B3_prod_s42] rc=0 2026-09-05T07:19:29Z
END[B3_log_s2027] rc=0 2026-09-05T07:19:29Z
END[B3_log_s42] rc=0 2026-09-05T07:19:29Z
CMD[B4_prod_s2027] (cwd=/workspace/review_scratch/seat_round2/dev_alt) 2026-09-05T07:19:29Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero PHI=0.45 FSEED=2027 UMASK_SCOPE=m1 UMASK_NPZ=/workspace/review_scratch/health_check/masks/umask_UPIT.npz COSTB_JSON=/workspace/review_scratch/health_check/calib/costb_fee_steady.json PHIDYN=1 OUT_TAG=B4_prod_s2027 /workspace/venv/bin/python ../w10_seat2.py
CMD[B4_prod_s42] (cwd=/workspace/review_scratch/seat_round2/dev_alt) 2026-09-05T07:19:29Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero PHI=0.45 FSEED=42 UMASK_SCOPE=m1 UMASK_NPZ=/workspace/review_scratch/health_check/masks/umask_UPIT.npz COSTB_JSON=/workspace/review_scratch/health_check/calib/costb_fee_steady.json PHIDYN=1 OUT_TAG=B4_prod_s42 /workspace/venv/bin/python ../w10_seat2.py
CMD[B4_log_s42] (cwd=/workspace/review_scratch/seat_round2/dev) 2026-09-05T07:19:29Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero PHI=0.45 FSEED=42 UMASK_SCOPE=m1 UMASK_NPZ=/workspace/review_scratch/health_check/masks/umask_UPIT.npz COSTB_JSON=/workspace/review_scratch/health_check/calib/costb_fee_steady.json PHIDYN=1 OUT_TAG=B4_log_s42 /workspace/venv/bin/python ../w10_seat2.py
CMD[B4_log_s2027] (cwd=/workspace/review_scratch/seat_round2/dev) 2026-09-05T07:19:29Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero PHI=0.45 FSEED=2027 UMASK_SCOPE=m1 UMASK_NPZ=/workspace/review_scratch/health_check/masks/umask_UPIT.npz COSTB_JSON=/workspace/review_scratch/health_check/calib/costb_fee_steady.json PHIDYN=1 OUT_TAG=B4_log_s2027 /workspace/venv/bin/python ../w10_seat2.py
END[B4_log_s42] rc=0 2026-09-05T07:19:58Z
END[B4_prod_s42] rc=0 2026-09-05T07:19:58Z
END[B4_prod_s2027] rc=0 2026-09-05T07:19:58Z
END[B4_log_s2027] rc=0 2026-09-05T07:19:58Z
CMD[B5_log_s42] (cwd=/workspace/review_scratch/seat_round2/dev) 2026-09-05T07:19:58Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero PHI=0.45 FSEED=42 UMASK_SCOPE=m1 UMASK_NPZ=/workspace/review_scratch/health_check/masks/umask_UPIT.npz COSTB_JSON=/workspace/review_scratch/health_check/calib/costb_fee_steady.json SEATF10=1 PHIDYN=1 OUT_TAG=B5_log_s42 /workspace/venv/bin/python ../w10_seat2.py
CMD[B5_prod_s42] (cwd=/workspace/review_scratch/seat_round2/dev_alt) 2026-09-05T07:19:58Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero PHI=0.45 FSEED=42 UMASK_SCOPE=m1 UMASK_NPZ=/workspace/review_scratch/health_check/masks/umask_UPIT.npz COSTB_JSON=/workspace/review_scratch/health_check/calib/costb_fee_steady.json SEATF10=1 PHIDYN=1 OUT_TAG=B5_prod_s42 /workspace/venv/bin/python ../w10_seat2.py
CMD[B5_log_s2027] (cwd=/workspace/review_scratch/seat_round2/dev) 2026-09-05T07:19:58Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero PHI=0.45 FSEED=2027 UMASK_SCOPE=m1 UMASK_NPZ=/workspace/review_scratch/health_check/masks/umask_UPIT.npz COSTB_JSON=/workspace/review_scratch/health_check/calib/costb_fee_steady.json SEATF10=1 PHIDYN=1 OUT_TAG=B5_log_s2027 /workspace/venv/bin/python ../w10_seat2.py
CMD[B5_prod_s2027] (cwd=/workspace/review_scratch/seat_round2/dev_alt) 2026-09-05T07:19:58Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero PHI=0.45 FSEED=2027 UMASK_SCOPE=m1 UMASK_NPZ=/workspace/review_scratch/health_check/masks/umask_UPIT.npz COSTB_JSON=/workspace/review_scratch/health_check/calib/costb_fee_steady.json SEATF10=1 PHIDYN=1 OUT_TAG=B5_prod_s2027 /workspace/venv/bin/python ../w10_seat2.py
END[B5_prod_s2027] rc=0 2026-09-05T07:20:28Z
END[B5_log_s42] rc=0 2026-09-05T07:20:28Z
END[B5_prod_s42] rc=0 2026-09-05T07:20:28Z
END[B5_log_s2027] rc=0 2026-09-05T07:20:28Z
CMD[B6_prod_s42] (cwd=/workspace/review_scratch/seat_round2/dev_alt) 2026-09-05T07:20:28Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero PHI=0.45 FSEED=42 UMASK_SCOPE=m1 UMASK_NPZ=/workspace/review_scratch/health_check/masks/umask_UPIT.npz COSTB_JSON=/workspace/review_scratch/health_check/calib/costb_fee_steady.json SEATNET=1 SEATCOST_BPS=2.035 SEATF10=1 PHIDYN=1 OUT_TAG=B6_prod_s42 /workspace/venv/bin/python ../w10_seat2.py
CMD[B6_log_s42] (cwd=/workspace/review_scratch/seat_round2/dev) 2026-09-05T07:20:28Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero PHI=0.45 FSEED=42 UMASK_SCOPE=m1 UMASK_NPZ=/workspace/review_scratch/health_check/masks/umask_UPIT.npz COSTB_JSON=/workspace/review_scratch/health_check/calib/costb_fee_steady.json SEATNET=1 SEATCOST_BPS=2.035 SEATF10=1 PHIDYN=1 OUT_TAG=B6_log_s42 /workspace/venv/bin/python ../w10_seat2.py
CMD[B6_log_s2027] (cwd=/workspace/review_scratch/seat_round2/dev) 2026-09-05T07:20:28Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero PHI=0.45 FSEED=2027 UMASK_SCOPE=m1 UMASK_NPZ=/workspace/review_scratch/health_check/masks/umask_UPIT.npz COSTB_JSON=/workspace/review_scratch/health_check/calib/costb_fee_steady.json SEATNET=1 SEATCOST_BPS=2.035 SEATF10=1 PHIDYN=1 OUT_TAG=B6_log_s2027 /workspace/venv/bin/python ../w10_seat2.py
CMD[B6_prod_s2027] (cwd=/workspace/review_scratch/seat_round2/dev_alt) 2026-09-05T07:20:28Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero PHI=0.45 FSEED=2027 UMASK_SCOPE=m1 UMASK_NPZ=/workspace/review_scratch/health_check/masks/umask_UPIT.npz COSTB_JSON=/workspace/review_scratch/health_check/calib/costb_fee_steady.json SEATNET=1 SEATCOST_BPS=2.035 SEATF10=1 PHIDYN=1 OUT_TAG=B6_prod_s2027 /workspace/venv/bin/python ../w10_seat2.py
END[B6_log_s42] rc=0 2026-09-05T07:20:58Z
END[B6_prod_s2027] rc=0 2026-09-05T07:20:58Z
END[B6_prod_s42] rc=0 2026-09-05T07:20:58Z
END[B6_log_s2027] rc=0 2026-09-05T07:20:59Z
```

### R.5 Artifact sha256 (probe_artifacts, arms B0..B6)
```
ARMS_START n=24 2026-09-05T07:18:06Z
32
263e82efba1745b91ee1e81320b74f3e34c2e45532cb8d3be6143ae97d4e0fa4  dev/probe_artifacts/w10_ablation_series_B0_log_s2027.npz
b78defb13dc3e208a9e64fd3eb1c2cbeab95831d040a66e8fe8fe55cdd23f2e1  dev/probe_artifacts/w10_ablation_series_B0_log_s42.npz
940c08f8be99d2b3346c484434cab9a9215f942d6a7258eca45ab4bd1965496f  dev/probe_artifacts/w10_ablation_series_B1_log_s2027.npz
f531a548304f9f761e1418488f177207ed3b6bba7b21c62964186f3e7ee28809  dev/probe_artifacts/w10_ablation_series_B1_log_s42.npz
8118c7e8bcea7d5d49913f988162166c5153ec8e32247888abe2b40953714ba3  dev/probe_artifacts/w10_ablation_series_B2_log_s2027.npz
a7c0b74c5f6b64cc0cc1447b7f1b9dc9c749c21aa9592e4c69d2e8108e09f5a3  dev/probe_artifacts/w10_ablation_series_B2_log_s42.npz
9711167e68feefe7f254e418f0dfaa8e092ed84abd016445ad655710dca883d3  dev/probe_artifacts/w10_ablation_series_B3_log_s2027.npz
6638ba40bebd580669a07b85b665ca82f16ee03aa57df1e9efaa65061cfbe08d  dev/probe_artifacts/w10_ablation_series_B3_log_s42.npz
1bc8946dcd4969a5f2a9c603b5328711aa99d31aa83bf743a0574c6ed7e2e265  dev/probe_artifacts/w10_ablation_series_B4_log_s2027.npz
1fc6ad61caa0743a1d2d287f3066b4ff2934236e162de15c442e969e9ccb1076  dev/probe_artifacts/w10_ablation_series_B4_log_s42.npz
59c5e949a9247ae31eb6089fe0a4e904086449178f03c1f14164be92fd665133  dev/probe_artifacts/w10_ablation_series_B5_log_s2027.npz
9a3208f5c07a40996018c56eda2538984342375ec823ce6c005256facda1f447  dev/probe_artifacts/w10_ablation_series_B5_log_s42.npz
7aa025edbde79ff27c886d6bcf4089e63acf73029f334fd47e3f825dde0607b7  dev/probe_artifacts/w10_ablation_series_B6_log_s2027.npz
c520637b53a8046b6e3d30bbdebb06fb5b790c0ecc9da9b00ecae621d017c14f  dev/probe_artifacts/w10_ablation_series_B6_log_s42.npz
467ad8e8ef277feb4b180358bfcde27a9daac33fceb2aeebd7b1c0bade526585  dev_alt/probe_artifacts/w10_ablation_series_B0_prod_s2027.npz
025d43d425548fac2e5425ba18174e64b6c6ee5c1555474dc2868ff5e2bec182  dev_alt/probe_artifacts/w10_ablation_series_B0_prod_s42.npz
eda7b0151e3d076bd4fdb4c984e3d24981e30515dcdeeec2182e39f17c7ff5d5  dev_alt/probe_artifacts/w10_ablation_series_B1_prod_s2027.npz
06cdd46ad12d069974ff6be4b74b76a9f86e08cca586038844063a0ce6e4e60f  dev_alt/probe_artifacts/w10_ablation_series_B1_prod_s42.npz
254e386a68c223bee724fc3185e76f24b8a72ecf3a78ac3e9fa83ef5cc94d62f  dev_alt/probe_artifacts/w10_ablation_series_B2_prod_s2027.npz
ee67970421f5860a71d02d80c3a869c22d068d6562f96f22ebdbee25ee4cee57  dev_alt/probe_artifacts/w10_ablation_series_B2_prod_s42.npz
e8847592ef50b7fb660313881b58ddf3c65210b1f924843af6214c1d7782da59  dev_alt/probe_artifacts/w10_ablation_series_B3_prod_s2027.npz
da6bbccc92558102c4ec20816dfb90a131a80b688a5cd6ed0074f2384bcea27b  dev_alt/probe_artifacts/w10_ablation_series_B3_prod_s42.npz
bfcbc217d17f8220f9f6774419abcba7b4fd378d91efd3b07aa3924df3502694  dev_alt/probe_artifacts/w10_ablation_series_B4_prod_s2027.npz
4e737ccd14c8cf156d7207d142ccd412366b9f7694d58b8143e9c8144958f6a9  dev_alt/probe_artifacts/w10_ablation_series_B4_prod_s42.npz
eaf8183aa263777a2c337bc8eb4a39cb6e7a7e27d4b0e5b83ac77b69e2345c05  dev_alt/probe_artifacts/w10_ablation_series_B5_prod_s2027.npz
f5213a319cd4666a6b0d7450892a77b5601ae75b2dad97fea6db6769cb4754ea  dev_alt/probe_artifacts/w10_ablation_series_B5_prod_s42.npz
40079a53720938a1ab8598f34c7798d7d1ec07b18c697a0ad49f6dcc95691904  dev_alt/probe_artifacts/w10_ablation_series_B6_prod_s2027.npz
4e790dc0c00e8ea49e9ddd340955c0148787aeb276ea1f5dd3c42bbc2ff31f6b  dev_alt/probe_artifacts/w10_ablation_series_B6_prod_s42.npz
CHAIN_ARMS_DONE 2026-09-05T07:21:01Z
```

### R.6 Judge run log (judge_seat2.py stdout)
```
LOADED 28 artifacts; device sha256 5285f0049286d8964d10ee1d4ce9e428b9343af3048924e94f52ae55eda0b8f0; arm d30_n2_c42; identical anchor set n=10038 first 2022-01-31 00:00 last 2026-08-30 20:00
window sizes: 2024=2196, 2024-H2->26=4746, 2025=2190, 2026<=08-10=1332, 2024->26=5838, 2025->26=3642

===== LEVELS caliber=prod [compounded Π(1+r5)-1 over [E+1,E+48] (meta_newprod swap), CAL=log] arm=d30_n2_c42 col=net_ex (bps/anchor); per window: mean S=Sharpe DD=maxDD(bps); then 2025->26 gross / w3_king / w3f_f10 / phi_t / turnover
arm seed  |                 2024 |          2024-H2->26 |                 2025 |          2026<=08-10 |             2024->26 |             2025->26 | gross w_king w3f_f10 phi turn
B0  s42   |  +0.107 S+0.45 DD846 |  +0.840 S+2.30 DD770 |  +0.203 S+0.67 DD409 |  +2.510 S+4.95 DD356 |  +0.614 S+1.75 DD846 |  +0.919 S+2.29 DD770 | 0.613 0.599 0.599 0.450 0.03412
B1  s42   |  +0.244 S+1.18 DD507 |  +0.873 S+2.42 DD787 |  +0.206 S+0.70 DD393 |  +2.502 S+4.94 DD357 |  +0.662 S+1.95 DD787 |  +0.915 S+2.30 DD787 | 0.599 0.599 0.635 0.450 0.03513
B2  s42   |  +0.350 S+1.54 DD514 |  +0.550 S+1.73 DD888 |  -0.035 S-0.14 DD774 |  +1.891 S+4.27 DD342 |  +0.471 S+1.54 DD888 |  +0.544 S+1.58 DD888 | 0.498 0.770 0.770 0.450 0.03893
B3  s42   |  +0.283 S+1.13 DD643 |  +0.694 S+1.90 DD840 |  +0.042 S+0.14 DD558 |  +2.447 S+4.89 DD371 |  +0.594 S+1.70 DD840 |  +0.782 S+1.96 DD840 | 0.630 0.475 0.475 0.450 0.03128
B4  s42   |  +0.145 S+0.58 DD795 |  +0.853 S+2.32 DD784 |  +0.169 S+0.58 DD384 |  +2.602 S+5.02 DD360 |  +0.634 S+1.80 DD795 |  +0.929 S+2.31 DD784 | 0.602 0.599 0.599 0.628 0.04015
B5  s42   |  +0.331 S+1.72 DD280 |  +0.895 S+2.48 DD788 |  +0.255 S+0.91 DD395 |  +2.589 S+4.99 DD360 |  +0.733 S+2.19 DD788 |  +0.976 S+2.46 DD788 | 0.579 0.599 0.635 0.639 0.04237
B6  s42   |  +0.333 S+1.62 DD248 |  +0.834 S+2.34 DD828 |  +0.218 S+0.80 DD410 |  +2.526 S+4.97 DD386 |  +0.698 S+2.10 DD828 |  +0.918 S+2.35 DD828 | 0.544 0.412 0.540 0.645 0.04176
B0  s2027 |  +0.147 S+0.61 DD852 |  +0.880 S+2.38 DD763 |  +0.268 S+0.86 DD404 |  +2.488 S+4.90 DD345 |  +0.648 S+1.83 DD852 |  +0.950 S+2.34 DD763 | 0.626 0.599 0.599 0.450 0.03334
B1  s2027 |  +0.316 S+1.50 DD451 |  +0.914 S+2.53 DD757 |  +0.248 S+0.84 DD359 |  +2.493 S+4.92 DD347 |  +0.706 S+2.08 DD757 |  +0.941 S+2.37 DD757 | 0.606 0.599 0.660 0.450 0.03534
B2  s2027 |  +0.418 S+1.80 DD493 |  +0.585 S+1.83 DD915 |  +0.024 S+0.10 DD791 |  +1.866 S+4.21 DD330 |  +0.514 S+1.66 DD915 |  +0.571 S+1.64 DD915 | 0.511 0.770 0.770 0.450 0.03832
B3  s2027 |  +0.327 S+1.30 DD604 |  +0.711 S+1.93 DD835 |  +0.073 S+0.24 DD519 |  +2.401 S+4.82 DD366 |  +0.613 S+1.74 DD835 |  +0.785 S+1.96 DD835 | 0.640 0.475 0.475 0.450 0.03029
B4  s2027 |  +0.172 S+0.69 DD760 |  +0.949 S+2.54 DD764 |  +0.331 S+1.09 DD442 |  +2.656 S+5.12 DD347 |  +0.720 S+2.02 DD764 |  +1.050 S+2.58 DD764 | 0.618 0.599 0.599 0.665 0.03881
B5  s2027 |  +0.492 S+2.63 DD184 |  +0.946 S+2.66 DD760 |  +0.332 S+1.21 DD367 |  +2.617 S+5.09 DD350 |  +0.832 S+2.52 DD760 |  +1.037 S+2.64 DD760 | 0.587 0.599 0.660 0.668 0.04269
B6  s2027 |  +0.564 S+3.00 DD232 |  +0.790 S+2.26 DD819 |  +0.127 S+0.47 DD439 |  +2.424 S+4.82 DD368 |  +0.729 S+2.24 DD819 |  +0.828 S+2.15 DD819 | 0.555 0.412 0.519 0.657 0.04053

===== LEVELS caliber=log [raw Σ-simple y4 (meta), CAL=log = no transform] arm=d30_n2_c42 col=net_ex (bps/anchor); per window: mean S=Sharpe DD=maxDD(bps); then 2025->26 gross / w3_king / w3f_f10 / phi_t / turnover
arm seed  |                 2024 |          2024-H2->26 |                 2025 |          2026<=08-10 |             2024->26 |             2025->26 | gross w_king w3f_f10 phi turn
B0  s42   |  +0.068 S+0.27 DD871 |  +0.849 S+2.31 DD784 |  +0.261 S+0.87 DD412 |  +2.505 S+4.88 DD365 |  +0.616 S+1.74 DD871 |  +0.946 S+2.34 DD784 | 0.628 0.577 0.577 0.450 0.03302
B1  s42   |  +0.146 S+0.72 DD578 |  +0.940 S+2.53 DD798 |  +0.338 S+1.14 DD412 |  +2.679 S+5.07 DD356 |  +0.709 S+2.04 DD798 |  +1.049 S+2.56 DD798 | 0.618 0.577 0.405 0.450 0.02961
B2  s42   |  +0.229 S+0.99 DD560 |  +0.569 S+1.74 DD794 |  -0.037 S-0.14 DD648 |  +2.004 S+4.43 DD366 |  +0.449 S+1.43 DD794 |  +0.582 S+1.64 DD794 | 0.525 0.724 0.724 0.450 0.03806
B3  s42   |  +0.236 S+0.94 DD658 |  +0.733 S+1.97 DD865 |  +0.105 S+0.35 DD579 |  +2.515 S+4.86 DD385 |  +0.614 S+1.73 DD865 |  +0.842 S+2.07 DD865 | 0.633 0.422 0.422 0.450 0.02877
B4  s42   |  +0.104 S+0.40 DD841 |  +0.860 S+2.31 DD779 |  +0.224 S+0.76 DD357 |  +2.569 S+4.94 DD369 |  +0.632 S+1.76 DD841 |  +0.950 S+2.34 DD779 | 0.624 0.577 0.577 0.545 0.03805
B5  s42   |  +0.211 S+1.07 DD343 |  +0.915 S+2.42 DD784 |  +0.243 S+0.83 DD330 |  +2.788 S+5.08 DD360 |  +0.726 S+2.06 DD784 |  +1.037 S+2.48 DD784 | 0.613 0.577 0.405 0.559 0.03376
B6  s42   |  +0.240 S+0.99 DD552 |  +0.891 S+2.28 DD840 |  +0.308 S+0.92 DD584 |  +2.632 S+5.05 DD382 |  +0.719 S+1.96 DD840 |  +1.008 S+2.38 DD840 | 0.632 0.375 0.159 0.509 0.03325
B0  s2027 |  +0.105 S+0.42 DD857 |  +0.885 S+2.39 DD774 |  +0.321 S+1.04 DD379 |  +2.485 S+4.85 DD373 |  +0.649 S+1.82 DD857 |  +0.976 S+2.39 DD774 | 0.641 0.577 0.577 0.450 0.03220
B1  s2027 |  +0.199 S+0.96 DD550 |  +0.981 S+2.61 DD793 |  +0.393 S+1.27 DD379 |  +2.659 S+5.03 DD362 |  +0.746 S+2.12 DD793 |  +1.075 S+2.59 DD793 | 0.630 0.577 0.410 0.450 0.02878
B2  s2027 |  +0.267 S+1.14 DD571 |  +0.609 S+1.85 DD782 |  +0.012 S+0.04 DD656 |  +2.013 S+4.45 DD369 |  +0.486 S+1.53 DD782 |  +0.618 S+1.72 DD782 | 0.537 0.724 0.724 0.450 0.03738
B3  s2027 |  +0.280 S+1.12 DD626 |  +0.771 S+2.05 DD846 |  +0.170 S+0.56 DD536 |  +2.513 S+4.86 DD386 |  +0.654 S+1.82 DD846 |  +0.879 S+2.15 DD846 | 0.643 0.422 0.422 0.450 0.02771
B4  s2027 |  +0.094 S+0.36 DD864 |  +0.911 S+2.44 DD770 |  +0.336 S+1.11 DD384 |  +2.561 S+4.93 DD373 |  +0.669 S+1.86 DD864 |  +1.016 S+2.49 DD770 | 0.636 0.577 0.577 0.594 0.03688
B5  s2027 |  +0.208 S+1.04 DD412 |  +0.991 S+2.59 DD778 |  +0.433 S+1.41 DD334 |  +2.768 S+5.06 DD364 |  +0.792 S+2.23 DD778 |  +1.144 S+2.71 DD778 | 0.623 0.577 0.410 0.609 0.03200
B6  s2027 |  +0.197 S+0.74 DD738 |  +0.918 S+2.33 DD838 |  +0.354 S+1.04 DD570 |  +2.632 S+5.05 DD382 |  +0.721 S+1.92 DD838 |  +1.036 S+2.43 DD838 | 0.639 0.375 0.159 0.526 0.03223

===== DELTAS caliber=prod: Δ = arm − B0, net_ex bps/anchor, paired by anchor; day-block bootstrap NB=2000 seed=20260905; cells: Δ [CI95] P(Δ>0)
arm seed  |                         2024 |                  2024-H2->26 |                         2025 |                  2026<=08-10 |                     2024->26 |                     2025->26 | ΔSharpe(25on/24on) Δturn%(25on/24on) maxDD B0/Bk(25on) DD ratio
B1  s42   | +0.136 [-0.042,+0.328] 0.926 | +0.033 [-0.011,+0.080] 0.931 | +0.003 [-0.064,+0.068] 0.550 | -0.007 [-0.073,+0.056] 0.433 | +0.049 [-0.023,+0.127] 0.897 | -0.004 [-0.047,+0.039] 0.433 | +0.01/+0.20 +3.0%/+5.6% 770/787 1.021
B2  s42   | +0.242 [-0.063,+0.571] 0.937 | -0.290 [-0.583,+0.002] 0.026 | -0.237 [-0.712,+0.242] 0.172 | -0.619 [-1.284,+0.085] 0.040 | -0.143 [-0.421,+0.152] 0.157 | -0.375 [-0.802,+0.018] 0.029 | -0.71/-0.21 +14.1%/+13.1% 770/888 1.153
B3  s42   | +0.175 [-0.160,+0.502] 0.859 | -0.146 [-0.365,+0.057] 0.079 | -0.161 [-0.453,+0.141] 0.159 | -0.062 [-0.444,+0.325] 0.378 | -0.019 [-0.203,+0.169] 0.424 | -0.137 [-0.351,+0.085] 0.116 | -0.33/-0.06 -8.3%/-5.5% 770/840 1.090
B4  s42   | +0.038 [-0.068,+0.138] 0.759 | +0.013 [-0.116,+0.136] 0.579 | -0.034 [-0.253,+0.189] 0.395 | +0.092 [-0.141,+0.329] 0.780 | +0.021 [-0.084,+0.126] 0.636 | +0.010 [-0.145,+0.172] 0.547 | +0.03/+0.05 +17.7%/+12.1% 770/784 1.017
B5  s42   | +0.224 [-0.116,+0.596] 0.886 | +0.055 [-0.077,+0.185] 0.785 | +0.052 [-0.152,+0.273] 0.677 | +0.079 [-0.137,+0.295] 0.775 | +0.120 [-0.050,+0.282] 0.914 | +0.057 [-0.097,+0.209] 0.753 | +0.17/+0.43 +24.2%/+28.5% 770/788 1.023
B6  s42   | +0.225 [-0.248,+0.708] 0.819 | -0.006 [-0.244,+0.225] 0.489 | +0.015 [-0.315,+0.364] 0.532 | +0.016 [-0.386,+0.428] 0.526 | +0.084 [-0.148,+0.330] 0.768 | -0.001 [-0.253,+0.243] 0.490 | +0.06/+0.34 +22.4%/+31.3% 770/828 1.074
B1  s2027 | +0.169 [-0.013,+0.365] 0.967 | +0.034 [-0.020,+0.088] 0.907 | -0.019 [-0.102,+0.067] 0.321 | +0.006 [-0.068,+0.074] 0.579 | +0.058 [-0.025,+0.144] 0.921 | -0.009 [-0.068,+0.046] 0.381 | +0.03/+0.24 +6.0%/+7.0% 763/757 0.993
B2  s2027 | +0.271 [-0.042,+0.620] 0.956 | -0.295 [-0.607,+0.010] 0.033 | -0.244 [-0.735,+0.230] 0.158 | -0.622 [-1.348,+0.112] 0.045 | -0.135 [-0.399,+0.146] 0.176 | -0.379 [-0.763,-0.003] 0.022 | -0.70/-0.17 +14.9%/+13.5% 763/915 1.200
B3  s2027 | +0.180 [-0.119,+0.501] 0.864 | -0.169 [-0.382,+0.039] 0.059 | -0.194 [-0.488,+0.091] 0.104 | -0.086 [-0.486,+0.338] 0.360 | -0.035 [-0.219,+0.162] 0.360 | -0.165 [-0.400,+0.071] 0.086 | -0.38/-0.09 -9.2%/-5.9% 763/835 1.094
B4  s2027 | +0.025 [-0.084,+0.131] 0.669 | +0.069 [-0.053,+0.193] 0.844 | +0.064 [-0.157,+0.281] 0.709 | +0.168 [-0.050,+0.402] 0.935 | +0.072 [-0.032,+0.184] 0.914 | +0.100 [-0.060,+0.260] 0.897 | +0.24/+0.19 +16.4%/+12.6% 763/764 1.002
B5  s2027 | +0.345 [-0.032,+0.736] 0.963 | +0.066 [-0.077,+0.210] 0.816 | +0.065 [-0.168,+0.289] 0.688 | +0.130 [-0.096,+0.381] 0.847 | +0.184 [+0.009,+0.360] 0.979 | +0.087 [-0.067,+0.238] 0.854 | +0.30/+0.68 +28.0%/+34.1% 763/760 0.996
B6  s2027 | +0.417 [-0.023,+0.863] 0.969 | -0.089 [-0.320,+0.147] 0.212 | -0.141 [-0.506,+0.257] 0.237 | -0.064 [-0.445,+0.321] 0.375 | +0.081 [-0.159,+0.329] 0.734 | -0.122 [-0.399,+0.146] 0.190 | -0.19/+0.41 +21.6%/+31.6% 763/819 1.074

===== DELTAS caliber=log: Δ = arm − B0, net_ex bps/anchor, paired by anchor; day-block bootstrap NB=2000 seed=20260905; cells: Δ [CI95] P(Δ>0)
arm seed  |                         2024 |                  2024-H2->26 |                         2025 |                  2026<=08-10 |                     2024->26 |                     2025->26 | ΔSharpe(25on/24on) Δturn%(25on/24on) maxDD B0/Bk(25on) DD ratio
B1  s42   | +0.078 [-0.111,+0.277] 0.778 | +0.091 [+0.027,+0.160] 0.998 | +0.077 [+0.004,+0.160] 0.978 | +0.174 [+0.010,+0.340] 0.982 | +0.093 [+0.003,+0.185] 0.978 | +0.102 [+0.026,+0.181] 0.996 | +0.22/+0.31 -10.3%/-0.2% 784/798 1.017
B2  s42   | +0.161 [-0.173,+0.503] 0.825 | -0.280 [-0.534,-0.030] 0.017 | -0.298 [-0.749,+0.163] 0.097 | -0.501 [-1.000,-0.019] 0.019 | -0.167 [-0.402,+0.082] 0.091 | -0.364 [-0.695,-0.037] 0.015 | -0.70/-0.31 +15.3%/+17.0% 784/794 1.013
B3  s42   | +0.168 [-0.153,+0.499] 0.837 | -0.116 [-0.310,+0.071] 0.129 | -0.156 [-0.436,+0.129] 0.142 | +0.010 [-0.282,+0.321] 0.504 | -0.002 [-0.169,+0.171] 0.470 | -0.105 [-0.312,+0.110] 0.166 | -0.27/-0.01 -12.9%/-5.7% 784/865 1.103
B4  s42   | +0.037 [-0.051,+0.127] 0.797 | +0.011 [-0.096,+0.114] 0.595 | -0.036 [-0.216,+0.154] 0.368 | +0.064 [-0.110,+0.222] 0.767 | +0.016 [-0.068,+0.107] 0.637 | +0.004 [-0.124,+0.136] 0.537 | +0.00/+0.03 +15.3%/+9.9% 784/779 0.994
B5  s42   | +0.143 [-0.200,+0.511] 0.793 | +0.066 [-0.079,+0.209] 0.837 | -0.017 [-0.215,+0.177] 0.429 | +0.283 [-0.027,+0.601] 0.965 | +0.110 [-0.050,+0.281] 0.914 | +0.090 [-0.070,+0.261] 0.849 | +0.14/+0.33 +2.3%/+19.3% 784/783 0.999
B6  s42   | +0.172 [-0.282,+0.633] 0.778 | +0.042 [-0.200,+0.283] 0.637 | +0.047 [-0.305,+0.407] 0.593 | +0.127 [-0.215,+0.463] 0.764 | +0.103 [-0.137,+0.337] 0.794 | +0.062 [-0.193,+0.314] 0.686 | +0.04/+0.23 +0.7%/+21.0% 784/840 1.070
B1  s2027 | +0.094 [-0.093,+0.290] 0.819 | +0.096 [+0.030,+0.165] 0.998 | +0.072 [-0.002,+0.155] 0.974 | +0.173 [+0.007,+0.347] 0.981 | +0.097 [+0.007,+0.189] 0.985 | +0.099 [+0.021,+0.176] 0.992 | +0.20/+0.30 -10.6%/-0.7% 774/793 1.024
B2  s2027 | +0.162 [-0.215,+0.527] 0.807 | -0.275 [-0.533,-0.024] 0.015 | -0.309 [-0.767,+0.107] 0.084 | -0.472 [-1.003,+0.076] 0.045 | -0.163 [-0.416,+0.068] 0.094 | -0.358 [-0.689,-0.044] 0.012 | -0.67/-0.29 +16.1%/+17.3% 774/781 1.009
B3  s2027 | +0.175 [-0.148,+0.517] 0.851 | -0.114 [-0.322,+0.082] 0.120 | -0.151 [-0.447,+0.151] 0.152 | +0.028 [-0.272,+0.364] 0.577 | +0.005 [-0.185,+0.177] 0.526 | -0.097 [-0.300,+0.117] 0.186 | -0.25/+0.01 -13.9%/-6.2% 774/846 1.093
B4  s2027 | -0.011 [-0.100,+0.074] 0.387 | +0.026 [-0.072,+0.125] 0.678 | +0.015 [-0.165,+0.206] 0.561 | +0.076 [-0.068,+0.222] 0.840 | +0.020 [-0.060,+0.102] 0.689 | +0.039 [-0.082,+0.164] 0.737 | +0.10/+0.04 +14.5%/+9.6% 774/770 0.994
B5  s2027 | +0.103 [-0.234,+0.479] 0.720 | +0.106 [-0.045,+0.260] 0.922 | +0.112 [-0.100,+0.328] 0.836 | +0.282 [-0.034,+0.601] 0.960 | +0.143 [-0.030,+0.323] 0.947 | +0.168 [+0.005,+0.342] 0.977 | +0.31/+0.41 -0.6%/+18.4% 774/778 1.005
B6  s2027 | +0.091 [-0.288,+0.473] 0.685 | +0.034 [-0.191,+0.263] 0.624 | +0.033 [-0.302,+0.365] 0.555 | +0.147 [-0.178,+0.490] 0.823 | +0.072 [-0.133,+0.282] 0.755 | +0.060 [-0.185,+0.297] 0.682 | +0.04/+0.11 +0.1%/+17.2% 774/839 1.083

===== SEAT / φ TRAJECTORIES: yearly mean | switches (sign(x-0.5) flips) | jumps (|Δx|>=0.05) 24on/25on | φ state counts warm/dyn/fallback/clipped
  B0 prod s42   w3_king : 2022=0.184 2023=0.181 2024=0.723 2025=0.742 2026=0.383 | 25on mean 0.599 [0.174,1.000] switches 114/43 jumps 281/15
  B0 prod s42   w3f_f10 : 2022=0.184 2023=0.181 2024=0.723 2025=0.742 2026=0.383 | 25on mean 0.599 [0.174,1.000] switches 114/43 jumps 281/15
  B0 prod s42   phi_t   : 2022=0.450 2023=0.450 2024=0.450 2025=0.450 2026=0.450 | 25on mean 0.450 [0.450,0.450] switches 0/0 jumps 0/0 | φ states [10038, 0, 0, 0]
  B0 prod s2027 w3_king : 2022=0.184 2023=0.181 2024=0.723 2025=0.742 2026=0.383 | 25on mean 0.599 [0.174,1.000] switches 114/43 jumps 281/15
  B0 prod s2027 w3f_f10 : 2022=0.184 2023=0.181 2024=0.723 2025=0.742 2026=0.383 | 25on mean 0.599 [0.174,1.000] switches 114/43 jumps 281/15
  B0 prod s2027 phi_t   : 2022=0.450 2023=0.450 2024=0.450 2025=0.450 2026=0.450 | 25on mean 0.450 [0.450,0.450] switches 0/0 jumps 0/0 | φ states [10038, 0, 0, 0]
  B0 log  s42   w3_king : 2022=0.187 2023=0.205 2024=0.674 2025=0.717 2026=0.366 | 25on mean 0.577 [0.178,1.000] switches 107/23 jumps 244/12
  B0 log  s42   w3f_f10 : 2022=0.187 2023=0.205 2024=0.674 2025=0.717 2026=0.366 | 25on mean 0.577 [0.178,1.000] switches 107/23 jumps 244/12
  B0 log  s42   phi_t   : 2022=0.450 2023=0.450 2024=0.450 2025=0.450 2026=0.450 | 25on mean 0.450 [0.450,0.450] switches 0/0 jumps 0/0 | φ states [10038, 0, 0, 0]
  B0 log  s2027 w3_king : 2022=0.187 2023=0.205 2024=0.674 2025=0.717 2026=0.366 | 25on mean 0.577 [0.178,1.000] switches 107/23 jumps 244/12
  B0 log  s2027 w3f_f10 : 2022=0.187 2023=0.205 2024=0.674 2025=0.717 2026=0.366 | 25on mean 0.577 [0.178,1.000] switches 107/23 jumps 244/12
  B0 log  s2027 phi_t   : 2022=0.450 2023=0.450 2024=0.450 2025=0.450 2026=0.450 | 25on mean 0.450 [0.450,0.450] switches 0/0 jumps 0/0 | φ states [10038, 0, 0, 0]
  B1 prod s42   w3_king : 2022=0.172 2023=0.120 2024=0.706 2025=0.742 2026=0.383 | 25on mean 0.599 [0.174,1.000] switches 108/43 jumps 281/15
  B1 prod s42   w3f_f10 : 2022=0.172 2023=0.885 2024=0.967 2025=0.798 2026=0.389 | 25on mean 0.635 [0.274,1.000] switches 13/13 jumps 13/5
  B1 prod s42   phi_t   : 2022=0.450 2023=0.450 2024=0.450 2025=0.450 2026=0.450 | 25on mean 0.450 [0.450,0.450] switches 0/0 jumps 0/0 | φ states [10038, 0, 0, 0]
  B1 prod s2027 w3_king : 2022=0.172 2023=0.120 2024=0.706 2025=0.742 2026=0.383 | 25on mean 0.599 [0.174,1.000] switches 108/43 jumps 281/15
  B1 prod s2027 w3f_f10 : 2022=0.172 2023=0.877 2024=0.964 2025=0.830 2026=0.402 | 25on mean 0.660 [0.297,1.000] switches 61/61 jumps 5/3
  B1 prod s2027 phi_t   : 2022=0.450 2023=0.450 2024=0.450 2025=0.450 2026=0.450 | 25on mean 0.450 [0.450,0.450] switches 0/0 jumps 0/0 | φ states [10038, 0, 0, 0]
  B1 log  s42   w3_king : 2022=0.174 2023=0.137 2024=0.664 2025=0.717 2026=0.366 | 25on mean 0.577 [0.178,1.000] switches 98/23 jumps 244/12
  B1 log  s42   w3f_f10 : 2022=0.174 2023=0.875 2024=0.935 2025=0.591 2026=0.124 | 25on mean 0.405 [0.000,1.000] switches 17/17 jumps 95/28
  B1 log  s42   phi_t   : 2022=0.450 2023=0.450 2024=0.450 2025=0.450 2026=0.450 | 25on mean 0.450 [0.450,0.450] switches 0/0 jumps 0/0 | φ states [10038, 0, 0, 0]
  B1 log  s2027 w3_king : 2022=0.174 2023=0.137 2024=0.664 2025=0.717 2026=0.366 | 25on mean 0.577 [0.178,1.000] switches 98/23 jumps 244/12
  B1 log  s2027 w3f_f10 : 2022=0.174 2023=0.827 2024=0.917 2025=0.608 2026=0.111 | 25on mean 0.410 [0.000,1.000] switches 25/25 jumps 86/36
  B1 log  s2027 phi_t   : 2022=0.450 2023=0.450 2024=0.450 2025=0.450 2026=0.450 | 25on mean 0.450 [0.450,0.450] switches 0/0 jumps 0/0 | φ states [10038, 0, 0, 0]
  B2 prod s42   w3_king : 2022=0.405 2023=0.450 2024=0.906 2025=0.904 2026=0.569 | 25on mean 0.770 [0.000,1.000] switches 106/51 jumps 242/185
  B2 prod s42   w3f_f10 : 2022=0.405 2023=0.450 2024=0.906 2025=0.904 2026=0.569 | 25on mean 0.770 [0.000,1.000] switches 106/51 jumps 242/185
  B2 prod s42   phi_t   : 2022=0.450 2023=0.450 2024=0.450 2025=0.450 2026=0.450 | 25on mean 0.450 [0.450,0.450] switches 0/0 jumps 0/0 | φ states [10038, 0, 0, 0]
  B2 prod s2027 w3_king : 2022=0.405 2023=0.450 2024=0.906 2025=0.904 2026=0.569 | 25on mean 0.770 [0.000,1.000] switches 106/51 jumps 242/185
  B2 prod s2027 w3f_f10 : 2022=0.405 2023=0.450 2024=0.906 2025=0.904 2026=0.569 | 25on mean 0.770 [0.000,1.000] switches 106/51 jumps 242/185
  B2 prod s2027 phi_t   : 2022=0.450 2023=0.450 2024=0.450 2025=0.450 2026=0.450 | 25on mean 0.450 [0.450,0.450] switches 0/0 jumps 0/0 | φ states [10038, 0, 0, 0]
  B2 log  s42   w3_king : 2022=0.402 2023=0.464 2024=0.894 2025=0.884 2026=0.481 | 25on mean 0.724 [0.008,1.000] switches 106/33 jumps 150/68
  B2 log  s42   w3f_f10 : 2022=0.402 2023=0.464 2024=0.894 2025=0.884 2026=0.481 | 25on mean 0.724 [0.008,1.000] switches 106/33 jumps 150/68
  B2 log  s42   phi_t   : 2022=0.450 2023=0.450 2024=0.450 2025=0.450 2026=0.450 | 25on mean 0.450 [0.450,0.450] switches 0/0 jumps 0/0 | φ states [10038, 0, 0, 0]
  B2 log  s2027 w3_king : 2022=0.402 2023=0.464 2024=0.894 2025=0.884 2026=0.481 | 25on mean 0.724 [0.008,1.000] switches 106/33 jumps 150/68
  B2 log  s2027 w3f_f10 : 2022=0.402 2023=0.464 2024=0.894 2025=0.884 2026=0.481 | 25on mean 0.724 [0.008,1.000] switches 106/33 jumps 150/68
  B2 log  s2027 phi_t   : 2022=0.450 2023=0.450 2024=0.450 2025=0.450 2026=0.450 | 25on mean 0.450 [0.450,0.450] switches 0/0 jumps 0/0 | φ states [10038, 0, 0, 0]
  B3 prod s42   w3_king : 2022=0.410 2023=0.477 2024=0.625 2025=0.589 2026=0.304 | 25on mean 0.475 [0.000,1.000] switches 69/44 jumps 172/147
  B3 prod s42   w3f_f10 : 2022=0.410 2023=0.477 2024=0.625 2025=0.589 2026=0.304 | 25on mean 0.475 [0.000,1.000] switches 69/44 jumps 172/147
  B3 prod s42   phi_t   : 2022=0.450 2023=0.450 2024=0.450 2025=0.450 2026=0.450 | 25on mean 0.450 [0.450,0.450] switches 0/0 jumps 0/0 | φ states [10038, 0, 0, 0]
  B3 prod s2027 w3_king : 2022=0.410 2023=0.477 2024=0.625 2025=0.589 2026=0.304 | 25on mean 0.475 [0.000,1.000] switches 69/44 jumps 172/147
  B3 prod s2027 w3f_f10 : 2022=0.410 2023=0.477 2024=0.625 2025=0.589 2026=0.304 | 25on mean 0.475 [0.000,1.000] switches 69/44 jumps 172/147
  B3 prod s2027 phi_t   : 2022=0.450 2023=0.450 2024=0.450 2025=0.450 2026=0.450 | 25on mean 0.450 [0.450,0.450] switches 0/0 jumps 0/0 | φ states [10038, 0, 0, 0]
  B3 log  s42   w3_king : 2022=0.408 2023=0.487 2024=0.619 2025=0.558 2026=0.216 | 25on mean 0.422 [0.000,1.000] switches 67/40 jumps 111/84
  B3 log  s42   w3f_f10 : 2022=0.408 2023=0.487 2024=0.619 2025=0.558 2026=0.216 | 25on mean 0.422 [0.000,1.000] switches 67/40 jumps 111/84
  B3 log  s42   phi_t   : 2022=0.450 2023=0.450 2024=0.450 2025=0.450 2026=0.450 | 25on mean 0.450 [0.450,0.450] switches 0/0 jumps 0/0 | φ states [10038, 0, 0, 0]
  B3 log  s2027 w3_king : 2022=0.408 2023=0.487 2024=0.619 2025=0.558 2026=0.216 | 25on mean 0.422 [0.000,1.000] switches 67/40 jumps 111/84
  B3 log  s2027 w3f_f10 : 2022=0.408 2023=0.487 2024=0.619 2025=0.558 2026=0.216 | 25on mean 0.422 [0.000,1.000] switches 67/40 jumps 111/84
  B3 log  s2027 phi_t   : 2022=0.450 2023=0.450 2024=0.450 2025=0.450 2026=0.450 | 25on mean 0.450 [0.450,0.450] switches 0/0 jumps 0/0 | φ states [10038, 0, 0, 0]
  B4 prod s42   w3_king : 2022=0.184 2023=0.181 2024=0.723 2025=0.742 2026=0.383 | 25on mean 0.599 [0.174,1.000] switches 114/43 jumps 281/15
  B4 prod s42   w3f_f10 : 2022=0.184 2023=0.181 2024=0.723 2025=0.742 2026=0.383 | 25on mean 0.599 [0.174,1.000] switches 114/43 jumps 281/15
  B4 prod s42   phi_t   : 2022=0.384 2023=0.400 2024=0.434 2025=0.622 2026=0.638 | 25on mean 0.628 [0.200,0.800] switches 88/58 jumps 128/89 | φ states [900, 2974, 3436, 2728]
  B4 prod s2027 w3_king : 2022=0.184 2023=0.181 2024=0.723 2025=0.742 2026=0.383 | 25on mean 0.599 [0.174,1.000] switches 114/43 jumps 281/15
  B4 prod s2027 w3f_f10 : 2022=0.184 2023=0.181 2024=0.723 2025=0.742 2026=0.383 | 25on mean 0.599 [0.174,1.000] switches 114/43 jumps 281/15
  B4 prod s2027 phi_t   : 2022=0.384 2023=0.400 2024=0.453 2025=0.676 2026=0.650 | 25on mean 0.665 [0.265,0.800] switches 87/42 jumps 71/34 | φ states [900, 2849, 3406, 2883]
  B4 log  s42   w3_king : 2022=0.187 2023=0.205 2024=0.674 2025=0.717 2026=0.366 | 25on mean 0.577 [0.178,1.000] switches 107/23 jumps 244/12
  B4 log  s42   w3f_f10 : 2022=0.187 2023=0.205 2024=0.674 2025=0.717 2026=0.366 | 25on mean 0.577 [0.178,1.000] switches 107/23 jumps 244/12
  B4 log  s42   phi_t   : 2022=0.409 2023=0.397 2024=0.416 2025=0.527 2026=0.574 | 25on mean 0.545 [0.200,0.800] switches 98/72 jumps 141/110 | φ states [900, 3644, 3591, 1903]
  B4 log  s2027 w3_king : 2022=0.187 2023=0.205 2024=0.674 2025=0.717 2026=0.366 | 25on mean 0.577 [0.178,1.000] switches 107/23 jumps 244/12
  B4 log  s2027 w3f_f10 : 2022=0.187 2023=0.205 2024=0.674 2025=0.717 2026=0.366 | 25on mean 0.577 [0.178,1.000] switches 107/23 jumps 244/12
  B4 log  s2027 phi_t   : 2022=0.409 2023=0.409 2024=0.416 2025=0.599 2026=0.588 | 25on mean 0.594 [0.200,0.800] switches 94/70 jumps 63/42 | φ states [900, 3664, 3627, 1847]
  B5 prod s42   w3_king : 2022=0.172 2023=0.120 2024=0.706 2025=0.742 2026=0.383 | 25on mean 0.599 [0.174,1.000] switches 108/43 jumps 281/15
  B5 prod s42   w3f_f10 : 2022=0.172 2023=0.885 2024=0.967 2025=0.798 2026=0.389 | 25on mean 0.635 [0.274,1.000] switches 13/13 jumps 13/5
  B5 prod s42   phi_t   : 2022=0.397 2023=0.724 2024=0.639 2025=0.645 2026=0.631 | 25on mean 0.639 [0.200,0.800] switches 63/38 jumps 132/77 | φ states [900, 3264, 1521, 4353]
  B5 prod s2027 w3_king : 2022=0.172 2023=0.120 2024=0.706 2025=0.742 2026=0.383 | 25on mean 0.599 [0.174,1.000] switches 108/43 jumps 281/15
  B5 prod s2027 w3f_f10 : 2022=0.172 2023=0.877 2024=0.964 2025=0.830 2026=0.402 | 25on mean 0.660 [0.297,1.000] switches 61/61 jumps 5/3
  B5 prod s2027 phi_t   : 2022=0.397 2023=0.731 2024=0.705 2025=0.683 2026=0.647 | 25on mean 0.668 [0.335,0.800] switches 116/63 jumps 104/34 | φ states [900, 2994, 1120, 5024]
  B5 log  s42   w3_king : 2022=0.174 2023=0.137 2024=0.664 2025=0.717 2026=0.366 | 25on mean 0.577 [0.178,1.000] switches 98/23 jumps 244/12
  B5 log  s42   w3f_f10 : 2022=0.174 2023=0.875 2024=0.935 2025=0.591 2026=0.124 | 25on mean 0.405 [0.000,1.000] switches 17/17 jumps 95/28
  B5 log  s42   phi_t   : 2022=0.417 2023=0.730 2024=0.584 2025=0.522 2026=0.615 | 25on mean 0.559 [0.200,0.800] switches 89/53 jumps 205/113 | φ states [900, 3794, 1694, 3650]
  B5 log  s2027 w3_king : 2022=0.174 2023=0.137 2024=0.664 2025=0.717 2026=0.366 | 25on mean 0.577 [0.178,1.000] switches 98/23 jumps 244/12
  B5 log  s2027 w3f_f10 : 2022=0.174 2023=0.827 2024=0.917 2025=0.608 2026=0.111 | 25on mean 0.410 [0.000,1.000] switches 25/25 jumps 86/36
  B5 log  s2027 phi_t   : 2022=0.417 2023=0.711 2024=0.593 2025=0.605 2026=0.615 | 25on mean 0.609 [0.200,0.800] switches 74/29 jumps 153/52 | φ states [900, 3663, 1805, 3670]
  B6 prod s42   w3_king : 2022=0.323 2023=0.318 2024=0.500 2025=0.499 2026=0.281 | 25on mean 0.412 [0.000,1.000] switches 40/15 jumps 172/147
  B6 prod s42   w3f_f10 : 2022=0.323 2023=0.960 2024=0.842 2025=0.729 2026=0.255 | 25on mean 0.540 [0.000,1.000] switches 65/27 jumps 205/167
  B6 prod s42   phi_t   : 2022=0.357 2023=0.709 2024=0.632 2025=0.602 2026=0.710 | 25on mean 0.645 [0.200,0.800] switches 42/21 jumps 104/66 | φ states [900, 1973, 1121, 6044]
  B6 prod s2027 w3_king : 2022=0.323 2023=0.318 2024=0.500 2025=0.499 2026=0.281 | 25on mean 0.412 [0.000,1.000] switches 40/15 jumps 172/147
  B6 prod s2027 w3f_f10 : 2022=0.323 2023=0.958 2024=0.912 2025=0.704 2026=0.240 | 25on mean 0.519 [0.000,1.000] switches 83/67 jumps 228/212
  B6 prod s2027 phi_t   : 2022=0.357 2023=0.709 2024=0.730 2025=0.629 2026=0.698 | 25on mean 0.657 [0.200,0.800] switches 66/27 jumps 120/73 | φ states [900, 2623, 911, 5604]
  B6 log  s42   w3_king : 2022=0.322 2023=0.325 2024=0.493 2025=0.480 2026=0.216 | 25on mean 0.375 [0.000,1.000] switches 64/39 jumps 111/84
  B6 log  s42   w3f_f10 : 2022=0.322 2023=0.905 2024=0.508 2025=0.264 2026=0.000 | 25on mean 0.159 [0.000,0.333] switches 16/0 jumps 17/1
  B6 log  s42   phi_t   : 2022=0.377 2023=0.711 2024=0.520 2025=0.443 2026=0.609 | 25on mean 0.509 [0.200,0.800] switches 43/25 jumps 116/80 | φ states [900, 2065, 2048, 5025]
  B6 log  s2027 w3_king : 2022=0.322 2023=0.325 2024=0.493 2025=0.480 2026=0.216 | 25on mean 0.375 [0.000,1.000] switches 64/39 jumps 111/84
  B6 log  s2027 w3f_f10 : 2022=0.322 2023=0.785 2024=0.465 2025=0.264 2026=0.000 | 25on mean 0.159 [0.000,0.333] switches 18/0 jumps 21/1
  B6 log  s2027 phi_t   : 2022=0.377 2023=0.691 2024=0.477 2025=0.469 2026=0.613 | 25on mean 0.526 [0.200,0.800] switches 36/19 jumps 73/51 | φ states [900, 2047, 2466, 4625]

===== PER-BOOK own net/ug (bps/anchor): yearly mean; 2024->26 and 2025->26 mean/Sharpe
  B0 prod s42   king_book : 2022=+0.306 2023=-0.505 2024=+0.168 2025=+0.392 2026=+2.199 | 24on +0.757/S+1.26 | 25on +1.113/S+1.70
  B0 prod s42   f10_book  : 2022=-0.027 2023=-0.726 2024=+0.412 2025=+0.704 2026=+2.819 | 24on +1.120/S+1.74 | 25on +1.547/S+2.28
  B0 prod s2027 king_book : 2022=+0.306 2023=-0.509 2024=+0.147 2025=+0.420 2026=+2.194 | 24on +0.758/S+1.26 | 25on +1.127/S+1.73
  B0 prod s2027 f10_book  : 2022=-0.027 2023=-0.648 2024=+0.559 2025=+0.877 2026=+2.747 | 24on +1.222/S+1.95 | 25on +1.622/S+2.44
  B0 log  s42   king_book : 2022=+0.268 2023=-0.471 2024=+0.119 2025=+0.599 2026=+2.243 | 24on +0.828/S+1.38 | 25on +1.255/S+1.92
  B0 log  s42   f10_book  : 2022=-0.078 2023=-0.740 2024=+0.190 2025=+0.462 2026=+2.592 | 24on +0.889/S+1.39 | 25on +1.311/S+1.98
  B0 log  s2027 king_book : 2022=+0.268 2023=-0.473 2024=+0.120 2025=+0.595 2026=+2.247 | 24on +0.827/S+1.38 | 25on +1.254/S+1.92
  B0 log  s2027 f10_book  : 2022=-0.078 2023=-0.622 2024=+0.271 2025=+0.643 2026=+2.540 | 24on +0.975/S+1.54 | 25on +1.399/S+2.14
  B1 prod s42   king_book : 2022=+0.191 2023=-0.623 2024=+0.100 2025=+0.419 2026=+2.184 | 24on +0.738/S+1.22 | 25on +1.123/S+1.72
  B1 prod s42   f10_book  : 2022=-0.156 2023=+0.716 2024=+1.131 2025=+0.678 2026=+2.740 | 24on +1.361/S+2.25 | 25on +1.500/S+2.25
  B1 prod s2027 king_book : 2022=+0.191 2023=-0.607 2024=+0.138 2025=+0.386 2026=+2.197 | 24on +0.743/S+1.23 | 25on +1.108/S+1.70
  B1 prod s2027 f10_book  : 2022=-0.156 2023=+0.800 2024=+1.368 2025=+0.849 2026=+2.712 | 24on +1.508/S+2.59 | 25on +1.592/S+2.46
  B1 log  s42   king_book : 2022=+0.150 2023=-0.565 2024=+0.031 2025=+0.589 2026=+2.326 | 24on +0.811/S+1.35 | 25on +1.282/S+1.96
  B1 log  s42   f10_book  : 2022=-0.209 2023=+0.617 2024=+0.762 2025=+0.715 2026=+2.991 | 24on +1.299/S+1.95 | 25on +1.622/S+2.13
  B1 log  s2027 king_book : 2022=+0.150 2023=-0.580 2024=+0.068 2025=+0.595 2026=+2.288 | 24on +0.818/S+1.36 | 25on +1.270/S+1.94
  B1 log  s2027 f10_book  : 2022=-0.209 2023=+0.435 2024=+0.863 2025=+0.872 2026=+3.037 | 24on +1.407/S+2.15 | 25on +1.735/S+2.30
  B2 prod s42   king_book : 2022=+0.306 2023=-0.489 2024=+0.337 2025=-0.264 2026=+1.326 | 24on +0.357/S+0.58 | 25on +0.370/S+0.57
  B2 prod s42   f10_book  : 2022=-0.027 2023=-0.363 2024=+1.116 2025=+0.654 2026=+2.539 | 24on +1.297/S+2.37 | 25on +1.406/S+2.37
  B2 prod s2027 king_book : 2022=+0.306 2023=-0.496 2024=+0.312 2025=-0.264 2026=+1.429 | 24on +0.374/S+0.61 | 25on +0.411/S+0.63
  B2 prod s2027 f10_book  : 2022=-0.027 2023=-0.147 2024=+1.254 2025=+0.773 2026=+2.432 | 24on +1.367/S+2.56 | 25on +1.435/S+2.48
  B2 log  s42   king_book : 2022=+0.268 2023=-0.464 2024=+0.196 2025=+0.055 2026=+1.555 | 24on +0.481/S+0.78 | 25on +0.653/S+0.99
  B2 log  s42   f10_book  : 2022=-0.078 2023=-0.345 2024=+0.671 2025=+0.197 2026=+2.425 | 24on +0.929/S+1.62 | 25on +1.085/S+1.73
  B2 log  s2027 king_book : 2022=+0.268 2023=-0.456 2024=+0.170 2025=+0.029 2026=+1.643 | 24on +0.483/S+0.79 | 25on +0.672/S+1.02
  B2 log  s2027 f10_book  : 2022=-0.078 2023=-0.170 2024=+0.716 2025=+0.415 2026=+2.393 | 24on +1.020/S+1.83 | 25on +1.204/S+1.96
  B3 prod s42   king_book : 2022=+0.306 2023=-0.485 2024=+0.213 2025=+0.018 2026=+2.161 | 24on +0.625/S+1.07 | 25on +0.873/S+1.34
  B3 prod s42   f10_book  : 2022=-0.027 2023=-0.286 2024=+0.302 2025=+0.576 2026=+2.976 | 24on +1.070/S+1.58 | 25on +1.533/S+2.10
  B3 prod s2027 king_book : 2022=+0.306 2023=-0.505 2024=+0.174 2025=+0.009 2026=+2.149 | 24on +0.603/S+1.03 | 25on +0.862/S+1.33
  B3 prod s2027 f10_book  : 2022=-0.027 2023=-0.152 2024=+0.482 2025=+0.583 2026=+2.847 | 24on +1.108/S+1.67 | 25on +1.485/S+2.06
  B3 log  s42   king_book : 2022=+0.268 2023=-0.462 2024=+0.164 2025=+0.359 2026=+2.244 | 24on +0.754/S+1.23 | 25on +1.111/S+1.60
  B3 log  s42   f10_book  : 2022=-0.078 2023=-0.283 2024=+0.150 2025=+0.524 2026=+2.916 | 24on +0.978/S+1.41 | 25on +1.478/S+1.94
  B3 log  s2027 king_book : 2022=+0.268 2023=-0.458 2024=+0.150 2025=+0.365 2026=+2.205 | 24on +0.742/S+1.21 | 25on +1.099/S+1.59
  B3 log  s2027 f10_book  : 2022=-0.078 2023=-0.125 2024=+0.287 2025=+0.666 2026=+2.912 | 24on +1.082/S+1.56 | 25on +1.561/S+2.05
  B4 prod s42   king_book : 2022=+0.312 2023=-0.507 2024=+0.160 2025=+0.380 2026=+2.190 | 24on +0.747/S+1.23 | 25on +1.102/S+1.67
  B4 prod s42   f10_book  : 2022=-0.021 2023=-0.728 2024=+0.403 2025=+0.678 2026=+2.675 | 24on +1.071/S+1.67 | 25on +1.474/S+2.19
  B4 prod s2027 king_book : 2022=+0.312 2023=-0.512 2024=+0.143 2025=+0.379 2026=+2.208 | 24on +0.745/S+1.23 | 25on +1.109/S+1.69
  B4 prod s2027 f10_book  : 2022=-0.021 2023=-0.650 2024=+0.519 2025=+0.815 2026=+2.760 | 24on +1.188/S+1.89 | 25on +1.591/S+2.40
  B4 log  s42   king_book : 2022=+0.274 2023=-0.471 2024=+0.136 2025=+0.598 2026=+2.302 | 24on +0.848/S+1.41 | 25on +1.277/S+1.95
  B4 log  s42   f10_book  : 2022=-0.072 2023=-0.740 2024=+0.256 2025=+0.508 2026=+2.599 | 24on +0.933/S+1.47 | 25on +1.342/S+2.03
  B4 log  s2027 king_book : 2022=+0.274 2023=-0.473 2024=+0.127 2025=+0.536 2026=+2.290 | 24on +0.818/S+1.36 | 25on +1.235/S+1.89
  B4 log  s2027 f10_book  : 2022=-0.072 2023=-0.622 2024=+0.298 2025=+0.609 2026=+2.563 | 24on +0.978/S+1.56 | 25on +1.388/S+2.14
  B5 prod s42   king_book : 2022=+0.191 2023=-0.662 2024=+0.152 2025=+0.411 2026=+2.213 | 24on +0.762/S+1.25 | 25on +1.129/S+1.72
  B5 prod s42   f10_book  : 2022=-0.156 2023=+0.826 2024=+1.288 2025=+0.779 2026=+2.648 | 24on +1.436/S+2.39 | 25on +1.524/S+2.29
  B5 prod s2027 king_book : 2022=+0.191 2023=-0.621 2024=+0.050 2025=+0.378 2026=+2.197 | 24on +0.707/S+1.16 | 25on +1.103/S+1.68
  B5 prod s2027 f10_book  : 2022=-0.156 2023=+0.896 2024=+1.433 2025=+0.830 2026=+2.684 | 24on +1.518/S+2.61 | 25on +1.569/S+2.45
  B5 log  s42   king_book : 2022=+0.150 2023=-0.550 2024=+0.071 2025=+0.552 2026=+2.258 | 24on +0.795/S+1.32 | 25on +1.232/S+1.88
  B5 log  s42   f10_book  : 2022=-0.209 2023=+0.714 2024=+0.844 2025=+0.718 2026=+2.995 | 24on +1.332/S+1.99 | 25on +1.626/S+2.12
  B5 log  s2027 king_book : 2022=+0.150 2023=-0.635 2024=+0.030 2025=+0.555 2026=+2.233 | 24on +0.775/S+1.28 | 25on +1.224/S+1.87
  B5 log  s2027 f10_book  : 2022=-0.209 2023=+0.445 2024=+0.855 2025=+0.865 2026=+3.020 | 24on +1.397/S+2.13 | 25on +1.724/S+2.28
  B6 prod s42   king_book : 2022=+0.116 2023=-0.637 2024=+0.209 2025=+0.103 2026=+1.878 | 24on +0.585/S+0.93 | 25on +0.811/S+1.19
  B6 prod s42   f10_book  : 2022=-0.249 2023=+0.936 2024=+0.903 2025=+0.606 2026=+2.929 | 24on +1.296/S+2.05 | 25on +1.532/S+2.15
  B6 prod s2027 king_book : 2022=+0.116 2023=-0.614 2024=+0.109 2025=+0.107 2026=+1.997 | 24on +0.578/S+0.92 | 25on +0.860/S+1.26
  B6 prod s2027 f10_book  : 2022=-0.249 2023=+0.951 2024=+1.359 2025=+0.483 2026=+2.752 | 24on +1.377/S+2.21 | 25on +1.387/S+1.98
  B6 log  s42   king_book : 2022=+0.072 2023=-0.590 2024=+0.126 2025=+0.473 2026=+2.184 | 24on +0.768/S+1.19 | 25on +1.155/S+1.63
  B6 log  s42   f10_book  : 2022=-0.302 2023=+0.846 2024=-0.122 2025=+0.183 2026=+3.221 | 24on +0.824/S+1.19 | 25on +1.394/S+1.76
  B6 log  s2027 king_book : 2022=+0.072 2023=-0.562 2024=+0.126 2025=+0.492 2026=+2.182 | 24on +0.775/S+1.21 | 25on +1.166/S+1.64
  B6 log  s2027 f10_book  : 2022=-0.302 2023=+0.677 2024=-0.427 2025=+0.328 2026=+3.220 | 24on +0.763/S+1.07 | 25on +1.481/S+1.85

===== TURNOVER per leg (unit gross/anchor) and deduction 2.035·turn (bps/anchor), yearly means (from the B3 artifacts, legs() sequence); leg r 2025->26 B0 / B2 / B3 seat inputs
  prod s42   king  : turn 2022=0.0000 2023=0.0000 2024=0.6444 2025=0.5673 2026=0.5507 all=0.3444 | deduction 2022=0.000 2023=0.000 2024=1.311 2025=1.155 2026=1.121 | r 25on B0 +2.180 → B2 +1.147 → B3 +0.006
  prod s42   rev24 : turn 2022=0.5448 2023=0.5311 2024=0.5281 2025=0.5293 2026=0.5276 all=0.5323 | deduction 2022=1.109 2023=1.081 2024=1.075 2025=1.077 2026=1.074 | r 25on B0 +1.173 → B2 +0.837 → B3 -0.239
  prod s42   fund  : turn 2022=0.0411 2023=0.0414 2024=0.0512 2025=0.0392 2026=0.0297 all=0.0413 | deduction 2022=0.084 2023=0.084 2024=0.104 2025=0.080 2026=0.060 | r 25on B0 +2.515 → B2 +0.555 → B3 +0.483
  prod s42   f10   : turn 2022=0.0000 2023=0.0000 2024=0.0000 2025=0.0000 2026=0.0000 all=0.0000 | deduction 2022=0.000 2023=0.000 2024=0.000 2025=0.000 2026=0.000 | r 25on B0 +0.000 → B2 +0.000 → B3 +0.000 (f10 leg return recorded only under SEATF10=1; B0/B2/B3 have SEATF10=0 ⇒ 0)
  prod s2027 king  : turn 2022=0.0000 2023=0.0000 2024=0.6444 2025=0.5673 2026=0.5507 all=0.3444 | deduction 2022=0.000 2023=0.000 2024=1.311 2025=1.155 2026=1.121 | r 25on B0 +2.180 → B2 +1.147 → B3 +0.006
  prod s2027 rev24 : turn 2022=0.5448 2023=0.5311 2024=0.5281 2025=0.5293 2026=0.5276 all=0.5323 | deduction 2022=1.109 2023=1.081 2024=1.075 2025=1.077 2026=1.074 | r 25on B0 +1.173 → B2 +0.837 → B3 -0.239
  prod s2027 fund  : turn 2022=0.0411 2023=0.0414 2024=0.0512 2025=0.0392 2026=0.0297 all=0.0413 | deduction 2022=0.084 2023=0.084 2024=0.104 2025=0.080 2026=0.060 | r 25on B0 +2.515 → B2 +0.555 → B3 +0.483
  prod s2027 f10   : turn 2022=0.0000 2023=0.0000 2024=0.0000 2025=0.0000 2026=0.0000 all=0.0000 | deduction 2022=0.000 2023=0.000 2024=0.000 2025=0.000 2026=0.000 | r 25on B0 +0.000 → B2 +0.000 → B3 +0.000 (f10 leg return recorded only under SEATF10=1; B0/B2/B3 have SEATF10=0 ⇒ 0)
  log  s42   king  : turn 2022=0.0000 2023=0.0000 2024=0.6444 2025=0.5673 2026=0.5507 all=0.3444 | deduction 2022=0.000 2023=0.000 2024=1.311 2025=1.155 2026=1.121 | r 25on B0 +2.330 → B2 +1.297 → B3 +0.156
  log  s42   rev24 : turn 2022=0.5448 2023=0.5311 2024=0.5281 2025=0.5293 2026=0.5276 all=0.5323 | deduction 2022=1.109 2023=1.081 2024=1.075 2025=1.077 2026=1.074 | r 25on B0 +1.218 → B2 +0.882 → B3 -0.194
  log  s42   fund  : turn 2022=0.0411 2023=0.0414 2024=0.0512 2025=0.0392 2026=0.0297 all=0.0413 | deduction 2022=0.084 2023=0.084 2024=0.104 2025=0.080 2026=0.060 | r 25on B0 +2.768 → B2 +0.807 → B3 +0.735
  log  s42   f10   : turn 2022=0.0000 2023=0.0000 2024=0.0000 2025=0.0000 2026=0.0000 all=0.0000 | deduction 2022=0.000 2023=0.000 2024=0.000 2025=0.000 2026=0.000 | r 25on B0 +0.000 → B2 +0.000 → B3 +0.000 (f10 leg return recorded only under SEATF10=1; B0/B2/B3 have SEATF10=0 ⇒ 0)
  log  s2027 king  : turn 2022=0.0000 2023=0.0000 2024=0.6444 2025=0.5673 2026=0.5507 all=0.3444 | deduction 2022=0.000 2023=0.000 2024=1.311 2025=1.155 2026=1.121 | r 25on B0 +2.330 → B2 +1.297 → B3 +0.156
  log  s2027 rev24 : turn 2022=0.5448 2023=0.5311 2024=0.5281 2025=0.5293 2026=0.5276 all=0.5323 | deduction 2022=1.109 2023=1.081 2024=1.075 2025=1.077 2026=1.074 | r 25on B0 +1.218 → B2 +0.882 → B3 -0.194
  log  s2027 fund  : turn 2022=0.0411 2023=0.0414 2024=0.0512 2025=0.0392 2026=0.0297 all=0.0413 | deduction 2022=0.084 2023=0.084 2024=0.104 2025=0.080 2026=0.060 | r 25on B0 +2.768 → B2 +0.807 → B3 +0.735
  log  s2027 f10   : turn 2022=0.0000 2023=0.0000 2024=0.0000 2025=0.0000 2026=0.0000 all=0.0000 | deduction 2022=0.000 2023=0.000 2024=0.000 2025=0.000 2026=0.000 | r 25on B0 +0.000 → B2 +0.000 → B3 +0.000 (f10 leg return recorded only under SEATF10=1; B0/B2/B3 have SEATF10=0 ⇒ 0)
  prod s42   f10 (from B1/B6): turn 2022=0.0000 2023=1.0195 2024=0.9946 2025=1.0630 2026=0.7245 all=0.7767 | r 25on B1 gross +2.091 (king +2.180, fund +2.515) → B6 −carry +1.899 → −carry−fee +0.011
  prod s2027 f10 (from B1/B6): turn 2022=0.0000 2023=0.7675 2024=0.9011 2025=0.9625 2026=0.7897 all=0.6888 | r 25on B1 gross +2.225 (king +2.180, fund +2.515) → B6 −carry +1.865 → −carry−fee +0.046
  log  s42   f10 (from B1/B6): turn 2022=0.0000 2023=1.0195 2024=0.9946 2025=1.0630 2026=0.7245 all=0.7767 | r 25on B1 gross +0.442 (king +2.330, fund +2.768) → B6 −carry +0.250 → −carry−fee -1.639
  log  s2027 f10 (from B1/B6): turn 2022=0.0000 2023=0.7675 2024=0.9011 2025=0.9625 2026=0.7897 all=0.6888 | r 25on B1 gross +0.471 (king +2.330, fund +2.768) → B6 −carry +0.111 → −carry−fee -1.708

===== YEARLY TABLES (net_ex per unit gross): year | mean bps/anchor | ann %/gross | Sharpe | maxDD bps | 2×DD %NAV | worst month | n
  B0 prod s42    2022      : +0.166 bps | +3.6%/gross | S +0.47 | DD 499 bps | 2×DD 10.0% NAV | worst -310 (2022-08) | n 2010
  B0 prod s42    2023      : -0.538 bps | -11.8%/gross ⚠ | S -1.90 | DD 1388 bps | 2×DD 27.8% NAV | worst -535 (2023-01) | n 2190
  B0 prod s42    2024      : +0.108 bps | +2.4%/gross | S +0.45 | DD 846 bps | 2×DD 16.9% NAV | worst -285 (2024-04) | n 2196
  B0 prod s42    2025      : +0.203 bps | +4.4%/gross | S +0.67 | DD 409 bps | 2×DD 8.2% NAV | worst -326 (2025-04) | n 2190
  B0 prod s42    2026≤08-10: +2.510 bps | +55.0%/gross | S +4.94 | DD 356 bps | 2×DD 7.1% NAV | worst +58 (2026-02) | n 1332
  B1 prod s42    2022      : +0.058 bps | +1.3%/gross | S +0.16 | DD 585 bps | 2×DD 11.7% NAV | worst -295 (2022-08) | n 2010
  B1 prod s42    2023      : -0.126 bps | -2.8%/gross ⚠ | S -0.65 | DD 536 bps | 2×DD 10.7% NAV | worst -415 (2023-01) | n 2190
  B1 prod s42    2024      : +0.244 bps | +5.3%/gross | S +1.18 | DD 507 bps | 2×DD 10.1% NAV | worst -162 (2024-06) | n 2196
  B1 prod s42    2025      : +0.206 bps | +4.5%/gross | S +0.70 | DD 393 bps | 2×DD 7.9% NAV | worst -326 (2025-04) | n 2190
  B1 prod s42    2026≤08-10: +2.502 bps | +54.8%/gross | S +4.94 | DD 357 bps | 2×DD 7.1% NAV | worst +75 (2026-02) | n 1332
  B2 prod s42    2022      : +0.166 bps | +3.6%/gross | S +0.47 | DD 499 bps | 2×DD 10.0% NAV | worst -310 (2022-08) | n 2010
  B2 prod s42    2023      : -0.390 bps | -8.5%/gross ⚠ | S -1.48 | DD 1200 bps | 2×DD 24.0% NAV | worst -441 (2023-01) | n 2190
  B2 prod s42    2024      : +0.350 bps | +7.7%/gross | S +1.54 | DD 514 bps | 2×DD 10.3% NAV | worst -211 (2024-07) | n 2196
  B2 prod s42    2025      : -0.034 bps | -0.8%/gross ⚠ | S -0.14 | DD 774 bps | 2×DD 15.5% NAV | worst -371 (2025-12) | n 2190
  B2 prod s42    2026≤08-10: +1.891 bps | +41.4%/gross | S +4.27 | DD 341 bps | 2×DD 6.8% NAV | worst -13 (2026-02) | n 1332
  B3 prod s42    2022      : +0.166 bps | +3.6%/gross | S +0.47 | DD 499 bps | 2×DD 10.0% NAV | worst -310 (2022-08) | n 2010
  B3 prod s42    2023      : -0.367 bps | -8.0%/gross ⚠ | S -1.40 | DD 1174 bps | 2×DD 23.5% NAV | worst -441 (2023-01) | n 2190
  B3 prod s42    2024      : +0.283 bps | +6.2%/gross | S +1.13 | DD 643 bps | 2×DD 12.9% NAV | worst -268 (2024-07) | n 2196
  B3 prod s42    2025      : +0.042 bps | +0.9%/gross | S +0.14 | DD 558 bps | 2×DD 11.2% NAV | worst -346 (2025-04) | n 2190
  B3 prod s42    2026≤08-10: +2.447 bps | +53.6%/gross | S +4.89 | DD 371 bps | 2×DD 7.4% NAV | worst +90 (2026-02) | n 1332
  B4 prod s42    2022      : +0.174 bps | +3.8%/gross | S +0.49 | DD 495 bps | 2×DD 9.9% NAV | worst -307 (2022-08) | n 2010
  B4 prod s42    2023      : -0.535 bps | -11.7%/gross ⚠ | S -1.90 | DD 1388 bps | 2×DD 27.8% NAV | worst -535 (2023-01) | n 2190
  B4 prod s42    2024      : +0.145 bps | +3.2%/gross | S +0.58 | DD 795 bps | 2×DD 15.9% NAV | worst -319 (2024-04) | n 2196
  B4 prod s42    2025      : +0.169 bps | +3.7%/gross | S +0.58 | DD 384 bps | 2×DD 7.7% NAV | worst -206 (2025-04) | n 2190
  B4 prod s42    2026≤08-10: +2.602 bps | +57.0%/gross | S +5.02 | DD 361 bps | 2×DD 7.2% NAV | worst +99 (2026-08) | n 1332
  B5 prod s42    2022      : +0.061 bps | +1.3%/gross | S +0.17 | DD 582 bps | 2×DD 11.6% NAV | worst -291 (2022-08) | n 2010
  B5 prod s42    2023      : +0.114 bps | +2.5%/gross | S +0.66 | DD 503 bps | 2×DD 10.1% NAV | worst -419 (2023-01) | n 2190
  B5 prod s42    2024      : +0.331 bps | +7.3%/gross | S +1.72 | DD 280 bps | 2×DD 5.6% NAV | worst -149 (2024-02) | n 2196
  B5 prod s42    2025      : +0.255 bps | +5.6%/gross | S +0.91 | DD 395 bps | 2×DD 7.9% NAV | worst -208 (2025-04) | n 2190
  B5 prod s42    2026≤08-10: +2.589 bps | +56.7%/gross | S +4.99 | DD 360 bps | 2×DD 7.2% NAV | worst +97 (2026-08) | n 1332
  B6 prod s42    2022      : +0.104 bps | +2.3%/gross | S +0.30 | DD 444 bps | 2×DD 8.9% NAV | worst -288 (2022-12) | n 2010
  B6 prod s42    2023      : +0.185 bps | +4.0%/gross | S +1.12 | DD 309 bps | 2×DD 6.2% NAV | worst -251 (2023-01) | n 2190
  B6 prod s42    2024      : +0.333 bps | +7.3%/gross | S +1.62 | DD 248 bps | 2×DD 5.0% NAV | worst -159 (2024-02) | n 2196
  B6 prod s42    2025      : +0.218 bps | +4.8%/gross | S +0.80 | DD 410 bps | 2×DD 8.2% NAV | worst -275 (2025-12) | n 2190
  B6 prod s42    2026≤08-10: +2.525 bps | +55.3%/gross | S +4.97 | DD 386 bps | 2×DD 7.7% NAV | worst +60 (2026-02) | n 1332
  B0 prod s2027  2022      : +0.166 bps | +3.6%/gross | S +0.47 | DD 499 bps | 2×DD 10.0% NAV | worst -310 (2022-08) | n 2010
  B0 prod s2027  2023      : -0.519 bps | -11.4%/gross ⚠ | S -1.83 | DD 1325 bps | 2×DD 26.5% NAV | worst -540 (2023-01) | n 2190
  B0 prod s2027  2024      : +0.147 bps | +3.2%/gross | S +0.61 | DD 852 bps | 2×DD 17.0% NAV | worst -270 (2024-04) | n 2196
  B0 prod s2027  2025      : +0.268 bps | +5.9%/gross | S +0.86 | DD 404 bps | 2×DD 8.1% NAV | worst -297 (2025-04) | n 2190
  B0 prod s2027  2026≤08-10: +2.488 bps | +54.5%/gross | S +4.90 | DD 345 bps | 2×DD 6.9% NAV | worst +72 (2026-02) | n 1332
  B1 prod s2027  2022      : +0.058 bps | +1.3%/gross | S +0.16 | DD 585 bps | 2×DD 11.7% NAV | worst -295 (2022-08) | n 2010
  B1 prod s2027  2023      : -0.096 bps | -2.1%/gross ⚠ | S -0.48 | DD 535 bps | 2×DD 10.7% NAV | worst -486 (2023-01) | n 2190
  B1 prod s2027  2024      : +0.316 bps | +6.9%/gross | S +1.50 | DD 451 bps | 2×DD 9.0% NAV | worst -170 (2024-06) | n 2196
  B1 prod s2027  2025      : +0.248 bps | +5.4%/gross | S +0.84 | DD 359 bps | 2×DD 7.2% NAV | worst -297 (2025-04) | n 2190
  B1 prod s2027  2026≤08-10: +2.493 bps | +54.6%/gross | S +4.92 | DD 347 bps | 2×DD 6.9% NAV | worst +61 (2026-02) | n 1332
  B2 prod s2027  2022      : +0.166 bps | +3.6%/gross | S +0.47 | DD 499 bps | 2×DD 10.0% NAV | worst -310 (2022-08) | n 2010
  B2 prod s2027  2023      : -0.340 bps | -7.4%/gross ⚠ | S -1.27 | DD 1085 bps | 2×DD 21.7% NAV | worst -440 (2023-01) | n 2190
  B2 prod s2027  2024      : +0.418 bps | +9.2%/gross | S +1.80 | DD 493 bps | 2×DD 9.9% NAV | worst -189 (2024-07) | n 2196
  B2 prod s2027  2025      : +0.024 bps | +0.5%/gross | S +0.10 | DD 791 bps | 2×DD 15.8% NAV | worst -398 (2025-12) | n 2190
  B2 prod s2027  2026≤08-10: +1.866 bps | +40.9%/gross | S +4.21 | DD 330 bps | 2×DD 6.6% NAV | worst -24 (2026-02) | n 1332
  B3 prod s2027  2022      : +0.166 bps | +3.6%/gross | S +0.47 | DD 499 bps | 2×DD 10.0% NAV | worst -310 (2022-08) | n 2010
  B3 prod s2027  2023      : -0.339 bps | -7.4%/gross ⚠ | S -1.27 | DD 1082 bps | 2×DD 21.6% NAV | worst -440 (2023-01) | n 2190
  B3 prod s2027  2024      : +0.327 bps | +7.2%/gross | S +1.30 | DD 604 bps | 2×DD 12.1% NAV | worst -246 (2024-07) | n 2196
  B3 prod s2027  2025      : +0.073 bps | +1.6%/gross | S +0.24 | DD 519 bps | 2×DD 10.4% NAV | worst -317 (2025-04) | n 2190
  B3 prod s2027  2026≤08-10: +2.401 bps | +52.6%/gross | S +4.82 | DD 366 bps | 2×DD 7.3% NAV | worst +101 (2026-02) | n 1332
  B4 prod s2027  2022      : +0.174 bps | +3.8%/gross | S +0.49 | DD 495 bps | 2×DD 9.9% NAV | worst -307 (2022-08) | n 2010
  B4 prod s2027  2023      : -0.517 bps | -11.3%/gross ⚠ | S -1.82 | DD 1324 bps | 2×DD 26.5% NAV | worst -540 (2023-01) | n 2190
  B4 prod s2027  2024      : +0.172 bps | +3.8%/gross | S +0.69 | DD 760 bps | 2×DD 15.2% NAV | worst -283 (2024-04) | n 2196
  B4 prod s2027  2025      : +0.331 bps | +7.3%/gross | S +1.09 | DD 442 bps | 2×DD 8.8% NAV | worst -155 (2025-04) | n 2190
  B4 prod s2027  2026≤08-10: +2.656 bps | +58.2%/gross | S +5.12 | DD 347 bps | 2×DD 6.9% NAV | worst +115 (2026-08) | n 1332
  B5 prod s2027  2022      : +0.061 bps | +1.3%/gross | S +0.17 | DD 582 bps | 2×DD 11.6% NAV | worst -291 (2022-08) | n 2010
  B5 prod s2027  2023      : +0.167 bps | +3.7%/gross | S +0.90 | DD 538 bps | 2×DD 10.8% NAV | worst -490 (2023-01) | n 2190
  B5 prod s2027  2024      : +0.492 bps | +10.8%/gross | S +2.63 | DD 184 bps | 2×DD 3.7% NAV | worst -41 (2024-06) | n 2196
  B5 prod s2027  2025      : +0.332 bps | +7.3%/gross | S +1.21 | DD 367 bps | 2×DD 7.3% NAV | worst -152 (2025-11) | n 2190
  B5 prod s2027  2026≤08-10: +2.617 bps | +57.3%/gross | S +5.09 | DD 350 bps | 2×DD 7.0% NAV | worst +108 (2026-08) | n 1332
  B6 prod s2027  2022      : +0.104 bps | +2.3%/gross | S +0.30 | DD 444 bps | 2×DD 8.9% NAV | worst -288 (2022-12) | n 2010
  B6 prod s2027  2023      : +0.251 bps | +5.5%/gross | S +1.41 | DD 358 bps | 2×DD 7.2% NAV | worst -297 (2023-01) | n 2190
  B6 prod s2027  2024      : +0.564 bps | +12.4%/gross | S +3.00 | DD 232 bps | 2×DD 4.6% NAV | worst -38 (2024-05) | n 2196
  B6 prod s2027  2025      : +0.126 bps | +2.8%/gross | S +0.47 | DD 439 bps | 2×DD 8.8% NAV | worst -291 (2025-12) | n 2190
  B6 prod s2027  2026≤08-10: +2.424 bps | +53.1%/gross | S +4.82 | DD 368 bps | 2×DD 7.4% NAV | worst +45 (2026-02) | n 1332
  B0 log  s42    2022      : +0.186 bps | +4.1%/gross | S +0.52 | DD 477 bps | 2×DD 9.5% NAV | worst -295 (2022-08) | n 2010
  B0 log  s42    2023      : -0.506 bps | -11.1%/gross ⚠ | S -1.80 | DD 1358 bps | 2×DD 27.2% NAV | worst -484 (2023-01) | n 2190
  B0 log  s42    2024      : +0.068 bps | +1.5%/gross | S +0.27 | DD 871 bps | 2×DD 17.4% NAV | worst -315 (2024-04) | n 2196
  B0 log  s42    2025      : +0.261 bps | +5.7%/gross | S +0.87 | DD 412 bps | 2×DD 8.2% NAV | worst -333 (2025-04) | n 2190
  B0 log  s42    2026≤08-10: +2.505 bps | +54.9%/gross | S +4.88 | DD 365 bps | 2×DD 7.3% NAV | worst +24 (2026-02) | n 1332
  B1 log  s42    2022      : +0.078 bps | +1.7%/gross | S +0.22 | DD 569 bps | 2×DD 11.4% NAV | worst -295 (2022-08) | n 2010
  B1 log  s42    2023      : -0.112 bps | -2.5%/gross ⚠ | S -0.57 | DD 540 bps | 2×DD 10.8% NAV | worst -387 (2023-01) | n 2190
  B1 log  s42    2024      : +0.146 bps | +3.2%/gross | S +0.72 | DD 578 bps | 2×DD 11.6% NAV | worst -163 (2024-02) | n 2196
  B1 log  s42    2025      : +0.338 bps | +7.4%/gross | S +1.14 | DD 412 bps | 2×DD 8.2% NAV | worst -333 (2025-04) | n 2190
  B1 log  s42    2026≤08-10: +2.679 bps | +58.7%/gross | S +5.07 | DD 356 bps | 2×DD 7.1% NAV | worst +34 (2026-02) | n 1332
  B2 log  s42    2022      : +0.186 bps | +4.1%/gross | S +0.52 | DD 477 bps | 2×DD 9.5% NAV | worst -295 (2022-08) | n 2010
  B2 log  s42    2023      : -0.379 bps | -8.3%/gross ⚠ | S -1.45 | DD 1207 bps | 2×DD 24.1% NAV | worst -435 (2023-01) | n 2190
  B2 log  s42    2024      : +0.229 bps | +5.0%/gross | S +0.99 | DD 560 bps | 2×DD 11.2% NAV | worst -190 (2024-07) | n 2196
  B2 log  s42    2025      : -0.037 bps | -0.8%/gross ⚠ | S -0.15 | DD 647 bps | 2×DD 12.9% NAV | worst -333 (2025-04) | n 2190
  B2 log  s42    2026≤08-10: +2.004 bps | +43.9%/gross | S +4.43 | DD 366 bps | 2×DD 7.3% NAV | worst -32 (2026-02) | n 1332
  B3 log  s42    2022      : +0.186 bps | +4.1%/gross | S +0.52 | DD 477 bps | 2×DD 9.5% NAV | worst -295 (2022-08) | n 2010
  B3 log  s42    2023      : -0.362 bps | -7.9%/gross ⚠ | S -1.39 | DD 1175 bps | 2×DD 23.5% NAV | worst -435 (2023-01) | n 2190
  B3 log  s42    2024      : +0.236 bps | +5.2%/gross | S +0.94 | DD 658 bps | 2×DD 13.2% NAV | worst -262 (2024-04) | n 2196
  B3 log  s42    2025      : +0.105 bps | +2.3%/gross | S +0.35 | DD 579 bps | 2×DD 11.6% NAV | worst -347 (2025-04) | n 2190
  B3 log  s42    2026≤08-10: +2.515 bps | +55.1%/gross | S +4.86 | DD 385 bps | 2×DD 7.7% NAV | worst +68 (2026-02) | n 1332
  B4 log  s42    2022      : +0.193 bps | +4.2%/gross | S +0.54 | DD 473 bps | 2×DD 9.5% NAV | worst -292 (2022-08) | n 2010
  B4 log  s42    2023      : -0.503 bps | -11.0%/gross ⚠ | S -1.79 | DD 1356 bps | 2×DD 27.1% NAV | worst -484 (2023-01) | n 2190
  B4 log  s42    2024      : +0.105 bps | +2.3%/gross | S +0.40 | DD 841 bps | 2×DD 16.8% NAV | worst -316 (2024-04) | n 2196
  B4 log  s42    2025      : +0.224 bps | +4.9%/gross | S +0.76 | DD 357 bps | 2×DD 7.1% NAV | worst -255 (2025-04) | n 2190
  B4 log  s42    2026≤08-10: +2.569 bps | +56.3%/gross | S +4.94 | DD 369 bps | 2×DD 7.4% NAV | worst +49 (2026-02) | n 1332
  B5 log  s42    2022      : +0.079 bps | +1.7%/gross | S +0.22 | DD 566 bps | 2×DD 11.3% NAV | worst -293 (2022-08) | n 2010
  B5 log  s42    2023      : +0.088 bps | +1.9%/gross | S +0.50 | DD 484 bps | 2×DD 9.7% NAV | worst -384 (2023-01) | n 2190
  B5 log  s42    2024      : +0.211 bps | +4.6%/gross | S +1.07 | DD 343 bps | 2×DD 6.9% NAV | worst -163 (2024-02) | n 2196
  B5 log  s42    2025      : +0.244 bps | +5.3%/gross | S +0.83 | DD 330 bps | 2×DD 6.6% NAV | worst -262 (2025-04) | n 2190
  B5 log  s42    2026≤08-10: +2.788 bps | +61.1%/gross | S +5.08 | DD 360 bps | 2×DD 7.2% NAV | worst +78 (2026-02) | n 1332
  B6 log  s42    2022      : +0.114 bps | +2.5%/gross | S +0.32 | DD 468 bps | 2×DD 9.4% NAV | worst -286 (2022-12) | n 2010
  B6 log  s42    2023      : +0.142 bps | +3.1%/gross | S +0.79 | DD 356 bps | 2×DD 7.1% NAV | worst -213 (2023-01) | n 2190
  B6 log  s42    2024      : +0.240 bps | +5.3%/gross | S +1.00 | DD 553 bps | 2×DD 11.1% NAV | worst -301 (2024-02) | n 2196
  B6 log  s42    2025      : +0.308 bps | +6.7%/gross | S +0.92 | DD 584 bps | 2×DD 11.7% NAV | worst -483 (2025-04) | n 2190
  B6 log  s42    2026≤08-10: +2.632 bps | +57.6%/gross | S +5.05 | DD 382 bps | 2×DD 7.6% NAV | worst +75 (2026-02) | n 1332
  B0 log  s2027  2022      : +0.186 bps | +4.1%/gross | S +0.52 | DD 477 bps | 2×DD 9.5% NAV | worst -295 (2022-08) | n 2010
  B0 log  s2027  2023      : -0.471 bps | -10.3%/gross ⚠ | S -1.67 | DD 1288 bps | 2×DD 25.8% NAV | worst -463 (2023-01) | n 2190
  B0 log  s2027  2024      : +0.105 bps | +2.3%/gross | S +0.42 | DD 857 bps | 2×DD 17.1% NAV | worst -301 (2024-04) | n 2196
  B0 log  s2027  2025      : +0.321 bps | +7.0%/gross | S +1.04 | DD 379 bps | 2×DD 7.6% NAV | worst -301 (2025-04) | n 2190
  B0 log  s2027  2026≤08-10: +2.485 bps | +54.4%/gross | S +4.85 | DD 373 bps | 2×DD 7.5% NAV | worst +16 (2026-02) | n 1332
  B1 log  s2027  2022      : +0.078 bps | +1.7%/gross | S +0.22 | DD 569 bps | 2×DD 11.4% NAV | worst -295 (2022-08) | n 2010
  B1 log  s2027  2023      : -0.135 bps | -3.0%/gross ⚠ | S -0.63 | DD 600 bps | 2×DD 12.0% NAV | worst -522 (2023-01) | n 2190
  B1 log  s2027  2024      : +0.199 bps | +4.4%/gross | S +0.96 | DD 550 bps | 2×DD 11.0% NAV | worst -172 (2024-02) | n 2196
  B1 log  s2027  2025      : +0.393 bps | +8.6%/gross | S +1.27 | DD 379 bps | 2×DD 7.6% NAV | worst -301 (2025-04) | n 2190
  B1 log  s2027  2026≤08-10: +2.659 bps | +58.2%/gross | S +5.03 | DD 362 bps | 2×DD 7.2% NAV | worst +28 (2026-02) | n 1332
  B2 log  s2027  2022      : +0.186 bps | +4.1%/gross | S +0.52 | DD 477 bps | 2×DD 9.5% NAV | worst -295 (2022-08) | n 2010
  B2 log  s2027  2023      : -0.324 bps | -7.1%/gross ⚠ | S -1.22 | DD 1105 bps | 2×DD 22.1% NAV | worst -428 (2023-01) | n 2190
  B2 log  s2027  2024      : +0.267 bps | +5.9%/gross | S +1.14 | DD 571 bps | 2×DD 11.4% NAV | worst -170 (2024-07) | n 2196
  B2 log  s2027  2025      : +0.012 bps | +0.3%/gross | S +0.04 | DD 655 bps | 2×DD 13.1% NAV | worst -351 (2025-12) | n 2190
  B2 log  s2027  2026≤08-10: +2.013 bps | +44.1%/gross | S +4.45 | DD 369 bps | 2×DD 7.4% NAV | worst -42 (2026-02) | n 1332
  B3 log  s2027  2022      : +0.186 bps | +4.1%/gross | S +0.52 | DD 477 bps | 2×DD 9.5% NAV | worst -295 (2022-08) | n 2010
  B3 log  s2027  2023      : -0.310 bps | -6.8%/gross ⚠ | S -1.18 | DD 1087 bps | 2×DD 21.7% NAV | worst -428 (2023-01) | n 2190
  B3 log  s2027  2024      : +0.280 bps | +6.1%/gross | S +1.12 | DD 626 bps | 2×DD 12.5% NAV | worst -245 (2024-07) | n 2196
  B3 log  s2027  2025      : +0.170 bps | +3.7%/gross | S +0.56 | DD 536 bps | 2×DD 10.7% NAV | worst -318 (2025-04) | n 2190
  B3 log  s2027  2026≤08-10: +2.513 bps | +55.0%/gross | S +4.86 | DD 386 bps | 2×DD 7.7% NAV | worst +75 (2026-02) | n 1332
  B4 log  s2027  2022      : +0.193 bps | +4.2%/gross | S +0.54 | DD 473 bps | 2×DD 9.5% NAV | worst -292 (2022-08) | n 2010
  B4 log  s2027  2023      : -0.469 bps | -10.3%/gross ⚠ | S -1.66 | DD 1285 bps | 2×DD 25.7% NAV | worst -464 (2023-01) | n 2190
  B4 log  s2027  2024      : +0.094 bps | +2.1%/gross | S +0.36 | DD 864 bps | 2×DD 17.3% NAV | worst -324 (2024-04) | n 2196
  B4 log  s2027  2025      : +0.336 bps | +7.4%/gross | S +1.11 | DD 384 bps | 2×DD 7.7% NAV | worst -236 (2025-04) | n 2190
  B4 log  s2027  2026≤08-10: +2.561 bps | +56.1%/gross | S +4.93 | DD 373 bps | 2×DD 7.5% NAV | worst +56 (2026-02) | n 1332
  B5 log  s2027  2022      : +0.079 bps | +1.7%/gross | S +0.22 | DD 566 bps | 2×DD 11.3% NAV | worst -293 (2022-08) | n 2010
  B5 log  s2027  2023      : +0.095 bps | +2.1%/gross | S +0.47 | DD 603 bps | 2×DD 12.1% NAV | worst -526 (2023-01) | n 2190
  B5 log  s2027  2024      : +0.208 bps | +4.6%/gross | S +1.04 | DD 412 bps | 2×DD 8.2% NAV | worst -172 (2024-02) | n 2196
  B5 log  s2027  2025      : +0.433 bps | +9.5%/gross | S +1.41 | DD 334 bps | 2×DD 6.7% NAV | worst -231 (2025-04) | n 2190
  B5 log  s2027  2026≤08-10: +2.768 bps | +60.6%/gross | S +5.06 | DD 364 bps | 2×DD 7.3% NAV | worst +81 (2026-02) | n 1332
  B6 log  s2027  2022      : +0.114 bps | +2.5%/gross | S +0.32 | DD 468 bps | 2×DD 9.4% NAV | worst -286 (2022-12) | n 2010
  B6 log  s2027  2023      : +0.138 bps | +3.0%/gross | S +0.66 | DD 384 bps | 2×DD 7.7% NAV | worst -278 (2023-01) | n 2190
  B6 log  s2027  2024      : +0.197 bps | +4.3%/gross | S +0.74 | DD 738 bps | 2×DD 14.8% NAV | worst -235 (2024-02) | n 2196
  B6 log  s2027  2025      : +0.354 bps | +7.7%/gross | S +1.04 | DD 570 bps | 2×DD 11.4% NAV | worst -478 (2025-04) | n 2190
  B6 log  s2027  2026≤08-10: +2.632 bps | +57.7%/gross | S +5.05 | DD 382 bps | 2×DD 7.6% NAV | worst +78 (2026-02) | n 1332

===== σ_fund TERCILES of Δ (2024->26): cuts 5.45/13.67 bps; n per tercile [1946, 1946, 1946]; mean σ per tercile [3.237, 9.56, 21.086]
  prod s42   B1: low +0.171 [-0.017,+0.385] P0.96 (+0.037→+0.208) | mid -0.028 [-0.103,+0.049] P0.23 (+0.508→+0.480) | high +0.003 [-0.071,+0.077] P0.53 (+1.296→+1.298)
  prod s42   B2: low +0.306 [-0.040,+0.700] P0.95 (+0.037→+0.343) | mid +0.046 [-0.267,+0.363] P0.59 (+0.508→+0.554) | high -0.780 [-1.453,-0.129] P0.01 (+1.296→+0.516)
  prod s42   B3: low +0.060 [-0.312,+0.431] P0.64 (+0.037→+0.097) | mid -0.118 [-0.359,+0.143] P0.18 (+0.508→+0.390) | high -0.000 [-0.351,+0.322] P0.49 (+1.296→+1.295)
  prod s42   B4: low +0.011 [-0.113,+0.133] P0.56 (+0.037→+0.049) | mid -0.073 [-0.243,+0.088] P0.18 (+0.508→+0.435) | high +0.123 [-0.115,+0.351] P0.84 (+1.296→+1.419)
  prod s42   B5: low +0.291 [-0.092,+0.686] P0.93 (+0.037→+0.328) | mid -0.098 [-0.283,+0.097] P0.18 (+0.508→+0.410) | high +0.167 [-0.060,+0.395] P0.93 (+1.296→+1.463)
  prod s42   B6: low +0.288 [-0.217,+0.797] P0.86 (+0.037→+0.325) | mid -0.039 [-0.362,+0.292] P0.40 (+0.508→+0.469) | high +0.003 [-0.381,+0.405] P0.52 (+1.296→+1.299)
  prod s2027 B1: low +0.198 [+0.011,+0.402] P0.98 (+0.038→+0.236) | mid -0.015 [-0.095,+0.071] P0.37 (+0.566→+0.552) | high -0.010 [-0.112,+0.087] P0.41 (+1.340→+1.330)
  prod s2027 B2: low +0.342 [-0.023,+0.726] P0.97 (+0.038→+0.380) | mid +0.039 [-0.250,+0.343] P0.59 (+0.566→+0.605) | high -0.784 [-1.473,-0.120] P0.01 (+1.340→+0.556)
  prod s2027 B3: low +0.069 [-0.290,+0.411] P0.64 (+0.038→+0.106) | mid -0.151 [-0.400,+0.108] P0.13 (+0.566→+0.416) | high -0.024 [-0.388,+0.329] P0.43 (+1.340→+1.316)
  prod s2027 B4: low -0.016 [-0.154,+0.113] P0.41 (+0.038→+0.021) | mid -0.028 [-0.186,+0.131] P0.38 (+0.566→+0.539) | high +0.259 [+0.034,+0.503] P0.99 (+1.340→+1.599)
  prod s2027 B5: low +0.453 [+0.045,+0.896] P0.99 (+0.038→+0.491) | mid -0.139 [-0.356,+0.073] P0.10 (+0.566→+0.427) | high +0.239 [+0.001,+0.492] P0.97 (+1.340→+1.578)
  prod s2027 B6: low +0.464 [-0.050,+0.953] P0.96 (+0.038→+0.502) | mid -0.090 [-0.407,+0.213] P0.27 (+0.566→+0.476) | high -0.132 [-0.534,+0.266] P0.27 (+1.340→+1.208)
  log  s42   B1: low +0.105 [-0.107,+0.327] P0.82 (+0.009→+0.114) | mid +0.023 [-0.079,+0.135] P0.67 (+0.504→+0.527) | high +0.152 [+0.035,+0.276] P0.99 (+1.335→+1.487)
  log  s42   B2: low +0.215 [-0.181,+0.641] P0.87 (+0.009→+0.223) | mid +0.018 [-0.255,+0.286] P0.54 (+0.504→+0.523) | high -0.733 [-1.276,-0.152] P0.01 (+1.335→+0.602)
  log  s42   B3: low +0.066 [-0.298,+0.437] P0.64 (+0.009→+0.075) | mid -0.087 [-0.332,+0.168] P0.25 (+0.504→+0.417) | high +0.015 [-0.284,+0.305] P0.52 (+1.335→+1.350)
  log  s42   B4: low +0.013 [-0.092,+0.128] P0.59 (+0.009→+0.022) | mid -0.024 [-0.168,+0.119] P0.37 (+0.504→+0.480) | high +0.059 [-0.119,+0.228] P0.74 (+1.335→+1.394)
  log  s42   B5: low +0.212 [-0.188,+0.604] P0.87 (+0.009→+0.221) | mid -0.076 [-0.269,+0.117] P0.23 (+0.504→+0.429) | high +0.194 [-0.047,+0.443] P0.94 (+1.335→+1.529)
  log  s42   B6: low +0.118 [-0.403,+0.629] P0.66 (+0.009→+0.126) | mid +0.197 [-0.119,+0.523] P0.89 (+0.504→+0.701) | high -0.005 [-0.359,+0.317] P0.49 (+1.335→+1.330)
  log  s2027 B1: low +0.123 [-0.082,+0.347] P0.87 (+0.013→+0.136) | mid +0.029 [-0.075,+0.143] P0.70 (+0.546→+0.575) | high +0.140 [+0.009,+0.268] P0.98 (+1.387→+1.527)
  log  s2027 B2: low +0.215 [-0.172,+0.608] P0.85 (+0.013→+0.228) | mid -0.001 [-0.269,+0.260] P0.50 (+0.546→+0.545) | high -0.703 [-1.248,-0.152] P0.01 (+1.387→+0.685)
  log  s2027 B3: low +0.087 [-0.278,+0.454] P0.68 (+0.013→+0.100) | mid -0.106 [-0.337,+0.148] P0.19 (+0.546→+0.440) | high +0.035 [-0.285,+0.367] P0.58 (+1.387→+1.422)
  log  s2027 B4: low -0.052 [-0.155,+0.049] P0.16 (+0.013→-0.039) | mid -0.021 [-0.160,+0.117] P0.38 (+0.546→+0.525) | high +0.134 [-0.033,+0.312] P0.94 (+1.387→+1.521)
  log  s2027 B5: low +0.156 [-0.225,+0.583] P0.78 (+0.013→+0.169) | mid -0.036 [-0.225,+0.158] P0.35 (+0.546→+0.510) | high +0.309 [+0.045,+0.582] P0.99 (+1.387→+1.696)
  log  s2027 B6: low -0.001 [-0.435,+0.414] P0.52 (+0.013→+0.012) | mid +0.214 [-0.103,+0.526] P0.90 (+0.546→+0.760) | high +0.002 [-0.341,+0.360] P0.50 (+1.387→+1.389)

===== DECISION [B1] SEATF10: F10 book gets its own msharpe seat (4-leg leg returns): UNDECIDED  (4-cell mean Δ 2025->26 +0.0471; aux 2024->26 +0.0742; 2024-H2->26 +0.0636)
  prod/s42: Δ -0.0042 CI [-0.0473,+0.0391] P 0.433 Δturn +2.95% DDratio 1.021 | aux 2024->26 Δ +0.0486 CI [-0.0227,+0.1269] | 2024-H2->26 Δ +0.0333 CI [-0.0105,+0.0802]
  prod/s2027: Δ -0.0089 CI [-0.0681,+0.0460] P 0.381 Δturn +5.99% DDratio 0.993 | aux 2024->26 Δ +0.0579 CI [-0.0246,+0.1440] | 2024-H2->26 Δ +0.0339 CI [-0.0201,+0.0883]
  log/s42: Δ +0.1025 CI [+0.0265,+0.1809] P 0.996 Δturn -10.31% DDratio 1.017 | aux 2024->26 Δ +0.0934 CI [+0.0032,+0.1846] | 2024-H2->26 Δ +0.0911 CI [+0.0274,+0.1599]
  log/s2027: Δ +0.0989 CI [+0.0214,+0.1762] P 0.992 Δturn -10.63% DDratio 1.024 | aux 2024->26 Δ +0.0969 CI [+0.0074,+0.1889] | 2024-H2->26 Δ +0.0963 CI [+0.0300,+0.1650]

===== DECISION [B2] SEATNET: seat input = leg return − 4h carry of the leg's unit-gross book: REJECT  (4-cell mean Δ 2025->26 -0.3692; aux 2024->26 -0.1517; 2024-H2->26 -0.2852)
  prod/s42: Δ -0.3751 CI [-0.8020,+0.0185] P 0.029 Δturn +14.08% DDratio 1.153 | aux 2024->26 Δ -0.1429 CI [-0.4211,+0.1517] | 2024-H2->26 Δ -0.2904 CI [-0.5831,+0.0024]
  prod/s2027: Δ -0.3790 CI [-0.7635,-0.0032] P 0.022 Δturn +14.95% DDratio 1.200 | aux 2024->26 Δ -0.1345 CI [-0.3991,+0.1465] | 2024-H2->26 Δ -0.2948 CI [-0.6073,+0.0103]
  log/s42: Δ -0.3643 CI [-0.6951,-0.0369] P 0.015 Δturn +15.27% DDratio 1.013 | aux 2024->26 Δ -0.1667 CI [-0.4021,+0.0820] | 2024-H2->26 Δ -0.2801 CI [-0.5338,-0.0302]
  log/s2027: Δ -0.3583 CI [-0.6887,-0.0438] P 0.012 Δturn +16.08% DDratio 1.010 | aux 2024->26 Δ -0.1627 CI [-0.4159,+0.0677] | 2024-H2->26 Δ -0.2753 CI [-0.5333,-0.0238]

===== DECISION [B3] SEATNET + SEATCOST 2.035 bps × leg rank-book turnover: UNDECIDED  (4-cell mean Δ 2025->26 -0.1261; aux 2024->26 -0.0130; 2024-H2->26 -0.1361)
  prod/s42: Δ -0.1371 CI [-0.3509,+0.0846] P 0.116 Δturn -8.32% DDratio 1.090 | aux 2024->26 Δ -0.0195 CI [-0.2030,+0.1685] | 2024-H2->26 Δ -0.1457 CI [-0.3655,+0.0566]
  prod/s2027: Δ -0.1653 CI [-0.3999,+0.0711] P 0.086 Δturn -9.15% DDratio 1.094 | aux 2024->26 Δ -0.0354 CI [-0.2191,+0.1621] | 2024-H2->26 Δ -0.1691 CI [-0.3815,+0.0393]
  log/s42: Δ -0.1046 CI [-0.3125,+0.1101] P 0.166 Δturn -12.87% DDratio 1.103 | aux 2024->26 Δ -0.0021 CI [-0.1694,+0.1706] | 2024-H2->26 Δ -0.1157 CI [-0.3098,+0.0707]
  log/s2027: Δ -0.0973 CI [-0.3005,+0.1167] P 0.186 Δturn -13.94% DDratio 1.093 | aux 2024->26 Δ +0.0051 CI [-0.1849,+0.1768] | 2024-H2->26 Δ -0.1138 CI [-0.3222,+0.0820]

===== DECISION [B4] PHIDYN: φ_t = shp_F10book/(shp_kingbook+shp_F10book) over prev 900 anchors, clip [0.2,0.8]: 不变差  (4-cell mean Δ 2025->26 +0.0384; aux 2024->26 +0.0322; 2024-H2->26 +0.0298)
  prod/s42: Δ +0.0104 CI [-0.1453,+0.1721] P 0.547 Δturn +17.67% DDratio 1.017 | aux 2024->26 Δ +0.0207 CI [-0.0839,+0.1258] | 2024-H2->26 Δ +0.0131 CI [-0.1157,+0.1363]
  prod/s2027: Δ +0.1001 CI [-0.0597,+0.2603] P 0.897 Δturn +16.41% DDratio 1.002 | aux 2024->26 Δ +0.0717 CI [-0.0320,+0.1841] | 2024-H2->26 Δ +0.0688 CI [-0.0527,+0.1927]
  log/s42: Δ +0.0040 CI [-0.1242,+0.1357] P 0.537 Δturn +15.26% DDratio 0.994 | aux 2024->26 Δ +0.0163 CI [-0.0681,+0.1068] | 2024-H2->26 Δ +0.0112 CI [-0.0957,+0.1142]
  log/s2027: Δ +0.0393 CI [-0.0822,+0.1644] P 0.737 Δturn +14.53% DDratio 0.994 | aux 2024->26 Δ +0.0202 CI [-0.0599,+0.1016] | 2024-H2->26 Δ +0.0262 CI [-0.0718,+0.1249]

===== DECISION [B5] B1 + B4: REJECT  (4-cell mean Δ 2025->26 +0.1005; aux 2024->26 +0.1392; 2024-H2->26 +0.0733)
  prod/s42: Δ +0.0570 CI [-0.0965,+0.2087] P 0.753 Δturn +24.18% DDratio 1.023 | aux 2024->26 Δ +0.1198 CI [-0.0504,+0.2816] | 2024-H2->26 Δ +0.0547 CI [-0.0770,+0.1849]
  prod/s2027: Δ +0.0870 CI [-0.0672,+0.2385] P 0.854 Δturn +28.04% DDratio 0.997 | aux 2024->26 Δ +0.1840 CI [+0.0088,+0.3601] | 2024-H2->26 Δ +0.0664 CI [-0.0766,+0.2100]
  log/s42: Δ +0.0903 CI [-0.0703,+0.2612] P 0.849 Δturn +2.27% DDratio 0.999 | aux 2024->26 Δ +0.1100 CI [-0.0496,+0.2811] | 2024-H2->26 Δ +0.0658 CI [-0.0786,+0.2086]
  log/s2027: Δ +0.1675 CI [+0.0046,+0.3418] P 0.977 Δturn -0.62% DDratio 1.005 | aux 2024->26 Δ +0.1431 CI [-0.0300,+0.3233] | 2024-H2->26 Δ +0.1064 CI [-0.0449,+0.2599]

===== DECISION [B6] B3 + B5 (all switches on): UNDECIDED  (4-cell mean Δ 2025->26 -0.0005; aux 2024->26 +0.0848; 2024-H2->26 -0.0048)
  prod/s42: Δ -0.0011 CI [-0.2525,+0.2432] P 0.490 Δturn +22.37% DDratio 1.074 | aux 2024->26 Δ +0.0840 CI [-0.1482,+0.3303] | 2024-H2->26 Δ -0.0057 CI [-0.2437,+0.2254]
  prod/s2027: Δ -0.1221 CI [-0.3991,+0.1460] P 0.190 Δturn +21.56% DDratio 1.074 | aux 2024->26 Δ +0.0805 CI [-0.1592,+0.3288] | 2024-H2->26 Δ -0.0894 CI [-0.3196,+0.1466]
  log/s42: Δ +0.0617 CI [-0.1927,+0.3135] P 0.686 Δturn +0.71% DDratio 1.070 | aux 2024->26 Δ +0.1032 CI [-0.1373,+0.3374] | 2024-H2->26 Δ +0.0419 CI [-0.2002,+0.2826]
  log/s2027: Δ +0.0597 CI [-0.1852,+0.2971] P 0.682 Δturn +0.09% DDratio 1.083 | aux 2024->26 Δ +0.0717 CI [-0.1325,+0.2820] | 2024-H2->26 Δ +0.0339 CI [-0.1906,+0.2625]

===== BEST PLAN: none (no ADMIT candidate). 不变差 arms (mechanism order, not recommended): ['B4']

wrote /workspace/review_scratch/seat_round2/judge.json and /workspace/review_scratch/seat_round2/REPORT_tables.md
```
