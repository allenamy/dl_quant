> **创建:** 2026-09-13 15:1xZ | **Session:** FX-TRAIN (fix worker, team-lead dispatch; session b9646a9e) | **状态:** 执行中 — one section per item, appended as each item's commit chain lands; independent review pending for every section | **作废条件:** a cited commit is reverted, or a cited file's sha changes without a new section here

# REPORT_FX_TRAIN — October retrain chain fixes (AUDIT_TRAIN 7e1ecf9a)

Fact table: `docs/fixprogram_2026-09-13/FX_TRAIN/FACT_TABLE_TRN.md` (sections are committed before the code of the item they describe).
Device dir: `C/` = `multi_asset/exports/research/retrain_2026-09/v4_chain_2026-09-09/`. Chain test logs: `C/receipts/fx_train_2026-09-13/`. Fact-table devices and pod2 receipts: `docs/fixprogram_2026-09-13/FX_TRAIN/{devices,receipts}/`.
Method for every code item: pre-fix source archived beside the current one as `<name>.r<N>_<sha8>.<ext>`; a new test block runs pre-fix (RED) and fixed (GREEN) on the same input in one run; the block is also run standalone against a pristine copy of the pre-fix directory to show the red is for the right reason; full suite re-run; `fx_ast_retention.py` proves every old top-level test statement is retained verbatim and in order.

Baseline (before any FX-TRAIN change): pristine copy of C/ at the audited shas (111 files, 0 mismatches vs `receipts_train/SHA256SUMS_v4_chain_dir.txt`) — `tests_pipeline_gates.py` a3af858d **ALL PASS (392 checks), rc 0**, 14:43:08Z-14:50:50Z (`C/receipts/fx_train_2026-09-13/baseline/baseline_tests_392.log`). A first attempt without the parent file `T/pod_export_bundle_v3.py` failed the [H] exporter-regeneration cell on a missing fixture (FileNotFoundError); kept as `baseline_tests_attempt1_missing_parent_v3.log`, not a finding.

---

## TRN-19 — bare parser output line exported as `R=R` (+ sibling: the dryrun negative control trusted its interpreter's rc 0)

**Problem.** `load_month_env` re-validates the parser's output in bash after rc 0, but splits each line with `${line%%=*}` / `${line#*=}`; a line with no `=` gives key == value == the line, so a bare `R` passed every check and was exported as `R=R` (FACT_TABLE 19.1-19.7). Needs a broken or substituted `$PY` (the real parser always prints `KEY=VALUE`). The red run found a sibling in the same family: the dryrun negative control (a) used the derivation program's rc 0 as the only evidence that every derived path lies under its empty root, and (b) used its receipt program's rc 0 as its verdict without checking the receipt exists (FACT_TABLE 19.8-19.9).

**Fix.**
- `C/chain_lib.sh` 4ee217e1 → 1add6df7: one guard before the split — `case $line in *=*) ;; *) … die month_env_parser_output_<file> 4 ;; esac`. Nothing else in the loader changed.
- `C/chain_v4_monthly_dryrun.sh` 407aa438 → 1d6ae66a: (a) after derivation, bash (no interpreter) re-checks every derived line: KEY=VALUE, a registered key exactly once, all keys present, `R == <scratch>/root`, `PY ==` the chosen interpreter, every non-label key under `<scratch>/root/`; any violation ⇒ rc 2, driver not run; (b) rc 0 of the receipt program counts only if `dryrun_receipt.json` exists and says `"PASS": true`, else rc 1.
- Pre-fix sources archived: `C/chain_lib.r3_4ee217e1.sh`, `C/chain_v4_monthly_dryrun.r3_407aa438.sh` (bytes = the committed pre-fix versions; the [V] block asserts both shas).

