> **创建:** 2026-09-27 16:56 UTC | **Session:** Codex acting-lead/live_recovery_audit_0927 | **状态:** final（研究门红绿通过，待root独立验收） | **作废条件:** 运行期watchdog写读合同或RID/capture生成机制改变

# 恢复验收器两处假合同的具名更正

旧`recovery_acceptance.py` SHA `8d87ce4ebc0b5c613a0f9e29b4df8adf3971889b08f36ecad423a60c540ab642`把state文件存在直接判FAIL，且要求RID秒等于capture时间整数部分。两条均不符合真实生产合同，责任在本研究验收装置；不能通过删除正常state或改变实际锚来满足它。

root于16:49:42Z观测：watchdog tripped=false，triggers/conditions_blind/conditions_unevaluated为空；正常state为`{"reduce_only":false,"tripped_at":null,"_mode":"LIVE"}`。root提供的16Z anchors：nominal_ts=1790524800，anchor_ts=1790526241.442726，rebalance_id=A1790526240。这些原观测保留；本次没有删除、重写或修饰实盘文件，也没有重跑inspect或调用API。

## 源码事实

- watchdog.py:3133–3135缺文件默认false/null，:3325无条件durable写state；正常评估也会创建文件。run_anchor.py:431盖_mode。anchor_loop.py:1179以unreadable或tripped_at或reduce_only判停机；:1959–1965已记过“存在≠触发”的历史错误。
- anchor_loop.py:1060独立取run_anchor的now，:1700用rebalance_id.mint(now)生成RID；之后:2213调用binance_executor.capture_anchor，后者:747再次取time.time。:2490将真实RID与capture时间同时返回，run_anchor.py:328记录phase_A。

运行树源SHA（只读核验）：

| 文件 | SHA256 |
|---|---|
| live/watchdog.py | 20a446cb4dff7ab744a22e7cfa0aba2136834a4e1d9809f1993706c05003b152 |
| scheduler/anchor_loop.py | 6f156753634953441a2513a9d647a1096dcb6a34d0cb88622cafcc45bc558498 |
| scheduler/run_anchor.py | 33b32cb58b80196b0c32b2cda1164b082cfceb61cb2dffe27d5b75e5e5b3ba50 |
| live/state_root.py | 36d112227bc9e4ecc51e5716e779db6a6a9b5acbf85f04f05d94ab846439691d |
| live/binance_executor.py | 7757431d016da647b18e7b9148cbdd2d1f3731d1aa18eee61d7c5ccfc74299eb |
| live/rebalance_id.py | 108819b62a8b27b5ab041c2e0684e756dd920b1b0d50ee7e0db7c5776a1ae867 |

## 修后最小合同

state缺失且父目录可列可PASS；存在时必须对象、严格false/null/LIVE且无矛盾trip元数据。true、非null、DRY_RUN或矛盾FAIL；缺字段、畸形、不可读UNKNOWN。ledger K5是存在性观测，须严格bool并与本次直读presence一致；policy由直读state判定，present来源留hash。

RID必须为A+十进制秒，在名义锚内且不晚于capture。anchors的RID和capture时间必须与同窗唯一真实TRADE/external phase_A逐字段相等；若phase_A有外部书nominal_ts或anchor_ts也必须等于A。不用anchors反造phase_A、不引入任意时间容差；phase日志为整秒格式，时间先后按该精度比较。phase_A缺失PENDING，畸形UNKNOWN，重复/错身份FAIL。venue窗口仍严格真实RID−600秒。

## 红绿与限制

旧实现加新控：29 tests，5 failures，精确复现正常state误拒、K5不一致漏判、损坏状态误分类、phase_A缺失漏判和RID双时钟误拒。修后39 tests通过；另加同秒capture/日志截秒控制，先红1，再按日志精度修正，最终40/40通过（0.112秒）。原有恢复门与symbol-bound venue测试保留，未改风险/到位率/报告时效/告警阈值。

命令：`/usr/bin/python3 -B -W error::ResourceWarning -m unittest -q test_recovery_acceptance.py test_venue_readonly_symbol_bound.py`，目录`multi_asset/exports/research/acting_lead_2026-09-27/devices`。新reader SHA `0e78dba29aa235fd120c11e12e0212a81648a570d9ab6ad1e3ee9942f007fc82`。

本次只跑合成研究验收测试，没有跑执行器套件或实盘交易。未以真实16Z全9项收据重跑判词；root仍需采集N+55报告、17Z venue等完整输入。funding缺口告警不因此被豁免。继承PLAN §8 K5已追加更正并保留原句；§7恢复瞬间检查保持；PREP追加A也同步说明。
