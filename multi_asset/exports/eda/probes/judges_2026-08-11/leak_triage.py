"""lgbm_vs_dl 0.083 读数的泄漏验尸: ①通道名单 ②逐通道 lag0 与未来 Y4 的 pooled corr
(泄漏通道会呈现远超其余的同期-未来相关) ③面板文件身份。"""
import sys, os
MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
sys.path.insert(0, MA); sys.path.insert(0, MA + "/engine/live")
sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset")
PD = "/mnt/storage/private/work_hsy/probe_artifacts"; sys.path.insert(0, PD)
import numpy as np
import engine.replay_fullhist as RF
import inspect
src = RF.get_src(None, f"{PD}/king_pred_newgen.npz", f"{PD}/s2_pred_newgen.npz")
print("面板路径解析:", [l.strip() for l in inspect.getsource(RF.get_src).splitlines() if "npz" in l.lower() or "path" in l.lower()][:6])
for attr in ("panel_path", "path", "src_path"):
    if hasattr(src, attr): print(attr, "=", getattr(src, attr))
print("通道名单:", list(src.ch))
a, yr = RF._all_anchors(src)
sub = a[::4]
cors = []
for c in range(src.CH.shape[2]):
    xs, ys = [], []
    for t in sub:
        ti = int(t); m = np.asarray(src.tradeable(ti))
        if m.dtype == bool: m = np.where(m)[0]
        x = src.CH[ti, m, c].astype(float); y = src.Y4[ti, m].astype(float)
        ok = np.isfinite(x) & np.isfinite(y)
        xs.append(x[ok]); ys.append(y[ok])
    X = np.concatenate(xs); Yv = np.concatenate(ys)
    cors.append((abs(float(np.corrcoef(X, Yv)[0, 1])), src.ch[c], c))
cors.sort(reverse=True)
print("\n|corr(通道_t, Y4未来)| 前8(泄漏通道会一骑绝尘):")
for v, nm, c in cors[:8]: print(f"  ch{c:2d} {nm}: {v:.4f}")
print("中位:", np.median([v for v,_,_ in cors]).round(4))
print("TRIAGE_DONE")
