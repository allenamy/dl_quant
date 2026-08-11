# ★ 正典基线 — 冠军配置复现依据 (用户令 2026-08-08 定盘)

> **创建:** 2026-08-08 01:0x UTC | **Session:** multi-asset-v2 主线 | **状态:** final
> **作废条件:** 仅当新基线以同等严格度(双种子+三环境对账)确立并显式引用本文废止
> 用户令: 「记录下来，作为之后复现基线的重要依据。架构升级，多源数据融合，特征升级
> 在该基线全面展开，风格残差分解等也是」

## 1. 基线数字(双种子, 三环境对账)

| 量 | 值 | 收据 |
|---|---|---|
| **resid rank-IC (y24)** | **0.0475** {s42: 0.0453, s2027: 0.0497} | `wide_harness_rb32_lam0_s{42,2027}.json` |
| **raw rank-IC (y24)** | **0.067** {0.0647, 0.0687} | 同上 |
| IR | 7.26 / 7.63 | 与 h24_C 的 7.26 相同 |
| persistence | 0.42 / 0.51 | |
| 逐年(s2027) | [0.048, 0.046, 0.050, 0.052, 0.053] | 五年全 ≥0.046, 散布 0.0026 |
| 对账① h24_C_s2 | 0.0466 | 差 +0.0009, 同 IR |
| 对账② 实盘账本 raw | 0.0794 (40锚, CI[0.042,0.117]) | 离线 raw 0.067 = 0.6 SE |
| 对账③ S1 记录(4h) | 0.0449 | lam0@y4 臂在跑, 出后补录 |

## 2. 精确复现命令

```bash
cd /workspace/code && export PYTHONPATH=/workspace/code
python3 -u multi_asset/train/train_wide_harness.py \
  --wide_dl_path <PANEL>            # ★ 必须显式; 见 §3
  --target_horizon 24 --aux_horizons 1,24 \
  --encoder conformer --n_factor_heads 6 \
  --xattn --n_xattn 1               # ★ 陷阱①: --xattn 是 store_true, 默认关; 漏它 −0.031
  --lam_orth 0                      # ★ 陷阱③: 默认 1.0 是被记录为劣的惩罚配置; 漏它 −0.012
  --d_model 64 --n_blocks 2 \
  --year_folds --year_folds_from 2022 --embargo_days 10 \  # 年折装置(--year_folds 也是 store_true)
  --seed 42                          # 双种子: 42 + 2027
```

## 3. 面板身份(★ 陷阱②: 默认路径歧义, exports 下有 10 份 wide_dl*, 含脏版)

- **正典**: `wide_dl_full_corrfund_causal_0731.npz`
  sha256 `3e8d562790a2ebdd49400e13abf808bf77d9066a9f3df1a3604709b1257b1965`(载于实盘 MANIFEST)
- RunPod 等价件: `/workspace/data/wide_dl_prodmask32.npz`(自建重建 × 生产零掩码;
  非零格与正典 corr 0.99999896, MEMBER 内差异 0.13%)
- **判脏工具**(任何面板一秒验): 反解 betaadj_ret24 对 `convolve(market,ones(24),"same")` 的
  相关 >0.9 ⇒ 脏(含 11h 未来)。`wide_dl_full.npz` 实测 0.9998 = 脏, 禁用。

## 4. 噪声标定(判任何 Δ 是否可信的尺)

| 来源 | 幅度 |
|---|---|
| 种子间(同配置) | ±0.002 |
| 同种子重跑(cuDNN 非确定) | ±0.0024 |
| **单变量 A/B 最低要求** | **双种子同向 且 \|Δ\| ≥ 0.005** |

环境注: RunPod(torch 2.8.0+cu128/5090) 与 jpline(2.7.1+cu126/3090) 在冠军配置下对齐
(h24_C@jpline 0.0466 ≈ lam0@RunPod 0.0475); lam=1.0 下曾见 −0.007 环境向差异, 冠军配置下不复现。

## 5. 展开规则(用户令的执行形态)

**一切升级 = 冠军配置 + 恰一个变量。** 适用于:
- **架构升级**(族塔/门控/注意力变体): encoder 换臂, 其余旗标不动
- **多源数据融合**(metrics v2 / book / basis): 面板换件(--wide_dl_path), 装置不动;
  已确证: 扁平拼接有害(2 族复现), 族塔可挽回 —— 新族一律族塔接入
- **特征升级**: 同上, 且须先过族门(G1/G1b/Ridge/PR, 判据在各 DESIGN 文档)
- **风格残差分解**: 现行 YR = 对 8 列 baseline 的逐时刻横截面 OLS 残差(风格层即 baseline);
  分解实验 = 换 --target_horizon / --per_head_targets / target_npz, 装置不动
- **视界**: y4/y8/y12/y24 目标列齐备(y8y12_sidecar); lam=1.0 下四视界 IC 等价、
  持续性 4h=2.8×24h —— **此结论待冠军配置复核后才可用于决策**

## 6. 基建欠账(最高优先, 未清偿前每次训练手工核对 §2)

1. harness 产物记录**完整 argv + 面板 SHA256**(现状: 两者皆无, 是本次三陷阱的共同根因)
2. 冠军配置固化为 `champion_run.sh` 入库(本文档 §2 的可执行形态)
