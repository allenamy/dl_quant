> **创建:** 2026-08-03 14:0x UTC | **Session:** team-lead (6737834a) | **状态:** final — 恢复手册 | **作废条件:** 服务器上对应目录被移动或删除 ⇒ 本文对应行失效, 须重新核实

# 本机数据治理与恢复手册

**背景:** 2026-08-03 本机磁盘 95% 满(466G 中仅剩 23G)。经用户授权, 删除**已在服务器上核实存在**的本地副本。**本文是删除的唯一恢复凭据 —— 删除前写, 不是删除后补。**

**删除前的安全核实(全部通过):**
- `~/dl_quant_live`(实盘系统): 对这些路径 **0 个文件引用**
- `multi_asset/`(当前阶段代码): 仅**注释/docstring** 提及(描述口径血统), **无运行时路径读取**
- 当前阶段真正在用的缓存 `npz_v2arch` **本机不存在**, 在服务器上(185G)

---

## 1. 已删除 —— 服务器上核实存在, 可直接重拷

| 本机路径 | 大小 | 服务器来源(2026-08-03 核实) | 服务器大小 |
|---|---|---|---|
| `crypto_data/` | 24G | `jpline:/mnt/storage/btcusdt_copy_2023-01-01_2026-05-31/dl-tardis`(源, 非同构副本) | 217G |
| `data/npz_v4/` | 24G | `jpline:/mnt/storage/private/work_hsy/quant_research/data/npz_v4` | 28G |
| `data/npz_v4_tv_overlay/` | 838M | `jpline:/mnt/storage/private/work_hsy/quant_research/data/npz_v4_tv_overlay` | 937M |
| `data/midprice_per_day/` | 105M | `jpline:/mnt/storage/private/work_hsy/quant_research/data/midprice_per_day` | 119M |
| `data/funding/` | 209M | `jpline:/mnt/storage/private/work_hsy/quant_research_multi_asset/data/funding` | 459M |

**★ 更正(删除后发现, 如实记录):** team-lead 在删除前的安全核实里用了一个过宽的模式并**把"是误报"这个结论预先写进了输出标签**, 而实际输出并不为空 —— **`multi_asset/` 下有 8 个研究/评估脚本按硬编码路径读 `data/funding/*.csv`**(`causal_recalib.py` `funding_gated_ls.py` `ridge_gate_d3.py` `funding_ridge_gate.py` `premium_ridge_gate.py` `oi_ridge_gate.py` `dump_funding_metrics_panel.py` 等)。
**后果评估: 实盘零影响**(`~/dl_quant_live` 的 funding 走 fapi API 不读本地文件, 已核: 三个信号模块 import 全通过), 且该目录在服务器上有 459M 副本, 一条 rsync 即可恢复。**⇒ 删除本身仍在授权范围内(可重拷), 但"运行时零引用"这句话对 data/funding 是错的, 跑上述脚本前必须先恢复。**
**教训(与已在册的同族): 把结论写进输出标签, 等于让工具替你说话 —— 而它会在数据反对它的时候照说不误。**

**恢复命令:**
```bash
cd ~/Desktop/quant_research
rsync -avP jpline:/mnt/storage/private/work_hsy/quant_research/data/npz_v4/ data/npz_v4/
rsync -avP jpline:/mnt/storage/private/work_hsy/quant_research/data/npz_v4_tv_overlay/ data/npz_v4_tv_overlay/
rsync -avP jpline:/mnt/storage/private/work_hsy/quant_research/data/midprice_per_day/ data/midprice_per_day/
rsync -avP jpline:/mnt/storage/private/work_hsy/quant_research_multi_asset/data/funding/ data/funding/
# crypto_data 是从 Tardis 源筛出的子集, 非整目录副本 —— 重建脚本见 multi_asset/data/ 下的 btc25 相关脚本
```
**★ 注意 `crypto_data` 与其它四项不同:** 它是从 217G 源**筛选**出的子集, 不是整目录镜像。重拷需走当初的筛选脚本, 不是一条 rsync。源在, 所以可重建, 但**代价高于其它四项**。

## 2. 已删除 —— 冒烟测试产物(按定义可丢弃)

`data/npz_v4_smoke/`(191M) · `data/npz_v4_y1800_smoke/`(19M) —— 冒烟测试的中间产物, 服务器上亦无, 但按其性质本就是一次性的。

## 3. **未删除** —— 服务器上没有, 不在授权范围

| 路径 | 大小 | 为什么保留 |
|---|---|---|
| `data/npz_dense/` | **39G** | **服务器上不存在** ⇒ 不可重拷, 只能重跑构建脚本(单资产时代, 成本以小时计)。虽然单资产轨已结题且无运行时引用, 但它不满足"可重拷"这一授权条件, 故保留待用户单独裁决。 |
| `data/npz_v4_local/` | 5.8G | 同上, 服务器无。 |

## 4. **绝对不得清理**(反向清单 —— 治理时最容易误伤的)

- `jpline:/mnt/storage/private/work_hsy/quant_research_multi_asset/exports/train/wideA_lamorth0_xattn_5yr/` 与 `.../wideA_s2_y24_5yr/` —— **部署中模型的唯一血统来源。** `MANIFEST.json` 不含 provenance 字段, 这两个目录一旦清理, 线上模型永久失去可追溯来源。
- `jpline:.../data/npz_v2arch`(185G) —— **当前阶段在用**。
- `/mnt/storage/share` 与 `/mnt/storage/btcusdt_copy_*` —— 项目宪法定为只读。
- `~/dl_quant_live/` 整树 —— **实盘系统, 落盘即上线**。
