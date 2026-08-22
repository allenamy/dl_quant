"""W2b 口径发现一(在役面板行标 vs 宽 E 网格 1h 相位)的检查脚本 @jpline; 数字见 RESULT_two_book_second_read_2026-08-22.md §2。只读。"""
import sys, json, time, numpy as np
PD = "/mnt/storage/private/work_hsy/probe_artifacts"; sys.path.insert(0, PD)
MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
sys.path.insert(0, MA); sys.path.insert(0, MA + "/engine/live"); sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset"); sys.path.insert(0, PD)
import engine.replay_fullhist as RF
B = "/mnt/storage/private/work_hsy/pod_backup_2026-08-21"
src = RF.get_src(None, f"{PD}/king_pred_newgen.npz", f"{PD}/s2_pred_newgen.npz")
a, yr = RF._all_anchors(src); N = src.N; n = len(a); SYMS = [str(s) for s in src.symbols]
ts_all = np.asarray(src.ts); tss = ts_all // 1000 if (ts_all[1] - ts_all[0]) >= 3600 * 1000 else ts_all
print("panel ts[0..3]", [time.strftime("%Y-%m-%d %H:%M", time.gmtime(int(x))) for x in tss[:3]], "step s", tss[1]-tss[0], "T", len(tss))
ats = np.array([int(tss[int(t)]) for t in a], dtype=np.int64)
print("anchor rows ts hour histogram", np.unique(np.array([time.gmtime(int(x)).tm_hour for x in ats]), return_counts=True))
MT = np.load(f"{B}/wide_fea_hist_meta.npz", allow_pickle=True)
E_ts = MT["E_ts"].astype(np.int64); y4 = MT["y4"]
print("wide E_ts hour histogram", np.unique(np.array([time.gmtime(int(x)).tm_hour for x in E_ts]), return_counts=True))
WSYM = [str(s) for s in np.load(f"{B}/wide_panel_4h_hist_v2.npz", allow_pickle=True)["symbols"]]
widx = {s: i for i, s in enumerate(WSYM)}; lmap = np.array([widx.get(s, -1) for s in SYMS])
wpos = {int(t): j for j, t in enumerate(E_ts)}
common = [(i, wpos[int(t)]) for i, t in enumerate(ats) if int(t) in wpos]
for k in (-2, -1, 0, 1, 2):
    cors = []; dabs = []
    for (i, j) in common[::7]:
        ti = int(a[i]) + k
        if ti < 0 or ti >= src.Y4.shape[0]: continue
        yl = src.Y4[ti]; yw = y4[j, lmap]; ok = np.isfinite(yl) & np.isfinite(yw)
        if ok.sum() > 20: cors.append(np.corrcoef(yl[ok], yw[ok])[0, 1]); dabs.append(np.abs(yl[ok] - yw[ok]).mean() * 1e4)
    print(f"offset k={k:+d}h: corr median {np.median(cors):.4f} mean {np.mean(cors):.4f} | mean|diff| {np.mean(dabs):.2f} bps")
# Y1 cumulative check: sum Y1[ti+k..ti+k+3] vs wide y4
for k in (-1, 0):
    cors = []
    for (i, j) in common[::7]:
        ti = int(a[i]) + k
        yl = np.nansum(src.Y1[ti:ti+4], 0); yw = y4[j, lmap]; ok = np.isfinite(yw) & np.isfinite(src.Y1[ti:ti+4]).all(0)
        if ok.sum() > 20: cors.append(np.corrcoef(yl[ok], yw[ok])[0, 1])
    print(f"sum Y1 k={k:+d}: corr median {np.median(cors):.4f}")
# king/s2 availability on rows ts%4h==3h (nominal-1h rows) vs ==0
rows3 = [int(t) - 1 for t in a]
fin0 = np.mean([np.isfinite(src.king[int(t)][src.member[int(t)]]).mean() for t in a[::50]])
fin3 = np.mean([np.isfinite(src.king[r][src.member[r]]).mean() for r in rows3[::50]])
print("king finite frac on CL4 rows", fin0, "on rows-1h", fin3)
s0 = np.mean([np.isfinite(src.s2[int(t)][src.member[int(t)]]).mean() for t in a[::50]]); s3 = np.mean([np.isfinite(src.s2[r][src.member[r]]).mean() for r in rows3[::50]])
print("s2 finite frac CL4 rows", s0, "rows-1h", s3)
print("CL4 true frac by hour:", {h: float(np.mean(src.CL4[np.array([time.gmtime(int(x)).tm_hour == h for x in tss])].any(1))) for h in range(0, 8)})
