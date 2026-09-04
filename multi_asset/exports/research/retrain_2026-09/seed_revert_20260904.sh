#!/bin/bash
# 恢复今早 08:53Z 换掉的席位历史(bundle 种子 + 实盘追加行, Σ简单口径, 与生产者追加行同口径), 并 kickstart 生产者。只在 pod 真简单口径判定确认后执行。
set -e
ST=/Users/haosiyu/wide_shadow/state
date -u +%FT%TZ
[ -f "$ST/leg_returns_live.json.pre_seatfix_20260904" ] || { echo "backup missing"; exit 2; }
echo "backup sha: $(shasum -a 256 $ST/leg_returns_live.json.pre_seatfix_20260904 | cut -c1-12) (expect 172715cea9f5)"
cp "$ST/leg_returns_live.json" "$ST/leg_returns_live.json.oos_expm1_seed_withdrawn_20260904"
cp "$ST/leg_returns_live.json.pre_seatfix_20260904" "$ST/leg_returns_live.json"
echo "restored sha: $(shasum -a 256 $ST/leg_returns_live.json | cut -c1-12)"
OLD=$(launchctl list | awk '/com.hsy.shadowloop/{print $1}'); echo "producer pid before: $OLD"
launchctl kickstart -k gui/$(id -u)/com.hsy.shadowloop
sleep 8
NEW=$(launchctl list | awk '/com.hsy.shadowloop/{print $1}'); echo "producer pid after: $NEW"
[ "$NEW" != "$OLD" ] && [ "$NEW" != "-" ] && echo "RESTART_OK" || echo "RESTART_CHECK_FAILED"
tail -3 /Users/haosiyu/wide_shadow/state/shadow_loop.log 2>/dev/null | cut -c1-160 || true
