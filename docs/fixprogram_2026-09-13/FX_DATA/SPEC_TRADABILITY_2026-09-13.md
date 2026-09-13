> **创建:** 2026-09-13 15:0xZ | **Session:** FX-DATA (fix worker, teammate of team-lead) | **状态:** FROZEN before any effect number (this commit precedes every probe and every replay run of TRD-01..05) | **作废条件:** the canonical cache sha changes (holefix2 1d7f459dee434ec4 / x0910 8115299410cd5e8d), or an amendment file `SPEC_TRADABILITY_AMENDMENT_<n>.md` is committed with its reason stated before the numbers it affects

# SPEC — tradability defined by actual trades (FIXPROGRAM §4.3 TRD-01; also TRD-02 / TRD-03 / TRD-04 / TRD-05)

Source of the defect: `docs/audit_pipeline_2026-09-13/AUDIT_DATA.md` TRD-01 (bb8a2806). After a Binance perpetual stops trading, the archive keeps writing 5m rows with zero trades and one frozen close, and funding archives keep settlement records. Every research eligibility rule reads such a contract as live. This spec fixes one definition that every research rule uses. It was written before any probe or replay number of this fix program was seen. Numbers already seen: the AUDIT_DATA counts quoted in the audit (156 contracts, 13,770,575 rows, 60,438 funding events, the per-year base / member / A0 exposure shares). They motivate the fix. They were not used to choose any parameter below.

## 1. Row-level fact (5m)

- **Source.** Channel `log_cnt` (= log1p(number_of_trades), clipped to [0, 20], float16) of the canonical 5m cache `/workspace/data/dlnative_5m_wide829_f16_holefix2.npz` (rows to 2026-09-01T00:00Z). Rows after that come from its extension `dlnative_5m_wide829_f16_holefix2_x0910.npz` (to 2026-09-11T00:00Z). A bar is labelled by its close time (`ts = open_time + 5 min`). Holes were filled from the official daily archives with the same channel math (`holefix2_daily.py`), so filled bars carry true trade counts.
- **States of a bar (s, t):** `TRADED` ⇔ log_cnt finite and > 0 · `UNTRADED` ⇔ log_cnt == 0 exactly · `NODATA` ⇔ log_cnt NaN.
- `ret5` is **not** part of the definition. The first bar of a listing, or the first bar after a gap, has a NaN return but real trades.
- **Preconditions** (refuse to build otherwise):
  - (a) both caches share the symbol axis;
  - (b) the x0910 prefix equals holefix2 bitwise on `log_cnt`, over holefix2's rows;
  - (c) the ts grid is strictly increasing with 300 s spacing, or every gap is listed and counted;
  - (d) there is no log_cnt value strictly between 0 and log1p(1) = 0.693 (that would mean a fractional count).

## 2. As-of tradability at a decision time (the flag every rule uses)

- **Definition.** `tradable(A, s)` ⇔ at least one `TRADED` bar of s with close time in **(A − W, A]**. `W = 24 h` (288 bars) is **primary**.
- **Anchor state:**
  - `TRADABLE` ⇔ ≥ 1 TRADED bar in the window;
  - `UNTRADED` ⇔ no TRADED bar, but ≥ 1 UNTRADED bar;
  - `NODATA` ⇔ every bar in the window is NaN.
- **Eligible ⇔ TRADABLE.** `NODATA` is never treated as tradable. It is counted separately in every receipt.
- **Causality.** Only bars closing at or before A are read. Research replays decide at A, and production reads at A + 23 min, so the flag is causal for both.
- **Refusals.** A decision time later than the last bar of the loaded cache raises; there is no carry-forward. A window that starts before the cache start is computed on the bars that exist and flagged `window_truncated`. That only applies to times before 2022-01-02T00:00Z, earlier than every research anchor axis.
- **Lag, declared.** A contract that dies at D stays `TRADABLE` for decision times in (D, D + 24 h]: at most 6 anchors. Those name-anchors are counted and reported, not hidden.
- **Why 24 h is primary** (reasons fixed before any number):
  - (i) It is the causal rule AUDIT_DATA recommends.
  - (ii) It is the same window P2 already uses for its TRADING proxy, so the two stay comparable.
  - (iii) It is robust to exchange-wide maintenance halts and to thin names with multi-hour gaps. A short window would drop live names that production's exchangeInfo TRADING base keeps.
  - (iv) Its worst-case lag is bounded and visible.
- **Sensitivity.** `W = 4 h` (48 bars) is reported beside every primary number. It never sets a label.

## 3. 5m granularity

`tradable5m(t, s)` ⇔ at least one TRADED bar in rows [t − 287, t] (the same window as §2 evaluated at every bar close). The anchor flag equals `tradable5m` sampled at the anchor row. Receipts assert this equality on every axis they write.

## 4. Descriptive only (never used in any decision)

