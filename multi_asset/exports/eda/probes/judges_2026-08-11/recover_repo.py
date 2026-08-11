"""Reconstruct dl_quant_live from the session transcript.

The repo was deleted from disk. Every file in it was created through this session's tool calls, so
the transcript is an append-only log of its construction: Write gives whole files, Edit gives
(old -> new) patches in order, and Bash heredocs (`cat > path <<'EOF'`) give whole files too.
Replaying them in order reconstructs the final content.
"""
import json
import os
import re
import sys

TRANSCRIPT = sys.argv[1]
STAGE = sys.argv[2]
MARK = "dl_quant_live"

files = {}          # path -> content
order = []
stats = {"write": 0, "edit": 0, "edit_miss": 0, "heredoc": 0}

HEREDOC = re.compile(
    r"(?:cat|tee)\s*(?:>|>>)\s*['\"]?(?P<path>[^\s'\"<>|]+)['\"]?\s*<<\s*'?(?P<tag>[A-Za-z_][A-Za-z0-9_]*)'?\n"
    r"(?P<body>.*?)\n(?P=tag)\b", re.S)


def note(path):
    if path not in order:
        order.append(path)


with open(TRANSCRIPT) as f:
    for line in f:
        try:
            d = json.loads(line)
        except Exception:
            continue
        msg = d.get("message") or {}
        content = msg.get("content")
        if not isinstance(content, list):
            continue
        for c in content:
            if not (isinstance(c, dict) and c.get("type") == "tool_use"):
                continue
            name, inp = c.get("name"), (c.get("input") or {})
            if name == "Write":
                p = inp.get("file_path", "")
                if MARK in p:
                    files[p] = inp.get("content", "")
                    note(p); stats["write"] += 1
            elif name == "Edit":
                p = inp.get("file_path", "")
                if MARK in p and p in files:
                    old, new = inp.get("old_string", ""), inp.get("new_string", "")
                    if inp.get("replace_all"):
                        if old in files[p]:
                            files[p] = files[p].replace(old, new); stats["edit"] += 1
                        else:
                            stats["edit_miss"] += 1
                    elif files[p].count(old) == 1:
                        files[p] = files[p].replace(old, new, 1); stats["edit"] += 1
                    else:
                        stats["edit_miss"] += 1
                elif MARK in p:
                    stats["edit_miss"] += 1
            elif name == "Bash":
                cmd = inp.get("command", "") or ""
                if MARK not in cmd:
                    continue
                for m in HEREDOC.finditer(cmd):
                    p = m.group("path")
                    if MARK in p:
                        files[p] = m.group("body") + "\n"
                        note(p); stats["heredoc"] += 1

print(json.dumps(stats))
for p in sorted(files):
    rel = p.split(MARK + "/", 1)[1] if MARK + "/" in p else os.path.basename(p)
    out = os.path.join(STAGE, rel)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w") as fh:
        fh.write(files[p])
    print(f"  {rel:55s} {len(files[p]):7d} bytes")
print(f"recovered {len(files)} files -> {STAGE}")
