"""W2b · 同一时钟收益立方体构建器 @jpline(2026-08-22, Session 6737834a-W2b)。

为什么需要它(实测, w2b_offset.py): 在役面板行标 T 的 Y4 = T+1h→T+5h(与宽 y4@T−1h 相关 0.982, @T 仅 0.703),
且 king/s2 预测只存在于行标 00/04/08/12/16/20 的行 ⇒ 在役回放族(9821 锚)的决策/持仓时钟 = 行标 +1h;
宽书 E 网格 = 名义 T(特征用 <T 的 5m bar, y4 = T→T+4h)。W2 一审按"行标 == E_ts"对齐 ⇒ 两序列相差 1h 相位。
合成一本书必须一个时钟: 取【在役时钟】(行标 T 的决策点 = T+1h; 宽部分用 E=T 的特征, 陈旧 1h, 因果无前视),
全部 829 名的逐名收益统一为 1h bar close[T+4h]/close[T](= T+1h→T+5h), 来源 data.binance.vision 1h 月度 zip(w3lane/wide1h_csv, jp_wide1h_pull.py)。

输出 probe_artifacts/w2b_ret_cube.npz: ts(9821, 秒, = w2_live_series.ts), symbols(829, = 宽 v2 面板), R_live(9821×829 f32, 在役时钟 4h 对数收益),
R_wide(同维, 宽时钟 T→T+4h, 仅作与 meta y4 的对账), 以及校验统计(json 字符串)。
校验(脚本内断言/打印): R_live vs 在役面板 Y4(140 名) 相关中位 ≥0.99; R_wide vs meta y4(829 名) 相关中位 ≥0.99; 覆盖率按宽书 gross 逐年报告。
只读公共数据与既有产物; 不碰 share / 实盘仓。
"""
import os, sys, io, json, time, zipfile, hashlib, numpy as np
from multiprocessing import Pool
PD = "/mnt/storage/private/work_hsy/probe_artifacts"; B = "/mnt/storage/private/work_hsy/pod_backup_2026-08-21"
CSV = "/mnt/storage/private/work_hsy/w3lane/wide1h_csv"
OUT = f"{PD}/w2b_ret_cube.npz"
t0 = time.time()
L = np.load(f"{PD}/w2_live_series.npz", allow_pickle=True); ats = L["ts"].astype(np.int64); lsym = [str(s) for s in L["symbols"]]
PW = np.load(f"{B}/wide_panel_4h_hist_v2.npz", allow_pickle=True); WSYM = [str(s) for s in PW["symbols"]]; NW = len(WSYM)
n = len(ats); print("anchors", n, "symbols", NW, flush=True)
T_need = {"c0": ats, "c4": ats + 4 * 3600, "cm1": ats - 3600, "c3": ats + 3 * 3600}

