> **创建:** 2026-09-13 14:3xZ | **Session:** https://claude.ai/code/session_01BzpuBRGZh8oPvpD8NgqsME (auditor teammate aud-data, read-only) | **状态:** 审计登记册(只读; 未改任何数据) | **作废条件:** 任一登记数据件 sha 变化(见 §0), 或任一登记项被修复/裁定后需差异复核

# AUDIT_DATA — data lineage and calibers for research, evaluation and retraining

Companion data: `AUDIT_DATA.json` (same items, same wording, plus the full inventory and dependency matrix). Every number below is rendered from the device receipts in `devices_data/receipts/` by `devices_data/build_audit_data.py`.

## 0. What was audited, frozen at what

| Object | Value |
|---|---|
| Research repo branch | `research/book-uplift-2026-09-11`; consumer scan at `deb8a47bb5` over 1067 devices committed since 2026-09-09 |
| Devices (committed before each run) | `feb7747e` ad_inventory / ad_funding_iv / ad_cache_members / ad_panel_holes / ad_consumers_scan; `deb8a47b` ad_batch2 (+ scan v2); `36633520` ad_batch3; `60461e1a` ad_tradability |
| Receipts | `AD_A_inventory.json` self 191d4a36; `AD_B_funding_iv.json` self f6d58b2b; `AD_C_cache_members.json` self 0e8bc8fd; `AD_D_panel_holes.json` self a62a9d48; `AD_E_consumers_matrix.json` self e6d9a686; `AD_F_batch2.json` self 941ba723; `AD_G_batch3.json` self f1e9b714; `AD_H_tradability.json` self 4c065c17 — each equals its committed device |
| Canonical cache | `dlnative_5m_wide829_f16_holefix2.npz` sha 1d7f459dee434ec4, 2022-01-01 → 2026-09-01T00:00 |
| Accounting meta | `meta_newprod_v4.npz` sha 0e3c09ac86c727ac; x0910 a8eb359701c71acf |
| Replay panel | `wide_panel_4h_v2ext.npz` sha 5e67c0559daa904d; splice c5d10f6ae31fa3f9; v1 canonical f14bc33d78b24929 |
| Audit clock | pod2 receipts written D 13:17:43Z, A 13:18:15Z, B 13:20:56Z, C 13:21:35Z, F 13:25:23Z, G 13:33:23Z (all rc=0 before the 13:34Z session stop, none repeated), H 14:12:20Z; P2 S2 running throughout |

Constraints kept: every dataset opened read-only (np.load / zipfile streaming); no dataset written, moved or rewritten; pod2 CPU only, nice 19, env -i with OMP=1; at most 6 worker processes; no GPU; PIDs 333197/339489 and P2 S2 processes untouched; no exchange or venue API call; no network download; hashes guarded (bytes read == st_size); every device committed before it ran; every receipt's self_sha256 equals the committed device.

Status legend: **FIXED_DEPLOYED** = fixed in the data or code that current consumers read; **VERIFIED_IMMATERIAL** = checked; no effect on the named layers (resolution given); **OPEN_MEASURED_MATERIAL** = defect confirmed with numbers; real effect on the named layer, even if small; **OPEN_NOT_MEASURED** = mechanism confirmed, size of effect not measured; **PENDING_USER_DECISION** = needs a user ruling; **DOC_STALE** = data and code are right, a document or memory note is wrong.

## 1. Result

**No P0 found. 3 P1 items.** All three are data facts that current evaluation and the October retrain inherit without any gate or register entry:

| ID | Title | Status | Why P1 |
|---|---|---|---|
| TRD-01 | Dead perpetuals keep writing untraded rows with a frozen close and keep funding records; every eligibility rule in research reads them as live | OPEN_MEASURED_MATERIAL | A verified, systematic defect with no guard anywhere in research: dead contracts enter universes, rank bases and statistics with zero returns and phantom funding; it already decided one research verdict (L4) and sits directly under the next ones (L3 delisting events, carry sleeves). |
| FEA-01 | DL training features carry funding only for the 450 names of the 2026-08 live list; for every other name the funding inputs are 0.0 back to 2022, and that flag carries forward-return information | OPEN_NOT_MEASURED | A future-derived availability flag sits in the training inputs of a live model leg and of every F10 out-of-fold series used to judge candidates; the October retrain would re-bake it, and no document records it as a defect. |
| TIM-01 | King training uses windows ending one bar before the anchor and labels starting one bar before it; the live producer serves windows that include the anchor bar; the October chain rebuilds the same way and no register carries it | OPEN_MEASURED_MATERIAL | A measured train/serve skew in a live model leg (7-22% of the top decile changes), with a ready fix blocked by a low-resolution guard, silently re-baked by the next retrain because it fell out of every register. |

| Status | Count |
|---|---:|
| FIXED_DEPLOYED | 2 |
| VERIFIED_IMMATERIAL | 13 |
| OPEN_MEASURED_MATERIAL | 5 |
| OPEN_NOT_MEASURED | 8 |
| PENDING_USER_DECISION | 0 |
| DOC_STALE | 1 |
| **Total** | **29** |

By severity: P0 0, P1 3, P2 9, P3 17.

## 2. Short answers to the audit questions

1. **Inventory.** Current devices read one canonical 5m cache (holefix2) plus its September extension, the pre-fix `_ext` cache only for axes/alignment, two raw-return patches, the v1/v2ext/v3splice panels and their x0910 extensions, the v4 king feature/meta pair, the v4 accounting meta, three DL target sets, fea82/fea89/legs, four OOF families, the CRYPTO mask, two funding pulls, the zip archive and P2's ledger. Paths, shas, builders, axes and consumers are in §6 and the JSON inventory; builders on pod2 equal git (LIN-03) except the x0910 builders, which are only on pod2 (LIN-01).
2. **Known defects per dataset.** (a) Return caliber: accounting returns are RAW and every clipped bar through 2026-09-11 is patched (RET-01); king labels stay clipped sums over an early window (LBL-01); some diagnostics still recompute returns from the clipped channel (RET-02). (b) Funding interval: the x0910 builder is located and reproduced exactly (FND-01); the canonical panels match settlement truth, but the spacing rule mislabels switch rows in API-only months (FND-02); the v1 prefix has 138 wrong cells (FND-03). (c) Timestamps: close-time labelling is consistent (TIM-03), the king clock is not (TIM-01), the metrics switch is handled (TIM-02). (d) Universe: tokenized stocks are 7.3% of 2026 training members (UNI-01); the September mask is carried forward (UNI-03). (e) Forward masks: the predicate removes almost nothing and the OOF arrays carry it exactly (FWD-01, FWD-02). (f) Survivorship: the axis keeps delisted names (UNI-02); the DL funding inputs exist only for the 2026-08 live list (FEA-01).
3. **Tradability by trades (L4b lesson).** No research layer defines tradability by trades. 156 dead contracts write 13.8M frozen rows with return exactly 0 in the canonical cache and 60 of them keep funding records; universes, rank bases and statistics admit them (TRD-01..05). On A0 the held exposure is at most 4.9e-04 of gross; the fund rank base carries 0.7-5.3% dead names (yearly mean); member sets carry 0.2-1.5%.
4. **Dependent results.** Each item lists its dependents. Only two dependent readings were re-run after their defect was found: T5c as T5d for FND-01 (not yet re-run by the lead) and L4 as L4b for TRD-01. Nothing else has been re-run.
5. **October chain.** See §4: of 15 checked defects, 9 would be carried into the next retrain as the chain stands, 3 conditionally, and 3 not.
6. **Inputs folded in.** AUDIT_TRAIN TRN-02: data side confirmed clean through 2026-09-11 00:00Z, nothing later exists (RET-01). AUDIT_EXEC LED-04: research readers of the daily_nav fee split listed; no conclusion depends on them (LED-01).

## 3. Register

| ID | Layer | Title | Status | Sev | Affects |
|---|---|---|---|---|---|
| TRD-01 | data layer / tradability definition (all panels, caches, metas, masks) | Dead perpetuals keep writing untraded rows with a frozen close and keep funding records; every eligibility rule in research reads them as live | OPEN_MEASURED_MATERIAL | P1 | future_eval, future_retrain, reporting |
| FEA-01 | DL training features / funding columns (fea82 via wide_panel_4h_v3splice) | DL training features carry funding only for the 450 names of the 2026-08 live list; for every other name the funding inputs are 0.0 back to 2022, and that flag carries forward-return information | OPEN_NOT_MEASURED | P1 | live_trading, future_eval, future_retrain |
| TIM-01 | king features and labels / clock (train vs serve) | King training uses windows ending one bar before the anchor and labels starting one bar before it; the live producer serves windows that include the anchor bar; the October chain rebuilds the same way and no register carries it | OPEN_MEASURED_MATERIAL | P1 | live_trading, future_retrain, future_eval |
| TRD-02 | fund leg rank base (replay FZB and P2 base proxy) | The fund leg's rank base in research includes dead contracts that still have funding records; production's base (exchangeInfo TRADING) does not | OPEN_NOT_MEASURED | P2 | future_eval |
| TRD-04 | state variables and member-set statistics | Cross-sectional statistics over 'finite qvk ∩ CRYPTO mask' include dead contracts with zero returns and phantom funding | OPEN_NOT_MEASURED | P2 | future_eval, reporting |
| FND-01 | 4h panel / x0910 funding tail | x0910 panels apply one pull-time settlement interval to every September API row of a symbol (builder located and reproduced) | OPEN_MEASURED_MATERIAL | P2 | future_eval, reporting |
| FND-02 | funding source (fund_aug) / interval rule for API rows | API funding rows get their interval from settlement spacing; the canonical panels match that rule exactly, but spacing mislabels switch rows and nobody has measured them in the research panels | OPEN_NOT_MEASURED | P2 | future_eval, future_retrain |
| HOL-01 | 4h panels / hole residuals | The panels every replay and the v4 chain read were built on the pre-holefix cache and still carry the filled holes in their kline columns | OPEN_NOT_MEASURED | P2 | future_eval, future_retrain |
| UNI-01 | universe / training member sets | Tokenized stock and commodity perps are 7.3% of 2026 training member pairs; evaluation masks them, training does not | OPEN_NOT_MEASURED | P2 | future_retrain, live_trading |
| OOF-01 | OOF predictions / reference book coverage | Replay model legs exist only from 2023 (F10) and 2024 (king), and A0's legs are on v3-lineage member lists; full-history numbers are not the in-service book | OPEN_MEASURED_MATERIAL | P2 | future_eval, reporting |
| LIN-01 | lineage hygiene / x0910 builders | The x0910 extension builders exist only on pod2, while committed devices consume their products | OPEN_MEASURED_MATERIAL | P2 | reporting, future_eval |
| DOC-01 | docs and memory | Caliber documents and memory notes miss or misstate several data-lineage facts | DOC_STALE | P2 | reporting, future_retrain |
| TRD-03 | replay book (A0) / positions in dead contracts | A0 holds dead contracts in the days right after their last trade, books a 0 return on them and charges carry from records that were not paid; the size is small | VERIFIED_IMMATERIAL | P3 | future_eval |
| TRD-05 | training rows (king meta, DL targets) | King and DL training members include dead contracts with labels exactly 0 in the first days after death | VERIFIED_IMMATERIAL | P3 | future_retrain |
| RET-01 | accounting returns / clip patch (data-side TRN-02 check) | Every clipped bar in the research caches through 2026-09-11 00:00Z has a patch entry; no research cache or panel exists after that | FIXED_DEPLOYED | P3 | future_eval |
| RET-02 | devices / returns recomputed from the clipped cache channel | Several devices written after the 09-12 rule still compound or sum returns from the clipped ret5 channel | OPEN_NOT_MEASURED | P3 | future_eval |
| LBL-01 | king labels | King labels are ranks of the clipped 5m sum over rows [E, E+47]; the export guard books P&L on the same label | VERIFIED_IMMATERIAL | P3 | future_retrain |
| FWD-01 | member screens / OOF availability (D20, E-0908-C) | The forward-return member predicate removes almost nothing, because dead contracts keep finite frozen returns; king and F10 OOF carry the same mask | VERIFIED_IMMATERIAL | P3 | future_eval, future_retrain |
| FWD-02 | replay accounting / non-finite forward returns | The replay exits positions whose next accounting return is non-finite and books 0 for them; 13 pairs in the whole A0 history | VERIFIED_IMMATERIAL | P3 | future_eval |
| FND-03 | v1 canonical panel / API tail intervals | The v1 canonical panel's August 2026 API tail stored one interval per symbol; 138 cells for five names, the same rows as the 08-16 bundle seed | VERIFIED_IMMATERIAL | P3 | future_retrain |
| UNI-02 | universe / symbol axis | The 829-name axis is an S3 listing from 2026-08-21 that keeps delisted names; it is frozen at that date | VERIFIED_IMMATERIAL | P3 | future_eval |
| TIM-02 | metrics archive label switch (2024-03-04) | Only L2 reads the metrics archive and it applies the label regime by date | VERIFIED_IMMATERIAL | P3 | future_eval |
| TIM-03 | 5m cache timestamps | The cache labels bars by close time; panel features end one bar before the anchor, DL features include the anchor bar | VERIFIED_IMMATERIAL | P3 | future_eval |
| HOL-02 | 5m cache / holes | Cache holes E-0908-D and E-0909-B are filled in holefix2 and in its extension | FIXED_DEPLOYED | P3 | future_eval, future_retrain |
| LIN-02 | lineage / write incident | A 09-12 test run rewrote dlw_v4raw/data/dlw_targets.npz on pod2; the bytes are identical | VERIFIED_IMMATERIAL | P3 | reporting |
| LIN-03 | lineage / builder identity | Builder copies on pod2 match git; all audit receipts are bound to the committed devices | VERIFIED_IMMATERIAL | P3 | reporting |
| EVL-01 | replay device default | w10 sleeve devices still default CAL to 'simple' (expm1 on an already simple return); every committed run since 09-09 sets CAL=log | VERIFIED_IMMATERIAL | P3 | future_eval |
| LED-01 | research readers of daily_nav (AUDIT_EXEC LED-04) | Research tools that read daily_nav.realised_by_type COMMISSION/REALIZED_PNL inside 07-29..09-12 print wrong fee columns; their conclusions do not use them | VERIFIED_IMMATERIAL | P3 | reporting |
| UNI-03 | universe mask frontier | September anchors use the last August mask row carried forward | OPEN_NOT_MEASURED | P3 | future_eval |

### TRD-01 — Dead perpetuals keep writing untraded rows with a frozen close and keep funding records; every eligibility rule in research reads them as live

