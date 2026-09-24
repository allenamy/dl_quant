> **创建:** 2026-09-24 06:5xZ | **追加:** 08:0xZ(本文 11 项已被实测降级为「非缺口主要来源」, 见开头 ★ 节) | **Session:** session_01MCyx6gj5EdbghE9bwjBjJv(news2) | **状态:** **第 2 步(逐段语义对照)完成; 第 3 步优先级已降低, 其 legal 阻塞已解除** | **预注册:** `docs/PREREG_legs_diff_NEW_vs_NC_2026-09-24.md` | **作废条件:** 两份腿代码任一 sha 改变

# 研究员 NEW 的 `combo_legs.py` 与 NC 的 `nc_legs.py`:逐段语义对照

**只报差在哪、差多少。不下「这就是缺口原因」的结论**(lead 2026-09-24 明令)。

## ★ 后续结论(2026-09-24 追加,写在前面免得本文的 11 项被当成活线索)

本文编目的 11 处差异**真实存在,但已被实测降级:它们不是 NEW↔NC 缺口的主要来源。**

- **腿数组直接对照**(`receipts/LEGS_ARRAY_DIFF.json`,提交 `7ac31b9fe`):`Z24`(rev24)pearson 1.0、2022-24 全锚逐位相同;`ZFD`(fund)0.9939–0.9999;**只有 `KZ`(king)差**(pearson 0.764/0.799/0.861/0.903,逐位相同锚 0)。判据窗内 `ready` **逐锚完全一致**。
- **`KZ` 的差继承自 King 预测本身**(`receipts/KING_OOF_DIFF.json`,提交 `3ae90ec9b`):King OOF spearman 0.7868/0.8102/0.8658/0.9065 与 KZ 腿的 0.7644/0.7989/0.8614/0.9039 **量级相同** ⇒ 腿代码不是主要来源。
  - ⚠ 该提交信息里"腿代码贡献 ≤0.02"一句**已撤回**(过度精确):两个 spearman 不在同一位置集上(KZ 在成员位置,King OOF 在全部有限位置),相减无效。站得住的只有定性结论;要净贡献须在同一位置集上重测。
- **而且两个 King 一样好**(`receipts/KING_IC_HEADTOHEAD.json`,提交 `7a3342d69`):同目标同位置集配对 rank-IC 只差 0.001–0.002,四年里两年 t<1.5。所以缺口**不在分数层技能**。

⇒ 本文第 3 步(在 NC 输入上各跑一遍逐数组比)的**优先级已降低**:它现在只会去确认"腿代码不是来源"。另:第 3 步原先被"缺全宽 `legal`(重建约 7 小时)"卡住,**该阻塞已解除**——研究员 `funding_state.npz` 里就有全宽 `legal` 与 `ema`,sha 与 `TARGET_RECEIPT_s42.json` 记的 combo 输入一致。

## 0. 对象与参照

| | sha256 | 核对 |
|---|---|---|
| 研究员 | `combo_legs.py` `0fc84ae8462f948c8b850eca376abfc2f8d5913500ac0c98a6e5e3a11f6e303b` | 与 `FILES_SHA256.tsv` MATCH |
| NC | `nc_legs.py` `18387627f8426a45135b348dd4508281b4811894c91eb50af87751760609c0a0` | 与 `P3_LEGS.json` `source_sha` MATCH |
| 生产参照 | 发布树 `treeNC5` `shadow_loop_v3.py` `a68c7a5f` | 12 个源文件与发布树逐位相同(集成代理核过) |

`combo_legs.py` **不存在于** NC 的装置目录。两边是两份独立实现。

## 1. 差异表

行号: 研究员 = `combo_legs.py`; NC = `nc_legs.py`; 生产 = `treeNC5/shadow_loop_v3.py`。

