> **创建:** 2026-09-28 01:04 SGT | **Session:** Codex acting-lead / research_resume_0927 | **状态:** final（装置已交付，真实读数未运行） | **作废条件:** 修后KSR DONE身份、绑定输入/源SHA、门4路径或冻结判据改变；任何新结果须独立收据

# KSR 终态后处理：范围与结果边界

对应 research_resume.md §6、root 已授权的缺口。只新增独立人工后处理装置 `ksr_terminal_audit.py` 和专属控制，不改原判官/38份series/16份targets_stats/11份gate4收据/D10的211pin/ACTING主台账。不部署、不起第三个等待器、不查未完成候选收益；KSR与D10作业监督仍归root。

运行必须在已部署修后reader的DONE之后：PGID3505287，上游3479615/start_ticks508358906；reader SHA816d3734…、waiter SHAab04c7f3…、config SHA5a0a12dc…都由代码钉死。先核DONE、INPUTS_BOUND与65份既有输入/代码SHA；本步只读收据和文件哈希，不先解析候选书层结果。之后才核以下技术前置；任何空轴、NaN/Inf、轴不等、缺首锚、首差延迟/提前、对象错位或未知均 `UNAVAILABLE`，不冒充收益REJECT。

1. 对全部8个S1核gate4收据与实际导出legs：来源必须是同成员的 `legs/KSR_S0_m{k}.npz` 与 `legs/KSR_S1_m{k}.npz`，不是名称相近或数值偶同的其它成员。SHA按原gate4收据绑定。实际King LR列0与LR整行均逐字节比较，第一次差异必须恰1696118400，且首锚真实存在、之前有非空历史。旧PASS标签不足以豁免此核查。
2. HYB不套此LR首差合同：SEAT_ONLY/COMP_ONLY保留A0 LR是设计行为。它们只参加同窗书层描述。
3. 38份series轴必须相等；16份targets的anchors必须与series相等。所有series/targets anchors与legs_E_ts均逐一确认七个切换/交回边缘精确存在，不能用searchsorted悄悄挪到下一锚。输出每条轴范围、长度和精确位置。
4. 仅在上述前置通过后加载m0的BASE/FULL/SEAT/COMP两seed收益与通道。其它7成员不进入交互项。

# 算法与窗口

对seed42、seed2027分别处理32条同序路径，在相同完整UTC日内先复利每条路径的6个r，再做FULL−BASE、SEAT−BASE、COMP−BASE。INT为 **(FULL−BASE)−(SEAT−BASE)−(COMP−BASE)=FULL−SEAT−COMP+BASE**，先逐seed/逐path/逐日算，再平均。绝不拿8成员平均FULL减单成员HYB，也不先平均路径再复利。

`dbar_compounded_bps`使用r的日复利收益差×10000；r已包含固定2倍gross，不再乘2。结果在每个窗口/seed/臂与冻结 `news_stats.dbar` 的32×日数矩阵直接对照（仅数值容差，不是研究门槛）。另报pnl价格、car资金费**付出**、cst费用**付出**、unk、g：原每锚gross bps在同完整日求和×GM2，单位NAV bps/日。正car/cst是更多付出。日复利差−算术g、g−(pnl−car−cst−unk)分别展示，不强制它们为零。

窗口并列、各列自己的实际起止/完整日数/日集合SHA：

- `PRE2026_ALL_AVAILABLE`：series首锚至2025-12-31T20Z，全部可用pre-2026。实际轴预计从2022-06-30起，以收据为准。
- `PRE2026_G4_COMMON`：G4/FRESH原比较口径2023-06-30T04Z至2025-12-31T20Z；06-30仅5锚，不是完整UTC日，首个实际用日为07-01。它不是H1合并，也不是上一个全可用列。
- `H1_2023/2024/2025`、`H1_merged`、`2026F`、`2026_ALL_AVAILABLE`，以及轴上所有 `MONTH_YYYY-MM`。

每段/seed/项给总均值、32条路径的各自日均值、日路径均值序列SHA；另给同path的两seed均值，保留两个seed原列。没有新置信门或“约0”阈值。原BOOK_HALF判词不被覆盖，最终OPTION_FOR_USER还需root按冻结IC/书层规则与所有必报缺项判断。

# 实测控制与来源

