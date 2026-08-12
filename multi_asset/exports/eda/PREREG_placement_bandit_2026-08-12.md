> **创建:** 2026-08-12 06:0xZ | **Session:** multi-asset-v2 主线 (6737834a) | **状态:** FROZEN(实施合同+判据, 先于部署)
> **授权:** 用户批准 2026-08-12("批准，一定要深入思考分析排查，确保没有错误和风险")
> **上游:** RESULT_r1_offline_eval(离线路线被自身弃用线合法关闭 ⇒ 反事实唯一路径) + DESIGN_r1_bandit_offline_eval §3

# PREREG — 挂单深度 ε-赌博机(实盘, 最小干预形态)

## 1. 干预定义(全部锁死)

- **动作集**: {join(现行: round_px 贴触价), behind(远离触价 1 tick)}; **ε = 0.10**;
- **范围**: 仅 attempt-1 主 maker 单(`submit_maker`); **topup/exit/reduce_only 单一律不入实验**(reduce_only=正在退出的仓, 不许实验);
- **分配**: 确定性 sha1(rebalance_id + symbol) 末字节 <26/256 → behind —— 可审计、锚内稳定、重放可复现, 无 RNG 状态;
- **behind 算术**: 严格 tick 网格: n=round(px/tick), buy→(n−1)·tick, sell→(n+1)·tick, 按 tick 小数位量化(−1111 浮点残渣教训); px−tick≤0 时回落 join;
- **结构安全网**: GTX post-only 不变 ⇒ 任何方向算错最坏 = 良性 -5022, **不可能变 taker**;
- **记账**: 执行器级 `_placement_experiment` 字典, `_order_row` 读取(**chase 模板: 不戳共享 plan 行** —— 那个错误咬过三次), 新列 `placement_arm` ∈ {join, behind, exempt}。

## 2. 失效安全(fail-closed 三层)

1. 配置读取任何异常 ⇒ eps=0 ⇒ 全 join = **逐位现行为**(带 T 级测试钉死);
2. 回滚 = `config/book.json` 里 eps 改 0, 下一锚生效, 无状态无重启;
3. 模块 import 失败 ⇒ 执行器照常走原路径(try/except 包裹, 镜像 chase_policy 的容错形状)。

## 3. 判据与停止规则(冻结)

- **读数点**: behind 臂 n≥600(预计 ~19 天)恰一次主判; 判据 = behind vs join 的 {成交率差, 成交单价改善(tick_bps), 未成交漂移成本} 合成 ΔV, CI95(逐日块 bootstrap)>0 ⇒ 提案将 behind 设为高 p̂(fill) 名的默认(那是**另一份**预注册);
- **安全线**(每日锚后人工复查, 亦在日报可见): behind 臂绝对成交率 <15%(n≥100 后)或实验列缺失 ⇒ eps 置 0 排查;
- **禁止**: n<300 不看臂间对比(除安全线); 不因中途读数改 ε 或动作集(改 = 新预注册);
- **84 锚窗**: 判据是绝对 income, 本实验期望净正且最坏 ~1 USDT/天, 不触发窗口重述; 照记不调和。

## 4. 预写死法

- behind 成交率与 join 无差(<2pp)⇒ I1 弹性被证伪于实盘, 轨道关闭;
- behind 的 markout 显著更毒(成交=被穿价)⇒ "省 tick 是逆向选择重定价"成立, 关闭并入档;
- 实验列在任意锚缺失 ⇒ 接线缺陷, eps=0 后修复重启计数。
