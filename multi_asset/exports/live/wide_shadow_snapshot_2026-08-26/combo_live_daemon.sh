#!/bin/bash
# COMBO-LIVE 守护(2026-08-26, 用户令"现在切"): 生产者写出本锚 target_live 后, 等 aux/rolling 落定,
# 立即 COMBO_LIVE=1 跑 combo_stage(重写 target_live 为候选书; 内置五层安全; 任何失败=king形态+HIGH页报)。
# 停止=kill 本 PID(按 PID); 回滚=停守护, 下一锚起执行器自动读 king 文件。每锚只尝试一次。
cd "$HOME/wide_shadow/fea171"
WS="$HOME/wide_shadow"
LASTF="$WS/fea171/combo_live_last_anchor"
page() {
  "$WS/venv/bin/python" - "$1" "$2" <<'PYEOF'
import sys
sys.path.insert(0, "/Users/haosiyu/dl_quant_live/live")
import telegram_notify as TN
tok = cid = None
for ln in open("/Users/haosiyu/dl_quant_live/.env"):
    ln = ln.strip()
    if ln.startswith("TELEGRAM_BOT_TOKEN="): tok = ln.split("=", 1)[1].strip().strip('"')
    elif ln.startswith("TELEGRAM_CHAT_ID="): cid = ln.split("=", 1)[1].strip().strip('"')
TN.TelegramNotifier(token=tok, chat_id=cid).alarm(sys.argv[1], sys.argv[2])
PYEOF
}
while true; do
  NOW=$(date -u +%s)
  A=$(( NOW / 14400 * 14400 ))
  TL="$WS/state/target_live/$A.json"
  LAST=$(cat "$LASTF" 2>/dev/null || echo 0)
  if [ -f "$TL" ] && [ "$A" != "$LAST" ]; then
    if [ $(( NOW - A )) -gt 1355 ]; then
      # 已过 N+22:35(守护迟到/重启), 不做无谓重写(combo_stage 的硬截止同判), 静默跳过
      echo "$A" > "$LASTF"
    else
      OK=""
      for i in $(seq 1 50); do
        AA=$("$WS/venv/bin/python" -c "import json;print(json.load(open('$WS/state/aux.json'))['prev_rec']['anchor_ts'])" 2>/dev/null)
        if [ "$AA" = "$A" ] && [ "$WS/state/rolling.npz" -nt "$TL" ]; then OK=1; break; fi
        sleep 3
      done
      if [ -n "$OK" ]; then
        RUNLOG=$(mktemp)
        COMBO_LIVE=1 "$WS/venv/bin/python" -u combo_stage.py > "$RUNLOG" 2>&1
        RC=$?
        cat "$RUNLOG" >> combo_live.log
        echo "=== combo_live anchor=$A rc=$RC $(date -u)" >> combo_live.log
        if [ "$RC" != "0" ] && ! grep -q "COMBO_LIVE ABORT" "$RUNLOG"; then
          page HIGH "combo_live 守护: combo_stage 异常退出 rc=$RC(锚 $A), 本锚交易 king 形态(原文件在位)"
        fi
        rm -f "$RUNLOG"
      else
        page HIGH "combo_live 守护: aux/rolling 150s 未落定(锚 $A), 跳过重写, 本锚交易 king 形态"
        echo "skip aux-not-settled anchor=$A $(date -u)" >> combo_live.log
      fi
      echo "$A" > "$LASTF"
    fi
  fi
  sleep 5
done