- `last_traded_ts[s]`: close time of the last TRADED bar in the loaded cache.
- `dead_after(t, s)` ⇔ t > last_traded_ts[s] and last_traded_ts[s] < cache_end − 24 h. The last trade must be more than 24 h before the cache end; otherwise the state is `CENSORED`.

These use the future (whether the name ever trades again). They exist only to count contamination and to pick red-test fixtures.

## 5. Funding records

A settlement record of s at time ft is **payable** only if `tradable(ft, s)` under §2. Records that fail the test are kept in the data but flagged `not_payable`. No research rule may book carry on them or rank them in a fund base.

## 6. Where research rules use it (fix sites; each row's legacy code is cited in FACT_TABLE_DATA.md)

| Rule | Legacy | Fixed |
|---|---|---|
| Replay universe (w10 `UMASK_SCOPE=m1`) | finite qvk ∩ U-PIT/CRYPTO row | finite qvk ∩ U-PIT/CRYPTO row ∩ tradable(A) |
| Fund leg rank base (w10 `FZB`) | every finite f_fund_ema_v1 on the panel row | finite f_fund_ema_v1 ∩ tradable(A) |
| Replay trade set `sel` | ⊂ universe | ⊂ fixed universe (inherits) |
| P2 base proxy (`p2_prep_inputs.py` TR24) | ≥ 1 settlement in (A − 24 h, A] | owner P2 decides consumption; FX-DATA hands over tradable(A) and the per-anchor difference |
| State-variable member sets (T1 / T8 / r12 / r19) | finite qvk ∩ m1 row | finite qvk ∩ m1 row ∩ tradable(A) |
| King / DL training member screens (TRD-05) | coverage + vol + finite forward return | owner FX-MODEL; FX-DATA provides the flag on the king-meta and dlw axes |
| U-PIT monthly row (UNI-03 neighbour) | listed ≥ 30 d and vol30 > 0 | unchanged monthly rule; tradable(A) is applied per anchor on top, never folded into the monthly row |

Positions held in a name at the first anchor where it is no longer tradable leave the member set. The replay device then books no price, carry or cost on them. That was already its treatment of names leaving the universe, and it is unchanged. The residual gross outside the member set on non-tradable names is measured and reported.

## 7. Effect measurement on A0 (frozen before any number)

- **Device.** `/workspace/uplift_2026-09-11/w10_sleeve.py` sha b88e35a4, **unmodified**. The A0 recipe is copied verbatim from `r3k_reprice3.py` BOOK + `FSEED` / `FPRED=f10_A0_s{seed}` + `COSTB_JSON=costb_PWR_G230k.json`. Seeds are 42 and 2027. `CAL=log`.
- **Arms.** Only the eligibility artifacts are injected; everything else is identical:
  - `C0`: A0 as is. **Positive control:** rec and W equal `r3k/arms/A0_PWR230k_s{seed}.npz` bitwise, or the run stops.
  - `TU`: `UMASK_NPZ` = U-PIT/CRYPTO ∧ tradable24h. Universe and trade set only.
  - `TB`: `FEMAT_NPZ` = f_fund_ema_v1 with non-tradable cells set to NaN. Fund rank base only.
  - `TF`: both. **This is the fixed book.**
  - `TF4`: both with W = 4 h. Sensitivity; never sets a label.
- **Statistic.** The r18_judge estimator, verbatim:
  - g = net_ex / gross_total (bps / 4h anchor / unit gross); paired Δg = g_arm − g_C0 per anchor.
  - UTC-day block bootstrap, 2000 draws, `default_rng([20260905, k])`, CI95.
  - Windows: W_ALPHA (primary, n = 9138), W_FULL (n = 10038), KING_LIVE (2024+, n = 5838).
  - Components (Δprice / Δcarry / Δcost) and per-year rows are reported.
- **Label.** `multi_asset/exports/research/common/equivalence_labels.py`, frozen δ table `DELTA_TABLE_K2.json` sha ad6af207, key **D1: δ = 0.05 bps / anchor / unit gross**, two-sided TOST on each seed's CI95. The label is `aggregate` over both seeds. Sensitivity columns δ ∈ {0.02, 0.25} never set the label.
- **Reading.** The TF label states whether A0-based readings move beyond δ when dead contracts are removed:
  - `EQUIVALENT` ⇒ TRD-03 is closed with receipts.
  - `NOT EQUIVALENT` or `INCONCLUSIVE` ⇒ the A0 reference is registered for re-basing by the lead. No research RESULT is edited by FX-DATA.
- **Also reported:**
  - dead (`dead_after`) and lag (tradable but dead) name-anchors that remain in the fixed universe;
  - |W| outside the member set on non-tradable names;
  - fund base size change per year.

## 8. What this spec does not decide

- It does not choose between the A0 and A1x references (OOF-01, owner P2).
- It does not define the exit price of a delisted contract. The data do not contain it; L4b measured it for one sleeve.
- It does not change any training member list (FX-MODEL), any P2 file (p2-oos-replay), or any existing artifact. All outputs are new files beside the old ones.
