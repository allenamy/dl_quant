# DESIGN · 判官出口底(REQUIRED_INPUTS["BUNDLE_export"])11 → 28: 与 v2 出口门闭包对齐 + 夹具扩到新底

> **创建:** 2026-09-12 (W4, research-chain engineer) | **Session:** b9646a9e / team W4 | **状态:** 事实表先写(§1); 代码改动 §3; 自检与 pod2 对照收据 §5(RESULT); **未提交, 由 lead 提交** | **作废条件:** 合同 `gates.BUNDLE_export` 换源(v2 门 sha 变)或 v2 门注册名集变 ⇒ 本底必须同步重对齐并重跑 §5

关联: `docs/RUNBOOK_monthly_retrain_2026-10.md` §0★ 步 7(v2 门 gate+require) · r20 RESULT `multi_asset/exports/research/uplift_2026-09-11/r20_gate_closure/RESULT_r20_gate_closure_2026-09-12.md` §3/§7/§8 · 合同应用记录 `ELIGIBILITY_CONTRACT.json` `applied_note`(「judge 底仍 11(扩底待夹具)」) · `STATE.md` 09-12 10:0xZ ⑥。

## 0. 一句话

判官 `judge_v4.py` 对候选臂的 `require` 只强制 11 个注册名(7 上游 + 4 判书), 而已应用的 v2 出口门实际注册 **28** 个(多出 4 基线书 + 清单 + 8 bundle 文件 + 成本/掩码/king 文件 + 合同本身); 缺口 = 判官对「收据写完后 bundle 文件/基线书/成本模型被换」是盲的(v2 门自身的 require 模式不盲, 但判官不调用它)。本改动把注册底扩成 v2 闭包**逐名相同**, 并把链自检夹具扩到同一底, 使判官层也能拒绝「28 中任一名被漏声明」。

## 1. 事实表(本会话逐条实测; 「读者在发出时重算」)

