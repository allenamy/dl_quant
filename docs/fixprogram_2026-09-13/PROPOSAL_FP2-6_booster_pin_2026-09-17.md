> **创建:** 2026-09-17 04:5xZ | **Session:** 0134cBjSFjjurUhAz95RNuWk | **状态:** 待用户裁定(线上行为门; 本件零部署、零改动执行器运行树) | **作废条件:** 在役 bundle 换装(sha 变)、`external_book.py` 钉逻辑变、或用户裁定后本件升为 RUNBOOK 修订

# FP2-6 · 执行器钉模型身份(booster_sha_pin)— 提案

## 0. 一句话
执行器读者已经**完整实现并被套件认证**了「钉 sha 不符 ⇒ 拒读 ⇒ HOLD」, 只是生产配置把两个钉都留空。建议**只钉 booster**(填在役 king bundle 的 sha256), **不钉 universe**(宇宙每月滚动, 钉了每次滚动都会 HOLD)。这是配置改动, 但改变线上行为的一个分支(模型身份不符时从「照常交易」变为「持仓不动 + HIGH 告警」), 按 CLAUDE.md 约束 5 需要用户字。

## 1. 事实(全部本会话读原件, VERIFIED)
| # | 事实 | 出处 |
|---|---|---|
| F1 | 读者钉检查: `if cfg.get("booster_sha_pin") and doc["booster_sha"] != cfg["booster_sha_pin"]: return _err("booster_pin", …)`; universe 同型 | `~/dl_quant_live/live/external_book.py` L380-386(运行树 6661ea3) |
| F2 | 拒读后的动作: `if ext is not None and not ext["ok"]: if action == "TRADE" or _ext_cfg["on_unavailable"] == "hold" or age == inf: action = "HOLD"`; 注释「A failed read NEVER trades and NEVER falls back to the internal composer」 | `scheduler/anchor_loop.py` L1426-1431 |
| F3 | 生产配置 `on_unavailable = 'hold'` ⇒ 拒读永远 HOLD, 不进 DERISK/FLATTEN 梯 | `config/book.json external_book` |
| F4 | 套件已认证: R2 `booster_sha pin mismatch ⇒ booster_pin`(读者层); H6 `on_unavailable=hold ⇒ HOLD even 20 anchors stale (never DERISK/FLATTEN)`; 源码钉格把 L1426-1431 的字节钉死 | `live/tests_external_book.py` L313-315 / L628-636 / L859-864 |
| F5 | 在役 bundle `~/wide_shadow/shadow_bundle/slow2026.txt` sha256 = `8d79186b6380132cb67684acf1ebfcdb2c53261c850f46a4908b06bfa7a81282`; target_live 逐锚 `booster_sha` 与之相同(64 hex) | 本会话 shasum + `state/target_live/1789588800.json` |
| F6 | target_live schema `wide_target_v1` 顶层键: anchor_ts, booster_sha, gross_norm, n_names, n_universe, producer, schema, universe, universe_sha, weights, weights_sha, written_utc —— **没有 F10/DL 模型身份字段** | 同上 |
| F7 | `run_acceptance.sh`: 任一套件 exit≠0(含 3)⇒ NOT GREEN; 且 `live/tests_*.py` 未登记即拒跑 | `run_acceptance.sh` 尾部 |
| F8 | 换装步骤单(十月 runbook §0★ 步 8)与 `CHECKLIST_combo_switch_2026-08-26.md` 均**不提** `book.json` 钉 | 两文件 grep 零命中 |

## 2. 建议的改动(裁定通过后才做, 经 `ops/safe_commit.sh` + 电池全绿 + 与 6661ea3 同样的部署 runbook)
1. **配置**: `config/book.json external_book.booster_sha_pin: null → "8d79186b…1282"`。补丁已生成(零上下文漂移): `FP2_receipts/fp2-6_booster_pin_book_json.patch`。`universe_sha_pin` **保持 null**(理由 §3.2)。
2. **换装步骤单**(十月 runbook §0★ 步 8 与 §3-3)加一行: 「换 bundle 与改 `booster_sha_pin` 必须在**同一个锚间静默窗**内完成(顺序无关), 电池全绿后才进下一锚; 回滚 bundle 必须同时回滚钉」。
3. **不加**「钉==bundle sha」的电池格: 电池在执行器提交时跑, 换装是生产者侧动作, 电池抓不到; 真正的守卫就是 F1-F3 那条锚时路径本身。加格只会在裁定前把电池染红(F7)。

