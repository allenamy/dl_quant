#!/usr/bin/env python3
"""dlarch_artifact_audit.py -- does any published dlarch number rest on a damaged artifact?

WHY: the /workspace quota bit while dlarch runs were writing (E-0925-A). Artifacts written before
`dlarch_safe_io` existed took their sha AFTER an unverified write, so a receipt could certify a
truncated file. This device re-opens every artifact under the dlarch root and checks it.

WHAT IT CHECKS
  1. every .npz fully READS BACK (each array decompressed -- a size check cannot see NUL padding)
  2. no text artifact has a long NUL run in its tail (the observed size-preserving damage mode)
  3. every .json parses
  4. every recorded `path -> sha256` map (inputs / sources / fold_artifacts) still matches

POSITIVE CONTROL (this is what makes a clean report mean anything):
  dlarch_safe_io's selftest leaves two DELIBERATELY corrupted files behind, out_safeio/r1.npz
  (NUL tail, size preserved) and r2.npz (truncated). This device asserts it FLAGS BOTH. If they are
  absent the control is unavailable and the device says so instead of silently reporting "all clean"
  -- an audit that has never been shown to fail is not evidence of cleanliness.

Read-only: opens files, writes nothing.
"""
import hashlib
import json
import os
import pathlib
import sys

import numpy as np

CONTROL_FILES = {"r1.npz": "NUL tail, size preserved", "r2.npz": "tail truncated"}


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def audit(base: pathlib.Path):
    npz_bad, nul_tail, unparsed, mism = [], [], [], []
    n_npz = n_json = n_sha = 0

    for p in sorted(base.rglob("*.npz")):
        n_npz += 1
        try:
            with np.load(p, allow_pickle=False) as z:
                for k in z.files:
                    a = z[k]
                    _ = a.tobytes()[:1] if a.size else b""
        except Exception as e:
            npz_bad.append((p, f"{type(e).__name__}: {str(e)[:60]}"))

    for p in sorted(base.rglob("*")):
        if not p.is_file() or p.is_symlink() or p.suffix not in (".json", ".log", ".md"):
            continue
        n = p.stat().st_size
        if n == 0:
            nul_tail.append((p, "ZERO BYTES"))
            continue
        with open(p, "rb") as f:
            f.seek(max(0, n - 4096))
            if b"\0" * 64 in f.read():
                nul_tail.append((p, f"NUL run in tail, size {n}"))

    for p in sorted(base.rglob("*.json")):
        n_json += 1
        try:
            d = json.loads(p.read_text())
        except Exception as e:
            unparsed.append((p, str(e)[:60]))
            continue
        for key in ("inputs", "sources", "fold_artifacts"):
            m = d.get(key)
            if not isinstance(m, dict):
                continue
            for path, h in m.items():
                if isinstance(h, str) and len(h) == 64 and pathlib.Path(path).exists():
                    n_sha += 1
                    got = sha(path)
                    if got != h:
                        mism.append((p, key, path, h[:16], got[:16]))

    return dict(n_npz=n_npz, n_json=n_json, n_sha=n_sha,
                npz_bad=npz_bad, nul_tail=nul_tail, unparsed=unparsed, mism=mism)


def main():
    WL = set(sys.argv[1].split(","))
    extra = sorted(set(os.environ) - WL)
    assert not extra, f"env outside whitelist: {extra}"
    base = pathlib.Path(sys.argv[2])
    print(f"self_sha256={sha(os.path.abspath(__file__))}")
    print(f"root={base}")
    r = audit(base)
    print(f"npz read back: {r['n_npz']} | json parsed: {r['n_json']} | path->sha re-verified: {r['n_sha']}")

    # ---- positive control, BEFORE any clean verdict is allowed to be printed ----
    flagged = {p.name for p, _ in r["npz_bad"]}
    present = {n for n in CONTROL_FILES if (base / "out_safeio" / n).exists()}
    if not present:
        control = "UNAVAILABLE (out_safeio/r1.npz, r2.npz absent -- rerun dlarch_safe_io selftest to create them)"
    elif present <= flagged:
        control = f"PASS (flagged {sorted(present)})"
    else:
        control = f"FAIL (did NOT flag {sorted(present - flagged)}) -- this audit has no power, ignore its verdict"
    print(f"POSITIVE_CONTROL={control}")

    for label, rows, fmt in (
        ("NPZ_UNREADABLE", r["npz_bad"], lambda x: f"{x[0]}  {x[1]}"),
        ("TEXT_DAMAGED", r["nul_tail"], lambda x: f"{x[0]}  {x[1]}"),
        ("JSON_UNPARSEABLE", r["unparsed"], lambda x: f"{x[0]}  {x[1]}"),
        ("SHA_MISMATCH", r["mism"], lambda x: f"{x[0]} [{x[1]}] {x[2]}  recorded={x[3]} now={x[4]}"),
    ):
        print(f"{label}: {len(rows)}")
        for x in rows:
            print(f"    {fmt(x)}")

    # Findings that are the controls themselves are not findings.
    real_npz = [x for x in r["npz_bad"] if x[0].name not in CONTROL_FILES]
    real = len(real_npz) + len(r["nul_tail"]) + len(r["unparsed"]) + len(r["mism"])
    print(f"DLARCH_ARTIFACT_AUDIT findings_excluding_controls={real} "
          f"control={control.split()[0]}")
    return 0 if real == 0 and control.startswith("PASS") else 1


if __name__ == "__main__":
    sys.exit(main())
