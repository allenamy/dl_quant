"""W2 两书配置装置 · 在役书逐锚序列生成器 @jpline(2026-08-22, Session 6737834a-W2)。
书构造 = cond_stop_tail.py(devices_2026-08-20)逐字同构: 实盘 legs.compose_book 原样 import, W/RB/EMA α0.05/带 b0.002/
成本 C1=4.137×换手, S0=无止损 / S1=在役逐名止损(成本均价深度 −25%, 连续 2 锚, 冷却 42 锚)。
新增逐锚仪器(不改书): gross(|w|合计), 换手, 毛 pnl, carry(宽 hist v2 面板 f_fund_now×4/f_fund_iv 按符号映射, 与宽书 v3 同式),
regime 变量(等权市场 4h 收益 / BTC 4h 收益), 单腿子书(king/s2/funding 各自 EMA+带, 无止损)。
复现收据: net_S0/net_S1 必须与 probe_artifacts/net_S0.npy / net_S1.npy 逐元素相等(maxabs<1e-9), ts 与 net_S1_ts.npy 相等。
输入: probe_artifacts/king_pred_newgen.npz, s2_pred_newgen.npz(面板由 PanelSource 默认), pod_backup_2026-08-21/wide_panel_4h_hist_v2.npz(仅 carry)。
输出: probe_artifacts/w2_live_series.npz + w2_live_summary.json。只读数据, 不碰实盘仓。
"""
import sys, json, time, numpy as np
PD = "/mnt/storage/private/work_hsy/probe_artifacts"; sys.path.insert(0, PD)
MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
sys.path.insert(0, MA); sys.path.insert(0, MA + "/engine/live"); sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset")
sys.path.insert(0, PD)
import legs as LG
import engine.replay_fullhist as RF
B = "/mnt/storage/private/work_hsy/pod_backup_2026-08-21"
W = {"king": .5952380952380952, "s2": .20238095238095238, "funding": .20238095238095238, "size": 0.}
RB = {"alpha": .5, "lambda": 1.}; C1 = 4.137; BW = 0.002; COOL = 42; ANN = np.sqrt(6 * 365)
t0 = time.time()
src = RF.get_src(None, f"{PD}/king_pred_newgen.npz", f"{PD}/s2_pred_newgen.npz")
a, yr = RF._all_anchors(src); N = src.N; n = len(a)
FI, RVI = src.fund_idx, src.ch.index("rvol_24h"); SYMS = [str(s) for s in src.symbols]
# ---- anchor timestamps (same heuristic as live_nets_ts.py) ----
ts_all = np.asarray(src.ts)
tss = ts_all // 1000 if (ts_all[1] - ts_all[0]) >= 3600 * 1000 else ts_all
ats = np.array([int(tss[int(t)]) for t in a], dtype=np.int64)
ref_ts = np.load(f"{PD}/net_S1_ts.npy")[:, 0].astype(np.int64)
assert np.array_equal(ref_ts, ats), "anchor ts mismatch vs net_S1_ts.npy"
# ---- BTC index ----
try:
    btc_j = int(src.btc_j)
except Exception:
    btc_j = SYMS.index("BTCUSDT")
assert SYMS[btc_j] == "BTCUSDT", f"btc_j={btc_j} -> {SYMS[btc_j]}"
# ---- carry map from wide hist v2 panel ----
PW = np.load(f"{B}/wide_panel_4h_hist_v2.npz", allow_pickle=True)
wsym = [str(s) for s in PW["symbols"]]; widx = {s: i for i, s in enumerate(wsym)}
pw_row = {int(t): j for j, t in enumerate(PW["ts"].astype(np.int64))}
FN = PW["f_fund_now"]; IV = PW["f_fund_iv"]
map_live = np.array([widx.get(s, -1) for s in SYMS]); mapped = map_live >= 0
print("live syms mapped to wide panel:", int(mapped.sum()), "/", N, "unmapped:", [s for s, ok in zip(SYMS, mapped) if not ok][:20], flush=True)
# ---- precompute targets: full book + single-leg sub-books ----
LEGW = {"king": {"king": 1., "s2": 0., "funding": 0., "size": 0.},
        "s2": {"king": 0., "s2": 1., "funding": 0., "size": 0.},
        "funding": {"king": 0., "s2": 0., "funding": 1., "size": 0.}}
