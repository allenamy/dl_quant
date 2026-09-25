#!/usr/bin/env python3
"""snap_retention.py — producer snapshot retention (user ruling 2026-09-25; docs/DESIGN_snap_retention_2026-09-25.md d60f79588 + correction
df8c6262b). Installed as ~/wide_shadow/fea171/combosnap/snap_retention.py and called by combo_state_snapshot.sh after each successful snapshot;
it REPLACES that script's former `find "$SNAP" -mindepth 1 -maxdepth 1 -type d -mtime +21 -exec rm -rf {} +` (whole-directory deletion).

Rule (RULE_VERSION below):
  * window = the newest COMPLETE snapshot's anchor − 14 × 24 h, by the anchor ts in the directory NAME (never by mtime);
    snapshots inside the window are not touched;
  * outside the window, in a COMPLETE snapshot, a regular file of ≥ 1,000,000 bytes that is not on the keep list is deleted —
    keep list = aux.json (user ruling) and every file below the size bar (SHA256SUMS, generation.json, COMPLETE, PARITY*, combo_live_status,
    leg_returns_live.json, members_hist.npz, boundary_raw.npz, RETENTION_TRIMMED.json …); in practice this deletes only rolling.npz;
  * before each deletion: (1) the file's sha256 is recomputed and must EQUAL its line in that snapshot's SHA256SUMS — a mismatch or a missing
    line ⇒ nothing in that snapshot is deleted and a HIGH page names it (the snapshot is damaged or unsigned); (2) the line
    `<sha256>  <A>/<file>  <bytes>  <deleted_utc>` is appended to the resident list state/snap/RETENTION_DELETED.sha256 (append, flush,
    fsync) and READ BACK (the last line must be exactly that line); (3) the file is removed; (4) RETENTION_TRIMMED.json in the snapshot
    directory lists what was removed (written durably, merged with any earlier record);
  * the resident list is append-only; this tool never truncates or rewrites it.
Readers that need a snapshot's rolling.npz (replays) must refuse a snapshot carrying RETENTION_TRIMMED.json by name.
usage: python snap_retention.py <snap dir> [--window-days 14] [--dry-run]      exit 0 ok · 3 a snapshot refused (HIGH paged)
"""
import hashlib, json, os, sys, time

RULE_VERSION = "snap_retention_v1_2026-09-25"
BAR = 1_000_000
KEEP = {"aux.json"}
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))                      # fea171 (durable_io lives there)
EXECUTOR_ROOT = os.environ.get("DL_QUANT_LIVE_ROOT", os.path.expanduser("~/dl_quant_live"))


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


def page(sev, msg):
    """the same path combo_stage._page uses: the executor's telegram_notify, token / chat id read from its .env only"""
    try:
        sys.path.insert(0, f"{EXECUTOR_ROOT}/live")
        import telegram_notify as TN
        tok = cid = None
        try:
            for ln in open(f"{EXECUTOR_ROOT}/.env"):
                ln = ln.strip()
                if ln.startswith("TELEGRAM_BOT_TOKEN="): tok = ln.split("=", 1)[1].strip().strip('"')
                elif ln.startswith("TELEGRAM_CHAT_ID="): cid = ln.split("=", 1)[1].strip().strip('"')
        except Exception:                          # noqa: BLE001
            pass
        r = TN.TelegramNotifier(token=tok, chat_id=cid).alarm(sev, msg)
        print(f"PAGE {sev} status={r.get('status') if isinstance(r, dict) else r}", flush=True)
    except Exception as e:                         # noqa: BLE001
        print(f"PAGE_FAIL {e!r}"[:200], flush=True)


def append_verified(listing, line):
    with open(listing, "a") as f:
        f.write(line + "\n"); f.flush(); os.fsync(f.fileno())
    with open(listing, "rb") as f:
        f.seek(0, os.SEEK_END); n = f.tell(); f.seek(max(0, n - 4096)); tail = f.read().decode("utf-8", "replace")
    if tail.splitlines()[-1:] != [line]:
        raise OSError(f"resident list read-back does not end with the appended line: {listing}")


def main(argv):
    snap = os.path.abspath(argv[1]); days = 14.0; dry = "--dry-run" in argv
    if "--window-days" in argv: days = float(argv[argv.index("--window-days") + 1])
    import durable_io as DIO
    anchors = sorted(int(d) for d in os.listdir(snap) if d.isdigit() and os.path.isfile(os.path.join(snap, d, "COMPLETE")))
    if not anchors:
        print("SNAP_RETENTION nothing to do (no complete snapshot)"); return 0
    cut = anchors[-1] - int(days * 86400)
    listing = os.path.join(snap, "RETENTION_DELETED.sha256")
    refused, n_del, bytes_del = [], 0, 0
    for A in anchors:
        if A >= cut:
            continue
        d = os.path.join(snap, str(A))
        cand = sorted(f for f in os.listdir(d) if f not in KEEP and os.path.isfile(os.path.join(d, f))
                      and not os.path.islink(os.path.join(d, f)) and os.path.getsize(os.path.join(d, f)) >= BAR)
        if not cand:
            continue
        sums = {}
        try:
            for ln in open(os.path.join(d, "SHA256SUMS")):
                p = ln.split()
                if len(p) >= 2: sums[p[1]] = p[0]
        except OSError:
            pass
        got = {f: sha(os.path.join(d, f)) for f in cand}
        bad = [f for f in cand if sums.get(f) != got[f]]
        if bad:
            refused.append((A, bad)); continue
        if dry:
            print(f"DRY {A}: would delete {cand}"); continue
        rec_p = os.path.join(d, "RETENTION_TRIMMED.json")
        rec = json.load(open(rec_p)) if os.path.isfile(rec_p) else {"rule": RULE_VERSION, "deleted": []}
        for f in cand:
            p = os.path.join(d, f); size = os.path.getsize(p); utc = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            append_verified(listing, f"{got[f]}  {A}/{f}  {size}  {utc}")
            os.remove(p); n_del += 1; bytes_del += size
            rec["deleted"].append({"file": f, "sha256": got[f], "bytes": size, "deleted_utc": utc})
        rec["rule"] = RULE_VERSION; rec["window_days"] = days
        DIO.write_json_durable(rec_p, rec, indent=1)
    for A, bad in refused:
        page("HIGH", f"快照保留: {A} 的大文件与其 SHA256SUMS 不符或未签名 {bad} — 未删除任何文件; 该快照可能已损坏, 请核对。")
    print(f"SNAP_RETENTION window_start={cut} deleted={n_del} bytes={bytes_del} refused={[a for a, _ in refused]} rule={RULE_VERSION}", flush=True)
    return 3 if refused else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
