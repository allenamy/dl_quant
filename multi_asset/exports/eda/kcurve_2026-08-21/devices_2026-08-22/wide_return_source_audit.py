"""WS · 宽书回测收益源对账装置 @jpline(2026-08-22, Session 6737834a-WS)。
SHA256: 脚本自身 SHA 与全部输入 SHA 在运行时写入结果 JSON(`self_sha256` / `input_sha256`); 文档引用以 JSON 为准。

关闭对象 = W2b 二读 §3 口径发现(b): "宽书回测收益源(pod 5m meta y4)与 1h K 线同窗口差均 27 bps/名·锚, 宽书夏普 1.91(meta)↔2.66(1h K 线)"。
只读数据(share 只读; pod 备份/1h 存储/5m 缓存只读); 写 probe_artifacts/ws_results/; 不碰 ~/dl_quant_live; 不调交易 API。

【冻结定义】(先于看 B/C 数字)
- 宽 meta y4(= 面板 Y4, 同一构造 pod_panel_wide / pod_fea_wide_hist): 5m 缓存(dlnative_5m_wide829_f16) ts = bar **收盘**时刻(pod_build_wide: ts=open_time+5min),
  ret5 = clip(c/c_prev−1, ±0.3)(简单收益), E = 缓存行 ts%4h==0(= 收盘于 T 的 bar), y4 = Σ ret5[E..E+47](≥46 有限, 缺 bar 记 0)。
  ⇒ 其价格窗口 = [T−5m, T+3h55m]。
- 1h K 线源 R_wide(W2b 立方体): log(close_1h[T+3h bar]/close_1h[T−1h bar]) = 价格 T→T+4h(宽时钟); R_live = 价格 T+1h→T+5h(在役时钟)。
- 5m 修正源: S_fixlog = Σ_{E+1..E+48} log1p(ret5)(价格 T→T+4h, 对数); S_fixsim = Σ_{E+1..E+48} ret5(影子 shadow_loop.py:307-327 的记账约定: seg=CD[pi+1:ai+1], 简单收益和)。
- 影子 score 行 gross_bps = Σ sm·y4v, y4v = Σ_{(T,T+4h]} ret5(fapi 5m kline close, 简单收益和) ⇒ 影子窗口 = [T, T+4h]。
- 可交易持有收益(4h 内不调仓, 仓位=NAV 份额 w): pnl = Σ w·(close[T+4h]/close[T] − 1) = Σ w·expm1(R_wide) ≡ 源 "1hsim"(1h K 线简单 close→close)。
  对数收益 L 低估多头、高估空头的简单收益各 ≈ L²/2 ⇒ 对净空高波动名的书, 对数口径偏乐观(凸性项 Σ w·(expm1(L)−L) < 0);
  5m 简单收益和 = expm1(L) − Σ_{i<j} r_i r_j(交叉项, 无窗内自相关时均值 0) ⇒ 影子/meta 的"Σ简单"约等于可交易口径。
【冻结判读】
- 对账口径: 成员名(members)上逐名·锚差, 报 均值/中位/p50/p90/p95/p99/>100bps 占比/相关/回归斜率; 偏移谱 k∈{−2..3}: corr(R_wide, Σ_{E+k..E+k+47} log1p ret5) 峰位即窗口错位量。
- 机制判定: 若 S_fixlog 对 R_wide 的 mean|d| ≤ 原 mean|d| 的 10% 且中位 ≈0 ⇒ "差异可解释(窗口错位 1 bar + 简单/对数和)"。
- 书级判定(同管线 w2b_common.wide_native 逐字, 仅换收益源; 臂 S0 / d30_n2_c42; 口径 = 已发表口径: 净 bps/锚(分层成本 情景b, carry×4/iv), 夏普=均/σ×√2190; 共同锚 2022-01-01→2026-06-29 为主比较段):
  |ΔSharpe(1h 或 fixlog vs meta)| ≤ 0.15 且配对块自助 CI 含 0 ⇒ "无实质影响"; 否则 "有实质影响"。
- 三选一: ① 面板源正确(差异可解释且无实质影响) ② 面板源有系统偏差(窗口含决策时已实现的 bar ⇒ 不可交易; 给修正数与受影响清单; 建议以对齐窗口源为准) ③ 传闻(机制不可复现)。
  注: ② 的成立条件是"窗口错位被复现"本身, 与 ΔSharpe 大小无关(错位源不可交易); ΔSharpe 只决定"实质影响"标签。
"""
import os, sys, io, json, time, zipfile, hashlib, glob, datetime as dt
import numpy as np
from multiprocessing import Pool
from scipy.stats import rankdata
PD = "/mnt/storage/private/work_hsy/probe_artifacts"; B = "/mnt/storage/private/work_hsy/pod_backup_2026-08-21"; W3 = "/mnt/storage/private/work_hsy/w3lane"
CACHE = f"{W3}/kcurve/data/dlnative_5m_wide829_f16.npz"; CSV1H = f"{W3}/wide1h_csv"; DAILY = f"{W3}/wide_daily_aug"; SH = f"{PD}/ws_shadow"
OUTD = f"{PD}/ws_results"; os.makedirs(OUTD, exist_ok=True)
OUT_JSON = f"{OUTD}/wide_return_source_audit_2026-08-22.json"
sys.path.insert(0, PD)
import w2b_common as C
T0 = time.time()
def log(*a):
    print(f"[{time.time()-T0:7.1f}s]", *a, flush=True)
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 24), b""): h.update(chunk)
    return h.hexdigest()
