#!/usr/bin/env python3
"""t5b_copy.py — Mac, READ-ONLY on ~/wide_shadow and ~/dl_quant_live (SPEC_T5b §0, §3). Copies the fixed source list into T5b/private/,
verifies source bytes == copy bytes (append-only logs: the source's first len(copy) bytes must hash to the copy), scans text copies for
credential patterns (hit => copy deleted, SKIPPED_SECRET), exports read-only `git show <commit>:<path>` for the SPEC §6.4 / §7.4 commit sets.
Computes nothing about Q1/Q2/Q3. Writes private/COPY_SHA256.txt, private/COPY_UTC.txt, receipts/RECEIPT_T5b_copy.json.
Launch: env -i PATH=/usr/bin:/bin HOME=$HOME /usr/bin/python3 devices/t5b_copy.py <T5b dir> CPATH,HOME,LC_CTYPE,LIBRARY_PATH,MANPATH,PATH,SDKROOT,__CF_USER_TEXT_ENCODING
"""
import os, sys, json, time, hashlib, re, subprocess
T5B = os.path.abspath(sys.argv[1]); WHITE = set(x for x in sys.argv[2].split(",") if x)
assert WHITE and sorted(k for k in os.environ if k not in WHITE) == [], ("ENV WHITELIST VIOLATION", sorted(os.environ))
SPEC_SHA = "92d901034b14eea09fea221fe4ca88b96b649d81e9955caf1dfa0aea570e5b87"
def shab(b): return hashlib.sha256(b).hexdigest()
def shaf(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for blk in iter(lambda: f.read(1 << 22), b""): h.update(blk)
    return h.hexdigest()
assert shaf(T5B + "/SPEC_T5b.md") == SPEC_SHA, "spec sha"
HOME = os.environ["HOME"]; WS = HOME + "/wide_shadow"; EX = HOME + "/dl_quant_live"; PRIV = T5B + "/private"
t0 = time.time(); u = lambda t: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t))
SRC = []   # (source abs path, dest rel path under private/, kind)
for A in range(1787688000, 1789214400 + 1, 14400):
    SRC += [(f"{WS}/state/target_live/{A}.json", f"ws/target_live/{A}.json", "json"), (f"{WS}/state/target_live/{A}.json.sha256", f"ws/target_live/{A}.json.sha256", "text"),
            (f"{WS}/state/target_combo/{A}.json", f"ws/target_combo/{A}.json", "json")]
for A in range(1788336000, 1789214400 + 1, 14400):
    SRC += [(f"{WS}/fea171/state_H_kc_{A}.npz", f"ws/fea171_states/state_H_kc_{A}.npz", "bin"), (f"{WS}/fea171/state_H_fc_{A}.npz", f"ws/fea171_states/state_H_fc_{A}.npz", "bin")]
SRC += [(f"{WS}/state/aux.json", "ws/aux.json", "json"), (f"{WS}/state/aux_pre_m1_20260904.json", "ws/aux_pre_m1_20260904.json", "json"),
        (f"{WS}/fea171/xfer_ref.npz", "ws/xfer_ref.npz", "bin"), (f"{WS}/shadow_bundle/config.json", "ws/shadow_bundle_config.json", "json"),
        (f"{WS}/fea171/combo_stage.py", "ws/combo_stage.py", "text"), (f"{WS}/fea171/combo_live.log", "ws/combo_live.log", "log"),
        (f"{WS}/fea171/combo_live_daemon.sh", "ws/combo_live_daemon.sh", "text"), (f"{WS}/fea171/check_ftrim_anchor.py", "ws/check_ftrim_anchor.py", "text")]
DAYS = []
d = time.mktime(time.strptime("20260801", "%Y%m%d"))
while True:
    ds = time.strftime("%Y%m%d", time.localtime(d))
    if ds > "20260912": break
    DAYS.append(ds); d += 86400
