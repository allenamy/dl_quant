#!/bin/bash
# 侧车守护: 影子写出新 target_live 文件后自动跑 sidecar_blend(只读侧车, blend 目录 live 不读)
cd "$HOME/wide_shadow/fea171"
LAST=""
while true; do
  NEW=$(ls -t "$HOME/wide_shadow/state/target_live"/*.json 2>/dev/null | head -1)
  if [ -n "$NEW" ] && [ "$NEW" != "$LAST" ]; then
    sleep 120   # 等影子状态文件(aux/weights)落定
    "$HOME/wide_shadow/venv/bin/python" -u sidecar_blend.py >> sidecar_daemon.log 2>&1
    echo "=== ran for $(basename $NEW) rc=$? $(date -u)" >> sidecar_daemon.log
    LAST="$NEW"
  fi
  sleep 180
done
