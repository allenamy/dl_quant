> **创建:** 2026-09-16 05:4xZ | **Session:** lead | **状态:** 生效(替代 59ec73d4 的就地标注) | **作废条件:** 各 DEV 项被其 owner 关闭并留受据

# DEV-01..DEV-11 装置更正 —— 旁挂本(**不得写回装置字节**)

## 为什么是旁挂而不是就地标注

K4 的方法是「原句字节保留, 后面挂更正块」。该方法对**散文文件**(STATE.md / CLAUDE.md / 登记册)是对的,
对**身份即证据的冻结装置是错的** —— 判官收据记录 `self_sha256`, 装置的字节**就是**证据本身,
只加注释也是一个新身份。**这条carve-out 是我(lead)批 K4 方法时漏了说的, 责任在我, 不在 AUD-KB。**

`59ec73d4` 对 8 个装置做了就地标注, 使它们的 sha 全部改变, 而这些 sha 被钉在**约 120 处**:
`SHA256SUMS.txt` 校验清单、`RECEIPT_*.json` 判官收据、5 份 PREREG/DESIGN、`STATE.md`, 以及几十份运行日志。
其中相当一部分是**已经发生过的运行的历史收据** —— 那些**不能**改写去迁就新 sha, 改了就是伪造记录。
故处置为**回退装置、旁挂标注**, 一步恢复全部约 120 处引用的正确性。

## 复原核对(回退后逐个实测)

| 装置 | 恢复后 sha16(= 被钉的那个) |
|---|---|
| `multi_asset/exports/live/pilot_journal/tools/parabolic_onset_forward_log.py` | `47dca131d8ffed81` |
| `multi_asset/exports/research/parity_replay_2026-09-12/phase2/devices/p2_g2c_judge.py` | `4951caf1526bc73b` |
| `multi_asset/exports/research/retrain_2026-09/v4_chain_2026-09-09/judge_v4.py` | `c2a81c48f0377560` |
| `multi_asset/exports/research/retrain_2026-09/v4_chain_2026-09-09/run_v4_arms.sh` | `0da0d464fea75ac2` |
| `multi_asset/exports/research/uplift_r2_2026-09-13/T4/devices/t4_judge.py` | `658835d70b46b6c1` |
| `multi_asset/exports/research/uplift_r2_2026-09-13/T5b/devices/t5b_q1.py` | `3c956b23ec353a14` |
| `multi_asset/exports/research/uplift_r2_2026-09-13/T5c/devices/t5c_bridge.py` | `e401f48ef68235a7` |
| `multi_asset/exports/research/uplift_r2_2026-09-13/T5d/devices/t5d_bridge.py` | `b99b870c70950f78` |

## 更正正文(按装置; 行号为 59ec73d4 中的插入位置, 仅供定位)

### `multi_asset/exports/live/pilot_journal/tools/parabolic_onset_forward_log.py`

- **@L14** ⚠ 更正 DEV-08 · P2 · AUD-KB K4 2026-09-16(原句字节保留, 不改写): 前向日志改读记账口径: 以原始 1m/5m 收盘价(未裁剪, float64)或 v4 记账元重算 onset 与 τ→下一锚收益; 在改之前, 日志与复判读数标注「裁剪缓存口径(E-0908-B 同族), 尾部为下界」并统计 |ret5|=0.30 饱和格数

### `multi_asset/exports/research/parity_replay_2026-09-12/phase2/devices/p2_g2c_judge.py`

- **@L43** ⚠ 更正 DEV-11 · P2 · AUD-KB K4 2026-09-16(原句字节保留, 不改写): G2-C 判官冻结 slot→anchor 映射, 断言每份收据恰一锚、集合无重漏, 并核 prep/输入身份与执行收据一致; 修前 G2-C PASS 只作「三份真实收据已人工核对」的描述

### `multi_asset/exports/research/retrain_2026-09/v4_chain_2026-09-09/judge_v4.py`

