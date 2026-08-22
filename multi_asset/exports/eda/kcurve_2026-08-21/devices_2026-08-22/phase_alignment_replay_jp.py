"""PH · 相位对齐审计 — 服务器侧装置 @jpline(2026-08-22, Session 6737834a-PH)。

问题(W2b 口径发现 (a)): 在役离线回放族(9821 锚)的预测只存在于行标 00/04/08/12/16/20Z 的行, 而行标 T 的 Y4[T] =
log CLOSE[T+4] − log CLOSE[T] = 价格 T+1h→T+5h ⇒ 离线族的决策时刻 = 行标+1h = 01/05/09/13/17/21Z; 实盘名义锚 N 用行标 N−1h
(preds.anchor_ts_ms = 最后一根完整小时 bar 开盘时刻), 持仓窗 ≈ [N, N+4h] ⇒ 离线族与实盘差 1h 相位。
本装置把 king/s2 五折 OOS 推理搬到【实盘相位的行】(行标 hour%4==3, 特征截至 N, Y4 = [N, N+4h]), 然后把在役书
(w2_live_replay.py / cond_stop_tail.py 逐字同构: 实盘 legs.compose_book + apply_harvest_ema α0.05 + 带 b0.002 + 止损 S1 + 成本 4.137)
在两个相位上各回放一遍, 报相位修正前后的净额/夏普/逐年/换手/书 IC 与 Δ 的日块自助 CI。

【判据冻结, 先于看数】
  G1 推理保真门: 逐折用训练侧 predict_scores_wide 在【原生行】复现 run 目录里冻结的 fold_k_head_scores (te_rows 上 max|Δ|),
     GPU 阈值 1e-4(记忆 vs_infer: 正确重建 GPU 1.2e-7 / CPU 3.5e-4; 错权重对照 6.5e-1); 任一折不过 ⇒ 该腿推理作废, 全文标"传闻"。
  G2 回放复现收据: 用 newgen 预测在相位 0 回放, net_S0/net_S1 必须与 probe_artifacts/net_S{0,1}.npy 逐元素 maxabs < 1e-9。
  G3 "我的推理/相位 0" 对照: 用本装置推理(相位 0 行)回放, 与 newgen 回放的净额差 |Δ均值| 应 < 0.05 bps/锚(推理复现层面同构);
     超出则报告并以"本装置相位 0"为唯一对照(苹果对苹果), 不与 newgen 混比。
  读法(三选一, 以 S1 净夏普为主读, 2022-01→2026-06 全史):
     (i) |Δ夏普(相位3−相位0_mine)| 的日块自助 95% CI 含 0 且 |Δ净| < 0.10 bps/锚 ⇒ "相位效应不可分辨, 离线族数字可沿用(标注相位)";
     (ii) CI 排除 0 ⇒ "离线族需相位修正", 给出相位 3 的全部数字与受影响数字清单;
     (iii) G1/G2 任一不过 ⇒ "传闻"。
  附读: 逐年 Δ 同号数; 书 rank-IC(持仓 vs Y4)两相位; king 单腿/funding 单腿的 IC 两相位(解释机制: funding 通道陈旧 vs 价格窗口)。
输入(只读): exports/wide_dl_full_corrfund_causal_v1.npz(训练面板, panel_ref.funding 位相等已核), exports/train/{wideA_lamorth0_xattn_5yr_corrfund_v1,
  wideA_s2_y24_5yr_corrfund_emb10}/fold_*_{model.pt,head_scores.npz}, probe_artifacts/{king,s2}_pred_newgen.npz, probe_artifacts/legs.py(实盘副本, 与 W2 同一份),
  engine.panel_source 默认面板(仅取 Y4/CH rvol/funding — 分数级回放, 与 W2 同), probe_artifacts/net_S{0,1}.npy, w2_wide_series.npz(ρ)。
输出: probe_artifacts/ph_preds_2026-08-22.npz, probe_artifacts/ph_series_2026-08-22.npz, probe_artifacts/phase_alignment_jp_2026-08-22.json。
不碰 share 数据 / 实盘仓; 不写训练目录。
用法: python phase_alignment_replay_jp.py [--skip_infer](复用已存 preds) [--folds_only K]
"""
import os, sys, json, time, glob, hashlib, argparse
import numpy as np, pandas as pd

PD = "/mnt/storage/private/work_hsy/probe_artifacts"
REPO = "/mnt/storage/private/work_hsy/quant_research_multi_asset"
MA = REPO + "/multi_asset"
for p_ in (PD, MA, MA + "/engine/live", REPO, PD):
    sys.path.insert(0, p_)
