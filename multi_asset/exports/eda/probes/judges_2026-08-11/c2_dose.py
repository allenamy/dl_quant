"""C2 (basis ⟂ funding) 权重剂量-反应 —— 部署定量前置。

★ 为什么必须做: 宽度门只测了 w ∈ {0.05, 0.10}, 而最好的一格恰在**测试范围端点**。
  E69 写死的规则: 「端点见顶 ⇒ 标为可疑, 不予录取(那是"越加越好"的过拟合签名)」。
  ⇒ 不扫宽就给不出一个可部署的权重。

★ 判据(写死于跑之前):
  (1) 可部署权重 w* = 使【安慰剂修正后净夏普】最大、且 CI95 下界 > 0、且【不在测试边界上】的那个 w
  (2) 若最优仍在最大测试权重 0.30 上 ⇒ 【仍标可疑】, 须再扫宽而非直接采用
  (3) 剂量曲线必须在 w 上大致单峰或单调后转平; 若锯齿状 ⇒ 噪声主导, 不出具权重建议
  (4) 三个 IC 口径(full/wtd/tail)的 dIC 应【同向】; 若打架则以净夏普为准并明记分歧
  成本: 3.115(换装后实测) 与 5.8 双报。
"""
import sys, json, time, numpy as np, pandas as pd
sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset")
exec(open("/mnt/storage/private/work_hsy/probe_artifacts/breadth2.py").read().split('R = {"prereg_sha"')[0])

WS = [0.02, 0.05, 0.10, 0.15, 0.20, 0.30]
SEEDS = [0, 1, 2, 3, 4]
COSTS = [3.115, 5.80]
OUT = "/mnt/storage/private/work_hsy/probe_artifacts/c2_dose.json"


def sh(p, t, c):
    return RF._dsharpe(pd.DataFrame({"day": DAY, "n": p - t*c*1e-4}).groupby("day").n.sum().values)


def boot(a, b, nb=4000, bl=5):
    rng = np.random.default_rng(20260809); n = len(a); nb_ = int(np.ceil(n/bl)); o = np.empty(nb)
    for k in range(nb):
        st = rng.integers(0, max(n-bl, 1), size=nb_)
        idx = (st[:, None]+np.arange(bl)[None, :]).ravel()[:n]; idx = idx[idx < n]
        o[k] = sh(a[idx], np.zeros_like(a[idx]), 0) - sh(b[idx], np.zeros_like(b[idx]), 0)
    return float(np.percentile(o, 2.5)), float(np.percentile(o, 97.5))


t0 = time.time()
bp, bt, bric = run(None)
bd = {c: pd.DataFrame({"day": DAY, "n": bp - bt*c*1e-4}).groupby("day").n.sum().values for c in COSTS}
print(f"基线书 rank-IC {np.nanmean(bric):+.5f}  " +
      "  ".join(f"Sh@{c} {RF._dsharpe(bd[c]):+.4f}" for c in COSTS), flush=True)

R = {"weights": WS, "costs": COSTS, "rows": {}}
print("\n  w     Δ毛额     Δ换手      dIC      真ΔSh@3.115  慰ΔSh   修正后    CI95下界")
print("-"*88)
for w in WS:
    rp, rt, rric = run("C2", "real", w)
    pls = [run("C2", f"sh{s}", w) for s in SEEDS]
    row = {"dIC": round(float(np.nanmean(rric - bric)), 6),
           "d_gross": round(float(rp.sum()-bp.sum()), 5),
           "d_turn": round(float(rt.sum()-bt.sum()), 1), "by_cost": {}}
    for c in COSTS:
        rd = pd.DataFrame({"day": DAY, "n": rp - rt*c*1e-4}).groupby("day").n.sum().values
        dsh = RF._dsharpe(rd) - RF._dsharpe(bd[c])
        pl = [RF._dsharpe(pd.DataFrame({"day": DAY, "n": p[0]-p[1]*c*1e-4}).groupby("day").n.sum().values)
              - RF._dsharpe(bd[c]) for p in pls]
        # 修正后效应的 CI: 真实书 vs 安慰剂均值书(逐日配对)
        plm = np.mean([pd.DataFrame({"day": DAY, "n": p[0]-p[1]*c*1e-4}).groupby("day").n.sum().values
                       for p in pls], axis=0)
        lo, hi = boot(rd, plm)
        row["by_cost"][str(c)] = {"dSh": round(dsh, 4), "placebo": round(float(np.mean(pl)), 4),
                                  "corrected": round(dsh-float(np.mean(pl)), 4),
                                  "ci95": [round(lo, 4), round(hi, 4)]}
    R["rows"][str(w)] = row
    e = row["by_cost"][str(COSTS[0])]
    print(f" {w:.2f} {row['d_gross']:+10.5f} {row['d_turn']:+9.1f} {row['dIC']:+9.5f}   "
          f"{e['dSh']:+8.4f} {e['placebo']:+8.4f} {e['corrected']:+8.4f}  {e['ci95'][0]:+8.4f}", flush=True)

print("\n===== 判据 =====")
cur = [(w, R["rows"][str(w)]["by_cost"][str(COSTS[0])]) for w in WS]
ok = [(w, e) for w, e in cur if e["ci95"][0] > 0 and
      R["rows"][str(w)]["by_cost"][str(COSTS[1])]["corrected"] > 0]
curve = [e["corrected"] for _, e in cur]
print(f"  剂量曲线@3.115 = {[round(x,4) for x in curve]}")
if ok:
    wbest, ebest = max(ok, key=lambda x: x[1]["corrected"])
    at_edge = (wbest == WS[-1])
    print(f"  两档为正且 CI 下界>0 的 w: {[w for w,_ in ok]}")
    print(f"  最优 w* = {wbest} (修正后 {ebest['corrected']:+.4f})  在边界上? {at_edge}")
    print(f"  ⇒ {'【仍可疑, 须再扫宽】' if at_edge else '可作为部署候选权重'}")
    R["w_star"] = wbest; R["at_boundary"] = bool(at_edge)
else:
    print("  没有任何 w 同时满足两档为正且 CI 下界>0 ⇒ 不出具权重建议")
    R["w_star"] = None
mono = all(curve[i] <= curve[i+1] for i in range(len(curve)-1))
peak_i = int(np.argmax(curve))
print(f"  形状: 单调={mono}  峰在 w={WS[peak_i]}  ({'边界' if peak_i in (0, len(WS)-1) else '内部'})")
R["shape"] = {"monotone": bool(mono), "peak_w": WS[peak_i], "peak_interior": peak_i not in (0, len(WS)-1)}
json.dump(R, open(OUT, "w"), indent=1)
print(f"\n[done] {time.time()-t0:.0f}s -> {OUT}\nC2DOSE_DONE")
