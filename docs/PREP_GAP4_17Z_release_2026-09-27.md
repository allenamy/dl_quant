> **创建:** 2026-09-27 15:57 UTC | **Session:** Codex acting-lead/live_recovery_audit_0927 | **状态:** final（准备材料已交付；待16Z恢复验收与C0后由root执行） | **作废条件:** 基线/候选/工具SHA变化、非预期新MH洞、16Z恢复验收或C0失败、17Z窗口错过、用户或root改裁定

# GAP4 17Z窗口：已核路径及逐步命令

继承 `docs/PREREG_GAP4_recovery_release_2026-09-27.md` 和 `docs/DEPLOY_gap_classfix_2026-09-26.md` rev3/P5澄清。本文是准备材料，**没有运行重放、电池、安装或服务操作**。不把离线恢复判词替代 VERSION_PROBE/M3/PARITY。

## 已核事实与承重检查

静态收据：`multi_asset/exports/research/acting_lead_2026-09-27/receipts/GAP4_static_readiness_20260927.json`，24项均一致。候选4文件分别对契约hash；当前4目标分别对基线/不存在条件；14个unchanged对真实home；GAP4 executor归档2文件与候选包逐字节一致。

- GAP4 clone `/Users/haosiyu/cc_tmp/gapfix4_exec_20260926T1911Z` HEAD `201188d652c69c2518be0d6457464940d24cca2e`，code区干净；只取 `ops/producer_release/20260927_gapfix/INSTALL_CONTRACT.json` 和 `PATCH_RECEIPT.json`。
- A10 clone `/Users/haosiyu/cc_tmp/fixpkg_e_exec` HEAD `cea1e15fa4051df1fb506a5989a3e582291ce95b`，code区干净；只取 `live/tests_nosleep.py`，SHA `64f09fe1c0156c1b800adf72726f496f96ee61cc9b2eddffeb99a1ae708ff179`。该commit的差异是A10从本机pmset大小依赖改为合成子进程超时，生产文件不在本次pathspec。
- 契约SHA `27a0c4935839c109d7af1bd34f158458c8e91fc34687c6ee66c5c04bdfa96eec`；combo候选 `5eaabcdb9e4d69c1af2339217ae46d11fe54c2f5d7e743409c5b585ff4a6e3a3`，现码 `12a76de89831fb42d05ec722f2e2506d6b288b4b9f5b86be04bc390c789a62a9`。
- W0/W4/W5原门的Desktop绝对路径均存在，仍是本机真实目录；只有将来要生成的backup/receipt/probe输出尚不存在。原门没有迁移后失效的`/usr/local`解释器路径。原门实际引用的9个依赖文件已核Desktop与当前WT逐字节相同。备份 `/Users/haosiyu/cc_tmp/gapfix_install_BK_20260927` 不存在；本方案C0目录和release clone也不存在；free138.5GiB。
- `gap_version_probe.py`真实字节SHA `4eeb641824853db49c050e6d23b18e4bcbf509e4ca475528e1300b10c69f2b7c`，等于固定提交3b4a2815a。新W6只改为20Z `1790539200`、固定三洞、当前WT中的已提交probe/package绝对路径；使用实际release_gates.load校验结构，未执行门。

源码承重审阅未找到当前正常锚的新阻断：`prev_state.py:73–90`只选A之前有效状态，正常A−4h路径来源仍own；`:22–55`拒绝损坏、错轴、非有限及gross<0.4。`combo_stage.py:56–64,257–283,331–377`保持正常向量路径，仅缺锚/坏状态/冷启动进入新分支；生产发布段的deadline/F10覆盖/gross/模型pin/原子写仍保留。`:168–200`按生产成员规则重算历史洞，当前三洞确实存在，因此20Z与现码的差异应限于该链条，必须由C0归因确认；这不是宣称所有正常锚都字节相同。`members_rule.py:6–7`使用当前fetch mask近似历史名单是原已量化约束，不扩大本包。源代码不含执行器下单改动。