PANEL_TRAIN = MA + "/exports/wide_dl_full_corrfund_causal_v1.npz"
RUNS = {"king": (MA + "/exports/train/wideA_lamorth0_xattn_5yr_corrfund_v1", 4, 8),
        "s2": (MA + "/exports/train/wideA_s2_y24_5yr_corrfund_emb10", 24, 10)}   # (dir, H, embargo_days)
NEWGEN = {"king": (f"{PD}/king_pred_newgen.npz", "king_pred"), "s2": (f"{PD}/s2_pred_newgen.npz", "s2_pred")}
OUT_PREDS = f"{PD}/ph_preds_2026-08-22.npz"; OUT_SER = f"{PD}/ph_series_2026-08-22.npz"; OUT_JSON = f"{PD}/phase_alignment_jp_2026-08-22.json"
W_LIVE = {"king": .5952380952380952, "s2": .20238095238095238, "funding": .20238095238095238, "size": 0.}
RB = {"alpha": .5, "lambda": 1.}; C1 = 4.137; BW = 0.002; COOL = 42; ALPHA = 0.05; ANN = np.sqrt(6 * 365)
G1_TOL = 1e-4
t0 = time.time()


def log(*a):
    print(f"[{time.time()-t0:7.1f}s]", *a, flush=True)


def sha(p):
    h = hashlib.sha256(); h.update(open(p, "rb").read()); return h.hexdigest()


def comp_panel(scores, mem, CLm, YR):
    """king_pred_panel.comp_panel 逐字: 逐行对 base=(mem&CL&finite YR) 的 6 头各自 z 化后取均值。"""
    Tt, Nn, Kk = scores.shape; Cc = np.full((Tt, Nn), np.nan, np.float32)
    for t in np.where((mem & CLm & np.isfinite(YR)).any(1))[0]:
        base = np.where(mem[t] & CLm[t] & np.isfinite(YR[t]))[0]
        if base.size < 5:
            continue
        comp = np.zeros(base.size); nk = 0
        for k in range(Kk):
            col = scores[t, base, k]
            if np.isfinite(col).all() and col.std() > 1e-12:
                comp += (col - col.mean()) / col.std(); nk += 1
        if nk:
            Cc[t, base] = (comp / nk).astype(np.float32)
    return Cc


