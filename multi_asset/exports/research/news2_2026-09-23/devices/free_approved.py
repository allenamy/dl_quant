"""Free ONLY the 0.776 GiB lead approved, each item verified against a receipt before deletion.

Rule I am applying to myself: nothing is deleted whose evidentiary role is not already discharged by a
receipt that survives it. For each item: state what receipt carries the conclusion, record the item's
size and (for files) its sha BEFORE deleting, then delete. Nothing belonging to another agent is touched.

usage: python free_approved.py <out.json>   (--dry-run to only report)
"""
import hashlib, json, os, shutil, subprocess, sys, time

W = "/dev/shm/news2_2026-09-23"
DRY = "--dry-run" in sys.argv
OUT = [a for a in sys.argv[1:] if not a.startswith("--")][0]

ITEMS = [
    {"path": f"{W}/work/king_run1_wrongenv",
     "why_safe": ("the comparison this directory existed for is recorded IN FULL in "
                  "receipts/KING_ENV_SENSITIVITY.json, including the per-array result (P: 8,566,057 cells, "
                  "0 different). Deleting the artefacts does not weaken that conclusion."),
     "receipt": f"{W}/receipts/KING_ENV_SENSITIVITY.json",
     "receipt_must_contain": "array_comparison"},
    {"path": f"{W}/work/king_run3_syspy_envset",
     "why_safe": "same as above; the same receipt carries both comparison arms.",
     "receipt": f"{W}/receipts/KING_ENV_SENSITIVITY.json",
     "receipt_must_contain": "array_comparison"},
    {"path": f"{W}/runs/NEWS2_s42X_scaled_rule_raw_UAFE",
     "why_safe": ("used only by the describe-only extension segment; its numbers are in "
                  "receipts/engine/NEWS2_EXT.json, and its per-file shas are in "
                  "receipts/engine/UPSTREAM_MANIFEST_POST.json."),
     "receipt": f"{W}/receipts/engine/NEWS2_EXT.json",
     "receipt_must_contain": "NEWS2_s42"},
    {"path": f"{W}/runs/NEWS2_s2027X_scaled_rule_raw_UAFE",
     "why_safe": "same as above, seed 2027.",
     "receipt": f"{W}/receipts/engine/NEWS2_EXT.json",
     "receipt_must_contain": "NEWS2_s2027"},
]


def du_gib(p):
    out = subprocess.run(["du", "-sk", p], capture_output=True, text=True).stdout.split()
    return round(int(out[0]) / 1048576, 4) if out else None


def free_gib():
    return round(int(subprocess.run(["df", "-k", "/dev/shm"], capture_output=True,
                                    text=True).stdout.splitlines()[-1].split()[3]) / 1048576, 4)


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 24), b""): h.update(b)
    return h.hexdigest()


before = free_gib()
done, refused = [], []
for it in ITEMS:
    p = it["path"]
    if not os.path.exists(p):
        refused.append({**it, "REFUSED": "path does not exist"})
        continue
    if not os.path.exists(it["receipt"]):
        refused.append({**it, "REFUSED": f"receipt missing: {it['receipt']}"})
        continue
    txt = open(it["receipt"], errors="replace").read()
    if it["receipt_must_contain"] not in txt:
        refused.append({**it, "REFUSED": f"receipt does not contain {it['receipt_must_contain']!r}"})
        continue
    size = du_gib(p)
    files = sorted(os.path.join(r, f) for r, _d, fs in os.walk(p) for f in fs)
    manifest = [{"rel": os.path.relpath(f, p), "bytes": os.path.getsize(f), "sha256": sha(f)}
                for f in files[:200]]
    rec = {"path": p, "gib": size, "n_files": len(files), "why_safe": it["why_safe"],
           "receipt": it["receipt"], "receipt_sha256": sha(it["receipt"]),
           "file_manifest_first_200": manifest}
    if not DRY:
        shutil.rmtree(p)
        rec["deleted"] = True
    else:
        rec["deleted"] = False
    done.append(rec)

after = free_gib()
out = {"receipt": os.path.basename(OUT), "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
       "authority": "lead 2026-09-24: only the 0.776 GiB listed; runs/NEWS2_s2027* untouched",
       "dry_run": DRY, "shm_free_gib_before": before, "shm_free_gib_after": after,
       "freed_gib_measured": round(after - before, 4),
       "deleted": done, "refused": refused,
       "not_touched": ["runs/NEWS2_s2027_* (6 dirs, 2.02 GiB): s2027 is the seed whose A gate failed and "
                       "its path-level numbers are the only material behind that finding",
                       "anything outside /dev/shm/news2_2026-09-23 (other agents)"],
       "consequence": ("UPSTREAM_MANIFEST_PRE/POST were taken BEFORE this deletion and still list the two X "
                       "run dirs. A future manifest comparison will therefore show them missing; that is "
                       "this deletion, not drift. The pre-deletion manifests remain the reference.")}
json.dump(out, open(OUT, "w"), indent=1)
print(f"FREE {'DRY-RUN ' if DRY else ''}deleted={len(done)} refused={len(refused)} "
      f"free {before} -> {after} GiB (freed {out['freed_gib_measured']})")
for d in done:
    print(f"   {'would free' if DRY else 'freed'} {d['gib']} GiB  {d['path']}")
for r in refused:
    print(f"   REFUSED {r['path']}: {r['REFUSED']}")
