#!/usr/bin/env python3
"""Print the state files a producer generation marker commits (its "files" keys), space separated, sorted.
Used by combo_state_snapshot.sh and combo_parity_replay.sh so the snapshot / replay copy exactly the set the producer signed,
for any producer version (3 files before the new-contract release, 5 after; NC design §A7 addendum, lead 2026-09-23).
Refuses (exit 3, message on stderr) on an unreadable marker, an empty set, a name that is not a plain state-file name, or the
marker naming itself. Never writes anything.
usage: generation_files.py <generation.json>"""
import json, re, sys

NAME = re.compile(r"[A-Za-z0-9_]+\.(npz|json)")


def main():
    try:
        rec = json.load(open(sys.argv[1]))
        files = rec["files"]
        if not isinstance(files, dict) or not files:
            raise ValueError("empty or non-dict files")
        names = sorted(files)
        bad = [n for n in names if not isinstance(n, str) or not NAME.fullmatch(n) or n == "generation.json"]
        if bad:
            raise ValueError(f"refused names {bad}")
    except Exception as exc:
        print(f"GENERATION_FILES_REFUSED {sys.argv[1] if len(sys.argv) > 1 else '?'}: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 3
    print(" ".join(names))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