| # | 事实 | 证据(命令/文件, 本会话) |
|---|---|---|
| F1 | `v4_gate_common.py` 现 sha `7b6d49a3…` == 待用 diff 的基线(diff 头 `(7b6d49a3)`); `REQUIRED_INPUTS["BUNDLE_export"]` = 11 名 = 7 上游(`wide_fea_v4, wide_fea_v4_meta, bundle_base, export_panel, bundle_cache, fund_aug, live_pins`)+ 4 判书(`BOOK_INPUTS`) | `shasum -a 256`; 文件 L56-58 |
| F2 | 真收据 pod2 `/workspace/uplift_2026-09-11/r20_gate_closure/receipts/pod2_applied/BUNDLE_export_v2_A1_applied.json`: gate=BUNDLE_export, PASS=true, arm=A1, self_sha256=`d63f4ec3…`(== 已应用合同批准源), utc 2026-09-12T09:23:10Z, 11 项 check 全 ok, E7 不适用(无 FEMAT 注入 ⇒ 收据**无** `femat`/`signal_receipt`), `registered_inputs` **28** 名, `registered_floor_v4_gate_common` 记录为 11 名, `contract_sha256`=`1188267a…` | ssh pod2 python 读取(只读) |
| F3 | diff 新增 17 名 == 真收据 28 − 现 11 的 17 名, **逐名相同, 顺序无关**: `base_{dyn,fix}_s{42,2027}`(4) · `bundle_manifest`(1) · `bundle/{slow_pred_pinned.npy, slow2026.txt, config.json, cache_tail_40d.npz, fund_ema_v1_state.json, funding_ledger_seed.json, leg_returns.npz, parity_signals_aug.json}`(8) · `costb_json, umask_npz, slow_npy, eligibility_contract`(4) | F2 输出 vs `infra2/v4chain_PROPOSED2/v4_gate_common.PROPOSED.diff`; 自检新增静态断言(§3.2 (i)) |
| F4 | 该底的消费者只有两处: `judge_v4.py` L205 `_require(receipt, caller inputs + 4 判书, expected_gate=合同 gate, profile=合同 profile)`; `v4e_gate_export_v2.py` L496 require 模式传 `cx.inputs`(从盘上派生的全集, A1 = 28)。`chain_*.sh` 只 require G2_closure / STEP1(@v4, @v4s) / STEP2, **无一 require BUNDLE_export** | `grep -n "REQUIRED_INPUTS\|BUNDLE_export\|require_gate" chain_*.sh` |
| F5 | 合同 5 个候选臂 `profile: null`, `book_binding: true`; 判官把 profile=None 传给 require ⇒ 键 = 裸 `BUNDLE_export` | `ELIGIBILITY_CONTRACT.json` arms |
| F6 | 夹具 `bound_entry` 只写 7 上游合成文件 + 判书 sha; 判官再加 4 判书 ⇒ 现夹具入参 11。扩底后所有基于 `bound_entry` 的正控会以 `omitted registered input(s) [17 名]` 变红(= lead 上午看到的 8 红) | `tests_pipeline_gates.py` L389-408 |
| F7 | 基线自检: `/usr/bin/python3 tests_pipeline_gates.py` ⇒ **ALL PASS (151 checks)**, 3 min 07 s | 本会话, 日志 `receipts/judge_floor_2026-09-12/tests_before_151.log` |
| F8 | pod2 起步状态: GPU `0 %, 2 MiB`; PID 333197 / 339489 在跑(不动); `JUDGE_HC=/workspace/review_scratch/health_check` 下 V4 书 28 个(A0,A0p,A1,A1s,A1e,A2,A3 × dyn/fix × s42/s2027)+ RAW_M1 参照 2 个 ⇒ 全判官可跑; `/workspace/uplift_2026-09-11/infra2/v4chain/` 四件 sha 与研究仓逐位同(common 7b6d49a3, judge 7f1aa5d6, v2 门 d63f4ec3, 合同 1188267a) | ssh pod2 `nvidia-smi --query-gpu`, `ps`, `ls`, `sha256sum` |
| F9 | 判官**不**自行绑定 `eligibility_contract`(只自行加 4 判书); 扩底后该名由调用方 entry 提供路径, require 只验「收据记的合同 sha == 该路径文件现 sha」, **不**验「== 判官自己读的合同」 | `judge_v4.py` L200-205 |
| F10 | 判官输出 `eligibility_by_arm[arm]["inputs"] = sorted(inputs)`; 现有检查 `r5_contract_sha_recorded` 断言 `inputs[-4:] == 4 判书` 或 `sorted[:4] == 4 判书`, 28 底下两者皆假(排序后 `base_*` 在前, `wide_fea_*` 在后)⇒ 该断言须按**意图**(判官绑上了 4 判书)重写 | `judge_v4.py` L206; `tests_pipeline_gates.py` L659-663 |
| F11 | `make_sha_manifest.py` 现产物 utc 2026-09-12T09:20:21Z, n_files 90, `POD2_UNQUERIED` 67(未给 POD2_SHA_FILE); `missing_sources []` | `receipts/v4_scripts_sha_full.json` |

## 2. 设计裁决(按事实)