| # | 项 | 研究员 | NC | 哪边与生产一致 |
|---|---|---|---|---|
| 1 | **腿收益累加的 dtype** | L63 `block.astype(np.float64)`, 在 **float64** 上求和 | L45-47 `seg` 为 **float32**, `np.where(fin,seg,0).sum(0)` 在 float32 上 | **NC**。生产的窗口内核在 float32 上累加(`wstat` 的 `s_.astype(np.float32)` 回舍, L672-673); NC 的 docstring L3 明写「float32 arithmetic as the producer does it」 |
| 2 | **收益通道来源** | L58 `market/returns.npz['R']` | L45 `I.R`(NC 合同的 rr = 生产者 `CDf[:,:,0]` 经 A3) | NC 自称二者同物(docstring L3「the researcher's R」)。**未实测**, 列为第 3 步要核的项 |
| 3 | **资金费秩基的定义** | L37 `base = legal & isfinite(funding)` | L65 `base_val`(= `legal ∧ crypto ∧ axis ∧ fresh known EMA`, docstring L5) | **NC**。生产有专门的 `xz_in_base`(L113-123), 其 docstring 明写基是「全场所有**新鲜结算**的名」。研究员的基**不含 crypto、axis、fresh-known-EMA 三个条件**, 因此更宽 |
| 4 | **秩变换函数** | L11-14 自带 `xz` | L20-26 从**生产树文本**抽 `xz_in_base` 与 `xz`(并断言 sha) | **两边都与生产一致**。研究员的 `xz`(L11-14)与生产 `xz`(L791-795)**逐语义相同**: 同一有限掩码、同一 `>=10` 门、同一 `rankdata/(n-1)-0.5`, 仅变量名不同 |
| 5 | **席位窗口长度 `look`** | L16 默认参数 `look=900`(硬写) | L57 `P["msharpe_look"]` 读配置, **实测值 900** | 数值相同。差别只在**来源**: 硬写 vs 配置 |
| 6 | **席位公式** | L41-43 `s = max(r.mean(0)/(r.std(0)+1e-9), 0)`; `seats = s/s.sum()` 否则 1/3 | L58-63 `shp = r.mean(1)/(r.std(1)+1e-9)`; `max(shp,0)`; 同式 | **相同**(只是转置) |
| 7 | **腿收益台账的入账条件** | L24 `if i and ready[i-1]` —— 只要上一锚 ready | L43 `prev is not None and prev["anchor_ts"]==last_anchor and A-last_anchor==14400` —— **额外要求 4h 连续** | NC 更严。生产逐锚推进, 不跨缺口, 与 NC 的连续性要求同向 |
| 8 | **可用性门(readiness)** | L34 `len(m)<50`; L35 `len(m)<10 or not finite(pred).all()`; L38 `len(base)<10` | L42 `len(m)<50`; **L68 `sel.sum() < sel_min`(流动性门)**; L69 `finite(pred).all()`; L70 `len(base_vals)<10` | **NC**(已核, 见 §2.1)。生产**有**这道门: `shadow_loop_v3.py` L800-803 与 `combo_stage.py` L70-75 同式。**研究员没有它, 所以在这一项上偏离生产的是研究员** |
| 9 | **rev24 来源** | L65 `v[:,:,1]`, 取自 `data/values40.npz['V']` | L66 `F["rev24"]`, 取自 `NC_FEATURES.npz` | 两边都做 `xz(-rev24)`。**来源不同**; 两边都没有额外的 rev24 掩码 |
| 10 | **输出数组集合** | `KZ Z24 ZFD WL ready LR seat_priced_fraction` | `KZ Z24 ZFD WL ready LR QV RN8` | `QV`/`RN8` **只有 NC 有**; `seat_priced_fraction` **只有研究员有** |
| 11 | **RN8(FTRIM)** | 不产出 | L74 `NC.funding_asof(...)[3]`(12h 新鲜度, 已知间隔) | NC 的 docstring L6 明写「不是 ledger tail」。研究员侧无对应物, 无法比 |

## 2. 与生产一致性的小结(可核, 非我的判断)

- **NC 与生产一致的项**: 1(float32 累加)、3(秩基用 `xz_in_base`)、4(函数取自生产树并断言 sha)、7(连续性)。
- **两边都与生产一致的项**: 4 的 `xz` 本体。
- **未实测的项**: 2(两个 R 是否同物)。

### 2.1 第 8 项已核:生产**有**这道门, 我先前的「未找到」是搜错了表示

lead 要求列出搜过的词。搜了: `250000` / `qv4h_min` / `qv4h` / `sel_min` / `min_members` / `expm1` / `qvm`。

| 位置 | 行 | 内容 |
|---|---|---|
| `shadow_loop_v3.py` | 800 | `qv4h = np.expm1(np.clip(qvm[m], 0, 30)) * 48` |
| `shadow_loop_v3.py` | 801 | `sel = qv4h >= P["qv4h_min"]` |
| `shadow_loop_v3.py` | 802-803 | `if sel.sum() < P["sel_min"]:` → `append_log({"e": "anchor_skip", ... "reason": f"sel {int(sel.sum())}<{P['sel_min']}"})` |
| `combo_stage.py` | 70 | 注释 `# sel: qv4h 门(与 run_anchor 同式)` |
| `combo_stage.py` | 74-75 | 同一 `qv4h` 与 `sel = qv4h >= P["qv4h_min"]` |

⇒ **NC 的流动性门与生产逐式相同**(连参数名都一样), 生产在 `sel.sum() < sel_min` 时**跳过该锚**。**研究员没有这道门。**

**我先前写「未找到」的原因**: 字面量 `250000` **不在源码里** —— 它是配置参数 `qv4h_min` 的值。只搜字面量会得到一个**假的「未找到」**。这是今晚同一形状的又一例: **搜的是值的一种表示, 而不是它在代码里的表示**。lead 要求「写明搜过哪些词」正是防这个 —— 若我只报「未找到」而不列词, 这个错误不可能被发现。

## 2.2 消费者普查(lead 点 2):同样的差异, 落在不同消费者上分量完全不同

| 输出 | 谁读它 | 行号 |
|---|---|---|
| `KZ` | 组合 `evolve` | `news2_combo.py` L59; `continuous_combo.py` L78 |
| **`ZFD`** | **组合 `evolve` + F10 训练** | `news2_combo.py` **L59**; `news2_train_f10.py` **L80**; `continuous_combo.py` L78 |
| `WL` | 组合 `evolve` + F10 训练 | `news2_combo.py` L59; `news2_train_f10.py` L80; `continuous_combo.py` L78 |
| `Z24` | **只有 F10 训练** | `news2_train_f10.py` L80 —— **不在 `evolve` 的参数里** |
| `QV` / `RN8` | 只有组合 | `news2_combo.py` L60 |
| `ready` | 组合 + F10 训练 | `news2_combo.py` L60; `news2_train_f10.py` L81; `continuous_combo.py` L78 |
| **`LR`** | **无人读** | 组合与 F10 路径里检索不到。它只在 `nc_legs.py` 内部用于算 `WL`(席位), 所以 `LR` 的差异**只能经由 `WL` 传出去** |

**回答 lead 的问题**: 组合**不另算**资金费腿的秩 —— `ZFD` 被**直接**当作 `evolve` 的参数传进去(`news2_combo.py` L59)。

⇒ 所以第 3 项(资金费秩基)的差异**直接落在资金费腿上**, 而不是只经由席位稀释。

另记一处**管线差异**: 研究员的 `causal_legs` 不产出 `QV`/`RN8`; `continuous_combo.py` L78 从**别处**取(`fund['rn8']`、`t['qvk']`)。NC 则由腿产出并传入。同一个量, 两边的来源不同。

## 3. 按预注册应报但本步无法给出的

第 3 步(在 NC 自己的输入上各跑一遍, 逐数组比 `LR`/`KZ`/`Z24`/`ZFD`/`WL`)**未做**, 所以本文**没有任何「差多少」的数字** —— 只有「差在哪」。
差多少必须由第 3 步给, 且按预注册要报: 不同锚数/总锚数、最大绝对差、**首个不同的锚**、中位绝对与中位相对差。

**预注册里写的风险 1 现在可以具体化**: `combo_legs.py` 的 `main()`(L47-69)绑死研究员的目录结构与收据链(`corrected_combo_v1d/BUILD_RECEIPT.json` 等), 无法直接跑在 NC 的输入上。可跑的是它的**纯函数** `causal_legs(pred, funding, rev24, seat_y, members, legal, look, min_members)`(L16-45) —— 它只吃数组。第 3 步的做法是: 从 NC 的输入构造这六个数组, 调 `causal_legs`, 与 NC 的 `legs.npz` 逐数组比。**不改写 `combo_legs.py` 一个字节**, 只调用它。

## 4. 下一步(需要 lead 点头的部分已标出)

1. 第 3 步: 只算腿, 不训练不跑引擎 —— 按 lead 已给的范围可直接做。
2. 若 `WL` 有差, 追加 pre-2026 席位分布差(第 4 步)。
3. 第 2 项差异(两个 R 是否同物)与第 8 项(流动性门是否在生产腿路径上有对应物)需要各一次实测。
4. **X89 的 22 列是否由 X82 的存储值派生**(lead 06:2xZ 给的可证伪方向)—— 优先级低于本项, 未做。
