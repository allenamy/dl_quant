"""开放问题探针: 毛额涨而排序不涨 —— 是不是【集中度】在动?

事实(两次独立出现, 均未解释):
  · C1 (原始 basis): Δ毛额 +0.053/+0.100, 而 dIC 在三个口径下全零, Δ换手 ≈ 0
  · C2 高权重端 w=0.30: dIC **转负** (−0.00187) 而 Δ毛额仍 +0.32
已排除: 幅度剖面(E75) / 换手 / 排序集中在尾部(E78-前身)。

★ 假说: 单位 L1 gross 下 Σw·r 上升而秩相关不变 ⇒ 变的只能是 |w| 的【形状】= 集中度。
  与已入档的 N8/N9 一致(「移除慢书主导方向 ⇒ 毛夏普跌」「集中即 alpha, 不是缺陷」)。

★ 预言(写死于跑之前):
  P-A: 集中度(N_eff 下降 / L2-over-L1 上升)随 w 单调变化
  P-B: 沿剂量曲线 corr(Δ毛额, Δ集中度) 高且同向(|r| > 0.8)
  ★会红: 若集中度不动或与毛额反向 ⇒ 本机制亦错, 事实继续悬置, **不换第五个解释**。
"""
import sys, json, time, numpy as np, pandas as pd
sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset")
exec(open("/mnt/storage/private/work_hsy/probe_artifacts/breadth2.py").read().split('R = {"prereg_sha"')[0])

WS = [0.0, 0.02, 0.05, 0.10, 0.15, 0.20, 0.30]
OUT = "/mnt/storage/private/work_hsy/probe_artifacts/conc_probe.json"


def shape_stats(cand, w_c):
    """返回 (累计毛额, 平均 N_eff, 平均 L2/L1, 平均 max|w|)。书均为单位 L1 gross。"""
    base_w = np.array([LIVE3["king"], LIVE3["s2"], LIVE3["funding"]]) * (1.0 - w_c)
    g_tot = 0.0; neff = []; l2l1 = []; mx = []
    for i in range(len(anchors)):
        m = M[i]
        combo = base_w @ HELD[i]
        if cand and w_c:
            combo = combo + w_c * CAND[cand]["real"][i]
        shaped = rb(chain.shape_position(combo[m]), RVOL[i])
        g = float(np.abs(shaped).sum())
        if g <= 1e-12:
            continue
        w = shaped / g
        a = np.abs(w)
        neff.append(1.0/float((a**2).sum()))          # 有效名字数(越小越集中)
        l2l1.append(float(np.sqrt((a**2).sum())))     # L2/L1(L1=1) 越大越集中
        mx.append(float(a.max()))
        r = RET[i]; ok = np.isfinite(r)
        g_tot += float(np.nansum(w[ok]*r[ok]))
    return g_tot, float(np.mean(neff)), float(np.mean(l2l1)), float(np.mean(mx))


t0 = time.time()
R = {"weights": WS, "arms": {}}
print("cand  w      累计毛额     N_eff     L2/L1    max|w|      Δ毛额     ΔN_eff   ΔL2/L1")
print("-"*88)
base = None
for cand in ["C1", "C2"]:
    rows = []
    for w in WS:
        g, ne, ll, mm = shape_stats(cand if w else None, w)
        if w == 0.0 and base is None:
            base = (g, ne, ll, mm)
        rows.append((w, g, ne, ll, mm))
        b = base
        print(f"{cand:4s} {w:.2f} {g:+11.5f} {ne:9.3f} {ll:9.5f} {mm:8.5f}  "
              f"{g-b[0]:+10.5f} {ne-b[1]:+9.3f} {ll-b[2]:+9.5f}", flush=True)
    R["arms"][cand] = [{"w": w, "gross": round(g, 5), "n_eff": round(ne, 4),
                        "l2_over_l1": round(ll, 6), "max_w": round(mm, 6)} for w, g, ne, ll, mm in rows]
    print()

print("===== 判据 =====")
for cand in ["C1", "C2"]:
    a = R["arms"][cand]
    dg = np.array([x["gross"] for x in a]) - a[0]["gross"]
    dl = np.array([x["l2_over_l1"] for x in a]) - a[0]["l2_over_l1"]
    dn = np.array([x["n_eff"] for x in a]) - a[0]["n_eff"]
    mono_l = all(dl[i] <= dl[i+1] for i in range(len(dl)-1)) or all(dl[i] >= dl[i+1] for i in range(len(dl)-1))
    r_gl = float(np.corrcoef(dg[1:], dl[1:])[0, 1]) if len(dg) > 3 else np.nan
    print(f"  {cand}: ΔL2/L1 单调={mono_l}  ΔN_eff 端点 {dn[-1]:+.3f}  "
          f"corr(Δ毛额, ΔL2/L1) = {r_gl:+.4f}  ⇒ P-B {'PASS' if abs(r_gl) > 0.8 else 'FAIL'}")
    R["arms"][cand + "_verdict"] = {"mono_l2l1": bool(mono_l), "corr_gross_conc": round(r_gl, 4),
                                    "dn_eff_endpoint": round(float(dn[-1]), 4)}
print("\n★会红: 若集中度不动或与毛额反向 ⇒ 本机制亦错, 事实继续悬置, 不换第五个解释。")
json.dump(R, open(OUT, "w"), indent=1)
print(f"\n[done] {time.time()-t0:.0f}s -> {OUT}\nCONC_DONE")
