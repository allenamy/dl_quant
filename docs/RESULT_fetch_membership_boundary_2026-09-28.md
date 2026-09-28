> **创建:** 2026-09-28 19:33 UTC | **Session:** Codex root / acting-lead-20260927 | **状态:** final | **作废条件:** 所引输入/源码SHA变化；仅八锚成员机制，不是全史平价或收益认证

# 六锚成员差异：研究判活代理没有生产当时的抓取名单

**六个差异锚的成员原因已实证；不是实盘继续交易死名，也不是新的盈利结果。** 生产与研究使用相同的成员代码，但研究把所有加密列当作可抓取列，生产使用每锚实际抓取名单。把研究侧这一项换为当时归档的真实名单，其它bar、参数、筛选与排序不动，六个差异锚及两个端点控制的400名成员顺序全部逐位相同。两侧各自的原人口也先复现成功。这个结果不能自动替代完整特征、F10历史成员、连续状态、费用及收益核验。

前件：[逐层对齐结果](RESULT_live_replay_layer_alignment_2026-09-28.md)。固定规格：[本次诊断计划](PLAN_fetch_membership_boundary_2026-09-28.md)，提交b27878ab6，真实UTC19:24:11；源码f3f327331，登记6d3f1523e，收官9110a6dfc。初版计划手填19:27而真实提交19:24，已按git更正，不修改原提交。

## 同一输入上的替换结果

| UTC锚 | 原研究多出 | 实际生产替代名 | 只替换fetch后完整400名 |
|---|---|---|---|
| 09-24 08 | 无 | 无 | 顺序精确相同 |
| 09-24 12 | STGUSDT | XAIUSDT | 顺序精确相同 |
| 09-24 16 | STGUSDT | HYPERUSDT | 顺序精确相同 |
| 09-24 20 | STGUSDT | XPINUSDT | 顺序精确相同 |
| 09-25 00 | STGUSDT | AUCTIONUSDT | 顺序精确相同 |
| 09-25 04 | STGUSDT | PHAROSUSDT | 顺序精确相同 |
| 09-25 08 | STGUSDT | BTCDOMUSDT | 顺序精确相同 |
| 09-25 12 | 无 | 无 | 顺序精确相同 |

八锚生产rolling/boundary必须匹配此前封存的SHA256SUMS，aux与原415文件归档一致；从原快照重算成员8/8精确。研究从原cache/R重算也8/8精确等于KING_FEATURES_AND_MEMBERS，之后才做fetch替换。两侧在最终实际成员上的qvm最大差均0；**全829轴缓存并不相同**，不能把成员相同写成全缓存平价。

## 为什么正好是这六锚

生产归档从09-24 12Z起fetch/base均不含STG，生产留存的最后有成交bar为09-24 08Z。研究公开缓存多了随后一小时的真实成交，最后有成交bar为09-24 09Z；之后继续存在交易数=0、报价成交量=0的bar。在09-24 12Z到09-25 12Z各窗口里，09Z之后分别有36/84/132/180/228/276/324根这种零活动bar。

研究`NC.legal_live`使用“过去24小时至少一根有成交bar，并有有限报价成交量”，因此直到09-25 08Z仍能通过。生产同样的判活门也在前五个差异锚为真，但另有实际fetch门把STG排除了；09-25 08Z实际缓存自己的W24H也转假。09-25 12Z研究W24H转假，两边人口自行重新一致。**有限报价成交量（包括0）不等于有成交，更不等于交易所当前仍处于TRADING。** `TRADE_ENDPOINT.json`特意把这三种概念分开。

本件没有调用交易所或查询历史公告，故不认证正式下市/停牌时刻及原因。已认证的是生产当时的fetch状态、两边实际bar、以及fetch替换对成员的充分解释。原`nc_hist_features.py`头部其实已登记“24小时内停止交易”的残余；这次把一个具名残余在实际八锚上测实，不能包装成原先从未有人知道的新缺陷。

源码出处：当前`/Users/haosiyu/wide_shadow/shadow_loop_v3.py`533–547行动态抓取，675–702行成员筛；`fea171/nc_contract.py::legal_live`与`tradability.py::window_states`。冻结NC的`pass1_anchor`把fetch设为全部加密列。实际成员块与冻结NC成员块逐字节一致，两份纯模块亦逐字节一致；保存的完整源码及SHA见收据/本机归档。没有import生产入口，也没有网络调用。