- **D1 不引入 profile。** 依 F4/F5: 没有任何阶段合法地消费 BUNDLE_export 收据的**子集**; 唯二消费者一个传全集(v2 门), 一个传「调用方声明 + 4 判书」(判官)。profile 是「不同阶段合法消费不同子集」的机制(STEP1@v4 / @v4s), 这里没有这种阶段。G2_closure / STEP1 / STEP1@v4s / STEP1@v4 / STEP2 五条注册**一字不动**(向后兼容由现有 [E]/[J] 自检守着)。
- **D2 底 = v2 闭包逐名相同, 顺序照 diff。** 保留 `[7:11] == BOOK_INPUTS`(判官/自检依赖 BOOK_INPUTS 连续)。`femat` / `signal_receipt` **不入静态底**: 它们只在书注入 FEMAT 时被 v2 门注册(E6/E7), A1 真收据无此二名(F2); 入底会让所有无 FEMAT 的臂永远不合格。它们由 v2 门自身的 require 模式按盘上派生集强制(extras allowed, 判官那里「收据记了就验」)。
- **D3 `judge_v4.py` 不改。** 扩底不需要判官任何代码变化(它把调用方 inputs 直接交给 require); 保持 sha `7f1aa5d6…` == pod2 副本。F9 的缺口(判官自行绑合同)是**语义增加**, 超出本次授权, 登记为开(§6)。
- **D4 夹具扩到真形状。** `bound_entry` 写: 7 上游合成文件 + 4 判书 sha(hc, 既有)+ 4 **基线书 = hc 里 A0 的判书**(与 v2 门 `derive_paths` 同路径形状)+ 一个真形状 bundle 目录(8 文件 + `MANIFEST.json` = {文件: sha})+ costb/umask/slow 合成文件 + `eligibility_contract` = 判官装置副本旁的合同(`q/device/ELIGIBILITY_CONTRACT.json`, 不存在时退到归档合同)。为此 `judge_case` 把装置副本的写入挪到 eligibility 回调之前(仅顺序, 无语义变化)。调用方 entry 声明 24 名(28 − 4 判书, 判书由判官绑)。
- **D5 新增断言**(§3.2): (i) 真形状: 静态「底 == 真收据 registered_inputs 集 == 夹具集」+ 判官级「归档判官 + 已发货合同 + 以 v2 门 sha 签的 28 名收据 ⇒ 合格、4 PROMOTE、why 含 `registered floor BUNDLE_export=28`」; (ii) 单名否定: 28 名逐一漏掉 ⇒ require 拒(单元级, 真合同 + 真模块), 17 新名逐一漏掉 ⇒ 判官级不合格且 0 PROMOTE; (iii) 导出器签的 28 名收据在已发货合同下仍「not an approved source」(既有 r5→r6 用例保留, 加一条显式); 另加「记了 femat/signal_receipt 的额外名不影响合格」(extras allowed, FEMAT 臂形状)。
- **D6 pod2 对照 = 三格 + 旧码红**(用户规则 09-10): 同一真 A1 收据 + 同一 28 名 entry: (a) 旧 common(7b6d49a3)⇒ 合格, floor=11; (b) 旧 common + 漏 1 新名 ⇒ **仍合格**(缺陷本体, 旧码红); (c) 新 common ⇒ 合格, floor=28, 28 inputs verified, 且 A1 为 (C) UNDECIDED ⇒ 0 PROMOTE; (d) 新 common + 漏 1 新名 ⇒ **不合格**。全部在隔离目录 `/workspace/uplift_2026-09-11/w4_judge_floor/`, 不写冻结 review_scratch, CPU only。

## 3. 改动(file:line 见 §5 RESULT 表)

### 3.1 `v4_gate_common.py`
- `REQUIRED_INPUTS["BUNDLE_export"]`: 11 → 28(diff 逐字, 注释标 ROUND 6)。
- 模块 docstring 加 ROUND 6 段: 为什么扩、为什么不 profile、femat/signal_receipt 为何不入底。
- 其他函数零改动。

### 3.2 `tests_pipeline_gates.py`
- 夹具: `ELIG_INPUTS` 重构为 24 名(7 上游 + 4 基线书 + 清单 + 8 bundle + 4 杂项), `bound_entry` 写真形状闭包(D4); `judge_case` 装置副本前移(D4)。
- 既有检查意图全保留; 文本/断言按 F10 调整两处(`[r5] REQUIRED_INPUTS[BUNDLE_export]` 计数 11→28 且逐名断言; `r5_contract_sha_recorded` 的 inputs 子句改为「4 判书 ⊆ inputs 且 |inputs| = 28」)。
- 新增 [O] 段(D5)。

### 3.3 不动
`judge_v4.py`, `v4e_gate_export_v2.py`, `gate_signal_parity_v2.py`, `ELIGIBILITY_CONTRACT.json`, 所有 `chain_*.sh` / `launch_mwf_*` / `merge_mwf_*` / `pod_f10_*` / `pod_legs_*` / `pod_export_bundle_v4.py`(W3 在改)。`~/dl_quant_live`, `~/wide_shadow` 只读未触。

## 4. 复跑命令(逐字)

```
cd /Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/retrain_2026-09/v4_chain_2026-09-09
/usr/bin/python3 tests_pipeline_gates.py
/usr/bin/python3 make_sha_manifest.py
```
pod2 对照命令见 `receipts/judge_floor_2026-09-12/COMMANDS_pod2.txt`(逐字抄自实际执行)。

## 5. RESULT(2026-09-12 10:2x–11:1xZ; 数字全部来自收据, 路径相对 `multi_asset/exports/research/retrain_2026-09/v4_chain_2026-09-09/`)

### 5.1 改了什么(file:line)