# ====================================================================== 1. inference
def run_inference(args):
    import torch
    from multi_asset.data.wide_panel_dataset import WidePanelData
    from multi_asset.model.wide_harness import WideFactorModel, ConformerPanelEncoder
    DEV = "cuda"
    try:
        import multi_asset.train.train_wide_harness as TH
        th_src = "import"
    except ImportError as e:          # server harness imports an encoder class absent from the server's model file (version skew)
        # VERBATIM copies of train_wide_harness.predict_scores_wide (L137-147) and year_folds (L96-115); the G1 gate below is the
        # equality assertion that makes a second copy legitimate (memory duplication_with_equality_assertion / vs_infer).
        import types
        TH = types.SimpleNamespace()
        def predict_scores_wide(model, data, split_days, batch_hours, K):
            model.eval()
            out = np.full((data.T, data.N, K), np.nan, np.float32)
            with torch.no_grad():
                for b in data.iter_batches(split_days, batch_hours=batch_hours, rng=None, shuffle=False):
                    x = torch.from_numpy(b["Xseq"]).to(DEV)
                    m = torch.from_numpy(b["mask"]).to(DEV)
                    sc = model(x, m)["factor_scores"].detach().cpu().numpy()   # (B,N,K)
                    mm = b["mask"] > 0.5
                    out[b["rows"]] = np.where(mm[:, :, None], sc, np.nan)
            return out
        def year_folds(data, embargo_days=8, val_days=30, min_train_days=120, min_test_days=60, year_from=None):
            yr_of_hour = pd.to_datetime(data.ts, unit="ms", utc=True).year.to_numpy()
            day_year = np.array([int(yr_of_hour[data.day == d][0]) for d in data.uniq_days])
            folds = []
            for Y in sorted(set(day_year.tolist())):
                if year_from is not None and Y < year_from:
                    continue
                te = data.uniq_days[day_year == Y]
                tr_all = data.uniq_days[day_year < Y]
                if len(te) < min_test_days or len(tr_all) < min_train_days + val_days + embargo_days:
                    continue
                tr_all = tr_all[:-embargo_days]
                tr, va = tr_all[:-val_days], tr_all[-val_days:]
                folds.append(dict(tr=tr, va=va, te=te, year=Y))
            return folds
        TH.predict_scores_wide = predict_scores_wide; TH.year_folds = year_folds
        th_src = f"verbatim-copy (harness import failed: {e})"
    log("predict/year_folds source:", th_src)
    assert torch.cuda.is_available(), "GPU required: G1 threshold is calibrated for GPU float32 (memory vs_infer)"
    res = {"panel_train": PANEL_TRAIN, "panel_train_sha256": None, "legs": {}, "predict_source": th_src}
    log("sha256 of training panel (1 GB) ...")
    res["panel_train_sha256"] = sha(PANEL_TRAIN)
    out_preds = {}
    for leg, (rdir, H, emb) in RUNS.items():
        log(f"== leg {leg}: H={H} run={os.path.basename(rdir)} embargo={emb}")
        data = WidePanelData(path=PANEL_TRAIN, target_horizon=H, aux_horizons=(1, 24))
        ts = data.ts.astype(np.int64); T, N = data.T, data.N
        hrs = pd.to_datetime(ts, unit="ms", utc=True).hour.values
        if leg == "king":
            out_preds["ts"] = ts
        member = data.member; YR = data.Y; CL_native = data.CL.copy(); vh_native = data.valid_hour.copy()
        folds = TH.year_folds(data, embargo_days=emb, val_days=30, year_from=2022)
        model = WideFactorModel(ConformerPanelEncoder(data.C, d=64, n_blocks=2, kernel_size=15, dropout=0.2),
                                n_factor_heads=6, xattn=True, n_xattn=1, dropout=0.2).to(DEV)
        P0 = np.full((T, N), np.nan, np.float32); P3 = np.full((T, N), np.nan, np.float32)
        legres = {"folds": [], "gate_G1_pass": True, "xattn_state_keys": None}
        fl = sorted(glob.glob(rdir + "/fold_*_head_scores.npz"), key=lambda x: int(x.split("fold_")[1].split("_")[0]))
        for f in fl:
            k = int(f.split("fold_")[1].split("_")[0])
            if args.folds_only is not None and k >= args.folds_only:
                break
            z = np.load(f); te_rows = z["te_rows"]; te_days = z["te_days"]; ref_sc = z["scores"]
            fold = folds[k]
            assert np.array_equal(np.asarray(fold["te"]), te_days), f"fold {k}: te_days mismatch vs year_folds(embargo={emb})"
            sd_ = torch.load(rdir + f"/fold_{k}_model.pt", map_location=DEV)
            if legres["xattn_state_keys"] is None:
                legres["xattn_state_keys"] = sorted({kk.split(".")[0] for kk in sd_.keys()})
            missing, unexpected = model.load_state_dict(sd_, strict=False)
            assert not missing and not unexpected, f"state_dict mismatch fold {k}: {missing} {unexpected}"
            model.eval()
            # ---- G1: native rows reproduce the frozen head scores. Norm stats from the fold's TRAIN days with the
            #      NATIVE CL (before any mask mutation — memory vs_infer hypothesis 2). Embargo decides `tr` => mu/sd;
            #      try the run's declared embargo first, fall back to the other candidate, record both. ----
            g1_tries = {}
            for emb_try in ([emb] + [e for e in (8, 10) if e != emb]):
                fold_t = TH.year_folds(data, embargo_days=emb_try, val_days=30, year_from=2022)[k]
                data.CL = CL_native; data.valid_hour = vh_native
                data.set_fold(fold_t["tr"])
                sc_nat = TH.predict_scores_wide(model, data, te_days, 32, 6)
                d_nat = sc_nat[te_rows] - ref_sc[te_rows]
                fin = np.isfinite(ref_sc[te_rows])
                g1 = float(np.nanmax(np.abs(np.where(fin, d_nat, 0.0)))) if fin.any() else np.nan
                same_nan = bool(np.array_equal(np.isfinite(sc_nat[te_rows]), fin))
                g1_tries[emb_try] = {"maxabs": g1, "same_nan": same_nan}
                if np.isfinite(g1) and g1 <= G1_TOL and same_nan:
                    break
            g1_pass = bool(np.isfinite(g1) and g1 <= G1_TOL and same_nan)
            legres["gate_G1_pass"] &= g1_pass
            legres.setdefault("embargo_used", {})[str(k)] = emb_try
            del sc_nat
            # ---- dense inference on phase-0 (hour%4==0) and phase-3 (hour%4==3) rows, mask = member & finite YR (densify recipe) ----
            fr = {}
            for ph, hsel in (("p0", 0), ("p3", 3)):
                data.CL = member.copy()
                vh = np.zeros(T, bool); ok = np.arange(T) >= (data.W - 1)
                vh[ok] = (hrs[ok] % 4 == hsel) & (member[ok] & np.isfinite(YR[ok])).any(1)
                data.valid_hour = vh
                sc = TH.predict_scores_wide(model, data, te_days, 32, 6)
                CLm = np.zeros((T, N), bool); CLm[hrs % 4 == hsel] = True
                Cc = comp_panel(sc, member, CLm, YR)
                rows_f = np.where(np.isfinite(Cc).any(1))[0]
                fr[ph] = {"rows": int(len(rows_f)), "first": str(pd.to_datetime(ts[rows_f[0]], unit="ms", utc=True)) if len(rows_f) else None,
                          "last": str(pd.to_datetime(ts[rows_f[-1]], unit="ms", utc=True)) if len(rows_f) else None}
                tgt = P0 if ph == "p0" else P3
                m = np.isfinite(Cc)
                fr[ph]["overlap_prev_fold_cells"] = int((m & np.isfinite(tgt)).sum())
                tgt[m] = Cc[m]
            legres["folds"].append({"fold": k, "te_year": int(fold.get("year", -1)), "n_te_rows_native": int(len(te_rows)),
                                    "G1_maxabs_native": g1, "G1_same_nan_pattern": same_nan, "G1_pass": g1_pass,
                                    "G1_tries_by_embargo": g1_tries, "embargo_used": emb_try, **fr})
            log(f"  fold {k} te={fold.get('year')}: G1 max|d|={g1:.3e} pass={g1_pass} | p0 rows {fr['p0']['rows']} | p3 rows {fr['p3']['rows']}")
        # compare phase-0 dense composite with newgen (informational; for king they should be near-identical)
        ng = np.load(NEWGEN[leg][0], allow_pickle=True)[NEWGEN[leg][1]].astype(np.float32)
        both = np.isfinite(ng) & np.isfinite(P0)
        legres["vs_newgen_p0"] = {"cells_both": int(both.sum()), "cells_newgen_only": int((np.isfinite(ng) & ~np.isfinite(P0)).sum()),
                                  "cells_mine_only": int((~np.isfinite(ng) & np.isfinite(P0)).sum()),
                                  "maxabs": float(np.max(np.abs(ng[both] - P0[both]))) if both.any() else None,
                                  "corr": float(np.corrcoef(ng[both], P0[both])[0, 1]) if both.sum() > 10 else None}
        log(f"  {leg} vs newgen (phase 0): {legres['vs_newgen_p0']}")
        out_preds[f"{leg}_p0"] = P0; out_preds[f"{leg}_p3"] = P3
        res["legs"][leg] = legres
        del data
    np.savez_compressed(OUT_PREDS, **out_preds)
    log("saved", OUT_PREDS)
    return res