安装器 `nc_install_files.py:78–120`真实schema为 `NC_FILES_INSTALL_RECEIPT.json`，成功字段 `stage=installed_not_started`、`state_manifest_diff=[]`、`completed_utc`、`installed`、`producer_load`。W5读的也是此名。不要误写成NC_INSTALL_RECEIPT。失败可能发生在文件已换之后；保持服务停止、保留现场，root裁定回滚，不能靠重跑apply得到绿。

**当前真正未满足项：16Z恢复验收；C0 current_vs_archived及三洞归因；发布时真实树电池；发布后W4/W5；20Z首锚W6。** 以下任一步非预期即停。不得绕过、删旧收据、关闭pin或并入M3。

## 0. 进入17Z窗口（root已独立完成标准16Z验收后）

以下段落在同一 `/bin/bash` 会话执行，保留 `set -euo pipefail`，不通过管道取退出码。只设任务变量；不改HOME/CODEX_HOME。

```bash
set -euo pipefail
QR=/Users/haosiyu/.codex/worktrees/acting-lead-20260927/quant_research
GAP="$QR/multi_asset/exports/research/gap_classfix_2026-09-26"
ACT="$QR/multi_asset/exports/research/acting_lead_2026-09-27"
RCP="$ACT/receipts"
LIVE=/Users/haosiyu/dl_quant_live
PKG="$GAP/package_GAP4"
GATES="$QR/multi_asset/exports/research/nc_2026-09-23/devices/release_gates.py"
XC=/Users/haosiyu/cc_tmp/gapfix_release_20260927T1700Z
C0ROOT=/Users/haosiyu/cc_tmp/gapfix_c0_round5_16Z_20260927
C0OUT="$RCP/GAP4_C0_round5_16Z_1790524800.json"
BK=/Users/haosiyu/cc_tmp/gapfix_install_BK_20260927
OLD=d01e35db56b4d7ed6abf0befd9f18452cd06c329
G4=201188d652c69c2518be0d6457464940d24cca2e
A10=cea1e15fa4051df1fb506a5989a3e582291ce95b
export EXPECT_MH=1790424000,1790438400,1790481600
/usr/bin/python3 -B - <<'PY'
import json
p='/Users/haosiyu/.codex/tmp/acting_lead_20260927/ACCEPT_16Z.json'
r=json.load(open(p))
assert r['anchor']==1790524800 and r['verdict']=='PASS'
assert len(r['checks'])==9 and all(c['status']=='PASS' for c in r['checks'].values())
print('RECOVERY_PRECONDITION PASS (standard VERSION_PROBE/M3/PARITY separately accepted by root)')
PY
/usr/bin/python3 -B "$QR/multi_asset/exports/research/common/venue_quiet_window.py" --json
test "$(git -C "$LIVE" rev-parse HEAD)" = "$OLD"
test ! -e "$C0ROOT"
test ! -e "$C0OUT"
test ! -e "$XC"
test ! -e "$BK"
```

## 1. C0两次回放及真实收据门（生产服务保持运行）

```bash
bash "$GAP/devices/run_c0_round5.sh" "$C0ROOT" 1790524800 "$C0OUT" > "$RCP/GAP4_C0_round5_16Z_1790524800.log" 2>&1
# 上行shell rc只是启动结果；真实判词如下，不能省略。
/usr/bin/python3 -B - "$C0ROOT" "$C0OUT" <<'PY'
from pathlib import Path
import json,sys
root,out=Path(sys.argv[1]),Path(sys.argv[2]); r=json.loads(out.read_text())
want={'i_current_vs_archived_bitwise','iii_a_holes_before_A_equal_literal',
'iii_a_patched_MH_RECOMPUTED_equals_literal_no_errors','iii_a_patched_missing_0',
'iii_a_current_missing_equals_len_literal','iii_b_patched_sources_own',
'iii_b_no_state_lookup_no_cold_no_page','iii_b_members_recomputed_keys_equal_literal',
'iii_b_rc_both_0','iii_c_kc_state_bitwise'}
assert r['device']=='c0_round5_attrib.py' and r['A']==1790524800
assert r['expect_mh']==[1790424000,1790438400,1790481600]
assert set(r['checks'])==want and all(v is True for v in r['checks'].values())
assert r['VERDICT']=='PASS'
for code in ('current','patched'):
    p=root/(code+'_base')/'1790524800'
    assert (p/'RC').read_text().strip()=='0'
    assert (p/'ISOLATION_OK').is_file()
print('C0_RECOVERY_REFERENCE PASS 10/10 and replay RC 0/0')
PY
```

