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
