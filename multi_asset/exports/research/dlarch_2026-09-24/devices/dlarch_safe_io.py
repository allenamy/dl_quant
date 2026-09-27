#!/usr/bin/env python3
"""dlarch_safe_io.py -- artifact writes whose sha256 is taken only AFTER the bytes are read back.

WHY (E-0925-A class, observed 2026-09-25 on pod2):
  /workspace quota exhaustion produced a file of exactly the right SIZE with a 200-byte NUL tail.
  The receipt's sha256 was then computed over that file, so the receipt CERTIFIED the truncated
  artifact. Neither guard in the reference recipe can see this:
    * a size check cannot -- the size was right;
    * a post-write sha cannot -- it hashes the damage and reports it as identity.
  The only instrument with power is: read the artifact back through the SAME reader that a consumer
  would use, compare to what we meant to write, and only then hash.

CLASS-SHAPED, not instance-shaped:
  Fixing the three call sites I happen to know about would leave a call site added tomorrow
  unprotected. So after the helpers are defined, install_guards() SHADOWS the raw writers
  (np.savez_compressed, np.savez, torch.save) with functions that raise. A new direct call site
  therefore fails loudly at runtime.
  This is deliberately a BEHAVIOURAL guard, not a grep over our own source text: a textual
  instrument for a behavioural property is a known defect form in this project's ledger.

RED CONTROLS (selftest, all must fail-to-pass):
  R1 NUL tail, size preserved  -- reproduces the observed failure mode exactly
  R2 tail truncated           -- the ordinary short-write mode
  R3 one flipped value byte   -- proves the comparison is bitwise, not structural
  R4 guard fires on a raw call
A green selftest without R1-R4 failing would mean the verification is vacuous.

DURABILITY (2026-09-27, October chain contract C1, news2 review): the temp file is fsync'd before its read-back and the
directory is fsync'd after os.replace, in all three writers (write_json / save_npz / save_torch). Before this, a power loss
after the replace could have lost a verified write. The four raw-write sites the contract scanner sees are this module's own
temp write (the verified writer itself) and three deliberate selftest fixtures; each carries a reasoned durable-exempt comment.
"""
import hashlib
import json
import os
import pathlib
import sys

import numpy as np

_ORIG_SAVEZ_COMPRESSED = np.savez_compressed
_ORIG_SAVEZ = np.savez
_ORIG_TORCH_SAVE = None  # bound in install_guards() if torch is present

_IN_HELPER = False  # only the helpers in this module may reach the raw writers