| 文件 | 位置 | 改动 | sha256 |
|---|---|---|---|
| `v4_gate_common.py` | L36-43 | docstring 加 ROUND 6 段(为何扩、为何无 profile、femat/signal_receipt 为何不入底) | 7b6d49a3… → **f8f4fc0e6ca3a02f9c51383b72f553b5f8614b3be5f496f510bae9d43fe0df12** |
| 同上 | L66-74 | `REQUIRED_INPUTS["BUNDLE_export"]` 11 → **28**(顺序: 7 上游 · 4 判书 `[7:11]` · 4 基线书 · `bundle_manifest` + 8 `bundle/*` · `costb_json, umask_npz, slow_npy, eligibility_contract`); 其他五条注册及全部函数零改动 | 同上 |
| `tests_pipeline_gates.py` | L200 | `[r5→r6]` 底计数 11→28, 加前 7 名与 `[7:11]==BOOK_INPUTS` 逐名断言 | 我方独立版 7f79bda6…; **盘上现为与 W3 段合并版 615b26faf79521e9ea597d28c58a9ed4e3a2d958c224dcbb871594ff88bdce29**(W3 的 `[N] MONTHLY CHAIN` 段在 L817 起, 我方未触) |
| 同上 | L391-396 | `ELIG_UPSTREAM/ELIG_BASELINE/ELIG_BUNDLE_FILES/ELIG_MISC`; `ELIG_INPUTS` = 调用方声明的 24 名 | |
| 同上 | L399-425 | `bound_entry` 写真形状 28 闭包(D4), 新参 `extra_inputs` | |
| 同上 | L470-476 | `judge_case` 装置副本(含合同)前移到 eligibility 回调之前(仅顺序) | |
| 同上 | L672, L682-687 | 两条既有检查按 F10 重写断言/文本(意图不变: 判官绑上 4 判书; 导出器签的收据在已发货合同下不批准) | |
| 同上 | L723-788 | 新段 **[O]**(D5): 4 静态 + 3 单元 + 1 判官正控 + 17 判官单名否定 + 1 「发货预测被改」+ 1 导出器签 28 名 + 1 FEMAT 臂 extras = **29 条** | |
| `receipts/v4_scripts_sha_full.json` | 全文 | `make_sha_manifest.py` 重生成: utc 2026-09-12T11:08:55Z, n_files 94(含 W3 新增 `v4_months.py` 等), POD2_UNQUERIED 71(未给 POD2_SHA_FILE, 与 09:20Z 版同口径), missing_sources [] | e132bf50ff24e2423256328674bb105b26485d617e1ba4014504b30f1783c426 |
| `docs/DESIGN_judge_floor_28_2026-09-12.md` | — | 本文(新) | 见最终消息 |

**未触**(sha 与起步同): `judge_v4.py` 7f1aa5d6…, `ELIGIBILITY_CONTRACT.json` 1188267a…, `v4e_gate_export_v2.py` d63f4ec3…, `gate_signal_parity_v2.py` abc45cad…, 所有 `chain_*.sh` / `launch_mwf_*` / `merge_mwf_*` / `pod_f10_*` / `pod_legs_*` / `pod_export_bundle_v4.py`(W3 的, 本会话期间被 W3 改动), `~/dl_quant_live`, `~/wide_shadow`。

### 5.2 自检前后(`/usr/bin/python3 tests_pipeline_gates.py`, mac python 3.9.6 / numpy 1.26.4 / bash 3.2.57)

| 跑 | 文件状态 | 结果 | 日志 |
|---|---|---|---|
| 前 | 归档原样(common 7b6d49a3, tests b579346d) | **ALL PASS (151)**, 3m07s | `receipts/judge_floor_2026-09-12/tests_before_151.log` |
| 就地 run1 | 我方两文件已改, (iii) 单元检查首版规格错; W3 同时在改 `pod_f10_*`/`chain_lib.sh`/`pod_export_bundle_v4.py` | 179 条: 175 OK / **4 FAIL** = 3 条 W3 在飞文件([H] 再生成 ×1, [J] `local -n` bash 3.2 ×2)+ **1 条我方 (iii)**(v2 签的收据 pin 到导出器 sha 先撞 identity 「caller trusts」, 到不了 approval 检查 — 我的规格错, 非模块错) | `tests_after_inplace_run1_175ok_4fail.log` |
| 就地 run2 | (iii) 已修(导出器**签**且 pin 自身 ⇒ 「not an APPROVED source」); W3 文件仍在飞 | 180 条: 176 OK / **4 FAIL**, 全部 W3 在飞文件([H] ×2: trainer/refit/exporter 再生成≠归档; [J] ×2 `local -n`) | `tests_after_inplace_run2_176ok_4fail.log` |
| **隔离** | 归档目录整体复制到 scratch, W3 的 7 个已改文件回到 HEAD, 仅我方两文件不同(逐文件 cmp 核对) | **ALL PASS (180 checks)** = 151 + 29 | `tests_after_isolated_180.log` |
| 就地 merged | 盘上合并文件 615b26fa(我方 [O] + W3 `[N] MONTHLY CHAIN`), W3 称其修复已在 HEAD(~18:45 本地) | **ALL PASS (222 checks)** = 180(151 旧 + 29 我方 [O])+ 42(W3 段, 盘上 18:54 版); 29 条 `[r6]` 全 OK, 0 FAIL | `tests_after_inplace_merged.log`; 装置快照 `tests_pipeline_gates.merged_615b26fa.snapshot.py` |

