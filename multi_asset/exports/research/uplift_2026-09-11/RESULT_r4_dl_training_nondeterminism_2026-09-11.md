# P4 结果 · DL 训练"非确定性"的量化 —— 前提被证伪, 真因是一个漏传的 env

> **创建:** 2026-09-11 | **Session:** b9646a9e (round 4 / P4) | **状态:** 结论已定, 收据齐(GATE P 逐位过)
> **作废条件:** pod GPU 型号/torch 版本更换后未重验; 或 `pod_f10_train_ext.py` 的 `V2` 开关被改
> **口径:** v4 pin。书层 = 钉死装置 `w10_sleeve.py` sha `b88e35a46b93d712`, 成本 = 拟合件
> `r3k/costb_PWR_G230k.json` sha `295b4e7b462373e4`; 统计 g = net_ex/gross_total, SR = mean/sd(ddof=1)·√2190;
> E-0911-A: 每条读数丢掉前 LOOK=900 个装置锚, 全周期 post-warm n=9018, SE(SR)=0.4928。
> **训练层用 `_ext` 谱系是刻意的、有标签的例外**: 被研究的对象**就是**在役那次训练, 复现它必须用它自己的输入;
> 训练层没有任何数字被当成 v4 记账数, 书层评估全在 v4 轴/v4 装置上。

## 0. 一句话

**round 3 的"同种子重跑相关 0.7526 < 换种子 0.8431 ⇒ 训练不确定"是误判。** 那次"同种子重跑"没有传
`V2=1`, 训练的是**另一个对象**。传上 `V2=1` 后, 同一颗种子在**十天之后、不同并发度、不同输出树**下
把归档的验证曲线**逐位重现**。这条链上的 DL 训练在本机是**确定的**; 书今天承担的"抽签风险"**不是训练抽签**,
而是"**一个默认为 0 的 env 开关可以静默换掉被训练的对象, 而产物 json 里看不见它**"。

## 1. 机制 —— 哪个算子不确定? 一个都没有

| 证据 | 数字 | 收据 |
|---|---|---|
| `torch.use_deterministic_algorithms(True, warn_only=True)` 跑完整一遍训练, **"没有确定性实现"的告警条数** | **0** | `r4_nondet/logs/probe_P1.log`(全程 731,890 条 UserWarning, 只有两类: `Converting a tensor with requires_grad=True to a scalar` 与 `Could not parse CUBLAS_WORKSPACE_CONFIG`) |
| `torch.backends.cuda.matmul.allow_tf32` 实测 | **False**(默认) | 同上 `DET_ENV` 行 |
| `torch.backends.cudnn.allow_tf32` 实测 | True —— 但网络是纯 `Linear/GELU/Dropout`(`pod_f10_train_ext.py` L155-157), **没有卷积**, cuDNN TF32 不进这条图 | 同上 |
| `cudnn.benchmark` | False(默认)⇒ 无 autotune 抽签 | 同上 |
| 环境 | torch **2.11.0+cu128** / cuDNN **91900** / **NVIDIA RTX PRO 4500 Blackwell** / driver 580.159.03 | 同上 + `nvidia-smi` |
| 8 个**同种子并发**训练(D1..D8, 8 路抢同一张卡) | 逐 epoch va **完全相同** | `logs/train_D{1..8}.log` |
| **9 次独立训练的预测数组 sha256**(round 3 的 REP42 @11:46Z 5 路并发 + 我的 D1..D8 @13:01Z 4/8/12 路并发, 不同输出树) | **全部 `e754c0ad39da3908…`, 逐位相同** | `r4_nondet/receipts/RESULT_P4_train.json` |
| 同种子、**跨十天**、跨并发度(V2=1) | 见 §2.1 / §3 | |

**dataloader 顺序**也不是嫌疑: `order = np.random.permutation(starts)`(L283)用的是 numpy 全局 RNG, 在
`np.random.seed(SEED)`(L41)之后**没有别的消费者**, 消费顺序固定 ⇒ 确定。
`scatter`/`index_put`(L236/243/294/332)都是**赋值**不是累加, 索引唯一, 不走 atomic 累加路径。

