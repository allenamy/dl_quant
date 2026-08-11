"""腿权重的净额最优重估 —— 执行 PREREG_leg_weight_netopt_2026-08-04.md
(FROZEN v1, sha 67f2128145462021a663bd6f20684999b6738ebb212c45283d28c72b0104d691)

装置 = engine.replay_fullhist.run_replay 直接调用(与 #22 同一入口, 不复制)。
判读协议在预注册 §3, 已封。本脚本只执行并把命中的那一行打出来。
"""
import sys, json, time, itertools
MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
sys.path.insert(0, MA); sys.path.insert(0, MA + "/engine/live")
sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset")
import numpy as np
import torch; torch.backends.mkldnn.enabled = False
from engine import replay_fullhist as RF

KING = "/tmp/king_pred_newgen.npz"
S2 = "/tmp/s2_pred_newgen.npz"
STEP = 0.05
COSTS = [3.63, 5.8]                       # 预注册 §1: 两档必须同时报
INCUMBENT = {"king": 0.5952380952380952, "s2": 0.20238095238095238,
             "funding": 0.20238095238095238, "size": 0.0}
EQUAL = {"king": 1/3, "s2": 1/3, "funding": 1/3, "size": 0.0}


def grid(step):
    n = int(round(1.0 / step))
    out = []
    for i in range(n + 1):
        for j in range(n + 1 - i):
            k = n - i - j
            out.append({"king": i * step, "s2": j * step, "funding": k * step, "size": 0.0})
    return out


def one(w, cost):
    RF.COST_BPS = cost
    o = RF.run_replay(funding_mode="rank", use_c5=True, shaping="cap",
                      king=KING, s2=S2, weights=dict(w), verbose=False)
    used = o.get("cost_bps")
    assert abs(float(used) - cost) < 1e-9, f"artifact cost {used} != {cost}"
    per_year = {int(y): float(o["per_year"][y]["net_of_cost_sharpe"]) for y in o["per_year"]}
    return {"avg": float(o["avg_net_of_cost_sharpe"]), "per_year": per_year,
            "gross_turn_ann": float(o.get("gross_turn_ann", float("nan")))}


G = grid(STEP)
print(f"grid points = {len(G)}; costs = {COSTS}", flush=True)

# ── 先量一次调用的墙钟, 据此决定是否降密度(诚实上报, 不偷偷砍) ──────────────
RF._SRC, RF._SRC_KEY = None, None
t0 = time.time(); _ = one(INCUMBENT, COSTS[0]); t_cold = time.time() - t0
t0 = time.time(); _ = one(EQUAL, COSTS[0]); t_warm = time.time() - t0
est = t_warm * len(G) * len(COSTS) / 60.0
print(f"cold={t_cold:.1f}s warm={t_warm:.1f}s -> full grid ≈ {est:.0f} min", flush=True)
if est > 150:
    STEP = 0.10
    G = grid(STEP)
    print(f"★ 降密度到 step={STEP} ({len(G)} points, ≈{t_warm*len(G)*len(COSTS)/60:.0f} min) "
          f"—— 预注册 §2 写的是 0.05; 这是【声明过的偏离】, 记在结果里, 不是静默调整", flush=True)

res = {}
for ci, cost in enumerate(COSTS):
    for gi, w in enumerate(G):
        key = (round(w["king"], 3), round(w["s2"], 3), round(w["funding"], 3), cost)
        res[key] = one(w, cost)
        if gi % 20 == 0:
            print(f"  [{cost}] {gi}/{len(G)}", flush=True)
for w, tag in ((INCUMBENT, "INCUMBENT"), (EQUAL, "EQUAL")):
    for cost in COSTS:
        res[(tag, cost)] = one(w, cost)

# ── 预注册 §3 的 walk-forward ────────────────────────────────────────────────
years = sorted(next(iter(res.values()))["per_year"].keys())
print(f"\nyears = {years}", flush=True)