- **Layer:** data layer / tradability definition (all panels, caches, metas, masks)
- **What is wrong or unverified:** No research panel, cache, meta, mask or replay defines tradability by trades. After a perp stops trading the archive keeps writing 5m rows with zero trades and one frozen close; in the canonical 5m cache 156 contracts stopped trading inside the cache and still carry 13,770,575 such rows, every one with ret5 exactly 0, log_qv exactly 0 and cpos/tbf NaN (129 of them still write frozen rows through the x0910 tail to 2026-09-11). Per year: 140,532 / 685,399 / 1,420,707 / 4,298,273 / 7,225,664 rows over 11 / 8 / 38 / 71 / 131 symbols (2022..2026). Zero-trade runs of 24 h or longer: 158, of which 147 never resume. The eligibility rules all pass such rows: panel elig and king/DL member screens use the share of finite ret5 bars (coverage) plus 7-day volatility and a finite forward return (a frozen close gives a finite 0); the replay universe is 'finite qvk' (the 7-day mean of log1p(quote volume), which is a finite 0 on frozen rows) intersected with U-PIT, whose monthly rule keeps any name with positive 30-day volume, i.e. up to about two months after death; the replay trade set uses a 7-day log-volume mean that decays only gradually after the stop (TRD-03 counts the dead pairs it still admits); P2 uses 'a settlement in the last 24 h' as its TRADING proxy. Funding archives keep records for dead contracts: 60 of the 156 dead contracts have 60,438 settlement events after their last trade (zips 58,509, fund_aug 60,188, r6 September pull 328), e.g. RAYUSDT last trade 2022-11-15, funding until 2025-06-19. My own survivorship reading C2 (28 names with last finite bar before 2026-08-01) was fooled by the same rows; by trades the number is 156. The book-level size on A0 is small (TRD-03) and the rank-base and statistics contamination is systematic (TRD-02, TRD-04); L4 already had its verdict decided by this failure (L4b).
- **Evidence:**
  - `retrain_2026-09/pod_merge_cache_ext.py:24,27-32 (git HEAD; = pod2 /workspace copy de7a0661)` — k['ts'] = pd.to_datetime(k.open_time...) + pd.Timedelta('5min') ... A[:,0] = np.clip(k.c.pct_change(fill_method=None), -0.3, 0.3) ... A[:,4] = np.log1p(k.cnt).clip(0, 20)
  - `devices_data/receipts/AD_H_tradability.json H1_cache (ad_tradability.py 4c065c17, commit 60461e1a before run)` — {"post_death_untraded_rows": 13770575, "ret5_exactly_0": 13770575, "log_qv_exactly_0": 13770575, "cpos_nan": 13770575, "tbf_nan": 13770575}; top: SCUSDT last trade 2022-06-17T09:00Z (1536.6 d frozen), FTTUSDT last trade 2022-11-14T04:05Z (1386.8 d frozen), RAYUSDT last trade 2022-11-15T04:05Z (1385.8 d frozen), STRAXUSDT last trade 2024-03-15T09:00Z (899.6 d frozen), DGBUSDT last trade 2024-04-01T09:05Z (882.6 d frozen), SNTUSDT last trade 2024-05-13T09:00Z (840.6 d frozen)
  - `AD_H_tradability.json H1_x0910_tail` — {"tail_rows": 2880, "symbols_dead_before_2026-09-01_still_writing_untraded_rows": 129, "untraded_rows_of_those": 371520, "ret5_exactly_0_of_those": 371520}
  - `retrain_2026-09/pod_panel_ext.py:40; v4_chain_2026-09-09/pod_fea_ext_clamp.py:37; pod_dlw_targets_raw.py:107` — elig = (covr >= 0.95) & (v7 >= 1e-4) | ok = (covr[i] >= 0.95) & (v7[i] >= 1e-4) & np.isfinite(y4[i]) | ok = (covr[i] >= 0.95) & (vstd[i] >= 1e-4) & np.isfinite(y4s[i])
  - `uplift_2026-09-11/r18_foundation/devices/w10_sleeve_r18.py:81,244,267 (A0 config MEMBERS_TOPN=829)` — _mem2[_i] = np.sort(_ord[:MEMBERS_TOPN]) (all finite qvk) ... ok = ... np.isfinite(y4[i, m]); qv4h = np.expm1(np.clip(qvk[i, m], 0, 30)) * 48 ... _nonsel[m[~sel]] = True
  - `retrain_2026-09/health_check_2026-09-05/build_umask.py:46 (U-PIT, monthly refresh)` — elig = has & (age >= 30) & (vol30 > 0)
  - `docs/PREREG_producer_parity_phase2_oos_2026-09-12.md:75 (P2 D3)` — exchangeInfo 历史不可得 ⇒ (A−24h, A] 有结算的名作 TRADING 代理
  - `AD_H_tradability.json H5_funding_after_death` — {"events": 60438, "zip": 58509, "aug": 60188, "sep": 328}; RAYUSDT 3414 events after last trade 2022-11-15 (last 2025-06-19), SCUSDT 3294 events after last trade 2022-06-17 (last 2025-06-19), FTTUSDT 2845 events after last trade 2022-11-14 (last 2025-06-19), STRAXUSDT 2766 events after last trade 2024-03-15 (last 2025-06-19), SNTUSDT 2412 events after last trade 2024-05-13 (last 2025-06-19)
  - `uplift_r3_2026-09-13/L4b/RESULT_L4b.md:46-47 (commit 30dc6eb2)` — After a perp stops trading, the archive keeps writing untraded 1m rows with one frozen close ... fund_aug keeps recording funding for some stopped perps (MDT 1,197 events ...)
  - `AD_C_cache_members.json C2_axis_survivorship (my earlier close-based reading)` — last_bar_before_2026-08-01_n 28 vs AD_H symbols_dead_inside_cache 156
- **Status:** OPEN_MEASURED_MATERIAL
- **Affects:** future_eval, future_retrain, reporting
- **Severity:** P1 — A verified, systematic defect with no guard anywhere in research: dead contracts enter universes, rank bases and statistics with zero returns and phantom funding; it already decided one research verdict (L4) and sits directly under the next ones (L3 delisting events, carry sleeves).
- **Recommended action:** Add a trades-based flag to the data layer (for each name and 5m row: traded = number_of_trades > 0 from log_cnt; untradable_since = first row after the last trade) and a causal version for decisions (no trade in the trailing 24 h). Apply it to U-PIT, the replay universe and trade set, the fund rank base, P2's base proxy, the king/DL member screens and state-variable member sets; set post-death returns to NaN, not 0, and treat funding records after the last trade as not paid. Re-run A0/NW and P2 S2 once, paired, to size the change.
- **Dependents (re-run status):** uplift_r3 L4 carry sleeve (corrected by L4b); P2 S2 historical replay (running; base proxy = settlement presence); every w10_sleeve arm with MEMBERS_TOPN=829 / UMASK m1 (A0, NW, C0, T1 C0, T2, T5, T5c); T1 H3 / T8 state variables over finite-qvk ∩ m1; r12 / r19 sig_fund and dispersion labels; my own C2 survivorship reading (corrected here)
- **Method:** VERIFIED

### FEA-01 — DL training features carry funding only for the 450 names of the 2026-08 live list; for every other name the funding inputs are 0.0 back to 2022, and that flag carries forward-return information

- **Layer:** DL training features / funding columns (fea82 via wide_panel_4h_v3splice)
- **What is wrong or unverified:** The DL feature builder takes fund_ema and fund_now from the splice panel (F171_PANEL = PANEL_SPLICE in the chain) and writes nan_to_num(value, 0.0). The splice panel's prefix up to 2026-08-15 is the v1 canonical panel, whose funding covers exactly the 450 symbols of live_pins symbols_live (identical sets), while the 829-name panel the replay reads has funding for 825. So among DL member pairs that do have funding in the 829-name panel, the training feature is 0.0 on 34.2% / 34.0% / 33.6% / 24.7% / 13.9% of pairs (2022..2026). Membership of a 2026-08 list is future information for 2022-2025 rows. The flag 'funding feature present' is informative about the next 4 h: restricted to pairs with real funding, the demeaned forward return of flagged minus unflagged names is +0.77 / +0.46 / +1.07 / +2.78 / +3.19 bps per 4 h (naive t 0.9 / 0.7 / 1.8 / 3.3 / 1.8; autocorrelated, descriptive). The in-service F10 (dlw_ext / f8_ext, built from the same splice), the v4 F10 and every F10 OOF used in replays (f10_A0, f10_v4RAW, P2's injection) were trained on this. Production scores only live names; how its own funding inputs are filled is a production-path question (T4b found historical-anchor fund rows back-filled with 0; AUDIT_PROD), so train and serve distributions of these two columns differ in an unmeasured way. The October template keeps PANEL_SPLICE, so the zero prefix persists. The size of the effect on F10 predictions and books was not measured.
- **Evidence:**
  - `retrain_2026-09/pod_dlw_features_ext.py:73,94` — FUND = [PW["f_fund_ema"]..., PW["f_fund_now"]...] ... X[sl, col] = 0.0 if j is None else np.nan_to_num(fv[j, m], nan=0.0)
  - `pod2 dlw_ext/results/dlw_features_report.json and dlw_v4raw/results/dlw_features_report.json (read-only)` — panel_sha256 c5d10f6ae31fa3f9... (= wide_panel_4h_v3splice.npz) in both; cache 72eb7849 (in-service, _ext) and 1d7f459d (v4, holefix2)
  - `retrain_2026-09/v4_chain_2026-09-09/chain_v4_monthly.sh:139` — env -i ... F171_CACHE=$CACHE F171_PANEL=$PANEL_SPLICE F171_OUT=$DLW_CLIP "$PY" "$BUILDER_FEA82"
  - `retrain_2026-09/pod_panel_splice.py:11-12 (CAN = v1 canonical, EXT = v2ext)` — CAN = np.load("/workspace/data/wide_panel_4h_v1.npz") ... EXT = np.load("/workspace/data/wide_panel_4h_v2ext.npz")
  - `devices_data/receipts/AD_G_batch3.json G1 (ad_batch3.py f1e9b714, commit 36633520 before run)` — {"v1_funding_symbols": 450, "live_pins_symbols": 450, "identical": true, "in_v1_not_live": [], "live_not_in_v1": []}
  - `AD_F_batch2.json F1 (ad_batch2.py 941ba723, commit deb8a47b)` — v1_symbols_with_any_finite_f_fund_ema 450; v2ext 825; f_fund_ema finite in v2ext but NaN in v3splice by year: 104,374 / 160,652 / 245,209 / 316,990 / 202,688
  - `AD_F_batch2.json F2 (dlw_v4raw dlw_fea82.npz 40608701, 2,753,289 member pairs)` — 2022: 97,546 of 285,622 pairs zero while v2ext finite; 2023: 139,361 of 410,358 pairs zero while v2ext finite; 2024: 202,279 of 601,406 pairs zero while v2ext finite; 2025: 210,066 of 849,811 pairs zero while v2ext finite; 2026: 80,970 of 581,200 pairs zero while v2ext finite
  - `AD_G_batch3.json G2` — 2022: anchors 2010, gap +0.77 bps (t 0.9), spearman -0.0031; 2023: anchors 2190, gap +0.46 bps (t 0.7), spearman +0.0018; 2024: anchors 2196, gap +1.07 bps (t 1.8), spearman -0.0041; 2025: anchors 2190, gap +2.78 bps (t 3.3), spearman +0.0059; 2026: anchors 1357, gap +3.19 bps (t 1.8), spearman -0.0079
  - `retrain_2026-09/second_instrument_rebuild_2026-09-05/REPORT.md:59` — the 08-21 instrument (v1 = wide_panel_4h_hist_v2.npz) used 450-symbol funding coverage ... The two instrument families therefore differed in funding coverage
  - `v4_chain_2026-09-09/v4_month_2026-10.env.template:10` — PANEL_SPLICE=/workspace/data/TODO_wide_panel_4h_v3splice_2026-10.npz
- **Status:** OPEN_NOT_MEASURED
- **Affects:** live_trading, future_eval, future_retrain
- **Severity:** P1 — A future-derived availability flag sits in the training inputs of a live model leg and of every F10 out-of-fold series used to judge candidates; the October retrain would re-bake it, and no document records it as a defect.
- **Recommended action:** Rebuild fea82 funding columns from the 829-name panel (or from the settlement stream with the declared interval) and keep NaN semantics explicit (a separate availability bit built from trades, TRD-01); measure on one monthly fold pair (current vs rebuilt features, same seed and recipe) the F10 OOF IC and the A1 book difference before October; until then label F10 OOF readings as carrying this flag.
- **Dependents (re-run status):** in-service F10 f10_live_s42_np (dlw_ext / f8_ext); RESULT_v4_chain_retrain_quantify_2026-09-09 (A1 vs A0, both affected); every replay F10 leg: f10_A0_s*, f10_v4RAW_s*; P2 F10 OOF injection (D2); none re-run
- **Method:** VERIFIED

### TIM-01 — King training uses windows ending one bar before the anchor and labels starting one bar before it; the live producer serves windows that include the anchor bar; the October chain rebuilds the same way and no register carries it

