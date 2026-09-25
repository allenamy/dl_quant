"""dlarch_t3_preflight.py -- check EVERY path T3 will read, before spending GPU time on it.

WHY (lead ruling 2026-09-25, item (d)2): the bulk data (NEWS_FEATURES.npz 2.96 GB, legs.npz, two
receipt json) stays in news2's volatile /dev/shm because it does not fit my /workspace quota. The
trainer already asserts those shas per fold, so a change cannot corrupt a result silently -- but it
would surface as a crash in fold 7 of 14, after an hour of GPU. This device moves that failure to
second 5, and it fails with the NAME of the offending path instead of a generic loader error.

EXPECTATIONS ARE DERIVED, NOT RETYPED. Every sha this device checks comes from an artifact that
already recorded it:
  * the 7 code sources and the 4 bulk inputs  <- the DELIVERED TRAIN_RECEIPT of a T0 family member,
    i.e. exactly the values the family was trained against;
  * the 2 vendored data files                 <- the vendor manifest (VENDOR_NEWS2_20260923.json);
  * MASK_PATH / NEWT / NEWT_SHA               <- parsed out of the trainer SOURCE with ast, so this
    device cannot drift from the trainer by retyping a constant;
  * UNIVERSE_PATH / SHA                       <- imported from book_universe, which is where the
    trainer gets them too.
Retyping any of these would create a second constant that must agree with the first, and those drift.

It is READ-ONLY: it opens files, hashes them, and writes one receipt. It never trains and never deletes.

usage: dlarch_t3_preflight.py <env-whitelist> <t3-dir> <delivered-seed-dir> <vendor-manifest> <out.json>
"""
import os, sys, ast, json, time, hashlib

WL = set(sys.argv[1].split(","))
_x = sorted(set(os.environ) - WL)
assert not _x, f"env outside whitelist: {_x}"
T3DIR, SEEDDIR, MANIFEST, OUT = sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5]


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(16 << 20), b""):
            h.update(b)
    return h.hexdigest()


def consts_from_source(path, names):
    """Read module-level string constants out of the trainer WITHOUT importing it (no torch, no CUDA).
    Reading the producer's own source beats retyping its values into this file.

    Accepts both `X = '...'` and `X = pathlib.Path('...')`: the trainer uses the wrapped form, and a
    reader that only understood plain strings would have reported the name as absent. The assert below
    is what turned that into a stop instead of a silently unchecked path."""
    tree = ast.parse(open(path).read())
    found = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            nm = node.targets[0].id
            if nm not in names:
                continue
            v = node.value
            if isinstance(v, ast.Constant) and isinstance(v.value, str):
                found[nm] = v.value
            elif (isinstance(v, ast.Call) and len(v.args) == 1
                  and isinstance(v.args[0], ast.Constant) and isinstance(v.args[0].value, str)):
                # pathlib.Path('...') -- the trainer wraps paths, so a plain-Constant reader would
                # report the name "not found" and (before the assert) silently skip checking that path
                found[nm] = v.args[0].value
    missing = sorted(set(names) - set(found))
    assert not missing, f"constants not found in {path} as plain string assignments: {missing}"
    return found


trainer = os.path.join(T3DIR, "dlarch_train_f10.py")
assert os.path.exists(trainer), f"no trainer at {trainer}"
C = consts_from_source(trainer, {"NEWT", "NEWT_SHA", "MASK_PATH", "REF_SHA",
                                 "BUNDLE_CFG_SHA", "P1_MEMBERS_SHA"})

# expectations from the delivered family member: these are the values the family was trained against
rec = json.load(open(os.path.join(SEEDDIR, "TRAIN_RECEIPT.json")))
expect = {}
for p, h in rec["inputs"].items():
    expect[p] = (h, "delivered TRAIN_RECEIPT inputs")
for p, h in rec["sources"].items():
    expect[p] = (h, "delivered TRAIN_RECEIPT sources")

# the T3 run reads CODE from the vendor tree under T3DIR, not from the delivered paths. Remap the code
# entries onto the vendored copies, keeping the delivered sha as the expectation -- the whole point of
# the one-cell bitwise check was that the bytes are the same, so the sha must carry over unchanged.
man = json.load(open(MANIFEST))
vend = os.path.join(T3DIR, "vendor_news2_20260923")
for rel, row in man["files"].items():
    if row.get("status") != "OK":
        continue
    p = os.path.join(vend, rel)
    expect[p] = (row["sha256"], f"vendor manifest ({rel})")
