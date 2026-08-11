> **创建:** 2026-08-04 07:5x UTC | **Session:** team-lead (6737834a) | **状态:** in-progress — 任务台账 #4, 阻塞于 #5(s2 PRODFOLD) | **作废条件:** 第一批上线且影子对照开始后归档

# RUNBOOK — 部署第一批(模型换代), 逐落点带 file:line 回执

**预勘结论(07:5xZ, 只读, 两轮 grep):** 六件里 **③④⑤ 的定位与任务描述不同**, 已按实测改写。
**分锚原则**: ①②③+门翻转 = **一个逻辑变更**("换模型代际"), 拆开会造成混代际书 ⇒ 同一锚原子上线。④⑤ 在**服务器影子侧, 不在下单路径** ⇒ 可异步, 不占锚。

## A. 本机原子批(下单路径, 一锚)

| # | 落点(实测) | 动作 | 守卫 |
|---|---|---|---|
| ① 权重 | `checkpoints/king_fold4.pt` `s2_fold4.pt`(`inference.py:33` CKPT_DIR) | 换成 PRODFOLD 双权重, **精确路径钉死(08-04 08:5x)**: king = `wideA_lamorth0_xattn_5yr_PRODFOLD_corrfund_v1/fold_0_model.pt`; **s2 = `wideA_s2_y24_PRODFOLD_corrfund_v1_val30/fold_0_model.pt`** | `inference.py:79` **strict=True** —— 锚前 CPU 干载测试。**★ 命名陷阱: 天然名 `…PRODFOLD_corrfund_v1`(无后缀)落在【val=90 变体】手里**(服务器只增不改, 改不了名) —— 按天然名取件会拿到非候选。两侧 PROVENANCE 应带机器可读 `deployment_candidate: true/false` 字段, 装配时**按字段核不按名字取** |
| ② norm | `inference.py:68-77`: mu/sd 与权重**同发** | **✅ 源产物已备(08-04 08:4xZ, B4 `064dc7a`)**: 三条生产折各一份 `NORM_PRODFOLD.npz`, **按实盘 `norm_stats.npz` 自己的键布局**(`king_mu/king_sd/s2_mu/s2_sd` (32,) float32) + resid_sigma + 训练窗边界 + 面板路径。装配 = 替换 `checkpoints/norm_stats.npz`(frozen_inputs 钉住件, 换它属部署动作归 #4) | shape/正性断言内建; ★静默半边已定价 ≈0.05% 横截面分歧(可忽略), **响亮半边(fold_4 文件名)仍是真阻塞, 禁改名桥接** |
| ③ funding 翻转 | `panel_build.py:16-17` 明写 "DL 面板 funding 是 AS-TRAINED…**复现面板 = 复现 bug**"; funding_ema 是**注入参数**(`:112`) ⇒ 翻转点在**调用方**(compute_preds 构造注入序列处) | 注入序列改为 corrected 口径 | 见下一行 —— **必须同批** |
| ③b **★ 休眠翻转的具名住址** | `signal/assert_funding_dim.py:5-6`: **"normfix 必须 GREEN / as_trained 必须 RED"** —— 换代后 DL 面板侧变 corrected, **这个双侧期望必须同批翻转, 否则电池会红对新模型** | 翻转期望并注明"随模型代际翻转" | journal §16-bis 那条"没有机制会提醒"——**它的机制就是这行, 现在有地址了** |
| 验收 | `run_acceptance.sh` 全电池 | 改后全绿贴读数 | 110/110 基线已知 |

## B. 服务器影子侧(非下单路径, 异步)

| # | 落点 | 动作 |
|---|---|---|
| ④ 守卫基线 | `engine/live/monitor.py:75-78` BASELINE_BY_YEAR/DECAY_FRAC | 按 SPEC `0f8be1fe` 重测: **SERVE 面板**(不用 causal—守卫回答"上线拿多少"不是"训得多好"); DECAY_FRAC 禁止同调; **绑 generation 哈希**(norm_stats 家族唯一裸着的成员); 用 argparse 透传(commit `5f3fb6b`) |
| ⑤ ~~embargo 10→8~~ **已撤销(08:0xZ)** | B4 逐产物实测: 在役 s2 配方=**10**, king=**8** —— **实盘写死的两个值都对**。"矛盾"是两个 run 的读数被说成一个(报告没带 run 名) | 无动作。新 s2 PRODFOLD 已按 10 训 ⇒ 与实盘一致 |
| ⑥ **★ 生产折服务路径(新, 08:0xZ)** | **本机**: `inference.py` 吃发运的 mu/sd ⇒ PRODFOLD run 目录里**没有** mu/sd ⇒ 须用 harness 同一代码路径从生产折训练窗**重导出并认证**; **影子**: `signal_loop.py:125-126` 找 `fold_4_model.pt` 且用 year_folds 第 4 折 tr 做归一化, 而生产折存 `fold_0` 且训在全量窗 | **★ 禁止用改名桥接**: 文件名那半会响亮失败, 而改名会把归一化人群错配**静默**装上(浅层错误掩护深层错误)。影子侧须加 prodfold 分支: **从发运件读归一化, 不重算** |

## C. 序(依赖实测)

```
#5 s2 PRODFOLD 落地 → A① 干载测试 → 定位 ② mu/sd 物理文件 → 分支上备齐 A 全件
→ 选锚(非交易高峰) → 原子落盘 → 电池全绿贴读数 → 影子对照开始(B④⑤ 并行做)
```

## D. 开放项(装配前必须闭合)

1. ② mu/sd 的物理位置未定位(checkpoints/ 只有 .pt)。
2. PRODFOLD-s2 架构是否满足 `inference.py` 的 strict=True 硬编码(xattn on / 6 heads)——干载测试回答。
3. ③ 调用方注入点的确切行号(compute_preds 内)——装配时定位并记录。
4. 掩码间隙(任务 #7)若定价出"很大", 换代批要重新评估——目前唯一未定价项。
