"""dlw_targets_ext 平价门 @pod: 重叠锚 vs 旧 dlw_targets.npz(f10 训练唯一真相源, 2026-09-01).
比对: E_ts 交集上 members 逐锚全等 / y4s exact&corr / YRZ corr / qvk corr. corr>=0.999 全过才 PASS.
用法: python3 pod_gate_dlw_ext.py [old_npz] [ext_npz]  (退出码 0/3)
"""
import sys
import numpy as np

OLD = sys.argv[1] if len(sys.argv) > 1 else "/workspace/data/dlw_targets.npz"
EXT = sys.argv[2] if len(sys.argv) > 2 else "/workspace/dlw_ext/data/dlw_targets.npz"
A = np.load(OLD, allow_pickle=True); B = np.load(EXT, allow_pickle=True)
assert [str(s) for s in A["symbols"]] == [str(s) for s in B["symbols"]], "symbols differ"
ta = {int(t): i for i, t in enumerate(A["E_ts"].astype(np.int64))}
pairs = [(ta[int(t)], j) for j, t in enumerate(B["E_ts"].astype(np.int64)) if int(t) in ta]
ia = np.array([p[0] for p in pairs]); ib = np.array([p[1] for p in pairs])
print(f"overlap anchors {len(ia)} / old {len(ta)} / ext {len(B['E_ts'])}", flush=True)
mem_eq = sum(1 for x, y in zip(ia, ib) if np.array_equal(A["members"][x], B["members"][y]))
print(f"members equal {mem_eq}/{len(ia)}", flush=True)
bad = [] if mem_eq == len(ia) else [("members", f"{mem_eq}/{len(ia)}")]
for k in ("y4s", "YRZ", "qvk"):
    va = A[k][ia].astype(np.float64); vb = B[k][ib].astype(np.float64)
    ok = np.isfinite(va) & np.isfinite(vb)
    x, y = va[ok], vb[ok]
    c = float(np.corrcoef(x, y)[0, 1]); exact = float(np.mean(x == y))
    fin_eq = float(np.mean(np.isfinite(va) == np.isfinite(vb)))
    if c < 0.999: bad.append((k, round(c, 6)))
    print(f"{k:5s} corr {c:.6f} exact {exact:.4f} fin_eq {fin_eq:.6f} n {int(ok.sum())}", flush=True)
print("GATE_DLW", "PASS" if not bad else f"FAIL {bad}", flush=True)
sys.exit(0 if not bad else 3)