# drop the /dev/shm CODE paths: T3 no longer reads those, and asserting them would re-create the
# dependency this vendoring removed. The BULK /dev/shm data paths stay, because T3 still reads them.
for p in list(expect):
    if p.startswith("/dev/shm/") and p.endswith(".py"):
        del expect[p]

# T3 runs the COPIES under T3DIR, not the delivered paths. Check those too: without this, a corrupted
# t3_2026-09-25/dlarch_chain_torch.py would pass a preflight that only looked at the delivered original.
# Where the delivered receipt pins the counterpart's sha, require the copy to match it byte for byte.
for fn in sorted(f for f in os.listdir(T3DIR) if f.endswith(".py")):
    cp = os.path.join(T3DIR, fn)
    orig = next((q for q in rec["sources"] if os.path.basename(q) == fn and not q.startswith("/dev/shm/")), None)
    if orig is not None and os.path.basename(orig) != "dlarch_train_f10.py":
        expect[cp] = (rec["sources"][orig], f"delivered sources, same basename ({fn})")
    elif fn != "dlarch_train_f10.py":
        expect[cp] = (None, f"T3 code copy, no frozen sha exists yet ({fn})")

# constants the T3 branch reads that no receipt covers yet (no T3 artifact exists to derive them from)
expect[C["NEWT"]] = (C["NEWT_SHA"], "trainer source NEWT_SHA")
sys.path.insert(0, os.path.join(vend, "devices"))
import book_universe as BU                                              # noqa: E402  (numpy only)
expect[BU.PATH] = (BU.SHA, "book_universe.SHA")
expect[C["MASK_PATH"]] = (None, "MASK_PATH -- existence only; the trainer sha-stamps it at run time "
                                "into inputs rather than asserting a frozen value")

rows, bad = {}, []
for p, (want, src) in sorted(expect.items()):
    if not os.path.exists(p):
        rows[p] = {"status": "MISSING", "expected_from": src}
        bad.append(p)
        continue
    got = sha(p)
    if want is None:
        rows[p] = {"status": "PRESENT_NO_SHA_PINNED", "sha256": got, "bytes": os.path.getsize(p),
                   "expected_from": src}
        continue
    ok = got.startswith(want) if len(want) < 64 else got == want
    rows[p] = {"status": "OK" if ok else "SHA_MISMATCH", "sha256": got, "expected": want,
               "bytes": os.path.getsize(p), "expected_from": src}
    if not ok:
        bad.append(p)

rec_out = {"device": "dlarch_t3_preflight.py", "self_sha256": sha(os.path.abspath(__file__)),
           "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "t3_dir": os.path.abspath(T3DIR), "trainer_sha256": sha(trainer),
           "delivered_reference": os.path.abspath(SEEDDIR),
           "n_paths": len(rows), "all_ok": not bad, "failures": bad, "paths": rows,
           "scope_note": ("CODE is expected under the vendor tree; BULK data is still expected in "
                          "news2's /dev/shm and that residual dependency is deliberate (quota) -- it is "
                          "an availability exposure, not a correctness one, because the trainer asserts "
                          "these same shas per fold."),
           "expectations_are_derived": ("from the delivered TRAIN_RECEIPT, the vendor manifest, the "
                                        "trainer source via ast, and book_universe -- nothing retyped, "
                                        "because a second copy of a constant drifts from the first.")}
tmp = OUT + ".tmp"
with open(tmp, "w") as f:
    json.dump(rec_out, f, indent=1)
    f.flush()
    os.fsync(f.fileno())
os.replace(tmp, OUT)
back = json.load(open(OUT))
assert back == rec_out, "preflight receipt read back differs from what was written"

for p, v in sorted(rows.items()):
    print("  %-14s %-58s %s" % (v["status"], p[-58:], v.get("sha256", "")[:16]))
print("T3_PREFLIGHT all_ok=%s n_paths=%d receipt=%s" % (rec_out["all_ok"], len(rows), OUT))
assert not bad, f"T3 preflight FAILED for: {bad}"
