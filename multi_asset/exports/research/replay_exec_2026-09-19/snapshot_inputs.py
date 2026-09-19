#!/usr/bin/env python3
"""replay_exec 2026-09-19 · input snapshot (READ-ONLY on the live system).

Copies every input the executor-layer simulator and its calibration read into ONE mirror directory, so that
calibration, simulation, V1 and the battery all read the same bytes, and writes INPUT_MANIFEST.json (sha256 + bytes
of every mirrored file) next to this script.

Read-only guarantees (hard rules of the task):
  · ~/dl_quant_live and ~/wide_shadow are only READ (open(..., "rb"), `git archive`, `git rev-parse`). Nothing is
    executed inside them, nothing is written there, nothing is imported from there.
  · Append-only ledgers (pilot_log/*.jsonl, anchor_runs.log) are copied as a COMPLETE-LINE PREFIX captured in one
    read: the bytes that are hashed are the bytes that are written (no second open between check and write).
  · Rolling files (rolling.npz, aux.json, exchange_info_cache.json) are rewritten by production every anchor; their
    mirrored copy is the only reproducible version — the manifest records its sha, a rerun needs the same-sha copy.
  · The executor source is exported with `git archive 409ea16` (git object store, read-only) — the tree the running
    executor is on (verified with `git rev-parse HEAD`, recorded).
Mirror layout keeps the executor's own relative paths (state/live/pilot_log/<day>/...), so the research repo's canonical
fills reader (fills_reader.py, root = mirror) reads the mirror exactly as it reads production.

usage: snapshot_inputs.py <mirror_dir>
"""
import hashlib, json, os, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
LIVE = os.path.expanduser("~/dl_quant_live")
WS = os.path.expanduser("~/wide_shadow")
EXEC_TREE = "409ea16"
DAYS = [time.strftime("%Y%m%d", time.gmtime(1787270400 + 86400 * k)) for k in range(0, 30)]   # 2026-08-21 .. 2026-09-19
DAYS = [d for d in DAYS if d <= "20260919"]
TABLES = ("orders", "fills", "anchors", "position_readback", "funding", "daily_nav", "_schema")
A_FIRST, A_LAST = 1787702400, 1789790400            # 2026-08-26 00Z .. 2026-09-19 04Z (target_live files)


def sha_bytes(b):
    return hashlib.sha256(b).hexdigest()


def read_once(p):
    with open(p, "rb") as fh:
        return fh.read()


def complete_line_prefix(b):
    """an append-only jsonl/log may be mid-write: keep only complete lines (bytes up to the last newline)"""
    i = b.rfind(b"\n")
    return b[:i + 1] if i >= 0 else b""


def put(mirror, rel, b, man, src):
    dst = os.path.join(mirror, rel)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    tmp = dst + ".part"
    with open(tmp, "wb") as fh:
        fh.write(b)
    os.replace(tmp, dst)
    got = read_once(dst)
    assert sha_bytes(got) == sha_bytes(b), f"write verification failed for {rel}"
    man[rel] = {"sha256": sha_bytes(b), "n_bytes": len(b), "source": src}


def main():
    mirror = os.path.abspath(sys.argv[1])
    os.makedirs(mirror, exist_ok=True)
    man = {}
    # ── 1. executor ledgers (append-only; complete-line prefix) ──
    for d in DAYS:
        for t in TABLES:
            src = f"{LIVE}/state/live/pilot_log/{d}/{t}.json" + ("" if t == "_schema" else "l")
            if not os.path.exists(src):
                continue
            b = read_once(src)
            if t != "_schema":
                b = complete_line_prefix(b)
            put(mirror, f"state/live/pilot_log/{d}/" + os.path.basename(src), b, man, src)
    b = complete_line_prefix(read_once(f"{LIVE}/state/anchor_runs.log"))
    put(mirror, "state/anchor_runs.log", b, man, f"{LIVE}/state/anchor_runs.log")
    put(mirror, "state/exchange_info_cache.json", read_once(f"{LIVE}/state/live/exchange_info_cache.json"), man,
        f"{LIVE}/state/live/exchange_info_cache.json")
    # ── 2. executor source: git archive of the running tree ──
    head = subprocess.run(["git", "-C", LIVE, "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    full = subprocess.run(["git", "-C", LIVE, "rev-parse", "--verify", EXEC_TREE + "^{commit}"], capture_output=True, text=True,
                          check=True).stdout.strip()
    tree_dir = os.path.join(mirror, f"exec_tree_{EXEC_TREE}")
    os.makedirs(tree_dir, exist_ok=True)
    ar = subprocess.run(["git", "-C", LIVE, "archive", EXEC_TREE, "scheduler", "signal", "live", "config"], capture_output=True,
                        check=True).stdout
    subprocess.run(["tar", "-x", "-C", tree_dir], input=ar, check=True)
    tree_files = {}
    for root, _, files in os.walk(tree_dir):
        for f in sorted(files):
            p = os.path.join(root, f)
            tree_files[os.path.relpath(p, mirror)] = sha_bytes(read_once(p))
    # ── 3. producer: archived target books, 5m panel, symbol axis, funding ledger ──
    for A in range(A_FIRST, A_LAST + 1, 14400):
        for ext in (".json", ".json.sha256"):
            src = f"{WS}/state/target_live/{A}{ext}"
            if os.path.exists(src):
                put(mirror, f"target_live/{A}{ext}", read_once(src), man, src)
    for rel, src in (("producer/rolling.npz", f"{WS}/state/rolling.npz"), ("producer/xfer_syms.npz", f"{WS}/fea171/xfer_syms.npz"),
                     ("producer/aux.json", f"{WS}/state/aux.json")):
        put(mirror, rel, read_once(src), man, src)
    doc = {"device": "snapshot_inputs.py", "device_sha256": sha_bytes(read_once(os.path.abspath(__file__))),
           "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "mirror": mirror,
           "executor_tree": {"requested": EXEC_TREE, "commit": full, "running_head_at_snapshot": head,
                             "head_equals_requested": head.startswith(EXEC_TREE) or head == full, "n_files": len(tree_files),
                             "files_sha256": tree_files},
           "rerun": f"/usr/bin/python3 {os.path.relpath(os.path.abspath(__file__), os.path.expanduser('~/Desktop/quant_research'))} {mirror}",
           "note": ("append-only tables are complete-line prefixes captured in one read; rolling files (rolling.npz, aux.json, "
                    "exchange_info_cache.json) cannot be re-captured later — a rerun of the downstream devices needs these exact bytes"),
           "files": man}
    out = os.path.join(HERE, "INPUT_MANIFEST.json")
    with open(out + ".part", "w") as fh:
        json.dump(doc, fh, indent=1, sort_keys=True)
    os.replace(out + ".part", out)
    print(f"snapshot: {len(man)} files + {len(tree_files)} tree files -> {mirror}; HEAD {head[:9]} (requested {EXEC_TREE}); manifest {out}")


if __name__ == "__main__":
    main()