- **Layer:** king features and labels / clock (train vs serve)
- **What is wrong or unverified:** pod_fea_ext_clamp.py builds every window as rows [E-w, E-1] and the label as the sum over rows [E, E+47]; shadow_loop_v3.py serves rows [ai+1-w, ai] where ai is the bar closing at the anchor; the accounting return is rows [E+1, E+48]. E-0909-F measured the skew on six anchors: prediction Spearman 0.976-0.990 between the training clock and the serving clock, top-decile overlap 78-93%, largest |Δpred| 1.2-1.9 times the score's sd. The clock-aligned builder (v4e) passed its parity gate but failed the export guard by rule (Sharpe 2.260 < 2.27, a guard whose sampling error is about ±0.6); book-level readings were (C). The in-service booster and the v4 candidate both carry the skew; the October chain calls pod_fea_ext_clamp.py again. RUNBOOK_2026-10, CALIBER_STATUS and FIXPROGRAM do not list it.
- **Evidence:**
  - `~/wide_shadow/shadow_loop_v3.py:280,285-286,356,358 (sha256 e9c98374...)` — "endTime": anchor * 1000 - 1 ... close_s = (int(k[0]) + 300000) // 1000 ... if close_s > anchor ... ai = row_of[anchor] ... seg = CDf[max(ai + 1 - w, 0):ai + 1, :, ch]
  - `v4_chain_2026-09-09/pod_fea_ext_clamp.py:33-34,48,51 (sha b9f9c728, = pod2 review_scratch copy)` — y4 = (CS["ret5"][0][E + 48] - CS["ret5"][0][E]) ... Ew = np.maximum(E - w, 0) ... VAL.append(((s_[E] - s_[Ew])))
  - `devices_data/receipts/AD_C_cache_members.json C3_positive_control.king` — member lists unequal 0; y4 maxabs vs Σ rows [E, E+47] = 0.0
  - `docs/HANDOFF_round2_b0a573a1_closure_2026-09-09.md:40,42,68` — 离线特征窗 [E−w, E−1] vs 生产 [E−w+1, E] ... Spearman 0.976–0.990, 顶十分位重叠 78–93% ... G2 导出门 = FAIL ... 守卫 Sharpe 2.260 < 2.27
  - `v4_chain_2026-09-09/chain_v4_monthly.sh:148` — env -i ... CACHE_IN=$CACHE PANEL_IN=$PANEL_KING FEA_OUT=$KING_FEA META_OUT=$KING_META "$PY" "$D/pod_fea_ext_clamp.py"
  - `grep 'E-0909-F|v4e|king_clock|时钟' RUNBOOK_monthly_retrain_2026-10.md, CALIBER_STATUS_2026-09-09.md, git show HEAD:docs/fixprogram_2026-09-13/FIXPROGRAM_2026-09-13.md` — no entry for the king clock; RUNBOOK mentions v4e only as the export gate file v4e_gate_export_v2.py; FIXPROGRAM's only 时钟 hit is D2 (metrics archive)
- **Status:** OPEN_MEASURED_MATERIAL
- **Affects:** live_trading, future_retrain, future_eval
- **Severity:** P1 — A measured train/serve skew in a live model leg (7-22% of the top decile changes), with a ready fix blocked by a low-resolution guard, silently re-baked by the next retrain because it fell out of every register.
- **Recommended action:** Add E-0909-F to FIXPROGRAM; decide the clock-aligned builder with a CI-based book judge instead of the ±0.6-noise guard band; until decided, state in RUNBOOK_2026-10 that October keeps the old clock.
- **Dependents (re-run status):** in-service king booster 8d79186b; v4 king SLOW_v4 (A1x, P2 king OOF); RESULT_king_clip_label_ablation / guard band 2.27-2.57 (computed on the same early-window label); none re-run
- **Method:** VERIFIED

### TRD-02 — The fund leg's rank base in research includes dead contracts that still have funding records; production's base (exchangeInfo TRADING) does not

- **Layer:** fund leg rank base (replay FZB and P2 base proxy)
- **What is wrong or unverified:** w10 m1 scope ranks each member's funding EMA among every finite value on the panel row; dead contracts with continuing funding records sit in that base. Dead names in the base, mean per anchor 1.4 / 6.5 / 15.8 / 17.5 / 4.3 (max 5 / 8 / 26 / 41 / 10) of a base of 146 / 199 / 296 / 464 / 597 names (2022..2026). P2's settlement-based TRADING proxy has the same contamination: 1.4 / 6.5 / 15.8 / 17.6 / 4.4 dead names per anchor (max 5 / 8 / 26 / 41 / 10). Relative order among live names is unchanged, but rank positions and therefore z levels and demeaned weights shift. Production's base is exchangeInfo TRADING perpetuals plus the pinned live list, so it excludes dead contracts unless they are still pinned. The book-level effect was not measured.
- **Evidence:**
  - `uplift_2026-09-11/r18_foundation/devices/w10_sleeve_r18.py:149` — def FZB(j, m): # ... fund z = rank position of each member among ALL finite fund-EMA values of the 829 base on panel row j
  - `devices_data/receipts/AD_H_tradability.json H3` — {"2022": {"base_mean": 145.96119402985076, "base_DEAD_mean": 1.4432835820895522, "base_DEAD_max": 5, "base_Z24_mean": 3.3049751243781094}, "2023": {"base_mean": 199.00502283105024, "base_DEAD_mean": 6.519178082191781, "base_DEAD_max": 8, "base_Z24_mean": 8.675342465753424}, "2024": {"base_mean": 296.4690346083789, "base_DEAD_mean": 15.824681238615664, "base_DEAD_max": 26, "base_Z24_mean": 17.469945355191257}, "2025": {"base_mean": 464.2365296803653, "base_DEAD_mean": 17.497260273972604, "base_DEAD_max": 41, "base_Z24_mean": 18.110045662100458}, "2026": {"base_mean": 596.7116311080523, "base_DEAD_mean": 4.263592567102546, "base_DEAD_max": 10, "base_Z24_mean": 0.7522367515485203}}
  - `AD_H_tradability.json H5.P2_base_proxy_on_king_axis` — {"2022": {"base_proxy_mean": 145.40130353817506, "base_proxy_DEAD_mean": 1.4003724394785848, "base_proxy_DEAD_max": 5}, "2023": {"base_proxy_mean": 199.0068493150685, "base_proxy_DEAD_mean": 6.519178082191781, "base_proxy_DEAD_max": 8}, "2024": {"base_proxy_mean": 296.4799635701275, "base_proxy_DEAD_mean": 15.835610200364298, "base_proxy_DEAD_max": 26}, "2025": {"base_proxy_mean": 464.3054794520548, "base_proxy_DEAD_mean": 17.561643835616437, "base_proxy_DEAD_max": 41}, "2026": {"base_proxy_mean": 597.0672153635117, "base_proxy_DEAD_mean": 4.3532235939643344, "base_proxy_DEAD_max": 10}}
  - `AD_H_tradability.json H6 fund_now_finite_on_DEAD (v2ext cells)` — 2,901 / 14,277 / 34,751 / 38,319 / 6,195
  - `docs/PREREG_producer_parity_phase2_oos_2026-09-12.md:75` — D3 基名单: exchangeInfo 历史不可得 ⇒ (A−24h, A] 有结算的名作 TRADING 代理
  - `~/wide_shadow/shadow_loop_v3.py:315-317 (e9c98374)` — _b = [x["symbol"] for x in _xi["symbols"] if x.get("contractType") == "PERPETUAL" and x.get("quoteAsset") == "USDT" and x.get("status") == "TRADING"] ... st.base = sorted(set(_b) | set(st.live))
- **Status:** OPEN_NOT_MEASURED
- **Affects:** future_eval
- **Severity:** P2 — Systematic 0.7-5.3% contamination of the rank base (yearly mean) behind the book's dominant leg in every replay and in P2's production-path claim; effect on levels not measured but paired contrasts mostly cancel.
- **Recommended action:** Drop from the base any name with no trade in the trailing 24 h (TRD-01 flag) in w10 FZB and in P2's base proxy; report the paired A0 and P2 differences.
- **Dependents (re-run status):** A0/NW/C0 and all m1-scope arms; P2 S2 (running); none re-run
- **Method:** VERIFIED

### TRD-04 — Cross-sectional statistics over 'finite qvk ∩ CRYPTO mask' include dead contracts with zero returns and phantom funding