- **@L300** ⚠ 更正 DEV-02 · P2 · AUD-KB K4 2026-09-16(原句字节保留, 不改写): levels() 增列 `maxdd_nav2x_compound = max 峰谷 of Π(1+2·g·1e−4)`, 打印行改为「annual % per gross = mean*2190/1e4; NAV 回撤按固定 2× 逐锚复利列, 勿用算术 ×2」
- **@L351** ⚠ 更正 DEV-01 · P1 · AUD-KB K4 2026-09-16(原句字节保留, 不改写): 判官 (A) 追加两个条件(预注册修订, 用户裁定): ① 双种子 CI 下界 > δ(K2 D1 = 0.05 bps/锚/gross, 非 0); ② 全周期逐年(2023–2026)无一年 Δ 的 CI 上界 < −δ, 且 2023(弱年)点估计 ≥ −δ; 冻结窗之外的扩展/逐年读数写入 verdict 旁并在 (A) 时强制打印

### `multi_asset/exports/research/retrain_2026-09/v4_chain_2026-09-09/run_v4_arms.sh`

- **@L17** ⚠ 更正 DEV-03 · P2 · AUD-KB K4 2026-09-16(原句字节保留, 不改写): 固定席位臂仅作描述(不出 verdict), 或按预注册改为「被判窗动态席位均值」(A0 冻结窗 0.5338); verdict 以动态席位为准

### `multi_asset/exports/research/uplift_r2_2026-09-13/T4/devices/t4_judge.py`

- **@L152** ⚠ 更正 DEV-04 · P2 · AUD-KB K4 2026-09-16(原句字节保留, 不改写): 采用 FX-EVAL K2 规则 R-T4(δ D1 = 0.05 / D4 = 0.003)替换 L150 谓词; 本次存档读数重标 = INCONCLUSIVE(RELABEL_TABLE_K2 T4 行), 不另立标签

### `multi_asset/exports/research/uplift_r2_2026-09-13/T5b/devices/t5b_q1.py`

- **@L250** ⚠ 更正 DEV-07 · P3 · AUD-KB K4 2026-09-16(原句字节保留, 不改写): 采用 FX-EVAL K2 R-T5B(δ D8 = 0.05, 上侧 = 付出): MATERIAL ⇔ CI 下界 ≥ 0.05; NOT MATERIAL (established below line) ⇔ CI 上界 < 0.05; 其余 INCONCLUSIVE; mean None ⇒ NOT MEASURED(RELABEL_TABLE_K2 T5b 行: 主读法不变, 三个次级 MATERIAL → INCONCLUSIVE)

### `multi_asset/exports/research/uplift_r2_2026-09-13/T5c/devices/t5c_bridge.py`

- **@L209** ⚠ 更正 DEV-05 · P2 · AUD-KB K4 2026-09-16(原句字节保留, 不改写): T5c 装置保留原样(存档); 引用其标签时改引 FX-EVAL K2 重标(R-LOSS, δ D1 = 0.05): 价格与净额 = **SHARED LOSS, DIFFERENCE INCONCLUSIVE**, carry = INCONCLUSIVE(RELABEL_TABLE_K2 T5c 行); 新装置复用 R-LOSS, 不复用本谓词

### `multi_asset/exports/research/uplift_r2_2026-09-13/T5d/devices/t5d_bridge.py`

- **@L75** ⚠ 更正 DEV-06 · P2 · AUD-KB K4 2026-09-16(原句字节保留, 不改写): 引用 T5d 标签时改引 FX-EVAL K2 重标(R-LOSS, δ D1 = 0.05; RELABEL_TABLE_K2 T5d 行: 价格/净额 SHARED LOSS, DIFFERENCE INCONCLUSIVE); PREREG §6.2 的 δ = 0.25 只能写作「A0 全周期净额约 40% 的量级线(≈10.95% NAV/年 @2×)」, 不得称「经济上可忽略」

## 规则(即刻生效, 全线)

**凡 sha 被任何收据/清单/预注册钉住的文件, 一律不得就地标注 —— 连注释都不行。**
更正写进本旁挂本或该线登记册, 并在引用处指向它。
判别法: 改之前问一句「这个文件的 sha 有没有被写进过任何一份收据?」有 ⇒ 旁挂。