原wrapper末行echo遮子rc；而此门读取真实RC/隔离标记/10项检查。原whole-section C0可能因预期MH差异FAIL，按P5只消费current_vs_archived与归因收据，run4未删未改。

## 2. W0 → W1（只能恢复与C0都通过之后）

```bash
/usr/bin/python3 -B "$GATES" "$GAP/window/gates_gapfix_W0_pre.json" "$RCP/GAP4_W0_17Z.log"
# 临近19:40不得压缩电池或留停机跨锚：至少留60分钟再开始停服务。
/usr/bin/python3 -B - "$QR/multi_asset/exports/research/common" <<'PY'
import sys
sys.path.insert(0,sys.argv[1])
from venue_quiet_window import require_quiet_window
require_quiet_window(min_remaining_min=60)
print('WINDOW_RESERVE PASS >=60m')
PY
GID="gui/$(id -u)"
for label in com.hsy.shadowloop com.hsy.combolive com.hsy.combosnap com.hsy.comboparity; do
  launchctl bootout "$GID/$label"
done
```

等周期作业自然退出，root核对只读PID/工作目录；不要按名字kill。不要输出完整cmdline或环境。安装器会再核这四项服务无PID及sidecar未加载。

## 3. W3：只含两份归档+A10，完整state，真实候选电池

```bash
git clone --branch main "$LIVE" "$XC"
git -C "$XC" remote set-url origin https://github.com/allenamy/dl_quant_live.git
git -C "$XC" config user.name haosiyu
git -C "$XC" config user.email siyuhao0702@gmail.com
test "$(git -C "$XC" rev-parse HEAD)" = "$OLD"
git -C "$XC" fetch /Users/haosiyu/cc_tmp/gapfix4_exec_20260926T1911Z "$G4"
git -C "$XC" fetch /Users/haosiyu/cc_tmp/fixpkg_e_exec "$A10"
mkdir -p "$XC/ops/producer_release/20260927_gapfix"
for p in ops/producer_release/20260927_gapfix/INSTALL_CONTRACT.json ops/producer_release/20260927_gapfix/PATCH_RECEIPT.json; do
  git -C "$XC" show "$G4:$p" > "$XC/$p"
done
git -C "$XC" show "$A10:live/tests_nosleep.py" > "$XC/live/tests_nosleep.py"
rsync -a --exclude acceptance/ --exclude quarantine/ --exclude __pycache__/ --exclude pycache_void/ --exclude '/*.log' --exclude '/*.out' --exclude anchor.lock "$LIVE/state/" "$XC/state/"
/usr/bin/python3 -B - "$XC" "$PKG" <<'PY'
from pathlib import Path
import hashlib,subprocess,sys
x,pkg=map(Path,sys.argv[1:]); want={'live/tests_nosleep.py','ops/producer_release/20260927_gapfix/INSTALL_CONTRACT.json','ops/producer_release/20260927_gapfix/PATCH_RECEIPT.json'}
s=subprocess.check_output(['git','-C',str(x),'status','--porcelain','--untracked-files=all','--','live','ops','config'],text=True)
assert {l[3:] for l in s.splitlines()}==want
assert hashlib.sha256((x/'live/tests_nosleep.py').read_bytes()).hexdigest()=='64f09fe1c0156c1b800adf72726f496f96ee61cc9b2eddffeb99a1ae708ff179'
for f in ('INSTALL_CONTRACT.json','PATCH_RECEIPT.json'):
    assert (x/'ops/producer_release/20260927_gapfix'/f).read_bytes()==(pkg/f).read_bytes()
print('CANDIDATE_PATHSPEC_AND_BYTES PASS 3/3')
PY
(cd "$XC" && bash ops/safe_commit.sh "producer release archive: GAP4 contract 27a0c493 + host-independent A10; recovery 16Z/C0 accepted, first anchor 20Z" ops/producer_release/20260927_gapfix/INSTALL_CONTRACT.json ops/producer_release/20260927_gapfix/PATCH_RECEIPT.json live/tests_nosleep.py) > "$RCP/GAP4_W3_safe_commit_17Z.log" 2>&1
# safe_commit内部唯一套件入口=ops/run_acceptance_offline.sh；rc非0即停。
NEWSHA=$(git -C "$XC" rev-parse HEAD)
/usr/bin/python3 -B /Users/haosiyu/cc_tmp/lead_deploy_20260923/ff_running_tree.py "$NEWSHA"
/usr/bin/python3 -B "$GAP/devices/gap_version_probe.py" after-w3 "$NEWSHA" ops/producer_release/20260927_gapfix/INSTALL_CONTRACT.json ops/producer_release/20260927_gapfix/PATCH_RECEIPT.json live/tests_nosleep.py --out "$RCP/GAP4_VP_after_w3_17Z.txt"
```

