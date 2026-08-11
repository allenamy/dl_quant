"""两项用户裁定的部署批(2026-08-10): ① harvest EMA α 1.0→0.3(重裁 T1) ② chase 政策 A(全不追)。
只在 04:00Z 锚验证通过后由外层执行。"""
import json, collections, re, sys

# ── ① config/book.json: harvest_ema ──────────────────────────────────────────────
p = "config/book.json"
d = json.load(open(p), object_pairs_hook=collections.OrderedDict)
assert d["harvest_ema"]["alpha"] == 1.0, f"当前不是 1.0: {d['harvest_ema']['alpha']}"
d["harvest_ema"] = collections.OrderedDict([
 ("alpha", 0.3),
 ("_basis", "★ 用户重裁 2026-08-10(T1 张力): 恢复 α=0.3。T1 v1(最近8锚IC<0.02且负锚≥4/8, "
  "commit 70d9d86)于 08-06 16:2xZ 无瑕疵执行并关闭 EMA —— 但 (a) 触发窗口事后查明是随机负段"
  "(逐锚 IC AR(1)=−0.058~−0.13, 无失效期), (b) 其前提『弱者恒弱』当日即被 AR(1) 实测反驳(张力同日登记), "
  "(c) 恢复规则(连续8锚IC>0.05)按 IC 分布(均值~0.049, sd~0.15)实质不可达 = 事实永久关闭。"
  "复验(2026-08-10, ema_exact.log): apply_harvest_ema 【原样 import】× 9821 锚 × 当前配置"
  "(king 8h·三腿·风险预算): 净@实测成本4.137 +0.378→+0.756, 夏普 +0.58→+1.05, Δ净 CI95[+0.206,+0.554] 排0, "
  "逐年 5/5 全正(0.17~0.66); 旧口径6.23 下亦翻正 −0.275→+0.411。盈亏平衡成本 1.562 bps/单位换手 —— "
  "成本须跌破纯 maker 费(2.0)才反转, 当前实测 4.137 = 2.6× 余量。prereg 76137fa4(冻结在数字前)+ "
  "RESULT_turnover_shaping(49385c50)。"),
 ("_t1_disposition", "★ T1 v1 已被本裁定【取代】: 在 #61 尺子审计交付重标定的守卫之前, "
  "任何自动/半自动把 α 改回 1.0 的动作都无授权 —— IC 类告警照发, 但改 α 一律需用户裁定。"
  "恢复规则 v1(连续8锚IC>0.05)同时废止(不可达 = 假门)。"),
 ("_state_note", "α=1.0 期间状态仍每锚写盘(legs.apply_harvest_ema 的 a>=1 分支设计如此), "
  "state/live/harvest_ema.json 是新鲜的 ⇒ 启用即从上一锚目标起步, 无陈旧记忆; halt/flatten 重置由 "
  "harvest_reset_required + resume 隔离清除双守卫(gate_coverage 的 [W] 组钉住)。"),
])
json.dump(d, open(p, "w"), indent=1, ensure_ascii=False)
print("① harvest_ema.alpha = 0.3 已写入")

# ── ② live/chase_policy.py: ARM_WEIGHTS ──────────────────────────────────────────
p2 = "live/chase_policy.py"
s = open(p2).read()
old = "ARM_WEIGHTS: Dict[str, float] = {ARM_CHASE: 1.0, ARM_NO_CHASE: 1.0}"
assert old in s
new = ("# ★ 政策 A(用户裁定 2026-08-10): 可交换总体【全不追】。chase 权重 0 ⇒ assign_arms 的\n"
 "#   `w[a] > 0` 过滤后只剩 no_chase, 全体确定性扣下。依据 RESULT_chase_experiment(039e26fc):\n"
 "#   E[H]−E[X] = +6.82 − 30.55 = −23.73 bps/单位残差(晚追付 ~17.4, 持有仅弃 6.8, 下一锚 maker\n"
 "#   以 −0.25 近乎免费重取; 69% 残差同向再来 = 不追是推迟)。决策论: 错误采纳的最大遗憾 ≈ CI 上界\n"
 "#   +0.08, 保留追单的最大遗憾 ≈ 48.9。★ 三个回退分支【原样保留】(无净值 / pop<min_eligible /\n"
 "#   臂倾斜>3% abort), 它们的失败方向都是『追』= 有界代价的保守侧; ARM_FORCED(中性保护)不受影响。\n"
 "#   ★ 记录自携: 每锚 anchors.jsonl 的 chase_experiment.weights 记下当锚权重, 历史校验\n"
 "#   (recompute_check)用记录内权重, 与本常量解耦。回滚 = 恢复 {1.0, 1.0}。\n"
 "ARM_WEIGHTS: Dict[str, float] = {ARM_CHASE: 0.0, ARM_NO_CHASE: 1.0}")
s = s.replace(old, new, 1)
open(p2, "w").write(s)
print("② ARM_WEIGHTS = {chase: 0.0, no_chase: 1.0} 已写入")

# ── ③ 生产钉: tests_harvest_ema 加 [P] 组(config 值 + 布线静态断言) ──────────────
p3 = "live/tests_harvest_ema.py"
t = open(p3).read()
if "[P] production pins" not in t:
    pin = '''

# ── [P] production pins (2026-08-10, 用户重裁 T1 后 α=0.3 生效; gate_coverage 曾自述的
#     盲区 (a)『anchor_loop 是否真读 config alpha』在 α 重新有牙后必须闭合) ─────────────
import json as _json, os as _os, re as _re
_repo = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_cfg = _json.load(open(_os.path.join(_repo, "config", "book.json")))
check("[P1] config harvest_ema.alpha == 0.3 (用户重裁 2026-08-10; 改动它需新裁定)",
      _cfg.get("harvest_ema", {}).get("alpha") == 0.3, repr(_cfg.get("harvest_ema", {}).get("alpha")))
_al = open(_os.path.join(_repo, "scheduler", "anchor_loop.py")).read()
check("[P2] anchor_loop 从 config 读 alpha 并调用 apply_harvest_ema(布线, 非意图)",
      '.get("harvest_ema") or {}).get("alpha"' in _al and "apply_harvest_ema(" in _al)
check("[P3] T1 v1 已废止的记录在 config 里(防止下一个读到旧规则的人照章再关)",
      "_t1_disposition" in (_cfg.get("harvest_ema") or {}))
'''
    marker = "print()\nprint(f\"  {'ALL PASS'"
    idx = t.find(marker)
    assert idx > 0, "找不到汇总打印锚点"
    t = t[:idx] + pin + "\n" + t[idx:]
    open(p3, "w").write(t)
    print("③ tests_harvest_ema 已加 [P] 生产钉")
else:
    print("③ 已存在, 跳过")
