> **创建:** 2026-09-11 | **Session:** round-5 NEW DATA 3 | **状态:** 提案, 未部署, 归用户裁定(书行为改动 = 预注册 + 用户裁定) | **作废条件:** 用户否决, 或 Phase B(M2)以别的形式落地

# PROPOSAL — monthly membership refresh for the 450-name universe

**This is a repair, not an uplift.** It adds no signal. It removes a cost the book is currently paying and
which grows every month. Evidence: `RESULT_r5_newdata3_universe_2026-09-11.md` §1-2.

## 1. The fact being repaired
`shadow_loop_v3.py` has **no code path that changes `symbols_live`**. The list has been byte-identical since
2026-08-16 (sorted-list sha256 `8aebc19d1e406f37`); the 2026-09-01 bundle rebuild replaced the booster and left
the universe alone. M1 (2026-09-04) widened only the fund-leg RANK BASE, not the tradable set.

At v4 caliber and the fitted cost, on the **deployed (fix) seat**, full cycle n=9018:

| staleness of the roster | Sharpe | dg vs fresh, CI95 |
|---|---|---|
| 0 (monthly, = A0) | **0.4841** | — |
| 1 month | 0.3420 | [-0.201, +0.059] |
| 3 months | -0.0214 | **[-0.471, -0.017]** |
| 6 months | -0.3174 | **[-0.650, -0.091]** |
| 12 months | -1.3393 | **[-1.218, -0.407]** |

The book is at ~0.9 months today and has no mechanism to stop. In 2026 an average of **51.3 names per month**
enter or leave the venue's top-449 by trailing-30d volume (0.5/month in 2023, 2.2 in 2024, 12.2 in 2025).

## 2. The proposal
At the first anchor of each calendar month, rebuild `symbols_live` as:

```
eligible = { venue PERPETUAL & quoteAsset==USDT & status==TRADING & underlyingType in (COIN, INDEX) }
           AND listed >= 30 days                     # the age rule already used by the member filter's 7d window
           AND trailing-30d quote volume > 0
new_live = top 450 of eligible by trailing-30d quote volume (sum of the 5m quote volume over 8640 bars
           strictly before the anchor)               # identical statistic to the U-PIT mask this study measured
```
Everything downstream is unchanged: `NTOP=400` by `log_qv`, `cov_min 0.95`, `vol_min 1e-4`,
`qv4h_min 2.5e5`, `EXIT_ON_LEAVE` / `EXIT_NON_MEMBERS` / the liquidity-exit set.

**This IS Phase B (M2).** `docs/PREREG_deploy_universe_2026-09-04.md` already pre-registered it ("Phase B
宇宙逐锚变, 首锚验收项含 universe_sha 轮换、n_in_universe、强制出场清单"), scheduled it for 2026-09-07, and
built `~/universe_shadow/universe_shadow.py` to score it (book C = "Phase B 起为动态成员"). **It has not
shipped**: the shadow's 42 logged anchors carry only books A and B (both frozen-member), and
`shadow_loop_v3.py` still has no refresh path. This proposal is not a new idea; it is a re-measurement of a
pre-registered, unshipped one at v4 caliber and the fitted cost, and the acceptance criteria in that PREREG
§3 should be the ones used.

**Not proposed:** widening past 450. `WIDE529` and `WIDE600` were measured and their dg CI95 straddles zero in
8/8 cells — the 80 names the venue lists and the book cannot trade are excluded *because* they are illiquid
(only 7 of 80 clear the 250k `qv4h` gate at a majority of 2026 anchors). Note the qualifier: A0 **already**
carries the 829-wide fund-leg rank base (M1, shipped 2026-09-04), which is where
`docs/RESULT_universe_dyn_2026-09-04.md` located +0.06..+0.085 of its +0.10 widening prize; that campaign
itself priced the extra *tradable* names at only +0.02..+0.03, and my measurement cannot separate that from
zero. Breadth beyond M1 is not the lever; freshness is.

**Not proposed:** any age tilt. Measured and refuted, four ways (RESULT §3).

## 3. What it costs
- **Turnover: measured, ~zero.** The names that drop out of the top-449 at a month boundary carry a mean
  **0.011%** of book gross (max 0.30% over 55 month-boundaries) at the last anchor before they leave, because a
  name that has fallen out of the top-449 has already been zeroed by the `qv4h >= 250k` gate. At the tier-2
  forced-exit rate of 4.7 bps that is below 0.001 bps/anchor.
- **Turnover goes the OTHER way.** Fix-seat mean turnover rises with staleness: 0.0160 (fresh) -> 0.0180 (3m)
  -> 0.0198 (6m) -> 0.0231 (12m). A stale roster keeps force-flattening names that fall through the gate.
  Refreshing is turnover-**negative**.
- **Data cost:** the 5m cache must carry columns for names not yet in `symbols_live`, or a new entrant starts
  with no history and fails `cov_min 0.95` for 7 days. Two options, and this is the real engineering decision:
  (a) fetch klines for the venue's full TRADING list (~528 names) instead of 450 — a 17% increase in the
  per-anchor kline weight, which the design budget (<900 weight/anchor, measured usage well under it) can
  absorb; or (b) accept a 7-day warm-up during which a new entrant is listed but not yet a member. **(a) is
  what I would do** — it makes entry instantaneous at the month boundary and costs only fetch weight.

## 4. What must be checked before it goes anywhere near the book
1. **This study did not test the live form.** Every number here is replay at ~355-425 allowed names per anchor;
   the live book trades 258-261. The replay-vs-live breadth gap (`docs/AUDIT_live_vs_replay_2026-09-04.md`
   row 2) is unchanged by this work. The staleness *direction* is robust (monotone, 8/8 cells, both seats,
   both seeds); the *magnitude* is not a live forecast.
2. **The survivorship trap must not be re-run as evidence.** `UFROZEN450` (today's 450 projected back) reads
   +0.225 to +0.462 **better** than monthly refresh. That is look-ahead. It is in the artifacts precisely so
   that nobody re-derives it later and reads it as a defence of freezing.
3. **Deployment is a separate event** per `RUNBOOK §B` (>= 3 days' separation from any other change, explicit
   user word). A universe change moves `universe_sha`, which the executor pins
   (`external_book.universe_sha_pin`, currently null in `config/book.json`) — the change must be a declared
   version event, not a silent bundle rebuild, exactly as `DESIGN_wide_shadow_2026-08-16.md` §2 already requires
   ("新上币不静默加入(周刷事件显式记录)").
4. **Two held names are already dead**: `SCRTUSDT` and `STORJUSDT` are `SETTLING` on the venue today. They are
   in the universe file and cannot be traded. Even without the monthly rule, they should come out.

## 5. Proposed diffs to `ELIGIBILITY_CONTRACT.json` / `judge_v4.py`
**None.** Nothing in this study changes the v4 retrain chain's gate definitions or its judge. The change this
study proposes is to the producer's universe construction (`~/wide_shadow`, non-git, user-owned), not to the
eligibility contract. I have not edited either file.