**Tests.** New block [V] TRN-19 in `C/tests_pipeline_gates.py` (14 cells; every cell runs pre-fix and fixed on the same input):
- V1 (reviewer's exact probe) stub interpreter prints 45 valid lines + bare `R` ⇒ pre-fix rc 0, MONTH_ENV_OK, `R=R`; fixed rc 4 `FAIL_month_env_parser_output`, names the missing `=`, no MONTH_ENV_OK.
- Neighbours: bare `SEEDS` (pre-fix rc 0 `SEEDS=SEEDS`; fixed rc 4); 46 lines + bare unregistered word (both rc 4; fixed names the missing `=`); 46 lines + `=R` (both rc 4, character-class check unchanged).
- Positives: a stub printing exactly the true 46 lines ⇒ both rc 0 with the identical exported environment; the real parser on the September contract and the October template ⇒ both rc 0, identical environment.
- Inheritor: the dryrun with the bare-R interpreter ⇒ fixed rc 2 before any driver run.
- Static: the `*=*` guard is the code line immediately before the only split.
- Sibling V9: interpreter prints a contract whose paths point below a never-created foreign root as the "derived env" ⇒ pre-fix dryrun ran the DRIVER against it and exited rc 0; fixed rc 2 `derived env REFUSED` naming R, driver not run. V10: interpreter exits 0 from the receipt program without writing a receipt ⇒ pre-fix rc 0 with no receipt; fixed rc 1. Positive: the real interpreter ⇒ both dryruns DRYRUN_PASS rc 0.
- No cell can write anywhere real: every stub path lies below a temp dir that is never created (E-0912-B rule); the one real-interpreter dryrun derives its env under a temp root.

**Red evidence (for the right reason).** The [V] block run standalone against a pristine pre-fix copy (both "old" and "current" = pre-fix): **7 FAIL / 7 OK**, rc 1 — V1/V2 fail because the loader accepts the bare key (rc 0), V3 because the refusal names the unregistered key, not the missing `=`, V7/V9 because the dryrun exits rc 0 and runs the driver, V10 because it exits rc 0 with no receipt, V8 because the guard line does not exist; the snapshot, setup, `=R` and positive cells pass. No crash, no missing fixture (`V_trn19_on_PRE_fix_RED.log`). Same on pod2 (bash 5.1.16): 7 FAIL / 14 (`V_trn19_pod2_pre.log`).

**Green.** Block on the fixed sources: **ALL PASS (14)** on the Mac (bash 3.2) and on pod2 (bash 5.1.16) (`V_trn19_on_FIXED_GREEN.log`, `V_trn19_pod2_fixed.log`). Full suite on the fixed copy: **ALL PASS (406 checks) = 392 + 14, rc 0**, 14:57:59Z-15:04:53Z, source shas identical at start and end (tests 31cd958c…, chain_lib 1add6df7…, dryrun 1d6ae66a…) (`tests_full_trn19_fixed.log`). AST retention vs a3af858d: 174/174 old top-level statements retained verbatim and in order, 0 changed, 7 added (`ast_retention_trn19.json`).

**Positive control on real data.** Not applicable beyond the positive cells: the change touches only the parser-output re-validation and the negative control; both delivered contracts load to the identical environment under pre-fix and fixed sources, and the real-interpreter dryrun passes unchanged.

**Not proven / boundary.**
- An interpreter that lies consistently (returns a well-formed foreign contract to the driver's own `load_month_env` and exits 0 from every gate program) can still direct the driver at arbitrary paths; no bash-level check removes that. Interpreter identity is not pinned anywhere in the chain (preflight records `PY` by path only).
- Not exercised by a real month run through the driver (none is possible before the October inputs exist).

---
## TRN-27 · 裁定文档点名了被取代的批准对象, 且带一张 6/6 陈旧的装置 sha 表(提交 98cc9f0f, 事实表 bc5d4bf2; 未经独立复审; lead 逐字转录 2026-09-16 04:0xZ)

**问题。** `RUNBOOK_monthly_retrain_2026-10` §0★ 要用户批准 `0fe5ec55…`(修订 4)、随后 `b2f9cfd4…`(修订 5)作为 STEP2_m 对象, 而盘上的文件自 09-13 起已是 `d99a9109…`; 对该文件 `grep -c d99a9109` 返回 **0**。全部八条事实都是今天用 `shasum -a 256` 亲测, 不是从审计搬来的(FACT_TABLE_TRN §TRN-27 行 27.1-27.8)。

**让它不止于「文字瑕疵」的那一点。** 我读的是 `diff v4_gate_step2_m.r2_b2f9cfd4.py v4_gate_step2_m.py`, 不是修订说明。`b2f9cfd4` **先**把成员索引转成 int64 再校验转换结果, 于是 `[False, True]` 变成 `[0, 1]` 并 **PASS** —— 而 `pod_export_bundle_v4.py` 用**持久化的**数组去下标 `y4[i, m]`, 会抛 IndexError。`d99a9109`(AMENDMENT 3)先在存储对象上检查 dtype kind, 直接拒绝 bool/float/object/string, 确认有效之后才转换。**批准 runbook 所点名的那个 sha, 等于批准一个会放行「导出器一碰就崩的输入」的门。**

**其他实测事实。** §0★ 的装置 sha 表 **6/6 陈旧**(声称 ffbb89b8 / ee0af0c0 / 29611dbc / 2563446d / db5839e4 / e1dec02b; 实测 1add6df7 / 2369a87d / 16bfdb7e / dbab81e0 / 683675d1 / c34aace9), 而那一行本身已经写着叫读者别信这张表。STEP1_m 那半是对的(L76 = 实测 79950786), 所以修复不动它。同族站点: `v4_month_2026-10.env.template` L50 重复了同一个陈旧对象。**该缺陷 fail closed** —— 合同两个月度门都没批准, 所以无论文档怎么写, 预检都会拒绝; 代价是**一次被浪费的裁定**和十月被推迟, 不是一个坏 bundle。

**修复。**
- **RUNBOOK §0★ 修订 6**, 带一个可机检的声明块: 两条 `APPROVAL_OBJECT` 行(一次裁定必须写进合同的**恰好**是什么)与两条 `SUPERSEDED_OBJECT` 行(存在文件的红控快照)。`455e3df4` 在散文里被点名为**没有存档文件因而无法被验证**的历史 —— **说出来而不是悄悄丢掉**。修订 4/5 逐字保留为它们本来的历史。同一节还带上另外三个十月决策(NONE clamp 开关; 导出基线 TRN-15; fea89 builder TRN-16 连同它被迫带来的后果 —— 追加式月滚动, 以及 2026-08-31 那 229,824 个 holefix2 填充格**不得**被现已可得的 vendor 存档替换)。
- **冻结 sha 表被删除**, 换成测量命令加上已提交的清单。**一张按构造就会过期、而且已经自我免责的表是纯粹的危险品。**
- **模板注释**现在点名 `d99a9109` 且不再复述任何旧 sha; 修复前的模板存档为 `v4_month_2026-10.env.r1_dc94784e.template`。
- **新门 `v4_doc_approval_gate.py`**(收据 `DOC_APPROVAL_IDENTITY` 经 `v4_gate_common.finalize`; `DOC` / `DEVICE_DIR` / `CONTRACT` / `DOCGATE_PROFILE` / `DOCGATE_OUT` 全部必填, 无默认)。**A1**: 被声明的批准对象必须等于被测量的文件, 而**截断的 sha 被拒为「一个标签, 不是一个身份」** —— 8-hex 的习惯正是错对象被引用的途径。**A2**: 每一个尚未进入合同的月度通用门, 必须以其实测 sha 恰好声明一次。**A3**: 文档提到的每一个存档快照 sha 都需要一条 `SUPERSEDED_OBJECT` 声明; 点名存档**文件**可豁免, 因为那是无歧义的。**A4**: 一个 sha 若与某个装置文件名之间只隔分隔符, 它就是关于该文件的声明; 再远一点的只报告、永不裁决 —— **门不猜散文的意思**。`DOCGATE_PROFILE` 必须显式给出(`ruling` / `reference`); `reference` 把 A2 记为 `NOT_APPLICABLE` 并附理由, 而不是静默通过。被取代的声明本身还被分类为「有存档可验」与「不可验」两类并计数, 使那条豁免可见。

**红, 且红对了理由。** 修复前的 RUNBOOK 跑出 **rc 3**, A2 + A3 + A4 同时失败: 两个月度通用门未声明、五处裸提被取代的 step2_m sha(L62 / L76 / L80 / L91×2)、六个陈旧装置 sha 以「声称 vs 实测」成对列出。修复前的模板 **rc 3**(L50 上的 A3)。把新 [W] 块跑在一份携带修复前模板的纯净链目录副本上: **W12 单独 FAIL, rc 1**, 13 格中 12 格绿 —— **无崩溃, 无缺失夹具**。收据: `FX_TRAIN/receipts/trn27/RED_prefix_{runbook,template}.{json,log}` · `W_block_on_PREFIX_template_RED.log`。

**绿。** 修复后的 RUNBOOK 在 `ruling` 档 **rc 0 PASS**, 修复后的模板在 `reference` 档 **rc 0 PASS**, 两条被取代声明都对着各自存档验过。新 [W] 块 13/13。**整套 `tests_pipeline_gates.py` ALL PASS(419 项检查), rc 0**(= 406 + 13), 03:23:04Z–03:26:52Z, 起止源码 sha 相同(tests `10b00289`, gate `f3a94cd5`, template `b19495c2`)—— **我读的是汇总行与退出码, 不是「任务完成了」**。对 `31cd958c` 的 AST 保留: **181/181** 旧顶层语句逐字且按序保留, 0 改动, 6 新增。`make_sha_manifest.py` rc 0。

**未证明 / 边界。**
- 这道门只能对它在装置目录里**量过**的文件说话。匹配不上那里任何文件的 hex 记号(提交 sha、收据 sha、别处的文件 —— runbook 里有 21 个)被记为数据, 不参与裁决。像 `455e3df4` 这样没有存档文件的红控, **永远只能是一条不可验证的声明**。
- 真正的 RUNBOOK 由已提交的收据检查, 而不是由可移植套件检查: `tests_pipeline_gates.py` 在 pod2 上从一个复制目录运行, 那里 `docs/` 并不存在, 所以套件到处都带着的唯一真实工件是十月模板。若要每次套件运行都检查 runbook, 需要在月合同里加一个 doc 路径键 —— **我没有加这个合同键**([P]/[U] 各格逐字钉住 46 个键)。
- A4 的邻接规则是关于散文的启发式, **故意偏向少声称**: 它只在「文件名 sha」这种表格形状上触发, 其余一律报告而不失败。**一个写在句子里而不是表格里的陈旧 sha 不会被抓到。**

### 顺带发现(lead 已登记为 **TRN-28, P1**)
`pod_f10_np_export.py` 在**它自己的 V1 门决定之前**就写出可部署的 npz(`np.savez` 在 L56, 然后才 `sys.exit(0 if ok else 3)`), 而在其默认 `F10_OUT` 下, 那条路径**就是在役工件本身**。所以一次失败的 V1 门仍会在实盘路径上留下一个完整、可加载的模型, 并覆盖原先那个。**这比审计的「产生在所有门之外」更锋利: 门是存在的, 只是它的判词不控制写入。**