DAYS = sorted(set(DAYS))
assert DAYS[0] == "20260801" and DAYS[-1] == "20260912" and len(DAYS) == 43, DAYS
for ds in DAYS:
    for f in ("_schema.json", "anchors.jsonl", "orders.jsonl", "fills.jsonl", "position_readback.jsonl", "funding.jsonl"):
        SRC.append((f"{EX}/state/live/pilot_log/{ds}/{f}", f"exec/pilot_log/{ds}/{f}", "log" if f.endswith(".jsonl") else "json"))
SRC += [(f"{EX}/state/anchor_runs.log", "exec/anchor_runs.log", "log"), (f"{EX}/state/notify_audit.jsonl", "exec/notify_audit.jsonl", "log"),
        (f"{EX}/state/launchd_out.log", "exec/launchd_out.log", "log"),
        (f"{EX}/state/live/per_name_stop.json", "exec/state_live_per_name_stop.json", "json"), (f"{EX}/state/live/no_trade_band.json", "exec/state_live_no_trade_band.json", "json"),
        (f"{EX}/state/no_trade_band.json", "exec/state_no_trade_band.json", "json"), (f"{EX}/config/book.json", "exec/worktree/config/book.json", "json"),
        (f"{EX}/live/per_name_stop.py", "exec/worktree/live/per_name_stop.py", "text"), (f"{EX}/scheduler/anchor_loop.py", "exec/worktree/scheduler/anchor_loop.py", "text"),
        (f"{EX}/live/binance_executor.py", "exec/worktree/live/binance_executor.py", "text"), (f"{EX}/live/external_book.py", "exec/worktree/live/external_book.py", "text")]
for s, _, _ in SRC:
    assert "/.env" not in s and not s.endswith(".env"), s
SECRET_PATTERNS = {
    "telegram_bot_token": re.compile(rb"\b\d{8,10}:[A-Za-z0-9_-]{35}\b"),
    "binance_key_assignment": re.compile(rb"BINANCE_API_(?:KEY|SECRET)\s*=\s*['\"]?[A-Za-z0-9]{20,}"),
    "api_or_secret_key_value": re.compile(rb"(?i)(?:api[_-]?key|secret[_-]?key|x-mbx-apikey)['\"]?\s*[:=]\s*['\"]?[A-Za-z0-9]{40,}"),
    "signed_query": re.compile(rb"signature=[0-9a-fA-F]{64}"),
}
manifest = []; skipped = []; missing = []; notes = []
def copy_one(src, rel, kind):
    dst = os.path.join(PRIV, rel); os.makedirs(os.path.dirname(dst), exist_ok=True)
    for attempt in range(4):
        st0 = os.stat(src); data = open(src, "rb").read(); h = shab(data)
        after = open(src, "rb").read()
        if after == data: integrity = "UNCHANGED"
        elif kind == "log" and len(after) > len(data) and after[:len(data)] == data: integrity = "APPEND_ONLY_GREW"
        else:
            integrity = None; time.sleep(2); continue
        hits = [nm for nm, pat in SECRET_PATTERNS.items() if pat.search(data)] if kind != "bin" else []
        if hits:
            if os.path.exists(dst): os.remove(dst)
            skipped.append(dict(src=src, rel=rel, patterns=hits)); return
        with open(dst, "wb") as f: f.write(data)
        hd = shaf(dst); assert hd == h, ("copy sha mismatch", src)
        manifest.append((h, rel)); return dict(src=src, rel=rel, bytes=len(data), src_mtime_utc=u(st0.st_mtime), integrity=integrity, attempts=attempt + 1)
    raise AssertionError(("source kept changing (non-append) during copy", src))
rows = []
for s, rel, kind in SRC:
    if not os.path.exists(s): missing.append(dict(src=s, rel=rel)); continue
    r = copy_one(s, rel, kind)
    if r: rows.append(r)
# ---------------- git (read-only) exports
def git(*args):
    return subprocess.run(["/usr/bin/git", "-C", EX] + list(args), capture_output=True)