TGT, MSK, RET, TGTL = [], [], [], {k: [] for k in LEGW}
mkt_ew = np.zeros(n); btc4 = np.zeros(n); ntrad = np.zeros(n, int)
held = {"k": np.full(N, np.nan), "s": np.full(N, np.nan), "f": np.full(N, np.nan)}
for i, t in enumerate(a):
    ti = int(t); m = np.asarray(src.tradeable(ti))
    if m.dtype == bool: m = np.where(m)[0]
    if i == 0 or ti % 8 == 0:
        v = np.full(N, np.nan); v[m] = src.king[ti, m]; held["k"] = v
    if i == 0 or ti % 24 == 0:
        v = np.full(N, np.nan); v[m] = src.s2[ti, m]; held["s"] = v
    if i == 0 or ti % 8 == 0:
        v = np.full(N, np.nan); v[m] = src.CH[ti, m, FI]; held["f"] = v
    rv = src.CH[ti, m, RVI].astype(float)
    r = LG.compose_book(held["k"][m], held["s"][m], held["f"][m], np.ones(len(m)), weights=W, rvol=rv, risk_budget=RB)
    w = np.full(N, 0.0); w[m] = np.asarray(r["target_w"], float)
    TGT.append(w); MSK.append(m); y = src.Y4[ti, m].astype(float); RET.append(y)
    for k, wl in LEGW.items():
        rl = LG.compose_book(held["k"][m], held["s"][m], held["f"][m], np.ones(len(m)), weights=wl, rvol=rv, risk_budget=RB)
        wv = np.full(N, 0.0); wv[m] = np.asarray(rl["target_w"], float); TGTL[k].append(wv)
    yf = y[np.isfinite(y)]; mkt_ew[i] = yf.mean() * 1e4 if len(yf) else np.nan; ntrad[i] = len(m)
    btc4[i] = float(src.Y4[ti, btc_j]) * 1e4 if np.isfinite(src.Y4[ti, btc_j]) else np.nan
    if i % 2000 == 0: print("precompute", i, "/", n, round(time.time() - t0, 1), "s", flush=True)

def run(mode, TGTx, stop):
    state = None; prev = np.zeros(N); Pi = np.ones(N); sh = np.zeros(N); cb = np.zeros(N)
    cnt = np.zeros(N, int); su = np.full(N, -1)
    pnl = np.zeros(n); trn = np.zeros(n); gross = np.zeros(n); carry = np.zeros(n); unc = np.zeros(n); fires = np.zeros(n, int); nheld = np.zeros(n, int)
    WS = np.zeros((n, N), np.float32)
    for i in range(n):
        m = MSK[i]; syms = [SYMS[j] for j in m]
        out = LG.apply_harvest_ema(TGTx[i][m], syms, state, 0.05); state = out["state"]
        tgt = np.asarray(out["target_w"], float)
        if stop:
            bs = set(np.where(su > i)[0].tolist())
            if bs:
                for k2, j in enumerate(m):
                    if j in bs: tgt[k2] = 0.0
        w = prev.copy(); w[[j for j in range(N) if j not in set(m)]] = 0.0
        d = tgt - w[m]; T = np.abs(d) > BW
        wm = w[m].copy(); wm[T] = tgt[T]
        if T.any(): wm[T] -= wm.sum() / T.sum()
        w[m] = wm
        y = RET[i]; ok = np.isfinite(y); idx = m[ok]
        c = np.zeros(N); c[idx] = w[m][ok] * y[ok] * 1e4
        pnl[i] = c.sum(); trn[i] = float(np.abs(w - prev).sum()); gross[i] = float(np.abs(w).sum()); nheld[i] = int((np.abs(w) > 1e-12).sum())
        # carry (same formula as wide v3: w · fund_now · 4/iv, bps)
        j = pw_row.get(int(ats[i]))
        if j is not None:
            fn = np.zeros(N); iv = np.full(N, 8.0); cov = np.zeros(N, bool)
            mm = mapped
            fnv = FN[j, map_live[mm]]; ivv = IV[j, map_live[mm]]
            fin = np.isfinite(fnv); fn[mm] = np.where(fin, fnv, 0.0); cov[mm] = fin
            ivv = np.where(np.isfinite(ivv) & (ivv > 0), ivv, 8.0); iv[mm] = ivv
            carry[i] = float((w * fn * (4.0 / iv)).sum() * 1e4)
            unc[i] = float(np.abs(w[~cov]).sum())
        else:
            carry[i] = np.nan; unc[i] = gross[i]
        WS[i] = w.astype(np.float32)
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
        if i % 2000 == 0: print(mode, i, "/", n, round(time.time() - t0, 1), "s", flush=True)
    net = pnl - trn * C1
    return dict(net=net, pnl=pnl, trn=trn, gross=gross, carry=carry, unc=unc, fires=fires, nheld=nheld, W=WS)

