> **创建:** 2026-09-27 06:3xZ | **Session:** session_01VNPQL7t93ECz7Xkrv9rH6n(news2) | **状态:** 结果(恒等控制,只作描述;不产生书层或模型层数字) | **作废条件:** 表中任一装置再改动(须对改动的行重跑);或参照产物被重建

# 结果:重建装置端到端干跑(2026-09-27,pod2)

**计划与判据**:`docs/PLAN_rebuild_devices_dry_run_2026-09-27.md`。lead 于 acd2303b6 冻结,冻结补遗 1 为 093f72527;另有两次续跑裁定:D3 因配额挂起,D5a 修复后续跑。
**问题**:d3a7f013d 把链上装置的写文件改成走 `common/durable_write.py`(ac8960d8b 又补了两处漏掉的 import);再加上三份收据补记的 argv 与解释器。在与上次交付完全相同的输入上重跑,产物是否与上次一致?

## 1. 逐行结果(以最后一次运行为准)

| 行 | 装置 | 结果 | 部分 | 说明 |
|---|---|---|---|---|
| S0 | 比较器自测 | PASS | 1–4 各一次 | S1–S15 全过,含 1 ULP、dtype、字节翻转、argv --out 断言 |
| D7 | `d10_make_symlists.py` | IDENTICAL | 1 | 80 个文件逐字节相同,文件集合相同 |
| D8 | `d10_manifest_gate.py --selftest` | PASS | 1 | SELFTEST GREEN 7/7 |
| D1 | `d10_build_ledger_ms.py` | IDENTICAL | 1 | 数组逐位相同;收据逐键相同;183 s |
| D2a | `d10_build_fund_state.py --mode snap` | IDENTICAL | 1 | 数组与收据相同 |
| D2b | `d10_build_fund_state.py --mode d10` | IDENTICAL | 1 | 数组与收据相同 |
| D3 | `d10_stage2_assemble.py` | IDENTICAL | 4 | 第 1 部分 ERROR:/workspace 配额满(EDQUOT),见 E-0927-D;第 2 部分记 NOT_RUN(quota);lead 释放配额后单独补跑,写前探针 4,034,360,591 字节完整写入并删除;56 s |
| D4a | `d10_parity_gate.py`(snap control) | IDENTICAL | 2 | 参照为 521c6a28 产出的收据(GREEN) |
| D4b | `d10_parity_gate.py`(common window) | IDENTICAL | 2 | RED 判词与内容逐键复现 |
| D4pc | `d10_parity_gate.py --positive-control` | PASS | 2 | CONTROL_PASS(只作功能检查,按补遗 1) |
| D5a | `d10_p2_ledger_vs_archive.py`(旧 P2) | IDENTICAL | 3 | 第 2 部分 ERROR,是**干跑抓到的真缺陷**,见 §2;修后 IDENTICAL |
| D5b | `d10_p2_ledger_vs_archive.py`(ledger_ms) | IDENTICAL | 3 | 126 s |
| D5c | `d10_legs_rn8_vs_archive.py` | IDENTICAL | 3 | 与 D5a 同一缺陷;修后首次实跑 |
| D6 | `d10_live_ledger_vs_archive.py` | IDENTICAL | 3 | 输入快照仍在,sha 91a1a2cd;没有 NOT_RUN |
| D9 | `d10_archive_inventory.py`(3 名,真实请求) | IDENTICAL | 3 | BTCUSDT、ETHUSDT、SOLUSDT 的盘点条目相同 |
| D10 | `d10_pull_months_pod2.sh` + rev 2 拉取器(3 名,真实拉取 2026-08) | IDENTICAL | 3 | COMPLETE all_verified=yes;3 个 zip 逐字节相同;manifest 条目相同 |

**gate_sha256 的豁免**(补遗 1 第 3 条):manifest 门的两个版本,793c5eb2 与 6a8b16ca,ast.dump 相等(ast sha 为 21aebc27a281d077,两侧相同)。D5a–D6 的收据里,两侧的取值恰好就是这两个版本。

## 2. 干跑抓到的缺陷(已修)

- **缺陷**:`d10_p2_ledger_vs_archive.py` 与 `d10_legs_rn8_vs_archive.py` 在 d3a7f013d 里改成调用 `DW.write_json`,但没有插入 import。审计本身跑完了,在写收据的最后一行抛出 NameError。
- **没被早些发现的原因**:解析检查、`--help`、裸写检查都过了,因为这个名字只在 main() 的最后一行才用到。
- **修复**:ac8960d8b。类守卫为契约测试 C5:runbook 点名的装置里,不许有无法解析的名字。它先在恰好这两个装置上判红,修后绿,26/26;扫描全目录没有其它命中。
- **影响面**(lead 要求核实):有缺陷的版本只存在于仓库(05:24Z 到修复)和 pod2 的干跑目录。pod2 上其它副本都是补丁前的版本,自 09-26 起未变;补丁之后,两台机器上都没有这两个装置的任何新产物。**这两个装置只在干跑里首次触发**,没有任何产物需要标为待重核。

## 3. 一处更正:npz 文件 sha 其实可以复现

- 计划 §1 第 1 条、d3a7f013d 的提交信息、比较器的 docstring 都写着「npz 文件本身的 sha 无法复现,因为 zip 条目带写入时刻」。**这是错的。**
- 实测:干跑写出的四个 npz,**文件 sha 与参照完全相同**:
  - NEWS_FEATURES_D10 f1cd3fa2
  - fund_state_snap 35cc8f30
  - fund_state_d10 f07e4ebd
  - ledger_full_ms e179071d
- 原因:numpy 的 `savez` 写出的 zip 条目时间固定为 1980-01-01,实测 date_time = (1980, 1, 1, 0, 0, 0)。
- 我先前的说法是从另一件事推广过来的:KING_OOF.npz 里带着每次运行都会变的 model_sha256 数组,所以它的文件 sha 会变。那是**内容**在变,不是容器在变。
- **对本次判据的影响**:按冻结判据,npz 的文件 sha 被列为「易变」。事实上它们全部相等,所以结果比判据要求的更强,没有任何一行的判词受影响。今后比较 npz,文件 sha 相等可以作为额外证据;不相等时,仍然要比数组,才能区分「内容变了」和「容器里某个辅助字段变了」。

## 4. 没有覆盖的

- `nc_p2_build.py`、`nc_legs.py`(生产派生的复制件,未改)、训练器、生产者树、执行器,都不在本次范围内。
- 干跑只证明「同输入,同输出」,不证明十月的新输入(九月的 zip、新轴)能走通。那部分由 runbook §1–§2 的恒等控制在十月当时负责。
- 两个尚未写的装置(ledger_ms rev 2、按 argv 取月份的复审计驱动)写好后,同样要先过契约测试与各自的控制。

## 5. 收据

- `multi_asset/exports/research/news2_2026-09-23/receipts/dryrun_2026-09-27/part{1,2,3,4}/`:每部分的 `DRYRUN_RESULT*.json`、`dryrun.log`,以及各行装置的 stdout/stderr。
- 装置:
  - 比较器 `d10_dryrun_compare.py`(sha 1c8f6148…)
  - runner `d10_dryrun_run.py`(rev 2,sha aca7dd6a…)
- pod2 上的产物:`/workspace/d10_dryrun_2026-09-27/out/`,3.1 G,与参照逐位相同,是冗余副本。清理与否由 lead 定。
