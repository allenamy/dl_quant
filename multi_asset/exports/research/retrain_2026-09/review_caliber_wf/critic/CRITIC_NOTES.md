# Critic notes (completeness) — 2026-09-04
Checked against: wf_results_round1.json (16 entries: 6 tracers + 10 refuters; C3_0/C4_0/C4_1/C6_0/C6_1 present only as scratch dirs),
refute_C6_{0,1,2} outputs, gt/*.json, docs RESULT_caliber_revalidation/truth, AUDIT_live_vs_replay, ERROR_LEDGER L373/L397, STATE.md,
w10_universe.py L17-30/L116/L262-312, regime_dash.py L53-121, tests_target_live_output.py L278-289, anchor_loop.py L1466-1471.
Unit chain re-computed: 0.4566/0.791=0.5773 ok; x2190=12.65% ok; 0.4065/0.791=0.514 ->11.3% ok; 2614/0.791=3305bps=33.1% ok but mixes
3-yr gross with a 2024-25 DD (2024 gross 0.847 -> 30.9%/gross -> 61.7%@2x; const-gross 31.6% -> 63.1%); all cumsum, not compounded.
Key contradictions found:
- Worst month: draft "no one computed" vs R-C6.0 recompute_out.txt L131-134 (2024-11 -717 / 2025-01 -634.5 / 2026-08 -252.4), REPORT.md 9.3, pod_units_table.py, RESULT_caliber_revalidation table.
- 2022/2023 exist in RECEIPT_EX by_year_ex (fixed -0.12/-0.381; dyn +0.313/-0.373; Pi -0.098/-0.404) but king NaN & F10 0/0.226 -> not stated.
- Carry: live funding -1.909+-0.689 bps/anchor (gt) vs replay carry_ex 0.34/0.68/0.92 (fixed) ; RESULT_revalidation L64: 0.77 vs 1.98 (27 anchors); AUDIT row 11: 0.5/2.65/1.2. Not in draft.
- R-C2.2 book numbers (1.49 vs 0.79) are column `net`, arm S0; §5 uses `net_ex`, arm d30_n2_c42.
- R-C3.0 (833/950 bitwise expm1) vs R-C3.1 (0/950 exact; label rests on code line) unreconciled.
- gt daily: 5 six-window days (09-03 residual -219.8 excluded silently; 08-27 with $5.4k deposit included).
- sigma ladder (live executor sizing, deployed 09:34Z) + AUDIT §3 / RESULT_allweather (jp_allweather.py on w10 series made 07:00Z = CAL=simple) not covered.
- STATE.md §4 still says expm1 rule; draft rule #1 edits only CLAUDE.md/ledger.
