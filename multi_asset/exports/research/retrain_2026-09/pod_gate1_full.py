"""门① 全列版 @pod(RUNBOOK step2 冻结口径: 重叠锚 13 kline 因子 + fund 全列 corr>=0.999).
比 pod_panel_ext.py 内建自检(7列)更严: 枚举两面板全部 f_* 公共列, 各报 corr/exact/n.
2026-09-01 首跑抓住 ema_v1 0.9796 / ema_v2 0.9975(zip interval 缺失 → normfix 递归污染)。
用法: python3 pod_gate1_full.py  (退出码 0=PASS, 3=FAIL)
"""
import sys
import numpy as np

A = np.load("/workspace/data/wide_panel_4h_v1.npz", allow_pickle=True)
B = np.load("/workspace/data/wide_panel_4h_v2ext.npz", allow_pickle=True)
fac = [k for k in sorted(set(A.files) & set(B.files)) if k.startswith("f_")]
ta = {int(t): i for i, t in enumerate(A["ts"].astype(np.int64))}
tb = B["ts"].astype(np.int64)
common = [(ta[int(t)], j) for j, t in enumerate(tb) if int(t) in ta]
ia = np.array([x[0] for x in common]); ib = np.array([x[1] for x in common])
assert list(A["symbols"]) == list(B["symbols"]), "symbol order differs"
print(f"overlap anchors {len(ia)} factor cols {len(fac)}", flush=True)
bad = []
for k in fac:
    va = A[k][ia].astype(np.float64); vb = B[k][ib].astype(np.float64)
    ok = np.isfinite(va) & np.isfinite(vb)
    n = int(ok.sum())
    if n < 1000:
        bad.append((k, f"n={n}")); print(f"{k:20s} n={n} INSUFF", flush=True); continue
    x = va[ok]; y = vb[ok]
    c = float(np.corrcoef(x, y)[0, 1]) if x.std() > 0 else (1.0 if np.allclose(x, y) else 0.0)
    exact = float(np.mean(x == y))
    if c < 0.999: bad.append((k, round(c, 6)))
    print(f"{k:20s} corr {c:.6f} exact {exact:.4f} n {n} {'OK' if c >= 0.999 else 'FAIL'}", flush=True)
print("GATE1_FULL", "PASS" if not bad else f"FAIL {bad}", flush=True)
sys.exit(0 if not bad else 3)