W3 的 4 红与本改动无关(W3 已确认并称已修; 我方 grep 确认 `chain_lib.sh` L68 现为 `eval`, `local -n` 只剩注释)。

### 5.3 pod2 对照(CPU only; `receipts/judge_floor_2026-09-12/RESULT_pod2_cells.json` + `pod2_out/`)

装置: `/workspace/uplift_2026-09-11/w4_judge_floor/device_{old,new}/` = judge 7f1aa5d6 + 合同 1188267a + common(old 7b6d49a3 / new f8f4fc0e); 同一真收据 A1(4fe0495f…); `JUDGE_HC=/workspace/review_scratch/health_check`(只读); `/workspace/venv/bin/python` 3.11.10 numpy 2.4.6; GPU **0 %, 2 MiB** 于 10:20:33Z(前)与 10:21:28Z(后); PID 333197/339489 前后均在。

| 格 | common | entry 声明 | A1 | why(截) | 判决 |
|---|---|---|---|---|---|
| old_full28 | 7b6d49a3 | 28 | 合格 | `28 inputs verified, registered floor BUNDLE_export=11` | 18 判决, 0 PROMOTE |
| **old_omit_slowpred**(旧码红) | 7b6d49a3 | 27(漏 `bundle/slow_pred_pinned.npy`) | **仍合格** | `27 inputs verified, registered floor BUNDLE_export=11` | 18, 0 PROMOTE |
| **new_full28** | f8f4fc0e | 28 | 合格 | `28 inputs verified, registered floor BUNDLE_export=28` | 18 判决, **0 PROMOTE**; A1-A0 dyn/fix 均 (C) UNDECIDED |
| new_omit_slowpred | f8f4fc0e | 27 | **不合格** | `caller omitted registered input(s) ['bundle/slow_pred_pinned.npy'] for BUNDLE_export` | 18, 0 PROMOTE |
| new_omit_contract | f8f4fc0e | 27(漏 `eligibility_contract`) | **不合格** | `caller omitted registered input(s) ['eligibility_contract']` | 18, 0 PROMOTE |

A1−A0 冻结窗对照(n=3168)五格逐字节相同: dyn s42 Δ +0.0605 CI [−0.168, +0.287]; dyn s2027 +0.0478 [−0.171, +0.270]; fix s42 +0.0047 [−0.076, +0.087]; fix s2027 −0.0103 [−0.102, +0.088] ⇒ 扩底只动资格, 不动经济量(与预期一致)。

### 5.4 复跑命令
`receipts/judge_floor_2026-09-12/COMMANDS_pod2.txt`(逐字)+ §4。pod2 隔离目录 `w4_judge_floor/` 保留作装置(收据同寿命); 未写任何冻结目录。

## 6. 仍开(不在本次授权内; r20 §8 之外新增 F9)

1. **收据无签名**(r20 §8-1): `require` 比的是字符串; 扩底只是让判官多验 17 个文件的现 sha == 收据记的 sha, 手改收据仍能过。关法 = 签名或判官复跑 v2 门 `require` 模式。
2. **`HEALTH.device_sha256` 自报**(r20 §8-2): 书里的装置 sha 是装置自己写的; 判官/门都不复跑装置。
3. **F9: 判官不把 `eligibility_contract` 绑到自己读的合同**: 现在由调用方 entry 给路径, require 只验该路径文件未变; 「收据针对的合同 == 判官在用的合同」未被验。对称做法是判官像绑 4 判书那样自加 `inputs["eligibility_contract"] = CONTRACT_PATH`(一行, 但属判官语义增加 ⇒ 需 lead/用户裁定)。
4. **manifest 的 POD2 栏**未查(与 09:20Z 版同口径 UNQUERIED); W3 本会话仍在改同目录多文件, **lead 提交前须重跑 `make_sha_manifest.py`**。
5. **共享文件 `tests_pipeline_gates.py`** 现为两人合并版(615b26fa); 提交前 lead 应以「就地 merged 跑 ALL PASS」为准, 不以任何一方的独立副本为准。

