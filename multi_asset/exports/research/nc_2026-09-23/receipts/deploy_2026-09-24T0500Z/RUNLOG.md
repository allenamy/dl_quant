# RUNLOG NC deploy 2026-09-24T05:00:33Z BK=/Users/haosiyu/cc_tmp/nc_deploy_20260924T0500Z
## §0.3 start 05:00:33
--- quiet window
{ "now_utc": "2026-09-24T05:00:33Z", "anchor_N_utc": "2026-09-24T04:00:00Z", "minutes_since_N": 60.6, "window": "[N+60m, N+220m]", "remaining_min": 159.4, "open": true, "reason": "open", "override": null, "last_anchor_start_utc": "2026-09-24T04:00:00Z", "last_anchor_done_utc": "2026-09-24T04:54:21Z", "anchor_in_progress": false, "stale_start": false}
qw rc=0
--- preflight
NC_INSTALL PREFLIGHT_PASS VERDICT=NO_DEPLOY USER_OVERRIDE=053d50f4ab034ca5e311600b10864d0e30046f2aedf2fca369ebecdc8d032b6b {"contract_sha256": "00238e4b865e235cc90ea7966b264a053842d4151744bb14b89f80ffaddaa33d", "files": 17, "verdict": {"bound": true, "VERDICT"
rc=0
--- executor HEAD
b66257b
--- book pins
8d79186b 351ae26b None
--- seed pack / crypto
600d760eed619c11651d136c60197b6e6a18b9d37db1ff5b0769dc55c87d101e  /Users/haosiyu/cc_tmp/nc_20260923/seed_pack_0919.npz
2323623fda9333710f5834911ab629377ab8c12b056f40ccfc9f7033c0c1f6f1  /Users/haosiyu/cc_tmp/news_20260923/package_NEW_S/crypto_P1_members_2025H2on.npz
--- sidecar disabled?
(grep rc=1; 1 = no line)
--- anchor done
2026-09-24T04:54:21Z anchor done rc=0
--- watchdog
watchdog tripped_at None reduce_only False | last_eval tripped False triggers [] 2026-09-24T04:47:46Z
last anchors row nominal 1790222400 opening_halted False
--- ALARM 4-2
{"ts": "2026-09-06T16:39:31Z", "severity": "HIGH", "msg": "STOP-LOSS TRIPPED \u2014 book flattened, reduce-only engaged", "reason": "\u00a74-2 single-day loss -4.28% of EQUITY, worse than -4.0%", "err
{"ts": "2026-09-06T20:39:29Z", "severity": "HIGH", "msg": "STOP-LOSS TRIPPED \u2014 book flattened, reduce-only engaged", "reason": "\u00a74-2 single-day loss -4.28% of EQUITY, worse than -4.0%", "err
(grep rc=0)
--- handoff check
HANDOFF_CHECK OK {"FROZEN_VERDICT": "NO_DEPLOY", "USER_OVERRIDE": "053d50f4ab034ca5e311600b10864d0e30046f2aedf2fca369ebecdc8d032b6b", "executor_pins": {"booster_sha_pin": "700d9e7b7ee992a786528477ff90
rc=0
## §0.3 end 05:00:35
## A0 start 05:01:12
--- executor before: HEAD b66257b6e86c18ed27c7971aa7fed64a69d71444 book.json 484e3728e9e9da40b68e846427f9abf3d4efbe54dcec71d39a7746a85288f76e
--- launchctl list before
13654	0	com.hsy.combolive
801	0	com.hsy.sidecar
13652	0	com.hsy.shadowloop
-	0	com.hsy.comboparity
-	0	com.hsy.combosnap
wait com.hsy.combosnap: iterations=1 (pid still present after loop: 0)
wait com.hsy.comboparity: iterations=1 (pid still present after loop: 0)
bootout com.hsy.shadowloop rc=0 05:01:12
bootout com.hsy.combolive rc=0 05:01:12
bootout com.hsy.combosnap rc=0 05:01:12
bootout com.hsy.comboparity rc=0 05:01:12
bootout com.hsy.sidecar rc=0 05:01:12
disable com.hsy.sidecar rc=0
上一行必须为空 (egrep rc=0)
上一行必须为空(平价锁不在) ls rc=1
--- launchctl list after
(grep rc=1; 1 = none listed)
print com.hsy.shadowloop rc=113 (non-zero = not loaded)
print com.hsy.combolive rc=113 (non-zero = not loaded)
print com.hsy.combosnap rc=113 (non-zero = not loaded)
print com.hsy.comboparity rc=113 (non-zero = not loaded)
print com.hsy.sidecar rc=113 (non-zero = not loaded)
--- print-disabled sidecar line
		"com.hsy.sidecar" => disabled
--- executor after: HEAD b66257b6e86c18ed27c7971aa7fed64a69d71444 book.json 484e3728e9e9da40b68e846427f9abf3d4efbe54dcec71d39a7746a85288f76e
## A0 end 05:01:13
--- A0 extra: old PIDs 13652 13654 801 alive?
pid 13652 gone
pid 13654 gone
pid 801 gone
--- process scan (self-match excluded)
84766 ugrep -G --ignore-files --hidden -I --exclude-dir=.git --exclude-dir=.svn --exclude-dir=.hg --exclude-dir=.bzr --exclude-dir=.jj --exclude-dir=.sl -E shadow_loop_v3|combo_stage|combo_live_daemon|sidecar_daemon|sidecar_blend|combo_state_snapshot|combo_parity
(matches above; empty = none) 05:01:20
## A1 start 05:01:44
NC_FETCH_LIST {"out": "/Users/haosiyu/cc_tmp/nc_deploy_20260924T0500Z/fetch_list.json", "n": 522, "not_in_symbols_live": 72, "anchor": 1790222400, "sha256": "3c8455803245262ecd08ece22fd2c6d029629ac196186423281dcf073bc656e6"}
fetch_list rc=0
{ "now_utc": "2026-09-24T05:01:44Z", "anchor_N_utc": "2026-09-24T04:00:00Z", "minutes_since_N": 61.7, "window": "[N+60m, N+220m]", "remaining_min": 158.3, "open": true, "reason": "open", "override": null, "last_anchor_start_utc": "2026-09-24T04:00:00Z", "last_anchor_done_utc": "2026-09-24T04:54:21Z"

qw rc=0  (必须 0)
axis_end=1789776000
--- nc_deploy_fetch start 05:01:48
NC_DEPLOY_FETCH {"device_sha256": "d67afe66e956d86e9117b25d005560034075aca2b38878bf5759de0197afa07e", "axis_end": 1789776000, "last_anchor": 1790222400, "new_names": 72, "rows": 107136, "bound_cells_after_axis": 3, "boundary_entries": 3, "failed": [], "own_weight": 723, "used_weight_1m_max": 600, "VERDICT": "PACKED"}
nc_deploy_fetch rc=0 end 05:02:54
--- A1 measured: 147 requests (all /fapi/v1/klines, 74 symbols), own_weight 723 (= 144 x 5 + 3 x 1), IP used_weight_1m peak 600 (requests.jsonl), 0 rows with status/error, bound cells after axis 3, raw finite 3/3; 05:03:16
304c1f0123c9a1ad1dd39bda9fd24d336ac10d57bf1cd8ecd0351cbed6ee3030  /Users/haosiyu/cc_tmp/nc_deploy_20260924T0500Z/live_pack.npz
3c8455803245262ecd08ece22fd2c6d029629ac196186423281dcf073bc656e6  /Users/haosiyu/cc_tmp/nc_deploy_20260924T0500Z/fetch_list.json
## A2 start 05:03:45
NC_SEED SEEDED {"rows_from_seed_pack": 10032, "post_axis_ch0_cross_gap_set_nan": 0, "live_pack_rows_filled": 107136, "post_axis_bound_unresolved": [], "boundary_cells": 15, "ledger_rows_le_axis_agree": 173338, "ledger_rows_le_axis_disagree": 0, "events_advanced_after_axis": 14680, "ledger_rows_le_axis_missing_in_replay": 0, "missing_in_replay_first": [], "replay_rows_in_production_coverage": 173338, "replay_rows_missing_in_production_in_coverage": 0, "replay_rows_missing_in_production_in_coverage_list": [], "replay_rows_missing_in_production_in_coverage_by_name": {}, "replay_rows_missing_in_production_out_of
nc_seed_state rc=0 end 05:04:38
A2 extra counts (computed by the integrator from prod rolling.npz 770b90a1 vs seeded rolling.npz a32075b8; not emitted by nc_seed_state):
{
 "window": [
  1786766700,
  1790222400
 ],
 "axis_end": 1789776000,
 "rows_pre_axis": 10032,
 "rows_post_axis": 1488,
 "crypto_cols": 680,
 "ch0_crypto_pre_axis": {
  "set_nan(prod finite -> seeded NaN)": 0,
  "filled(prod NaN -> seeded finite)": 1480361,
  "value_changed(both finite)": 0,
  "both_nan": 826999
 },
 "ch0_crypto_post_axis": {
  "set_nan(prod finite -> seeded NaN)": 0,
  "filled(prod NaN -> seeded finite)": 107136,
  "value_changed(both finite)": 0,
  "both_nan": 235104
 },
 "ch0_noncrypto_all_rows_bytes_equal": true,
 "boundary_table": {
  "entries": 15,
  "in_window": 15,
  "pre_axis": 12,
  "post_axis": 3
 },
 "bound_cells_in_ch0(|ch0|==f16(0.3), crypto)": 15
}
A2 fill split: {"pre_axis_filled_crypto_in_symbols_live": 0, "pre_axis_filled_crypto_not_in_symbols_live": 1480361, "names_in_symbols_live_with_pre_axis_fills": 0, "post_axis_filled_crypto_in_symbols_live": 0, "post_axis_filled_crypto_not_in_symbols_live": 107136, "crypto_names_in_symbols_live": 450, "crypto_names_not_in_symbols_live": 230}
RECEIPT NOTE (lead 2026-09-24): the filled names are the crypto names on the 829 axis outside symbols_live (incl. delisted); their history comes from the seed pack; whether they become members is decided per anchor by the liveness gate.
  measured: crypto names outside symbols_live = 230; with >=1 filled cell = 199; with 0 filled cells = 31 ['1000BTTCUSDT', 'AERGOUSDT', 'AKROUSDT', 'ANCUSDT', 'ANTUSDT', 'AUDIOUSDT', 'BDXNUSDT', 'BLUEBIRDUSDT', 'BTCSTUSDT', 'BTSUSDT']
  of the 230, in the A1 fetch list (currently TRADING) = 72
## A3 start 05:06:01
{ "now_utc": "2026-09-24T05:06:01Z", "anchor_N_utc": "2026-09-24T04:00:00Z", "minutes_since_N": 66.0, "window": "[N+60m, N+220m]", "remaining_min": 154.0, "open": true, "reason": "open", "override": n

NC_INSTALL PREFLIGHT_PASS VERDICT=NO_DEPLOY USER_OVERRIDE=053d50f4ab034ca5e311600b10864d0e30046f2aedf2fca369ebecdc8d032b6b {"contract_sha256": "00238e4b865e235cc90ea7966b264a053842d4151744bb14b89f80ffaddaa33d", "files": 17, "verdict": {"bound": true, "VERDICT": "NO_DEPLOY", "USER_OVERRIDE": "053d50f4ab034ca5e311600b10864d0e30046f2aedf2fca369ebecdc8d032b6b", "export_manifest_sha256": "64abda0d8793a1fc44235b3b8057302ec24de19b3c827f70961753918d86efd9", "statement": "VERDICT=NO_DEPLOY USER_OVERRIDE=053d50f4ab034ca5e311600b10864d0e30046f2aedf2fca369ebecdc8d032b6b; a user permission recorded against the frozen verdict, not an admission; FREEZE \u00a72 unamended"}, "package": "PASS", "seeded": {"rows": 11520, "axis_end": 1789776000, "noncrypto_cells_differing": 0, "pre_axis_crypto_cells_differing_from_pack": 0, "post_axis_ch1_6_cells_differing_outside_live_filled": 0, "post_axis_rows_filled_where_production_had_none": 107136, "post_axis_ch0_changed": 0, "post_axis_ch0_changed_to_non_nan": 0, "bound_cells_crypto": 15, "bound_cells_missing_from_table": [], "boundary_table_cells": 15, "seed_counts": {"rows_from_seed_pack": 10032, "boundary_cells": 15, "post_axis_ch0_cross_gap_set_nan": 0, "live_pack_rows_filled": 107136, "events_advanced_after_axis": 14680, "replay_rows_missing_in_production_in_coverage": 0, "replay_rows_in_production_coverage": 173338, "member_history_anchors_from_seed": 209, "member_history_anchors_recomputed": 31, "fetch_n": 522}}}
preflight rc=0 05:06:05
--- apply start 05:06:09
NC_INSTALL installed_not_started VERDICT=NO_DEPLOY USER_OVERRIDE=053d50f4ab034ca5e311600b10864d0e30046f2aedf2fca369ebecdc8d032b6b {"module_sha256": "a68c7a5f0c6e8e0af89eda0307ab0b9ad6b38fa82810f4d04c1ab99deb1d510c", "state_files": ["aux.json", "boundary_raw.npz", "leg_returns_live.json", "members_hist.npz", "rolling.npz"], "generation_anchor": 1790222400, "last_anchor": 1790222400}
apply rc=0 05:06:17
--- version probe after-a3 05:06:22
after-a3 contract 00238e4b865e235cc90ea7966b264a053842d4151744bb14b89f80ffaddaa33d files=17 home=/Users/haosiyu
  OK  regime_dash/regime_dash.py: measured=8210fe733a9f73351f1f268631c99c9476e86d49c901067db5bc90f6e5c730ce compared_with=8210fe733a9f73351f1f268631c99c9476e86d49c901067db5bc90f6e5c730ce
  OK  wide_shadow/fea171/beta_overlay_producer.py: measured=b77c180d69170988780566e19d0ee4a0f85af25a9b9e9be08b6e4a386095fb58 compared_with=b77c180d69170988780566e19d0ee4a0f85af25a9b9e9be08b6e4a386095fb58
  OK  wide_shadow/fea171/combo_stage.py: measured=363dd8c8876ab29eb9c098fe47a40a37bd6c7c912d9cb6cf2cbc7a17b87e9f65 compared_with=363dd8c8876ab29eb9c098fe47a40a37bd6c7c912d9cb6cf2cbc7a17b87e9f65
  OK  wide_shadow/fea171/combo_state_snapshot.sh: measured=58e58bd11141daed1dfdd703c05df942223b95c9e7fc6010bfac6d61be72b915 compared_with=58e58bd11141daed1dfdd703c05df942223b95c9e7fc6010bfac6d61be72b915
  OK  wide_shadow/fea171/combosnap/combo_parity_replay.sh: measured=d49cd8345f9dae0a83ef18aa10c48a5b27b7bf27c7c20b335b03f7ce59f73922 compared_with=d49cd8345f9dae0a83ef18aa10c48a5b27b7bf27c7c20b335b03f7ce59f73922
  OK  wide_shadow/fea171/combosnap/generation_files.py: measured=925481d0d77562020d51b30ee51e4fdccff35a86c497b6533a8ce67b194b48ac compared_with=925481d0d77562020d51b30ee51e4fdccff35a86c497b6533a8ce67b194b48ac
  OK  wide_shadow/fea171/dlw_features.py: measured=874c18705c3027a2f1aaa50bff52d11edcb0f984e5945e8755b6c30890ce2247 compared_with=874c18705c3027a2f1aaa50bff52d11edcb0f984e5945e8755b6c30890ce2247
  OK  wide_shadow/fea171/f10_live_s42_np.npz: measured=3d7d050f78a98cb09586ac9c75c0c12526bfd54b5d9f4c6d151f6121b333139f compared_with=3d7d050f78a98cb09586ac9c75c0c12526bfd54b5d9f4c6d151f6121b333139f
  OK  wide_shadow/fea171/f8_higher_order_features.py: measured=98bc036d98a1b2385dd9e035a4803e03426047ba058d30e93df959b3f3788fb6 compared_with=98bc036d98a1b2385dd9e035a4803e03426047ba058d30e93df959b3f3788fb6
  OK  wide_shadow/fea171/feature_cache_identity.py: measured=e4ec55d1e3d4ca0df1f0a258b98849eb545fb6161b0fab1cc516248a3b090af2 compared_with=e4ec55d1e3d4ca0df1f0a258b98849eb545fb6161b0fab1cc516248a3b090af2
  OK  wide_shadow/fea171/nc_contract.py: measured=316a0b9bcf1461401740ebd79a3292a9bfcdc49d56f111219ff6e126110650cb compared_with=316a0b9bcf1461401740ebd79a3292a9bfcdc49d56f111219ff6e126110650cb
  OK  wide_shadow/fea171/stable_trend_reference.py: measured=01bf8b3d35a23b6599ceddcc849dbbbbb85eff5eceebfe1a5a045fe9ca8b79ae compared_with=01bf8b3d35a23b6599ceddcc849dbbbbb85eff5eceebfe1a5a045fe9ca8b79ae
  OK  wide_shadow/fea171/tradability.py: measured=a9fad82ce26845a6f3d61cfa9077a6286949346e92c1fbfea17a663363264914 compared_with=a9fad82ce26845a6f3d61cfa9077a6286949346e92c1fbfea17a663363264914
  OK  wide_shadow/shadow_bundle/MANIFEST.json: measured=d4290418f398466d00582600f343d0ea72f1348ef0ae45f547a89dac74490e53 compared_with=d4290418f398466d00582600f343d0ea72f1348ef0ae45f547a89dac74490e53
  OK  wide_shadow/shadow_bundle/crypto_axis.json: measured=a4df6824fbcdf613eba5802c3a44c6dc6514e7d1a6f8df288382b1494dc01d2f compared_with=a4df6824fbcdf613eba5802c3a44c6dc6514e7d1a6f8df288382b1494dc01d2f
  OK  wide_shadow/shadow_bundle/slow2026.txt: measured=700d9e7b7ee992a786528477ff9007ec93c3d16654f1abc52766e5406654020d compared_with=700d9e7b7ee992a786528477ff9007ec93c3d16654f1abc52766e5406654020d
  OK  wide_shadow/shadow_loop_v3.py: measured=a68c7a5f0c6e8e0af89eda0307ab0b9ad6b38fa82810f4d04c1ab99deb1d510c compared_with=a68c7a5f0c6e8e0af89eda0307ab0b9ad6b38fa82810f4d04c1ab99deb1d510c
VERSION_PROBE after-a3 OK n=0
probe rc=0
--- backup SHA256SUMS entries:       15
receipt stage installed_not_started VERDICT NO_DEPLOY USER_OVERRIDE 053d50f4ab034ca5e311600b10864d0e30046f2aedf2fca369ebecdc8d032b6b completed_utc 2026-09-24T05:06:17Z backup {'entries': 15, 'sha256sums': 'f8a3e1ea6e660f6f3011d91fb205617697818fea0f00d01b7c03391f817572b6'} producer_load {"module_sha256": "a68c7a5f0c6e8e0af89eda0307ab0b9ad6b38fa82810f4d04c1ab99deb1d510c", "state_files": ["aux.json", "boundary_raw.npz", "leg_returns_live.json", "members_hist.npz", "rolling.npz"], "generation_anchor": 1790222400, "last_anchor": 1790222400}
--- executor untouched: HEAD b66257b6e86c18ed27c7971aa7fed64a69d71444 book.json 484e3728e9e9da40b68e846427f9abf3d4efbe54dcec71d39a7746a85288f76e
## A3 end 05:06:22
## A4 start 05:07:11 XC=/Users/haosiyu/cc_tmp/nc_exec_20260924T0507Z
clone+config rc=0
XC HEAD b66257b
484e3728e9e9da40b68e846427f9abf3d4efbe54dcec71d39a7746a85288f76e  /Users/haosiyu/cc_tmp/nc_deploy_20260924T0500Z/book.json.pre_nc
book backup+cmp rc=0
after ff-merge XC HEAD 5b3d89c
5b3d89c tests_beta_overlay: the non-DRY stub snapshot carries the three balance fields the daily_nav
b81c4cb M3 round-10 review fixes (R10-A01 leverage budget + cond4b, R10-A02 overlay-net caliber, mod
80ae104 M3: correct two stale comments in live/beta_overlay.py (comment-only; compiled code byte-ide
4dd7d53 M3: align BTC's eligibility with the evaluated M3b rule exactly (quant_research AMENDMENT_1 
c71ca7a M3 AMENDMENT_1 (quant_research 912788743, coordinator's constraint): BTC's 2x-minNotional el
11aa8d1 M3 follow-up (full offline battery round 1 on b7a44eb): declare live/beta_overlay.py in the 
8725e7d M3 BTC-beta overlay leg on the EXECUTED book (PREREG quant_research docs/PREREG_m3_beta_over
anchor_report patch rc=0
release archive rc=0
NC_EXEC_CONFIG OK {"pins": ["8d79186b->700d9e7b", "351ae26b->3d7d050f"], "beta_overlay": {"mode": "off->shadow", "max_combined_leverage": "None->2.5"}, "producer_contract": "None->nc_v1"}
nc_exec_config rc=0
--- git diff --stat
 config/book.json                    | 10 ++++++----
 live/tests_anchor_report_builder.py | 25 +++++++++++++++++++++++-
 ops/anchor_report.py                | 39 ++++++++++++++++++++++++++++++-------
 3 files changed, 62 insertions(+), 12 deletions(-)
--- git status --porcelain
 M config/book.json
 M live/tests_anchor_report_builder.py
 M ops/anchor_report.py
?? ops/producer_release/20260923_nc/
--- A4 part1 end 05:07:18
--- rsync state 05:07:25
rsync rc=0 05:07:30
--- safe_commit start 05:07:32
── 1/5 拉取远端(显式检查, 不经管道)
From https://github.com/allenamy/dl_quant_live
 * branch            main       -> FETCH_HEAD
  ✓ 已是最新
── 2/5 检查显式路径存在(只对新文件 intent-to-add —— 见第 4 步为什么)
 config/book.json                                   |  10 +-
 live/tests_anchor_report_builder.py                |  25 +-
 ops/anchor_report.py                               |  39 +-
 .../20260923_nc/INSTALL_CONTRACT.json              | 179 ++++++++
 .../20260923_nc/PATCH_RECEIPT.json                 | 469 +++++++++++++++++++++
 5 files changed, 710 insertions(+), 12 deletions(-)
── 3/5 离线隔离验收 runner(全绿才提交)
----------------------------------------------------------------
ACCEPTANCE: ALL GREEN (163/163 suites exit 0)
OFFLINE_ACCEPTANCE_EXIT: 0
── 4/5 提交(pathspec 形式 —— 只提交列出的路径)
[main 5d3029c] NC release: producer_contract nc_v1 + pins (booster 700d9e7b / f10 3d7d050f) + M3 beta_overlay shadow 2.5 + anchor_report daemon contract; VERDICT=NO_DEPLOY USER_OVERRIDE=053d50f4ab034ca5e311600b10864d0e30046f2aedf2fca369ebecdc8d032b6b
 5 files changed, 710 insertions(+), 12 deletions(-)
 create mode 100644 ops/producer_release/20260923_nc/INSTALL_CONTRACT.json
 create mode 100644 ops/producer_release/20260923_nc/PATCH_RECEIPT.json
── 5/5 推送
To https://github.com/allenamy/dl_quant_live.git
   b66257b..5d3029c  main -> main
✓ 完成: 5d3029c NC release: producer_contract nc_v1 + pins (booster 700d9e7b / f10 3d7d050f) + M3 beta_overlay shadow 2.5 + anchor_report daemon contract; VERDICT=NO_DEPLOY USER_OVERRIDE=053d50f4ab034ca5e311600b10864d0e30046f2aedf2fca369ebecdc8d032b6b 
safe_commit rc=0 end 05:25:09
NEWSHA=5d3029c0411bf08d7d3e1457f6b46c3ac1ff043b
--- ff_running_tree 05:25:29
{ "now_utc": "2026-09-24T05:25:29Z", "anchor_N_utc": "2026-09-24T04:00:00Z", "minutes_since_N": 85.5, "window": "[N+60m, N+220m]", "remaining_min": 134.5, "open

FF_OK before=b66257b6e8 after=5d3029c041 origin/main=5d3029c041
ff_running_tree rc=0 05:25:31
--- three-way
5d3029c0411bf08d7d3e1457f6b46c3ac1ff043b
5d3029c0411bf08d7d3e1457f6b46c3ac1ff043b
5d3029c0411bf08d7d3e1457f6b46c3ac1ff043b
--- code area (must be empty)
上一行必须为空
--- version probe after-a4
after-a4 NEWSHA=5d3029c0411bf08d7d3e1457f6b46c3ac1ff043b
  OK  running tree HEAD: measured=5d3029c0411bf08d7d3e1457f6b46c3ac1ff043b compared_with=5d3029c0411bf08d7d3e1457f6b46c3ac1ff043b
  OK  origin/main (local ref): measured=5d3029c0411bf08d7d3e1457f6b46c3ac1ff043b compared_with=5d3029c0411bf08d7d3e1457f6b46c3ac1ff043b
  OK  origin/main (GitHub ls-remote): measured=5d3029c0411bf08d7d3e1457f6b46c3ac1ff043b compared_with=5d3029c0411bf08d7d3e1457f6b46c3ac1ff043b
  OK  git show NEWSHA file list: measured=['config/book.json', 'live/tests_anchor_report_builder.py', 'ops/anchor_report.py', 'ops/producer_release/20260923_nc/INSTALL_CONTRACT.json', 'ops/producer_release/20260923_nc/PATCH_RECEIPT.json'] compared_with=['config/book.json', 'live/tests_anchor_report_builder.py', 'ops/anchor_report.py', 'ops/producer_release/20260923_nc/INSTALL_CONTRACT.json', 'ops/producer_release/20260923_nc/PATCH_RECEIPT.json']
  VAL external_book.booster_sha_pin = 700d9e7b7ee992a786528477ff9007ec93c3d16654f1abc52766e5406654020d
  VAL external_book.f10_sha_pin = 3d7d050f78a98cb09586ac9c75c0c12526bfd54b5d9f4c6d151f6121b333139f
  VAL beta_overlay.mode = shadow
  VAL beta_overlay.max_combined_leverage = 2.5
  VAL external_book.producer_contract = nc_v1
  OK  booster_sha_pin == contract: measured=700d9e7b7ee992a786528477ff9007ec93c3d16654f1abc52766e5406654020d compared_with=700d9e7b7ee992a786528477ff9007ec93c3d16654f1abc52766e5406654020d
  OK  f10_sha_pin == contract: measured=3d7d050f78a98cb09586ac9c75c0c12526bfd54b5d9f4c6d151f6121b333139f compared_with=3d7d050f78a98cb09586ac9c75c0c12526bfd54b5d9f4c6d151f6121b333139f
  OK  beta_overlay.mode: measured=shadow compared_with=shadow
  OK  beta_overlay.max_combined_leverage: measured=2.5 compared_with=2.5
  OK  external_book.producer_contract: measured=nc_v1 compared_with=nc_v1
  OK  running-tree book.json bytes == NEWSHA:config/book.json: measured=f623ac271851dc0a32a68e4dd25bab452ca106d6e521ec903ab8c3c1c5bf180c compared_with=f623ac271851dc0a32a68e4dd25bab452ca106d6e521ec903ab8c3c1c5bf180c
VERSION_PROBE after-a4 OK n=0
probe rc=0
## A4 end 05:25:32
## A5 start 05:26:03
bootstrap com.hsy.comboparity rc=0 05:26:03
bootstrap com.hsy.combosnap rc=0 05:26:03
bootstrap com.hsy.combolive rc=0 05:26:03
bootstrap com.hsy.shadowloop rc=0 05:26:03
--- SHADOW_OFFSET_MIN
SHADOW_OFFSET_MIN=12
--- loop.out tail
next 2026-09-24T08:12:00+00:00 in 14150s
next 2026-09-24T08:12:00+00:00 in 9952s
--- sidecar print-disabled
		"com.hsy.sidecar" => disabled
--- sidecar print
Bad request.
(print rc=113)
--- launchctl list
91620	0	com.hsy.combolive
91626	0	com.hsy.shadowloop
-	0	com.hsy.comboparity
-	3	com.hsy.combosnap
--- shadow.lock pid 91626; combo_live_daemon.pid 91620
--- version probe after-a5
after-a5 A3 apply completed_utc=2026-09-24T05:06:17Z stage=installed_not_started VERDICT=NO_DEPLOY USER_OVERRIDE=053d50f4ab034ca5e311600b10864d0e30046f2aedf2fca369ebecdc8d032b6b
  VAL com.hsy.shadowloop pid=91626 start_utc=2026-09-24T05:26:03Z cwd=/Users/haosiyu/wide_shadow args=/usr/local/Cellar/python@3.14/3.14.4/Frameworks/Python.framework/Versions/3.14/Resources/Python.app/Contents/MacOS/Python shadow_loop_v3.py run
  OK  com.hsy.shadowloop start > A3 completion: measured=True compared_with=True
  VAL com.hsy.shadowloop script path=/Users/haosiyu/wide_shadow/shadow_loop_v3.py realpath=/Users/haosiyu/wide_shadow/shadow_loop_v3.py
  OK  com.hsy.shadowloop shadow_loop_v3.py sha at the run path: measured=a68c7a5f0c6e8e0af89eda0307ab0b9ad6b38fa82810f4d04c1ab99deb1d510c compared_with=a68c7a5f0c6e8e0af89eda0307ab0b9ad6b38fa82810f4d04c1ab99deb1d510c
  VAL com.hsy.combolive pid=91620 start_utc=2026-09-24T05:26:03Z cwd=/Users/haosiyu/wide_shadow/fea171 args=/bin/bash /Users/haosiyu/wide_shadow/fea171/combo_live_daemon.sh
  OK  com.hsy.combolive start > A3 completion: measured=True compared_with=True
  VAL combo daemon script invokes combo_stage.py in its cwd: True
  VAL com.hsy.combolive script path=/Users/haosiyu/wide_shadow/fea171/combo_stage.py realpath=/Users/haosiyu/wide_shadow/fea171/combo_stage.py
  OK  com.hsy.combolive combo_stage.py sha at the run path: measured=363dd8c8876ab29eb9c098fe47a40a37bd6c7c912d9cb6cf2cbc7a17b87e9f65 compared_with=363dd8c8876ab29eb9c098fe47a40a37bd6c7c912d9cb6cf2cbc7a17b87e9f65
  VAL sidecar launchctl loaded=False print-disabled=['"com.hsy.sidecar" => disabled'] processes=[]
  OK  sidecar not loaded: measured=False compared_with=False
  OK  sidecar processes: measured=[] compared_with=[]
  OK  sidecar disabled: measured=True compared_with=True
VERSION_PROBE after-a5 OK n=0
probe rc=0
--- executor unchanged since A4: HEAD 5d3029c0411bf08d7d3e1457f6b46c3ac1ff043b book.json f623ac271851dc0a32a68e4dd25bab452ca106d6e521ec903ab8c3c1c5bf180c
## A5 end 05:26:11
## §B first anchor A=1790236800 (08Z) B1-B3 read at 08:18:25Z
B1 target_live keys: ['anchor_ts', 'beta_overlay', 'booster_sha', 'f10_sha', 'gross_norm', 'n_names', 'n_universe', 'producer', 'schema', 'universe', 'universe_sha', 'weights_sha', 'written_utc']
B1 target_live booster_sha 700d9e7b7ee992a786528477ff9007ec93c3d16654f1abc52766e5406654020d f10_sha 3d7d050f78a98cb09586ac9c75c0c12526bfd54b5d9f4c6d151f6121b333139f written_utc 2026-09-24T08:17:55Z producer combo_stage_v1(kingLGBM 0.55 + V2MAIN 0.45, rev24 leg removed; base shadow_loop_
B1 beta_overlay present True version m3_beta_v1 anchor_ts 1790236800 data_cutoff_ts 1790236800 n_names 450 n_estimated 449 n_fallback 0 n_no_cache_column 0
B1 combo_live_status: {"anchor": 1790236800, "step": "done", "ok": true, "reader_ok": true, "reader_verdict": null, "beta_overlay": {"ok": true, "version": "m3_beta_v1", "n_names": 450, "n_estimated": 449, "n_fallback": 0, "n_no_cache_column": 0, "elapsed_s": 0.172, "reader_verdict": {"ok": true, "reason": null, "detail": "", "betas_sha256": "9a04b58ba8b63f45f9de6efb1d9b564694bc8c44096239428a7ae889069b728c"}}}
B1 target_combo: {"schema": "wide_target_combo_v1_execcal", "anchor_ts": 1790236800, "phi": 0.45, "book_form": "combo_v2main_norev24", "w3_masked": [0.396099, 0.0, 0.603901], "kc_state_source": "own", "fc_state_source": "own", "gross": 0.837882, "net_after_reshape": 0.0, "kc_gross": 0.877891, "fc_gross": 0.836567, "rho_kc_fc": 0.9106, "n_f10_scored": 400, "ftrim": {"rule": "pre_zero_rn8_le_-10bp_8h", "hi": -0.001, "rn8_coverage": 1.0, "n_kc": 8, "n_fc": 8, "names_kc": {"CELRUSDT": -0.0021352, "CVCUSDT": -0.0072292, "IOSTUSDT": -0.0011377, "KERNELUSDT": -0.001487, "LSKUSDT": -0.0116231, "ONEUSDT": -0.0116949, "STEEMUSDT": -0.0091092, "VTHOUSDT": -0.0016519}, "names_fc": {"CELRUSDT": -0.0021352, "CVCUSDT": -0.0072292, "IOSTUSDT": -0.0011377, "KERNELUSDT": -0.001487, "LSKUSDT": -0.0116231, "ONEUSDT": -0.0116949, "STEEMUSDT": -0.0091092, "VTHOUSDT": -0.0016519}}}
B2/B3 shadow_log rows for A: [('target_live', 1790236800), ('signal', 1790236800), ('anchor_diagnostics', 1790236800)]
B2 signal keys: ['anchor_ts', 'base_n', 'booster_sha', 'carry_bps', 'cost_bps', 'coverage', 'data_max_ts', 'e', 'exinfo_ok', 'fetched', 'forced_exit_gross', 'forced_exit_n', 'fund_base_n', 'fund_updates', 'fund_updates_base', 'future_dropped', 'gross_pos', 'logged_utc', 'members', 'missing', 'nc', 'runtime_s', 'sel', 'status', 'top5', 'turnover', 'w3', 'weight_used', 'weights_sha']
B2 runtime_s 42.2 logged_utc 2026-09-24T08:12:42Z
B2 anchor_diagnostics phase_s {"setup": 0.7062334030633792, "exchange_info": 0.27890612196642905, "klines": 34.050157806952484, "funding": 3.2683304040692747, "feature_inference": 3.8185291859554127, "previous_anchor_score": 0.005966034950688481, "target_build": 0.026645545032806695, "target_write": 0.012718272977508605, "state_save": 7.749679426080547} total 49.917176758055575
B3 exinfo_ok True fund_bulk_ok None members 400 fund_updates 454
B3 nc block: {"fetch_n": 520, "fetch_new": [], "backfill_residual": [], "fetch_workers": 6, "fetch_budget": 900, "fund_bulk_ok": true, "fund_bulk_pages": 7, "fund_per_symbol": 0, "used_weight_1m_max": 521}
--- B2 combo_live.log for 08Z
waiting launch-window anchor=1790236800 elapsed=1013 Thu Sep 24 08:16:53 UTC 2026
waiting launch-window anchor=1790236800 elapsed=1018 Thu Sep 24 08:16:58 UTC 2026
=== combo_live anchor=1790236800 rc=0 Thu Sep 24 08:17:57 UTC 2026
1537:[  31.9s] ⑤ COMBO_LIVE 写者完成 rehearsal=False n=298 gross=0.8377 读者验收 ok age=0.5s
1549:[  49.6s] FTRIM 负费率空头排除: kc 6 名 / fc 6 名 (rn8 覆盖 1.000)
1550:[  49.6s] ④ COMBO 落盘 n=299 gross=0.8386 kc_src=own fc_src=own w3m=[0.4003, 0.0, 0.5997]
1551:[  50.6s] ⑤ COMBO_LIVE 写者完成 rehearsal=False n=299 gross=0.8386 读者验收 ok age=0.4s
1569:[  39.0s] FTRIM 负费率空头排除: kc 5 名 / fc 5 名 (rn8 覆盖 1.000)
1570:[  39.0s] ④ COMBO 落盘 n=303 gross=0.8407 kc_src=own fc_src=own w3m=[0.3981, 0.0, 0.6019]
1571:[  39.6s] ⑤ COMBO_LIVE 写者完成 rehearsal=False n=303 gross=0.8407 读者验收 ok age=0.5s
1624:[   1.9s] anchor 09-24 08:00 members 400
1630:[  47.6s] FTRIM 负费率空头排除: kc 8 名 / fc 8 名 (rn8 覆盖 1.000)
1631:[  47.6s] ④ COMBO 落盘 n=304 gross=0.8379 kc_src=own fc_src=own w3m=[0.3961, 0.0, 0.6039]
1632:[  47.8s] M3 beta_overlay: {'ok': True, 'version': 'm3_beta_v1', 'n_names': 450, 'n_estimated': 449, 'n_fallback': 0, 'n_no_cache_column': 0, 'elapsed_s': 0.172}
1633:[  49.5s] ⑤ COMBO_LIVE 写者完成 rehearsal=False n=304 gross=0.8379 读者验收 ok age=0.6s
B3 aux.fetch_syms n 520 | A1 fetch_list (04Z) n 522 | in 04Z not 08Z: ['SCRTUSDT', 'STORJUSDT'] | in 08Z not 04Z: []
--- B5 at 08:26:05
COMPLETE
PARITY.json
PARITY.run.log
SHA256SUMS
aux.json
boundary_raw.npz
combo_live_status.json
generation.json
leg_returns_live.json
members_hist.npz
rolling.npz
snap generation 1 1790236800 ['aux.json', 'boundary_raw.npz', 'leg_returns_live.json', 'members_hist.npz', 'rolling.npz']
snap 1790222400 2026-09-24T04:18:16Z
snap 1790236800 2026-09-24T08:18:11Z
parity 1790222400 rc=0 2026-09-24T04:19:17Z PARITY_PARITY anchor 1790222400 why=[] weights={'n_archived': 303, 'n_replay': 303, 'n_differing': 0, 'max_abs_dw': 0.0}
parity 1790236800 rc=0 2026-09-24T08:22:00Z PARITY_PARITY anchor 1790236800 why=[] weights={'n_archived': 304, 'n_replay': 304, 'n_differing': 0, 'max_abs_dw': 0.0}
-	0	com.hsy.comboparity
-	0	com.hsy.combosnap
invalid-manifest lines total: 171; last err line: UNAVAILABLE snapshot generation: FeatureCacheError: invalid producer generation manifest
Sep 24 16:17
## B0 first-anchor probe 08:58:49
first-anchor A=1790236800 (2026-09-24T08:00Z)
  VAL target_live booster_sha=700d9e7b7ee992a786528477ff9007ec93c3d16654f1abc52766e5406654020d f10_sha=3d7d050f78a98cb09586ac9c75c0c12526bfd54b5d9f4c6d151f6121b333139f written_utc=2026-09-24T08:17:55Z
  OK  target_live booster_sha: measured=700d9e7b7ee992a786528477ff9007ec93c3d16654f1abc52766e5406654020d compared_with=700d9e7b7ee992a786528477ff9007ec93c3d16654f1abc52766e5406654020d
  OK  target_live f10_sha: measured=3d7d050f78a98cb09586ac9c75c0c12526bfd54b5d9f4c6d151f6121b333139f compared_with=3d7d050f78a98cb09586ac9c75c0c12526bfd54b5d9f4c6d151f6121b333139f
  VAL shadow_log signal rows for A: 1; booster_sha(12)=['700d9e7b7ee9']
  OK  shadow_log signal booster_sha (12): measured=['700d9e7b7ee9'] compared_with=['700d9e7b7ee9']
  OK  MANIFEST slow2026.txt: measured=700d9e7b7ee992a786528477ff9007ec93c3d16654f1abc52766e5406654020d compared_with=700d9e7b7ee992a786528477ff9007ec93c3d16654f1abc52766e5406654020d
  OK  on-disk slow2026.txt: measured=700d9e7b7ee992a786528477ff9007ec93c3d16654f1abc52766e5406654020d compared_with=700d9e7b7ee992a786528477ff9007ec93c3d16654f1abc52766e5406654020d
  OK  on-disk f10_live_s42_np.npz: measured=3d7d050f78a98cb09586ac9c75c0c12526bfd54b5d9f4c6d151f6121b333139f compared_with=3d7d050f78a98cb09586ac9c75c0c12526bfd54b5d9f4c6d151f6121b333139f
  VAL generation.json schema_version=1 anchor_ts=1790236800 files=['aux.json', 'boundary_raw.npz', 'leg_returns_live.json', 'members_hist.npz', 'rolling.npz']
  OK  generation.json file set (NC contract = 5 signed files): measured=['aux.json', 'boundary_raw.npz', 'leg_returns_live.json', 'members_hist.npz', 'rolling.npz'] compared_with=['aux.json', 'boundary_raw.npz', 'leg_returns_live.json', 'members_hist.npz', 'rolling.npz']
  VAL executor anchors rows for A: 1; external_book ok=True reason=None sha_ok=True booster_sha=700d9e7b7ee992a786528477ff9007ec93c3d16654f1abc52766e5406654020d f10_sha=3d7d050f78a98cb09586ac9c75c0c12526bfd54b5d9f4c6d151f6121b333139f opening_halted=False
  OK  executor external_book ok: measured=True compared_with=True
  OK  executor external_book reason: measured=None compared_with=None
  OK  executor read booster_sha == book pin: measured=700d9e7b7ee992a786528477ff9007ec93c3d16654f1abc52766e5406654020d compared_with=700d9e7b7ee992a786528477ff9007ec93c3d16654f1abc52766e5406654020d
  OK  executor read f10_sha == book pin: measured=3d7d050f78a98cb09586ac9c75c0c12526bfd54b5d9f4c6d151f6121b333139f compared_with=3d7d050f78a98cb09586ac9c75c0c12526bfd54b5d9f4c6d151f6121b333139f
  VAL anchor_runs.log lines in hour 2026-09-24T08Z naming REFUSED/HOLD/sha_pin/PIN: 1
    2026-09-24T08:25:44Z phase_A: {"anchor_wall_ts": 1790236904.8318021, "book_source": "external", "external_wait": {"nominal_anchor_ts": 1790236800, "wake_at": 1790238240.0, "wait_s": 1335.2, "reason": 
  OK  anchor_runs.log pin refusal / HOLD lines: measured=[] compared_with=[]
VERSION_PROBE first-anchor OK n=0
probe rc=0
## B4 executor 08Z (pooled only)
B4 anchors row: opening_halted False target_gross 223266.5 realized_gross 221528.2 n_names_skipped 93 net_over_gross 0.0136
B4 m3_beta_overlay keys ['beta_exec_gross_units', 'beta_exec_over_book_gross', 'beta_exec_usdt', 'beta_missing_head', 'betas_sha256', 'book_gross_usdt', 'btc_book_target_usdt', 'btc_combined_target_usdt', 'btc_dust_only', 'btc_held_usdt', 'budget', 'combined_dust_threshold_usdt', 'data_cutoff_ts', 'field_detail', 'field_ok', 'field_reason', 'gross_final_target_usdt', 'hard_sources', 'hedge_intent_usdt', 'hedge_target_usdt', 'max_combined_leverage', 'mode', 'n_beta_missing', 'n_betas', 'n_fallback', 'n_targeted_names', 'nav_usdt', 'overlay_net_usdt', 'prev_leg_active', 'reason', 'shadow_would_be', 'sizing_gross_usdt', 'status', 'version_expected']
B4 m3: mode shadow status shadow reason None field_ok True n_betas 450 n_fallback 0 data_cutoff_ts 1790236800 beta_exec_usdt -4708.16437857485 hedge_intent_usdt 4708.16437857485 hedge_target_usdt 4708.16437857485 betas_sha256 9a04b58ba8b63f45
B4 hedge_target_usdt finite: True
B4 pilot_log files: ['_schema.json', 'anchors.jsonl', 'daily_nav.jsonl', 'fills.jsonl', 'funding.jsonl', 'orders.jsonl', 'position_readback.jsonl']
B4 rebalance_id A1790238240 orders rows this anchor: 554 | status counts: {None: 554}
B4 order keys with m3/overlay in name: []
B4 orders carrying an m3/overlay/hedge marker: 0 | rows with a truthy m3/overlay key: 0
--- B4 anchor_report
Sep 24 16:55
keys ['anchor_ts', 'lines', 'status', 'utc', 'warn']
anchor 1790236800
守护 … 08:55:02Z", "status": "green", "warn": [], "lines": ["锚 09-24 08:00Z 排查(常驻器)", "守护 2/2", "fund_upd 454 cov 1.0 forced 16", "w3m [0.396, 0.0, 0.604] kc/fc own/own f10 400", "age 365.0s n 304 | 单 554 拒 
基线(近42锚, 不含重建/停开仓): taker 中位 25% 线 41% | |净/gross| 中位 0.50% 线 1.62%
参照(S1a_2026-08-28_2026-09-01T12Z): taker 中位 5.0% → 当前 24.6% (Δ+19.56pp) | |净/gross| 中位 0.36% → 当前 0.50% (Δ+0.14pp) · 判词见日报
funding 287名 -12.29U
twin AGREE(ledger-only; nav row stale) eq=112952.14 nav=112861.12370189 day
[sent]
## B6 regime_dash 08:59:28
B6 last row anchor 1790236800 2026-09-24T08:00Z w3_masked 0.3961 0.6039 keys 35
awk: syntax error at source line 1
 context is
	{print >>>  \ <<< "REGIME_DASH.md mtime\", $6,$7,$8}
awk: illegal statement at source line 1
/Users/haosiyu/regime_dash/launchd.log:0
/Users/haosiyu/regime_dash/launchd_weekly.log:0
launchd.log REGIME_DASH.md regime_dash.jsonl REGIME_DASH.html flag_state.json regime_dash.py 
## B7(b) self-check 08:59:28
M3 selfcheck (production-formula self-consistency, NOT research-side parity) A=1790236800
  OK  installed beta_overlay_producer.py sha == contract candidate: measured=b77c180d69170988780566e19d0ee4a0f85af25a9b9e9be08b6e4a386095fb58 compared_with=b77c180d69170988780566e19d0ee4a0f85af25a9b9e9be08b6e4a386095fb58
  OK  target_live has beta_overlay field: measured=True compared_with=True
  VAL field version=m3_beta_v1 anchor_ts=1790236800 data_cutoff_ts=1790236800 n_names=450 n_estimated=449 n_fallback=0 n_no_cache_column=0
  OK  field anchor_ts / data_cutoff_ts == A: measured=(1790236800, 1790236800) compared_with=(1790236800, 1790236800)
  OK  snapshot COMPLETE: measured=True compared_with=True
  OK  snapshot rolling.npz sha == its SHA256SUMS entry: measured=1e2585a686477b684832aaf4e5d483bd338aa308856d729d368a43a093dea218 compared_with=1e2585a686477b684832aaf4e5d483bd338aa308856d729d368a43a093dea218
  VAL snapshot generation anchor_ts=1790236800 files=['aux.json', 'boundary_raw.npz', 'leg_returns_live.json', 'members_hist.npz', 'rolling.npz']
  OK  snapshot generation anchor == A: measured=1790236800 compared_with=1790236800
  OK  recomputed name list == published: measured=['BTCUSDT', '0GUSDT', '1000BONKUSDT', '1000CATUSDT', '1000FLOKIUSDT', '1000LUNCUSDT', '1000PEPEUSDT', '1000RATSUSDT', '1000SATSUSDT', '1000SHIBUSDT', '1000XECUSDT', '1INCHUSDT', '1MBABYDOGEUSDT', '2ZUSDT', '4USDT', 'AAVEUSDT', 'ACEUSDT', 'ACHUSDT', 'ACTUSDT', 'ACUUSDT', 'ADAUSDT', 'AEROUSDT', 'AEVOUSDT', 'AGLDUSDT', 'AGTUSDT', 'AIAUSDT', 'AIGENSYNUSDT', 'AINUSDT', 'AIOTUSDT', 'AIOUSDT', 'AIXBTUSDT', 'AKEUSDT', 'AKTUSDT', 'ALGOUSDT', 'ALICEUSDT', 'ALLOUSDT', 'ALTUSDT', 'ANKRUSDT', 'APEUSDT', 'API3USDT', 'APRUSDT', 'APTUSDT', 'ARBUSDT', 'ARCUSDT', 'ARIAUSDT', 'ARKMUSDT', 'ARPAUSDT', 'ARUSDT', 'ASTERUSDT', 'ATHUSDT', 'ATOMUSDT', 'ATUSDT', 'AUCTIONUSDT', 'AUSDT', 'AVAAIUSDT', 'AVAXUSDT', 'AVNTUSDT', 'AWEUSDT', 'AXSUSDT', 'B2USDT', 'BABYUSDT', 'BANANAS31USDT', 'BANANAUSDT', 'BANKUSDT', 'BANUSDT', 'BARDUSDT', 'BASEDUSDT', 'BASUSDT', 'BATUSDT', 'BBUSDT', 'BCHUSDT', 'BEATUSDT', 'BELUSDT', 'BERAUSDT', 'BICOUSDT', 'BIGTIMEUSDT', 'BILLUSDT', 'BIOUSDT', 'BIRBUSDT', 'BLESSUSDT', 'BLUAIUSDT', 'BLURUSDT', 'BMTUSDT', 'BNBUSDT', 'BOMEUSDT', 'BRETTUSDT', 'BREVUSDT', 'BROCCOLI714USDT', 'BROCCOLIF3BUSDT', 'BRUSDT', 'BSBUSDT', 'BSVUSDT', 'BTCDOMUSDT', 'BTRUSDT', 'BULLAUSDT', 'BUSDT', 'C98USDT', 'CAKEUSDT', 'CARVUSDT', 'CATIUSDT', 'CCUSDT', 'CELOUSDT', 'CETUSUSDT', 'CFGUSDT', 'CFXUSDT', 'CGPTUSDT', 'CHILLGUYUSDT', 'CHIPUSDT', 'CHRUSDT', 'CHZUSDT', 'CLOUSDT', 'COAIUSDT', 'COLLECTUSDT', 'COMPUSDT', 'COOKIEUSDT', 'COTIUSDT', 'CROSSUSDT', 'CRVUSDT', 'CTSIUSDT', 'CUSDT', 'CVXUSDT', 'CYSUSDT', 'DASHUSDT', 'DEEPUSDT', 'DEXEUSDT', 'DIAUSDT', 'DODOXUSDT', 'DOGEUSDT', 'DOGSUSDT', 'DOLOUSDT', 'DOODUSDT', 'DOTUSDT', 'DRIFTUSDT', 'DUSKUSDT', 'DYDXUSDT', 'DYMUSDT', 'EDENUSDT', 'EDGEUSDT', 'EDUUSDT', 'EGLDUSDT', 'EIGENUSDT', 'ELSAUSDT', 'ENAUSDT', 'ENJUSDT', 'ENSOUSDT', 'ENSUSDT', 'EPICUSDT', 'ERAUSDT', 'ESPORTSUSDT', 'ESPUSDT', 'ETCUSDT', 'ETHFIUSDT', 'ETHUSDT', 'EULUSDT', 'EVAAUSDT', 'FARTCOINUSDT', 'FETUSDT', 'FFUSDT', 'FHEUSDT', 'FIDAUSDT', 'FIGHTUSDT', 'FILUSDT', 'FLOCKUSDT', 'FLOWUSDT', 'FLUIDUSDT', 'FOGOUSDT', 'FOLKSUSDT', 'FORMUSDT', 'FUSDT', 'GALAUSDT', 'GASUSDT', 'GENIUSUSDT', 'GIGGLEUSDT', 'GMTUSDT', 'GMXUSDT', 'GPSUSDT', 'GRASSUSDT', 'GRIFFAINUSDT', 'GRTUSDT', 'GTCUSDT', 'GUAUSDT', 'GUNUSDT', 'GUSDT', 'GWEIUSDT', 'HAEDALUSDT', 'HANAUSDT', 'HBARUSDT', 'HEIUSDT', 'HEMIUSDT', 'HMSTRUSDT', 'HOLOUSDT', 'HOMEUSDT', 'HOTUSDT', 'HUMAUSDT', 'HUSDT', 'HYPERUSDT', 'HYPEUSDT', 'ICNTUSDT', 'ICPUSDT', 'IDOLUSDT', 'IDUSDT', 'IMXUSDT', 'INJUSDT', 'INUSDT', 'INXUSDT', 'IOSTUSDT', 'IOTAUSDT', 'IOTXUSDT', 'IOUSDT', 'IRYSUSDT', 'JASMYUSDT', 'JCTUSDT', 'JELLYJELLYUSDT', 'JOEUSDT', 'JSTUSDT', 'JTOUSDT', 'JUPUSDT', 'KAIAUSDT', 'KAITOUSDT', 'KASUSDT', 'KATUSDT', 'KAVAUSDT', 'KERNELUSDT', 'KGENUSDT', 'KITEUSDT', 'KMNOUSDT', 'KOMAUSDT', 'KSMUSDT', 'LABUSDT', 'LAUSDT', 'LAYERUSDT', 'LDOUSDT', 'LIGHTUSDT', 'LINEAUSDT', 'LINKUSDT', 'LISTAUSDT', 'LITUSDT', 'LPTUSDT', 'LQTYUSDT', 'LSKUSDT', 'LTCUSDT', 'LUMIAUSDT', 'LUNA2USDT', 'LYNUSDT', 'MAGICUSDT', 'MAGMAUSDT', 'MANAUSDT', 'MANTAUSDT', 'MANTRAUSDT', 'MAVUSDT', 'MEGAUSDT', 'MEMEUSDT', 'MERLUSDT', 'METUSDT', 'MEUSDT', 'MINAUSDT', 'MIRAUSDT', 'MITOUSDT', 'MMTUSDT', 'MONUSDT', 'MOODENGUSDT', 'MORPHOUSDT', 'MOVEUSDT', 'MOVRUSDT', 'MUBARAKUSDT', 'MUSDT', 'MYXUSDT', 'NAORISUSDT', 'NEARUSDT', 'NEIROUSDT', 'NEOUSDT', 'NEWTUSDT', 'NIGHTUSDT', 'NILUSDT', 'NOMUSDT', 'NOTUSDT', 'NXPCUSDT', 'OGNUSDT', 'ONDOUSDT', 'ONEUSDT', 'ONGUSDT', 'ONTUSDT', 'ONUSDT', 'OPENUSDT', 'OPGUSDT', 'OPNUSDT', 'OPUSDT', 'ORCAUSDT', 'ORDERUSDT', 'ORDIUSDT', 'PARTIUSDT', 'PAXGUSDT', 'PENDLEUSDT', 'PENGUUSDT', 'PEOPLEUSDT', 'PHAROSUSDT', 'PHAUSDT', 'PIEVERSEUSDT', 'PIPPINUSDT', 'PIXELUSDT', 'PLAYUSDT', 'PLUMEUSDT', 'PNUTUSDT', 'POLUSDT', 'POPCATUSDT', 'PORTALUSDT', 'POWERUSDT', 'POWRUSDT', 'PRLUSDT', 'PROMPTUSDT', 'PROMUSDT', 'PROVEUSDT', 'PTBUSDT', 'PUMPUSDT', 'PYTHUSDT', 'QNTUSDT', 'QTUMUSDT', 'QUSDT', 'RAREUSDT', 'RAVEUSDT', 'RECALLUSDT', 'RENDERUSDT', 'RESOLVUSDT', 'REZUSDT', 'RIFUSDT', 'RIVERUSDT', 'RLCUSDT', 'ROBOUSDT', 'RONINUSDT', 'ROSEUSDT', 'RSRUSDT', 'RUNEUSDT', 'RVNUSDT', 'SAFEUSDT', 'SAGAUSDT', 'SAHARAUSDT', 'SANDUSDT', 'SAPIENUSDT', 'SCRTUSDT', 'SCRUSDT', 'SEIUSDT', 'SENTUSDT', 'SHELLUSDT', 'SIGNUSDT', 'SIRENUSDT', 'SKLUSDT', 'SKRUSDT', 'SKYAIUSDT', 'SKYUSDT', 'SNXUSDT', 'SOLUSDT', 'SOLVUSDT', 'SOONUSDT', 'SOPHUSDT', 'SPACEUSDT', 'SPELLUSDT', 'SPKUSDT', 'SPXUSDT', 'SQDUSDT', 'SSVUSDT', 'STABLEUSDT', 'STARUSDT', 'STBLUSDT', 'STGUSDT', 'STORJUSDT', 'STOUSDT', 'STRKUSDT', 'STXUSDT', 'SUIUSDT', 'SUSDT', 'SUSHIUSDT', 'SWARMSUSDT', 'SXTUSDT', 'SYNUSDT', 'SYRUPUSDT', 'TACUSDT', 'TAGUSDT', 'TAIKOUSDT', 'TAKEUSDT', 'TAOUSDT', 'TAUSDT', 'THETAUSDT', 'THEUSDT', 'TIAUSDT', 'TLMUSDT', 'TNSRUSDT', 'TOSHIUSDT', 'TOWNSUSDT', 'TRADOORUSDT', 'TRBUSDT', 'TREEUSDT', 'TRIAUSDT', 'TRUMPUSDT', 'TRUSTUSDT', 'TRUTHUSDT', 'TRXUSDT', 'TSTUSDT', 'TURBOUSDT', 'TURTLEUSDT', 'TUSDT', 'TUTUSDT', 'TWTUSDT', 'UAIUSDT', 'UBUSDT', 'UMAUSDT', 'UNIUSDT', 'USDCUSDT', 'USELESSUSDT', 'USUALUSDT', 'USUSDT', 'VANAUSDT', 'VELODROMEUSDT', 'VELVETUSDT', 'VETUSDT', 'VIRTUALUSDT', 'VVVUSDT', 'WALUSDT', 'WAXPUSDT', 'WETUSDT', 'WIFUSDT', 'WLDUSDT', 'WLFIUSDT', 'WOOUSDT', 'WUSDT', 'XAIUSDT', 'XANUSDT', 'XAUTUSDT', 'XLMUSDT', 'XMRUSDT', 'XNYUSDT', 'XPINUSDT', 'XPLUSDT', 'XRPUSDT', 'XTZUSDT', 'XVGUSDT', 'YBUSDT', 'YFIUSDT', 'YGGUSDT', 'ZAMAUSDT', 'ZBTUSDT', 'ZECUSDT', 'ZENUSDT', 'ZEREBROUSDT', 'ZETAUSDT', 'ZILUSDT', 'ZKCUSDT', 'ZKPUSDT', 'ZKUSDT', 'ZORAUSDT', 'ZROUSDT'] compared_with=['BTCUSDT', '0GUSDT', '1000BONKUSDT', '1000CATUSDT', '1000FLOKIUSDT', '1000LUNCUSDT', '1000PEPEUSDT', '1000RATSUSDT', '1000SATSUSDT', '1000SHIBUSDT', '1000XECUSDT', '1INCHUSDT', '1MBABYDOGEUSDT', '2ZUSDT', '4USDT', 'AAVEUSDT', 'ACEUSDT', 'ACHUSDT', 'ACTUSDT', 'ACUUSDT', 'ADAUSDT', 'AEROUSDT', 'AEVOUSDT', 'AGLDUSDT', 'AGTUSDT', 'AIAUSDT', 'AIGENSYNUSDT', 'AINUSDT', 'AIOTUSDT', 'AIOUSDT', 'AIXBTUSDT', 'AKEUSDT', 'AKTUSDT', 'ALGOUSDT', 'ALICEUSDT', 'ALLOUSDT', 'ALTUSDT', 'ANKRUSDT', 'APEUSDT', 'API3USDT', 'APRUSDT', 'APTUSDT', 'ARBUSDT', 'ARCUSDT', 'ARIAUSDT', 'ARKMUSDT', 'ARPAUSDT', 'ARUSDT', 'ASTERUSDT', 'ATHUSDT', 'ATOMUSDT', 'ATUSDT', 'AUCTIONUSDT', 'AUSDT', 'AVAAIUSDT', 'AVAXUSDT', 'AVNTUSDT', 'AWEUSDT', 'AXSUSDT', 'B2USDT', 'BABYUSDT', 'BANANAS31USDT', 'BANANAUSDT', 'BANKUSDT', 'BANUSDT', 'BARDUSDT', 'BASEDUSDT', 'BASUSDT', 'BATUSDT', 'BBUSDT', 'BCHUSDT', 'BEATUSDT', 'BELUSDT', 'BERAUSDT', 'BICOUSDT', 'BIGTIMEUSDT', 'BILLUSDT', 'BIOUSDT', 'BIRBUSDT', 'BLESSUSDT', 'BLUAIUSDT', 'BLURUSDT', 'BMTUSDT', 'BNBUSDT', 'BOMEUSDT', 'BRETTUSDT', 'BREVUSDT', 'BROCCOLI714USDT', 'BROCCOLIF3BUSDT', 'BRUSDT', 'BSBUSDT', 'BSVUSDT', 'BTCDOMUSDT', 'BTRUSDT', 'BULLAUSDT', 'BUSDT', 'C98USDT', 'CAKEUSDT', 'CARVUSDT', 'CATIUSDT', 'CCUSDT', 'CELOUSDT', 'CETUSUSDT', 'CFGUSDT', 'CFXUSDT', 'CGPTUSDT', 'CHILLGUYUSDT', 'CHIPUSDT', 'CHRUSDT', 'CHZUSDT', 'CLOUSDT', 'COAIUSDT', 'COLLECTUSDT', 'COMPUSDT', 'COOKIEUSDT', 'COTIUSDT', 'CROSSUSDT', 'CRVUSDT', 'CTSIUSDT', 'CUSDT', 'CVXUSDT', 'CYSUSDT', 'DASHUSDT', 'DEEPUSDT', 'DEXEUSDT', 'DIAUSDT', 'DODOXUSDT', 'DOGEUSDT', 'DOGSUSDT', 'DOLOUSDT', 'DOODUSDT', 'DOTUSDT', 'DRIFTUSDT', 'DUSKUSDT', 'DYDXUSDT', 'DYMUSDT', 'EDENUSDT', 'EDGEUSDT', 'EDUUSDT', 'EGLDUSDT', 'EIGENUSDT', 'ELSAUSDT', 'ENAUSDT', 'ENJUSDT', 'ENSOUSDT', 'ENSUSDT', 'EPICUSDT', 'ERAUSDT', 'ESPORTSUSDT', 'ESPUSDT', 'ETCUSDT', 'ETHFIUSDT', 'ETHUSDT', 'EULUSDT', 'EVAAUSDT', 'FARTCOINUSDT', 'FETUSDT', 'FFUSDT', 'FHEUSDT', 'FIDAUSDT', 'FIGHTUSDT', 'FILUSDT', 'FLOCKUSDT', 'FLOWUSDT', 'FLUIDUSDT', 'FOGOUSDT', 'FOLKSUSDT', 'FORMUSDT', 'FUSDT', 'GALAUSDT', 'GASUSDT', 'GENIUSUSDT', 'GIGGLEUSDT', 'GMTUSDT', 'GMXUSDT', 'GPSUSDT', 'GRASSUSDT', 'GRIFFAINUSDT', 'GRTUSDT', 'GTCUSDT', 'GUAUSDT', 'GUNUSDT', 'GUSDT', 'GWEIUSDT', 'HAEDALUSDT', 'HANAUSDT', 'HBARUSDT', 'HEIUSDT', 'HEMIUSDT', 'HMSTRUSDT', 'HOLOUSDT', 'HOMEUSDT', 'HOTUSDT', 'HUMAUSDT', 'HUSDT', 'HYPERUSDT', 'HYPEUSDT', 'ICNTUSDT', 'ICPUSDT', 'IDOLUSDT', 'IDUSDT', 'IMXUSDT', 'INJUSDT', 'INUSDT', 'INXUSDT', 'IOSTUSDT', 'IOTAUSDT', 'IOTXUSDT', 'IOUSDT', 'IRYSUSDT', 'JASMYUSDT', 'JCTUSDT', 'JELLYJELLYUSDT', 'JOEUSDT', 'JSTUSDT', 'JTOUSDT', 'JUPUSDT', 'KAIAUSDT', 'KAITOUSDT', 'KASUSDT', 'KATUSDT', 'KAVAUSDT', 'KERNELUSDT', 'KGENUSDT', 'KITEUSDT', 'KMNOUSDT', 'KOMAUSDT', 'KSMUSDT', 'LABUSDT', 'LAUSDT', 'LAYERUSDT', 'LDOUSDT', 'LIGHTUSDT', 'LINEAUSDT', 'LINKUSDT', 'LISTAUSDT', 'LITUSDT', 'LPTUSDT', 'LQTYUSDT', 'LSKUSDT', 'LTCUSDT', 'LUMIAUSDT', 'LUNA2USDT', 'LYNUSDT', 'MAGICUSDT', 'MAGMAUSDT', 'MANAUSDT', 'MANTAUSDT', 'MANTRAUSDT', 'MAVUSDT', 'MEGAUSDT', 'MEMEUSDT', 'MERLUSDT', 'METUSDT', 'MEUSDT', 'MINAUSDT', 'MIRAUSDT', 'MITOUSDT', 'MMTUSDT', 'MONUSDT', 'MOODENGUSDT', 'MORPHOUSDT', 'MOVEUSDT', 'MOVRUSDT', 'MUBARAKUSDT', 'MUSDT', 'MYXUSDT', 'NAORISUSDT', 'NEARUSDT', 'NEIROUSDT', 'NEOUSDT', 'NEWTUSDT', 'NIGHTUSDT', 'NILUSDT', 'NOMUSDT', 'NOTUSDT', 'NXPCUSDT', 'OGNUSDT', 'ONDOUSDT', 'ONEUSDT', 'ONGUSDT', 'ONTUSDT', 'ONUSDT', 'OPENUSDT', 'OPGUSDT', 'OPNUSDT', 'OPUSDT', 'ORCAUSDT', 'ORDERUSDT', 'ORDIUSDT', 'PARTIUSDT', 'PAXGUSDT', 'PENDLEUSDT', 'PENGUUSDT', 'PEOPLEUSDT', 'PHAROSUSDT', 'PHAUSDT', 'PIEVERSEUSDT', 'PIPPINUSDT', 'PIXELUSDT', 'PLAYUSDT', 'PLUMEUSDT', 'PNUTUSDT', 'POLUSDT', 'POPCATUSDT', 'PORTALUSDT', 'POWERUSDT', 'POWRUSDT', 'PRLUSDT', 'PROMPTUSDT', 'PROMUSDT', 'PROVEUSDT', 'PTBUSDT', 'PUMPUSDT', 'PYTHUSDT', 'QNTUSDT', 'QTUMUSDT', 'QUSDT', 'RAREUSDT', 'RAVEUSDT', 'RECALLUSDT', 'RENDERUSDT', 'RESOLVUSDT', 'REZUSDT', 'RIFUSDT', 'RIVERUSDT', 'RLCUSDT', 'ROBOUSDT', 'RONINUSDT', 'ROSEUSDT', 'RSRUSDT', 'RUNEUSDT', 'RVNUSDT', 'SAFEUSDT', 'SAGAUSDT', 'SAHARAUSDT', 'SANDUSDT', 'SAPIENUSDT', 'SCRTUSDT', 'SCRUSDT', 'SEIUSDT', 'SENTUSDT', 'SHELLUSDT', 'SIGNUSDT', 'SIRENUSDT', 'SKLUSDT', 'SKRUSDT', 'SKYAIUSDT', 'SKYUSDT', 'SNXUSDT', 'SOLUSDT', 'SOLVUSDT', 'SOONUSDT', 'SOPHUSDT', 'SPACEUSDT', 'SPELLUSDT', 'SPKUSDT', 'SPXUSDT', 'SQDUSDT', 'SSVUSDT', 'STABLEUSDT', 'STARUSDT', 'STBLUSDT', 'STGUSDT', 'STORJUSDT', 'STOUSDT', 'STRKUSDT', 'STXUSDT', 'SUIUSDT', 'SUSDT', 'SUSHIUSDT', 'SWARMSUSDT', 'SXTUSDT', 'SYNUSDT', 'SYRUPUSDT', 'TACUSDT', 'TAGUSDT', 'TAIKOUSDT', 'TAKEUSDT', 'TAOUSDT', 'TAUSDT', 'THETAUSDT', 'THEUSDT', 'TIAUSDT', 'TLMUSDT', 'TNSRUSDT', 'TOSHIUSDT', 'TOWNSUSDT', 'TRADOORUSDT', 'TRBUSDT', 'TREEUSDT', 'TRIAUSDT', 'TRUMPUSDT', 'TRUSTUSDT', 'TRUTHUSDT', 'TRXUSDT', 'TSTUSDT', 'TURBOUSDT', 'TURTLEUSDT', 'TUSDT', 'TUTUSDT', 'TWTUSDT', 'UAIUSDT', 'UBUSDT', 'UMAUSDT', 'UNIUSDT', 'USDCUSDT', 'USELESSUSDT', 'USUALUSDT', 'USUSDT', 'VANAUSDT', 'VELODROMEUSDT', 'VELVETUSDT', 'VETUSDT', 'VIRTUALUSDT', 'VVVUSDT', 'WALUSDT', 'WAXPUSDT', 'WETUSDT', 'WIFUSDT', 'WLDUSDT', 'WLFIUSDT', 'WOOUSDT', 'WUSDT', 'XAIUSDT', 'XANUSDT', 'XAUTUSDT', 'XLMUSDT', 'XMRUSDT', 'XNYUSDT', 'XPINUSDT', 'XPLUSDT', 'XRPUSDT', 'XTZUSDT', 'XVGUSDT', 'YBUSDT', 'YFIUSDT', 'YGGUSDT', 'ZAMAUSDT', 'ZBTUSDT', 'ZECUSDT', 'ZENUSDT', 'ZEREBROUSDT', 'ZETAUSDT', 'ZILUSDT', 'ZKCUSDT', 'ZKPUSDT', 'ZKUSDT', 'ZORAUSDT', 'ZROUSDT']
  VAL betas: n=450 max|recomputed - published|=0.000e+00 n_differing=0
  OK  betas bit-identical (n differing): measured=0 compared_with=0
  OK  n_obs identical (n differing): measured=0 compared_with=0
  OK  counter n_names: measured=450 compared_with=450
  OK  counter n_estimated: measured=449 compared_with=449
  OK  counter n_fallback: measured=0 compared_with=0
  OK  counter n_no_cache_column: measured=0 compared_with=0
  OK  counter first_bar_end_ts: measured=1787659200 compared_with=1787659200
  OK  counter version: measured=m3_beta_v1 compared_with=m3_beta_v1
  OK  executor anchors rows for A: measured=True compared_with=True
  VAL anchors.m3_beta_overlay keys=['beta_exec_gross_units', 'beta_exec_over_book_gross', 'beta_exec_usdt', 'beta_missing_head', 'betas_sha256', 'book_gross_usdt', 'btc_book_target_usdt', 'btc_combined_target_usdt', 'btc_dust_only', 'btc_held_usdt', 'budget', 'combined_dust_threshold_usdt', 'data_cutoff_ts', 'field_detail', 'field_ok', 'field_reason', 'gross_final_target_usdt', 'hard_sources', 'hedge_intent_usdt', 'hedge_target_usdt', 'max_combined_leverage', 'mode', 'n_beta_missing', 'n_betas', 'n_fallback', 'n_targeted_names', 'nav_usdt', 'overlay_net_usdt', 'prev_leg_active', 'reason', 'shadow_would_be', 'sizing_gross_usdt', 'status', 'version_expected']
  VAL mode=shadow status=shadow reason=None field_ok=True n_betas=450 n_fallback=0 data_cutoff_ts=1790236800 beta_exec_usdt=-4708.16437857485 hedge_intent_usdt=4708.16437857485 hedge_target_usdt=4708.16437857485
  OK  executor mode: measured=shadow compared_with=shadow
  OK  executor status: measured=shadow compared_with=shadow
  OK  executor betas_sha256 == canonical hash of published betas: measured=9a04b58ba8b63f45f9de6efb1d9b564694bc8c44096239428a7ae889069b728c compared_with=9a04b58ba8b63f45f9de6efb1d9b564694bc8c44096239428a7ae889069b728c
  VAL beta_exec recompute: NOT COMPUTABLE from the anchors row (no executed-target map in the row); reported, not estimated
M3_SELFCHECK 1790236800 OK n=0
selfcheck rc=0
B6 REGIME_DASH.md mtime 2026-09-24T16:50:04+0800
2
B7 m3 record (pooled): {"nav_usdt": 112902.31304595001, "sizing_gross_usdt": 225804.63, "book_gross_usdt": 223266.54562743174, "gross_final_target_usdt": 223266.54562743174, "beta_exec_usdt": -4708.16437857485, "beta_exec_gross_units": -0.020850610452827517, "beta_exec_over_book_gross": -0.021087639284890606, "hedge_intent_usdt": 4708.16437857485, "hedge_target_usdt": 4708.16437857485, "overlay_net_usdt": null, "btc_book_target_usdt": 559.3740458271146, "btc_combined_target_usdt": 5267.538424401965, "btc_dust_only": false, "btc_held_usdt": 588.6524, "max_combined_leverage": 2.5, "budget": {"max_combined_leverage": 2.5, "nav_usdt": 112902.31304595001, "limit_usdt": 282255.782614875, "gross_without_leg_usdt": 223266.54562743174, "gross_with_full_leg_usdt": 227974.7100060066, "gross_with_placed_leg_usdt": 227974.7100060066, "scale": 1.0, "truncated": false, "rule": "the leg is scaled down so the combined target gross <= max(max_combined_leverage x NAV, the book's own gross)"}, "n_targeted_names": 290, "n_beta_missing": 0, "prev_leg_active": false, "shadow_would_be": "applied", "hard_sources": []}
B7 combined leverage reading: (book final gross 223266.5 + |hedge| 4708.2) / nav 112902.3 = 2.0192x (cap 2.5)
--- new alarm classes since 08:00Z
ALARM.log rows since 05:00Z: 0
B7 overlay_net_usdt = null
B7 budget = {"max_combined_leverage": 2.5, "nav_usdt": 112902.31304595001, "limit_usdt": 282255.782614875, "gross_without_leg_usdt": 223266.54562743174, "gross_with_full_leg_usdt": 227974.7100060066, "gross_with_placed_leg_usdt": 227974.7100060066, "scale": 1.0, "truncated": false, "rule": "the leg is scaled down so the combined target gross <= max(max_combined_leverage x NAV, the book's own gross)"}
B7 shadow_would_be = "applied"
B7 btc_dust_only = false
B7 prev_leg_active = false
B7 n_targeted_names = 290
B7 n_beta_missing = 0
B7 hard_sources = []
B7 max_combined_leverage = 2.5
B7 anchors neutrality fields: {"neutrality_caliber": "signed sum of the venue's own position notionals at the end-of-anchor read; a SNAPSHOT, not a P&L and not a forecast. net_over_gross is the leverage-independent reading \u2014 use it to compare across anchors.", "neutrality_price": {"deficient_side": "sell", "taker_notional_needed_usdt": 3012.7392, "measured_taker_bps_same_side": 101.9402, "measured_over": "MEASURED fills only \u2014 fills with a usable price (finite positive avg_fill_px and mid) AND a known fee (fee_paid
B7 notify_audit messages since 08:00Z: 7
   08:24:00Z HIGH | class: position reconcile: # name(s) differ fro | seen in prior 14 days: True
   08:24:02Z INFO | class: # name(s) withheld: the venue reports ma | seen in prior 14 days: True
   08:24:03Z INFO | class: 重整后 # 个名字跨过了 min_notional 门槛: ['#SYM'] — | seen in prior 14 days: True
   08:24:03Z INFO | class: # held name(s) withheld, reduce#only fro | seen in prior 14 days: True
   08:44:33Z INFO | class: # 个 maker 被 # 拒(post#only 会立刻成交), 其残差按全额 | seen in prior 14 days: True
   08:46:50Z INFO | class: per_name_stop: SYM 冷却期满, 恢复可入 | seen in prior 14 days: True
   08:50:02Z INFO | class: ℹ️
funding span 表(执行器内部 DL 面板专用)已过期: # 个 | seen in prior 14 days: True
B4 reject check (pooled, no arm split): 08Z anchor rejects=82 orders=554 maker=333 reject/orders=0.148 reject/maker=0.246
past 14 days, 08Z anchors only: anchors=14 rejects median=60 p90=91 | reject/orders median=0.127 p90=0.166 | reject/maker median=0.218 p90=0.283
past 14 days, all anchors: anchors=83 rejects median=69 p90=92 | reject/orders median=0.137 p90=0.177 | reject/maker median=0.241 p90=0.302
SCRT/STORJ (pooled, the two names combined):
  last readback before the 08Z rebalance: names with rows=0 gross position notional=0.00 USDT (read_ts max None)
  in the 08Z target: 0 of 2; combined |weight| in target=0.000000
  08Z orders on the two names: rows=0 intended_notional=0.00 filled_notional=0.00 USDT; terminal_reason set=[]
  last readback after the 08Z rebalance: gross position notional=0.00 USDT
  target_live 1790208000: SCRT/STORJ in target 0 of 2
  target_live 1790222400: SCRT/STORJ in target 0 of 2
  position_readback rows for the two names in the last 8 daily logs: 0; latest read_ts None
EXEC_TRACKING (pooled; target_i = target_live w_i / sum|w| x anchors.target_gross; actual = post-anchor venue readback; fill = sum|filled_notional| / sum|intended_notional| over the rebalance's order rows)
  08Z 09-24: L1/gross=0.1304 fill/planned=0.6540 fill/planned(excl skipped_min_notional)=0.6620 G=223267 orders=554
  past 14d, 08Z anchors (n=14): l1_over_gross median=0.1283 p90=0.1574 p10=0.0859
  past 14d, 08Z anchors (n=14): fill_over_planned median=0.6514 p90=0.7098 p10=0.4142
  past 14d, 08Z anchors (n=14): fill_over_planned_excl_skipped median=0.6609 p90=0.7199 p10=0.4164
  past 14d, all anchors (n=83): l1_over_gross median=0.1244 p90=0.1626 p10=0.0870
  past 14d, all anchors (n=83): fill_over_planned median=0.6363 p90=0.7047 p10=0.4537
  past 14d, all anchors (n=83): fill_over_planned_excl_skipped median=0.6432 p90=0.7107 p10=0.4574
## §B second anchor A=1790251200 (12Z) B1-B3 read at 12:18:32Z
B1 target_live booster_sha 700d9e7b7ee992a786528477ff9007ec93c3d16654f1abc52766e5406654020d f10_sha 3d7d050f78a98cb09586ac9c75c0c12526bfd54b5d9f4c6d151f6121b333139f written_utc 2026-09-24T12:17:48Z
B1 beta_overlay present True version m3_beta_v1 anchor_ts 1790251200 data_cutoff_ts 1790251200 n_names 450 n_estimated 449 n_fallback 0 n_no_cache_column 0
B1 combo_live_status: {"anchor": 1790251200, "step": "done", "ok": true, "reader_ok": true, "reader_verdict": null, "beta_overlay": {"ok": true, "version": "m3_beta_v1", "n_names": 450, "n_estimated": 449, "n_fallback": 0, "n_no_cache_column": 0, "elapsed_s": 0.193, "reader_verdict": {"ok": true, "reason": null, "detail": "", "betas_sha256": "96dd666c372bbf31ae707dbef9d4d152e30dcbf030d7c20e1b0baa8ed61828a3"}}}
B1 target_combo: {"anchor_ts": 1790251200, "w3_masked": [0.388768, 0.0, 0.611232], "kc_state_source": "own", "fc_state_source": "own", "gross": 0.828908, "net_after_reshape": -0.0, "n_f10_scored": 400} ftrim n_kc 6 n_fc 6 rn8_coverage 1.0
B2 signal runtime_s 26.5 logged_utc 2026-09-24T12:12:26Z | diag total 34.22 phase_s {"setup": 0.57, "exchange_info": 0.2, "klines": 22.14, "funding": 1.38, "feature_inference": 2.14, "previous_anchor_score": 0.0, "target_build": 0.02, "target_write": 0.01, "state_save": 7.75}
B3 exinfo_ok True members 400 fund_updates 355 forced_exit_n 19
B3 nc: {"fetch_n": 519, "fetch_new": [], "backfill_residual": [], "fetch_workers": 6, "fetch_budget": 900, "fund_bulk_ok": true, "fund_bulk_pages": 7, "fund_per_symbol": 0, "used_weight_1m_max": 520}
B3 aux fetch_syms n 519 nc_backfill_residual []
[  40.3s] ④ COMBO 落盘 n=306 gross=0.8289 kc_src=own fc_src=own w3m=[0.3888, 0.0, 0.6112]
[  40.4s] M3 beta_overlay: {'ok': True, 'version': 'm3_beta_v1', 'n_names': 450, 'n_estimated': 449, 'n_fallback': 0, 'n_no_cache_column': 0, 'elapsed_s': 0.193}
[  41.8s] ⑤ COMBO_LIVE 写者完成 rehearsal=False n=306 gross=0.8289 读者验收 ok age=0.2s
B3 fetch set 08Z 520 -> 12Z 519 | dropped ['STGUSDT'] in symbols_live [True] | added []
dropped names in 08Z target: ['STGUSDT']
## EXINFO probe re-armed 12:19:14 with --symbols SCRTUSDT,STORJUSDT,STGUSDT (lead approval); previous waiting task stopped by its own task id before 13:00:30Z, no request had been sent
FORCED_EXIT attribution A=1790236800: n_forced=191 (producer king-book H weight on them, gross units 0.5642)
   3 member but fails the liquidity gate sel (qv4h; pre-existing rule): 191
FORCED_EXIT attribution A=1790251200: n_forced=196 (producer king-book H weight on them, gross units 0.5783)
   2c legal+crypto but not in this anchor's fetch set (exchangeInfo not TRADING): 1
   3 member but fails the liquidity gate sel (qv4h; pre-existing rule): 195
   STGUSDT among the 12Z forced: True ["2c legal+crypto but not in this anchor's fetch set (exchangeInfo not TRADING)"]
(corrected: sel_idx are POSITIONS within prev_rec.members — shadow_loop_v3.py L861 np.where(sel)[0])
FORCED_EXIT attribution A=1790236800: n_forced=1 (producer king-book H on them, gross units 0.0008)
   3 member but fails the liquidity gate sel (qv4h >= qv4h_min; pre-existing rule): 1
FORCED_EXIT attribution A=1790251200: n_forced=2 (producer king-book H on them, gross units 0.0062)
   2c legal+crypto but not in this anchor's fetch set: 1
   3 member but fails the liquidity gate sel (qv4h >= qv4h_min; pre-existing rule): 1
   STGUSDT among the 12Z forced: True ["2c legal+crypto but not in this anchor's fetch set"] | source of 12Z state: /Users/haosiyu/wide_shadow/state/snap/1790251200
A=1790236800: members outside symbols_live=38; SELECTED members (m[sel]) outside symbols_live=24; held-H names not kept=1; sum=25 (signal forced_exit_n: 16)
A=1790251200: members outside symbols_live=38; SELECTED members (m[sel]) outside symbols_live=24; held-H names not kept=2; sum=26 (signal forced_exit_n: 19)
A=1790236800 reconstruction: forced_n=16 forced_gross=0.0107 | signal: forced_exit_n=16 forced_exit_gross=0.0107
   of which: selected members OUTSIDE symbols_live (never holdable; alpha*tgt >= band) = 15 (gross 0.0098); names inside symbols_live that were held and are no longer kept = 1 (gross 0.0008)
A=1790251200 reconstruction: forced_n=19 forced_gross=0.0161 | signal: forced_exit_n=19 forced_exit_gross=0.0161
   of which: selected members OUTSIDE symbols_live (never holdable; alpha*tgt >= band) = 17 (gross 0.0104); names inside symbols_live that were held and are no longer kept = 2 (gross 0.0057)
## 12Z executor read
12:25:29
{'ok': True, 'reason': None, 'nominal_ts': 1790251200, 'n_names': 306, 'booster_sha': '700d9e7b7ee992a786528477ff9007ec93c3d16654f1abc52766e5406654020d', 'f10_sha': '3d7d050f78a98cb09586ac9c75c0c12526bfd54b5d9f4c6d151f6121b333139f', 'sha_ok': True, 'age_s': 372.0}

[exited with code 0]
--- B5 12Z 12:25:37
COMPLETE PARITY.json PARITY.run.log SHA256SUMS aux.json boundary_raw.npz combo_live_status.json generation.json leg_returns_live.json members_hist.npz rolling.npz 
snap 1790251200 2026-09-24T12:18:47Z
parity 1790251200 rc=0 2026-09-24T12:23:02Z PARITY_PARITY anchor 1790251200 why=[] weights={'n_archived': 306, 'n_replay': 306, 'n_differing': 0, 'max_abs_dw': 0.0}
-	0	com.hsy.comboparity
-	0	com.hsy.combosnap
## B0 12Z probe 12:58:55
first-anchor A=1790251200 (2026-09-24T12:00Z)
  VAL target_live booster_sha=700d9e7b7ee992a786528477ff9007ec93c3d16654f1abc52766e5406654020d f10_sha=3d7d050f78a98cb09586ac9c75c0c12526bfd54b5d9f4c6d151f6121b333139f written_utc=2026-09-24T12:17:48Z
  OK  target_live booster_sha: measured=700d9e7b7ee992a786528477ff9007ec93c3d16654f1abc52766e5406654020d compared_with=700d9e7b7ee992a786528477ff9007ec93c3d16654f1abc52766e5406654020d
  OK  target_live f10_sha: measured=3d7d050f78a98cb09586ac9c75c0c12526bfd54b5d9f4c6d151f6121b333139f compared_with=3d7d050f78a98cb09586ac9c75c0c12526bfd54b5d9f4c6d151f6121b333139f
  VAL shadow_log signal rows for A: 1; booster_sha(12)=['700d9e7b7ee9']
  OK  shadow_log signal booster_sha (12): measured=['700d9e7b7ee9'] compared_with=['700d9e7b7ee9']
  OK  MANIFEST slow2026.txt: measured=700d9e7b7ee992a786528477ff9007ec93c3d16654f1abc52766e5406654020d compared_with=700d9e7b7ee992a786528477ff9007ec93c3d16654f1abc52766e5406654020d
  OK  on-disk slow2026.txt: measured=700d9e7b7ee992a786528477ff9007ec93c3d16654f1abc52766e5406654020d compared_with=700d9e7b7ee992a786528477ff9007ec93c3d16654f1abc52766e5406654020d
  OK  on-disk f10_live_s42_np.npz: measured=3d7d050f78a98cb09586ac9c75c0c12526bfd54b5d9f4c6d151f6121b333139f compared_with=3d7d050f78a98cb09586ac9c75c0c12526bfd54b5d9f4c6d151f6121b333139f
  VAL generation.json schema_version=1 anchor_ts=1790251200 files=['aux.json', 'boundary_raw.npz', 'leg_returns_live.json', 'members_hist.npz', 'rolling.npz']
  OK  generation.json file set (NC contract = 5 signed files): measured=['aux.json', 'boundary_raw.npz', 'leg_returns_live.json', 'members_hist.npz', 'rolling.npz'] compared_with=['aux.json', 'boundary_raw.npz', 'leg_returns_live.json', 'members_hist.npz', 'rolling.npz']
  VAL executor anchors rows for A: 1; external_book ok=True reason=None sha_ok=True booster_sha=700d9e7b7ee992a786528477ff9007ec93c3d16654f1abc52766e5406654020d f10_sha=3d7d050f78a98cb09586ac9c75c0c12526bfd54b5d9f4c6d151f6121b333139f opening_halted=False
  OK  executor external_book ok: measured=True compared_with=True
  OK  executor external_book reason: measured=None compared_with=None
  OK  executor read booster_sha == book pin: measured=700d9e7b7ee992a786528477ff9007ec93c3d16654f1abc52766e5406654020d compared_with=700d9e7b7ee992a786528477ff9007ec93c3d16654f1abc52766e5406654020d
  OK  executor read f10_sha == book pin: measured=3d7d050f78a98cb09586ac9c75c0c12526bfd54b5d9f4c6d151f6121b333139f compared_with=3d7d050f78a98cb09586ac9c75c0c12526bfd54b5d9f4c6d151f6121b333139f
  VAL anchor_runs.log lines in hour 2026-09-24T12Z naming REFUSED/HOLD/sha_pin/PIN: 1
    2026-09-24T12:25:20Z phase_A: {"anchor_wall_ts": 1790251243.700235, "book_source": "external", "external_wait": {"nominal_anchor_ts": 1790251200, "wake_at": 1790252640.0, "wait_s": 1396.3, "reason": "
  OK  anchor_runs.log pin refusal / HOLD lines: measured=[] compared_with=[]
VERSION_PROBE first-anchor OK n=0
probe rc=0
## B4 12Z (pooled) rebalance A1790252640: orders 593 venue_reject 109 opening_halted False target_gross 222997.0 realized_gross 222052.8 net_over_gross 0.012829
B4 m3: mode shadow status shadow field_ok True n_betas 450 n_fallback 0 beta_exec_usdt -4693.160366861709 hedge_target_usdt 4693.160366861709 finite True shadow_would_be applied n_beta_missing 0 hard_sources []
B7 budget: limit 281950.195407125 gross_without_leg 222997.01925972776 gross_with_full_leg 227690.17962658947 scale 1.0 truncated False nav 112780.07816285
B7 combined leverage reading (integrator's division of the executor's fields): 2.0189x (cap 2.5)
B4 orders with an overlay/hedge marker: 0
B4 STGUSDT (pooled): position notional after the 08Z rebalance 835.94 USDT; 12Z target weight 0.0; 12Z orders rows 0 intended 0.00 filled 0.00 USDT; terminal []; position after 12Z 0.00 USDT
anchor_report 1790251200 green [] 2026-09-24T12:55:01Z
锚 09-24 12:00Z 排查(常驻器)
守护 2/2
fund_upd 355 cov 1.0 forced 19
w3m [0.389, 0.0, 0.611] kc/fc own/own f10 400
age 372.0s n 306 | 单 593 拒 109 | 换手 8.0% 成交 11562U taker 22% fee 2.67bps
gross 222053 net 2849(1.28%) gaps 219U
external_book held_exit: ['PRLUSDT', 'SCRUSDT', 'THEUSDT'] n_held_exit 3
post readback rows 297 | STG row present: True
STG fills today: [('A1790209440', 'buy', 30.58, 'maker'), ('A1790209440', 'buy', 30.58, 'maker'), ('A1790238240', 'buy', 4.87, 'maker'), ('A1790238240', 'buy', 13.04, 'maker'), ('A1790238240', 'buy', 13.04, 'maker'), ('A1790238240', 'buy', 46.89, 'maker'), ('A1790238240', 'buy', 13.57, 'maker'), ('A1790238240', 'buy', 42.01, 'maker'), ('A1790238240', 'buy', 4.87, 'maker'), ('A1790238240', 'buy', 13.04, 'maker'), ('A1790238240', 'buy', 46.89, 'maker'), ('A1790238240', 'buy', 13.57, 'maker'), ('A1790238240', 'buy', 42.01, 'maker'), ('A1790238240', 'buy', 13.04, 'maker')]
STG order rows today: [('A1790209440', 'buy', 'maker', 30.72, 0.0, 'venue_reject'), ('A1790209440', 'buy', 'maker', 30.72, 30.58, 'partial_expired'), ('A1790209440', 'buy', 'topup_taker', 0.13, 0.0, 'skipped_min_notional'), ('A1790223839', 'buy', 'maker', 60.34, 0.0, 'venue_reject'), ('A1790223839', 'buy', 'topup_taker', 60.34, 0.0, 'skipped_venue_lock'), ('A1790238240', 'buy', 'maker', 133.69, 0.0, 'venue_reject'), ('A1790238240', 'buy', 'maker', 133.69, 133.41, 'partial_expired'), ('A1790238240', 'buy', 'topup_taker', 0.27, 0.0, 'abandoned_spread_gt_25bps')]
## B6 12Z 13:00:09
B6 last row 1790251200 2026-09-24T12:00Z 0.3888 0.6112
B6 REGIME_DASH.md mtime 2026-09-24T20:50:04+0800
0
## B7(b) 12Z
  VAL betas: n=450 max|recomputed - published|=0.000e+00 n_differing=0
  VAL mode=shadow status=shadow reason=None field_ok=True n_betas=450 n_fallback=0 data_cutoff_ts=1790251200 beta_exec_usdt=-4693.160366861709 hedge_intent_usdt=4693.160366861709 hedge_target_usdt=4693.160366861709
  OK  executor betas_sha256 == canonical hash of published betas: measured=96dd666c372bbf31ae707dbef9d4d152e30dcbf030d7c20e1b0baa8ed61828a3 compared_with=96dd666c372bbf31ae707dbef9d4d152e30dcbf030d7c20e1b0baa8ed61828a3
  VAL beta_exec recompute: NOT COMPUTABLE from the anchors row (no executed-target map in the row); reported, not estimated
M3_SELFCHECK 1790251200 OK n=0
selfcheck rc=0
B7 12Z notify_audit since 12:00Z: 6
   12:24:01Z HIGH | class: position reconcile: # name(s) differ fro | seen in prior 14 days: True
   12:24:02Z INFO | class: # name(s) withheld: the venue reports ma | seen in prior 14 days: True
   12:24:02Z INFO | class: 重整后 # 个名字跨过了 min_notional 门槛: ['#SYM', ' | seen in prior 14 days: True
   12:24:02Z INFO | class: # held name(s) withheld, reduce#only fro | seen in prior 14 days: True
   12:44:06Z INFO | class: # 个 maker 被 # 拒(post#only 会立刻成交), 其残差按全额 | seen in prior 14 days: True
   12:48:43Z HIGH | class: 局部止损触发(比例门): 仅所涉名已平, 全书未平, 开仓已停。触发: §#b  | seen in prior 14 days: False
  '局部止损' (local stop) pages in the whole audit file: 1 | first: 2026-09-24T12:48Z
  ALARM.log rows since 12:00Z: [('2026-09-24T12:48:40Z', 'HIGH', '局部止损触发(比例门): 仅所涉名已平, 全书未平, 开仓已停')]
## EXINFO probe start 13:00:50 (waits for M3 FETCH_MANIFEST.json "verdict")
## EXINFO probe (no-wait, lead 13:0xZ) start 13:01:17
{ "now_utc": "2026-09-24T13:01:18Z", "anchor_N_utc": "2026-09-24T12:00:00Z", "minutes_since_N": 61.3, "window": "[N+60m, N+220m]", "remaining_min": 158.7, "open": true, "reason": "open", "override": null, "last_anchor_st

EXINFO_PROBE preceding job ended: NO_WAIT (lead instruction: send now)
EXINFO_PROBE {"utc": "2026-09-24T13:01:18Z", "path": "/fapi/v1/exchangeInfo", "weight_declared": 1, "used_weight_1m_after": 43, "n_symbols_in_response": 907, "preceding_job_end_line": "NO_WAIT (lead instruction: send now)", "symbols": {"SCRTUSDT": {"status": "SETTLING", "contractType": "PERPETUAL"}, "STORJUSDT": {"status": "SETTLING", "contractType": "PERPETUAL"}, "STGUSDT": {"status": "SETTLING", "contractType": "PERPETUAL"}}}
exinfo_probe rc=0 end 13:01:18