head = git("rev-parse", "HEAD"); assert head.returncode == 0, head.stderr
HEAD = head.stdout.decode().strip()
def commits(paths):
    r = git("log", "--format=%H %cI", "--since=2026-08-22T04:58:00Z", "--until=2026-09-12T12:00:00Z", "--", *paths); assert r.returncode == 0, r.stderr
    return [ln.split(" ", 1) for ln in r.stdout.decode().splitlines() if ln.strip()]
CFG_PATHS = ["config/book.json"]; CODE_PATHS = ["scheduler/anchor_loop.py", "live/binance_executor.py", "live/per_name_stop.py", "live/external_book.py"]
C_cfg = commits(CFG_PATHS); C_code = commits(CODE_PATHS)
gitrows = []
for group, clist, paths in (("C_cfg", C_cfg, CFG_PATHS), ("C_code", C_code, CODE_PATHS)):
    for c, ct in clist:
        for p in paths:
            r = git("show", f"{c}:{p}")
            rel = f"exec_git/{c[:12]}/{p}"; dst = os.path.join(PRIV, rel)
            if r.returncode != 0:
                gitrows.append(dict(group=group, commit=c, commit_time=ct, path=p, present=False, err=r.stderr.decode()[:200])); continue
            data = r.stdout
            hits = [nm for nm, pat in SECRET_PATTERNS.items() if pat.search(data)]
            if hits: skipped.append(dict(src=f"git show {c}:{p}", rel=rel, patterns=hits)); continue
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            with open(dst, "wb") as f: f.write(data)
            assert shaf(dst) == shab(data)
            manifest.append((shab(data), rel)); gitrows.append(dict(group=group, commit=c, commit_time=ct, path=p, present=True, rel=rel, sha256=shab(data)))
manifest.sort(key=lambda x: x[1])
with open(PRIV + "/COPY_SHA256.txt", "w") as f:
    for h, rel in manifest: f.write(f"{h}  {rel}\n")
copy_utc = u(time.time())
open(PRIV + "/COPY_UTC.txt", "w").write(copy_utc + "\n")
ext = {p: shaf(p) for p in (T5B + "/../T1/receipts/pod2/T1_d2.npz", T5B + "/../T5/receipts/pod2/T5_bridge_components.npz", T5B + "/../T5/receipts/pod2/RECEIPT_T5_bridge.json")}
RC = dict(self_sha256=shaf(os.path.abspath(__file__)), spec_sha256=SPEC_SHA, copy_utc=copy_utc, n_sources=len(SRC), n_copied=len(rows), n_missing=len(missing), missing=missing,
          n_skipped_secret=len(skipped), skipped_secret=skipped, integrity_counts={k: sum(1 for r in rows if r["integrity"] == k) for k in ("UNCHANGED", "APPEND_ONLY_GREW")},
          append_only_grew=[r["rel"] for r in rows if r["integrity"] == "APPEND_ONLY_GREW"], exec_head=HEAD, C_cfg=C_cfg, C_code=C_code, git_exports=gitrows,
          manifest_sha256=shaf(PRIV + "/COPY_SHA256.txt"), n_manifest=len(manifest), research_inputs_sha256={os.path.relpath(k, T5B): v for k, v in ext.items()},
          env=dict(whitelist=sorted(WHITE), actual={k: os.environ[k] for k in sorted(os.environ)}), python=sys.version.split()[0], wall_s=round(time.time() - t0, 1))
json.dump(RC, open(T5B + "/receipts/RECEIPT_T5b_copy.json", "w"), indent=1)
print("COPY_SUMMARY copied", len(rows), "missing", len(missing), "skipped_secret", len(skipped), "git_exports", sum(1 for g in gitrows if g.get("present")), "C_cfg", len(C_cfg), "C_code", len(C_code),
      "append_only_grew", RC["integrity_counts"]["APPEND_ONLY_GREW"], "exec_head", HEAD[:9], "manifest", RC["manifest_sha256"][:12], "wall_s", RC["wall_s"])