**⇒ 要让它"可复现"不需要做任何事 —— 它已经复现了。** 要让它**被保证**可复现(而不是碰巧), 需要
`torch.use_deterministic_algorithms(True)` + `CUBLAS_WORKSPACE_CONFIG=:4096:8` + 关 TF32;
代价见 §6(实测)。

## 2. 真因: `V2` 这个 env, 默认 0

```
/workspace/pod_f10_train_ext.py  L91:   V2 = int(os.environ.get("V2", "0"))
```

`V2=1` 打开**在役那条合成链**(L214-217): `r = wl[0]·r_model + wl[1]·Z24 + wl[2]·ZFD`, 即 msharpe 腿权 ×
[model, rev24, fund] —— "可微书损失"真正优化的那个东西。`V2=0` 训练的是**只有模型腿**的另一个对象。

- round 3 的 `r3_xib/train_seeds.sh` L11: `env ARM=V2MAIN SEED=$S COST=3.52 LDD=0.25 AFIX=0 EPOCHS=15 LR=3e-4`
  —— **没有 `V2=1`**。它的五次训练(s7/s101/s1234/s31337/"REP42")全是 V2=0 对象。
- pod 上**其它每一个** launcher 都传了: `pod_accept.sh` L8、`pod_ple_seq.sh` L14/37/40、`f11_chain.sh` L16、
  `gpu_queue.sh` L6。
- 部署重训脚本 `pod_f10_refit_ext.py`(sha `ea3675b8…`)把同一条链**硬接**(L25/L62-63, 无 env 开关)
  ⇒ **在役权重永远是 V2 对象**; 陷阱只在研究侧的走查训练。
- 产物 json 记录 arm/seed/cost/ldd/afix/epochs/lr/win/burn/stride/embargo + 三个输入 sha + self_sha256,
  **不记录 V2**(也不记录 `f10v2_legs.npz` 这个第四输入的 sha)⇒ **照着 json 复跑是复不出来的**。

### 2.1 逐位对账

| 跑法 | 2023 折 va[0..2] | 年均净(训练帧) |
|---|---|---|
| **归档在役 s42**(2026-09-01 07:30Z) | **−7.3493 / −5.6893 / −4.5234** | **+1.302** |
| round 3 "REP42"(V2 未传) | −6.073 / −3.570 / −5.500 | +0.165 |
| 我的 D1..D8(逐字抄 round 3 的调用) | −6.073 / −3.570 / −5.500 | 同上 |
| **我的 R1..R4(只加 `V2=1`)** | **−7.349 / −5.689 / −4.523** | 见 §3 |

⇒ 加上 `V2=1`, **十天前的归档验证曲线被重现**; 不加, 稳定地得到另一条曲线。
"同种子重跑不一致"从来不是抽签, 是**跑的不是同一个东西**。

### 2.2 round 3 自己的收据里本来就有这条线索

`r3_xib/receipts/SUPP.json`(dyn/FROZEN, `mean_abs_dg_A0`): 归档两件 {42, 2027} 与四颗新"种子"之间
**3.00–3.74**, 而四颗新"种子"彼此之间只有 **1.49–1.90**。归档件自成一簇 —— 这是"两个对象"的签名,
不是"环境漂移"的签名。round 3 把它读成了环境位移。

## 3. 书层后果 —— 该测的那个数

**N=4 次同种子重训**(R1..R4, `V2=1`, 2026-09-11, 与 D1..D8 抢同一张卡, 各自独立输出树)+ 归档在役那次
= **5 个抽样**。每个抽样过对齐 → 钉死装置 → **拟合成本 PWR230k**, 全周期 post-warm **n=9018**:

| 席位 | 窗 | mean | **sd** | min | max | 逐抽样 |
|---|---|---|---|---|---|---|
| dyn | FULL post-warm | **1.4150** | **0.0000** | 1.4150 | 1.4150 | R1/R2/R3/R4/归档 = 1.4150 ×5 |
| fix | FULL post-warm | **0.4841** | **0.0000** | 0.4841 | 0.4841 | ×5 |
| dyn | FROZEN | **2.9357** | **0.0000** | 2.9357 | 2.9357 | ×5 |
| fix | FROZEN | **2.8334** | **0.0000** | 2.8334 | 2.8334 | ×5 |

**sd = 0 不是"小", 是逐位相同**: R1..R4 的预测数组 sha256 全为 `42666fc75aa68b44…`, **与归档在役件
`f8_ext/preds/f10_V2MAIN_s42.npy` 逐位相等**(`bitwise==ARCH_s42: True`), 四折 best_va
`−4.0958/−4.6342/−3.1712/−7.6507` 与年均净 `+1.302` **逐字复现**归档 json。
V2=0 那一侧同样: 9 次(round 3 的 REP42 + 我的 D1..D8)全是 `e754c0ad39da3908…`, 书层 SR 1.1959 ×9, sd 0。

### 3.1 三把尺子并排(dyn 席位, FULL post-warm, 拟合成本)

| 量 | 值 | 相对 SE(SR)=0.4928 |
|---|---|---|
| **抽样间 sd(本题问的那个)** | **0.0000** | 0% |
| 种子间 sd(同一对象 V2=0, 4 颗种子) | **0.0203**(fix 0.0168; FROZEN dyn 0.0402) | 4.1% |
| 种子间 range(同一对象 V2=1, 2 颗: s42 1.4150 / s2027 1.4370) | 0.0220 | 4.5% |
| **漏 `V2=1` 这一件事**(1.4150 → 1.1959) | **−0.2191** | **44.5%** |
| 同上, FROZEN 窗(2.9357 → 2.5586) | **−0.3771** | 45.4%(该窗 SE 0.8314) |

**读法**: 书今天在 DL 腿上承担的"抽签风险"**是零**; 种子风险是 SE 的 4%; 而**一个漏传的 env 值
0.22 SR** —— 比种子噪声大 **10.8 倍**, 接近整条全周期 Sharpe 估计标准误的一半。
**该被写进风险表的不是"训练抽签", 是"配方的 env 没有被产物记下来"。**

### 3.2 预测层相关(round 3 那张表的正确版本)

| 对 | ρ(逐锚横截面 Spearman 均值) | n_pairs |
|---|---|---|
| 同种子 · 同对象(V2=1: R1..R4 + 归档) | **1.0000**(逐位) | 10 |
| 同种子 · 同对象(V2=0: D1..D8 + REP42) | **1.0000**(逐位) | 36 |
| **同种子 · 不同对象(V2=1 vs V2=0)** | **0.7526** | — |
| 不同种子 · 同对象(V2=1: 归档 s42 vs s2027) | **0.8431** | 1 |
| 不同种子 · 同对象(V2=0: 7/101/1234/31337 两两) | 0.6254(0.4728–0.7708) | 6 |

**round 3 的 0.7526 与 0.8431 都复现得到, 但第一行的标签是错的**: 它不是"同一颗种子重跑一次",
是"同一颗种子, 换了一个对象"。真正的同种子重跑是 **1.0000, 逐位**。

### 3.3 round 3 的哪些结论要动, 哪些不动

