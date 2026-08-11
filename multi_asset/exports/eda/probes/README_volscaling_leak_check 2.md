> **创建:** 2026-08-03 15:40 UTC | **Session:** C3-volcheck | **状态:** final — 存档说明 | **授权:** team-lead(2026-08-03, 明示授权把 6 份预测面板拷出 `/tmp`) | **作废条件:** `wide_dl_full.npz` / 部署权重 / `engine/` 任一改动 ⇒ 这些面板不再对应任何在用的东西, 应连同本文件一起删。

# vol-scaling 前视对照(TRAIN / SERVE / CAUSAL)—— 中间产物存档

**结论文件: `../RESULT_volscaling_leak_check_2026-08-03.md`。本目录只放它的可复算材料。**

## ★ 为什么这些文件不该被随手删

它们支撑的是一个**否决了部署的结论**(2026-08-03 20:00Z vol-scaling 部署由此否决)。
**重建这 6 份面板需要 ~106 分钟 CPU**(6 进程并行 × 4 线程, 实测 6,351–6,410 s/进程, 0.644 s/锚 × 9,851 锚)。
一个改变了决定的结果, 其可复算路径不该只挂在 `/tmp` 上 —— 这就是它们被拷到这里的全部理由。

## 文件

| 文件 | 是什么 | 大小 |
|---|---|---|
| `vs_pred_king_{TRAIN,SERVE,CAUSAL}.npz` | king 在三种 ch31 口径下的 OOS 预测面板 `pred (T,N)` + `ts` | 各 27 MB |
| `vs_pred_s2_{TRAIN,SERVE,CAUSAL}.npz` | s2 同上 | 各 27 MB |
| `vs_*.py` | 全部探针脚本(见下方复算顺序) | 小 |

**未存档: `vs_ch31_arms.npz`(81 MB, 三种口径的 ch31 通道本身)。** 刻意不存 —— 它由 `vs_leak_probeB.py` 在 **~2 分钟**内确定性重建, 且脚本**自带 `np.array_equal(TRAIN_arm, CH[:,:,31])` 断言**, 重建即自验。存一份反而多一个会过期的副本。

## 口径(读这些面板之前必须知道)

- **输入面板是 `exports/wide_dl_full.npz`(as-trained), 不是 `wide_dl_full_fundfix.npz`。** split-path: **腿吃 fundfix, 模型吃 as-trained**。搞反会得到一本不同的书。
- **三个臂共用同一套冻结归一化 `mu/sd`**(按各折训练日在 **TRAIN 口径**面板上重算;king fold4 与部署 `norm_stats.npz` **逐位相同**)。**臂间唯一的差是 ch31 这一个通道。**
- 折号严格 OOS: 每个 ts 只用它自己测试年的 checkpoint(fold0–4 = te 2022–2026)。
- `TRAIN` 臂与存盘通道**逐位相同** ⇒ `SERVE`/`CAUSAL` 是精确扰动, 不是近似。
- 三臂有限格数**完全一致**(king 990,224 / s2 987,239), 锚集均 9,821 ⇒ 宇宙与口径无关。

## 复算顺序

```
cwd  /mnt/storage/private/work_hsy/quant_research_multi_asset
env  /root/miniconda3/envs/hsy_v5push/bin/python3
★ 必须 torch.backends.mkldnn.enabled = False (脚本里已有); 不设会 RuntimeError: could not create a primitive

0. vs_leak_probeA.py   面板血统 / 折号识别 / mu-sd 重建校验
1. vs_leak_probeB.py   -> /tmp/vs_ch31_arms.npz   (含 TRAIN==存盘 逐位断言 + 重推理保真度)
2. vs_infer.py --model {king,s2} --arm {TRAIN,SERVE,CAUSAL}   -> 本目录的 6 份面板  ← 106 分钟的那一步
3. vs_book.py     ΔNet 三口径 (首先打一致性锚点, 不过则后面不必读)
4. vs_attrib.py   beta 通道 / 静态 vs 择时 / 书级 rank-IC
5. vs_mech.py     L1/L2/L3 + 红测 corr(倾斜, 泄漏)
6. vs_cost.py     成本敏感性 + 基线书月度解剖 + n=6 功效
```

**一致性锚点(步骤 3 会自己打印, 对不上就停):** `netSum(λ=0)=9.8773` · `ΔNet=+1.81420` · `t_raw=+10.3826` · `p⁺=0.9630` · `t_eff A/B/min=+3.3142/+3.0895/+3.0895`。

## ★ 两条关于本目录自身的事实

1. **`multi_asset/exports/` 被 `sync_to_server.sh` 整个 `--exclude` 掉了**(该脚本第 29 行)。
   ⇒ **好消息**: 本目录**不会**被 `rsync --delete` 抹掉。
   ⇒ **坏消息**: 本目录在**本地仓与 jpline 之间永不自动同步**。**`.npz` 只存在于 jpline**(且 `*.npz` 被 `.gitignore` 第 9 行忽略, 本来也进不了 git);`.py` 与本文件两边各一份, **它们不会互相追平**。改脚本时两边都要改, 否则就是本项目反复出事的那一族「一个事实两处存放, 而没有任何东西比较它们」。
2. **本目录的 `.npz` 不在 git 里, 也不在任何备份里。** 它们只在 jpline 的这一个位置。若 jpline 的磁盘出事, 唯一的恢复途径是上面那 106 分钟。
