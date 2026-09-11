> **创建:** 2026-09-11 | **Session:** round-2 LOB sleeve hunt | **状态:** VERIFIED (device receipt below) | **作废条件:** `w10_health.py` sha 8684d9a9… 的 `w3_at` 改写, 或 LOOK 不再是 900

# E-0911-A — LOOK=900 暖机段污染了 round-1 全部 standalone sleeve 的水平数

## 缺陷
`/workspace/review_scratch/health_check/w10_health.py` 的 `w3_at(i)` 第 166 行:

```python
p = pos.get(int(i), 0)
if p < LOOK: return np.array([1/3]*3)
```

前 `LOOK=900` 个锚**无条件**返回三腿等权 `[1/3, 1/3, 1/3]`, **绕过 LEGS 掩码**。
sleeve 臂用 `LEGS=001 PHI=0` 跑, 本意是"只有注入分的单腿书"; 但第 0..899 行实际是
**1/3 king + 1/3 rev24 + 1/3 注入分** 的三腿书。第 900 行起 `w3_fund` 才变成 1.0。

对 LOB 族更严重: LOB 原始数据始于 2023-01-01, 暖机段(2022-01-31..2022-06-29)注入分**全 NaN**,
`np.nan_to_num` 后 z 的 fund 分量恒为 0 ⇒ 那 900 个锚是**纯 king+rev24 书**, 与被测特征零关系,
且所有 LOB 臂在这 900 行**逐位相同**(实测 `np.array_equal` = True, 三个不同臂)。

## 量化(装置: judge 定义 g = net_ex/gross_total bps/锚/gross; GATE P 已逐位通过)
| 臂 | 暖机 0..899 g / Sharpe | 暖机后 g / Sharpe | 合并(= round-1 报的数) |
|---|---|---|---|
| `SL_ORTH_f_amihud_24h__p` | **+2.4815 / 4.05** | **+0.7097 / 1.54** | +0.8686 / **1.82** |
| `SL_ORTH_f_asz_24h__m` | +2.6141 / 4.29 | +0.6110 / 1.40 | +0.7905 / 1.74 |
| `SL_LOBDEPTH__m` | +0.6333 / 0.68 | +1.0625 / 1.90 | +1.0188 / 1.67 |
| `R2_ORTH_LDVOL__m`(本轮) | +0.6333 / 0.68 | −0.6529 / −1.13 | −0.5218 / −0.84 |

`w3_fund < 0.999` 的行数 = **900, 每个臂都是 900**(实测)。

## 结论
1. round-1 头条 **"ORTH_amihud standalone 全周期 +0.868 / Sharpe 1.83"** 里, 900 个锚(9.0%)不是 sleeve,
   是三腿书, 且那一段 Sharpe 4.05 —— **诚实的 standalone 数是 +0.7097 / Sharpe 1.54**(n=9018)。
2. 目标算术随之改口径: brief 写 `2.39 + 1.83 的无关 sleeve -> 3.01`; 用 1.54 则 `-> 2.84`, **达不到 3.0**。
3. **成对对照(paired D)不受影响**: 两臂共享同一暖机段, 差分抵消。受影响的只有**水平数与 standalone Sharpe**。
4. A0 反向受影响: A0 用 `LEGS=101`, 暖机段被塞进 1/3 rev24(已退役腿)。
   A0 全周期 archived **+0.6627 / 1.32**(与 brief 逐位相符), 暖机后 **+0.7421 / 1.52**。

## 本轮采用的口径
所有 sleeve 只在 `w3_fund == 1.0 且 gross_total > 0` 的锚上评估; LOB 族的评估锚集从 34 个 tranche-1 臂
取交集后**冻结**(`/workspace/uplift_2026-09-11/r2/LOBTS_frozen.npy`, n=7923, 2023-01-02 20Z .. 2026-08-25 00Z),
后续每个臂都判在同一锚集上。

## 收据
- GATE P: `w10_sleeve.py` sha256 `b88e35a46b93d712`, 六旋钮全关 ⇒ `V4_A0_{dyn,fix}_s{42,2027}` 的
  `d30_n2_c42_rec` / `d30_n2_c42_W` / `S0_rec` **4/4 逐位相等**, shape (10039, 23)。
- 复跑: `/workspace/uplift_2026-09-11/r2/gateP.sh`, 逐位比对 `/tmp/gp.py`
- 暖机量化: `/tmp/warm.py`; 逐位相同性 `/tmp/chk2.py`