| round 3 的话 | 处置 |
|---|---|
| "同种子重跑相关 0.7526 < 换种子 0.8431 ⇒ 训练不是确定性的"(§8) | **撤回**。逐位反证。 |
| "环境位移: 归档 A0 水平 +1.8937/+1.8975 vs 本轮 +1.6942…+1.7401"(§8) | **重新归因**: 那是 V2=1→V2=0 的对象差。实测 REP42 的 A0 水平 **1.7320**, 落在四颗新"种子"簇 [1.6942, 1.7401] 内, 而归档两件 1.8937/1.8975 自成一簇(间隔 ≈10σ)。不是环境。 |
| "六颗种子" | **重述为**: 2 个抽样是在役对象(归档 42/2027), 4 个是 V2=0 对象。**"6 seeds" 是混合集**。 |
| XIB_LAG50 的配对 Δ 与判决 | **不翻**。配对是**在每个抽样内部**做的; 实测两簇给出的 Δ 重叠: FROZEN/dyn 在役对象 {+0.4698, +0.3932} 均值 +0.4315 vs V2=0 四个 {+0.4401,+0.4540,+0.4036,+0.4382} 均值 +0.4340 ⇒ 该对比**跨对象稳健**。**但"6/6 格"的预注册计数规则是在混合集上执行的**, 措辞需改。 |
| "种子不是瓶颈, t 天花板 2.12/0.66" | **方向维持, 更强**: 抽样维度方差为 0, 种子维度 sd 只有 SE 的 4% ⇒ 加种子/加抽样都买不到判决力。 |

## 4. 判决装置与门

- **GATE P(逐位)**: 我的装置实例 knobs-off 骑归档 s42/s2027 预测, 对 `V4_A0_{dyn,fix}_s{42,2027}` 的
  `d30_n2_c42_rec` **与** `d30_n2_c42_W` 以及 `S0_rec/S0_W/legs_*` 八个键**全部逐位相等, n_diff=0, maxabs 0.0**
  ⇒ `r4_nondet/receipts/GATE_P.json` `"PASS": true`。
- **书层证据链骑的是对的对象**: `review_scratch/health_check/dev_v4/f8_2026-08-22/preds/f10_A0_s42.npy`
  与"把归档 `f8_ext/preds/f10_V2MAIN_s42.npy` 用 `build_dev_v4.py` 的 `align()` 对到 v4 轴"**逐位相等**
  (实测 True)⇒ A0 基线 = 归档 V2=1 那次训练。**只有 round 3 的新抽样跑偏了, 在役证据链没有。**

## 5. 三条"明说的后果"

### 5a. 每一条"同种子"声明必须带**产物 sha + env 白名单**, 光带 sha 还不够

本案的教训比预期的更咬人: round 3 **已经**核对了三个输入 sha 和装置 sha, 全对, 仍然训了另一个对象 ——
因为**决定对象的那个开关不在任何被 hash 的东西里**。

审计结果(读过原文, 逐条):

| 位置 | 声明 | 判定 |
|---|---|---|
| `STATE.md` L69 | 在役 DL 件 `fea171/f10_live_s42_np.npz` **sha 351ae26b** | ✅ 合规(带 sha) |
| `docs/REVIEW_caliber_final_2026-09-04.md` L55 | 在役权重 sha 351ae26b pod==Mac==STATE.md L31 | ✅ 合规 |
| `docs/PREREG_l1_softmin_2026-09-02.md` L18 | jpline 同机复跑 preds sha256 与 canon **完全相同(7fa3cc9f…)** | ✅ 合规(正面范例) |
| `docs/PREREG_leg_ablation_2026-08-26.md` §J | V2DET vs V2PAR **逐位相同 / Spearman 1.000000** | ✅ 合规(正面范例, 且与本轮结论一致: 训练是确定的) |
| `docs/DESIGN_differentiable_book_loss_2026-08-22.md` L186 | "部署候选维持 V2MAIN×C3r φ0.45(**工件 s42**)" | ⚠️ 只带种子号 |
| 同上 L192 | "跨机平价受据: 双种子 8 折中 6 折 Δ≤0.022 … 均 ≪ **种子噪声 ~0.10-0.17**" | ⚠️ 把跨机差异归给"种子噪声"(该案差异很小, 结论不受影响, 但归因用错了名词) |
| `docs/PREREG_deploy_dl_recipe_2026-10.md` §2 | 10-01 重训配方"其余逐字不变 … **种子 42**" | ⚠️ 需补 env 白名单(见 §7) |
| `RESULT_r3_instrument3_xib_seeds_2026-09-11.md` §8 | "同种子重跑的差异比换种子还大 ⇒ 训练不是确定性的" | ❌ **本文证伪** |

