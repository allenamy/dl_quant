> **创建:** 2026-09-16 05:3xZ | **Session:** lead | **状态:** 双臂完成; 判决见 §4(含一条**推翻自己冻结判据**的说明) | **作废条件:** 同题更晚双臂受据

# RESULT — fx-exec 电池两格红 = 树外前置条件缺失(非分支回归)

**预注册:** `PREREG_clone_red_is_environmental_2026-09-16.md` sha256
`63ae5601ee81cddfddaa01138abb1689501759e24d488da83d953054dc7dc8d3`(提交 b56636ba, 冻结于任何臂运行之前)。

## 1. 装置
全新克隆两棵, 同 head `f7e8e3a8`, 同解释器 `/usr/bin/python3`(3.9.6), **不碰正在跑电池的那棵树**。
两臂**代码逐字节同一** —— `git status` 唯一差异是 `state/notify_audit.jsonl`(数据账本)与新增的合成 `.env`;
`git diff --stat` 无任何代码文件。

| | ARM-0 | ARM-1 |
|---|---|---|
| `.env` | 无 | 合成假值 2 行(**未拷生产密钥**) |
| `state/notify_audit.jsonl` | 1047 行, 最新 2026-08-26T02:24Z | 1986 行(自生产拷入), 最新 2026-09-16T04:45:58Z |

## 2. 结果(与预注册逐格对照)
| 套件 | 预期 ARM-0 | 实测 ARM-0 | 预期 ARM-1 | 实测 ARM-1 |
|---|---|---|---|---|
| `tests_env_loading` | 10/15, [B] 五格 FAIL | **10/15, [B] 五格 FAIL** ✓ | 15/15 | **15/15** ✓ |
| `tests_alarm_digest` | FAILURES=['★★★ last-24h push discipline'] | **同, 32 格** ✓ | ALL PASS | **ALL PASS, 33 格** ✓ |

## 3. ★ 我自己的证伪条件触发了 —— 以及为什么最终推翻它
预注册 §4 第三条: 「两臂**检查总格数**不同 ⇒ 报 INCONCLUSIVE, 不报通过」。
`tests_alarm_digest` 是 32 vs 33, **该条触发**。

逐格 diff 后, 格数差被**双射地**解释清楚, 且只有这一个 hunk, 其余 31 格逐字节相同:
- ARM-0(窗口不可观测): 发出**一格占位** `★★★ last-24h push discipline`, 判 FAIL, 判词
  「only 0 readable alarms in 24h — **NOT OBSERVABLE, not a pass**」;
- ARM-1(窗口有数据): 这一格占位被它所代表的**两格具名检查**取代 ——
  `★★★ nothing PUSHED in the last 24h that the rules do not class as DECIDE` 与
  `★★ ...and suppression does real work WHEN THERE IS WORK`。

我写这条证伪条件, 是为了抓「补上前置条件顺手换进一套更容易的检查集」。此处不是那回事:
1 格占位 ⟷ 它点名的 2 格, 其余全等。**故判两臂仍可比, 结论成立。**

这条明确记为**带说明地推翻自己冻结的判据**, 不是悄悄放行。且该证伪条件起了作用 ——
它逼我去看, 而看到的东西比干净通过更重要(见 §5)。

## 4. 判决
**命题成立**: 两格红由树外前置条件缺失造成, **与 fx-exec 分支的任何代码改动无关**。
fx-exec head `f7e8e3a8` 在本项上**被开脱**。

## 5. ★ 但由此暴露两件更重要的事

### 5.1 一格**诚实的红**与一格**不诚实的红**
两格红的环境成因相同, 行为却相反:
- `tests_alarm_digest` **诚实**: 明确区分「不可观测」与「不通过」, 判词自己写着
  「NOT OBSERVABLE, not a pass」, 并把不可评估的两格收缩成一格占位。
  这正是 GATE B-REPRO 要求的纪律(**失败即报 UNAVAILABLE, 绝不顶替**)。**保留, 作范本。**
