"""T1 复审 · 换手前沿装置 frontier_sweep.py 原样重跑(只换 cost_bps): KA 控制 + cost 轴 C ∈ {0.32, 3.52, 6.64} × λ ∈ {0, .25, .5}。
C = 实测在役每单位意图换手 cash+opp 的 CI 下/点/上(turnover_cost_reaudit_2026-08-21.json)。算法/书/预测逐字不动(07-26 四腿正典引擎书)。
★ 若 KA-1 不过(engine/replay_fullhist.py 自 07-26 起 sha 已变 e426dfe5→94c303ac), 如实报告, 不带着漂移的基准做前沿。"""
import sys, os, json, time
sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports/eda")
import frontier_sweep as FS
OUT = "/mnt/storage/private/work_hsy/probe_artifacts/frontier_reaudit"
os.makedirs(OUT, exist_ok=True)
canon = FS.load_canonical()
t0 = time.time()
out = FS.run_point()
chk = FS.ka_check(out, canon)
json.dump({"known_answer": chk, "raw": out}, open(f"{OUT}/ka.json", "w"), indent=1, default=str)
print("KA:", json.dumps(chk, ensure_ascii=False), "elapsed", round(time.time()-t0,1), flush=True)
if not (chk["KA1_matches_pinned_canonical"] and chk["KA2_per_year_turnover_sums_to_engine"]):
    print("★ KA 未过 —— 停, 不跑成本轴 (装置基准已漂移, 按预注册规则作废)", flush=True)
    # 仍记录 canonical 与本次 b=λ=0 的差异以便归因
    print("pinned avg_net", canon.get("avg_net_of_cost_sharpe"), "rerun avg_net", out.get("avg_net_of_cost_sharpe"), flush=True)
    raise SystemExit(0)
res = {}
for cb in (0.32, 3.52, 6.64):
    for lam in (0.0, 0.25, 0.50):
        t1 = time.time()
        o = FS.run_point(inertia=lam, cost_bps=cb)
        tag = f"cost{cb}_lam{lam}"
        json.dump(o, open(f"{OUT}/pt_{tag}.json", "w"), indent=1, default=str)
        res[tag] = {"net_turn_ann": o["netting"]["net_turn_ann"], "avg_net_sharpe": o["avg_net_of_cost_sharpe"],
                    "per_year_net": {str(y): o["per_year"][y]["net_of_cost_sharpe"] for y in o["per_year"]}}
        print(f"[{tag}] turn={o['netting']['net_turn_ann']:.1f} avg_net={o['avg_net_of_cost_sharpe']} elapsed {round(time.time()-t1,1)}s", flush=True)
json.dump(res, open(f"{OUT}/summary.json", "w"), indent=1)
print("FRONTIER_REAUDIT_DONE")
