> **创建:** 2026-09-11 | **Session:** https://claude.ai/code/session_01H39k5rgyd43mFMNsaBqzeX | **状态:** **裁定用文档 —— 本文不做任何改动, 不请求上线**;证据见 `RESULT_r3_resid_deployable_2026-09-11.md` | **作废条件:** RESULT 的 GATE P / C1 / D-DEPLOY 任一被推翻; 或 `~/wide_shadow` 生产者形态变更
> **只读声明:** `~/dl_quant_live`、`~/wide_shadow` 本轮**零写入、零重启、零下单**。以下所有生产者事实来自**读**这两棵树的文件与日志, 路径与行号在文中给出。

# 部署形态 · RESID_SHARPE 作为**第四腿** —— 一份裁定材料

## §0 先说结论(三句)
1. **工程上这是本项目迄今最便宜的一次模型上线**: 生产者**每锚已经在算这 82 列特征**(逐位同一套, `names` sha 相同),
   **已经在跑同一形状的 numpy MLP**(在役 F10 腿), 增量推理实测 **≤8 ms**, 对 **N+22:40 硬截止**的 78 s 最坏余量占 **~2%**。
2. **研究上它还没到可裁定的成色**: 预注册主端点 D3 **在 s42 上差 0.014 未过**(NEAR_MISS), 且**首次对抗**
   (臂 − 标签打乱孪生)在全周期上 **95% 区间含 0**。
3. **而且"第四腿"这个形态本身没有被测过**: 测的是"50/50 等 gross 叠两本书", 不是"在一本书里混第四条腿"。
   **这是本文最大的空洞, 写在 §3。**

## §1 在役链路(实测事实, 带出处)
```
~/wide_shadow/shadow_loop_v3.py   (launchd, SHADOW_OFFSET_MIN=16)
      ↓ 写 state/target_live/<anchor>.json (+ .sha256)   ← king 形态, 三腿 king/rev24/fund
~/wide_shadow/fea171/combo_stage.py  (COMBO_LIVE=1, combo_live_daemon.sh)
      ① king 书自平价复算        [实测 0.8–1.5 s]
      ② 171 管线重跑 → mini/data/dlw_fea82.npz + f8_fea89.npz      ← **本步已产出第四腿要的全部特征**
         然后 numpy 前向 f10_live_s42_np.npz (combo_stage.py:160–166) → F-10 腿分
      ③ 0.55·king_book + 0.45·f10_book → exec_reshape → 五层安全 → **重写 target_live/<anchor>.json**
      ④ 任何一层不过 ⇒ 拷回 king 备份 + HIGH 页报 ⇒ 本锚交易 king 形态(fail-open)
~/dl_quant_live  scheduler/anchor_loop.py + live/external_book.py
      N+24:00 读 target_live(config/book.json:158 anchor_offset_min=24, poll_grace_min=5 → 重试到 N+29,
      max_age_min=10, anchor_ts 必须等于本锚)
```
**时序(最近 7 锚实测, `fea171/combo_live.log` + `state/combo_live_status.json`)**

| 锚 | 写者起跑 | 运行 | 落盘 | 距硬截止 N+22:40 |
|---|---|---|---|---|
| 09-11 08Z | ≈N+20:31 | 42.1 s | N+21:13 | **87 s** |
| 09-11 04Z | ≈N+20:30 | 51.8 s | N+21:22 | **78 s**(本周最坏) |
| 09-11 00Z | ≈N+20:29 | 31.6 s | N+21:01 | 99 s |
| 09-10 20Z / 16Z / 12Z / 08Z | ≈N+20:29 | 31.7 / 32.5 / 48.7 / 33.3 s | N+21:01..21:09 | 91–107 s |

**硬截止的实现**(`combo_stage.py` §COMBO_LIVE): `_deadline = A + 22*60 + 40`; 超过就 `_bail` ⇒ **不写**, 交易 king 形态。
⇒ **延迟风险的失败模式已经是安全的**: 变慢不会导致迟写, 只会导致当锚回落 king。