# ====================================================================== 2. replay (w2_live_replay.py 逐字同构, 相位参数化)
def build_src():
    from engine.panel_source import PanelSource
    src = PanelSource(king=NEWGEN["king"][0], s2=NEWGEN["s2"][0])    # default dirty panel: Y4 / CH(rvol, funding) only — score-level
    return src


def replay(src, K, S, phase_row_hour, tag, want_W=False, anchors_ref=None):
    """K,S: (T,N) preds. phase_row_hour: 0 (离线族: 行 00/04/.. 决策 T+1h) or 3 (实盘相位: 行 23/03/.. 决策 N=T+1h=00/04/..).
    refresh: king/funding 每 2 锚(名义 00/08/16Z), s2 每 6 锚(名义 00Z) — 与 w2_live_replay 的 ti%8==0 / ti%24==0 在相位 0 逐字相同."""
    import legs as LG
    src.king = K.astype(np.float64); src.s2 = S.astype(np.float64)
    N = src.N; ts_all = np.asarray(src.ts).astype(np.int64)
    hrs = pd.to_datetime(ts_all, unit="ms", utc=True).hour.values
    nominal = ts_all // 1000 + 3600                     # decision time = row + 1h
    lo = int(pd.Timestamp("2022-01-01", tz="UTC").timestamp()); hi = int(pd.Timestamp("2026-07-01", tz="UTC").timestamp())
    trad_any = (src.member & np.isfinite(src.king) & np.isfinite(src.s2)).any(1)
    a = np.where((hrs % 4 == phase_row_hour) & trad_any & (nominal >= lo) & (nominal < hi))[0]
    if anchors_ref is not None:
        a = np.asarray(anchors_ref)
    n = len(a); ats = nominal[a]; yr = pd.to_datetime(ats, unit="s", utc=True).year.to_numpy()
    FI, RVI = src.fund_idx, src.ch.index("rvol_24h"); SYMS = [str(s) for s in src.symbols]
    off = (3 - phase_row_hour) % 4      # row index offset so that (ti+off) % 8 == 0 <=> nominal hour % 8 == 0 ... see below
    # grid starts 2021-01-01 00:00 => row index ti has hour ti%24. phase 0: refresh when ti%8==0 (rows 0/8/16) [W2 逐字];
    # phase 3: rows 23/7/15 <=> (ti+1)%8==0. Generic: (ti + (1 if phase_row_hour==3 else 0)) % 8 == 0.
    shift = 1 if phase_row_hour == 3 else 0
    TGT, MSK, RET = [], [], []; TGTL = {"king": [], "s2": [], "funding": []}
    LEGW = {"king": {"king": 1., "s2": 0., "funding": 0., "size": 0.}, "s2": {"king": 0., "s2": 1., "funding": 0., "size": 0.},
            "funding": {"king": 0., "s2": 0., "funding": 1., "size": 0.}}
    held = {"k": np.full(N, np.nan), "s": np.full(N, np.nan), "f": np.full(N, np.nan)}
    ic_book_leg = {k: np.full(n, np.nan) for k in ("king", "s2", "funding")}
    from scipy.stats import rankdata
    for i, t in enumerate(a):
        ti = int(t); m = np.asarray(src.tradeable(ti))
        if m.dtype == bool: m = np.where(m)[0]
        if i == 0 or (ti + shift) % 8 == 0:
            v = np.full(N, np.nan); v[m] = src.king[ti, m]; held["k"] = v
        if i == 0 or (ti + shift) % 24 == 0:
            v = np.full(N, np.nan); v[m] = src.s2[ti, m]; held["s"] = v
        if i == 0 or (ti + shift) % 8 == 0:
            v = np.full(N, np.nan); v[m] = src.CH[ti, m, FI]; held["f"] = v
        rv = src.CH[ti, m, RVI].astype(float)
        r = LG.compose_book(held["k"][m], held["s"][m], held["f"][m], np.ones(len(m)), weights=W_LIVE, rvol=rv, risk_budget=RB)
        w = np.full(N, 0.0); w[m] = np.asarray(r["target_w"], float)
        y = src.Y4[ti, m].astype(float)
        TGT.append(w); MSK.append(m); RET.append(y)
        for k, wl in LEGW.items():
            rl = LG.compose_book(held["k"][m], held["s"][m], held["f"][m], np.ones(len(m)), weights=wl, rvol=rv, risk_budget=RB)
            wv = np.full(N, 0.0); wv[m] = np.asarray(rl["target_w"], float); TGTL[k].append(wv)
            ok = np.isfinite(y) & (np.abs(wv[m]) > 1e-12)
            if ok.sum() >= 10:
                ic_book_leg[k][i] = np.corrcoef(rankdata(wv[m][ok]), rankdata(y[ok]))[0, 1]
        if i % 2000 == 0: log(f"  [{tag}] precompute {i}/{n}")

    def run(TGTx, stop):
        state = None; prev = np.zeros(N); Pi = np.ones(N); sh = np.zeros(N); cb = np.zeros(N)
        cnt = np.zeros(N, int); su = np.full(N, -1)
        pnl = np.zeros(n); trn = np.zeros(n); gross = np.zeros(n); fires = np.zeros(n, int); ic = np.full(n, np.nan)
        WS = np.zeros((n, N), np.float32) if want_W else None
        for i in range(n):
            m = MSK[i]; syms = [SYMS[j] for j in m]
            out = LG.apply_harvest_ema(TGTx[i][m], syms, state, ALPHA); state = out["state"]
            tgt = np.asarray(out["target_w"], float)
            if stop:
                bs = set(np.where(su > i)[0].tolist())
                if bs:
                    for k2, j in enumerate(m):
                        if j in bs: tgt[k2] = 0.0
            w = prev.copy(); w[[j for j in range(N) if j not in set(m)]] = 0.0
            d = tgt - w[m]; Tm = np.abs(d) > BW
            wm = w[m].copy(); wm[Tm] = tgt[Tm]
            if Tm.any(): wm[Tm] -= wm.sum() / Tm.sum()
            w[m] = wm
            y = RET[i]; ok = np.isfinite(y); idx = m[ok]
            c = np.zeros(N); c[idx] = w[m][ok] * y[ok] * 1e4
            pnl[i] = c.sum(); trn[i] = float(np.abs(w - prev).sum()); gross[i] = float(np.abs(w).sum())
            hv = ok & (np.abs(w[m]) > 1e-12)
            if hv.sum() >= 10:
                ic[i] = np.corrcoef(rankdata(w[m][hv]), rankdata(y[hv]))[0, 1]
            if want_W: WS[i] = w.astype(np.float32)
            nsh = np.where(Pi > 1e-12, w / Pi, 0.0)
            same = np.sign(nsh) == np.sign(sh); add = same & (np.abs(nsh) > np.abs(sh))
            red = same & (~add) & (np.abs(nsh) > 1e-12); new = (~same) | (np.abs(sh) < 1e-12)
            cb = np.where(add, cb + (nsh - sh) * Pi, cb)
            with np.errstate(all='ignore'):
                ratio = np.where(np.abs(sh) > 1e-12, nsh / np.where(np.abs(sh) > 1e-12, sh, 1.0), 0.0)
            cb = np.where(red, cb * ratio, cb); cb = np.where(new, nsh * Pi, cb); cb = np.where(np.abs(nsh) < 1e-12, 0.0, cb)
            sh = nsh
            with np.errstate(all='ignore'):
                avg = np.where(np.abs(sh) > 1e-12, cb / sh, np.nan)
                dep = np.where(np.isfinite(avg) & (Pi > 0), np.sign(sh) * (1.0 - avg / Pi), 0.0)
            if stop:
                thr = np.full(N, -0.25)
                cand = (np.abs(sh) > 1e-12) & (dep <= thr) & (su <= i)
                cnt = np.where(cand, cnt + 1, 0)
                fire = cnt >= 2
                if fire.any(): su[fire] = i + COOL; cnt[fire] = 0; fires[i] = int(fire.sum())
            prev = w; upd = np.zeros(N); upd[idx] = y[ok]; Pi = Pi * (1.0 + upd)
        net = pnl - trn * C1
        return dict(net=net, pnl=pnl, trn=trn, gross=gross, fires=fires, ic=ic, W=WS)
    R = {"S0": run(TGT, False), "S1": run(TGT, True)}
    for k in LEGW:
        R["leg_" + k] = run(TGTL[k], False)
    R["meta"] = {"n": int(n), "ats": ats, "yr": yr, "rows": a, "ic_book_leg": ic_book_leg,
                 "first_nominal": str(pd.to_datetime(ats[0], unit="s", utc=True)), "last_nominal": str(pd.to_datetime(ats[-1], unit="s", utc=True))}
    log(f"  [{tag}] done n={n} S1 mean={R['S1']['net'].mean():.4f} sharpe={R['S1']['net'].mean()/R['S1']['net'].std(ddof=1)*ANN:.3f}")
    return R


