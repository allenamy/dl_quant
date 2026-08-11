# 部署交接 — 上真实账户前的显式必检项

> **创建:** 2026-07-25 JST | **Session:** multi-asset-v2 (0B) | **状态:** live checklist
> **作废条件:** 全部项在真实账户上验证完毕并记录
> ⚠ 本文列的是**在拿到账户前无法验证、因而必须在接入时逐条人工确认**的事项。**不是注释, 是必检项。**

## ★ MC-1 停开仓必须严格限于「开仓方向」

**规格 (当前只在 `MockBroker` 上成立):**
```python
if self.open_orders_halted and not order.get("reduce_only"):
    raise OpeningHalted(...)
```

**为什么是必检项:** 降级阶梯已重排为 **停开仓 → 平仓 → 告警**, 因为停开仓是零依赖、最可靠的一层。**但这个顺序只有在停开仓不拦截 reduce-only 时才是安全的 —— 若真实场所适配器无差别拦截, 前置的 halt 会挡掉我们自己的平仓, 把一个改进变成一场灾难。**

**`tests_production_signature.py [D5]` 验证的是 `MockBroker` —— 那是*规格*, 不是*实现*。真实适配器是另一份代码, 在拿到账户前无法验证。**

**接入时必须逐条确认:**
- [ ] 真实适配器实现了同一条语义 (halt 只对开仓方向生效);
- [ ] 在 sandbox/最小额度上**实测**: `open_orders_halted=True` 时 reduce-only 平仓单**仍能提交并成交**;
- [ ] 实测: 同状态下开仓方向单**被拒**;
- [ ] 若场所 API 不支持区分 reduce-only, **必须在下单前于我方代码判定方向**, 不得依赖场所标志。

## ★ MC-2 错误码表 0 行 `observed`

`venue_error_codes.py` 全部标 `doc-derived, UNVERIFIED`。**表不可能完整, 完整性由行为兜底提供** (N=3 连续失败尝试 / M=2 连续锚点)。
- [ ] 真实账户上观测到任一码后, 把该行改标 `observed`;
- [ ] **行为兜底路径必须在真实适配器上重测** —— 它才是保护, 码表只是快路径。

## ★ MC-3 数据陈旧门必须按数据源重标
`DATA_SOURCE_TYPE` 目前是 `t_plus_1_public_archive` (门 96h)。**pilot 走实时场所 feed ⇒ 必须切到 `live_venue_feed` (门 6h)。** 未加对应门的新数据源会直接 BLOCK (已断言), 但**切换动作本身是人工的**。
- [ ] 接入实时 feed 时同步改 `DATA_SOURCE_TYPE`。

## ★ MC-4 因子版本注册表
`factor_version_registry.py` 中 `pilot_book → funding_ema_normfix` (协议 §5)。
- [ ] pilot 出任何读数**之前**完成切换; 否则 `pilot_daily` 会 BLOCK (已断言)。

## ★ MC-5 第二双眼睛仍是已知缺口
日报投递到 `info@nanofika.com`, **收件人是操作者本人** ⇒ §9-F6-3 的"对不在这笔亏损里的人可见"**未满足**。用户知情取舍 ($25k)。
- [ ] 若规模上升, 重新评估;
- [ ] SMTP 凭据到位后确认 `delivery_status.json` 显示 `SENT` —— **只有投递回执可读作"已送达", 本地写文件不可以。**

## 验收状态的唯一来源
```
bash engine/live/run_acceptance.sh            # exit 0 ⇔ 全绿
```
**任何"套件全绿"的说法必须引用此脚本输出, 不得由人工逐个观察拼装。**