## §2 第四腿要什么(逐项, 附实测数字)
| 项 | 需要什么 | 现状 | 实测 |
|---|---|---|---|
| **推断路径** | 冻结权重 + 冻结归一化, CPU, numpy | **已存在同形状路径**: `combo_stage.py:160–166` 就是 `Linear-GELU-Linear-GELU-Linear` 的 numpy 前向, 归一化序 **标准化→clip(±5)→NaN置0**(E-0826) | 我导出的 `ckpt_np/*_np.npz` 键集与 `f10_live_s42_np.npz` **完全相同**(`w0,b0,w1,b1,w2,b2,mu,sd_,alpha,n_cols,trained_through`), 只是 `n_cols=82` 而非 171 |
| **数值一致** | numpy 前向必须等于训练期 torch 前向 | 已验 | maxabs **≤1.5e-7**(float32 舍入), 逐锚名次相关 **1.0**(40 个 ckpt 中 39 个为 1.0, 1 个 0.9999993 = 一对相邻名次互换) |
| **特征构建** | `dlw_fea82` 的 82 列, 同名同序 | **生产者每锚已经在建**(`combo_stage.py` ② → `mini/data/dlw_fea82.npz`) | 生产者与研究面板的 `names` **sha256 前缀同为 `a011b54953cbffa6`**, 82 列, dtype 均 float16 ⇒ **特征构建增量成本 = 0** |
| **推理延迟** | 必须塞进 N+22:40 | — | 生产者 Mac 实测 numpy 前向: 400 名 **中位 5.65 ms / 最大 7.89 ms**; 450 名 中位 6.27 / 最大 7.68 ms |
| **成书延迟** | 第四腿要自己走一遍 `chain()`(秩→demean→L1→softcap→EMA) | 在役 F10 腿已在做同样的事 | 以 ① 的 king 自平价 `chain()` 为尺 **0.8–1.5 s** |
| **状态文件** | 第四腿要自持 EMA 仓位态(同 `state_H_f10_<anchor>.npz` 形态, 按锚命名以保证重跑幂等, E-0825-D) | 形态现成 | 写入 ~ms |
| **合计增量** | — | — | **≈1.5 s**, 占最坏余量 78 s 的 **≈2%** |

**⇒ 延迟不是这件事的约束。** 约束全在研究成色与书行为。

## §3 ★ 最大的空洞: 被测的形态 ≠ 可部署的形态
- **被测的**: `LEGS=001 PHI=0 FTRIM=off` 的**独立 sleeve 书**, 再与 A0 **等 gross 50/50** 叠加, **每本自付换手费**。
- **可部署的**: 在**同一本书**里把第四条腿的秩混进去, 仓位**先净额再收费**。
- 成本侧的差已量化且很小(`NETTING_BOUND.json`): 净额只省 **9.6–11.1%** 换手 = **0.009–0.011 bps/锚/gross**
  (两本仓位近正交, `corr(W_sleeve, W_A0)` 仅 **0.069 / 0.095**)。
- **但仓位侧完全没测**: 50/50 等 gross 意味着**把一半的书权重交给这条 sleeve**。这对一个 **NEAR_MISS** 对象是极大的配额,
  而 combo 现行是 `0.55·king + 0.45·f10`。第四腿的权重 `a·king + b·f10 + c·resid` 是**三个自由度**,
  **本轮一个都没有预注册、没有测、没有席位规则**(A0 的三腿用 `WRULE=msharpe LOOK=900`, 第四腿的席位规则不存在)。
- **⇒ 任何裁定必须先要求一次"在书内混腿"的预注册与测量, 而不是把 50/50 叠书的数字当部署数字。**