## §8 第七轮(2026-09-12 11:3xZ, lead): §7 (3) F9 关闭 —— 判官自绑 `eligibility_contract`

**为什么现在做**: 用户字 09-12「按照最正确的逻辑全部做, 修复所有漏洞」; F9 是本文 §7 明写的漏洞: 第六轮把 `eligibility_contract` 放进 28 名底, 但**路径由调用方给**, require 只验「调用方指的那份文件自收据后未变」, 不验「收据针对的合同 == 判官此刻在用的合同」⇒ 一份在别的合同(或本合同早期版本)下签出的 PASS 收据, 只要调用方把名字指向那份文件, 判官就接受。

**改动(一处语义, 七行)**: `judge_v4.py` `_eligibility()` 在绑 4 判书之后加 `inputs["eligibility_contract"] = _CONTRACT_PATH`(判官读的合同文件); 调用方给了别的路径时记 `caller_contract_path`(透明, 不作为拒绝理由——拒绝由 require 的 sha 比对给出)。前身存 `judge_v4.r4_7f1aa5d6.py`(它写出了 §5 的 pod2 收据; 判决装置与结论同寿命)。合同文件 `ELIGIBILITY_CONTRACT.json`(1188267a)**未动**——它第 7 句本来就写「判官从自己目录读本文件, 无 env 可替代」, 本轮只是让 require 也执行这句。

**自检新节 [Q] 6 格**(`tests_pipeline_gates.py`; `judge_case` 新参 `judge_src` 可在装置副本里跑归档判官):
| 格 | 情形 | 期望 | 结果 |
|---|---|---|---|
| (i) | 门对**另一份合同**(加一键, 批准表相同)签收据, 调用方把 `eligibility_contract` 指向它 | 不合格, why 命名 `'eligibility_contract' changed since the receipt`, 记 caller 路径, 0 PROMOTE | OK |
| (ii) | 同上但那份文件是判官合同的**逐字节副本** | 仍合格(绑的是 sha 不是路径), 28 输入 verified, 4 PROMOTE | OKI |
| (iii) | 出厂合同 + 归档判官 + v2 签名的全 28 收据, 但合同 sha 是另一份的 | 不合格, 判官合同 sha = 1188267a…, 0 PROMOTE | OKII |
| (iv) | **旧码红**: `judge_v4.r4_7f1aa5d6.py` 在装置副本上跑情形 (i) | 合格 + 4 PROMOTE(旧判官验的是调用方的文件) | OKV |
| (v) | 静态: 在役判官含绑定行; 快照 sha 以 7f1aa5d6 开头且不含绑定行; 合同第 7 句仍在 | 三真 | OK ×2 |

**[O] 一格改标**: 第六轮的「调用方漏报 `eligibility_contract` ⇒ 不合格」在第七轮语义下反转为「仍合格」(该名已同四判书一样由判官绑定, 调用方漏报由判官补, 收据仍须散列过判官的那份合同); 首跑 227/228 正是这一格红, 改标后全绿。这不是放宽: 调用方**指错**仍拒((i)/(iii)), 只是**不指**不再是拒绝理由。

**全套件**: 修前(W3+W4 合并, lead 复跑)**ALL PASS (222 checks)**(`receipts/monthly_chain_2026-09-12/tests_pipeline_gates_lead_merged.log`)→ 加 [Q] 后 **ALL PASS (228 checks)**(`…/tests_pipeline_gates_lead_r7.log`)。judge_v4.py sha 7f1aa5d6 → f6850dc3215f。

**未做/仍开**: 合同文本第 8 句 (e) 只提「四判书」不提「合同自身」——文本落后于代码一句, 但改合同 = 改 sha = 需用户字, 记为下次合同修订项(RULINGS_requested 追加 R-9)。
