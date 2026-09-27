> **创建:** 2026-09-27 01:0xZ | **Session:** session_01VNPQL7t93ECz7Xkrv9rH6n (integ) | **状态:** FROZEN 首个 on 锚验收判据 —— 写于任何 on 读数之前(M3 从未以 on 运行过) | **作废条件:** lead 裁定;只追加 AMENDMENT

# M3 开启(beta_overlay.mode shadow → on)首锚验收判据

- 依据:用户裁定(lead 转达,2026-09-27);上限 2.5 取自 AMENDMENT_2 §1,用户 2026-09-23 14:1xZ 原话「按推荐来」。
- 打开步骤:AMENDMENT_2 §3 第 5 步。执行器语义:book.json `beta_overlay._semantics`,以及 live/beta_overlay.py `stage` / `after_cap` / `after_plan`。
- 装置:`devices/m3_on_first_anchor.py <A> [--expect on|shadow]`。只读、合池,不读任何分臂字段。
- 判定:F1–F9 全部 PASS ⇒ **PASS**。其中只有 F5 允许 WARN,出现时判 **PASS_WITH_WARN**,并写明原因。任一项 FAIL ⇒ **FAIL** ⇒ 交 lead,按回滚门执行。

| # | 检查 | 通过条件 |
|---|---|---|
| F1 | 配置与版本 | 运行树 book.json 中 `beta_overlay.mode == "on"`、`max_combined_leverage == 2.5`,且其余键与发布前逐字节相同(由版本探针 after-w3 负责);target_live 的 beta_overlay `version == m3_beta_v2`,`anchor_ts == data_cutoff_ts == A`;锚行记录 `mode == "on"`、`version_expected == m3_beta_v2`、`field_ok` |
| F2 | 状态 | `status ∈ {applied, applied_via_combined}`。若为 `budget_zero` / `combined_dust` / `refused` / 暂停(逐名止损或冷却中的 BTC),判 **UNDECIDED(按设计弃权)**,写明原因,交 lead;其余状态判 FAIL |
| F3 | 对冲算术(M3_SELFCHECK 的 on 口径) | 由订单表 plan 行重建**只含书**的执行目标:非 BTC 名 = target_w × book_gross_usdt,BTC 的书内成分 = 记录中的 `btc_book_target_usdt`。c1:非 BTC 的 Σ\|target_w\| + \|btc_book\|/G 与 1 的差 ≤ 1e-9;c2:BTC plan 行 target_w × G == `btc_combined_target_usdt`(相对 1e-9);c3:Σ book_i·β_i(用发布的 β,BTC 取 1)== `beta_exec_usdt`(相对 1e-9);c4:`hedge_intent_usdt == −beta_exec_usdt`,`hedge_target_usdt == intent × budget.scale`,`btc_combined == btc_book + hedge_target`(绝对差 ≤ 1e-6)。另报 B7v2 容差 max(1%·\|β_exec\|, 0.1%·NAV),只作参照 |
| F4 | 对冲腿确实下单 | 本锚至少有一条 BTCUSDT 订单行带 `m3_overlay_leg`,且 `submit_ts` 不为空;计划方向 = sign(combined − held) |
| F5 | 交付(回读) | 交付比 = (本锚回读 BTC − 上锚回读 BTC) / (combined 目标 − 上锚回读 BTC),均按本锚 mid 计价。∈ [0.8, 1.1] 判 PASS;∈ [0.5, 0.8) 或 (1.1, 1.3] 判 WARN(依据 AMENDMENT_3「首个 on 锚一次建满」,部分成交留待下一锚);其余判 FAIL |
| F6 | 合计 gross | 记录中 after_cap 的 `combined_target_gross` ≤ 2.5 × NAV(相对 1e-9);回读 gross(Σ\|venue notional\|,含 BTC)≤ 2.5 × NAV × 1.03,容差留给成交与价格漂移 |
| F7 | BTC 腿的执行与费用 | 只看 BTC 的成交(先用 collapse_supersedes 折叠):成交笔数、maker 标志计数、commission 合计、按成交名义折算的费率。每笔成交都要有 commission;费率 ≤ 5.0 bps(taker 费率);报出所走的订单类型路径。**不报任何分臂字段** |
| F8 | 书本身与 shadow 逐位相同 | 与 layered_book 同一套重建:E6 Σ L0 == net_producer_usdt;L1 重建能复现 reshape 报告的 net_after / gross_after;**所有未被钳位、未触场所上限的非 BTC 名 L2 == L1**,最大差 < 1e-6·G。shadow 下这条恒等式对全部未钳位名都成立,on 下它对非 BTC 名依然成立 ⇒ 书对生产者文件的函数不变。BTC 未被钳位时,L2 − L1 == hedge_target_usdt,差 ≤ 1 USDT |
| F9 | 无误报 | notify_audit 在 [A, A+1h] 内的 HIGH / CRITICAL 中,不得出现提及 净额 / 中性 / neutral / net / cond4b / gross 的新告警;watchdog 对本锚未触发;锚行 `net_over_gross` 仍在中性带内(\|net\|/gross ≤ 2%)。锚行的中性口径是否已剔除对冲腿,记录为 `neutrality_caliber` |

另外:
- lead 的标准验收(inspect_anchor / VERSION_PROBE / parity / anchor_report)照常跑。
- **B4_POOLED 中「不得有 overlay / 对冲单」那一条,是 shadow 时代的判据,on 之后应当反过来**。on 锚上以本装置的 F4 为准,B4 那一条判为不适用,须具名注明。
- **控制(写在读数之前)**:
  - 对 00Z 锚(1790467200,shadow)用 `--expect shadow` 跑,全部检查必须 PASS。shadow 口径下:F2 要求 `status == shadow`;F4 要求**没有**对冲腿订单;F5 不适用;F8 对全部未钳位名成立。这是基线为绿。
  - 同一锚用 `--expect on` 跑,必须在 F1 / F2 / F4 上 FAIL。这证明装置有分辨力。