def fmt(t): return time.strftime("%Y-%m-%d %H:%M", time.gmtime(int(t)))
R = {"session": "6737834a-WS", "created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "self_sha256": sha(os.path.abspath(__file__))}
INPUTS = {"cache_5m": CACHE, "meta": f"{B}/wide_fea_hist_meta.npz", "panel_v2": f"{B}/wide_panel_4h_hist_v2.npz", "slow_pred": f"{B}/slow_pred_hist_oos.npy",
          "cube": f"{PD}/w2b_ret_cube.npz", "nets_d30": f"{B}/nets_histv2_-30_2_42.npy", "nets_S0": f"{B}/nets_histv2_0_0_0.npy", "w2b_common": f"{PD}/w2b_common.py",
          "shadow_log": f"{SH}/shadow_log.jsonl", "shadow_cfg": f"{SH}/shadow_bundle/config.json"}
R["input_sha256"] = {k: (sha(v) if os.path.exists(v) else None) for k, v in INPUTS.items()}
log("input shas done")

# ───────────────────────────────────────────── 1. 5m cache → cumulative sums
z = zipfile.ZipFile(CACHE)
cts = np.lib.format.read_array(io.BytesIO(z.read("ts.npy"))).astype(np.int64)
csym = [str(s) for s in np.lib.format.read_array(io.BytesIO(z.read("symbols.npy")))]
data = np.lib.format.read_array(io.BytesIO(z.read("data.npy")))
r5 = data[:, :, 0].astype(np.float32); del data, z
TT, NW = r5.shape; log("cache", r5.shape, fmt(cts[0]), "->", fmt(cts[-1]))
fin5 = np.isfinite(r5)
CSr = np.concatenate([np.zeros((1, NW)), np.cumsum(np.where(fin5, r5, 0).astype(np.float64), 0)])
CSl = np.concatenate([np.zeros((1, NW)), np.cumsum(np.where(fin5, np.log1p(r5.astype(np.float64)), 0), 0)])
CSf = np.concatenate([np.zeros((1, NW), np.int32), np.cumsum(fin5, 0, dtype=np.int32)])
clip_hits = int((np.abs(r5) >= 0.3 - 1e-6).sum()); R["cache_clip_hits_total"] = clip_hits
cpos = {int(t): i for i, t in enumerate(cts)}
# receipt 0: cache ts semantics vs raw BTC 5m zip (close-time grid)
zz = zipfile.ZipFile(f"{W3}/wide5m_csv/BTCUSDT/2022-01.zip"); raw = zz.read(zz.namelist()[0]).decode().split("\n")
rows = [r.split(",") for r in raw[1:6]]; jb = csym.index("BTCUSDT"); rec0 = []
for k in range(1, 4):
    ot = int(rows[k][0]) // 1000; c1 = float(rows[k - 1][4]); c2 = float(rows[k][4]); exp_ret = c2 / c1 - 1
    got = float(r5[cpos[ot + 300], jb]); rec0.append({"bar_open": fmt(ot), "cache_ts(close)": fmt(ot + 300), "raw_ret": exp_ret, "cache_ret5": got, "abs_err": abs(got - exp_ret)})
R["receipt_cache_ts_is_close_time"] = rec0; log("receipt0", rec0[0])
assert all(r["abs_err"] < 2e-5 for r in rec0), "cache ts is not bar close time?!"

# ───────────────────────────────────────────── 2. meta / panel / cube / W2b data
MT = np.load(f"{B}/wide_fea_hist_meta.npz", allow_pickle=True); E_ts = MT["E_ts"].astype(np.int64); members = MT["members"]; y4 = MT["y4"]; qvk = MT["qvk"]
nA = len(E_ts); assert y4.shape == (nA, NW)
PW = np.load(f"{B}/wide_panel_4h_hist_v2.npz", allow_pickle=True); pts = PW["ts"].astype(np.int64); PY4 = PW["Y4"]; assert [str(s) for s in PW["symbols"]] == csym
pr = {int(t): j for j, t in enumerate(pts)}; jj = np.array([pr.get(int(t), -1) for t in E_ts]); okj = jj >= 0
fin_both = np.isfinite(y4[okj]) & np.isfinite(PY4[jj[okj]])
R["receipt_meta_y4_equals_panel_Y4"] = {"n_both_finite": int(fin_both.sum()), "maxabs": float(np.max(np.abs(y4[okj][fin_both] - PY4[jj[okj]][fin_both]))),
                                        "finite_pattern_identical": bool((np.isfinite(y4[okj]) == np.isfinite(PY4[jj[okj]])).all())}
log("receipt meta==panel", R["receipt_meta_y4_equals_panel_Y4"])
Z = np.load(f"{PD}/w2b_ret_cube.npz", allow_pickle=True); ats = Z["ts"].astype(np.int64); RWc = Z["R_wide"]; RLc = Z["R_live"]; assert [str(s) for s in Z["symbols"]] == csym
wpos = {int(t): j for j, t in enumerate(E_ts)}; crow = np.array([wpos[int(t)] for t in ats])        # meta row per cube anchor
yrs = np.array([time.gmtime(int(t)).tm_year for t in E_ts])
M = np.zeros((nA, NW), bool)
for j in range(nA): M[j, members[j]] = True
# meta row -> cache index (E) where available with E+49 <= TT
Ei = np.array([cpos.get(int(t), -1) for t in E_ts]); inc = (Ei >= 0) & (Ei + 49 <= TT)
def _valid(a_off, b_off): return (Ei >= 0) & (Ei + min(a_off, 0) >= 0) & (Ei + max(a_off, b_off) <= TT)
def win_rows(CS, a_off, b_off):
    out = np.full((nA, NW), np.nan, np.float32); v = _valid(a_off, b_off); e = Ei[v]
    out[v] = (CS[e + b_off] - CS[e + a_off]).astype(np.float32); return out
def nfin_rows(a_off, b_off):
    out = np.zeros((nA, NW), np.int32); v = _valid(a_off, b_off); e = Ei[v]; out[v] = CSf[e + b_off] - CSf[e + a_off]; return out
S_rec = win_rows(CSr, 0, 48); S_rec[nfin_rows(0, 48) < 46] = np.nan                    # meta definition reproduced
S_fixlog = win_rows(CSl, 1, 49); nf = nfin_rows(1, 49); S_fixlog[nf < 46] = np.nan     # aligned window, log
S_fixsim = win_rows(CSr, 1, 49); S_fixsim[nf < 46] = np.nan                          # aligned window, simple (shadow convention)
JEN = S_fixsim - S_fixlog                                                              # Σ(simple−log) = Jensen term
KNOWN = np.full((nA, NW), np.nan, np.float32); KNOWN[inc] = r5[Ei[inc]]                # ret5 of bar (T−5m, T]: already realised at decision
LAST = np.full((nA, NW), np.nan, np.float32); LAST[inc] = np.log1p(r5[Ei[inc] + 48].astype(np.float64))   # bar (T+3h55m, T+4h]
# receipt 1: reconstruction == meta y4
okr = inc[:, None] & np.isfinite(S_rec) & np.isfinite(y4) & M
d = np.abs(S_rec[okr] - y4[okr])
R["receipt_reconstruction_equals_meta_y4"] = {"n": int(okr.sum()), "maxabs": float(d.max()), "frac_abs_lt_1e-6": float((d < 1e-6).mean()), "mean_abs_bps": float(d.mean() * 1e4),
                                              "finite_pattern_mismatch_rows(members,in_cache)": int(((np.isfinite(S_rec) != np.isfinite(y4)) & inc[:, None] & M).sum())}
log("receipt1", R["receipt_reconstruction_equals_meta_y4"])
del S_rec
# 1h source aligned to meta rows: cube on common anchors + extension (2026-06-29 .. 2026-07-31) from monthly 1h zips
S_1h = np.full((nA, NW), np.nan, np.float32); S_1h[crow] = RWc
S_1hlive = np.full((nA, NW), np.nan, np.float32); S_1hlive[crow] = RLc
ext_rows = np.where((E_ts > ats[-1]) & (E_ts <= int(dt.datetime(2026, 7, 31, 20, tzinfo=dt.timezone.utc).timestamp())))[0]
def parse_1h_ext(s):
    d = f"{CSV1H}/{s}"; ot = []; cl = []
    for ym in ("2026-06", "2026-07"):
        p = f"{d}/{ym}.zip"
        if not os.path.exists(p) or os.path.getsize(p) < 100: continue
        try:
            zq = zipfile.ZipFile(p); rawq = zq.read(zq.namelist()[0]).decode("utf-8", "ignore")
        except Exception:
            continue
        for line in rawq.split("\n"):
            if not line or line.startswith("open_time"): continue
            parts = line.split(",")
            try:
                t = int(parts[0]); t = t // 1000 if t > 10 ** 11 else t; ot.append(t // 1000 if t > 10 ** 10 else t); cl.append(float(parts[4]))
            except Exception:
                continue
    if not ot: return s, None
    ot = np.array(ot, np.int64); cl = np.array(cl); o = np.argsort(ot); ot = ot[o]; cl = cl[o]
    def at(tsx):
        idx = np.searchsorted(ot, tsx); ok = idx < len(ot); idx2 = np.where(ok, idx, 0); hit = ok & (ot[idx2] == tsx)
        return np.where(hit, cl[idx2], np.nan)
    T = E_ts[ext_rows]; c0 = at(T - 3600); c3 = at(T + 3 * 3600)
    with np.errstate(all="ignore"):
        r = np.log(c3 / c0)
    r[~(np.isfinite(r) & (c0 > 0) & (c3 > 0))] = np.nan
    return s, r.astype(np.float32)
with Pool(16) as pool:
    for s, r in pool.imap_unordered(parse_1h_ext, csym, chunksize=8):
        if r is not None: S_1h[ext_rows, csym.index(s)] = r
log("1h extension rows", len(ext_rows), fmt(E_ts[ext_rows[0]]), "->", fmt(E_ts[ext_rows[-1]]), "coverage(members)", float(np.isfinite(S_1h[ext_rows][M[ext_rows]]).mean()))
has1h = np.isfinite(S_1h).any(1); R["spans"] = {"meta_all": [fmt(E_ts[0]), fmt(E_ts[-1]), int(nA)], "cache_5m": [fmt(cts[0]), fmt(cts[-1])],
                                                 "common_cube": [fmt(ats[0]), fmt(ats[-1]), int(len(ats))], "ext_1h": [fmt(E_ts[ext_rows[0]]), fmt(E_ts[ext_rows[-1]]), int(len(ext_rows))]}

# ───────────────────────────────────────────── 3. §A 对账
A = {}
def pair_stats(X, Y, mask):
    ok = np.isfinite(X) & np.isfinite(Y) & mask
    if ok.sum() < 10: return None
    x = X[ok].astype(np.float64); y = Y[ok].astype(np.float64); dd = (x - y) * 1e4; a = np.polyfit(y, x, 1)
    ad = np.abs(dd)
    return {"n": int(ok.sum()), "corr": round(float(np.corrcoef(x, y)[0, 1]), 5), "mean_bps": round(float(dd.mean()), 3), "median_bps": round(float(np.median(dd)), 3),
            "mean_abs_bps": round(float(ad.mean()), 3), "p50_abs": round(float(np.percentile(ad, 50)), 2), "p90_abs": round(float(np.percentile(ad, 90)), 2),
            "p95_abs": round(float(np.percentile(ad, 95)), 2), "p99_abs": round(float(np.percentile(ad, 99)), 2), "max_abs": round(float(ad.max()), 1),
            "frac_abs_gt_100bps": round(float((ad > 100).mean()), 5), "frac_abs_gt_20bps": round(float((ad > 20).mean()), 4),
            "slope_x_on_y": round(float(a[0]), 4), "intercept_bps": round(float(a[1] * 1e4), 3)}
MC = M & has1h[:, None] & inc[:, None]            # members, anchors with both 1h and cache available (= W2b comparison base + July ext)
MCc = M & np.isin(np.arange(nA), crow)[:, None] & inc[:, None]   # strictly common cube anchors
A["pairs_common_cube(members)"] = {"meta−1h": pair_stats(y4, S_1h, MCc), "fixlog−1h": pair_stats(S_fixlog, S_1h, MCc), "fixsim−1h": pair_stats(S_fixsim, S_1h, MCc),
                                   "meta−fixlog": pair_stats(y4, S_fixlog, MCc), "fixsim−fixlog(Jensen)": pair_stats(S_fixsim, S_fixlog, MCc), "1hlive−1h": pair_stats(S_1hlive, S_1h, MCc),
                                   "meta−1hlive": pair_stats(y4, S_1hlive, MCc)}
A["pairs_all_pairs_not_only_members"] = {"meta−1h": pair_stats(y4, S_1h, np.isin(np.arange(nA), crow)[:, None] & np.ones((nA, NW), bool)), "fixlog−1h": pair_stats(S_fixlog, S_1h, np.isin(np.arange(nA), crow)[:, None] & inc[:, None])}
log("A pairs", json.dumps(A["pairs_common_cube(members)"]["meta−1h"]), json.dumps(A["pairs_common_cube(members)"]["fixlog−1h"]))
# Jensen check: Σ(simple−log) vs ½Σr²
half_r2 = np.full((nA, NW), np.nan, np.float32)
CS2 = np.concatenate([np.zeros((1, NW)), np.cumsum(np.where(fin5, r5.astype(np.float64) ** 2, 0), 0)]); half_r2[inc] = 0.5 * (CS2[Ei[inc] + 49] - CS2[Ei[inc] + 1]); del CS2
A["jensen_vs_half_sum_r2"] = pair_stats(JEN, half_r2, MCc); del half_r2
# offset spectrum (5m resolution): corr(R_wide, Σ_{E+k..E+k+47} log1p ret5)
spec = {}
for k in (-2, -1, 0, 1, 2, 3):
    Sk = win_rows(CSl, k, k + 48); st = pair_stats(Sk, S_1h, MCc); spec[f"k={k:+d}"] = {"corr": st["corr"], "mean_abs_bps": st["mean_abs_bps"]} if st else None
A["offset_spectrum_corr_R1h_vs_sum_logret5[E+k..E+k+47]"] = spec; log("offset spectrum", spec)
# by year
A["by_year"] = {}
for y in sorted(set(yrs[has1h & inc].tolist())):
    my = MCc & (yrs == y)[:, None] if y < 2026 else MC & (yrs == y)[:, None]
    A["by_year"][int(y)] = {"meta−1h": pair_stats(y4, S_1h, my), "fixlog−1h": pair_stats(S_fixlog, S_1h, my)}
# by liquidity tier (qv4h from qvk: tier0 ≥5e6, tier1 ≥1e6, tier2 <1e6)
qv4h = np.expm1(np.clip(np.nan_to_num(qvk, nan=0), 0, 30)) * 48
A["by_liquidity_tier"] = {}
for nm, mk in (("tier0_qv4h>=5e6", qv4h >= 5e6), ("tier1_1e6..5e6", (qv4h >= 1e6) & (qv4h < 5e6)), ("tier2_<1e6", qv4h < 1e6)):
    A["by_liquidity_tier"][nm] = {"meta−1h": pair_stats(y4, S_1h, MCc & mk), "fixlog−1h": pair_stats(S_fixlog, S_1h, MCc & mk)}
# by name
byname = {}
for j, s in enumerate(csym):
    mk = MCc[:, j]
    if mk.sum() < 200: continue
    a1 = pair_stats(y4[:, j], S_1h[:, j], mk); a2 = pair_stats(S_fixlog[:, j], S_1h[:, j], mk)
    byname[s] = {"n": a1["n"], "meta−1h_mean_abs": a1["mean_abs_bps"], "meta−1h_mean": a1["mean_bps"], "meta−1h_p99": a1["p99_abs"], "fixlog−1h_mean_abs": a2["mean_abs_bps"], "fixlog−1h_max": a2["max_abs"], "fixlog−1h_median": a2["median_bps"]}
A["by_name_examples"] = {s: byname.get(s) for s in ("BTCUSDT", "ETHUSDT", "SOLUSDT", "DOGEUSDT", "1000PEPEUSDT", "ARBUSDT", "BNBUSDT", "XRPUSDT")}
A["by_name_worst10_fixlog_residual_mean_abs"] = dict(sorted(byname.items(), key=lambda kv: -kv[1]["fixlog−1h_mean_abs"])[:10])
A["by_name_worst10_meta_mean_abs"] = dict(sorted(byname.items(), key=lambda kv: -kv[1]["meta−1h_mean_abs"])[:10])
A["by_name_summary"] = {"n_names": len(byname), "median_over_names_meta_mean_abs": float(np.median([v["meta−1h_mean_abs"] for v in byname.values()])),
                        "median_over_names_fixlog_mean_abs": float(np.median([v["fixlog−1h_mean_abs"] for v in byname.values()])),
                        "names_with_fixlog_mean_abs_gt_2bps": [s for s, v in byname.items() if v["fixlog−1h_mean_abs"] > 2.0]}
# H4 symbols: names without 1h data / without 5m data
no1h = [s for j, s in enumerate(csym) if not np.isfinite(S_1h[:, j]).any()]; no5m = [s for j, s in enumerate(csym) if not fin5[:, j].any()]
A["H4_symbols"] = {"n_symbols_both": NW, "names_without_any_1h_data": no1h, "names_without_any_5m_data": no5m, "note": "same 829-name list on both sides (1h pull used panel symbols); renames not an issue within one source family"}
# H5 gaps
nf_m = nf[MCc]; gapfrac = float((nf_m < 48).mean())
gm = MCc & (nf < 48)
A["H5_gaps"] = {"frac_member_windows_lt_48_finite_bars": gapfrac, "frac_lt_46(excluded_by_rule)": float((nf_m < 46).mean()),
                "fixlog−1h_on_gap_windows": pair_stats(S_fixlog, S_1h, gm), "fixlog−1h_on_full_windows": pair_stats(S_fixlog, S_1h, MCc & (nf == 48))}
# H6 outliers: top-10 |fixlog−1h| pairs
dd = np.where(MCc & np.isfinite(S_fixlog) & np.isfinite(S_1h), np.abs(S_fixlog - S_1h), 0)
flat = np.argsort(dd, axis=None)[-10:][::-1]; outl = []
for f in flat:
    i, j = np.unravel_index(f, dd.shape); e = Ei[i]; seg = r5[e + 1:e + 49, j]
    outl.append({"symbol": csym[j], "anchor": fmt(E_ts[i]), "fixlog": float(S_fixlog[i, j]), "R1h": float(S_1h[i, j]), "meta": float(y4[i, j]), "abs_diff_bps": float(dd[i, j] * 1e4),
                 "n_finite_bars": int(np.isfinite(seg).sum()), "n_clipped_bars(|ret5|>=0.3)": int((np.abs(seg) >= 0.3 - 1e-6).sum()), "max_abs_ret5": float(np.nanmax(np.abs(seg))) if np.isfinite(seg).any() else None})
A["H6_outliers_top10_fixlog_vs_1h"] = outl
A["H7_f16_floor_BTC"] = byname.get("BTCUSDT")
del dd
R["A"] = A; log("A done")

# ───────────────────────────────────────────── 4. §B 书级: 同管线换收益源
D = C.load_all(verbose=False); log("w2b D loaded")
LRa, POS = C.wide_legs(D)
def wide_native_rows(RET_rows, depth, need, cool, keep_W, tag):
    """= w2b_common.wide_native 逐字(宽书自有管线 α0.1/b2.5e-4/止损置零于 EMA 前/分层成本/成员名记账), 仅两处改动:
    (1) 收益源按 meta 行给定(RET_rows[j]; 该行全 NaN ⇒ 回退 meta y4, 仅暖机/末尾), (2) 返回全部产出锚(非仅共同锚)。"""
    NWx = D.NW; nAx = len(D.E_ts); H = np.zeros(NWx); Pi = np.ones(NWx); sh = np.zeros(NWx); cb = np.zeros(NWx); cnt = np.zeros(NWx, int); su = np.full(NWx, -1)
    rec = []; WS = []; nfb = 0
    for j in range(nAx):
        jp = D.pw_row.get(int(D.E_ts[j]))
        if jp is None: continue
        m = D.members[j]
        sc = {"king": D.SLOW[j, m], "rev24": -D.R24[jp, m], "fund": D.FE[jp, m]}
        w3 = C.wide_w3_at(LRa, POS, j)
        zed = w3[0] * np.nan_to_num(C.xz(sc["king"])) + w3[1] * np.nan_to_num(C.xz(sc["rev24"])) + w3[2] * np.nan_to_num(C.xz(sc["fund"]))
        ok = np.isfinite(D.y4m[j, m]); qv = np.expm1(np.clip(D.qvk[j, m], 0, 30)) * 48
        sel = ok & (qv >= 2.5e5)
        if sel.sum() < 80: continue
        w = np.where(sel, zed, 0.0); w -= w[sel].mean(); g = np.abs(w).sum()
        if g < 1e-9: continue
        w /= g; capw = 2.5 / max(int(sel.sum()), 1); w = np.clip(w, -capw, capw); g2 = np.abs(w).sum()
        if g2 > 1e-9: w /= g2
        tgt = np.zeros(NWx); tgt[m] = w
        if depth is not None:
            bl = su > j
            if bl.any(): tgt[bl] = 0.0
        sm = H + 0.1 * (tgt - H); trade = sm - H
        sm = np.where(np.abs(trade) < 2.5e-4, H, sm); trade = sm - H
        tr = C.tier_of(qv); tabs = np.abs(trade[m])
        cbps = sum(tabs[tr == tt].sum() * (fr * mk + (1 - fr) * tk) for tt, (mk, tk, fr) in enumerate(C.COST_B))
        rowret = RET_rows[j, m] if RET_rows is not None else None
        if rowret is None or not np.isfinite(rowret).any():
            yv = np.nan_to_num(D.y4m[j, m], nan=0.0); nfb += 1
        else:
            yv = np.nan_to_num(np.asarray(rowret, float), nan=0.0)
        yfull = np.zeros(NWx); yfull[m] = yv
        fnow = np.nan_to_num(D.FN[jp, m], nan=0.0); ivv = D.IV[jp, m]; ivv = np.where(np.isfinite(ivv) & (ivv > 0), ivv, 8.0)
        car = (sm[m] * fnow * (4.0 / ivv)).sum() * 1e4; pnl_raw = float((sm[m] * yv).sum() * 1e4)
        nsh = np.where(Pi > 1e-12, sm / Pi, 0.0)
        same = np.sign(nsh) == np.sign(sh); add = same & (np.abs(nsh) > np.abs(sh))
        red = same & (~add) & (np.abs(nsh) > 1e-12); new = (~same) | (np.abs(sh) < 1e-12)
        cb = np.where(add, cb + (nsh - sh) * Pi, cb)
        with np.errstate(all="ignore"):
            ratio = np.where(np.abs(sh) > 1e-12, nsh / np.where(np.abs(sh) > 1e-12, sh, 1.0), 0.0)
        cb = np.where(red, cb * ratio, cb); cb = np.where(new, nsh * Pi, cb); cb = np.where(np.abs(nsh) < 1e-12, 0.0, cb)
        sh = nsh
        with np.errstate(all="ignore"):
            avg = np.where(np.abs(sh) > 1e-12, cb / sh, np.nan)
            dep = np.where(np.isfinite(avg) & (Pi > 0), np.sign(sh) * (1.0 - avg / Pi), 0.0)
        fires_i = 0
        if depth is not None:
            cand = (np.abs(sh) > 1e-12) & (dep <= depth) & (su <= j)
            cnt = np.where(cand, cnt + 1, 0); fr2 = cnt >= need
            if fr2.any(): su[fr2] = j + cool; cnt[fr2] = 0; fires_i = int(fr2.sum())
        rec.append((int(D.E_ts[j]), float(pnl_raw - car - cbps), pnl_raw, float(car), float(cbps), float(np.abs(sm).sum()), float(np.abs(sm[m]).sum()), int((np.abs(sm) > 1e-12).sum()), fires_i, float(np.abs(trade).sum()), j))
        if keep_W: WS.append(sm.astype(np.float32))
        H = sm; Pi = Pi * (1.0 + yfull)
    rec = np.array(rec); out = {"ts": rec[:, 0].astype(np.int64), "net": rec[:, 1], "pnl": rec[:, 2], "carry": rec[:, 3], "cost": rec[:, 4], "gross": rec[:, 5], "gross_member": rec[:, 6], "nheld": rec[:, 7].astype(int), "fires": rec[:, 8].astype(int), "trn": rec[:, 9], "row": rec[:, 10].astype(int), "n_fallback_meta": nfb}
    if keep_W: out["W"] = np.stack(WS)
    return tag, out
S_1hsim = np.expm1(S_1h.astype(np.float64)).astype(np.float32)                          # 1h K 线简单 close→close = 可交易 4h 持有收益
SRC = {"meta": None, "fixlog": S_fixlog, "fixsim": S_fixsim, "1h": S_1h, "1hlive": S_1hlive, "1hsim": S_1hsim}
ARMS = {"S0": (None, 0, 0), "d30": (-0.30, 2, 42)}
jobs = [(f"{s}|{a}", SRC[s], ARMS[a], a == "d30") for s in SRC for a in ARMS]
def _job(args):
    tag, ret, (dp, nd, cl), keep = args
    return wide_native_rows(ret, dp, nd, cl, keep, tag)
RUNS = {}
with Pool(len(jobs)) as pool:
    for tag, out in pool.imap_unordered(_job, jobs):
        RUNS[tag] = out; log("run done", tag, "n", len(out["ts"]), "fallback rows", out["n_fallback_meta"])
# receipts vs pod nets
Bres = {"receipts": {}}
for arm, fn in (("d30", "nets_histv2_-30_2_42.npy"), ("S0", "nets_histv2_0_0_0.npy")):
    ref = np.load(f"{B}/{fn}"); o = RUNS[f"meta|{arm}"]; rt = ref[:, 0].astype(np.int64); ot = o["ts"]
    common = np.intersect1d(rt, ot); ri = np.searchsorted(rt, common); oi = np.searchsorted(ot, common)
    Bres["receipts"][f"meta|{arm} vs pod {fn}"] = {"n_ref": int(len(rt)), "n_run": int(len(ot)), "n_common": int(len(common)), "maxabs_net_diff": float(np.max(np.abs(ref[ri, 1] - o["net"][oi]))) if len(common) else None}
log("receipts B", Bres["receipts"])
# spans
ts_any = RUNS["meta|d30"]["ts"]; yr_run = np.array([time.gmtime(int(t)).tm_year for t in ts_any])
span_masks = {"FULL(published span, meta only)": np.ones(len(ts_any), bool), "COMMON(2022-01-01..2026-06-29)": np.isin(ts_any, ats), "EXT(..2026-07-31)": ts_any <= E_ts[ext_rows[-1]]}
def metrics(net, pnl, carry, cost, yr, fires, gross):
    def sh_(x): s = x.std(ddof=1); return float(x.mean() / s * np.sqrt(2190)) if s > 0 and len(x) > 2 else float("nan")
    cum = np.cumsum(net); dd = cum - np.maximum.accumulate(cum)
    m24 = yr >= 2024; out = {"n": int(len(net)), "net_mean": round(float(net.mean()), 4), "sharpe": round(sh_(net), 3), "net_2024on": round(float(net[m24].mean()), 4) if m24.any() else None,
                              "sharpe_2024on": round(sh_(net[m24]), 3) if m24.any() else None, "maxDD_cum_bps": round(float(-dd.min()), 1), "ES5_pg": round(float(np.sort(net)[:max(1, len(net) // 20)].mean()), 2),
                              "pnl_gross_mean": round(float(pnl.mean()), 4), "carry_mean": round(float(carry.mean()), 4), "cost_mean": round(float(cost.mean()), 4), "fires": int(fires.sum()), "gross_held_mean": round(float(gross.mean()), 4),
                              "by_year": {int(y): {"net": round(float(net[yr == y].mean()), 4), "sharpe": round(sh_(net[yr == y]), 3), "pnl_gross": round(float(pnl[yr == y].mean()), 4), "n": int((yr == y).sum())} for y in sorted(set(yr.tolist()))}}
    return out
Bres["runs"] = {}
for tag, o in RUNS.items():
    Bres["runs"][tag] = {}
    for sp, mk0 in span_masks.items():
        if tag.split("|")[0] != "meta" and sp.startswith("FULL"): continue
        mk = np.isin(o["ts"], ts_any[mk0])
        if tag.split("|")[0] in ("1h", "1hlive") and sp.startswith("EXT") and tag.split("|")[0] == "1hlive": continue
        yr_o = np.array([time.gmtime(int(t)).tm_year for t in o["ts"]])
        Bres["runs"][tag][sp] = metrics(o["net"][mk], o["pnl"][mk], o["carry"][mk], o["cost"][mk], yr_o[mk], o["fires"][mk], o["gross"][mk])
# W2b held-gross caliber on COMMON (net / S0-twin gross_total of the same source)
for s in SRC:
    for arm in ARMS:
        o = RUNS[f"{s}|{arm}"]; o0 = RUNS[f"{s}|S0"]; mk = np.isin(o["ts"], ats); mk0 = np.isin(o0["ts"], o["ts"][mk])
        x = o["net"][mk] / o0["gross"][mk0]; flat = (o["pnl"][mk] - o["carry"][mk] - 3.52 * o["trn"][mk]) / o0["gross"][mk0]
        Bres["runs"][f"{s}|{arm}"]["COMMON_W2b_heldgross_caliber"] = {"sharpe_tiered": round(C.sharpe(x), 3), "sharpe_flat3.52": round(C.sharpe(flat), 3), "by_year_sharpe_flat3.52": {int(y): round(C.sharpe(flat[yr_run[np.isin(ts_any, o["ts"][mk])] == y]), 3) for y in sorted(set(yr_run.tolist()))}}
# paired block-bootstrap ΔSharpe on COMMON (raw net caliber)
def aligned(tagA, tagB):
    a = RUNS[tagA]; b = RUNS[tagB]; cm = np.intersect1d(np.intersect1d(a["ts"], b["ts"]), ats)
    return a["net"][np.searchsorted(a["ts"], cm)], b["net"][np.searchsorted(b["ts"], cm)]
Bres["delta_sharpe_boot_COMMON"] = {}
for arm in ARMS:
    for pa, pb in (("1h", "meta"), ("fixlog", "meta"), ("fixlog", "1h"), ("fixsim", "fixlog"), ("1hlive", "1h"), ("fixsim", "meta"), ("1hsim", "meta"), ("1hsim", "fixsim"), ("1hsim", "1h"), ("1hsim", "fixlog")):
        x, y = aligned(f"{pa}|{arm}", f"{pb}|{arm}")
        bs = C.boot_delta_sharpe(x, y); bs["sharpe_a"] = round(C.sharpe(x), 3); bs["sharpe_b"] = round(C.sharpe(y), 3); bs["delta_point"] = round(C.sharpe(x) - C.sharpe(y), 3)
        Bres["delta_sharpe_boot_COMMON"][f"{arm}: {pa} − {pb}"] = bs
log("B delta", json.dumps(Bres["delta_sharpe_boot_COMMON"]))
# fixed-position decomposition (positions from meta|d30 run): pnl_src = Σ W·S_src (members), terms KNOWN/LAST/JENSEN
o = RUNS["meta|d30"]; Wm = o["W"]; rowsR = o["row"]; mkc = np.isin(o["ts"], ats) & inc[rowsR]
Bres["fixed_position_decomposition_COMMON(meta d30 positions)"] = {}
def book_dot(Sx, rowsel):
    out = np.zeros(rowsel.sum())
    for k, (i, j) in enumerate(zip(np.where(rowsel)[0], rowsR[rowsel])):
        m = members[j]; out[k] = float((Wm[i, m] * np.nan_to_num(Sx[j, m], nan=0.0)).sum() * 1e4)
    return out
CONVEX = (np.expm1(S_1h.astype(np.float64)) - S_1h).astype(np.float32)                    # 真凸性: 可交易简单 − 对数(1h)
CROSS = (S_fixsim - np.expm1(S_fixlog.astype(np.float64))).astype(np.float32)             # 5m 简单和 − 真简单 = −Σ_{i<j} r_i r_j(交叉项)
pn = {nm: book_dot(Sx, mkc) for nm, Sx in (("meta", y4), ("fixlog", S_fixlog), ("fixsim", S_fixsim), ("1h", S_1h), ("1hlive", S_1hlive), ("1hsim", S_1hsim), ("KNOWN_bar(T-5m,T]", KNOWN), ("LAST_bar(T+3h55m,T+4h]", LAST), ("JENSEN", JEN), ("CONVEX(expm1(L1h)-L1h)", CONVEX), ("CROSS(fixsim-expm1(fixlog))", CROSS))}
yr_c = np.array([time.gmtime(int(t)).tm_year for t in o["ts"][mkc]])
dec = {"all": {nm: round(float(v.mean()), 4) for nm, v in pn.items()}, "by_year": {}}
dec["all"]["meta−fixlog"] = round(float((pn["meta"] - pn["fixlog"]).mean()), 4); dec["all"]["KNOWN−LAST+JENSEN"] = round(float((pn["KNOWN_bar(T-5m,T]"] - pn["LAST_bar(T+3h55m,T+4h]"] + pn["JENSEN"]).mean()), 4)
dec["all"]["corr(meta−fixlog, KNOWN−LAST+JENSEN)"] = round(float(np.corrcoef(pn["meta"] - pn["fixlog"], pn["KNOWN_bar(T-5m,T]"] - pn["LAST_bar(T+3h55m,T+4h]"] + pn["JENSEN"])[0, 1]), 4)
dec["all"]["1hsim−1h(=CONVEX)"] = round(float((pn["1hsim"] - pn["1h"]).mean()), 4); dec["all"]["meta−1hsim"] = round(float((pn["meta"] - pn["1hsim"]).mean()), 4); dec["all"]["fixsim−1hsim(=CROSS)"] = round(float((pn["fixsim"] - pn["1hsim"]).mean()), 4)
dec["all"]["CONVEX_share_of_1h_pnl"] = round(float(pn["CONVEX(expm1(L1h)-L1h)"].mean() / pn["1h"].mean()), 4)
dec["all"]["sd_pg"] = {nm: round(float(v.std(ddof=1)), 3) for nm, v in pn.items()}
for y in sorted(set(yr_c.tolist())):
    m_ = yr_c == y; dec["by_year"][int(y)] = {nm: round(float(v[m_].mean()), 4) for nm, v in pn.items()}
    dec["by_year"][int(y)]["meta−fixlog"] = round(float((pn["meta"] - pn["fixlog"])[m_].mean()), 4); dec["by_year"][int(y)]["meta−1h"] = round(float((pn["meta"] - pn["1h"])[m_].mean()), 4)
    dec["by_year"][int(y)]["meta−1hsim"] = round(float((pn["meta"] - pn["1hsim"])[m_].mean()), 4); dec["by_year"][int(y)]["t_stat_CONVEX"] = round(float(pn["CONVEX(expm1(L1h)-L1h)"][m_].mean() / pn["CONVEX(expm1(L1h)-L1h)"][m_].std(ddof=1) * np.sqrt(m_.sum())), 2)
    dec["by_year"][int(y)]["t_stat_KNOWN"] = round(float(pn["KNOWN_bar(T-5m,T]"][m_].mean() / pn["KNOWN_bar(T-5m,T]"][m_].std(ddof=1) * np.sqrt(m_.sum())), 2)
Bres["fixed_position_decomposition_COMMON(meta d30 positions)"] = dec; log("decomp", json.dumps(dec["all"]))
# side estimate (out of scope, no pipeline re-run): in-役 book replay family uses log Y4 (= R_live); convexity term Σ W_S1·(expm1(R_live) − R_live) on the 140 live names
try:
    LV = np.load(f"{PD}/w2_live_series.npz", allow_pickle=True); lsym = [str(s) for s in LV["symbols"]]; lmap = np.array([csym.index(s) for s in lsym]); WS1 = LV["W_S1"].astype(float); lts = LV["ts"].astype(np.int64)
    assert np.array_equal(lts, ats)
    RLl = RLc[:, lmap].astype(np.float64); conv = np.nan_to_num(np.expm1(RLl) - RLl); pnl_log = np.nan_to_num(RLl)
    cv = (WS1 * conv).sum(1) * 1e4; pl = (WS1 * pnl_log).sum(1) * 1e4; yr_l = np.array([time.gmtime(int(t)).tm_year for t in lts])
    S1_net = LV["S1_net"]; S1_pnl = LV["S1_pnl"]
    Bres["spillover_live_book_convexity(side_estimate)"] = {"note": "在役离线回放族 Y4 为对数收益(= R_live); 此处只对 W2 在役 S1 持仓算凸性项 Σ W·(expm1(Y4)−Y4), 不重跑在役管线; 正=对数口径低估, 负=对数口径高估",
        "convexity_mean_bps_per_anchor": round(float(cv.mean()), 4), "S1_pnl_mean(log caliber)": round(float(S1_pnl.mean()), 4), "S1_net_mean(log caliber)": round(float(S1_net.mean()), 4),
        "my_pnl_log_mean(check ≈ S1_pnl)": round(float(pl.mean()), 4), "convexity_share_of_pnl": round(float(cv.mean() / S1_pnl.mean()), 4),
        "sharpe_S1_net_log": round(C.sharpe(S1_net), 3), "sharpe_S1_net_plus_convexity": round(C.sharpe(S1_net + cv), 3), "by_year_convexity": {int(y): round(float(cv[yr_l == y].mean()), 4) for y in sorted(set(yr_l.tolist()))}}
    log("spillover live", json.dumps(Bres["spillover_live_book_convexity(side_estimate)"]))
except Exception as ex:
    Bres["spillover_live_book_convexity(side_estimate)"] = {"error": repr(ex)}
# leg rank-IC vs targets (members; per anchor; COMMON span rows)
rows_c = np.where(np.isin(np.arange(nA), crow) & inc & has1h)[0]
def ic_chunk(rows):
    out = {}
    for j in rows:
        jp = D.pw_row.get(int(E_ts[j]));
        if jp is None: continue
        m = members[j]
        legs = {"king": D.SLOW[j, m], "rev24": -D.R24[jp, m], "fund": D.FE[jp, m]}
        w3 = C.wide_w3_at(LRa, POS, j); legs["book_z"] = w3[0] * np.nan_to_num(C.xz(legs["king"])) + w3[1] * np.nan_to_num(C.xz(legs["rev24"])) + w3[2] * np.nan_to_num(C.xz(legs["fund"]))
        tg = {"meta": y4[j, m], "fixlog": S_fixlog[j, m], "fixsim": S_fixsim[j, m], "1h": S_1h[j, m], "1hlive": S_1hlive[j, m], "KNOWN": KNOWN[j, m]}
        res = {}
        for ln, lv in legs.items():
            for tn, tv in tg.items():
                ok = np.isfinite(lv) & np.isfinite(tv)
                if ok.sum() < 30: res[f"{ln}|{tn}"] = np.nan; continue
                a = rankdata(lv[ok]); b = rankdata(tv[ok]); res[f"{ln}|{tn}"] = float(np.corrcoef(a, b)[0, 1])
        out[int(j)] = res
    return out
with Pool(14) as pool:
    parts = pool.map(ic_chunk, np.array_split(rows_c, 14))
ICS = {}
for p in parts: ICS.update(p)
keys = sorted({k for v in ICS.values() for k in v}); rows_s = sorted(ICS)
ICM = {k: np.array([ICS[r].get(k, np.nan) for r in rows_s]) for k in keys}; yr_i = yrs[np.array(rows_s)]
icout = {"mean": {}, "by_year": {}, "paired_delta(meta−fixlog)": {}}
for k in keys:
    v = ICM[k]; icout["mean"][k] = {"ic": round(float(np.nanmean(v)), 5), "t": round(float(np.nanmean(v) / np.nanstd(v, ddof=1) * np.sqrt(np.isfinite(v).sum())), 2)}
for ln in ("king", "rev24", "fund", "book_z"):
    d_ = ICM[f"{ln}|meta"] - ICM[f"{ln}|fixlog"]; ok = np.isfinite(d_)
    icout["paired_delta(meta−fixlog)"][ln] = {"mean": round(float(d_[ok].mean()), 5), "t": round(float(d_[ok].mean() / d_[ok].std(ddof=1) * np.sqrt(ok.sum())), 2),
                                           "by_year": {int(y): round(float(np.nanmean(d_[yr_i == y])), 5) for y in sorted(set(yr_i.tolist()))}}
    icout["by_year"][ln] = {int(y): {tn: round(float(np.nanmean(ICM[f"{ln}|{tn}"][yr_i == y])), 5) for tn in ("meta", "fixlog", "1h", "KNOWN")} for y in sorted(set(yr_i.tolist()))}
Bres["leg_rank_ic_vs_targets_COMMON"] = icout; log("IC", json.dumps(icout["paired_delta(meta−fixlog)"]))
R["B"] = Bres

# ───────────────────────────────────────────── 5. §C 影子对账(08-16→08-21 score 行)
Cres = {}
try:
    cfg = json.load(open(f"{SH}/shadow_bundle/config.json")); psym = cfg["symbols_panel"]; assert psym == csym; live = cfg["symbols_live"]
    sc = [json.loads(l) for l in open(f"{SH}/shadow_log.jsonl")]; sc = {int(r["anchor_ts"]): r for r in sc if r.get("e") == "score"}
    wfiles = {int(os.path.basename(f)[:-4]): f for f in glob.glob(f"{SH}/state/weights/*.npz")}
    roll = np.load(f"{SH}/state/rolling.npz", allow_pickle=True); rts = roll["ts"].astype(np.int64); rr5 = roll["data"][:, :, 0].astype(np.float32); rpos = {int(t): i for i, t in enumerate(rts)}
    # vision daily 5m / 1h for live names
    def parse_daily(s):
        out5 = {}; out1 = {}
        for iv, store in (("5m", out5), ("1h", out1)):
            for p in sorted(glob.glob(f"{DAILY}/{s}/{iv}/*.zip")):
                try:
                    zq = zipfile.ZipFile(p); rawq = zq.read(zq.namelist()[0]).decode("utf-8", "ignore")
                except Exception:
                    continue
                for line in rawq.split("\n"):
                    if not line or line.startswith("open_time"): continue
                    parts = line.split(",")
                    try:
                        t = int(parts[0]); t = t // 1000 if t > 10 ** 14 else t; t = t // 1000 if t > 10 ** 10 else t; store[t] = float(parts[4])
                    except Exception:
                        continue
        return s, out5, out1
    with Pool(16) as pool:
        VIS = {s: (o5, o1) for s, o5, o1 in pool.imap_unordered(parse_daily, live, chunksize=10)}
    nvis = sum(1 for s in VIS if VIS[s][0]); log("vision daily parsed names with 5m", nvis, "of", len(live))
    tab = []
    for T in sorted(sc):
        if T not in wfiles: continue
        wz = np.load(wfiles[T]); idx = wz["idx"].astype(int); val = wz["val"].astype(float)
        pi = rpos.get(T); ai = rpos.get(T + 14400)
        if pi is None or ai is None: continue
        seg_sh = rr5[pi + 1:ai + 1][:, idx]; seg_meta = rr5[pi:ai][:, idx]
        def ssum(seg, logm=False):
            finm = np.isfinite(seg); x = np.where(finm, np.log1p(seg.astype(np.float64)) if logm else seg, 0).sum(0); x[finm.sum(0) < 46] = 0.0; return x
        g_sh = float((val * ssum(seg_sh)).sum() * 1e4); g_meta = float((val * ssum(seg_meta)).sum() * 1e4); g_fixlog = float((val * ssum(seg_sh, True)).sum() * 1e4)
        # vision 5m / 1h
        g_v5 = np.nan; g_v1 = np.nan; g_v1s = np.nan; cov5 = 0; cov1 = 0
        v5 = np.zeros(len(idx)); v1 = np.zeros(len(idx)); ok5 = np.zeros(len(idx), bool); ok1 = np.zeros(len(idx), bool)
        for k, j in enumerate(idx):
            s = csym[j]; o5, o1 = VIS.get(s, ({}, {}))
            cl = [o5.get(T + 300 * q) for q in range(0, 49)]
            if all(c is not None and c > 0 for c in cl):
                v5[k] = sum(cl[q + 1] / cl[q] - 1 for q in range(48)); ok5[k] = True
            c0 = o1.get(T - 3600); c4 = o1.get(T + 3 * 3600)
            if c0 and c4 and c0 > 0 and c4 > 0: v1[k] = np.log(c4 / c0); ok1[k] = True
        wabs = np.abs(val).sum()
        if ok5.sum() and np.abs(val[ok5]).sum() / wabs > 0.95: g_v5 = float((val * v5).sum() * 1e4)
        if ok1.sum() and np.abs(val[ok1]).sum() / wabs > 0.95: g_v1 = float((val * v1).sum() * 1e4); g_v1s = float((val * np.where(ok1, np.expm1(v1), 0.0)).sum() * 1e4)
        tab.append({"anchor": fmt(T), "anchor_ts": T, "gross_logged": sc[T]["gross_bps"], "net_logged": sc[T]["net_bps"], "g_shadow_conv(rolling,(T,T+4h],simple)": round(g_sh, 3),
                    "g_meta_conv(rolling,[T-5m,T+3h55m],simple)": round(g_meta, 3), "g_fixlog(rolling,(T,T+4h],log)": round(g_fixlog, 3),
                    "g_vision5m_conv": None if not np.isfinite(g_v5) else round(g_v5, 3), "g_vision1h_log": None if not np.isfinite(g_v1) else round(g_v1, 3), "g_vision1h_simple(tradable)": None if not np.isfinite(g_v1s) else round(g_v1s, 3),
                    "gross_pos": round(float(wabs), 4), "cov_vision5m_w": round(float(np.abs(val[ok5]).sum() / wabs), 3), "cov_vision1h_w": round(float(np.abs(val[ok1]).sum() / wabs), 3)})
    Cres["per_anchor"] = tab
    def col(k): return np.array([r[k] if r[k] is not None else np.nan for r in tab], float)
    gl = col("gross_logged"); summ = {"n_anchors": len(tab)}
    for k in ("g_shadow_conv(rolling,(T,T+4h],simple)", "g_meta_conv(rolling,[T-5m,T+3h55m],simple)", "g_fixlog(rolling,(T,T+4h],log)", "g_vision5m_conv", "g_vision1h_log", "g_vision1h_simple(tradable)"):
        v = col(k); ok = np.isfinite(v) & np.isfinite(gl)
        if ok.sum() >= 3:
            dd_ = v[ok] - gl[ok]; rel = np.abs(dd_) / np.maximum(np.maximum(np.abs(v[ok]), np.abs(gl[ok])), 1.0)
            summ[k] = {"n": int(ok.sum()), "corr_vs_logged": round(float(np.corrcoef(v[ok], gl[ok])[0, 1]), 4), "mean_diff_bps": round(float(dd_.mean()), 3), "mean_abs_diff_bps": round(float(np.abs(dd_).mean()), 3),
                       "max_abs_diff_bps": round(float(np.abs(dd_).max()), 3), "median_rel_abs_diff(recon_style)": round(float(np.median(rel)), 4), "sum_source_bps": round(float(v[ok].sum()), 2), "sum_logged_bps": round(float(gl[ok].sum()), 2)}
    Cres["summary_vs_logged_gross"] = summ
    Cres["note"] = "shadow gross_bps source = /fapi/v1/klines 5m close (simple-return sum over (T,T+4h], shadow_loop.py:307-327); bookTicker mids are not archived by the shadow (no such series exists) — (iii) 'bookTicker 中价' 不可得, 以影子实际源代之."
    log("C", json.dumps(summ))
except Exception as ex:
    import traceback; Cres["error"] = repr(ex); Cres["trace"] = traceback.format_exc(); log("C failed", repr(ex))
R["C"] = Cres

# ───────────────────────────────────────────── 6. verdict fields
pm = A["pairs_common_cube(members)"]
explained = pm["fixlog−1h"]["mean_abs_bps"] <= 0.10 * pm["meta−1h"]["mean_abs_bps"] and abs(pm["fixlog−1h"]["median_bps"]) < 0.5
dsb = Bres["delta_sharpe_boot_COMMON"]
material = {k: (abs(v["delta_point"]) > 0.15 or not (v["CI95"][0] <= 0 <= v["CI95"][1])) for k, v in dsb.items() if ("1h − meta" in k or "fixlog − meta" in k or "1hsim − meta" in k or "fixsim − meta" in k)}
tradable_gap = {k: v["delta_point"] for k, v in dsb.items() if "1hsim − meta" in k}
spec_peak = max(spec.items(), key=lambda kv: kv[1]["corr"] if kv[1] else -1)[0]
R["verdict"] = {"mechanism_reproduced": bool(explained), "offset_spectrum_peak": spec_peak, "window_of_meta_y4": "[T-5m, T+3h55m] (includes the bar already realised at decision time T; excludes the last 5m bar)",
                "material_sharpe_impact": material, "choice": ("② 面板源有系统偏差(窗口错位 1 bar: meta y4 含决策时已实现的 bar, 不可交易; 以对齐窗口源(1h K 线 / 5m 修正)为准)" if explained else "③ 传闻/未复现"),
                "tradable_caliber_gap_1hsim_minus_meta_sharpe": tradable_gap,
                "recommended_source": "可交易口径 = 1h K 线简单 close→close 持有收益(源 1hsim, 窗口 T→T+4h); 影子的 Σ简单5m(T,T+4h] 与之只差交叉项; 对数口径(1h-log/fixlog)对净空高波动名的书偏乐观(凸性项), 不得作为宽书净额口径; meta(Σ简单, 窗口前移一根 bar)对书级数字的影响 = 1hsim−meta 列"}
json.dump(R, open(OUT_JSON, "w"), indent=1, ensure_ascii=False, default=lambda o: bool(o) if isinstance(o, np.bool_) else (float(o) if isinstance(o, np.floating) else (int(o) if isinstance(o, np.integer) else str(o))))
log("DONE", OUT_JSON, R["verdict"])