**在役链没有被这个缺陷咬到**(§4 第二条): 部署重训脚本硬接 V2 链, 在役件按 sha 记账。

### 5b. 席位规则对 DL 抽签既不放大也不衰减 —— 它**根本看不见** DL 腿

`w10_sleeve.py` 的席位 `w3_at()`(L174-200)用的是 `LRa["king"/"rev24"/"fund"]`, 而 `legs()`(L160-170)
构造 king 腿收益用的是 **king 分数 `sc["king"]`**; φ 混合发生在**仓位层**、席位之后(L303
`smb = (1-PHI)*sm + PHI*_smf`)。开关 `SEATF10`(L42)可以让 F10 链用四腿自己的席位, **在役是 0**。

实测(七个不同 DL 抽样, dyn 席位): `legs_king` 与 `w3_king` **逐位相同, 最大绝对差 0.0**。
⇒ 结构性事实, 不是统计推断。**两个席位读数之差是纯敞口缩放**: dyn 的 king 腿权全周期均值
**0.46356** vs fix 的 **0.21**(=2.21×), 而 SR 的种子间 sd 之比只有 **1.21×**(FULL)/1.42×(FROZEN)
⇒ 单位 king 敞口上, 动态席位反而**更不散**(0.0438 vs 0.0800)。

### 5c. 在役那次抽签"运气"如何 —— 抽签维度上**没有彩票**

- **抽签(run)维度**: 方差为 0(§3), 不存在"这一抽是好是坏"的问题。
- **种子维度**(唯一真实存在的抽签, 但很小): V2=1 对象两颗种子 dyn 全周期 post-warm SR **s42 1.4150 /
  s2027 1.4370** —— 在役这颗是两颗里**低的那颗**(−0.022)。V2=0 对象四颗种子的 sd **0.0203**
  ⇒ 种子抽签在书层约 ±0.02 SR, **= SE(SR)=0.4928 的 4%**。
- **选择性说明(自证的部分要说清)**: 种子 42 不是从一堆种子里挑出来的 —— 它是脚本默认值, 且
  `DESIGN_differentiable_book_loss` 的部署判据是"双种子各自过门"而非"取更好的那颗"
  ⇒ 这里没有典型的选择偏差; 但"在役是低的那颗"这句本身是**事后**读数, 不构成任何加分。

## 6. 让"确定"变成"被保证"的代价 —— 实测 **+37.9% 训练时间, 换到 0 个比特的改变**

三次**独占卡**(无并发)的短跑(EPOCHS=1, 机制探针, 非书层配方), 逐字同配方只改确定性开关:

| 跑 | 模式 | epoch 秒数(四折) | 合计 | 预测 sha256 |
|---|---|---|---|---|
| S1 | 现状(什么都不改) | 7 / 11 / 17 / 23 | **58 s** | `0da06fa5d6f24977…` |
| S3 | `use_deterministic_algorithms(True)` + `cudnn.deterministic` + TF32 全关 + `CUBLAS_WORKSPACE_CONFIG=:4096:8` | 9 / 15 / 24 / 32 | **80 s** | `0da06fa5d6f24977…` |
| S4 | 同 S3(第二次) | 9 / 15 / 23 / 32 | **79 s** | `0da06fa5d6f24977…` |

- **S3 ≡ S4 逐位**(保证成立), **且 S1 ≡ S3 逐位** ⇒ 打开全套确定性开关**一个比特都没改变**。
- 代价 **80/58 = 1.379**, 即 **+37.9% 训练时间**(墙钟 94 s → 128/129 s, +36%)。
  换算到在役配方(15 epoch × 4 折, 独占卡约 8-10 分钟): **每次重训多花约 3-4 分钟**。
