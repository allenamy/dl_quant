"""jpline 积压批次 —— 一次传输一次启动, 顺序跑完全部服务器侧待办。
J1 旧/新 DL 腿同锚对比   (PREREG_oldnew_coincidence 7db1a08b, 主判 M + 反向对照 R + 前置 P1/P2/P3)
J2 funding 口径对账      (C2 影子的阻塞项)
J3 宇宙钉子 MANIFEST     (任务 #57, 只做只读盘点, 不签发)
每段独立 try, 一段挂不拖累其余; 全部落 JSON。
"""
import sys, os, json, glob, time, traceback, hashlib
import numpy as np, pandas as pd
sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset")
PD = "/mnt/storage/private/work_hsy/probe_artifacts"
OUT = f"{PD}/jpline_batch.json"
R = {}


def sha8(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()[:12]


# ══════════════════════ J0 盘点: 到底有哪些预测件 ══════════════════════
try:
    inv = []
    for p in sorted(glob.glob(f"{PD}/*.npz")):
        try:
            z = np.load(p, allow_pickle=True)
            ks = list(z.keys())
            n = {k: (z[k].shape if hasattr(z[k], "shape") else None) for k in ks[:6]}
            inv.append({"f": os.path.basename(p), "mb": round(os.path.getsize(p)/1e6, 1),
                        "mtime": time.strftime("%Y-%m-%d %H:%M", time.gmtime(os.path.getmtime(p))),
                        "keys": ks[:8], "shapes": {k: str(v) for k, v in n.items()},
                        "sha8": sha8(p)})
        except Exception as e:
            inv.append({"f": os.path.basename(p), "err": str(e)[:80]})
    R["J0_inventory"] = inv
    print("═"*80); print("J0 预测件盘点"); print("═"*80)
    for d in inv:
        print(f"  {d.get('f'):46s} {d.get('mb','?'):>7} MB  {d.get('mtime','?')}  sha8={d.get('sha8','?')}  {d.get('keys','')}")
except Exception:
    R["J0_inventory"] = {"err": traceback.format_exc()[-600:]}; print(traceback.format_exc()[-600:])

# ══════════════════════ J1 旧/新同锚对比 ══════════════════════
try:
    import engine.replay_fullhist as RF
    from engine.signal_chain import SignalChain
    from engine.funding_risk import FundingLegRiskControl
    from engine.vol_gate import VolGate
    from engine.netting import LEG_CADENCE_H
    LIVE3 = {"king": 0.5952380952380952, "s2": 0.20238095238095238,
             "funding": 0.20238095238095238, "size": 0.0}
    COSTS = [3.115, 5.80]; RBP = {"alpha": 0.5, "lambda": 1.0}

    def find(pats):
        for p in pats:
            g = sorted(glob.glob(f"{PD}/{p}"))
            if g: return g[0]
        return None
    KN = find(["king_pred_newgen.npz"]); SN = find(["s2_pred_newgen.npz"])
    KO = find(["king_pred_oldgen.npz", "king_pred_old.npz", "king_pred_deployed.npz",
               "king_pred_prev*.npz", "king_pred*dirty*.npz"])
    SO = find(["s2_pred_oldgen.npz", "s2_pred_old.npz", "s2_pred_deployed.npz",
               "s2_pred_prev*.npz", "s2_pred*dirty*.npz"])
    print("\n" + "═"*80); print("J1 旧/新 DL 腿同锚对比"); print("═"*80)
    print(f"  new: king={os.path.basename(KN) if KN else None}  s2={os.path.basename(SN) if SN else None}")
    print(f"  old: king={os.path.basename(KO) if KO else None}  s2={os.path.basename(SO) if SO else None}")
    if not (KO and SO):
        R["J1"] = {"status": "SKIP_no_oldgen", "note": "probe_artifacts 内未找到 old-gen 预测件; 见 J0 盘点自行指认"}
        print("  ⇒ 未找到 old-gen 预测件 ⇒ J1 跳过(P1 无法检验)。J0 盘点已列全部候选。")
    else:
        def build(kp, sp, tag):
            src = RF.get_src(None, kp, sp)
            a, yr = RF._all_anchors(src)
            dref = FundingLegRiskControl.calibrate_dispersion(src, a)
            frc = FundingLegRiskControl(winsor_z=4.0, name_cap=0.15, disp_gate_z=4.0,
                                        disp_shrink=0.3, disp_ref=dref)
            ch = SignalChain(src, weights=LIVE3, funding_mode="rank", vol_gate=VolGate(src),
                             funding_risk=frc, pos_cap_pct=99.0)
            ch.calibrator = None
            RVI = src.ch.index("rvol_24h"); cad = dict(LEG_CADENCE_H)
            LK = ["king", "s2", "funding"]; held = {k: np.zeros(src.N) for k in LK}
            H = np.zeros((len(a), 3, src.N)); M, RET, RV = [], [], []
            for i, t in enumerate(a):
                ti = int(t); lp, m = ch.leg_positions(ti)
                for j, k in enumerate(LK):
                    if i == 0 or (ti % cad[k] == 0):
                        nw = np.zeros(src.N); nw[m] = lp[k]; held[k] = nw
                    H[i, j] = held[k]
                M.append(m); RET.append(src.Y4[ti, m])
                RV.append(src.CH[ti, m, RVI].astype(np.float64))
            print(f"  [{tag}] anchors={len(a)} N={src.N}")
            return dict(src=src, a=a, yr=yr, H=H, M=M, RET=RET, RV=RV, ch=ch)

        def rb(s_, rvol):
            al, lm = RBP["alpha"], RBP["lambda"]
            v = np.asarray(rvol, float); fin = np.isfinite(v) & (v > 0)
            if not fin.any(): return s_
            med = float(np.median(v[fin]))
            if med <= 0: return s_
            v = np.where(fin, v, med)
            w = np.sign(s_)*np.abs(s_)**al/np.power(v/med, lm)
            return w - w.mean()

        def econ(B):
            wv = np.array([LIVE3[k] for k in ["king", "s2", "funding"]])
            n = len(B["a"]); prev = np.zeros(B["src"].N)
            pnl = np.zeros(n); trn = np.zeros(n); ric = np.full(n, np.nan)
            for i in range(n):
                m = B["M"][i]
                sh = rb(B["ch"].shape_position((wv @ B["H"][i])[m]), B["RV"][i])
                g = float(np.abs(sh).sum())
                if g > 1e-12: sh = sh/g
                net = np.zeros(B["src"].N); net[m] = sh
                r = B["RET"][i]; ok = np.isfinite(r)
                pnl[i] = float(np.nansum(sh[ok]*r[ok]))
                trn[i] = 0.0 if i == 0 else float(np.abs(net-prev).sum())
                if ok.sum() >= 5:
                    ric[i] = float(np.corrcoef(pd.Series(sh[ok]).rank(),
                                               pd.Series(r[ok]).rank())[0, 1])
                prev = net
            return pnl, trn, ric

        BN = build(KN, SN, "new"); BO = build(KO, SO, "old")
        # ── P2 同锚断言
        same = (len(BN["a"]) == len(BO["a"])) and bool(np.array_equal(np.asarray(BN["a"]), np.asarray(BO["a"])))
        print(f"  P2 同锚: {same}  (new {len(BN['a'])} vs old {len(BO['a'])})")
        if not same:
            ca = np.intersect1d(np.asarray(BN["a"]), np.asarray(BO["a"]))
            print(f"     ⇒ 取交集 {len(ca)} 锚")
        pN, tN, rN = econ(BN); pO, tO, rO = econ(BO)
        if not same:
            iN = {int(v): k for k, v in enumerate(BN["a"])}; iO = {int(v): k for k, v in enumerate(BO["a"])}
            ca = sorted(set(iN) & set(iO))
            jN = [iN[x] for x in ca]; jO = [iO[x] for x in ca]
            pN, tN, rN = pN[jN], tN[jN], rN[jN]; pO, tO, rO = pO[jO], tO[jO], rO[jO]
            yrv = np.asarray(BN["yr"])[jN]
        else:
            yrv = np.asarray(BN["yr"])

        def boot(d, nb=3000, bl=5):
            rng = np.random.default_rng(99); n = len(d); k = int(np.ceil(n/bl)); o = np.empty(nb)
            for q in range(nb):
                st = rng.integers(0, max(n-bl, 1), size=k)
                ix = (st[:, None]+np.arange(bl)[None, :]).ravel()[:n]; ix = ix[ix < n]
                o[q] = d[ix].mean()*1e4
            return float(np.percentile(o, 2.5)), float(np.percentile(o, 97.5))

        def row(nm, p, t, r):
            g = p.mean()*1e4; tn = t.sum()/len(t)
            print(f"  {nm:10s} 毛{g:+8.3f}  IC{np.nanmean(r):+8.5f}  换手{tn:7.4f}  " +
                  "  ".join(f"净@{c}{g-tn*2*c:+8.3f}" for c in COSTS))
            return {"gross": round(float(g), 4), "ic": round(float(np.nanmean(r)), 5),
                    "turn": round(float(tn), 4),
                    **{f"net@{c}": round(float(g-tn*2*c), 4) for c in COSTS}}
        print(f"\n  ── 全期 {len(pN)} 锚 ──")
        rr = {"new": row("new(在役)", pN, tN, rN), "old": row("old(脏世代)", pO, tO, rO)}
        d = pO - pN; lo, hi = boot(d)
        print(f"\n  M · Δ毛(old−new) = {d.mean()*1e4:+.3f} bps   日块CI95[{lo:+.3f},{hi:+.3f}]")
        verdict = "M2_old更好" if lo > 0 else ("M3_new更好" if hi < 0 else "M1_覆盖0_E3被拒")
        print(f"  ⇒ 裁定 {verdict}")
        # 反向对照 R
        d2 = pN - pO; lo2, hi2 = boot(d2)
        okR = abs(d2.mean()+d.mean()) < 1e-12 and abs(lo2+hi) < 1e-6
        print(f"  R 反向对照: Δ(new−old)={d2.mean()*1e4:+.3f} CI[{lo2:+.3f},{hi2:+.3f}] ⇒ 对称 {okR}")
        dfy = pd.DataFrame({"y": yrv, "d": d*1e4}).groupby("y").d.mean()
        print(f"  逐年 Δ毛(old−new): {dict(dfy.round(3))}")
        sgn = set(np.sign(dfy.values[np.abs(dfy.values) > 1e-9]))
        print(f"  ⇒ 逐年符号{'一致' if len(sgn) <= 1 else '【翻转 ⇒ regime 特异, 不可外推】'}")
        # 近窗(最后 180 锚 ≈ 30 天)
        k = min(180, len(pN))
        dk = (pO-pN)[-k:]; lok, hik = boot(dk)
        print(f"  近窗{k}锚: Δ毛 {dk.mean()*1e4:+.3f}  CI[{lok:+.3f},{hik:+.3f}]")
        rr.update({"delta_gross": round(float(d.mean()*1e4), 4), "ci": [round(lo, 4), round(hi, 4)],
                   "verdict": verdict, "reverse_symmetric": bool(okR),
                   "per_year": {int(a_): round(float(b_), 4) for a_, b_ in dfy.items()},
                   "recent": {"k": int(k), "delta": round(float(dk.mean()*1e4), 4),
                              "ci": [round(lok, 4), round(hik, 4)]},
                   "P2_same_anchors": bool(same), "n_common": int(len(pN)),
                   "files": {"king_new": os.path.basename(KN), "s2_new": os.path.basename(SN),
                             "king_old": os.path.basename(KO), "s2_old": os.path.basename(SO)}})
        R["J1"] = rr
except Exception:
    R["J1"] = {"err": traceback.format_exc()[-1200:]}; print(traceback.format_exc()[-1200:])

# ══════════════════════ J2 funding 口径对账 ══════════════════════
try:
    import engine.replay_fullhist as RF2
    print("\n" + "═"*80); print("J2 funding 口径对账 (C2 影子阻塞项)"); print("═"*80)
    s = RF2.get_src(None, f"{PD}/king_pred_newgen.npz", f"{PD}/s2_pred_newgen.npz")
    fi = s.fund_idx; a, _ = RF2._all_anchors(s); last = int(a[-1])
    m = s.tradeable(last); v = s.CH[last, m, fi].astype(np.float64); v = v[np.isfinite(v)]
    av = s.CH[a, :, fi].astype(np.float64); av = av[np.isfinite(av)]
    q = np.percentile(v, [1, 25, 50, 75, 99]).tolist()
    print(f"  [离线宽面板 末锚 n={len(v)}] ch='{s.ch[fi]}'")
    print(f"    分位[1,25,50,75,99] = {[f'{x:+.4e}' for x in q]}")
    print(f"    均值 {v.mean():+.4e}  sd {v.std():.4e}  |中位| {np.median(np.abs(v)):.4e}")
    print(f"  [离线全期 n={len(av):,}]  |中位| {np.median(np.abs(av)):.4e}  "
          f"分位[1,50,99]={[f'{x:+.4e}' for x in np.percentile(av,[1,50,99])]}")
    print(f"  [实盘 preds_latest 2026-08-09] |中位| 8.576e-05  均值 +4.725e-05  sd 1.075e-04")
    ratio = float(np.median(np.abs(v))/8.576e-05)
    print(f"  ⇒ |中位|比值 离线/实盘 = {ratio:.3f}   "
          f"{'同口径(比值在 0.5~2)' if 0.5 <= ratio <= 2 else '★不同口径 —— C2 影子正交化减掉的不是在役 funding'}")
    R["J2"] = {"ch": s.ch[fi], "offline_absmed_last": float(np.median(np.abs(v))),
               "offline_absmed_all": float(np.median(np.abs(av))),
               "live_absmed": 8.576e-05, "ratio": round(ratio, 4),
               "same_caliber": bool(0.5 <= ratio <= 2),
               "q_last": [float(x) for x in q]}
except Exception:
    R["J2"] = {"err": traceback.format_exc()[-800:]}; print(traceback.format_exc()[-800:])

# ══════════════════════ J3 宇宙钉子盘点(#57, 只读) ══════════════════════
try:
    print("\n" + "═"*80); print("J3 宇宙钉子 MANIFEST 盘点 (#57, 只读不签发)"); print("═"*80)
    hits = []
    for pat in ["/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/**/MANIFEST*",
                "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/**/*universe*.json",
                f"{PD}/MANIFEST*"]:
        hits += glob.glob(pat, recursive=True)
    for h in sorted(set(hits))[:25]:
        print(f"  {time.strftime('%Y-%m-%d %H:%M', time.gmtime(os.path.getmtime(h)))}  "
              f"{os.path.getsize(h):>9,}  {h}")
    R["J3"] = {"n": len(set(hits)), "files": sorted(set(hits))[:25]}
except Exception:
    R["J3"] = {"err": traceback.format_exc()[-500:]}; print(traceback.format_exc()[-500:])

json.dump(R, open(OUT, "w"), indent=1, default=str)
print(f"\n[done] -> {OUT}\nJPLINE_BATCH_DONE")