## 3. 后果分析(辩证)
### 3.1 钉了之后, 各种情形
| 情形 | 现状(钉空) | 钉后 |
|---|---|---|
| 正常锚 | 交易 | 交易(sha 相同, 零变化) |
| 有人/有进程换了 king bundle 但没改钉 | **照常按新模型交易**(执行器不知道) | HOLD + HIGH 告警, 直到钉被改; 持仓不动, 不平仓 |
| 生产者写坏 booster_sha 字段 | 只校验自洽 ⇒ 交易 | HOLD + 告警 |
| 回滚 bundle 忘了回滚钉 | 交易 | HOLD + 告警 |
安全方向一致: **错误只会让书停在原地, 不会让书按未授权模型交易, 也不会触发平仓**(F2/F3/H6)。代价: 忘改钉 = 少交易若干锚 + 告警噪音。

### 3.2 为什么不钉 universe
`universe_sha` 是 symbols_live 列表的 sha256(order-preserving)。宇宙 Phase A(M1)每月滚动、宇宙事件(下市/新上)也改列表 ⇒ 钉了会在每次合法滚动时 HOLD。读者已经**重算**列表 sha 并拒绝不自洽(`universe_list_sha` 格), 完整性已有保障; 钉 universe 换来的只是「拒绝一切宇宙变更」。

### 3.3 局限(如实)
- **F10/DL 腿身份仍不可钉**(F6): schema 没有该字段。现有守卫是 sidecar 的 `SIDECAR_DRYRUN PASS 每锚` + combo_stage 五层安全 + 换装 checklist 的 np≡torch 平价。要钉它需要生产者扩 schema(`f10_sha` 字段)+ 读者加钉 —— 生产者改动, 另立 FP2-6b, 不在本裁定内。
- 钉只防「身份不符」, 不防「同 sha 的模型本身不好」—— 那是 FP2-8 判官的事。

## 4. 需要用户回答的
**(a) 是否同意钉 booster(§2.1)?** 同意 ⇒ 我按 §2 落地(safe_commit + 电池 + 部署 runbook + STATE/记忆更新), 与 6661ea3 部署同一套流程; 首锚验收看 external_book.ok=true 与 booster_sha 一致。
**(b) 是否同意 universe 不钉(§3.2)?**
不回答 = 维持现状(钉空), 本件保持「待裁定」。

## 5. 用户裁定(2026-09-17 09:0xZ)与执行
- (a) **钉 king: 已部署** 执行器 6e177c4(09:16Z; 生产电池 160/1/0, 唯一红 NOSLEEP-1); 首锚 12:24Z 验。(b) **universe 不钉**: 确认。
- (c) **DL 也钉 = FP2-6b**, 三步、各在锚间窗:
  1. 执行器读者(叠加树已改, 套件 132/132 含 R2f0–R2f5): 配置 `external_book.f10_sha_pin`(缺省 null); 钉设时文件缺 `f10_sha` 或不等 ⇒ `f10_pin` 拒读 ⇒ HOLD; 每锚 anchors 行记录 `f10_sha`。部署时机: 12:24Z 锚(king 钉首锚)收尾后、16:00Z 前。
  2. 生产者 `~/wide_shadow/fea171/combo_stage.py`(非 git; 补丁 `FP2_receipts/fp2-6b_combo_stage_f10_sha.patch`): 在 `_doc` 写 `f10_sha` = 所载 `f10_live_s42_np.npz` 的 sha256(现役 351ae26b…), 自验配置加 `f10_sha_pin: None`。先用 `COMBO_LIVE_DIR=…/target_live_REHEARSAL` 排练一锚(读者验收 ok 且文件含 f10_sha), 再生效; 生产者快照入研究仓。时机: 与步 1 同窗或下一窗。
  3. 看到一锚 anchors 行含 `f10_sha == 351ae26b…` 后, 执行器配置 `f10_sha_pin` ← 该值, 同一部署协议。时机: 16:24Z 锚后、20:00Z 前。
- 与换装的耦合: 以后换 F10 模型与改 `f10_sha_pin` 必须同窗(runbook §0★ 修订 10 同句扩到 DL)。
