# P9 declared-interval table — which rows are exact and which are likely (answer to FX-DATA; readable without the exchange)
Table: `P9_declared_interval_table_2026-07-01_2026-09-13T12Z_zipszips_2026-08.csv.gz`, sha256 366763a4aae854b2415fb461334efe95c1a74f93fc9e81c112c6138b16ec3197. The generator is `fx/p9_declared_interval_table.py` (fx_prod d49f1ef); the column definitions are in its docstring.

**Exact** = column `iv_best` is non-null. Column `iv_best_source` says why:
- `zip`: the exchange's monthly zip `funding_interval_hours`. This is the declared value (months pulled: ≤ 2026-08).
- One or more exact rules, joined with `+`. Each rule equals the zip on every scored row of full history (2020 through 2026-07, 2.52M rows; with August added the result stays 100%):
  - `structure_steady`: snap(back gap) == snap(fwd gap). 2,625,081/2,625,083; the two misses are the XAG/XAU 2026-01-30 exchange anomalies.
  - `interest_signature`: rate == 1.25e-5·iv for exactly one candidate in {snap back, snap fwd}. 694/694, plus 423/423 at series edges.
  - `cap_signature_4h_to_1h` / `cap_signature_8h_to_1h`: |rate| == 0.02, back gap 4h/8h, fwd gap 1h. 174/174 + 27/27.
  - `structure_last_1h_before_gap2` / `…gap3`: the last 1h row before a 2–3h gap. 53/53 + 44/44.

**Not exact** = `iv_best` null, and `iv_best_source` is either `unresolved_<regime>` (transition or edge) or `conflicting_rules:…`.
- **Likely** = additionally `iv_likely` is non-null. `iv_likely_support` gives the rule and its hit rate over full history:
  - `structure_gap3_into_longer`: 40/41 in the generator's scored set; 42/43 on the v4 evaluation.
  - `structure_gap2_into_longer`: 52/62; 55/65 on v4.
  These are below 100%: use them as a best guess only, never as a label to correct against.
- Rows with `iv_best` and `iv_likely` both null have no usable label without the next monthly zip.

Examples in the live window:
- T 09-06 00Z and SKR 09-07 20Z: unresolved until the September zip.
- ZKC 09-02 20Z and SOPH 09-11 12Z: not exact; likely 4.
- COTI 08-31 20Z and ONG 08-25 08Z: exact through the August zip (4).

Producer columns: `iv_producer` is the stored label. `producer_vs_best` ∈ {match, mismatch, unresolved, not_in_producer_ledger} compares it with `iv_best` only, so exact rows only.