R = {}
R["S0"] = run("S0", TGT, False); R["S1"] = run("S1", TGT, True)
for k in LEGW: R["leg_" + k] = run("leg_" + k, TGTL[k], False)
# ---- reproduction receipts ----
rec = {}
for k in ("S0", "S1"):
    ref = np.load(f"{PD}/net_{k}.npy"); d = float(np.max(np.abs(ref - R[k]["net"])))
    rec[k] = {"maxabs_diff_vs_probe_artifacts_net": d, "n": int(n), "mean": round(float(R[k]["net"].mean()), 4),
              "sd": round(float(R[k]["net"].std(ddof=1)), 3), "sharpe": round(float(R[k]["net"].mean() / R[k]["net"].std(ddof=1) * ANN), 3),
              "by_year": {int(y_): round(float(R[k]["net"][yr == y_].mean()), 3) for y_ in sorted(set(yr.tolist()))},
              "gross_mean": round(float(R[k]["gross"].mean()), 4), "gross_p5": round(float(np.percentile(R[k]["gross"], 5)), 4), "gross_p95": round(float(np.percentile(R[k]["gross"], 95)), 4),
              "turnover_mean": round(float(R[k]["trn"].mean()), 5), "carry_mean_bps": round(float(np.nanmean(R[k]["carry"])), 4),
              "carry_uncovered_gross_share": round(float(np.nanmean(R[k]["unc"] / np.maximum(R[k]["gross"], 1e-9))), 4),
              "fires_total": int(R[k]["fires"].sum())}
    print("RECEIPT", k, json.dumps(rec[k]), flush=True)
for k in LEGW:
    x = R["leg_" + k]["net"]; rec["leg_" + k] = {"mean": round(float(x.mean()), 4), "sharpe": round(float(x.mean() / x.std(ddof=1) * ANN), 3), "carry_mean_bps": round(float(np.nanmean(R["leg_" + k]["carry"])), 4)}
rec["anchors"] = {"n": int(n), "first": time.strftime("%Y-%m-%d %H:%M", time.gmtime(int(ats[0]))), "last": time.strftime("%Y-%m-%d %H:%M", time.gmtime(int(ats[-1])))}
rec["carry_map"] = {"mapped": int(mapped.sum()), "N": int(N)}
json.dump(rec, open(f"{PD}/w2_live_summary.json", "w"), indent=1, ensure_ascii=False)
np.savez_compressed(f"{PD}/w2_live_series.npz", ts=ats, yr=yr, symbols=np.array(SYMS), mkt_ew=mkt_ew, btc4=btc4, ntrad=ntrad,
                    **{f"{k}_{f}": R[k][f] for k in R for f in ("net", "pnl", "trn", "gross", "carry", "unc", "fires", "nheld")},
                    W_S1=R["S1"]["W"], W_S0=R["S0"]["W"])
print("DONE", round(time.time() - t0, 1), "s", flush=True)
