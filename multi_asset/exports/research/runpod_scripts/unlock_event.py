"""解锁事件窗研究 —— 用【对的问题形式】重问一次 #63 判负的那条轨。

★ 为什么重问: #63 的判负原文自述三条限制 ——「覆盖 25% + 视界严重错配(月度事件 vs 4h 目标)
  + **未做事件窗研究(那是另一个问题)**」, 且三个特征 G1 **符号全对**(零假设 1/8)。
★ 结构论据(今日定量): 最锐的 ul_next7/ul_past7 只在 **2.28%** 的格上非零。
  而 #21/#63 用的是逐锚等权、要求全宇宙稠密的 4h 增量门 —— 今日 C2 的 dIC 分辨率是 ±1.8e-4,
  一个 2% 稀疏因子的书级 dIC 大概率在此之下 ⇒ **那个门按构造拒绝这一类, 与它有没有 alpha 无关。**

★ 判据(写死于跑之前):
  主判 : [0,+7d] 累计【横截面去均值】收益 < 0 (供给压力机制), 且事件聚类 bootstrap CI95 上界 < 0
  对侧 : 安慰剂(同符号、随机时点、避开任何真事件 ±14d, 5 个固定种子)同窗累计 |·| < 真实的一半
  副读 : [-7d,0] 前置窗(预期) 与 [+7d,+14d] 后窗(是否反转)
  必报 : 事件期格占比 + 只在事件窗内交易的 sleeve 的毛夏普与换手(可交易性)
  ★会红: 若 [0,+7d] 为【正】⇒ 供给压力机制被证伪, 整条轨作废。**不得改口径去找一个正的窗。**
"""
import numpy as np, json, time

t0 = time.time()
U = np.load("/workspace/data/unlocks_hourly.npz", allow_pickle=True)
P = np.load("/workspace/data/wide_dl_pm32_hz.npz", allow_pickle=True)
feats = [str(x) for x in U["feats"]]
assert U["ts"].shape == P["ts"].shape and (U["ts"] == P["ts"]).all(), "时间网格不对齐"
usym = [str(x) for x in U["symbols"]]; psym = [str(x) for x in P["symbols"]]
assert usym == psym, "符号网格不对齐"
X = U["X"]; ts = U["ts"]
past7 = X[:, :, feats.index("ul_past7")]
Y4 = P["Y4"].astype(np.float64); MEM = P["MEMBER110"]; CL = P["CL4"]
T, N = Y4.shape
print(f"[A] 网格 {T}×{N} 对齐 ✓  {time.time()-t0:.0f}s", flush=True)

# 横截面去均值的异常收益(市场中性), 只在 member&CL&finite 上定义
AB = np.full((T, N), np.nan)
ok = MEM & CL & np.isfinite(Y4)
for t in np.where(ok.any(1))[0]:
    b = np.where(ok[t])[0]
    if b.size >= 5:
        AB[t, b] = Y4[t, b] - Y4[t, b].mean()
print(f"[A] 异常收益格 {np.isfinite(AB).mean():.3f}  {time.time()-t0:.0f}s", flush=True)

# 事件 = ul_past7 的上升沿(解锁发生的那一小时)
fin = np.isfinite(past7)
p = np.where(fin, past7, 0.0)
ev = (p[1:] > 0) & (p[:-1] == 0)
ev_t, ev_j = np.where(ev)
ev_t = ev_t + 1
print(f"[A] 原始事件 {len(ev_t)}  覆盖币 {len(set(ev_j.tolist()))}", flush=True)

STEP = 4                      # 4h 步
W = 84                        # ±14 天
offs = np.arange(-W, W + 1)


def profile(E_t, E_j):
    """返回 (offs, 每个 offset 的平均异常收益, 有效样本数)。"""
    acc = np.zeros(len(offs)); cnt = np.zeros(len(offs))
    for t, j in zip(E_t, E_j):
        idx = t + offs * STEP
        m = (idx >= 0) & (idx < T)
        v = AB[idx[m], j]
        g = np.isfinite(v)
        acc[np.where(m)[0][g]] += v[g]
        cnt[np.where(m)[0][g]] += 1
    return acc / np.maximum(cnt, 1), cnt


