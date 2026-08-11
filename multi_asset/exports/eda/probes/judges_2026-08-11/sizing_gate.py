"""★ 新装置: 「排序 vs 定量」增量分解门 —— 补上现有门看不见的那条通道。

动机(今天实测, 非推测): C1(原始 basis) 增量 rank-IC = +0.00008(CI 跨零 ⇒ 等于零),
却带来 +0.053 累计毛额。机制: rank-IC 对名字【等权】, 而 P&L 按【仓位】加权
⇒ 一个因子可以不改排序只改幅度。现有三关全部只看排序与净额, 没有把这条通道单列。

★ 分解构造(逐锚, 两本书都是单位 L1 gross):
  w0 = 基线书, w1 = 并入候选后的书。把每个 w 拆成 (符号, 排序, 幅度剖面):
    w_ORD  = 取 w1 的【排序】, 配 w0 的【幅度剖面】(把 w0 的排序后幅度按 |w1| 的秩重新指派)
    w_SIZE = 取 w0 的【排序】, 配 w1 的【幅度剖面】
  ⇒ ΔP&L(w_ORD − w0) = 纯排序贡献;  ΔP&L(w_SIZE − w0) = 纯定量贡献。

★ 会红的验证(先跑, 不过就说明装置错了):
  C1 的增益应几乎【全部】落在 SIZE 通道(因为它的 dIC 实测为零)。
  若 C1 的增益落在 ORD 通道 ⇒ 本装置的分解是错的, 结论一律作废。
"""
import sys, json, time, numpy as np, pandas as pd
sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset")
src_txt = open("/mnt/storage/private/work_hsy/probe_artifacts/breadth2.py").read()
exec(src_txt.split('R = {"prereg_sha"')[0])          # 复用 breadth2 的装置与缓存

COSTS = [3.115, 3.63]        # 换装后真实成本 + 旧口径(对照)
OUT = "/mnt/storage/private/work_hsy/probe_artifacts/sizing_gate.json"


def split_ord_size(w0, w1):
    """返回 (w_ORD, w_SIZE), 都保持单位 L1 gross。"""
    a0, a1 = np.abs(w0), np.abs(w1)
    s1 = np.sign(w1)
    r1 = np.argsort(np.argsort(a1))              # |w1| 的秩 (0..n-1)
    r0 = np.argsort(np.argsort(a0))
    prof0 = np.sort(a0)                          # w0 的幅度剖面(升序)
    prof1 = np.sort(a1)
    w_ord = np.sign(w1) * prof0[r1]              # w1 的排序 + w0 的幅度剖面
    w_siz = np.sign(w0) * prof1[r0]              # w0 的排序 + w1 的幅度剖面
    for w in (w_ord, w_siz):
        g = np.abs(w).sum()
        if g > 1e-12:
            w /= g
    return w_ord, w_siz


def book_weights(cand, variant, w_c):
    """逐锚返回单位 gross 的目标权重 (m, w)。"""
    base_w = np.array([LIVE3["king"], LIVE3["s2"], LIVE3["funding"]]) * (1.0 - w_c)
    out = []
    for i in range(len(anchors)):
        m = M[i]
        combo = base_w @ HELD[i]
        if cand:
            combo = combo + w_c * CAND[cand][variant][i]
        shaped = rb_(chain.shape_position(combo[m]), RVOL[i])
        g = float(np.abs(shaped).sum())
        out.append(shaped/g if g > 1e-12 else shaped)
    return out


def rb_(s_, rvol):
    a, l = 0.5, 1.0
    v = np.asarray(rvol, float); fin = np.isfinite(v) & (v > 0)
    if not fin.any():
        return s_
    med = float(np.median(v[fin]))
    if med <= 0:
        return s_
    v = np.where(fin, v, med)
    w = np.sign(s_) * np.abs(s_) ** a / np.power(v/med, l)
    return w - w.mean()


def pnl_turn(W):
    prev = np.zeros(N); p = np.zeros(len(anchors)); t = np.zeros(len(anchors))
    for i, w in enumerate(W):
        m = M[i]; r = RET[i]; ok = np.isfinite(r)
        p[i] = float(np.nansum(w[ok]*r[ok]))
        full = np.zeros(N); full[m] = w
        t[i] = 0.0 if i == 0 else float(np.abs(full-prev).sum())
        prev = full
    return p, t


def sh(p, t, c):
    return RF._dsharpe(pd.DataFrame({"day": DAY, "n": p - t*c*1e-4}).groupby("day").n.sum().values)


t0 = time.time()
W0 = book_weights(None, "real", 0.0)
p0, t0_ = pnl_turn(W0)
R = {"note": "ORD/SIZE 分解; 验证臂 = C1(dIC 实测为零, 增益应全落 SIZE)", "arms": {}}
print(f"基线 累计毛额 {p0.sum():+.4f}  " + "  ".join(f"Sh@{c} {sh(p0,t0_,c):+.4f}" for c in COSTS), flush=True)
print("\n臂          通道      Δ累计毛额   " + "  ".join(f"ΔSh@{c}" for c in COSTS))
print("-"*66)
for cand in ["C1", "C2"]:
    for wc in [0.05, 0.10]:
        W1 = book_weights(cand, "real", wc)
        p1, t1 = pnl_turn(W1)
        Wo, Ws = [], []
        for w0, w1 in zip(W0, W1):
            a, b = split_ord_size(w0, w1); Wo.append(a); Ws.append(b)
        po, to = pnl_turn(Wo); ps, ts = pnl_turn(Ws)
        row = {}
        for tag, (p_, t_) in [("FULL", (p1, t1)), ("ORD", (po, to)), ("SIZE", (ps, ts))]:
            row[tag] = {"d_gross": round(float(p_.sum()-p0.sum()), 5),
                        **{f"dSh@{c}": round(sh(p_, t_, c)-sh(p0, t0_, c), 4) for c in COSTS}}
            print(f"{cand} w={wc:.2f} {tag:6s} {p_.sum()-p0.sum():+11.5f}   " +
                  "  ".join(f"{sh(p_,t_,c)-sh(p0,t0_,c):+8.4f}" for c in COSTS), flush=True)
        R["arms"][f"{cand}_w{wc}"] = row
        print()

c1 = R["arms"]["C1_w0.1"]
share = c1["SIZE"]["d_gross"] / max(abs(c1["ORD"]["d_gross"]) + abs(c1["SIZE"]["d_gross"]), 1e-9)
print(f"★ 会红的验证: C1(dIC≈0) 的增益里 SIZE 通道占比 = {share:.1%}")
print(f"   判读: 应【接近 1】。若 ORD 通道占大头 ⇒ 本装置分解错误, 全部结论作废。")
R["validation_C1_size_share"] = round(float(share), 4)
json.dump(R, open(OUT, "w"), indent=1)
print(f"\n[done] {time.time()-t0:.0f}s -> {OUT}\nSIZING_DONE")
