# 磁盘清理 manifest（复原保证存证）

> **创建:** 2026-07-12 22:50 JST | **Session:** fable multi-asset-v2 autonomous | **状态:** final | **作废条件:** 无（永久存证）
> 用户批准条件: "确保能够完美复原，有迹可循，则可考虑清理"（2026-07-12）。本文件即复原凭证。删除执行于 jpline `/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports/`（下称 $E）。背景: /mnt/storage 4TB 100% 满（0 字节），阻断全队写入。

## 删除项与复原方法

### 1. `$E/seq_cache/` — 358.7 GB, 1432 files（20220101.npz … 20251130.npz + feature_names.json）
- **用途**: 14 币时序-空间阶段（2026-06-09 启动，已收官）的逐日 1s 序列缓存。当前无任何在跑/计划任务引用（Engine A 宽书用 wide_dl*.npz）。
- **复原**: 运行 `multi_asset/data/build_seq_cache.py`（**git tracked, md5 `da38fb4f9f21af12e83b3fad10dec2ad`，已验证与 server 执行版 bit-identical**），源数据 `/mnt/storage/share/bar_data`（READ-ONLY，完好）。逐日重建，参数为脚本内默认（见脚本头）。
- **抽样校验和**（重建后可验证）: 20220101.npz `bee824c5573c7dd9b294412ed815e402` / 20240101.npz `90c49d48536a9e73400e8b628b58e6c5` / 20251101.npz `2a2252d45cc121199b59306c5fc4a427`。

### 2. `$E/mh_targets_long/` — 18.2 GB, 1430 files（20220101 … 20251130）
- **用途**: y_1800/3600 长 horizon 标签（NX 计划期；1h L/S 轨已判 NO-GO，无引用）。
- **复原**: `multi_asset/data/build_multihorizon_targets.py`（git tracked, md5 `baf78acbba348eaa143d4d529cf6c619`, 与 server 版 bit-identical），源 = bar_data。
- **抽样校验和**: 20220101.npz `b9355fea726e25848c5518fc29268ab5` / 20251101.npz `655e0315a93152363bcc5419462e59f5`。

### 3. `$E/panel_cache_bak487/` — 0.62 GB, 18 files
- **用途**: production `panel_cache`（487 天）的备份副本。
- **复原**: 删除前已验证 **18/18 文件 md5 与在役 `$E/panel_cache/` 完全一致** —— 在役副本即复原源（`cp -r panel_cache panel_cache_bak487`）。

## 明确保留（勿删清单）
`wide_dl.npz`（3-fold 协议复现资产）、`wide_dl_full.npz`、`panel_cache`、`panel_cache_full1429`、全部冻结资产（`d1_*_run1` / `npz_v2arch` / `run1_*`）、`train/`（判决 JSON）、`eda/`（审计产物）。

## 执行记录
删除顺序: bak487 → mh_targets_long → seq_cache。执行时间与释放量见下方追加行。