safe_commit确切候选树必须全绿166/166，`OFFLINE_ACCEPTANCE_EXIT 0`；run log在`$XC/state/_safe_commit_acc.log`。如safe_commit失败，未快进/未装包；不要重复跑到绿，先核具名失败、剩余窗口与生产服务状态。

## 4. W4 → W5（四服务仍停止）

```bash
/usr/bin/python3 -B "$GATES" "$GAP/window/gates_gapfix_W4_install.json" "$RCP/GAP4_W4_17Z.log"
/usr/bin/python3 -B - "$BK/NC_FILES_INSTALL_RECEIPT.json" <<'PY'
import json,sys
r=json.load(open(sys.argv[1]))
assert r['stage']=='installed_not_started' and r['state_manifest_diff']==[]
assert len(r['installed'])==4 and r['preflight']['package']=='PASS'
assert r['no_launchctl'] is False and r['ignore_window'] is False
print('FILES_ONLY_RECEIPT PASS installed_not_started, state unchanged')
PY
for label in com.hsy.shadowloop com.hsy.combolive com.hsy.combosnap com.hsy.comboparity; do
  launchctl bootstrap "$GID" "/Users/haosiyu/Library/LaunchAgents/$label.plist"
done
/usr/bin/python3 -B "$GATES" "$GAP/window/gates_gapfix_W5_after_start.json" "$RCP/GAP4_W5_17Z.log"
```

W4与W5门本身打印简明判词；完整probe日志会包含进程参数，保存收据即可，不整体回显到聊天。W5必须实际看到producer/combo PID启动时间晚于completed_utc及运行路径hash为候选；只bootstrap成功不等于W5通过。任何失败由root处置，本文不自动回滚或重新恢复交易。

## 5. 20Z首锚（21Z完整验收时）

```bash
/usr/bin/python3 -B "$GATES" "$ACT/window/gates_gapfix_W6_first_anchor_1790539200_20Z.json" "$RCP/GAP4_W6_20Z.log"
```

