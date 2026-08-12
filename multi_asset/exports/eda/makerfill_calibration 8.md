> **创建:** 2026-07-12 | **Session:** 0C Track-1 execution calibration | **状态:** final | **作废条件:** live maker-fill pilot 落地(实测 fill/markout 替换回放先验),或 bar_1s 口径重建

# Track-1 maker-fill 保守回放校准 — pilot 判词 (0C)

**一句话: PILOT 值得开。** 保守 maker-fill 下界(join-at-back 队列 / 仅 trade-driven 消耗 / **不记 spread-capture 利润** / 小币档显式 haircut)下,xattn 书有效成本 **~1.5-1.9 bps/side(全书)/ ~1.0-1.6(calib-grounded @k300)/ ~0.4-1.0(calib-grounded @k900)—— 远低于 5 bps taker 底**,逐年净 Sharpe 保持 **+9~+22(含弱年 2022/2026)**。**★ calib-grounded 书(≥$4M/h,零外推)已独立净正 → 判词不依赖小币外推。**

## 1. 校准场 = 14 mega-cap bar_1s(5 档 LOB + 成交流,12 天跨 2022-2025)

保守法: 挂 touch 被动单;queue-ahead = 全 L1 名义(join-at-back);仅按对手侧 taker 名义消耗(排除 cancel);我方全单 O 须在 L1 之上清完;窗口 k 内成交;成交后 D=60s adverse markout。

**流动性谱(小时名义)+ 成交经济(bps):**
| coin | hrN $M | spread | markout | eff-if-fill(−=利润) |
|--|--|--|--|--|
| btc | 628 | 0.02 | −0.07 | +0.06 |
| eth | 345 | 0.05 | −0.20 | +0.18 |
| sol | 75 | 0.64 | −0.07 | −0.25 |
| xrp | 57 | 1.94 | −0.27 | −0.70 |
| ... | ... | ... | ... | ... |
| fil | 5.1 | 2.27 | −0.23 | −0.90 |
| trx | 4.0 | 1.00 | +0.04 | −0.54 |

**关键发现:** (a) **fill-rate 曲线在 f=order/hourly-notl 上流动性无关**(BTC≈TRX):f≤0.5% 时 >0.95,f~2% 后崩;(b) adverse markout **极小**(−0.03~−0.38 bps);(c) half-spread capture 0.01(BTC)→1.1 bps(小币)。⇒ 成交的 maker 单是**便宜到盈利**的,但**我们保守地把成交成本 floor 到 0(不记做市利润)**。

## 2. 外推 caveat(诚实量化)

**★ 109/140 宽币在 $4M/h 校准底之下**(宽币中位 $1.25M/h)。小币档**外推**并加显式保守 haircut: fill×0.7 / adverse=p25(更差尾)/ spread-capture 只信 50%。**决定性: calib-grounded 书(≥$4M/h,~31 币,零外推)独立净正(净 Sharpe 9-16)→ 外推尾是边际拖累非承重,pilot 判词对外推稳健。**

## 3. 保守净 Sharpe(floor 版,$10M AUM)

| 书 / 年 | 2022 | 2023 | 2024 | 2025 | 2026 | 有效成本 bps |
|--|--|--|--|--|--|--|
| 全书 k300 | 10.5 | 16.6 | 19.6 | 20.7 | 11.1 | 1.7-1.8 |
| mega+mid k300 | 10.2 | 17.4 | 19.8 | 21.9 | 12.5 | 1.6-1.7 |
| **calib-grounded k300** | **9.2** | **16.0** | **17.7** | **19.0** | **14.3** | **1.4-1.6** |
| **calib-grounded k900** | **10.1** | **16.9** | **18.6** | **20.2** | **15.3** | **0.6-0.8** |

**全部逐年净正**,含弱年。**mega+mid ≥ 全书**(丢贵的小币尾改善净);**calib-grounded 2026 反而最高**(14-15 vs 全书 11 —— 弱年丢流动性尾更划算,呼应 0C 容量表"小币容量受抑非承重")。AUM $5M→$25M 净 Sharpe 缓降无悬崖。

## 4. Reads

- 有效成本 ~1.5-1.9 bps(全书保守)vs 加冕用的 5 bps taker → maker 把成本砍到 1/3~1/2,净 Sharpe 回到近 gross。
- **k=900(15min 工作)** vs k=300: fill 0.5-0.84 vs 0.3-0.5,成本 0.4-1.0 vs 1.0-1.6(calib)—— 工作时长是成本操作杆。
- 更高 AUM → 单更大 vs 成交量 → fill 降、成本升,但缓;测试区无悬崖。

## 5. Pilot 建议书

- **开 $2-5M live maker-fill pilot,交 calib-grounded / mega+mid 核心**(≥$4M/h ~31 币 全验证;或 ≥$0.89M/h mega+mid)。**<$0.89M 小币尾可选,起步不带。**
- **规模:** $2-5M 起(净 Sharpe 跨 $5-25M ~平,成本缓升),实测 fill/成本确认后扩到 $10-25M。
- **工作:** touch 被动挂,工作 k=300-900s,残余 taker 补齐。
- **成功判据:** 实测 fill ≥ 校准(核心书 ≥0.40@k300 / ≥0.65@k900);实测有效成本 ≤ 2.0 bps/side;实测 adverse markout(D60s)在实测 −0.05~−0.4 的 ~2× 内;实测净边际 ≥ 本保守下界。
- **止损线:** 有效成本 >3.5 bps(逼近 taker)持续 / fill ≪ 校准(<半) / adverse markout >1 bp(信息流 pickoff 超预期)。

## 6. 诚实 caveats(量化)

1. 保守 floor **不记 spread capture**(真实书大概率能赚一些 → 上行)。
2. 1s bar 聚合忽略秒内 trade/cancel 排序(对 adverse 排序略乐观);被 join-at-back + 排除 cancel(对 fill 保守)抵消 → order-of-magnitude,双向 bracket。
3. adverse 用 D=60s markout;更长视野信息 pickoff 可能更差,但实测 markout <0.4 bps,即便 2× 亦小。
4. **2026 无 bar_1s(2025-11 止)→ 2026 用外推法**,标为 model 非观测。
5. 净 Sharpe **量级**(9-22)仍带频率×breadth×参与模型 caveat(同加冕/容量文档);**可部署结论是有效成本(~1.5 bps 保守)≪ gross 边际 = 书能扛真实 maker 执行**,非 Sharpe 数本身。

---
**产物:** `makerfill_calibration.json` · `makerfill_calib_raw.json`(14 币校准)· `makerfill_apply_raw.json`(书应用)· `calib_makerfill.py` / `apply_makerfill.py`(可复算)