- 受据: `r4_nondet/receipts/RESULT_P4_determinism_cost.json`, 日志 `logs/probe_S{1,3,4}.log`。

## 7. 建议(带代价)

**不建议**为"防非确定性"改生产重训路径 —— 那个病不存在。建议改的是**产物的自述**, 三件, 训练时间代价 0:

1. **把 env 白名单与第四个输入的 sha 写进产物 json**(提案 diff: `r4_nondet/PROPOSED_DIFF_env_stamp.md`)。
   同时给 `V2` 去掉默认值改成**必须显式传**(断言), 让漏传变成红而不是静默换对象。
2. **10-01 重训(`PREREG_deploy_dl_recipe_2026-10`)的配方描述补一行 env 白名单**:
   该案新引入 `INIT_STATE`(热启动权重)——**又一个"有默认值就会静默改变对象"的开关**。
   建议在 §2 的"逐字不变"清单里显式写出全部 env 键值, 并在 §4 门 3 的"记 sha"里加上
   **训练调用的 env 转录**(逐字, 不是描述)。
3. **每次重训的产物里记 torch/cuDNN/GPU 型号**。本轮确定性成立于
   `torch 2.11.0+cu128 / cuDNN 91900 / RTX PRO 4500 Blackwell`; pod 是租用容器, **GPU 型号可能在重启后变**,
   而这条链上没有任何地方记录它。这是我能指出但**无法测**的唯一真实残余风险(只有一张卡)。

### 7.1 生产重训路径要不要改成"确定性"? —— **不要, 按现在这个代价不值**

| 选项 | 买到什么 | 代价 | 判 |
|---|---|---|---|
| A. 现状 | 实测确定(9+5 次逐位), 但**没有保证** | 0 | **维持** |
| B. 打开全套确定性开关 | **保证**(S3≡S4), 今天一个比特不变 | **+37.9% 训练时间** ≈ 每次重训 +3-4 分钟 | 不值 —— 它防的是一个实测不存在的病 |
| C. 把 env/输入/torch/GPU 写进产物 json + `V2` 去默认值 | 防住**实测已经发生过一次**的病(round 3), 且让"同种子"声明可被机械核对 | **0 训练时间**, 约 10 行代码 | **建议做** |

**若将来有人要 B**, 唯一站得住的理由是"月度重训件要能被第三方在别的机器上逐位复核";
那时 B 的正确形态是 **B+C**(光有 B 没有 C 依然复现不出来 —— round 3 就是反例: 它的装置是确定的, 照样复不出)。

## 8. 我留下的洞(明写)

1. **只有一张卡**。本轮的确定性成立于 `torch 2.11.0+cu128 / cuDNN 91900 / RTX PRO 4500 Blackwell`。
   **换 GPU 型号 / 换 torch 会不会改变结果, 我无法测** —— pod 是租用容器, 型号可能在重启后变, 而
   链上没有任何地方记录过它。这是唯一真实的残余风险, 我只能指出, 不能量化。
   (旁证: 2026-08-25 `queue_determinism.sh` 的 V2DET 逐位相等 + 本轮逐位相等, 跨 17 天同容器成立。)
2. **归档那次训练的 env 没有直接收据** —— 没有 launcher 落在盘上。我的结论是**行为等价推断的**:
   加 `V2=1` 后预测数组与归档**逐位相等**(sha `42666fc7…`)。这在实践上等价于证据, 但严格说是
   "找到了一组能逐位重现的 env", 不是"读到了当时那条命令"。
3. **V2=1 只验了种子 42**。s2027 我没重训(没必要, 但也就没验)。
4. **EPOCHS=1 的确定性探针不是书层配方**。§6 的时间比是在 1 个 epoch 上测的, 假设 epoch 间同构。
5. **round 3 的 XIB 判决我没有重跑**。§3.3 用的是 round 3 自己的收据做的跨对象一致性检查,
   不是新装置上的重判。**XIB_LAG50 的 6 格预注册计数在混合对象集上执行**这一条, 需要 round 3 的
   owner 决定是重述还是重跑。