- `tests_env_loading` **不诚实**: 同一个环境缺失, 它报 FAIL, 读者无法从判词分辨
  「代码没接 loader」与「树里没有 .env 可载」。

### 5.2 ★★★ 一道**空转的变异控制** —— 变异控制只在基线为绿时才有意义
`tests_env_loading` [E] 的逻辑是「删掉 loader ⇒ 不再填充 TELEGRAM_* ⇒ 判变异被杀死」。
在 ARM-0 里:
- [B] 已记录**未变异**的 `ops/unseed_rehearsal_halt.py` **不**填充 TELEGRAM_*;
- [E] 又把「删掉 loader 后不填充」记为杀死成功。

**两处是同一个观测值。** 变异前后同值, 这道控制在 ARM-0 中**毫无鉴别力, 却判通过**。
ARM-1 里 [B] 转绿, [E] 这才真正有了鉴别力。

**该套件从不断言基线为绿就去跑变异。** 这是比"假绿"更隐蔽的一种:
**假绿的控制** —— 它本身是我一直拿来当黄金标准的那件东西。
一般形式: **形如「变异 ⇒ 翻红」的红能力检查, 在基线已经是红的时候恒真。**
凡红能力检查, 必须先断言基线为绿, 否则报 UNAVAILABLE。

## 6. ★ 对电池计数纪律的后果(KB-73 的推广)
KB-73 说电池计数只在**同一解释器**下可比。本受据把它推广一格:

> **电池计数只在同一「树外状态」下可比。** 同一份代码, 生产树 135/135,
> 临时克隆 133/135 —— 差的两格与代码无关, 只因克隆没有 `.env`、
> 且 `state/notify_audit.jsonl` 是 21 天前的快照。

**任何跨树的电池计数比较, 未声明树外状态即作废。**

## 7. 顺带自证: [A] 的「人口要算不要打」确实在工作
生产树该套件 14 格, fx-exec head 15 格。差的一格**不是有人手加的检查**, 而是
`alarm_capable()` 算出的人口从 4 个文件涨到 5 个 —— `ops/notarize_ledgers.py` 被接上了
`_envfile.load()`, [B] 于是自动多长出一格。[A] 的判词原话正是
「人口必须是**算出来的, 不是打出来的** —— 手写清单每有人写个新工具就过期一格」。

## 8. 待办(本受据产生)
- `FX-EXEC ENVRED-1`(P2): `tests_env_loading` 在 `.env` 缺失时须报 **UNAVAILABLE**(独立退出码),
  不得报 FAIL; 且 **[E] 必须先断言 [B] 基线为绿**, 否则该红能力检查报 UNAVAILABLE。
- `FX-EXEC ENVRED-2`(P2): 电池 runner 在 KB-73 解释器记录旁, 追加**树外状态记录**
  (`.env` 有无、`notify_audit.jsonl` 行数与最新时戳距今小时数), 使跨树计数可判可比。
- `GEN-4`(P1, 跨线): **全库排查形如「变异 ⇒ 翻红」而不先断言基线为绿的红能力检查。**
  这类控制在基线已红时恒真。owner: 待派。

## 9. 复跑命令(逐字)
```
SP=<scratchpad>/envred
git clone --no-hardlinks ~/cc_tmp/fx_exec $SP/arm0 && (cd $SP/arm0 && git checkout f7e8e3a8734ea96c807b533d760612ccf30ec07b)
cp -R $SP/arm0 $SP/arm1
printf 'TELEGRAM_BOT_TOKEN=DUMMY_NOT_A_REAL_TOKEN_0000000000\nTELEGRAM_CHAT_ID=-1000000000000\n' > $SP/arm1/.env
cp ~/dl_quant_live/state/notify_audit.jsonl $SP/arm1/state/notify_audit.jsonl
for ARM in arm0 arm1; do for S in tests_env_loading tests_alarm_digest; do
  (cd $SP/$ARM && env -u TELEGRAM_BOT_TOKEN -u TELEGRAM_CHAT_ID /usr/bin/python3 live/$S.py > $SP/${ARM}_${S}.out 2>&1; echo "$ARM $S exit=$?")
done; done
```