def cum(mu, lo, hi):
    s = (offs >= lo) & (offs <= hi)
    return float(np.nansum(mu[s]))


keep = np.array([np.isfinite(AB[min(max(t, 0), T-1), j]) for t, j in zip(ev_t, ev_j)])
E_t, E_j = ev_t[keep], ev_j[keep]
print(f"[A] 可评事件 {len(E_t)}(落在 member&CL 上)", flush=True)
mu, cnt = profile(E_t, E_j)

# 安慰剂: 同符号随机时点, 避开任何真事件 ±14d
rng_seeds = [0, 1, 2, 3, 4]
bad = {}
for j in set(E_j.tolist()):
    tt = E_t[E_j == j]
    bad[j] = np.concatenate([np.arange(max(t-W*STEP, 0), min(t+W*STEP, T)) for t in tt]) if len(tt) else np.array([], int)
PL = []
for s in rng_seeds:
    rng = np.random.default_rng(9000 + s)
    pt, pj = [], []
    for j in set(E_j.tolist()):
        n_ = int((E_j == j).sum())
        allowed = np.setdiff1d(np.arange(W*STEP, T - W*STEP), bad[j])
        if allowed.size < n_:
            continue
        pt += rng.choice(allowed, n_, replace=False).tolist(); pj += [j]*n_
    m_, _ = profile(np.array(pt), np.array(pj))
    PL.append(m_)

WIN = {"pre[-7d,0)": (-42, -1), "post[0,+7d]": (0, 42), "late[+7d,+14d]": (43, 84)}
print("\n===== 事件窗累计【横截面去均值】收益 (bps) =====")
print("窗口              真实      安慰剂5种子均值   安慰剂逐种子")
R = {"n_events": int(len(E_t)), "n_symbols": len(set(E_j.tolist())),
     "event_cell_share": float(np.mean(np.abs(p) > 0)), "windows": {}}
for k, (lo, hi) in WIN.items():
    r = cum(mu, lo, hi) * 1e4
    ps = [cum(m_, lo, hi) * 1e4 for m_ in PL]
    R["windows"][k] = {"real_bps": round(r, 2), "placebo_mean_bps": round(float(np.mean(ps)), 2),
                       "placebo_seeds": [round(x, 2) for x in ps]}
    print(f"{k:16s} {r:+9.2f}   {np.mean(ps):+9.2f}      " + " ".join(f"{x:+.2f}" for x in ps), flush=True)

# 事件聚类 bootstrap (按符号重抽)
syms = sorted(set(E_j.tolist()))
rng = np.random.default_rng(7)
boot = []
for _ in range(2000):
    pick = rng.choice(syms, len(syms), replace=True)
    tt = np.concatenate([E_t[E_j == j] for j in pick]); jj = np.concatenate([E_j[E_j == j] for j in pick])
    m_, _ = profile(tt, jj)
    boot.append(cum(m_, 0, 42) * 1e4)
lo_, hi_ = np.percentile(boot, [2.5, 97.5])
R["post_ci95_bps"] = [round(float(lo_), 2), round(float(hi_), 2)]
print(f"\n[0,+7d] 事件聚类 bootstrap CI95 = [{lo_:+.2f}, {hi_:+.2f}] bps")
real_post = R["windows"]["post[0,+7d]"]["real_bps"]
pl_post = R["windows"]["post[0,+7d]"]["placebo_mean_bps"]
g1 = real_post < 0 and hi_ < 0
g2 = abs(pl_post) < abs(real_post) / 2
print(f"主判(<0 且 CI 上界<0): {'PASS' if g1 else 'FAIL'} | 对侧(安慰剂 < 真实一半): {'PASS' if g2 else 'FAIL'}")
R["verdict"] = {"g1_primary": bool(g1), "g2_placebo": bool(g2)}
json.dump(R, open("/workspace/unlock_event.json", "w"), indent=1)
print(f"\n[done] {time.time()-t0:.0f}s\nUNLOCK_DONE")
