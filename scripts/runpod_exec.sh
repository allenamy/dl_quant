#!/bin/bash
# Execute a command on the RunPod pod via SSH proxy (requires expect for PTY).
# Usage: ./scripts/runpod_exec.sh "your command"
set -euo pipefail

RUNPOD_USER="${RUNPOD_USER:-n1z3bv2ri7lphk-64411f30}"
RUNPOD_HOST="${RUNPOD_HOST:-ssh.runpod.io}"
RUNPOD_KEY="${RUNPOD_KEY:-$HOME/.ssh/runpod_ed25519}"
CMD="$1"
BEGIN="__CLAUDE_BEGIN__"
END="__CLAUDE_END__"

expect -c "
set timeout 3600
log_user 1
spawn ssh -o StrictHostKeyChecking=accept-new -i $RUNPOD_KEY ${RUNPOD_USER}@${RUNPOD_HOST}
expect -re {[\$#] \$}
send {echo ${BEGIN}; (${CMD}); echo ${END}; exit}
send \"\r\"
expect ${END}
expect eof
" 2>&1 | sed -e 's/\x1b\[[0-9;?]*[a-zA-Z]//g' -e 's/\[?2004[hl]//g' \
       | awk -v beg="$BEGIN" -v end="$END" '
    $0 ~ beg { inside=1; next }
    $0 ~ end { inside=0; next }
    inside   { print }
'