## §4 失败模式与回滚(按现行五层设计)
| 情形 | 现行行为(已实现) | 第四腿需要加什么 |
|---|---|---|
| **模型文件不存在 / 读不出** | `np.load` 抛异常 ⇒ COMBO_LIVE 块内的 `try` ⇒ `_bail` ⇒ **拷回 king 备份 + HIGH 页报 ⇒ 本锚交易 king 形态** | 保持**硬失败**。**禁止**"模型没加载就把第四腿权重设 0 继续写"—— 那是静默改书(`zero_delta_means_switch_not_wired` / `patch_on_disk_is_not_patch_running` 同族) |
| **模型文件被换了** | **无防护**: `combo_stage.py:160` 直接 `np.load(f10_live_s42_np.npz)`, **没有 sha256 校验** | **建议**: 第四腿的 `_np.npz` 进一个 sha256 清单, 飞前断言(生产者已有先例: `shadow_loop_v3.py:140–143` 对 `shadow_bundle/MANIFEST.json` 逐文件 sha256; 执行器有 `checkpoints/MANIFEST.json`) |
| **分数覆盖不足** | 飞前断言"F10 打分覆盖≥380 / gross∈[0.4,1.2] / 名数≥150 / 宇宙名单与 king 文件逐字相同" | 第四腿加同款覆盖门(建议同阈 ≥380) |
| **跑超时** | `_deadline = A + 22*60 + 40` ⇒ `_bail` ⇒ king 形态 | 无需改;但增量 1.5 s 也应进飞前的 elapsed 断言 |
| **写出的文件执行器不认** | 第 4 层: 用**执行器自己的** `external_book.verify_file + parse_target` 验收, 不过则回滚 | 不变 |
| **回滚** | 拷回 `state/target_live_king/<anchor>.json` + `.sha256` | 代码级回滚 = 把 `combo_stage.py` 换回不含第四腿的版本; **生产者 king 文件路径全程未被改动**, 所以最坏情况就是回到当前 combo 或 king 形态 |

**另一条必须说的**: 本轮所有 checkpoint 都是**走前折模型**(每年一个)。在役 F10 腿用的是**全史重训件**
(`f10_live_s42_np.npz`; `w10_sleeve.py:117` 明写"全史重训件 **不参与任何历史评估**")。
⇒ **上线用的那一件我没有训**。要上线必须再训一件全史件, 而那一件**按定义不可用本轮任何数字背书**。

## §5 如果要裁定, 需要先补的清单(按优先级)
1. **在书内混腿的预注册 + 测量**(§3): 权重网格、席位规则、逐位平价收据。没有这个, 部署数字不存在。
2. **把 D3 补过**: 目前 s42 的 BONF2 下界 **−0.014**。可选路径 = 第三个种子(**必须预注册 K 的变化**), 或接受 NEAR_MISS。
3. **把 §5 的对抗补过**: 全周期"臂 − 打乱孪生"ΔSharpe CI95 **[−0.148, +2.754]** 含 0。
   最省力的补法是把 2022 折做扎实(现在只有 816 个训练锚 / 12 个窗口, 且训练期 `W_A0` 是热身书)。
4. **全史重训件 + 它自己的 sha 清单**(§4 末)。
5. **偏移谱那条门的裁定**(RESULT §7.1 的建议 diff): 现在三轮都记了 FAIL-as-written, 而在役书自己的两条腿也过不了。
   **这条要用户拍板, 不是研究员自己豁免。**

## §6 我没有做的事(明写)
- 没有改 `~/wide_shadow`、`~/dl_quant_live` 的任何字节; 没有重启任何进程; 没有 load 任何 launchd job; 没有下任何单。
- 没有改 `judge_v4.py`、`ELIGIBILITY_CONTRACT.json`、`v4_leakcheck.py` —— 只在 RESULT §7.1 给出**建议 diff**。
- 没有改 `dev_v4` 与任何冻结 v4 工件; 本轮全部产物在 `/workspace/uplift_2026-09-11/r3_resid/` 与本仓
  `multi_asset/exports/research/uplift_2026-09-11/`(分支 `research/book-uplift-2026-09-11`, **未提交**)。
- 没有请求上线。**本文是裁定材料, 不是上线申请。**
