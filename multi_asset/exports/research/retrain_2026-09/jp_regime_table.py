"""新书逐 regime 全表 @jpline(执行器口径, 与候选 §2 同轴): 逐年/市场五分位/波动五分位/广度三分位。
输入: w10 NEW9 双种子序列 + B 档 meta(y4 → 市场/波动代理)。R1 闭环数一并打印。"""
import numpy as np, time
PD = "/mnt/storage/private/work_hsy/probe_artifacts"
B = "/mnt/storage/private/work_hsy/pod_backup_2026-08-21"
MT = np.load(f"{B}/wide_fea_hist_meta.npz", allow_pickle=True)
mts = MT["E_ts"].astype(np.int64); y4 = MT["y4"]
mrow = {int(t): i for i, t in enumerate(mts)}
def mkt_vol(ts):
    mk = np.full(len(ts), np.nan); vl = np.full(len(ts), np.nan)
    for p, t in enumerate(ts):
        i = mrow.get(int(t))
        if i is None: continue
        v = y4[i]; v = v[np.isfinite(v)]
        if len(v) > 50: mk[p] = v.mean(); vl[p] = v.std()
    return mk, vl
def load(run):
    z = np.load(f"{PD}/{run}.npz", allow_pickle=True)
    cols = [str(c) for c in z["cols"]]; rec = z["d30_n2_c42_rec"]
    return (rec[:, cols.index("ts")].astype(np.int64),
            rec[:, cols.index("net_ex")].astype(np.float64),
            rec[:, cols.index("nsel")].astype(np.float64))
# R1 闭环
print("== R1 正典 preds 复现(期望 1.681/1.736/1.595)")
for S in (42, 2027, 3037):
    ts, nex, _ = load(f"w10_canonpred_s{S}")
    yrs = np.array([time.gmtime(int(t)).tm_year for t in ts]); s = yrs >= 2023
    r = nex[s]
    print(f"  s{S}: 净/锚 {r.mean():+.3f} bps 夏普 {r.mean()/(r.std()+1e-12)*np.sqrt(6*365):.2f} (n {s.sum()})")
# 新书逐 regime(双种子)
for RUN in ("w10_v2gate_s42_NEW9", "w10_v2gate_s2027_NEW9"):
    ts, nex, nsel = load(RUN)
    yrs = np.array([time.gmtime(int(t)).tm_year for t in ts])
    s23 = yrs >= 2023
    mk, vl = mkt_vol(ts)
    tag = RUN.split("_")[2]
    r = nex[s23]
    print(f"== 新书 {tag}(执行器口径, 2023+ n {s23.sum()}) 全期 净{r.mean():+.3f} 夏普{r.mean()/(r.std()+1e-12)*np.sqrt(6*365):.2f}")
    row = []
    for y in (2023, 2024, 2025, 2026):
        sy = yrs == y
        ry = nex[sy]
        row.append(f"{y}:[{ry.mean():+.2f},{ry.mean()/(ry.std()+1e-12)*np.sqrt(6*365):.2f}]")
    print("  逐年[净,夏普] " + " ".join(row))
    ok = s23 & np.isfinite(mk)
    q = np.quantile(mk[ok], [0.2, 0.4, 0.6, 0.8])
    lab = ["大跌", "跌", "平", "涨", "普涨"]
    out = []
    for i in range(5):
        lo = -np.inf if i == 0 else q[i - 1]; hi = np.inf if i == 4 else q[i]
        s_ = ok & (mk > lo) & (mk <= hi)
        out.append(f"{lab[i]}:{nex[s_].mean():+.2f}")
    print("  市场五分位(由跌到涨) " + " ".join(out))
    qv = np.quantile(vl[ok], [0.2, 0.4, 0.6, 0.8])
    out = []
    for i in range(5):
        lo = -np.inf if i == 0 else qv[i - 1]; hi = np.inf if i == 4 else qv[i]
        s_ = ok & (vl > lo) & (vl <= hi)
        out.append(f"V{i+1}:{nex[s_].mean():+.2f}")
    print("  波动五分位(低→高) " + " ".join(out))
    qb = np.quantile(nsel[s23], [1/3, 2/3])
    for tag2, s_ in (("窄", s23 & (nsel <= qb[0])), ("中", s23 & (nsel > qb[0]) & (nsel < qb[1])), ("宽", s23 & (nsel >= qb[1]))):
        print(f"  广度{tag2}档 净 {nex[s_].mean():+.2f} bps/锚 (n {int(s_.sum())})")
print("REGIME_TABLE_DONE")
