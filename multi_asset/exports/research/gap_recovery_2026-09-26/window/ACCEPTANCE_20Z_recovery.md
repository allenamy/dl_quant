> **创建:** 2026-09-26 17:3xZ | **Session:** session_01VNPQL7t93ECz7Xkrv9rH6n(lead) | **状态:** 冻结判据,写于 20Z(1790452800)任何读数产出之前 | **作废条件:** 20Z 前生产者/combo/执行器代码或配置变化

# 主机迁移中断后首锚(20Z 1790452800)恢复验收

背景:09-26 11:14Z–16:58Z 期间 macOS 迁移(2 次重启、1 次睡眠),12Z 与 16Z 两锚生产者、combo、执行器都没有运行,16Z 执行器在下任何单之前被杀。17:19Z 已装状态桥(`BRIDGE_RECEIPT_1790438400.json`)。用户判定:漏掉的两锚属于正常,不补交易。

## 判据(按层,逐条给出 PASS / 预期偏差 / RED)
1. **生产者 20:12Z**:`shadow_log.jsonl` 里有锚 1790452800 的 `signal` 行,status=OK,coverage ≥ 0.95;有 `target_live` 行;没有 `anchor_error`。
   - **预期偏差(不算红)**:没有 08Z 的 `score` 行(L752 要求相邻 4h);`leg_returns_live.json` 不追加,20Z 之后仍与安装件逐位相同(sha 5a1ed5a0…)。
2. **combo 20:17Z**:`target_combo/1790452800.json` 中 `kc_state_source=own`、`fc_state_source=own`;`target_blend/1790452800.json` 中 `h_source=own`;gross ∈ [0.4, 1.2];`combo_live_status` 为 ok=true、step=done。
   - **预期偏差**:`self_parity_maxdw` 偏大(weights/16Z 故意不写,H=0),只是诊断项。
   - **RED**:ABORT,或任何 `warmstart_*` / `king_fallback` 状态源。
3. **执行器 20Z**:`anchor_runs.log` 出现 `anchor done rc=0`。首条命令为 `inspect_anchor.py`(标准验收:VERSION_PROBE OK、M3_SELFCHECK OK、parity n_differing 0、B4_POOLED OK)。
   - 本锚换手会大于常规:持仓是 08Z 的书,市场已走 12h;只报合池量。
   - **RED**:HOLD、SKIP、rc≠0,或验收任何一项红。
4. **对账**:
   - `daily_nav` 有 20Z 行,12Z/16Z 无行(属于预期,须具名);
   - `funding.jsonl` 补入 08Z 之后到 20Z 的结算,若有 skipped 须具名;
   - 回读持仓与目标闭合,按标准 B4 口径。
5. **席位重播种首锚**:`reseed_first_anchor.py --anchor 1790452800`。
   - 判据 (1) 预期为 `UNDECIDED (k=0)`,因为没有追加。这是由缺口决定的,不算红。
   - 判据 (2) 席位对 regime_dash 的 w3_raw 必须在 5e-5 以内,否则 RED。
   - 00Z(1790467200)是第一个 k=1 的锚,届时三条判据全判。
6. **comboparity 20Z**:快照重放 PARITY(快照含桥接的 16Z 状态文件),否则 RED。

任何 RED ⇒ lead 按回滚与 HOLD 规程处理,并报用户。