还须标准inspect/VERSION_PROBE/M3 shadow/PARITY/B4合池/报告/watchdog；恢复第二锚另跑symbol-bound venue K1，机械恢复门`--minimum-fill-ratio 0.95`。新W6读取target_combo的真实字段`kc_state_source/fc_state_source`和target_blend的`h_source`，都必须own；`members_recomputed`键恰好三洞、errors={}、无GAP_PAGE，当前MH洞仍恰好三洞；不能拿文件名20Z冒充epoch。

## 未验证与回滚入口

6段Bash命令通过`bash -n`，5段Python heredoc只做compile语法检查，均未执行其中命令。未调用GitHub远端、未在17Z重新preflight、未跑C0或电池；16Z完整验收还未产出，20Z前驱自然未知。已经存在的候选绿收据不替代此次真实候选safe_commit。未复演rollback；原门`$GAP/window/gates_gapfix_RB_rollback.json`读相同backup，必须先停止同四服务、静默窗及锁成立，由root决定执行。成功字段为`rolled_back_not_started`，新文件移入backup下的具名aside，状态保持不变；随后启动服务并核baseline。回滚恢复原缺锚缺陷，不能据此声称恢复正常。

## 追加 A：16Z 完整验收 actual inputs（N+55 报告；17Z 才能一次收齐）

报告 launchd `/Users/haosiyu/Library/LaunchAgents/com.hsy.anchor_report.plist` 使用 `/usr/bin/python3 /Users/haosiyu/dl_quant_live/ops/anchor_report.py`，每四小时55分触发；venue收据另要求N+60、锚done及静默窗。故**只到16:55不够全9PASS**。以下命令供root于17Z执行；先inspect，再标准门与恢复门。本附录未执行这些命令。输出保存在新目录，不回显完整文件或臂结局。