- **Layer:** state variables and member-set statistics
- **What is wrong or unverified:** T1 (AMENDMENT 2) and the w10 state instruments define the member set as finite qvk ∩ m1 mask, which is exactly the universe that contains the dead member-anchors counted in TRD-03 (1.30% / 0.19% / 1.19% / 1.20% / 1.48% of pairs per year) and, for funding statistics, the base contamination of TRD-02. Breadth (share of positive returns), return dispersion and funding dispersion (sig_fund) are therefore computed with zero-return rows and stale default funding rates; the direction is toward lower breadth and lower dispersion. Size on T1/T8/r12/r19 readings not measured.
- **Evidence:**
  - `uplift_r2_2026-09-13/T1/PREREG_AMENDMENT_2_T1_2026-09-13.md:9` — 成员集改为 m_k = { n : qvk[k, n] 有限 } ∩ CRYPTO m1 掩码行(= 装置 MEMBERS_TOPN=829 语义
  - `devices_data/receipts/AD_H_tradability.json H2 U_pairs / U_DEAD / U_Z24` — {"2022": {"U_pairs": 283632, "U_DEAD": 3689, "U_Z24": 2150}, "2023": {"U_pairs": 391716, "U_DEAD": 753, "U_Z24": 735}, "2024": {"U_pairs": 583698, "U_DEAD": 6948, "U_Z24": 6568}, "2025": {"U_pairs": 883752, "U_DEAD": 10564, "U_Z24": 11015}, "2026": {"U_pairs": 618259, "U_DEAD": 9165, "U_Z24": 8905}}
  - `uplift_2026-09-11/r19_trackF_reindex/RESULT_r19_trackF_reindex_2026-09-12.md:14` — 更正后 sig_fund 对 ... R6M 臂(meta 成员 ∩ m1, x0910 轴)共同 10039 锚 maxabs 3.78e-6
- **Status:** OPEN_NOT_MEASURED
- **Affects:** future_eval, reporting
- **Severity:** P2 — 0.2-1.5% of member pairs per year are dead; state-conditioned readings (all nulls so far) are unlikely to flip but the bias is one-directional and undocumented.
- **Recommended action:** Recompute the T1/T8 state columns and r19 sig_fund with the trades flag once; if nothing moves beyond resolution, record VERIFIED_IMMATERIAL.
- **Dependents (re-run status):** T1 H3 states; T8 24 state columns; r12 REGIME12 / causal primitives; r19 sig_fund / disp24 labels; none re-run
- **Method:** VERIFIED

### FND-01 — x0910 panels apply one pull-time settlement interval to every September API row of a symbol (builder located and reproduced)

- **Layer:** 4h panel / x0910 funding tail
- **What is wrong or unverified:** r6_fetch_funding.py read fundingIntervalHours from /fapi/v1/fundingInfo once at 2026-09-11 and stored it as intervals; r6_panel_splice.py appends every September row with that value and prefers it to the settlement spacing. Re-deriving the r6 rule reproduces the panel tail exactly (iv cells not reproduced 0, EMA maxabs 0.0). Against settlement truth the tail has 547 wrong interval cells over 23 symbols (IOST 1h for true 8h; SKR, T, SOPH, ZKC, COTI 4h for true 1h; six tokenized stock perps 4h for 8h). Corrected f_fund_ema_v1 differs by up to 0.0115 (IOST), 844 cells above 1e-6, per-anchor Spearman ≥ 0.9911, 47 FTRIM class flips on 38 anchors. The incumbent prefix is correct (0 mismatches). Caveat: settlement spacing itself mislabels the first long-interval settlement after a short-to-long switch (FIXPROGRAM P9); four of the counted cells fall exactly on the switch rows P9 lists (COTI 08-31 20Z, ZKC 09-02 20Z, T 09-06 00Z, SKR 09-07 20Z), where the pull-time value is probably the declared one and spacing is wrong, so the true count is 543-547. T5d re-ran T5c with corrected intervals (not yet re-run by the lead); T1 D2 September carry and the other September readings were not re-run. Recurrence in October is AUDIT_TRAIN TRN-07.
- **Evidence:**
  - `pod2 /workspace/uplift_2026-09-11/r6/r6_fetch_funding.py:33-34,69 (sha 298927ad, not in git)` — INFO = {d["symbol"]: float(d["fundingIntervalHours"]) for d in get(".../fapi/v1/fundingInfo") ...} ... "intervals": {k: v for k, v in INFO.items() if k in rates}
  - `pod2 /workspace/uplift_2026-09-11/r6/r6_panel_splice.py:82,90 (sha cccc5b6b, not in git)` — rows.append((int(t_ms)//1000, float(rate), SEP_IV.get(s, np.nan))) ... iv_full = np.where(np.isfinite(fiv), fiv, dv)
  - `devices_data/receipts/AD_B_funding_iv.json panels.v2ext_x0910 (ad_funding_iv.py f6d58b2b, commit feb7747e before run)` — {"iv_mismatch_cells": {"prefix": 0, "tail": 547}, "symbols": 23, "PC2": {"tail_iv_cells_not_reproduced": 0, "tail_ema_v1_cells_compared": 40560, "tail_ema_v1_maxabs_replica_vs_panel": 0.0, "PASS": true}, "flips": 47}
  - `AD_B_funding_iv.json top_symbols` — HK0700USDT panel [4.0] true [8.0] last 2026-09-10T00:00Z; HK1810USDT panel [4.0] true [8.0] last 2026-09-10T00:00Z; IOSTUSDT panel [1.0] true [8.0] last 2026-09-10T00:00Z; MINIMAXUSDT panel [4.0] true [8.0] last 2026-09-10T00:00Z; POPMARTUSDT panel [4.0] true [8.0] last 2026-09-10T00:00Z; TENCENTUSDT panel [4.0] true [8.0] last 2026-09-10T00:00Z; ZHIPUUSDT panel [4.0] true [8.0] last 2026-09-10T00:00Z; SKRUSDT panel [4.0] true [1.0] last 2026-09-07T20:00Z; TUSDT panel [4.0] true [1.0] last 2026-09-06T00:00Z; ZKCUSDT panel [4.0] true [1.0, 2.0] last 2026-09-02T20:00Z; SOPHUSDT panel [4.0] true [1.0] last 2026-09-10T00:00Z; COTIUSDT panel [4.0] true [1.0] last 2026-08-31T20:00Z
  - `docs/fixprogram_2026-09-13/FIXPROGRAM_2026-09-13.md:46 (P9)` — 短→长间隔切换时, 新制度首次结算按长间隔申报而时间差是短, 被标成短 ... COTI 08-31 20Z / ZKC 09-02 20Z / T 09-06 00Z / SKR 09-07 20Z
  - `git e73f50e6 (T5d)` — 研究 T5d 入库(结算间隔真值修正后重生成仓位复算 T5c; 未经 lead 复跑) ... 部署 king 链九月 carry 被低估 +0.253
- **Status:** OPEN_MEASURED_MATERIAL
- **Affects:** future_eval, reporting
- **Severity:** P2 — Confined to 60 September anchors and 23 names, already flagged PROVISIONAL and partly re-run; it can still move September carry and FTRIM readings by up to 2.4 bps per anchor for single names.
- **Recommended action:** Rebuild the x0910 funding tail with the declared interval where available and spacing otherwise (P9-aware), then re-run T1 D2 and any September carry reading; retire the r6 splice for future extensions (TRN-07).
- **Dependents (re-run status):** T1 D2 September carry (PROVISIONAL, not re-run); T5c (re-run as T5d e73f50e6, lead re-run pending); T2 live addendum d4; r6 JUDGE-1/2 September anchors; r9 x0910 replays; r12/r19 September sig_fund
- **Method:** VERIFIED

### FND-02 — API funding rows get their interval from settlement spacing; the canonical panels match that rule exactly, but spacing mislabels switch rows and nobody has measured them in the research panels

- **Layer:** funding source (fund_aug) / interval rule for API rows
- **What is wrong or unverified:** fund_aug.json.gz was written with an empty intervals map, so pod_panel_ext.py, pod_panel_splice.py and the bundle exporter derive API-row intervals from spacing; zip rows use the archive's own column. On the canonical v2ext panel the interval matches (zip column, else spacing) on all 3,263,922 compared cells. Spacing agrees with the archive column on 2,522,533 of 2,523,179 zip rows; the 646 disagreements are consistent with the switch rows FIXPROGRAM P9 describes (not classified row by row). The same mislabel therefore exists, unmeasured, wherever panel rows came from the API instead of a zip: 2026-08 rows of v2ext/v3splice (the August zip was not published at build time) and all x0910 September rows. The precedence rule (explicit interval over spacing) is a latent trap for any fund pull that fills intervals (TRN-07).
- **Evidence:**
  - `retrain_2026-09/fund_pull_pod.py:28 (= pod2 copy fa665810)` — out = {"rates": rates, "intervals": {}}
  - `retrain_2026-09/pod_panel_ext.py:66,105,120` — AUG_IV = {k: float(v) for k, v in (AUG.get("intervals") or {}).items() if v} ... AUG_IV.get(s, np.nan) ... iv_full = np.where(np.isfinite(fiv), fiv, dv)
  - `devices_data/receipts/AD_A_inventory.json fund_aug.json.gz (8a9e7715)` — {"n_symbols": 827, "n_rows": 2474251, "min_utc": "2021-12-01T00:00:00Z", "max_utc": "2026-09-01T02:00:00Z", "intervals_type": "dict", "intervals_n": 0, "intervals_head": {}, "meta": null}
  - `devices_data/receipts/AD_B_funding_iv.json PC1 and panels.v2ext` — {"PC1": {"zip_rows_with_col": 2524020, "both_defined": 2523179, "col_ne_spacing": 646, "rate_conflicts_between_sources": 0}, "v2ext": {"compared": {"prefix": 3263922, "tail": 0}, "mismatch": {"prefix": 0, "tail": 0}}}
  - `pod2 /workspace/wide_multisrc/funding (AD_A dirs)` — {"2025-12": 8, "2026-01": 9, "2026-02": 7, "2026-03": 9, "2026-04": 18, "2026-05": 4, "2026-06": 8, "2026-07": 680} (latest zip month per symbol; 2026-08 zips are .404 placeholders)
- **Status:** OPEN_NOT_MEASURED
- **Affects:** future_eval, future_retrain
- **Severity:** P2 — Switch rows scale one settlement by 2-4x in the normalised EMA and can flip FTRIM for one anchor; rare (646 rows in the whole zip history) but concentrated in the live window where intervals changed.
- **Recommended action:** Download the now-published 2026-08 (and later 2026-09) fundingRate zips read-only and rebuild the August/September intervals from the declared column; make every builder use declared > spacing and never a pull-time map.
- **Dependents (re-run status):** v2ext/v3splice August 2026 funding cells; x0910 September funding cells; bundle funding_ledger_seed / EMA state for October
- **Method:** VERIFIED

### HOL-01 — The panels every replay and the v4 chain read were built on the pre-holefix cache and still carry the filled holes in their kline columns

- **Layer:** 4h panels / hole residuals
- **What is wrong or unverified:** Same builder, same code, pre-fix cache versus hole-fixed cache: 393,475 kline cells differ on 522 anchors near the four fill runs and 0 cells elsewhere (the positive control). Examples: elig 28,183 cells, Y4 25,941, f_mom_30d 42,916, f_amihud_24h up to 302.9; funding keys identical. v3splice carries the same cells (its v1 prefix has the 2022 holes too) and the x0910 panels copy both prefixes verbatim. Consumers: rev24 z in the F10 legs (old rows verbatim), the pinned 2022 warm-up seat of A0, amihud/XIB candidates, and state variables on anchors within 30 days after a fill run (2022-02-25..2022-05-03 and 2026-08-11 to the panel end). October: a fresh PANEL_KING build on the rolled cache would be clean, but PANEL_SPLICE rolls the prefix and LEGS_OLD rows are copied verbatim, so the residual persists there. Book-level effect not measured.
- **Evidence:**
  - `devices_data/receipts/AD_D_panel_holes.json comparisons.v2ext (ad_panel_holes.py a62a9d48, commit feb7747e before run)` — {"common_anchors": 10039, "anchors_near_hole": 522, "kline_diff_cells_near_hole_total": 393475, "kline_diff_cells_away_from_hole_total": 0, "positive_control_kline_equal_away_from_holes": true}
  - `AD_D_panel_holes.json holes.fill_runs_utc (holefix2_cells.npz 6156f97a)` — [["2022-02-26T00:05Z", "2022-03-01T00:00Z"], ["2022-04-01T00:05Z", "2022-04-03T00:00Z"], ["2026-08-12T00:05Z", "2026-08-24T04:00Z"], ["2026-08-31T00:05Z", "2026-09-01T00:00Z"]]
  - `AD_A_inventory.json` — wide_panel_4h_v2ext.npz 5e67c0559daa904d mtime 2026-09-01T05:30:25Z (holefix2 cache mtime 2026-09-09T02:27:16Z); reference rawbuild_x0910 92a870a79cfaf130
  - `uplift_2026-09-11/RESULT_r6_coverage_extension_2026-09-11.md:249,254` — incumbent 面板里最大 302.9 ... 回放装置消费的面板就是 wide_panel_4h_v2ext.npz
- **Status:** OPEN_NOT_MEASURED
- **Affects:** future_eval, future_retrain
- **Severity:** P2 — Confined to about 5% of anchors, but those include the 2026-08 live window that current diagnostics study and the legs every F10 retrain copies forward.
- **Recommended action:** Rebuild v2ext-type and splice panels (and the legs Z24/ZFD old rows) on holefix2; re-run the diagnostics that use panel kline columns near 2026-08.
- **Dependents (re-run status):** XIB/amihud candidates (r5, r6 X3); T1/T8 states near 2026-08; F10 legs Z24; A0 warm-up 2022 rev24; none re-run
- **Method:** VERIFIED

### UNI-01 — Tokenized stock and commodity perps are 7.3% of 2026 training member pairs; evaluation masks them, training does not

- **Layer:** universe / training member sets
- **What is wrong or unverified:** Using the venue class snapshot, non-crypto names are 42,363 of 583,200 king-meta member pairs in 2026 (7.26%, present at all 1458 anchors), and identical in the DL targets; 2025 has 24 pairs. The replay and judge use the CRYPTO mask, but the F10 2026 folds, the F10 refit and the king fold-2026 gates (ic26, guard) include these names, and October adds September rows. Effect on models not measured.
- **Evidence:**
  - `devices_data/receipts/AD_C_cache_members.json C6 (venue_class_20260908.json fa9196a3)` — {"king": {"2022": {"pairs": 304434, "noncrypto_pairs": 0, "unknown_class_pairs": 25024, "anchors_with_noncrypto": 0, "noncrypto_share": 0.0}, "2023": {"pairs": 410358, "noncrypto_pairs": 0, "unknown_class_pairs": 23296, "anchors_with_noncrypto": 0, "noncrypto_share": 0.0}, "2024": {"pairs": 601406, "noncrypto_pairs": 0, "unknown_class_pairs": 13836, "anchors_with_noncrypto": 0, "noncrypto_share": 0.0}, "2025": {"pairs": 849811, "noncrypto_pairs": 24, "unknown_class_pairs": 5051, "anchors_with_noncrypto": 24, "noncrypto_share": 2.8e-05}, "2026": {"pairs": 583200, "noncrypto_pairs": 42363, "unknown_class_pairs": 344, "anchors_with_noncrypto": 1458, "noncrypto_share": 0.072639}}, "noncrypto_symbols_on_axis": 149}
  - `docs/PREREG_producer_parity_phase2_oos_2026-09-12.md D10` — 缺口 = 研究侧 top-400 取自全 829 名含股票永续, 生产-PIT 取自 PIT 名
- **Status:** OPEN_NOT_MEASURED
- **Affects:** future_retrain, live_trading
- **Severity:** P2 — A growing share of the newest training rows are names production never scores; it shifts the rank labels and the monthly folds that decide the swap.
- **Recommended action:** Apply the CRYPTO class filter to the king/DL member screens (or report the fold gates on both member sets) before the October folds.
- **Dependents (re-run status):** F10 monthly folds 202601-202608 and refit; king ic26 gate; P2 D10 coverage gap
- **Method:** VERIFIED

### OOF-01 — Replay model legs exist only from 2023 (F10) and 2024 (king), and A0's legs are on v3-lineage member lists; full-history numbers are not the in-service book

- **Layer:** OOF predictions / reference book coverage
- **What is wrong or unverified:** King OOF SLOW_v4 starts 2024-01-01T00:00Z (5844 anchors), F10 OOF starts 2023-01-01T00:00Z; A0's legs (SLOW_v3_on_v4axis, f10_A0) sit on member lists that differ from the v4 meta in 8,365 cells. So 2022 rows run without the F10 leg and 2022-2023 rows without the king leg, and A0 is built from the v3 lineage; the uplift error ledger (★1/★3) records that the cross-regime Sharpe used as a planning number is measured on a book that is not the in-service form for 36% of the sample.
- **Evidence:**
  - `devices_data/receipts/AD_C_cache_members.json C5_oof_masks` — {"SLOW_v4": {"anchors_with_any_pred": 5844, "first_pred_anchor": "2024-01-01T00:00Z", "pred_cells_outside_members": 0, "member_cells_without_pred_on_pred_anchors": 0, "pred_cells_with_nonfinite_forward_y4": 0}, "SLOW_v3_on_v4axis": {"anchors_with_any_pred": 5838, "first_pred_anchor": "2024-01-01T00:00Z", "pred_cells_outside_members": 8365, "member_cells_without_pred_on_pred_anchors": 8365, "pred_cells_with_nonfinite_forward_y4": 0}, "f10_v4RAW_s42": {"anchors_with_any_pred": 8034, "first_pred_anchor": "2023-01-01T00:00Z", "last_pred_anchor": "2026-08-31T20:00Z", "pred_cells_outside_dlw_v4raw_members": 0, "dlw_v4raw_member_cells_without_pred_on_pred_anchors": 0, "pred_cells_with_nonfinite_forward_y4s": 0}, "f10_v4RAW_s2027": {"anchors_with_any_pred": 8034, "first_pred_anchor": "2023-01-01T00:00Z", "last_pred_anchor": "2026-08-31T20:00Z", "pred_cells_outside_dlw_v4raw_members": 0, "dlw_v4raw_member_cells_without_pred_on_pred_anchors": 0, "pred_cells_with_nonfinite_forward_y4s": 0}, "f10_A0_s42": {"anchors_with_any_pred": 8028, "first_pred_anchor": "2023-01-01T00:00Z", "last_pred_anchor": "2026-08-30T20:00Z", "pred_cells_outside_dlw_v4raw_members": 8365, "dlw_v4raw_member_cells_without_pred_on_pred_anchors": 8365, "pred_cells_with_nonfinite_forward_y4s": 0}, "f10_A0_s2027": {"anchors_with_any_pred": 8028, "first_pred_anchor": "2023-01-01T00:00Z", "last_pred_anchor": "2026-08-30T20:00Z", "pred_cells_outside_dlw_v4raw_members": 8365, "dlw_v4raw_member_cells_without_pred_on_pred_anchors": 8365, "pred_cells_with_nonfinite_forward_y4s": 0}}
  - `uplift_2026-09-11/handoff_audit/errors/ERROR_LEDGER_uplift_2026-09-12.md:18,132,161` — 归档基线 A0 的 2022 与 2023 两行, 是缺腿的书 ... ★1 归档基线 A0 本身建在被 PIN 明令禁止的 v3 谱系上 ... ★3 1110 锚 F10 死前缀 + 3300 锚 king 死前缀
- **Status:** OPEN_MEASURED_MATERIAL
- **Affects:** future_eval, reporting
- **Severity:** P2 — Any full-history or 2022-2023 level quoted for the in-service form measures a different book; reference choice (A0 vs A1x) is still open.
- **Recommended action:** Quote the in-service form only on windows where both legs exist; decide the reference (A1x v4-native vs A0) and restate the yearly table with SE.
- **Dependents (re-run status):** CALIBER_PIN_v4 yearly table; CLOSEOUT uplift; ~300 paired verdicts against A0
- **Method:** VERIFIED

### LIN-01 — The x0910 extension builders exist only on pod2, while committed devices consume their products

- **Layer:** lineage hygiene / x0910 builders
- **What is wrong or unverified:** None of the 20 r6 builders and chain scripts (merge cache, panel splice, funding fetch, raw patch extension, king prediction, legs, dev tree, gates) is in git; the RESULT cites them by name only. Committed devices since 09-09 that read x0910 products: accounting meta 22, panel 19, cache 8, DL 14, king OOF 8 (overlapping). One of the unarchived builders carries FND-01.
- **Evidence:**
  - `devices_data/receipts/AD_A_inventory.json (pod2 r6 scripts)` — r6_bw1_gate.py 121e82a822ae6b3b; r6_bw345_fix.py 6fc58fc28ec35732; r6_bw345_gate.py 924737ec567254b8; r6_dev_tree.py faffd7268d75261a; r6_fetch_funding.py 298927ad16af7c03; r6_fetch_klines.py 2e52f81a64faf6d2; r6_incumbent.py 9a96db6ed07a9a88; r6_king_pred.py f8aba90458f23f7a; r6_legs_repair5.py 26b66fbc3b98a086; r6_legs_x0910.py 031b06b03a75e73d; r6_manifest.py d8dad04e419243b5; r6_merge_cache.py 3227e4f5be49cf54; r6_panel_splice.py cccc5b6be9248671; r6_raw_patch_ext.py 808d2f666f0c0be8; r6_xking.py a8fc225433eb3c08; r6_chain.sh acd39ebe0ca936a6; r6_chain_resume.sh 7eff9d2a523068d6; r6_chain_resume2.sh 728afae738cf4192; r6_finish.sh 72c47c4d1b24ec82; r6_super.sh ff15de651c25cfc1
  - `git ls-files | grep r6_` — receipts and RESULT only; no r6_*.py or r6_*.sh
  - `devices_data/receipts/AD_E_consumers_matrix.json (ad_consumers_scan.py e6d9a686, HEAD deb8a47b)` — {"acct_meta_v4_x0910": {"multi_asset/exports/research/uplift_2026-09-11/r12_intervene": 6, "multi_asset/exports/research/uplift_r2_2026-09-13/T1": 5, "multi_asset/exports/research/uplift_r2_2026-09-13/T5c": 3, "multi_asset/exports/research/uplift_r2_2026-09-13/T2": 2, "multi_asset/exports/research/uplift_2026-09-11/handoff_audit": 1, "multi_asset/exports/research/uplift_2026-09-11/r21_nulls_costbridge": 1, "multi_asset/exports/research/uplift_2026-09-11/r9_coverage": 1, "multi_asset/exports/research/uplift_r2_2026-09-13/T3": 1, "multi_asset/exports/research/uplift_r2_2026-09-13/T4": 1, "multi_asset/exports/research/uplift_r2_2026-09-13/T5": 1}, "panel_v2ext_x0910": {"multi_asset/exports/research/uplift_r2_2026-09-13/T1": 4, "multi_asset/exports/research/uplift_2026-09-11/r12_intervene": 3, "multi_asset/exports/research/uplift_r2_2026-09-13/T2": 2, "multi_asset/exports/research/uplift_r2_2026-09-13/T5": 2, "multi_asset/exports/research/uplift_r2_2026-09-13/T5c": 2, "multi_asset/exports/research/uplift_2026-09-11/handoff_audit": 1, "multi_asset/exports/research/uplift_2026-09-11/r21_nulls_costbridge": 1, "multi_asset/exports/research/uplift_2026-09-11/r9_coverage": 1, "multi_asset/exports/research/uplift_r2_2026-09-13/T3": 1, "multi_asset/exports/research/uplift_r2_2026-09-13/T4": 1, "multi_asset/exports/research/uplift_r2_2026-09-13/T5d": 1}}
- **Status:** OPEN_MEASURED_MATERIAL
- **Affects:** reporting, future_eval
- **Severity:** P2 — Conclusions outlive their devices (project rule 5); a pod loss would make every September reading irreproducible, and the defective splice would be re-used from memory.
- **Recommended action:** Copy the r6 builders with their shas into the research repo next to r6_MANIFEST; mark r6_panel_splice.py as defective (FND-01).
- **Dependents (re-run status):** all x0910 consumers
- **Method:** VERIFIED

### DOC-01 — Caliber documents and memory notes miss or misstate several data-lineage facts

- **Layer:** docs and memory
- **What is wrong or unverified:** CALIBER_STATUS_2026-09-09 still lists E-0908-C as 'full-history size not measured' (measured here, FWD-01) and has no rows for the king clock (TIM-01), DL funding coverage (FEA-01), dead contracts (TRD-01), hole residuals in panels (HOL-01) or non-crypto training members (UNI-01). RUNBOOK_2026-10 says the raw patch 'travels with the cache' with no extension step. The P2 prereg says F10 OOF availability is 'not checked' (C5 shows it has the same mask). crypto_mask_note.json says underlyingType=='COIN' while the builder keeps {COIN, INDEX}. The clip-compound memory note calls E-0908-C 'mild survivorship' without numbers.
- **Evidence:**
  - `docs/CALIBER_STATUS_2026-09-09.md:15` — E-0908-C | 成员集含未来标签谓词 | 研究员 C 臂: 单窗每锚 +0.0025/+0.0009 | 我方回放同样继承; 全史量级未测
  - `docs/RUNBOOK_monthly_retrain_2026-10.md:15,193` — 原始收益补丁 raw_patch.npz 随缓存走 ... 原始收益补丁 raw_patch.npz(952 bar)随缓存走
  - `docs/PREREG_producer_parity_phase2_oos_2026-09-12.md:329` — S2 不修正, 列为继承偏差; F10 OOF 的可得性掩码未核
  - `universe_crypto_2026-09-08/scripts/build_crypto_mask.py:11,44` — (CLS[s]["underlyingType"] in ("COIN","INDEX")) ... "definition":"UPIT & underlyingType=='COIN' (unknown -> kept)"
- **Status:** DOC_STALE
- **Affects:** reporting, future_retrain
- **Severity:** P2 — The October runbook and the caliber ledger are what an operator will read; three P1 facts are absent from both.
- **Recommended action:** Add rows for TIM-01, FEA-01, TRD-01, HOL-01, UNI-01 to CALIBER_STATUS; add the patch-extension and trades-flag steps to RUNBOOK_2026-10; update the P2 prereg D20 note and the mask note string.
- **Method:** VERIFIED

### TRD-03 — A0 holds dead contracts in the days right after their last trade, books a 0 return on them and charges carry from records that were not paid; the size is small

- **Layer:** replay book (A0) / positions in dead contracts
- **What is wrong or unverified:** On the A0 axis the replay universe contains dead member-anchors 3,689 / 753 / 6,948 / 10,564 / 9,165 per year (2022..2026, 1.30% / 0.19% / 1.19% / 1.20% / 1.48% of universe pairs); the trade set keeps 58 / 33 / 220 / 290 / 134 of them and all of those are held (|W| sum 0.413 / 0.151 / 0.612 / 0.408 / 0.303, share of annual |W| 2.5e-04 / 8.3e-05 / 4.9e-04 / 3.6e-04 / 2.6e-04). Every held dead cell has accounting return exactly 0; the carry booked on them is +1.68 / -0.45 / +0.51 / +2.24 / +3.54 bps summed over each year (s42; s2027 +1.68 / -0.45 / +0.50 / +3.25 / +3.52). The exit loss of a dead contract is not in the data. At this size the replay's level and Sharpe do not change within resolution; the separate forward-return exit (FWD-02) is smaller still.
- **Evidence:**
  - `devices_data/receipts/AD_H_tradability.json H2_A0_population (A0_PWR230k_s42 352ac36f, s2027 aa44e18f)` — {"2022": {"U_pairs": 283632, "U_DEAD": 3689, "U_DEAD_sel": 58, "held_DEAD": 58, "absW_DEAD": 0.4128885488025844, "absW_DEAD_share": 0.0002468700497636465, "held_DEAD_y4_exactly0": 58, "carry_bps_booked_on_DEAD": 1.6841929405466933}, "2023": {"U_pairs": 391716, "U_DEAD": 753, "U_DEAD_sel": 33, "held_DEAD": 33, "absW_DEAD": 0.1511420781898778, "absW_DEAD_share": 8.259326731883982e-05, "held_DEAD_y4_exactly0": 33, "carry_bps_booked_on_DEAD": -0.44815621486495155}, "2024": {"U_pairs": 583698, "U_DEAD": 6948, "U_DEAD_sel": 220, "held_DEAD": 220, "absW_DEAD": 0.6124279987598129, "absW_DEAD_share": 0.0004893531958731533, "held_DEAD_y4_exactly0": 220, "carry_bps_booked_on_DEAD": 0.5135642590723974}, "2025": {"U_pairs": 883752, "U_DEAD": 10564, "U_DEAD_sel": 290, "held_DEAD": 290, "absW_DEAD": 0.40751904986882437, "absW_DEAD_share": 0.00036415127689178874, "held_DEAD_y4_exactly0": 290, "carry_bps_booked_on_DEAD": 2.2360928163956664}, "2026": {"U_pairs": 618259, "U_DEAD": 9165, "U_DEAD_sel": 134, "held_DEAD": 134, "absW_DEAD": 0.3033953535104956, "absW_DEAD_share": 0.0002639636916705671, "held_DEAD_y4_exactly0": 134, "carry_bps_booked_on_DEAD": 3.5363017476887553}}
  - `AD_H_tradability.json H2 positive-control field held_outside_U (smoothing carry-over outside the universe)` — 0 / 0 / 0 / 366 / 186
- **Status:** VERIFIED_IMMATERIAL
- **Affects:** future_eval
- **Severity:** P3 — Held dead exposure is at most 4.9e-4 of annual gross and the booked carry about 0.002 bps per anchor; far below the 0.23 bps resolution.
- **Recommended action:** None for A0; include the trades flag (TRD-01) before any sleeve that holds illiquid or deeply negative-funding names is judged.
- **Dependents (re-run status):** A0 / NW (immaterial)
- **Method:** VERIFIED

### TRD-05 — King and DL training members include dead contracts with labels exactly 0 in the first days after death

- **Layer:** training rows (king meta, DL targets)
- **What is wrong or unverified:** King meta members that are dead: 255 / 126 / 1,250 / 762 / 304 pairs per year (2022..2026), all with accounting y4 exactly 0; DL members 255 / 126 / 1,250 / 762 / 304, all y4s exactly 0 (largest share 0.21%). The 7-day volatility screen removes them after about a week; before that they are training rows with a zero label.
- **Evidence:**
  - `devices_data/receipts/AD_H_tradability.json H4_training_rows` — {"king_meta": {"2022": {"king_member_pairs": 304434, "Z24": 324, "DEAD": 255, "DEAD_y4_exactly0": 255, "Z24_y4_exactly0": 324}, "2023": {"king_member_pairs": 410358, "Z24": 108, "DEAD": 126, "DEAD_y4_exactly0": 126, "Z24_y4_exactly0": 108}, "2024": {"king_member_pairs": 601406, "Z24": 1214, "DEAD": 1250, "DEAD_y4_exactly0": 1250, "Z24_y4_exactly0": 1214}, "2025": {"king_member_pairs": 849811, "Z24": 650, "DEAD": 762, "DEAD_y4_exactly0": 762, "Z24_y4_exactly0": 650}, "2026": {"king_member_pairs": 583200, "Z24": 81, "DEAD": 304, "DEAD_y4_exactly0": 304, "Z24_y4_exactly0": 81}}, "dl_targets": {"2022": {"dl_member_pairs": 308514, "DEAD": 255, "DEAD_y4s_exactly0": 255, "anchors_off_king_axis": 30}, "2023": {"dl_member_pairs": 410358, "DEAD": 126, "DEAD_y4s_exactly0": 126, "anchors_off_king_axis": 0}, "2024": {"dl_member_pairs": 601406, "DEAD": 1250, "DEAD_y4s_exactly0": 1250, "anchors_off_king_axis": 0}, "2025": {"dl_member_pairs": 849811, "DEAD": 762, "DEAD_y4s_exactly0": 762, "anchors_off_king_axis": 0}, "2026": {"dl_member_pairs": 583200, "DEAD": 304, "DEAD_y4s_exactly0": 304, "anchors_off_king_axis": 0}}}
- **Status:** VERIFIED_IMMATERIAL
- **Affects:** future_retrain
- **Severity:** P3 — At most 0.21% of member pairs; rank labels place them mid-distribution.
- **Recommended action:** Exclude with the trades flag when the member screens are next edited; not worth a retrain by itself.
- **Dependents (re-run status):** king v3/v4 boosters, F10 v3/v4 (immaterial)
- **Method:** VERIFIED

### RET-01 — Every clipped bar in the research caches through 2026-09-11 00:00Z has a patch entry; no research cache or panel exists after that

- **Layer:** accounting returns / clip patch (data-side TRN-02 check)
- **What is wrong or unverified:** Canonical cache: 953 cells sit exactly on the float16 ±0.30 bound, 0 beyond it; 952 are in raw_patch.npz and the remaining one (NMRUSDT 2025-10-10T21:35Z) is a true return inside ±0.30 that float16 rounds onto the bound (make_raw_patch 'not clipped'), so no clipped bar is unpatched. x0910 tail: 3 bound cells (AKEUSDT 2026-09-02T21:45Z, BULLAUSDT 2026-09-05T03:00Z, WOOUSDT 2026-09-06T01:35Z), all in raw_patch_x0910; its first 952 rows equal raw_patch.npz. Clipped bars per month in 2026: 01 4, 02 7, 03 11, 04 16, 05 5, 06 6, 07 10, 08 9, 09 3. No research cache, panel or meta has rows after 2026-09-11 00:00Z, so September 11-30 is not present and must be checked when the month is rolled (the gate itself is AUDIT_TRAIN TRN-02, P1).
- **Evidence:**
  - `devices_data/receipts/AD_C_cache_members.json C1_clip_bound_vs_patch (ad_cache_members.py 0e8bc8fd, commit feb7747e before run)` — {"bound_value": 0.300048828125, "bound_cells": 953, "cells_beyond_bound": 0, "patch_rows": 952, "bound_cells_in_patch": 952, "bound_cells_NOT_in_patch": 1, "not_in_patch_list": [{"ts": "2025-10-10T21:35Z", "symbol": "NMRUSDT", "clip16": 0.300048828125}], "bound_cells_by_year": {"2022": 33, "2023": 6, "2024": 13, "2025": 833, "2026": 68}}
  - `AD_C_cache_members.json C1.x0910` — {"tail_first": "2026-09-01T00:05Z", "tail_last": "2026-09-11T00:00Z", "tail_bound_cells": 3, "tail_bound_cells_in_patch": 3, "patch_x0910_prefix_equals_incumbent_patch": true}
  - `retrain_2026-09/caliber_program_2026-09-09/make_raw_patch.py:30` — if abs(rv) <= 0.3: notclip += 1; continue
  - `AD_A_inventory.json` — holefix2_x0910 cache last row 2026-09-11T00:00:00Z; meta_newprod_v4_x0910 last anchor 2026-09-10T20:00:00Z
- **Status:** FIXED_DEPLOYED
- **Affects:** future_eval
- **Severity:** P3 — The evaluation data in use are correct; the open risk is the October roll, registered as TRN-02.
- **Recommended action:** None for current data; implement TRN-02's coverage assertion in the roll.
- **Dependents (re-run status):** meta_newprod_v4 / x0910 accounting y4; dlw_v4raw RAW targets
- **Method:** VERIFIED

### RET-02 — Several devices written after the 09-12 rule still compound or sum returns from the clipped ret5 channel

- **Layer:** devices / returns recomputed from the clipped cache channel
- **What is wrong or unverified:** r14 (estimand drift), r21 (cost bridge), r12_mon (y4 monitors), event_state build_sett_v4 (settlement-window drift), s12 (target direction), smooth_latency_core (latency P&L), materiality_probe_v2 (rolling.npz, acknowledged) and r13/beta estimation read ret5 for returns. Only windows containing a bound bar are wrong; 2026 had 68 such bars before September and the live window 3. Per-device exposure was not measured; T3 uses the channel only to back-project up to 5 bars and is guarded.
- **Evidence:**
  - `uplift_2026-09-11/r14_estimand/devices/r14_gap.py:68,93` — RET = np.asarray(CD[:, :, 0], np.float64) ... CL = np.concatenate([...np.cumsum(np.where(fin, np.log1p(np.clip(RET, -0.99, None)), 0.0), 0)])
  - `uplift_2026-09-11/r12_intervene/devices/r12_mon.py:36,51` — y4 = prod(1+ret5[E+1 .. E+48]) - 1 ... cp=np.cumprod(1.0+blk,0)-1.0
  - `uplift_2026-09-11/event_state/devices/build_sett_v4.py:48` — dr=float(np.prod(1.0+w[ok])-1.0) if ok.any() else np.nan
  - `memory cache_ret5_channel_clipped_at_0p30_2026_09_12` — never rebuild 4h/24h returns, price-available flags, or regime primitives from the cache ret5 on extreme bars
- **Status:** OPEN_NOT_MEASURED
- **Affects:** future_eval
- **Severity:** P3 — Diagnostics over short windows; wrong only where a bound bar falls inside the window.
- **Recommended action:** Swap to raw_patch-corrected returns or assert no bound bar in the window, per device, when each is next reused.
- **Dependents (re-run status):** r12 monitors; r14; r21; event_state; r10 s12
- **Method:** VERIFIED

### LBL-01 — King labels are ranks of the clipped 5m sum over rows [E, E+47]; the export guard books P&L on the same label

- **Layer:** king labels
- **What is wrong or unverified:** The king meta y4 is Σ clipped ret5 over rows [E, E+47] (reproduced exactly, maxabs 0.0), i.e. from the close before the anchor to five minutes before the accounting window ends; the exporter ranks it for training and uses it for the guard band P&L. Both parts were measured at book level: the clip part on an upper-bound arm (four cells undecided) and the window part (-0.051 [-0.115, +0.016] bps per anchor per gross, 2024-26). October keeps both.
- **Evidence:**
  - `v4_chain_2026-09-09/pod_export_bundle_v4.py:42,55-59,166` — y4 = MT["y4"] ... rr = rankdata(yv[ok]) ... rows_y.append(rr) ... yv = np.nan_to_num(y4[i, m], nan=0.0)
  - `docs/RESULT_king_clip_label_ablation_2026-09-08.md:52` — 裁剪不构成 king 的重训理由(上界臂实测, 四格 UNDECIDED)
  - `docs/RESULT_f10_caliber_sensitivity_2026-09-05.md:28` — king 窗口项 2024→26 -0.051 [-0.115,+0.016](小, CI 含 0)
- **Status:** VERIFIED_IMMATERIAL
- **Affects:** future_retrain
- **Severity:** P3 — Both parts measured inside resolution; the window part is fixed together with TIM-01.
- **Recommended action:** Fold into the TIM-01 decision (the clock-aligned builder also moves the label to [E+1, E+48]).
- **Dependents (re-run status):** king boosters; export guard band
- **Method:** VERIFIED

### FWD-01 — The forward-return member predicate removes almost nothing, because dead contracts keep finite frozen returns; king and F10 OOF carry the same mask

- **Layer:** member screens / OOF availability (D20, E-0908-C)
- **What is wrong or unverified:** Rebuilding both member rules exactly (positive control: axes and every member list equal) and dropping only the forward predicate: king rule removes 33 / 3 / 1 / 3 / 3 pairs per year (2022..2026), DL rule 33 / 3 / 1 / 3 / 3; no anchor exists only without it; 24 of the 33 2022 removals never trade again. King OOF (SLOW_v4) and F10 OOF (f10_v4RAW) are written exactly on those member lists (0 predictions outside, 0 members without prediction, 0 predictions on non-finite forward returns). The predicate cannot see most deaths because the archive's frozen rows keep the forward return finite at 0 (TRD-01); the real survivorship channel is inclusion, not exclusion. AUDIT_TRAIN TRN-06's 'wider than recorded' reading should be read with these counts.
- **Evidence:**
  - `devices_data/receipts/AD_C_cache_members.json C3_positive_control` — {"king": {"axis_equal": true, "n_derived": 10182, "n_file": 10182, "member_lists_unequal": 0, "unequal_first": [], "y4_finite_pattern_equal": true, "y4_maxabs_window_rows_E_to_E+47": 0.0}, "dl": {"axis_equal": true, "n_derived": 10212, "n_file": 10212, "member_lists_unequal": 0, "unequal_first": [], "y4s_finite_pattern_equal_rule_count_ge_46": true}, "PASS": true}
  - `AD_C_cache_members.json C3_forward_predicate.king_meta_rule` — {"2022": {"anchors_no_predicate": 2148, "anchors_with_predicate": 2148, "anchors_only_without_predicate": 0, "pairs_no_predicate": 304467, "pairs_removed_forward_nonfinite": 33, "pairs_backfilled": 0, "removed_y4n_zero": 22, "removed_y4n_partial": 11, "removed_name_never_trades_again": 24, "removed_inside_crypto_mask": 30, "share_removed_of_no_predicate_pairs": 0.000108}, "2023": {"anchors_no_predicate": 2190, "anchors_with_predicate": 2190, "anchors_only_without_predicate": 0, "pairs_no_predicate": 410361, "pairs_removed_forward_nonfinite": 3, "pairs_backfilled": 0, "removed_y4n_zero": 2, "removed_y4n_partial": 1, "removed_name_never_trades_again": 0, "removed_inside_crypto_mask": 3, "share_removed_of_no_predicate_pairs": 7e-06}, "2024": {"anchors_no_predicate": 2196, "anchors_with_predicate": 2196, "anchors_only_without_predicate": 0, "pairs_no_predicate": 601407, "pairs_removed_forward_nonfinite": 1, "pairs_backfilled": 0, "removed_y4n_zero": 0, "removed_y4n_partial": 1, "removed_name_never_trades_again": 1, "removed_inside_crypto_mask": 1, "share_removed_of_no_predicate_pairs": 2e-06}, "2025": {"anchors_no_predicate": 2190, "anchors_with_predicate": 2190, "anchors_only_without_predicate": 0, "pairs_no_predicate": 849811, "pairs_removed_forward_nonfinite": 3, "pairs_backfilled": 3, "removed_y4n_zero": 2, "removed_y4n_partial": 1, "removed_name_never_trades_again": 3, "removed_inside_crypto_mask": 3, "share_removed_of_no_predicate_pairs": 4e-06}, "2026": {"anchors_no_predicate": 1458, "anchors_with_predicate": 1458, "anchors_only_without_predicate": 0, "pairs_no_predicate": 583200, "pairs_removed_forward_nonfinite": 3, "pairs_backfilled": 3, "removed_y4n_zero": 2, "removed_y4n_partial": 1, "removed_name_never_trades_again": 3, "removed_inside_crypto_mask": 3, "share_removed_of_no_predicate_pairs": 5e-06}}
  - `AD_C_cache_members.json C5_oof_masks (SLOW_v4, f10_v4RAW_s42)` — {"SLOW_v4": {"axis": "king meta (10182)", "anchors_with_any_pred": 5844, "first_pred_anchor": "2024-01-01T00:00Z", "pred_cells_outside_members": 0, "member_cells_without_pred_on_pred_anchors": 0, "pred_cells_with_nonfinite_forward_y4": 0}, "f10_v4RAW_s42": {"axis": "dlw_v4raw targets (10212)", "anchors_with_any_pred": 8034, "first_pred_anchor": "2023-01-01T00:00Z", "last_pred_anchor": "2026-08-31T20:00Z", "pred_cells_outside_dlw_v4raw_members": 0, "dlw_v4raw_member_cells_without_pred_on_pred_anchors": 0, "pred_cells_with_nonfinite_forward_y4s": 0}}
- **Status:** VERIFIED_IMMATERIAL
- **Affects:** future_eval, future_retrain
- **Severity:** P3 — At most 1.1e-4 of member pairs per year.
- **Recommended action:** None beyond TRD-01; replace the predicate by the causal trades flag when the screens are edited.
- **Dependents (re-run status):** P2 D20; FIXPROGRAM D3; AUDIT_TRAIN TRN-06
- **Method:** VERIFIED

### FWD-02 — The replay exits positions whose next accounting return is non-finite and books 0 for them; 13 pairs in the whole A0 history

- **Layer:** replay accounting / non-finite forward returns
- **What is wrong or unverified:** A0 positions dumped because the next 4 h accounting return is non-finite: 10 / 1 / 0 / 1 / 0 pairs per year (2022..2026), |W| 0.0411 / 0.0094 / 0.0000 / 0.0002 / 0.0000, 9 of 13 in contracts that never trade again (KEEP, NU, 1000BTTC, YFII, ANC, LUNA, DODO, AKRO, EOS). The exit P&L at those delistings is not in the data (L4b measured such exits for the carry sleeve).
- **Evidence:**
  - `devices_data/receipts/AD_C_cache_members.json C4_A0_forward_nonfinite_exits.42` — {"2022": {"anchors": 2009, "anchors_with_dump": 7, "dumped_pairs": 10, "dumped_abs_weight_prev": 0.04106994689209387, "dumped_pairs_name_never_trades_again": 8, "dumped_abs_weight_never_trades_again": 0.029905769450124353, "abs_weight_at_anchor_on_dumped": 0.0, "gross_prev_sum": 1671.5690522663992, "dumped_share_of_gross_prev_sum": 2.456969805489586e-05}, "2023": {"anchors": 2190, "anchors_with_dump": 1, "dumped_pairs": 1, "dumped_abs_weight_prev": 0.009416750632226467, "dumped_pairs_name_never_trades_again": 0, "dumped_abs_weight_never_trades_again": 0.0, "abs_weight_at_anchor_on_dumped": 0.0, "gross_prev_sum": 1830.13997613188, "dumped_share_of_gross_prev_sum": 5.1453718049093616e-06}, "2024": {"anchors": 2196, "anchors_with_dump": 0, "dumped_pairs": 0, "dumped_abs_weight_prev": 0.0, "dumped_pairs_name_never_trades_again": 0, "dumped_abs_weight_never_trades_again": 0.0, "abs_weight_at_anchor_on_dumped": 0.0, "gross_prev_sum": 1251.7970190506828, "dumped_share_of_gross_prev_sum": 0.0}, "2025": {"anchors": 2190, "anchors_with_dump": 1, "dumped_pairs": 1, "dumped_abs_weight_prev": 0.0001812294649425894, "dumped_pairs_name_never_trades_again": 1, "dumped_abs_weight_never_trades_again": 0.0001812294649425894, "abs_weight_at_anchor_on_dumped": 0.0, "gross_prev_sum": 1118.7053626909615, "dumped_share_of_gross_prev_sum": 1.619992814789549e-07}, "2026": {"anchors": 1453, "anchors_with_dump": 0, "dumped_pairs": 0, "dumped_abs_weight_prev": 0.0, "dumped_pairs_name_never_trades_again": 0, "dumped_abs_weight_never_trades_again": 0.0, "abs_weight_at_anchor_on_dumped": 0.0, "gross_prev_sum": 1149.435523992192, "dumped_share_of_gross_prev_sum": 0.0}}
- **Status:** VERIFIED_IMMATERIAL
- **Affects:** future_eval
- **Severity:** P3 — Largest yearly share 2.5e-5 of gross.
- **Recommended action:** None.
- **Dependents (re-run status):** r18 N2 (consistent: 15 cells)
- **Method:** VERIFIED

### FND-03 — The v1 canonical panel's August 2026 API tail stored one interval per symbol; 138 cells for five names, the same rows as the 08-16 bundle seed

- **Layer:** v1 canonical panel / API tail intervals
- **What is wrong or unverified:** On the splice prefix (v1 canonical) 138 cells differ from settlement truth, all in 2026-08-01..08-14 for DEXE, ERA, BANK, PROM and ACE (stored 4 h, true 1-2 h); nothing earlier differs. These are the D17 rows P2 traced to the 08-16 bundle seed; their residual in live EMA is decaying and was measured small. Builder on jpline (unverifiable).
- **Evidence:**
  - `devices_data/receipts/AD_B_funding_iv.json panels.v3splice` — {"mismatch": {"prefix": 138, "tail": 0}, "by_month": {"2026-08": 138}, "symbols": ["DEXEUSDT", "ERAUSDT", "BANKUSDT", "PROMUSDT", "ACEUSDT"]}
  - `retrain_2026-09/second_instrument_rebuild_2026-09-05/REPORT.md:55` — rebuilt interval 1 h / 2 h (per-settlement column of the 2026-08 monthly zip) vs v1 4 h (the 08-21 API tail's single per-symbol interval)
- **Status:** VERIFIED_IMMATERIAL
- **Affects:** future_retrain
- **Severity:** P3 — 138 cells in two weeks for five names; live residual measured by P2 D17 and FIXPROGRAM P6'.
- **Recommended action:** Covered by FIXPROGRAM P6'; rebuild the splice prefix funding from zips when HOL-01/FEA-01 are rebuilt.
- **Dependents (re-run status):** legs ZFD for five names in 2026-08; fund_state_canoncont seeds
- **Method:** VERIFIED

### UNI-02 — The 829-name axis is an S3 listing from 2026-08-21 that keeps delisted names; it is frozen at that date

- **Layer:** universe / symbol axis
- **What is wrong or unverified:** The axis includes contracts that died before and inside the window (by trades 156 died inside the cache; 3 names have no bar at all). No 2022+ survivorship is visible in the axis. The CRYPTO mask keeps the 31 names absent from today's exchangeInfo. Names listed after 2026-08-21 never enter research data; production pins are also frozen, so the two agree.
- **Evidence:**
  - `retrain_2026-09/jpline_lineage_2026-09-05.md:26` — 宇宙符号轴 ... S3 列 data/futures/um/monthly/klines/ 前缀 ... panel_symbols_wide.txt ... 829
  - `devices_data/receipts/AD_C_cache_members.json C2 + AD_H H1` — no_finite_bar ['BZRXUSDT', 'DOTECOUSDT', 'LENDUSDT']; dead inside cache by trades 156
  - `universe_crypto_2026-09-08/scripts/build_crypto_mask.py:11` — if s in CLS else True for s in syms])  # 未知 ⇒ 保留
- **Status:** VERIFIED_IMMATERIAL
- **Affects:** future_eval
- **Severity:** P3 — No survivorship in the axis for the evaluation window.
- **Recommended action:** Refresh the axis when the universe is refreshed (separate event).
- **Method:** VERIFIED

### TIM-02 — Only L2 reads the metrics archive and it applies the label regime by date

- **Layer:** metrics archive label switch (2024-03-04)
- **What is wrong or unverified:** The 2024-03-04 switch (window END labels before, START after) matters only to consumers of data.binance.vision metrics; since 09-09 those are the L2 devices, which encode the regime explicitly. No panel, cache or retrain builder reads the archive (AUDIT_TRAIN TRN-08).
- **Evidence:**
  - `uplift_r3_2026-09-13/L2/devices/l2_a_archive.py:12-14,225` — archive labels = window END up to 2024-03-03 and window START from 2024-03-04 ... REG = ("END_pre_2024-03-04", "START_from_2024-03-04")
  - `devices_data/receipts/AD_E_consumers_matrix.json metrics_archive` — {"multi_asset/exports/research/uplift_r3_2026-09-13/L2": 2}
- **Status:** VERIFIED_IMMATERIAL
- **Affects:** future_eval
- **Severity:** P3 — Handled at the only consumer.
- **Recommended action:** None.
- **Dependents (re-run status):** FIXPROGRAM D2
- **Method:** VERIFIED

### TIM-03 — The cache labels bars by close time; panel features end one bar before the anchor, DL features include the anchor bar

- **Layer:** 5m cache timestamps
- **What is wrong or unverified:** ts = open_time + 5 min in the cache builder and the producer; panel windows are rows [E-w, E-1] (one bar staler than production), DL windows [E-w+1, E] with targets from E+1. The rev24 panel factor is out of the combo book; research factors from the panel are one bar stale, which is conservative.
- **Evidence:**
  - `retrain_2026-09/pod_merge_cache_ext.py:24` — k['ts'] = pd.to_datetime(k.open_time.astype(np.int64), unit='ms') + pd.Timedelta('5min')
  - `retrain_2026-09/pod_dlw_features_ext.py:3` — 窗端点对齐为 rows [E−w+1, E+1)(含收盘于 N 的那根 bar; 目标从 E+1 起 ⇒ 零重叠零间隙)
- **Status:** VERIFIED_IMMATERIAL
- **Affects:** future_eval
- **Severity:** P3 — Consistent within each lineage; the king case is TIM-01.
- **Recommended action:** None.
- **Method:** VERIFIED

### HOL-02 — Cache holes E-0908-D and E-0909-B are filled in holefix2 and in its extension

- **Layer:** 5m cache / holes
- **What is wrong or unverified:** holefix2 filled 1,422,720 (row, symbol) pairs in four runs; the coverage gate passes on holefix2 and on the x0910 extension, and the r6 extension is bitwise equal to holefix2 on the common prefix. The residual lives in the panels built earlier (HOL-01).
- **Evidence:**
  - `AD_D_panel_holes.json holes` — [["2022-02-26T00:05Z", "2022-03-01T00:00Z"], ["2022-04-01T00:05Z", "2022-04-03T00:00Z"], ["2026-08-12T00:05Z", "2026-08-24T04:00Z"], ["2026-08-31T00:05Z", "2026-09-01T00:00Z"]]
  - `uplift_2026-09-11/RESULT_r6_coverage_extension_2026-09-11.md (X1, BW-1)` — COVERAGE_GATE_V2 PASS (hole symbol-days 0 in multi-symbol runs; wide-gap days 0) ... bitwise_diff 0
- **Status:** FIXED_DEPLOYED
- **Affects:** future_eval, future_retrain
- **Severity:** P3 — Fixed at the cache.
- **Recommended action:** None.
- **Method:** VERIFIED

### LIN-02 — A 09-12 test run rewrote dlw_v4raw/data/dlw_targets.npz on pod2; the bytes are identical

- **Layer:** lineage / write incident
- **What is wrong or unverified:** tests_pipeline_gates [S] R5 ran the untranslated legacy chain_v4_data.sh on pod2 at 15:12Z; the 60 s timeout killed bash but the python child finished at 15:17:54Z and rewrote the RAW targets, their report and chain_v4_data.log. The file's sha is still d1976cf6 (the 09-09 value) and the test was switched to a translated copy in 942b3e73.
- **Evidence:**
  - `retrain_2026-09/v4_chain_2026-09-09/receipts/monthly_chain_2026-09-12/tests_pipeline_gates_pod2_final3.log:380-381` — subprocess.TimeoutExpired: Command '['bash', '/workspace/w3_monthly_chain_2026-09-12/device/chain_v4_data.sh']' timed out after 60 seconds
  - `devices_data/receipts/AD_A_inventory.json dlw_v4raw/data/dlw_targets.npz` — sha d1976cf6246cdc25 mtime 2026-09-12T15:17:54Z
- **Status:** VERIFIED_IMMATERIAL
- **Affects:** reporting
- **Severity:** P3 — No content change; same family as E-0912-B.
- **Recommended action:** Record the incident next to E-0912-B.
- **Method:** VERIFIED

### LIN-03 — Builder copies on pod2 match git; all audit receipts are bound to the committed devices

- **Layer:** lineage / builder identity
- **What is wrong or unverified:** 16 builder copies on pod2 equal git HEAD byte for byte; build_dev_v4.py, pod_legs_v4b.py and pod_export_bundle_v4.py on pod2 equal earlier commits (5749a821, 3f058a7c, 5d214260). Every AD receipt's self_sha256 equals the committed device.
- **Evidence:**
  - `devices_data/receipts/AD_A_inventory.json (pod2 builder shas) vs git show HEAD:<path> | shasum` — fund_pull_pod fa665810, pod_panel_ext db7f0474, pod_panel_splice a9c29141, pod_fea_ext_clamp b9f9c728, pod_dlw_targets_raw d7c52823, make_raw_patch 7716e7d3 ... equal
- **Status:** VERIFIED_IMMATERIAL
- **Affects:** reporting
- **Severity:** P3 — Traceable lineage.
- **Recommended action:** None.
- **Method:** VERIFIED

### EVL-01 — w10 sleeve devices still default CAL to 'simple' (expm1 on an already simple return); every committed run since 09-09 sets CAL=log

- **Layer:** replay device default
- **What is wrong or unverified:** 21 sleeve device files committed since 09-09 read os.environ.get("CAL", "simple"); among receipt/log files committed since then, 39 record "CAL": "log" and none "CAL": "simple". A run that forgets the variable would apply expm1 to RAW y4.
- **Evidence:**
  - `uplift_2026-09-11/r18_foundation/devices/w10_sleeve_r18.py:17` — CAL = os.environ.get("CAL", "simple")                 # simple = 交易所记账(y -> expm1)
- **Status:** VERIFIED_IMMATERIAL
- **Affects:** future_eval
- **Severity:** P3 — Latent trap (E-0826-C family); no affected run found.
- **Recommended action:** Make CAL required or default to log.
- **Method:** VERIFIED

### LED-01 — Research tools that read daily_nav.realised_by_type COMMISSION/REALIZED_PNL inside 07-29..09-12 print wrong fee columns; their conclusions do not use them

- **Layer:** research readers of daily_nav (AUDIT_EXEC LED-04)
- **What is wrong or unverified:** live_root_cause_2026-09-09.py and live_root_cause_part3_flatten_funding.py print COMMISSION next to NAV, TRANSFER and FUNDING_FEE; three August probes (attr_2day, inrole_simple_return_rerun, phase_alignment_audit) and build_viz.py read COMMISSION/REALIZED_PNL. LED-04 affects COMMISSION and REALIZED_PNL (shared tranIds, BNB amounts); FUNDING_FEE and TRANSFER rows share no tranId. The 09-09 root cause rests on the position-times-mid decomposition, not on the fee column.
- **Evidence:**
  - `multi_asset/exports/live/pilot_journal/tools/live_root_cause_2026-09-09.py:80,82` — cm = float(bt.get("COMMISSION") or 0) ... print(f"... funding {ff:+7,.0f} comm {cm:+6,.0f} | pos×mid {pm:+8,.0f}")
  - `multi_asset/exports/live/pilot_journal/tools/live_root_cause_part3_flatten_funding.py:43,47` — cm=float(bt.get("COMMISSION") or 0) ... tot_cm = sum(v["cm"] for d, v in daily.items() if d >= "20260827")
  - `docs/audit_pipeline_2026-09-13/AUDIT_EXEC.json LED-04` — 24,723 tranIds shared by a COMMISSION and a REALIZED_PNL row of the same symbol; FUNDING_FEE rows share none
- **Status:** VERIFIED_IMMATERIAL
- **Affects:** reporting
- **Severity:** P3 — Printed columns only; no decision depends on them.
- **Recommended action:** Annotate those outputs; take fees from guard_twin income.jsonl if they are reused.
- **Dependents (re-run status):** journal tables printed by the two 09-09 tools; build_viz daily split chart
- **Method:** VERIFIED

### UNI-03 — September anchors use the last August mask row carried forward

- **Layer:** universe mask frontier
- **What is wrong or unverified:** umask_UPIT_CRYPTO ends 2026-08-31 00Z; x0910 September readings carry that row forward (declared in T2/T5c). A September listing, delisting or monthly refresh is therefore not reflected; not measured.
- **Evidence:**
  - `devices_data/receipts/AD_A_inventory.json` — umask_UPIT_CRYPTO last 2026-08-31T00:00:00Z; T5c umask_UPIT_CRYPTO_cf_x0910 last 2026-09-10T00:00:00Z
  - `uplift_r2_2026-09-13/T2/PREREG_T2_carry_net_sizing_2026-09-13.md:73` — the incumbent umask ends 2026-08-31 00Z, so its last row is carried forward for September — an approximation, labelled
- **Status:** OPEN_NOT_MEASURED
- **Affects:** future_eval
- **Severity:** P3 — Declared approximation over 60 anchors.
- **Recommended action:** Build a September mask row with the same monthly rule when September is rolled.
- **Dependents (re-run status):** T2 d4; T5c/T5d
- **Method:** VERIFIED

## 4. Would the next retrain still carry them? (October chain inputs)

| Defect | Carried into October | Items |
|---|---|---|
| Clip-compound on new clipped bars (E-0908-B) | Yes unless the roll extends the patch; current data clean through 2026-09-11 | RET-01, AUDIT_TRAIN TRN-02 |
| Month-roll inputs without a committed builder | Yes | AUDIT_TRAIN TRN-01, LIN-01, FND-01 |
| King clock / label window (E-0909-F) | Yes (pod_fea_ext_clamp.py again) | TIM-01, LBL-01 |
| DL funding features from the 2026-08 live list | Yes (PANEL_SPLICE keeps the v1 prefix) | FEA-01 |
| Dead contracts with frozen rows / funding records | Yes (no trades flag anywhere) | TRD-01, TRD-02, TRD-05 |
| Non-crypto names in training members | Yes, larger (September rows) | UNI-01 |
| Hole residuals in panels and legs | Partly: a fresh PANEL_KING is clean, PANEL_SPLICE prefix and LEGS_OLD rows are not | HOL-01 |
| Pull-time funding interval | Only if the September pull fills intervals | FND-01, FND-02, AUDIT_TRAIN TRN-07 |
| Switch-row interval mislabels (spacing rule) | Yes for API-only rows (September, and August if not rebuilt from zips) | FND-02, FIXPROGRAM P9 |
| Fund EMA v0 train / v1 serve (H2b) | Yes | AUDIT_TRAIN TRN-04/TRN-05, FIXPROGRAM P1/R1 |
| Frontier truncation (E-0911-B) | Yes (tail gate floor calibrated at 0.9756 admits it) | AUDIT_TRAIN TRN-17 |
| Forward member predicate (D20) | Yes, but it removes almost nothing | FWD-01, AUDIT_TRAIN TRN-06 |
| Cache holes | No (coverage gate in the driver) | HOL-02 |
| King window wrap (E-0909-A) | No (clamp builder) | CALIBER_STATUS |
| Metrics label switch | No (no builder reads metrics) | TIM-02, AUDIT_TRAIN TRN-08 |

## 5. Not checked

- Anything that exists only on jpline (unreachable since 09-04): the v1 canonical panel builder and its 2020-2021 caches, w3lane funding (UNVERIFIABLE); v1 is used here only as data.
- Declared settlement intervals for 2026-08 and 2026-09 API rows (FND-02): the 2026-08 fundingRate zips were not on pod2 and no download was made.
- The size of FEA-01, TRD-02, TRD-04, HOL-01 and UNI-01 on F10 predictions, books or state readings; no model was retrained and no arm re-run.
- fea89 (f8_fea89) column-level lineage, its funding-derived columns and its trend_288 global cumulative sum; legs Z24/ZFD beyond the ZFD finiteness count.
- Production-side live state (rolling.npz, aux ledger, seat seeds, F10 fea171 inputs) beyond reading shadow_loop_v3.py for the clock; owned by AUDIT_PROD.
- Frozen-close rows in the 1m premium index and spot archives used by r5 basis and L4 (only the 5m perp cache was measured).
- September 11-30 data: no research cache or panel contains it.
- Per-device exposure of RET-02 consumers to bound bars.
- Other OOF arrays (v4CLIP, v4sRAW, A0p, SLOW_v4e) for masks and coverage; NW/C0 inputs beyond A0's.
- Whether any committed RESULT quotes numbers built on superseded metas (meta_newprod.npz, _ext-based panels) after 09-09 beyond the device grep; only device references were classified.
- LOB, OI/metrics (L2), KRW (T7) and event (L3) datasets beyond confirming the metrics label handling.

## 6. Appendix A — inventory (pod2, measured by ad_inventory.py)

| Dataset | Path | sha256[:16] | Axis | Builder | Consumers |
|---|---|---|---|---|---|
| 5m cache (canonical) | `/workspace/data/dlnative_5m_wide829_f16_holefix2.npz` | 1d7f459dee434ec4 | 490,753 · 2022-01-01 → 2026-09-01T00:00 | holefix2 chain (caliber_program holefix2_daily.py) on _ext | v4 chain, P2, A0/NW, r12, r14, r21, audits |
| 5m cache (Sept extension) | `/workspace/data/dlnative_5m_wide829_f16_holefix2_x0910.npz` | 8115299410cd5e8d | 493,633 · 2022-01-01 → 2026-09-11T00:00 | r6_merge_cache.py 3227e4f5 (pod2 only) | T3, r12, r21 |
| 5m cache (pre-fix) | `/workspace/data/dlnative_5m_wide829_f16_ext.npz` | 72eb784949e90a09 | 490,753 · 2022-01-01 → 2026-09-01T00:00 | pod_merge_cache_ext.py de7a0661 | L2 alignment spectra, L4 symbol axis, gates |
| raw-return patch | `/workspace/review_scratch/raw_patch.npz` | adecf276bcfd89f4 | 952 · 2022-05-11 → 2026-08-24T13:00 | make_raw_patch.py 7716e7d3 | dlw_v4raw RAW targets, STEP1 gate |
| raw-return patch (Sept) | `/workspace/uplift_2026-09-11/r6/out/raw_patch_x0910.npz` | 94e8e8c119ea719a | 955 · 2022-05-11 → 2026-09-06T01:35 | r6_raw_patch_ext.py 808d2f66 (pod2 only) | dlw_v4raw_x0910 |
| hole cells | `/workspace/review_scratch/holefix2_cells.npz` | 6156f97a0709f073 | 1,422,720 · 2022-02-26 → 2026-09-01T00:00 | v4_hole_cells.py / holefix2 chain | STEP1, build_dev_v4 |
| 4h panel v1 canonical | `/workspace/data/wide_panel_4h_v1.npz` | f14bc33d78b24929 | 14,329 · 2020-01-31 → 2026-08-15T00:00 | jpline (UNVERIFIABLE) | splice prefix, panel_ext self-check |
| 4h panel v2ext | `/workspace/data/wide_panel_4h_v2ext.npz` | 5e67c0559daa904d | 10,039 · 2022-01-31 → 2026-08-31T00:00 | pod_panel_ext.py db7f0474 on _ext | every w10 replay (alias hist_v2), king PANEL_IN, T-series |
| 4h panel v3splice | `/workspace/data/wide_panel_4h_v3splice.npz` | c5d10f6ae31fa3f9 | 14,425 · 2020-01-31 → 2026-08-31T00:00 | pod_panel_splice.py a9c29141 | DL targets/fea82, legs, bundle export |
| 4h panel v2ext x0910 | `/workspace/uplift_2026-09-11/r6/out/wide_panel_4h_v2ext_x0910.npz` | 042478f7d8e9f947 | 10,099 · 2022-01-31 → 2026-09-10T00:00 | r6_panel_splice.py cccc5b6b (pod2 only) | T1, T2, T5, T5c, T5d, r12 |
| 4h panel v3splice x0910 | `/workspace/uplift_2026-09-11/r6/out/wide_panel_4h_v3splice_x0910.npz` | df847cd7ac4201a0 | 14,485 · 2020-01-31 → 2026-09-10T00:00 | r6_panel_splice.py cccc5b6b (pod2 only) | none since 09-09 |
| EMA state | `/workspace/fund_state_canoncont.json` | c1dbb41f7c9120d5 |  | pod_panel_splice.py a9c29141 | bundle export EMA_STATE_JSON |
| funding API pull | `/workspace/fund_aug.json.gz` | 8a9e771577602dd1 |  | fund_pull_pod.py fa665810 | panels, exporter, P2 ledger, L4/L4b |
| funding Sept pull | `/workspace/uplift_2026-09-11/r6/dl/r6_fund_sep.json.gz` | bfd9bc65c24916ac |  | r6_fetch_funding.py 298927ad (pod2 only) | x0910 panels, T5d |
| P2 settlement ledger | `/workspace/uplift_r2_2026-09-13/P2/work/ledger_full.npz` | bea6f5752772d54e | [2633090] | p2_prep_inputs.py | P2 S1/S2 |
| king features v4 | `/workspace/data/wide_fea_v4.npy` | 268f6c9c247cdf1f | [10182, 829, 82] | pod_fea_ext_clamp.py b9f9c728 | v4 king export, STEP2 |
| king meta v4 | `/workspace/data/wide_fea_v4_meta.npz` | 12ea42c4557093f1 | 10,182 · 2022-01-08 → 2026-08-31T20:00 | pod_fea_ext_clamp.py b9f9c728 | exporter, legs, build_dev_v4 |
| king features v2ext (in-service) | `/workspace/data/wide_fea_v2ext.npy` | f88b07205bf19870 | [10176, 829, 82] | pod_fea_ext.py 02157bda | in-service booster lineage, STEP2 reference |
| accounting meta v4 | `/workspace/review_scratch/refute_C6_2/altrun/meta_newprod_v4.npz` | 0e3c09ac86c727ac | 10,182 · 2022-01-08 → 2026-08-31T20:00 | build_dev_v4.py 0dbc2f60 (git 5749a821) | every w10 replay (alias wide_fea_hist_meta), P2 accounting |
| accounting meta x0910 | `/workspace/uplift_2026-09-11/r6/out/meta_newprod_v4_x0910.npz` | a8eb359701c71acf | 10,242 · 2022-01-08 → 2026-09-10T20:00 | r6_dev_tree.py faffd726 (pod2 only) | T1, T2, T3, T5c, r12 |
| DL targets RAW | `/workspace/dlw_v4raw/data/dlw_targets.npz` | d1976cf6246cdc25 | 10,212 · 2022-01-03 → 2026-08-31T20:00 | pod_dlw_targets_raw.py d7c52823 | F10 v4 training, legs, F10 alignment in replays |
| DL targets CLIP | `/workspace/dlw_hf3/data/dlw_targets.npz` | 720f03a447278b4b | 10,212 · 2022-01-03 → 2026-08-31T20:00 | pod_dlw_targets_raw.py d7c52823 (no patch) | STEP1 reference |
| DL targets in-service | `/workspace/dlw_ext/data/dlw_targets.npz` | 31d043e8f160a1d4 | 10,206 · 2022-01-03 → 2026-08-30T20:00 | pod_dlw_targets_ext.py c21683ee | in-service F10, A0 F10 alignment, P2 |
| DL fea82 | `/workspace/dlw_v4raw/data/dlw_fea82.npz` | 40608701cad1aea1 | [2753289, 82] | pod_dlw_features_ext.py e86725cc | F10 v4 |
| DL fea89 | `/workspace/f8_v4/data/f8_fea89.npz` | f7363889fa823a97 | [2753289, 89] | pod_f8_build_ext.py f606bffa | F10 v4 |
| F10 legs v4 | `/workspace/f8_v4/data/f10v2_legs.npz` | c535decd6524b091 | 10,212 · 2022-01-03 → 2026-08-31T20:00 | pod_legs_v4b.py 6f0f0095 (git 3f058a7c) | F10 v4 trainer (V2) |
| king OOF v4 | `/workspace/review_scratch/king_v4/SLOW_v4.npy` | dde19142d017c37d | [10182, 829] | pod_export_bundle_v4.py 23b1a5c7 (bundle v4) | A1x, P2 king OOF, r-series |
| king OOF v3 on v4 axis | `/workspace/review_scratch/king_v4/SLOW_v3_on_v4axis.npy` | 647673183e6af44a | [10182, 829] | build_dev_v4.py 0dbc2f60 | A0 king leg |
| F10 OOF A0 | `/workspace/review_scratch/health_check/dev_v4/f8_2026-08-22/preds/f10_A0_s42.npy` | ff109711f5526c68 | [10212, 829] | build_dev_v4.py (align f8_ext yearly OOF) | A0 F10 leg |
| F10 OOF v4RAW | `/workspace/review_scratch/health_check/dev_v4/f8_2026-08-22/preds/f10_v4RAW_s42.npy` | 58d64a6ff9684589 | [10212, 829] | merge_mwf_v4b.py | A1x, P2 F10 injection |
| universe mask CRYPTO | `/workspace/review_scratch/health_check/masks/umask_UPIT_CRYPTO.npz` | 47d87b5165b695a7 | 10,039 · 2022-01-31 → 2026-08-31T00:00 | build_crypto_mask.py 43ebca0d on build_umask.py (U-PIT) | every m1 replay, P2 PIT universe |
| A0 reference book | `/workspace/uplift_2026-09-11/r3k/arms/A0_PWR230k_s42.npz` | 352ac36fb3195327 | [10039, 829] | w10_sleeve.py b88e35a4 | ~300 paired verdicts, T-series, P2 |

## 7. Appendix B — dependency matrix (dataset token × research line; number of devices committed since 09-09, audit devices excluded)

| Token | total | v4 chain | rt09 other | parity/phase2 | parity/devices | r1 (uplift round 1) | r2/T1 | r2/T2 | r2/T3 | r2/T4 | r2/T4b | r2/T5 | r2/T5c | r2/T5d | r2/T6 | r2/T7 | r2/T8 | r3/L2 | r3/L4 | r3/L4b | multi_asset/exports/live |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| cache_holefix2 | 54 | 26 | 2 | 5 |  | 21 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| cache_holefix2_x0910 | 8 |  |  | 1 |  | 6 |  |  | 1 |  |  |  |  |  |  |  |  |  |  |  |  |
| cache_holefix_round1 | 11 | 6 | 5 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| cache_ext_prefix | 16 | 7 | 4 |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 4 | 1 |  |  |
| cache_holefix_raw | 1 |  | 1 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| producer_rolling_cache | 48 | 6 |  | 4 | 8 | 18 |  |  |  | 4 | 5 | 1 | 1 |  |  |  |  |  |  |  | 1 |
| raw_patch | 10 | 9 | 1 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| raw_patch_x0910 | 0 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| panel_v1 | 2 |  |  |  |  |  |  |  |  | 2 |  |  |  |  |  |  |  |  |  |  |  |
| panel_v2ext | 133 | 12 | 3 | 3 |  | 97 | 5 | 2 |  | 5 | 1 | 2 |  |  |  | 1 | 1 | 1 |  |  |  |
| panel_alias_hist_v2 | 110 | 2 | 2 | 1 |  | 95 | 2 | 3 |  | 1 |  | 2 | 2 |  |  |  |  |  |  |  |  |
| panel_v3splice | 17 | 12 | 1 |  |  | 4 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| panel_v2ext_x0910 | 19 |  |  |  |  | 6 | 4 | 2 | 1 | 1 |  | 2 | 2 | 1 |  |  |  |  |  |  |  |
| panel_v3splice_x0910 | 0 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| panel_v2holefix | 3 |  | 1 |  |  | 2 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| king_meta_v4 | 38 | 26 |  | 4 |  | 6 | 1 |  |  | 1 |  |  |  |  |  |  |  |  |  |  |  |
| king_fea_v4 | 23 | 19 |  |  |  | 3 | 1 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| king_meta_v2ext | 38 | 17 | 9 | 1 |  | 6 | 1 |  |  | 3 | 1 |  |  |  |  |  |  |  |  |  |  |
| king_v4_x0910 | 1 |  |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  |  |  |  |  |
| king_v4e | 8 | 8 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| meta_alias_hist | 94 | 3 | 1 | 1 |  | 79 | 2 | 3 |  | 1 |  | 2 | 2 |  |  |  |  |  |  |  |  |
| acct_meta_v4 | 83 | 2 |  | 3 | 2 | 62 | 3 | 2 |  | 2 |  | 1 | 1 |  |  | 1 | 1 | 3 |  |  |  |
| acct_meta_v4_x0910 | 22 |  |  |  |  | 9 | 5 | 2 | 1 | 1 |  | 1 | 3 |  |  |  |  |  |  |  |  |
| acct_meta_pre_v4 | 5 | 1 | 4 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| dl_v4raw | 102 | 34 |  | 5 |  | 55 | 4 | 1 |  | 2 |  | 1 |  |  |  |  |  |  |  |  |  |
| dl_hf3_clip | 43 | 41 | 1 |  |  | 1 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| dl_ext | 45 | 23 | 3 | 5 |  | 11 | 2 |  |  |  | 1 |  |  |  |  |  |  |  |  |  |  |
| dl_x0910 | 14 |  |  |  |  | 10 |  |  | 1 | 1 |  |  | 2 |  |  |  |  |  |  |  |  |
| fea89 | 54 | 34 | 2 | 1 | 1 | 10 |  |  |  | 1 | 5 |  |  |  |  |  |  |  |  |  |  |
| legs | 22 | 21 |  |  |  | 1 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| oof_king_v4 | 55 | 3 |  | 6 |  | 42 | 1 | 1 |  | 1 |  | 1 |  |  |  |  |  |  |  |  |  |
| oof_king_v3_on_v4 | 86 | 3 |  | 6 |  | 64 | 2 | 3 |  | 2 |  | 2 | 1 |  | 1 |  | 1 | 1 |  |  |  |
| oof_king_x0910 | 8 |  |  |  |  | 7 |  |  |  |  |  |  | 1 |  |  |  |  |  |  |  |  |
| oof_alias_hist | 49 | 2 |  | 1 |  | 37 | 2 | 2 |  | 1 |  | 2 | 2 |  |  |  |  |  |  |  |  |
| bundle_pinned | 31 | 18 | 1 | 1 |  | 9 |  |  |  | 1 | 1 |  |  |  |  |  |  |  |  |  |  |
| oof_f10_A0 | 90 | 3 |  | 4 |  | 75 | 2 | 2 |  | 1 |  | 1 | 1 |  | 1 |  |  |  |  |  |  |
| oof_f10_v4RAW | 20 | 2 |  | 6 |  | 12 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| oof_f10_V2MAIN_yearly | 45 | 13 |  | 1 |  | 27 | 1 | 1 |  |  |  | 1 | 1 |  |  |  |  |  |  |  |  |
| umask_crypto | 150 | 6 | 3 | 5 |  | 120 | 5 | 4 |  | 1 |  | 1 | 1 |  | 1 | 1 | 1 | 1 |  |  |  |
| umask_upit | 2 |  |  |  |  | 2 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| umask_frozen_or_pins | 24 | 9 | 2 | 3 |  | 9 |  |  | 1 |  |  |  |  |  |  |  |  |  |  |  |  |
| fund_aug | 15 | 6 |  | 2 |  | 3 |  |  |  |  |  |  |  | 1 |  |  |  |  | 1 | 2 |  |
| fund_sep_r6 | 1 |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  |  |  |  |
| ledger_full_p2 | 4 |  |  | 4 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| funding_zips | 6 | 3 |  | 2 |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  |  |
| bundle_funding_seed | 15 | 6 |  | 1 | 1 | 2 |  |  |  | 3 | 2 |  |  |  |  |  |  |  |  |  |  |
| metrics_archive | 2 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 2 |  |  |  |

## 8. Reproduction notes

- Devices A-D, F-H: `bash docs/audit_pipeline_2026-09-13/devices_data/run_pod2.sh sync` then `run_pod2.sh <A|B|C|D|F|G|H>` (pod2, `env -i`, nice 19); E: `run_pod2.sh E` (Mac, git objects); receipts via `run_pod2.sh fetch`.
- Positive controls read before any finding: C3 member lists and king label window reproduced bitwise; B PC2 r6 funding rule reproduced the x0910 tail exactly; D kline columns equal away from hole neighbourhoods; H frozen-row signature 100%.
- Render: `python3 docs/audit_pipeline_2026-09-13/devices_data/build_audit_data.py` (reads receipts only).