6. **`r2_learned/r2_stage2.py`** 自称"chain copied verbatim from the in-service F10", 但它是**重写**,
   用的是自己的 fund 腿合成(L93/L189), 不是 L214-217 的三腿 msharpe 合成。**本轮没审它**
   (RESID_SHARPE 已在 round 3 判死, 优先级低), 记为活口。

## 9. 落盘

- pod: `/workspace/uplift_2026-09-11/r4_nondet/`
  - 装置: `train_nd.sh`(V2=0 复刻)· `train_v2.sh`(V2=1 真复制)· `det_wrap.py` · `train_probe.sh` ·
    `probe_drive2.sh` · `setup_tree.py` · `runner.py` · `gateP.py` · `align_p4.py` · `verify_train.py` ·
    `analyze_p4.py` · `chain.sh`
  - 收据: `receipts/GATE_P.json`(PASS, 逐位)· `receipts/RESULT_P4_train.json` ·
    `receipts/ALIGN_P4.json` · `receipts/RESULT_P4_book.json` · `receipts/RESULT_P4_determinism_cost.json`
  - 日志: `logs/chain.log`(全链逐字)· `logs/train_{D1..D8,R1..R4}.log` · `logs/probe_{P1,S1,S3,S4}.log` ·
    `logs/probe_drive.log`
  - 新 DL 产物: `f8_{D1..D8,R1..R4}/preds/f10_V2MAIN_s42.npy` → 对齐 `f8x/preds/f10_A0_s{D*,R*}.npy`
  - 臂: `arms/w10_ablation_series_R4_A0_{STD,PWR230k}_{dyn,fix}_s*.npz`
- 本地: 本文件 + `r4_nondet/`(装置副本)+ `r4_nondet/PROPOSED_DIFF_env_stamp.md`。**未 commit**。
  实盘两仓(`~/dl_quant_live`, `~/wide_shadow`)全程**只读**; `/workspace` 只写 `uplift_2026-09-11/r4_nondet/`。

## 10. 逐字复跑命令(转录)

```bash
# 真复制(V2=1), 四抽样
cd /workspace/uplift_2026-09-11/r4_nondet && for L in R1 R2 R3 R4; do ./train_v2.sh $L & done; wait
# round 3 的复刻(V2 漏传), 八抽样
cd /workspace/uplift_2026-09-11/r4_nondet && for L in D1 D2 D3 D4 D5 D6 D7 D8; do ./train_nd.sh $L & done; wait
# GATE P(逐位)
/workspace/venv/bin/python runner.py 42,2027 STD && /workspace/venv/bin/python gateP.py
# 训练层对账 / 对齐 / 书层 / 分布
/workspace/venv/bin/python verify_train.py D1,D2,D3,D4,D5,D6,D7,D8,R1,R2,R3,R4
/workspace/venv/bin/python align_p4.py   D1,D2,D3,D4,D5,D6,D7,D8,R1,R2,R3,R4
/workspace/venv/bin/python runner.py     D1,D2,D3,D4,D5,D6,D7,D8,R1,R2,R3,R4 PWR230k
/workspace/venv/bin/python analyze_p4.py '{"SAME_SEED42_V2ONE":["R1","R2","R3","R4","42"],"SAME_SEED42_V2ZERO":["D1","D2","D3","D4","D5","D6","D7","D8","REP42"],"SEEDS_V2ZERO":["7","101","1234","31337"],"ARCHIVED_V2ONE":["42","2027"]}' SEEDS_V2ZERO
# 确定性代价(独占卡)
./train_probe.sh S1 off 1 ; ./train_probe.sh S3 full 1 ; ./train_probe.sh S4 full 1
# 非确定算子枚举
./train_probe.sh P1 warn 1   # -> logs/probe_P1.log: 0 条 "does not have a deterministic implementation"
```
