"""N7 —— meta-data(hour-of-day / day-of-week)有没有可利用的横截面结构。

★ 为什么它值得测: 若某些锚点系统性更好, "只在好锚点交易"同时【降换手】与【提 IC】——
   是我已建立的成本轴上唯一的双赢形态。若无结构, 一次便宜的关闭。
★ 判读预写: 组间差异必须超过【同形状置换零假设】(打乱 hour 标签 1000 次的最大|t|), 否则是
   多重比较的产物 —— 6 个 hour × 7 个 weekday = 13 个组, 单看 t>2 必然有假阳性。
"""
import sys, json
MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
sys.path.insert(0, MA)
import numpy as np, datetime as dt
from scipy.stats import rankdata

z = np.load(f"{MA}/exports/wide_dl_full_corrfund_causal_0731.npz", allow_pickle=True)
ts = z["ts"].astype(np.int64); ts_s = ts // 1000 if int(ts[0]) > 10**11 else ts
Y4 = z["Y4"].astype(np.float64); CL4 = z["CL4"].astype(bool); MEM = z["MEMBER110"].astype(bool)
K = np.load("/tmp/king_pred_newgen.npz", allow_pickle=True)
S = np.load("/tmp/s2_pred_newgen.npz", allow_pickle=True)
kp = K["king_pred"]; sp = S[[f for f in S.files if f != "ts"][0]]
kpos = {int(t): i for i, t in enumerate(K["ts"])}
NR = kp.shape[0]


def rank_c(x):
    o = np.zeros_like(x, float); m = np.isfinite(x)
    if m.sum() < 3:
        return o
    r = rankdata(x[m]); o[m] = 2 * (r - 1) / (len(r) - 1) - 1
    return o


rows, ics, hours, wdays = [], [], [], []
for i in range(min(NR, len(ts))):
    t = int(ts[i])
    if t not in kpos:
        continue
    m = MEM[i] & CL4[i] & np.isfinite(Y4[i])
    if m.sum() < 20:
        continue
    sc = .5952 * rank_c(np.where(m, kp[kpos[t]], np.nan)) + .2024 * rank_c(np.where(m, sp[kpos[t]], np.nan))
    v = m & np.isfinite(sc)
    if v.sum() < 20 or np.std(sc[v]) < 1e-12:
        continue
    c = np.corrcoef(rankdata(sc[v]), rankdata(Y4[i, v]))[0, 1]
    if not np.isfinite(c):
        continue
    d = dt.datetime.utcfromtimestamp(int(ts_s[i]))
    ics.append(c); hours.append(d.hour); wdays.append(d.weekday()); rows.append(i)

ics = np.array(ics); hours = np.array(hours); wdays = np.array(wdays)
print(f"[样本] {len(ics)} 个干净锚点, 总体 mean rank-IC = {ics.mean():+.5f} "
      f"(SE {ics.std(ddof=1)/np.sqrt(len(ics)):.5f}, t={ics.mean()/(ics.std(ddof=1)/np.sqrt(len(ics))):.2f})",
      flush=True)


def grp(lab, name):
    out = []
    for g in sorted(set(lab)):
        x = ics[lab == g]
        se = x.std(ddof=1) / np.sqrt(len(x)) if len(x) > 2 else np.nan
        out.append((int(g), len(x), float(x.mean()), float(x.mean() / se) if se and se > 0 else np.nan))
    print(f"\n[{name}]  组   n     mean IC    t", flush=True)
    for g, n, mu, t in out:
        print(f"          {g:3d}  {n:5d}  {mu:+.5f}  {t:+6.2f}", flush=True)
    return out


gh = grp(hours, "hour-of-day (UTC)")
gw = grp(wdays, "weekday (0=Mon)")

# ★ 同形状置换零假设: 打乱标签 1000 次, 记录【最大|t|】的分布
rng = np.random.default_rng(20260806)
def null_max_t(lab, n_perm=1000):
    mx = []
    for _ in range(n_perm):
        p = rng.permutation(lab)
        ts_ = []
        for g in sorted(set(lab)):
            x = ics[p == g]
            se = x.std(ddof=1) / np.sqrt(len(x)) if len(x) > 2 else np.nan
            if se and se > 0:
                ts_.append(abs(x.mean() / se))
        mx.append(max(ts_) if ts_ else 0.0)
    return np.array(mx)


for lab, name, g in ((hours, "hour", gh), (wdays, "weekday", gw)):
    obs = max(abs(t) for _, _, _, t in g if np.isfinite(t))
    nul = null_max_t(lab)
    p = float((nul >= obs).mean())
    print(f"\n★ [{name}] 观测最大|t| = {obs:.2f} | 置换零假设 最大|t| 的 95 分位 = "
          f"{np.percentile(nul,95):.2f} | p = {p:.3f} ⇒ "
          f"{'有真实结构' if p < 0.05 else '与多重比较不可区分 ⇒ 无结构'}", flush=True)

print("\nJSON_BEGIN")
print(json.dumps({"n": int(len(ics)), "overall_ic": float(ics.mean()),
                  "hour": [[a, b, c, d] for a, b, c, d in gh],
                  "weekday": [[a, b, c, d] for a, b, c, d in gw]}))
print("JSON_END")