def wf(cost, pool):
    """w*(Y) 在【严格早于 Y】的年份上最优, 在 Y 上读数。"""
    out = {}
    for Y in years[1:]:
        prior = [y for y in years if y < Y]
        best, bw = -1e18, None
        for k, v in res.items():
            if k[-1] != cost or isinstance(k[0], str):
                continue
            if pool is not None and k[:3] not in pool:
                continue
            m = float(np.mean([v["per_year"][y] for y in prior]))
            if m > best:
                best, bw = m, k
        out[Y] = {"w": bw[:3], "oos": res[bw]["per_year"][Y],
                  "turn": res[bw]["gross_turn_ann"]}
    return out


rows = {}
for cost in COSTS:
    opt = wf(cost, None)
    rows[cost] = {
        "walkforward_opt": {"per_year": {y: v["oos"] for y, v in opt.items()},
                            "mean": float(np.mean([v["oos"] for v in opt.values()])),
                            "w_by_year": {y: v["w"] for y, v in opt.items()},
                            "turn_by_year": {y: v["turn"] for y, v in opt.items()}},
        "incumbent": {"per_year": {y: res[("INCUMBENT", cost)]["per_year"][y] for y in years[1:]},
                      "mean": float(np.mean([res[("INCUMBENT", cost)]["per_year"][y] for y in years[1:]])),
                      "turn": res[("INCUMBENT", cost)]["gross_turn_ann"]},
        "equal": {"per_year": {y: res[("EQUAL", cost)]["per_year"][y] for y in years[1:]},
                  "mean": float(np.mean([res[("EQUAL", cost)]["per_year"][y] for y in years[1:]])),
                  "turn": res[("EQUAL", cost)]["gross_turn_ann"]},
    }
    ins = max((v["avg"], k[:3]) for k, v in res.items() if k[-1] == cost and not isinstance(k[0], str))
    rows[cost]["in_sample_upper_bound"] = {"avg": ins[0], "w": ins[1],
                                           "note": "UPPER BOUND ONLY — not deployable (fit and read on the same data)"}

print("\n" + "=" * 78)
for cost in COSTS:
    r = rows[cost]
    print(f"[cost {cost}]  walk-forward OOS mean:  OPT {r['walkforward_opt']['mean']:+.3f}  "
          f"INCUMBENT {r['incumbent']['mean']:+.3f}  EQUAL {r['equal']['mean']:+.3f}"
          f"   | in-sample UB {r['in_sample_upper_bound']['avg']:+.3f} @ {r['in_sample_upper_bound']['w']}")
    print(f"          w*(Y) by year: {r['walkforward_opt']['w_by_year']}")
    print(f"          turnover: OPT {r['walkforward_opt']['turn_by_year']}  INCUMBENT {r['incumbent']['turn']:.0f}")
    d_inc = r["walkforward_opt"]["mean"] - r["incumbent"]["mean"]
    d_eq = r["walkforward_opt"]["mean"] - r["equal"]["mean"]
    if d_eq <= 0:
        v = "装置没找到东西 —— 优化打不过等权 ⇒ 报『权重优化在本书上无效』(预注册 §3 第三行)"
    elif d_inc <= 0:
        v = "优化不如现行权重 ⇒ 不换"
    else:
        v = f"优化优于现行 {d_inc:+.3f} 且优于等权 {d_eq:+.3f} ⇒ 待 day-block CI 判(下一步)"
    print(f"          判读: {v}")

json.dump({"prereg": "PREREG_leg_weight_netopt_2026-08-04.md",
           "prereg_sha256": "67f2128145462021a663bd6f20684999b6738ebb212c45283d28c72b0104d691",
           "step": STEP, "n_grid": len(G), "costs": COSTS, "years": years, "rows": rows},
          open(MA + "/exports/eda/RESULT_leg_weight_netopt_2026-08-04.json", "w"), indent=1)
print("\nrecord -> exports/eda/RESULT_leg_weight_netopt_2026-08-04.json")