本地14/14专属测试通过（含子测），EMPTY_HISTORY_RED.log仅规范化行尾空格，原始SHA保留在VERIFICATION.json；其余日志原样保存。绿色日志在 `../receipts/ksr_terminal_audit_20260928/GREEN.log`。红控日志保留：装置不存在时缺功能红；无首窗前历史却想声称逐位相等红；同值但错成员腿路径红。后两项都在修前实见断言失败，修后转绿。

已知答案控制包括：四臂相同⇒所有差与INT全零；baseline10/FULL17/SEAT12/COMP13⇒INT2（逐path可异）；两seed倍数1/2⇒INT均值3；日复利先路径后平均；无重复gross；不完整UTC日排除；缺DONE时np.load不可触达；m7真实首差延迟但旧PASS和首差字段仍在时拒绝；HYB不读LR门；冻结NS逐路径对照；小合成全输出JSON回读。

- 装置 sourceSHA：`075382db08c2974a7a18f51b3b8a3b6d7ffc9703a820171862252c86336655d5`
- 17:18Z列名更正：只将异常提示中的 `[King,F10,fund]` 改为 `[King,rev24,fund]`。KSR `ksr_master.sh:93` 调 `mr_prep.sh:67` 的 `nc_legs.py`，后者第56行按king/rev24/fund写LR；F10在另一组合层。逐字比较确认源码仅这一字符串替换，归一该字符串后AST相等；数值、门和控制均未改。独立收据 `../receipts/ksr_terminal_audit_20260928/LR_LABEL_CORRECTION.json` SHA `802daf40f21a1c64bd3a5f2b3ea98d716ad71bff96568a6c413edb07e04a3158`。原14/14验证属于旧 sourceSHA `5a2fc0070e6425eca9077e54696ecd391ccb066b234e3a8cbc7d15f0a6e4c3f7`；原VERIFICATION与日志原样保留，不把旧测试收据改绑新SHA。
- 专属测试SHA：`ca13222d9580385abd2852bd9ca4e293cca3f60d62ed315ab314898ad7f28fcf`
- 证据清单 `../receipts/ksr_terminal_audit_20260928/VERIFICATION.json` SHA：`1cbfe0dfb7cdd9f0fa3140a2f301d6fae5ae9d34b8f9ec67eed73041961fc017`
- 保存器 `fa_ladsave.py` SHA a2dccf15a232a546c886e12fb2e1cd5522762509f42edd324eb3df4e57d17855；队列 `mr_engine_queue.sh` SHA000b6a4ba599ee0fd701a705effa2fba096dbc86296a23783462561676732f98。两者17:00Z与Pod实际文件同SHA，此次SSH只读代码SHA，没有读候选。
- NS/BT/DL的完整源SHA，以及冻结规则、设计、G4文件SHA均在VERIFICATION.json，运行时再次核reader原code_pins。

本地复跑：
```sh
cd /Users/haosiyu/.codex/worktrees/acting-lead-20260927/quant_research
python3 -B multi_asset/exports/research/acting_lead_2026-09-27/devices/test_ksr_terminal_audit.py
```
测试中的冻结NS对照使用本worktree文件布局；此测试命令供本地复跑。真实Pod运行本身也强制对照Pod上已绑定的冻结NS。

# root人工部署和执行（未执行）

root先审本件与sourceSHA，等修后KSR reader DONE。选择独立新目录；以下device目录不存在才创建，不覆盖。无需复制原38series或任何D10文件。

```sh
ssh pod2 mkdir -m 700 /workspace/codex_research/QNT-2026-0907/acting_lead_20260927/ksr_terminal_audit_device_20260928
scp /Users/haosiyu/.codex/worktrees/acting-lead-20260927/quant_research/multi_asset/exports/research/acting_lead_2026-09-27/devices/ksr_terminal_audit.py pod2:/workspace/codex_research/QNT-2026-0907/acting_lead_20260927/ksr_terminal_audit_device_20260928/
ssh pod2 sha256sum /workspace/codex_research/QNT-2026-0907/acting_lead_20260927/ksr_terminal_audit_device_20260928/ksr_terminal_audit.py
```

SHA必须恰为上述sourceSHA。确认KSR/D10资源调度可容纳轻CPU读数后，人工执行一次：