def parse_sym(s):
    d = f"{CSV}/{s}"
    if not os.path.isdir(d): return s, None, 0
    ot = []; cl = []; nf = 0
    for f in sorted(os.listdir(d)):
        if not f.endswith(".zip"): continue
        p = f"{d}/{f}"
        if os.path.getsize(p) < 100: continue
        try:
            z = zipfile.ZipFile(p); nm = z.namelist()[0]; raw = z.read(nm).decode("utf-8", "ignore")
        except Exception:
            continue
        nf += 1
        for line in raw.split("\n"):
            if not line or line.startswith("open_time"): continue
            parts = line.split(",")
            try:
                ot.append(int(parts[0]) // 1000); cl.append(float(parts[4]))
            except Exception:
                continue
    if not ot: return s, None, nf
    ot = np.array(ot, dtype=np.int64); cl = np.array(cl, dtype=np.float64)
    # some 2025+ files carry microsecond timestamps (16 digits) — normalise
    big = ot > 10 ** 11
    if big.any(): ot = np.where(big, ot // 1000, ot)
    o = np.argsort(ot); ot = ot[o]; cl = cl[o]
    def at(ts):
        idx = np.searchsorted(ot, ts); ok = (idx < len(ot)); idx2 = np.where(ok, idx, 0); hit = ok & (ot[idx2] == ts)
        return np.where(hit, cl[idx2], np.nan)
    c0, c4, cm1, c3 = at(T_need["c0"]), at(T_need["c4"]), at(T_need["cm1"]), at(T_need["c3"])
    with np.errstate(all="ignore"):
        rl = np.log(c4 / c0); rw = np.log(c3 / cm1)
    rl[~(np.isfinite(rl) & (c0 > 0) & (c4 > 0))] = np.nan; rw[~(np.isfinite(rw) & (cm1 > 0) & (c3 > 0))] = np.nan
    return s, (rl.astype(np.float32), rw.astype(np.float32)), nf

if __name__ == "__main__":
    R_live = np.full((n, NW), np.nan, np.float32); R_wide = np.full((n, NW), np.nan, np.float32); nfiles = {}
    with Pool(24) as pool:
        for k, (s, res, nf) in enumerate(pool.imap_unordered(parse_sym, WSYM, chunksize=4)):
            nfiles[s] = nf
            if res is not None:
                j = WSYM.index(s); R_live[:, j] = res[0]; R_wide[:, j] = res[1]
            if k % 100 == 0: print("parsed", k, "/", NW, round(time.time() - t0), "s", flush=True)
    print("parse done", round(time.time() - t0), "s; symbols with data", sum(1 for s in WSYM if nfiles.get(s, 0) > 0), flush=True)
    # ---- validation 1: R_live vs live panel Y4 on the 140 live names (same source granularity: 1h klines) ----
    sys.path.insert(0, PD); MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
    sys.path.insert(0, MA); sys.path.insert(0, MA + "/engine/live"); sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset"); sys.path.insert(0, PD)
    import engine.replay_fullhist as RF
    src = RF.get_src(None, f"{PD}/king_pred_newgen.npz", f"{PD}/s2_pred_newgen.npz")
    a, yr = RF._all_anchors(src); assert len(a) == n
    lmap = np.array([WSYM.index(s) for s in lsym])
    cors = []; dabs = []; cover_live = []
    for i in range(0, n, 5):
        yl = src.Y4[int(a[i])]; yw = R_live[i, lmap]; ok = np.isfinite(yl) & np.isfinite(yw)
        cover_live.append(np.isfinite(yw[np.isfinite(yl)]).mean() if np.isfinite(yl).any() else np.nan)
        if ok.sum() > 20: cors.append(np.corrcoef(yl[ok], yw[ok])[0, 1]); dabs.append(np.abs(yl[ok] - yw[ok]).mean() * 1e4)
    v1 = {"corr_median": float(np.median(cors)), "corr_p5": float(np.percentile(cors, 5)), "mean_abs_diff_bps": float(np.mean(dabs)), "live_names_covered_frac": float(np.nanmean(cover_live))}
    print("VALID1 R_live vs live Y4:", v1, flush=True)
    # ---- validation 2: R_wide vs meta y4 (wide clock) on all 829 ----
    MT = np.load(f"{B}/wide_fea_hist_meta.npz", allow_pickle=True); E_ts = MT["E_ts"].astype(np.int64); y4 = MT["y4"]; members = MT["members"]
    wpos = {int(t): j for j, t in enumerate(E_ts)}; cors = []; dabs = []; covw = []
    for i in range(0, n, 5):
        j = wpos[int(ats[i])]; m = members[j]; yw = y4[j, m]; rw = R_wide[i, m]; ok = np.isfinite(yw) & np.isfinite(rw)
        covw.append(np.isfinite(rw[np.isfinite(yw)]).mean())
        if ok.sum() > 20: cors.append(np.corrcoef(yw[ok], rw[ok])[0, 1]); dabs.append(np.abs(yw[ok] - rw[ok]).mean() * 1e4)
    v2 = {"corr_median": float(np.median(cors)), "corr_p5": float(np.percentile(cors, 5)), "mean_abs_diff_bps": float(np.mean(dabs)), "wide_members_covered_frac": float(np.mean(covw))}
    print("VALID2 R_wide vs meta y4:", v2, flush=True)
    # ---- coverage by wide-book gross (W2 d30 weights) per year ----
    Wd = np.load(f"{PD}/w2_wide_series.npz", allow_pickle=True); cols = [str(c) for c in Wd["cols"]]; RW = Wd["d30_n2_c42_rec"]; WW = Wd["d30_n2_c42_W"]
    wts = RW[:, 0].astype(np.int64); wp = {int(t): j for j, t in enumerate(wts)}
    yrs = np.array([time.gmtime(int(t)).tm_year for t in ats]); cov_by_year = {}
    for y in sorted(set(yrs.tolist())):
        rows = np.where(yrs == y)[0][::3]; c = []
        for i in rows:
            w = np.abs(WW[wp[int(ats[i])]]).astype(float); g = w.sum()
            if g > 0: c.append((w * np.isfinite(R_live[i])).sum() / g)
        cov_by_year[int(y)] = {"mean": round(float(np.mean(c)), 4), "min": round(float(np.min(c)), 4)}
    print("coverage of wide-book gross by R_live, by year:", cov_by_year, flush=True)
    # ---- manifest sha of input zips ----
    h = hashlib.sha256()
    for s in WSYM:
        d = f"{CSV}/{s}"
        if os.path.isdir(d):
            for f in sorted(os.listdir(d)):
                h.update(f"{s}/{f}:{os.path.getsize(os.path.join(d, f))}\n".encode())
    manifest_sha = h.hexdigest()
    meta = {"created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "session": "6737834a-W2b", "n_anchors": int(n), "n_symbols": int(NW),
            "symbols_with_data": int(sum(1 for s in WSYM if nfiles.get(s, 0) > 0)), "zip_manifest_sha256": manifest_sha,
            "definition": {"R_live": "log(close_1h[T+4h]/close_1h[T]) = price T+1h -> T+5h (在役时钟, 行标 T 的决策点 T+1h)", "R_wide": "log(close_1h[T+3h]/close_1h[T-1h]) = price T -> T+4h (宽时钟)"},
            "valid_R_live_vs_live_Y4_140": v1, "valid_R_wide_vs_meta_y4_829": v2, "coverage_wide_gross_by_year": cov_by_year}
    np.savez_compressed(OUT, ts=ats, symbols=np.array(WSYM), R_live=R_live, R_wide=R_wide, meta=json.dumps(meta, ensure_ascii=False))
    json.dump(meta, open(f"{PD}/w2b_ret_cube_meta.json", "w"), indent=1, ensure_ascii=False)
    print("DONE", OUT, round(time.time() - t0), "s", flush=True)