def summ(x, yr):
    x = np.asarray(x, float)
    return {"mean_bps": round(float(np.nanmean(x)), 4), "sd": round(float(np.nanstd(x, ddof=1)), 3),
            "sharpe": round(float(np.nanmean(x) / np.nanstd(x, ddof=1) * ANN), 3),
            "by_year_mean": {int(y): round(float(np.nanmean(x[yr == y])), 3) for y in sorted(set(yr.tolist()))},
            "by_year_sharpe": {int(y): round(float(np.nanmean(x[yr == y]) / np.nanstd(x[yr == y], ddof=1) * ANN), 3) for y in sorted(set(yr.tolist()))}}


def daily(x, ats):
    d = (np.asarray(ats) // 86400).astype(np.int64)
    u, inv = np.unique(d, return_inverse=True)
    s = np.zeros(len(u)); np.add.at(s, inv, np.nan_to_num(x)); return u, s


def boot_delta(xa, ta, xb, tb, nb=2000, seed=0):
    """日块自助: 两序列先按日求和对齐(共同日), 自助日 ⇒ Δ均值(bps/日→/锚 按 6)与 Δ夏普 CI。"""
    ua, sa = daily(xa, ta); ub, sb = daily(xb, tb)
    com, ia, ib = np.intersect1d(ua, ub, return_indices=True)
    A = sa[ia]; B = sb[ib]; n = len(com); rng = np.random.default_rng(seed)
    def sh(v): return float(v.mean() / (v.std(ddof=1) + 1e-12) * np.sqrt(365.0))
    dm = []; ds = []
    for _ in range(nb):
        idx = rng.integers(0, n, n)
        dm.append((A[idx] - B[idx]).mean() / 6.0); ds.append(sh(A[idx]) - sh(B[idx]))
    return {"n_days": int(n), "delta_mean_bps_per_anchor": round(float((A - B).mean() / 6.0), 4),
            "delta_mean_ci95": [round(float(np.percentile(dm, 2.5)), 4), round(float(np.percentile(dm, 97.5)), 4)],
            "delta_daily_sharpe": round(sh(A) - sh(B), 3),
            "delta_daily_sharpe_ci95": [round(float(np.percentile(ds, 2.5)), 3), round(float(np.percentile(ds, 97.5)), 3)],
            "daily_sharpe_A": round(sh(A), 3), "daily_sharpe_B": round(sh(B), 3),
            "frac_days_A_ge_B": round(float((A >= B).mean()), 4)}


def corr_on(ts_a, xa, ts_b, xb):
    com, ia, ib = np.intersect1d(ts_a, ts_b, return_indices=True)
    if len(com) < 10: return {"n": int(len(com)), "rho": None}
    return {"n": int(len(com)), "rho": round(float(np.corrcoef(xa[ia], xb[ib])[0, 1]), 4)}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--skip_infer", action="store_true"); ap.add_argument("--folds_only", type=int, default=None)
    args = ap.parse_args()
    res = {"created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "session": "6737834a-PH", "script_sha256": sha(os.path.abspath(__file__)),
           "inputs_sha256": {"legs.py": sha(f"{PD}/legs.py"), "king_pred_newgen": sha(NEWGEN["king"][0]), "s2_pred_newgen": sha(NEWGEN["s2"][0]),
                             "net_S0": sha(f"{PD}/net_S0.npy"), "net_S1": sha(f"{PD}/net_S1.npy")}}
    if not args.skip_infer or not os.path.exists(OUT_PREDS):
        res["inference"] = run_inference(args)
    else:
        res["inference"] = {"note": "skipped; reused " + OUT_PREDS}
    P = np.load(OUT_PREDS, allow_pickle=True)
    src = build_src()
    assert np.array_equal(np.asarray(src.ts).astype(np.int64), P["ts"].astype(np.int64)), "panel ts mismatch between training panel and replay panel"
    # --- Y4 definition receipt on the replay panel: Y4[t] == log CLOSE[t+4] - log CLOSE[t] (price T+1h -> T+5h) ---
    # (PanelSource has no CLOSE; use Y1 chain: Y4[t] == Y1[t]+Y1[t+1]+Y1[t+2]+Y1[t+3] where all finite)
    Y1 = src.Y1; Y4 = src.Y4
    chain = Y1[:-3] + Y1[1:-2] + Y1[2:-1] + Y1[3:]
    okc = np.isfinite(chain) & np.isfinite(Y4[:-3])
    res["y4_definition_receipt"] = {"max_abs_Y4_minus_sum_Y1_4": float(np.max(np.abs(chain[okc] - Y4[:-3][okc]))), "cells": int(okc.sum()),
                                    "meaning": "Y4[row T] = Σ_{k=0..3} Y1[T+k] = log CLOSE[T+4]/CLOSE[T] = price (T+1h) -> (T+5h); CLOSE[T] closes at T+1h"}
    log("Y4 receipt", res["y4_definition_receipt"])
    # --- G2: newgen preds, phase 0, reproduce net_S0/net_S1 ---
    import engine.replay_fullhist as RF
    a_ref, _ = RF._all_anchors(src)
    Kng = np.load(NEWGEN["king"][0], allow_pickle=True)[NEWGEN["king"][1]]; Sng = np.load(NEWGEN["s2"][0], allow_pickle=True)[NEWGEN["s2"][1]]
    R_ng = replay(src, Kng, Sng, 0, "newgen_p0", anchors_ref=a_ref)
    ref0 = np.load(f"{PD}/net_S0.npy"); ref1 = np.load(f"{PD}/net_S1.npy")
    g2 = {"maxabs_S0": float(np.max(np.abs(ref0 - R_ng["S0"]["net"]))), "maxabs_S1": float(np.max(np.abs(ref1 - R_ng["S1"]["net"]))), "n": int(R_ng["meta"]["n"])}
    g2["pass"] = bool(g2["maxabs_S0"] < 1e-9 and g2["maxabs_S1"] < 1e-9)
    res["G2_receipt"] = g2; log("G2", g2)
    # --- my preds: phase 0 (control) and phase 3 (live phase) ---
    R0 = replay(src, P["king_p0"], P["s2_p0"], 0, "mine_p0", want_W=True)
    R3 = replay(src, P["king_p3"], P["s2_p3"], 3, "mine_p3", want_W=True)
    out = {}
    for nm, R in (("newgen_p0", R_ng), ("mine_p0", R0), ("mine_p3", R3)):
        yr = R["meta"]["yr"]; ats = R["meta"]["ats"]
        out[nm] = {"n_anchors": int(R["meta"]["n"]), "first_nominal": R["meta"]["first_nominal"], "last_nominal": R["meta"]["last_nominal"]}
        for k in ("S0", "S1", "leg_king", "leg_s2", "leg_funding"):
            out[nm][k] = {"net": summ(R[k]["net"], yr), "pnl_gross": summ(R[k]["pnl"], yr),
                          "turnover_mean": round(float(R[k]["trn"].mean()), 5), "gross_mean": round(float(R[k]["gross"].mean()), 4),
                          "fires_total": int(R[k]["fires"].sum()), "book_rank_ic_mean": round(float(np.nanmean(R[k]["ic"])), 5),
                          "book_rank_ic_by_year": {int(y): round(float(np.nanmean(R[k]["ic"][yr == y])), 5) for y in sorted(set(yr.tolist()))}}
        out[nm]["leg_target_rank_ic"] = {k: round(float(np.nanmean(v)), 5) for k, v in R["meta"]["ic_book_leg"].items()}
        out[nm]["leg_target_rank_ic_by_year"] = {k: {int(y): round(float(np.nanmean(v[yr == y])), 5) for y in sorted(set(yr.tolist()))} for k, v in R["meta"]["ic_book_leg"].items()}
    res["replay"] = out
    # --- G3 + paired deltas ---
    res["G3_mine_vs_newgen_p0"] = {k: {"delta_mean_bps": round(float(R0[k]["net"].mean() - R_ng[k]["net"].mean()), 4),
                                       "corr": round(float(np.corrcoef(R0[k]["net"], R_ng[k]["net"])[0, 1]), 5) if R0["meta"]["n"] == R_ng["meta"]["n"] else None,
                                       "same_n": bool(R0["meta"]["n"] == R_ng["meta"]["n"])} for k in ("S0", "S1")}
    res["delta_p3_minus_p0_mine"] = {k: boot_delta(R3[k]["net"], R3["meta"]["ats"], R0[k]["net"], R0["meta"]["ats"]) for k in ("S0", "S1", "leg_king", "leg_s2", "leg_funding")}
    res["delta_p3_minus_p0_mine_gross"] = {k: boot_delta(R3[k]["pnl"], R3["meta"]["ats"], R0[k]["pnl"], R0["meta"]["ats"]) for k in ("S0", "S1")}
    res["delta_p3_minus_newgen_p0"] = {k: boot_delta(R3[k]["net"], R3["meta"]["ats"], R_ng[k]["net"], R_ng["meta"]["ats"]) for k in ("S0", "S1")}
    # --- rho with the wide book series on the same clock ---
    Wd = np.load(f"{PD}/w2_wide_series.npz", allow_pickle=True); cols = [str(c) for c in Wd["cols"]]; rec = Wd["d30_n2_c42_rec"]
    wts = rec[:, cols.index("ts")].astype(np.int64); wnet = rec[:, cols.index("net")]
    rho = {}
    for nm, R in (("newgen_p0", R_ng), ("mine_p0", R0), ("mine_p3", R3)):
        rowts = (R["meta"]["ats"] - 3600).astype(np.int64); nomts = R["meta"]["ats"].astype(np.int64)
        rho[nm] = {"wide_E_eq_row_ts (W2 一审对齐: 宽 E=T, 在役决策 T+1h, 错 1h)": corr_on(rowts, R["S1"]["net"], wts, wnet),
                   "wide_E_eq_nominal (同钟: 宽 E=N 与在役决策 N)": corr_on(nomts, R["S1"]["net"], wts, wnet)}
    res["rho_with_wide_S1"] = rho
    # --- save series ---
    np.savez_compressed(OUT_SER, **{f"{nm}_{k}_{f}": R[k][f] for nm, R in (("newgen_p0", R_ng), ("mine_p0", R0), ("mine_p3", R3))
                                    for k in ("S0", "S1", "leg_king", "leg_s2", "leg_funding") for f in ("net", "pnl", "trn", "gross", "ic")},
                        **{f"{nm}_ats": R["meta"]["ats"] for nm, R in (("newgen_p0", R_ng), ("mine_p0", R0), ("mine_p3", R3))},
                        mine_p0_W_S1=R0["S1"]["W"], mine_p3_W_S1=R3["S1"]["W"])
    res["outputs"] = {"preds": OUT_PREDS, "series": OUT_SER}
    json.dump(res, open(OUT_JSON, "w"), indent=1, ensure_ascii=False, default=str)
    log("DONE ->", OUT_JSON)
    print(json.dumps({"G1": {l: res["inference"]["legs"][l]["gate_G1_pass"] for l in res["inference"].get("legs", {})} if "legs" in res["inference"] else "skipped",
                      "G2": g2, "S1": {nm: out[nm]["S1"]["net"] for nm in out}, "delta_S1": res["delta_p3_minus_p0_mine"]["S1"], "rho": rho}, indent=1, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