```sh
ssh pod2 env -i PATH=/usr/bin:/bin HOME=/root LC_CTYPE=C OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \
  /usr/bin/timeout 900s /workspace/venv/bin/python -B \
  /workspace/codex_research/QNT-2026-0907/acting_lead_20260927/ksr_terminal_audit_device_20260928/ksr_terminal_audit.py \
  --readout-root /workspace/codex_research/QNT-2026-0907/acting_lead_20260927/ksr_readout \
  --out-dir /workspace/codex_research/QNT-2026-0907/acting_lead_20260927/ksr_terminal_audit_20260928 \
  --self-sha 075382db08c2974a7a18f51b3b8a3b6d7ffc9703a820171862252c86336655d5
```

输出目录必须是reader目录的独立新同级目录、名字以ksr_terminal_audit_开头；已存在则拒绝，不重复claim/覆盖。输出KSR_TERMINAL_AUDIT.json和DONE.json（绑定输出SHA），成功stdout `KSR_POSTPROCESS_DONE` / rc0；技术失败stdout `KSR_POSTPROCESS_UNAVAILABLE` / rc2，若新输出目录已建则同时写FAILED.json。timeout的rc124、信号退出或进程消失**不算完成**，不得仅见result文件就读结论。

单CPU、OMP/BLAS1、nice19、RLIMIT_AS3GiB、CPU600s、外层wall900s；运行前有限cgroup headroom至少2GiB。不循环等资源、不起子训练。预计常驻数组约0.15–0.4GiB，JSON数MiB，另有逐文件SHA流读成本；真实峰值/耗时未测，最终收据记录。若D10当前占用令cgroup不足，root另择时人工调用，不加等待器。

# 明确未验证

尚未在真实DONE输入上运行，尚无实际首差8/8结论、INT/pre/月读数或候选判词。保存器将seed0..31按序写入并核过seed字段，但SER没有显式path-id列；原PATH文件已按队列删除，不能独立再核历史逐PATH身份。当前源码SHA相同也不是历史部署时间的全新证明。此项在输出内具名，不以收益形状推测路径。

H2同日年龄斜率仍未运行；本工具不建立FRESH弱因果的充分结论，不新增“为正/约0即归因”规则，不将不显著当等效。原CFG04/06盲态未打开。本交付不会改ACTING主台账，由root按完成收据更新。

## 22Z真实运行后的来源合同修复（root，2026-09-27 UTC）

原装置在实际DONE输入上返回rc2 `non-finite LR`；原FAILED和原075382db源码保留，不覆盖。原因属于本后处理器：nc_legs.py（Pod与仓库均SHA18387627…）先把LR全置NaN，只在下一锚到来后回填前锚i−1，且King OOF首个可用锚之前没有LR。实际16份legs同样具有1086行不可计量前缀（至2022-06-30T20Z）和最后一行未闭合LR；第一可用锚2022-07-01T00Z，中间无缺值，8组King首个字节差都恰为1696118400。我的首个诊断探针误假定所有缺值只在前缀，遇尾行越界；原错误输出保留，后续按连续区间重查。

修复只限验收器：额外钉住真实nc_legs源；从两边ready轴验证同一连续预热前缀，要求全部三列恰在该前缀及未闭合尾行NaN，其余全有限，Infinity永拒；要求在W0前已有真实有限历史；仍对整个LR逐字节比较及核King/LR准确首差。不填0、不删行、不改候选、窗口或统计门。上述修订取代本件开头“任意NaN都拒”的过宽表述。没有读取KSR书层结果后选取例外。

新增真实入口夹具在旧075382db上拒绝（同一non-finite LR），修后专属套件15/15，通过9种反例：中间NaN、前缀Inf、单边缺值、两ready不同、ready中间孔洞、非bool、前缀伪造有限值、尾行伪造有限值、无真实窗前历史。源SHA `2f2b9465685ff947209e9627ebf33d5719d3a27f9d985b81cd7c9d5873f6d515`，测试SHA `3f4fe91c782f1466d038ce7c96cfd1e2496b1e4b862ed8e8d454928cca89b6c8`。

实际重跑使用新目录 `ksr_terminal_audit_device_20260928_lr_support` / `ksr_terminal_audit_20260928_lr_support`，同样单CPU/AS3GiB/600sCPU/900s墙钟。原目录不可复写。原reader与D10门全不改。