def _fsync_path(p):
    fd = os.open(str(p), os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _tmp_for(path: "pathlib.Path") -> "pathlib.Path":
    """`a/b.npz` -> `a/b.tmp.npz`. The suffix MUST be preserved: np.savez_compressed silently
    appends '.npz' when the name does not end in it, so a `b.npz.tmp` temp becomes `b.npz.tmp.npz`
    and the read-back then looks for a file that was never written. (The reference recipe names its
    temp `F10_OOF.tmp.npz` for exactly this reason.) Found by this module's own read-back check."""
    return path.with_name(path.stem + ".tmp" + path.suffix)


class ArtifactVerifyError(AssertionError):
    """Raised when an artifact does not read back as what we wrote. Never catch this."""


def sha(p) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def _verify_npz(path, arrays: dict):
    """Read back through numpy and compare bitwise. Raises ArtifactVerifyError on any difference."""
    try:
        with np.load(path, allow_pickle=False) as z:
            got_keys = set(z.files)
            want_keys = set(arrays)
            if got_keys != want_keys:
                raise ArtifactVerifyError(
                    f"{path}: keys read back {sorted(got_keys)} != written {sorted(want_keys)}")
            for k, want in arrays.items():
                want = np.asarray(want)
                back = z[k]
                if back.shape != want.shape:
                    raise ArtifactVerifyError(f"{path}[{k}]: shape {back.shape} != {want.shape}")
                if back.dtype != want.dtype:
                    raise ArtifactVerifyError(f"{path}[{k}]: dtype {back.dtype} != {want.dtype}")
                # tobytes() compares NaN bit patterns exactly, which is what identity means here.
                if back.tobytes() != want.tobytes():
                    raise ArtifactVerifyError(f"{path}[{k}]: bytes differ on read-back")
    except ArtifactVerifyError:
        raise
    except Exception as e:  # a truncated / NUL-tailed container usually fails to parse at all
        raise ArtifactVerifyError(f"{path}: unreadable on read-back ({type(e).__name__}: {e})")


def save_npz(path, **arrays) -> str:
    """savez_compressed -> read back -> compare bitwise -> atomic replace -> re-hash. Returns sha256."""
    global _IN_HELPER
    path = pathlib.Path(path)
    tmp = _tmp_for(path)
    _IN_HELPER = True
    try:
        _ORIG_SAVEZ_COMPRESSED(tmp, **arrays)
    finally:
        _IN_HELPER = False
    _fsync_path(tmp)
    _verify_npz(tmp, arrays)
    want = sha(tmp)
    os.replace(tmp, path)
    _fsync_path(path.parent)
    got = sha(path)
    if got != want:
        raise ArtifactVerifyError(f"{path}: sha changed across replace ({got[:16]} != {want[:16]})")
    _verify_npz(path, arrays)  # and it still reads back correctly at its final name
    return got


def write_json(path, obj) -> str:
    """json.dumps(allow_nan=False) -> read back -> compare canonical form -> atomic replace. Returns sha256."""
    path = pathlib.Path(path)
    tmp = _tmp_for(path)
    text = json.dumps(obj, indent=2, allow_nan=False, sort_keys=False)
    tmp.write_text(text)  # durable-exempt: this IS the verified writer -- temp write, fsync, read-back compare, atomic replace, fsync dir
    _fsync_path(tmp)
    back = tmp.read_text()
    if back != text:
        raise ArtifactVerifyError(f"{path}: text read back differs ({len(back)} vs {len(text)} chars)")
    canon = json.dumps(obj, sort_keys=True, allow_nan=False)
    if json.dumps(json.loads(back), sort_keys=True, allow_nan=False) != canon:
        raise ArtifactVerifyError(f"{path}: json does not round-trip")
    want = sha(tmp)
    os.replace(tmp, path)
    _fsync_path(path.parent)
    got = sha(path)
    if got != want:
        raise ArtifactVerifyError(f"{path}: sha changed across replace")
    if json.dumps(json.loads(path.read_text()), sort_keys=True, allow_nan=False) != canon:
        raise ArtifactVerifyError(f"{path}: json does not round-trip at final name")
    return got


def save_torch(path, obj) -> str:
    """torch.save -> torch.load -> compare tensors bitwise -> atomic replace -> re-hash. Returns sha256."""
    global _IN_HELPER
    import torch
    path = pathlib.Path(path)
    tmp = _tmp_for(path)
    _IN_HELPER = True
    try:
        (_ORIG_TORCH_SAVE or torch.save)(obj, tmp)
    finally:
        _IN_HELPER = False
    _fsync_path(tmp)
    try:
        back = torch.load(tmp, map_location="cpu", weights_only=True)
    except Exception as e:
        raise ArtifactVerifyError(f"{path}: unreadable on read-back ({type(e).__name__}: {e})")
    def _flat(d, pre=""):
        out = {}
        if isinstance(d, dict):
            for k, v in d.items():
                out.update(_flat(v, f"{pre}{k}."))
        elif hasattr(d, "detach"):
            out[pre[:-1]] = d.detach().cpu().numpy()
        return out
    fa, fb = _flat(obj), _flat(back)
    if set(fa) != set(fb):
        raise ArtifactVerifyError(f"{path}: tensor keys differ on read-back")
    for k in fa:
        if fa[k].shape != fb[k].shape or fa[k].dtype != fb[k].dtype or fa[k].tobytes() != fb[k].tobytes():
            raise ArtifactVerifyError(f"{path}[{k}]: tensor differs on read-back")
    want = sha(tmp)
    os.replace(tmp, path)
    _fsync_path(path.parent)
    got = sha(path)
    if got != want:
        raise ArtifactVerifyError(f"{path}: sha changed across replace")
    return got


def install_guards():
    """Shadow the raw writers so a call site that bypasses verification raises at runtime."""
    global _ORIG_TORCH_SAVE

    def _mk(name):
        def _forbidden(*a, **k):
            if _IN_HELPER:
                return {"np.savez_compressed": _ORIG_SAVEZ_COMPRESSED,
                        "np.savez": _ORIG_SAVEZ,
                        "torch.save": _ORIG_TORCH_SAVE}[name](*a, **k)
            raise RuntimeError(
                f"{name} called directly: artifact writes must go through dlarch_safe_io "
                f"(save_npz / write_json / save_torch) so the sha is taken after read-back (E-0925-A)")
        return _forbidden

    np.savez_compressed = _mk("np.savez_compressed")
    np.savez = _mk("np.savez")
    if "torch" in sys.modules:
        import torch
        if _ORIG_TORCH_SAVE is None:
            _ORIG_TORCH_SAVE = torch.save
        torch.save = _mk("torch.save")


# ----------------------------------------------------------------------------- selftest
def _expect_raise(label, fn):
    try:
        fn()
    except ArtifactVerifyError as e:
        print(f"  RED-OK   {label}: {type(e).__name__}: {str(e)[:90]}")
        return True
    except RuntimeError as e:
        print(f"  RED-OK   {label}: RuntimeError: {str(e)[:90]}")
        return True
    print(f"  RED-FAIL {label}: no exception -- the check is VACUOUS")
    return False


def selftest(workdir):
    w = pathlib.Path(workdir)
    w.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(20260925)
    A = rng.standard_normal((400, 64)).astype(np.float32)
    A[3, 5] = np.nan  # NaN must survive read-back bitwise
    B = np.arange(400, dtype=np.int64)
    ok = True

    print("GREEN: an honest write verifies and returns a sha")
    p = w / "green.npz"
    s = save_npz(p, P=A, rows=B)
    print(f"  sha={s[:16]} size={p.stat().st_size}")
    ok &= s == sha(p)
    pj = w / "green.json"
    sj = write_json(pj, {"a": 1, "b": [1, 2, 3], "c": "x"})
    ok &= sj == sha(pj)
    print(f"  json sha={sj[:16]}")

    print("RED controls (each MUST raise, else verification is decoration)")

    # R1: the observed failure mode -- NUL tail, size preserved.
    p1 = w / "r1.npz"
    save_npz(p1, P=A, rows=B)
    n = p1.stat().st_size
    with open(p1, "r+b") as f:  # durable-exempt: selftest red control R1 corrupts its own fixture on purpose
        f.seek(-200, os.SEEK_END)
        f.write(b"\0" * 200)
    assert p1.stat().st_size == n, "R1 must preserve size to model E-0925-A"
    ok &= _expect_raise("R1 NUL tail, size preserved", lambda: _verify_npz(p1, {"P": A, "rows": B}))

    # R2: ordinary short write.
    p2 = w / "r2.npz"
    save_npz(p2, P=A, rows=B)
    with open(p2, "r+b") as f:  # durable-exempt: selftest red control R2 truncates its own fixture on purpose
        f.truncate(p2.stat().st_size - 512)
    ok &= _expect_raise("R2 tail truncated", lambda: _verify_npz(p2, {"P": A, "rows": B}))

    # R3: a single flipped byte inside a value -- proves the compare is bitwise.
    p3 = w / "r3.npz"
    save_npz(p3, P=A, rows=B)
    A2 = A.copy()
    A2[7, 7] = np.float32(A2[7, 7] + np.float32(1e-7))
    ok &= _expect_raise("R3 one changed value", lambda: _verify_npz(p3, {"P": A2, "rows": B}))

    # R4: the behavioural guard stops a bypassing call site.
    install_guards()
    ok &= _expect_raise("R4 guard on raw np.savez_compressed",
                        lambda: np.savez_compressed(w / "r4.npz", P=A))  # durable-exempt: selftest red control R4, the guard must raise
    print("GREEN after guards: the helpers still work (they hold the original writer)")
    s2 = save_npz(w / "green2.npz", P=A, rows=B)
    ok &= s2 == s  # same arrays, same bytes
    print(f"  sha={s2[:16]} equal_to_first={s2 == s}")

    for f in list(w.glob("*.tmp.*")) + list(w.glob("*.tmp")):
        ok = False
        print(f"  LEAK: temporary left behind: {f}")

    print(f"DLARCH_SAFE_IO_SELFTEST={'GREEN' if ok else 'RED'}")
    return 0 if ok else 1


if __name__ == "__main__":
    WL = set(sys.argv[1].split(","))
    extra = sorted(set(os.environ) - WL)
    assert not extra, f"env outside whitelist: {extra}"
    print(f"self_sha256={sha(os.path.abspath(__file__))}")
    sys.exit(selftest(sys.argv[2]))