```bash
set -euo pipefail
QR=/Users/haosiyu/.codex/worktrees/acting-lead-20260927/quant_research
RC="$QR/multi_asset/exports/research/nc_2026-09-23"
AD="$QR/multi_asset/exports/research/acting_lead_2026-09-27/devices"
RCP=/Users/haosiyu/.codex/tmp/acting_lead_20260927
COL="$RCP/FIRST_ACCEPT_16Z_20260927T1700Z"
A=1790524800
mkdir "$COL"
/usr/bin/python3 -B "$QR/multi_asset/exports/live/pilot_journal/tools/inspect_anchor.py" "$A" > "$COL/INSPECT_16Z.txt"
/usr/bin/python3 -B /Users/haosiyu/cc_tmp/nc_20260923/src/nc_version_probe.py --out "$COL/VERSION_PROBE_16Z.txt" first-anchor /Users/haosiyu/cc_tmp/nc_20260923/package_NC "$A" > "$COL/VERSION_PROBE_16Z.stdout.txt" 2>&1
/Users/haosiyu/wide_shadow/venv/bin/python -B "$RC/devices/nc_m3_selfcheck.py" /Users/haosiyu/cc_tmp/nc_20260923/package_v2c_20260925 "$A" --expect-version m3_beta_v2 --out "$COL/M3_SELFCHECK_16Z.txt" > "$COL/M3_SELFCHECK_16Z.stdout.txt" 2>&1
# PARITY由launchd产出；此处只读收据，不手动重放。
/usr/bin/python3 -B - "$COL" <<'PY'
from pathlib import Path
import json,sys
A=1790524800; p=Path('/Users/haosiyu/wide_shadow/state/snap')/str(A)
assert (p/'COMPLETE').is_file(), 'SNAPSHOT_PENDING'
r=json.loads((p/'PARITY.json').read_text())
assert r['device']=='combo_parity_compare.py' and r['anchor_ts']==A
assert r['combo_stage_rc']==0 and r['VERDICT']=='PARITY' and r['why']==[]
i=r['anchor_identity']
assert i['requested']==i['archived']==i['replayed']==A
assert i['schema_archived']==i['schema_replayed']=='wide_target_v1'
w=r['weights']; assert w['n_archived']==w['n_replay'] and w['n_archived']>0
assert w['n_differing']==0 and w['max_abs_dw']==0
Path(sys.argv[1],'PARITY_16Z.json').write_bytes((p/'PARITY.json').read_bytes())
print('SNAPSHOT_PARITY PASS identity/rc/keys/weights')
PY
/usr/bin/python3 -B "$RC/devices/nc_b4_pooled.py" "$A" > "$COL/B4_POOLED_16Z.txt" 2>&1
/usr/bin/python3 -B "$QR/multi_asset/exports/research/recovery_2026-09-27/devices/ledger_side_check.py" "$A" --out "$COL/LEDGER_16Z.json" > "$COL/LEDGER_16Z.stdout.txt" 2>&1
/usr/bin/python3 -B "$QR/multi_asset/exports/research/common/venue_quiet_window.py" --json > "$COL/QUIET_16Z.json"
# 唯一联网步骤，只能root在已授权静默窗执行；本子任务没有执行。
/usr/bin/python3 -B "$AD/venue_readonly_symbol_bound.py" anchor --anchor "$A" --out "$COL/VENUE_16Z.json" > "$COL/VENUE_16Z.stdout.txt" 2>&1
# 保存会覆盖或增长的来源；不得将state.json的缺失复制成空文件。
cp /Users/haosiyu/dl_quant_live/state/live/pilot_log/20260927/anchors.jsonl "$COL/anchors.jsonl"
cp /Users/haosiyu/dl_quant_live/state/anchor_runs.log "$COL/anchor_runs.log"
cp /Users/haosiyu/dl_quant_live/state/live/watchdog/ALARM.log "$COL/ALARM.log"
cp /Users/haosiyu/dl_quant_live/state/live/watchdog/last_eval.json "$COL/last_eval.json"
cp /Users/haosiyu/dl_quant_live/state/anchor_report_last.json "$COL/anchor_report_last.json"
/usr/bin/python3 -B "$AD/recovery_acceptance.py" --anchor "$A" --observed-at "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  --inspect "$COL/INSPECT_16Z.txt" --anchors "$COL/anchors.jsonl" --anchor-log "$COL/anchor_runs.log" \
  --ledger-receipt "$COL/LEDGER_16Z.json" --alarm-log "$COL/ALARM.log" --watchdog-eval "$COL/last_eval.json" \
  --watchdog-state /Users/haosiyu/dl_quant_live/state/live/watchdog/state.json \
  --anchor-report "$COL/anchor_report_last.json" --venue-receipt "$COL/VENUE_16Z.json" --out "$RCP/ACCEPT_16Z.json"
```

恢复门9个输入分别为inspect、anchors、anchor_runs、ledger、ALARM、last_eval、可列父目录下缺失的state.json、N+55报告、新symbol-bound venue收据。标准门必须各自rc0并留收据；原`accept_anchor_v2.sh`的DONE/脚本rc不能替代。B4只输出opening_halted/external_book而未门控，由恢复门补；M3_SELFCHECK只消费shadow合池，不能打开M3。报告或PARITY尚未来保持PENDING，不能补旧文件；COL/ACCEPT若已存在须具名续次，禁止覆盖。K1仍仅覆盖commission列名的已成交订单及RID−600s至采集末端。

## 追加 B：发布脚本路径与行为

- `~/dl_quant_live/ops/safe_commit.sh:110–117`在电池通过、显式pathspec提交后**自动`git push origin main`**。W3会发布提交；push失败时可能已本地提交，不能重跑混淆候选。
- `/Users/haosiyu/cc_tmp/lead_deploy_20260923/ff_running_tree.py:4`使用`expanduser("~/dl_quant_live")`。本机account home与expanduser均为`/Users/haosiyu`，realpath相同且非symlink。`:7–26`非阻塞flock、code dirty拒绝、fetch、origin expected匹配和ff-only兼容新机；调用给完整NEWSHA。无额外架构白名单。本次未执行fetch、merge或锁写入。
