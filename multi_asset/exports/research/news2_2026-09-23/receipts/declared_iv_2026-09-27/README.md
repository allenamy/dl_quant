> **创建:** 2026-09-27 06:5xZ | **Session:** session_01VNPQL7t93ECz7Xkrv9rH6n(news2) | **状态:** 取证结果(runbook §3c,lead §7 裁定 5),待 lead 裁定用法 | **作废条件:** fundingInfo 的覆盖面变化(再跑本装置)

# declared_iv 取证:「不在 fundingInfo 里 ⇒ 8h」

装置 `d10_declared_iv_evidence.py`,先入库、后运行(305bc42d79fa4f36b27d0bbd2934b6d41a2edfe0);自测 5/5。pod2 于 2026-09-27 06:4xZ 运行;读 2026-01 到 08 共 8 个 VERIFIED 月。

1. **文档**:官方说明原文为「Query funding rate info for symbols that had FundingRateCap/FundingRateFloor / fundingIntervalHours adjustment」,**没有**说其余的名都是 8h。
   - 这段原文经 WebFetch 取得,是模型转述后的引文,不是字节快照。原页面对 curl 返回 202 且内容为空,**字节快照未取到**。
2. **当前响应**:791 个名,间隔分布为 1h 1 个、4h 469 个、8h 321 个。响应原文见 `D10_DECLARED_IV_EVIDENCE_fundingInfo_raw.json`。
   - **它现在把 8h 的名也列出来了**,实际上已覆盖几乎所有名。
3. **A**(不在响应里的名,2026-08 的每一行都应是 8h):2026-08 归档中共 11 个这样的名。
   - 其中 8 个有非 8h 的行,且都已下架(exchangeInfo 查无此名),与「在役名」无关。
   - 其余 3 个(EOSUSDT、FRONTUSDT、MATICUSDT)全部是 8h,**但它们同样已不在 exchangeInfo 里**。
4. **关键事实**:当前 570 个 TRADING 永续合约**全部**出现在 fundingInfo 中,缺名为 0。
   - 所以「缺名 ⇒ 8h」这条分支**在在役人口里没有任何适用对象**。归档上「0 例不符」是在 0 个在役名上成立的,**不构成证据**。
5. **B**(在响应里的名):655 个与归档最后一行一致;14 个不一致,可能是 9 月之后的调整(归档止于 08-31),本装置判不了。另有 122 个名在 2026-01 到 08 的归档中完全没有,多为新上的名。
6. **C**:7 个缺名在更早的月份用过非 8h 间隔、之后又回到 8h,全部已下架。

**建议**(lead 裁定):不启用「缺名 ⇒ 8h」,缺名一律走 UNRESOLVED 并具名告警。依据:在役人口中缺名为 0,所以这样做今天的成本也是 0;而这条规则的证据在在役人口上为空。
