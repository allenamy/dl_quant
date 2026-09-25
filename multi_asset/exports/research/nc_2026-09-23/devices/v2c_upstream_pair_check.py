#!/usr/bin/env python3
"""Read-only replacement for "read N and the per-file list from drift_gate's output" (lead 2026-09-25 ~10:1xZ). That reading is not possible:
the guard prints `no drift across {len(manifest lines)} vendored modules` and no per-file list, and it SKIPS a manifest entry whose upstream
file is missing (`continue  # retired upstream file`) — measured 2026-09-25 10:1xZ with the candidate guard (6cc11cc) against a staged upstream:
durable_io.py ABSENT ⇒ "no drift across 6 … all covered" rc 0; PRESENT and equal ⇒ the identical line rc 0; PRESENT and altered ⇒ DRIFT rc 1.
So the output line cannot show whether durable_io.py was compared. This check measures the pair directly, per A-set entry of the manifest:
  both files exist (research <QR>/multi_asset/engine/live/<name>, executor <tree>/live/<name>), both readable within a timeout (iCloud),
  sha(research) == sha(executor) == the manifest sha. Status per name: COMPARED_EQUAL | MISSING_RESEARCH | MISSING_LOCAL | UNREADABLE | DIFFERENT.
PASS iff every entry is COMPARED_EQUAL and the count == --expect-n (written in the window checklist before the window: 6).
usage: /usr/bin/python3 v2c_upstream_pair_check.py <executor tree> --expect-n 6 [--out F]"""
import hashlib, os, subprocess, sys

QR = os.path.expanduser("~/Desktop/quant_research"); UP = f"{QR}/multi_asset/engine/live"


def sha_timeout(p, t=30):
    try:
        r = subprocess.run(["/usr/bin/python3", "-c", "import hashlib,sys; print(hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest())", p],
                           capture_output=True, text=True, timeout=t)
        return r.stdout.strip() if r.returncode == 0 else None
    except subprocess.TimeoutExpired:
        return None


def main():
    tree = os.path.abspath(sys.argv[1]); a = sys.argv[2:]
    n_exp = int(a[a.index("--expect-n") + 1]); out = a[a.index("--out") + 1] if "--out" in a else None
    lines = [l.split() for l in open(f"{tree}/ops/UPSTREAM_MANIFEST.sha256") if l.strip() and not l.startswith("#")]
    rows, L = [], []
    for h, name, *rest in lines:
        rp, lp = f"{UP}/{name}", f"{tree}/live/{name}"
        if not os.path.exists(rp): st, rs, ls_ = "MISSING_RESEARCH", None, None
        elif not os.path.exists(lp): st, rs, ls_ = "MISSING_LOCAL", None, None
        else:
            rs, ls_ = sha_timeout(rp), sha_timeout(lp)
            st = "UNREADABLE" if rs is None or ls_ is None else ("COMPARED_EQUAL" if rs == ls_ == h else "DIFFERENT")
        rows.append((name, rest[0] if rest else "?", st)); L.append(f"  {st:16s} {name} [{rest[0] if rest else '?'}] manifest={h[:12]} research={(rs or '-')[:12]} executor={(ls_ or '-')[:12]}")
    n_eq = sum(r[2] == "COMPARED_EQUAL" for r in rows)
    ok = n_eq == len(rows) == n_exp
    L.append(f"UPSTREAM_PAIR_CHECK {'PASS' if ok else 'RED'} compared_equal={n_eq} manifest_entries={len(rows)} expected={n_exp} "
             f"durable_io={next((r[2] for r in rows if r[0] == 'durable_io.py'), 'NOT_IN_MANIFEST')}")
    print("\n".join(L))
    if out: open(out, "w").write("\n".join(L) + "\n")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