## 能关闭什么、仍不能关闭什么

接受：六锚成员差异由实际抓取状态边界解释；补该真实输入后成员可以完全复现。生产当前已有这一门，本批无需改生产成员代码。

不接受：以W24H代理声称历史交易状态精确、把今天的fetch名单倒填历史、把成员平价升级为完整组合或收益平价。没有历史真实状态的时段仍是具有限制的研究回放；若要求生产同输入认证，缺该输入应具名不可认证，不能默认全加密名等价于TRADING。

后续完整对接还须把这六锚的全部特征与历史成员传播接进去，再验F10、King/fund横截面秩、LR席位和H状态；本件不重算这些量，也不更改前件末锚0.352%的残余。不因这六锚撤销旧年候选失败，不生成新收益/夏普，不称本次已解释近期亏损规模。GAP4仍受原生产电池门约束，不能把本次诊断当作发布批准。

## 验证、资源与归档

- 本机原快照重算8.384秒；Pod研究重算与替换8.313秒，单CPU、零GPU。未占用训练，也未删除原始数据。
- 本机/Pod各12工程控制（包含原生产成员块的fetch移除负控、未来bar污染不变）；另62项独立人口/身份/归档核对通过。62不是独立重训或经济验收。
- 原研究来源按全文件SHA验证；实际快照按原manifest验证；八份7日全轴输入切片、纯模块、执行脚本、结果与日志26件均已本机封存并逐件核SHA。
- 实盘19:22:42Z轻审LIVE、无新trip；triggers/errors/blind/unevaluated/degraded均0，历史cond2/4 partial2未变，S3心跳10.5秒。该读数不是20Z验收；20Z需21Z静默窗并确认done后检查。K1三锚已完成不重复。

收据目录：`multi_asset/exports/research/acting_lead_2026-09-27/receipts/FETCH_MEMBERSHIP_BOUNDARY_20260928/`。

| 文件 | SHA256 |
|---|---|
| ACTUAL.json | 471dc2c226f2b6a9f8d858ff4724f07782ac6e4914c4eb2ea0e6e2d225271c64 |
| RESULT.json | 02d0201933add4c54935fdb7b94f13aa4682bd65e7704a9b3daa239d2f15592b |
| VERIFY.json | b1fdbec624c999e62823282a7c78a062bb0617481a71e6099b1e80a96f975ec6 |
| TRADE_ENDPOINT.json | 0f885b43a2932ae7162bd23d2cc3a49d672283d02eae60c9cd2b98570abe5f5a |
| 完整本机ZIP | d7dc2f5a08aea7b2e44e30f514a89a5ad51056476bc271b4adddc4ca67f3331d |

完整ZIP：`/Users/haosiyu/.codex/tmp/pod_archive_20260928/fetch_membership_boundary.zip`，135,871,881字节，26成员。远端原结果：`/dev/shm/fetch_membership_boundary_20260928/`；本机原材料：`/Users/haosiyu/.codex/tmp/fetch_membership_boundary_20260928/`。本机Python为`/Users/haosiyu/wide_shadow/venv/bin/python`，Pod为`/workspace/venv/bin/python`；具体numpy版本分别记于ACTUAL与RESULT。生产源码副本只读用于纯成员计算，未运行生产交易入口。

只读复验（在独立研究worktree；不碰交易所）：

```sh
DEV=multi_asset/exports/research/acting_lead_2026-09-27/devices/fetch_membership_boundary_20260928
PROBE_SOURCES=/Users/haosiyu/.codex/tmp/fetch_membership_boundary_20260928/sources OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 /Users/haosiyu/wide_shadow/venv/bin/python -m unittest discover -s "$DEV" -p 'test_*.py'
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 /Users/haosiyu/wide_shadow/venv/bin/python "$DEV/verify.py" /Users/haosiyu/.codex/tmp/fetch_membership_boundary_20260928 /Users/haosiyu/.codex/tmp/live_replay_layers_20260928/result
```

原数值运行命令已保留源码；不要向冻结结果目录重新运行`probe.py actual/research`覆盖原件。新复算要用新输出根并保留本件输入身份。
