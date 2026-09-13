"""Copy FX-TRAIN work files into the research repo with drift protection.
usage: fx_sync_to_repo.py <base_dir> <work_dir> <repo_dir> file [file ...]
For each file: if it exists in base, the repo copy must still equal the base copy (else REFUSE: someone changed it since the audit copy);
if it does not exist in base it must not exist in the repo (new file). Then copy work -> repo and verify sha equality (dataless/short-read guarded)."""
import hashlib, os, shutil, stat, sys
SF = 0x40000000
def sha(p):
    st = os.stat(p)
    if st.st_flags & SF: raise SystemExit(f"REFUSE dataless {p}")
    h = hashlib.sha256(); n = 0
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b); n += len(b)
    if n != st.st_size: raise SystemExit(f"REFUSE short read {p}")
    return h.hexdigest()
base, work, repo = sys.argv[1:4]; files = sys.argv[4:]; plan = []
for f in files:
    b, w, r = os.path.join(base, f), os.path.join(work, f), os.path.join(repo, f)
    if not os.path.exists(w): raise SystemExit(f"REFUSE work file missing {w}")
    if os.path.exists(b):
        if not os.path.exists(r) or sha(r) != sha(b): raise SystemExit(f"REFUSE repo drift: {r} != base {b}")
        plan.append((f, "MODIFY", sha(b)))
    else:
        if os.path.exists(r): raise SystemExit(f"REFUSE new file already in repo: {r}")
        plan.append((f, "NEW", None))
for f, kind, old in plan:
    w, r = os.path.join(work, f), os.path.join(repo, f); os.makedirs(os.path.dirname(r), exist_ok=True)
    shutil.copyfile(w, r); shutil.copymode(w, r)
    sw, sr = sha(w), sha(r)
    if sw != sr: raise SystemExit(f"REFUSE copy mismatch {f}")
    print(f"{kind:6s} {f}  {(old or '-')[:16]} -> {sr[:16]}")
print(f"SUMMARY fx_sync_to_repo n={len(plan)} OK")
