> **创建:** 2026-09-27 15:46:08 UTC | **Session:** acting_lead/funding_mechanism_0927 | **状态:** final | **作废条件:** 输入身份或同人口闭合失败、读数后改分组/匹配

# 近期资金费状态迟滞：描述性人口闭合

窗口固定为冻结仓 3b4a2815a 下 lossdecomp/side_split_0924_0927_snap1790467200/NAMES.jsonl 的全部 priced 区间（既有说明为09-24 12Z至09-26 08Z，12个）。该NAMES SHA=4e84c8ddab83a177ca9d90e67f7935422daaccde42608c115b2ca2eaae833382。这段已被原研究用于生成假设，必须只称描述性，不作OOS/部署证据。

只读同锚aux.json的prev_rec.members/legz.fund/legz.king/legz.rev24、ema、ledger_tail，以及combined target_live中beta_overlay与既有SIDE_SPLIT.json的同持有窗BTC收益。符号轴读shadow_bundle/config.json并钉SHA。必须断言prev_rec.anchor_ts=A、EMA last_ts及ledger时点<=A、已知间隔与<=12h新鲜度；不补缺失、不前向填未来、无快照的锚不可测。参数代码读取冻结nc_contract.funding_asof；不运行其生产主程序。

人口从实际合池持有NAMES的L5 notional<0出发（非target负号），依次报全部已定价空头、可确定状态空头、当前RN8<0的付费方向空头、EMA<0且fund_z<=-0.25的极端组。定义滞后L：极端组内 RN8>=EMA/2 且 RN8<0，即费率负值至少恢复一半但EMA排名仍低。对照C：同一极端组内RN8<EMA/2。其余明确归other/unknown。不把当前负费率自动当实际收到或支付了多少。

先报各组名锚、|名义|、价格损益、去BTC beta后的价格残差，分组加总必须逐锚回到已认证SIDE_SPLIT短侧总额（含unknown），金额误差<=1e-6。不能用同号以外的份额；只报金额及gross份额。再读固定20260924/25/26 funding.jsonl，仅 settlement_ts in (tA,tB]，去重键必须唯一；检查现金流符号=-sign(notional)*sign(rate)，按结算当刻notional<0区分付费/收息。按该锚组归属与方向一致才附到组，否则进unknown；各组资金费加总必须闭合短侧真实现金簿。此表与模型标签、静态持有价格P&L仍是不同时间采样，不得拼成精确NAV归因。

唯一匹配：L与C在同锚内一对一贪婪匹配（L按symbol字典序，C距离并列按symbol），caliper |fund_z差|<=0.10、|rev24_z差|<=0.20、|beta差|<=0.25；距离=(Δfund_z/0.10)^2+(Δrev24_z/0.20)^2+(Δbeta/0.25)^2+(Δking_z/0.20)^2。不放宽caliper、不替换成别的规格。结果为L名义加权的短侧价格残差差=-Σ|n_L|[(r_L−β_L*rBTC)−(r_C−β_C*rBTC)]/Σ|n_L|，单位bps；控制比较名义匹配，报告覆盖率和各匹配变量差。至少20对且6个区间才给该描述均值，否则MATCHED_UNAVAILABLE（保留人口普查）。无显著性或因果结论。

该诊断把三天特征EMA与仓位EMA区分，但没有改变任一EMA。闭合算术是高分辨率人口测量，12区间匹配不是高功效策略测试；不得据此新增收益规格。

## 输入表示修订（2026-09-27 15:50:26 UTC，只见首锚整体空头金额，未见分组/匹配）

原装置先因锚键格式报错两次；实际SIDE_SPLIT键含分钟09-24T12:00Z，已加全集绝对键相等断言。之后原闭合门在首锚price短侧−4919.366554289033对已存−4919.37报红。回到side_split.py原码确认：每区间金额round(v,2)，r_btc=round(rb,5)。因此原1e-6用于已舍入SIDE_SPLIT不可满足，不能视为数据经济差异。改为round(独立重算金额,2)与SIDE_SPLIT逐位相等；加+0.01美元必须不等的红控。另以NAMES的同区间BTCUSDT未舍入r代替已舍入r_btc（12/12区间均存在），断言round(rawBTC,5)==receipt。新增整书价格L5对LAYERED_BOOK原始金额1e-6闭合；该守卫未放宽。人口、分组、caliper、匹配顺序、窗口、至少20对/6区间全部未改。两次格式失败和本次精度失败日志保留。
