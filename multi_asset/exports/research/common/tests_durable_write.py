#!/usr/bin/env python3
"""tests_durable_write.py -- red/green tests for common/durable_write.py (news2 class fix of the puller's manifest write, 2026-09-27).

The class: `json.dump(x, open(p, "w"))`, `open(p, "w").write(...)`, `np.savez(p, ...)` straight onto the final path. A short write
(full disk: E-0925 executor defect) leaves a truncated file under the real name and may not raise; a failure after the temp file
exists (puller rev 1, P9 selftest R2) leaves the temp behind -- rev 1's commit message said "no .tmp left" while its own receipt
listed one. Every cell below is a way the write can go wrong, and each must end with: the old file intact, no temp left, and an
exception (never a silent return). Baseline cells come first: a red run of the mutations means nothing if the baseline is red.
usage: python3 -B tests_durable_write.py [out.json]
"""
import hashlib, json, os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if os.environ.get("DW_MODULE_PATH"):        # mutation runs only: load a deliberately weaker implementation under the same name
    import importlib.util
    _spec = importlib.util.spec_from_file_location("durable_write", os.environ["DW_MODULE_PATH"])
    DW = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(DW)
else:
    import durable_write as DW

RES = []
def cell(n, fn):
    try: fn(); RES.append((n, True, ""))
    except AssertionError as e: RES.append((n, False, "assert: %s" % e))
    except Exception as e: RES.append((n, False, "%s: %s" % (type(e).__name__, e)))
def raises(exc, fn, needle=None):
    try: fn()
    except exc as e:
        assert needle is None or needle in str(e), "wrong message: %s" % e
        return e
    raise AssertionError("did not raise %s" % exc.__name__)

def tdir():
    return tempfile.mkdtemp(prefix="dw_test_")
def leftovers(d, keep):
    return sorted(n for n in os.listdir(d) if n not in keep)


# ---- baseline (must be green before any mutation cell means anything) ----
def g1():
    d = tdir(); p = os.path.join(d, "M.json"); body = b'{"a": 1}'
    sha = DW.write_bytes(p, body)
    assert open(p, "rb").read() == body
    assert sha == hashlib.sha256(body).hexdigest(), "returned sha must be the sha of the verified bytes"
    assert leftovers(d, {"M.json"}) == [], leftovers(d, {"M.json"})
cell("G1_write_bytes_roundtrip_no_temp_left", g1)

def g2():
    d = tdir(); p = os.path.join(d, "M.json"); open(p, "wb").write(b"old")
    sha = DW.write_json(p, {"b": [1, 2]}, indent=1)
    body = json.dumps({"b": [1, 2]}, indent=1).encode()
    assert open(p, "rb").read() == body and sha == hashlib.sha256(body).hexdigest()
    assert leftovers(d, {"M.json"}) == []
cell("G2_write_json_replaces_existing_file", g2)

def g3():
    import numpy as np
    d = tdir(); p = os.path.join(d, "X")          # no .npz suffix: np.savez(path) would silently write X.npz
    sha = DW.write_npz(p, a=np.arange(5), s=np.array(["x", "y"]))
    assert os.listdir(d) == ["X"], os.listdir(d)
    z = np.load(p); assert (z["a"] == np.arange(5)).all() and list(z["s"]) == ["x", "y"]
    assert sha == hashlib.sha256(open(p, "rb").read()).hexdigest()
cell("G3_write_npz_exact_path_and_loadable", g3)

def g4():
    d = tdir(); p = os.path.join(d, "M.json")
    old = os.umask(0o022); os.umask(old)
    DW.write_bytes(p, b"x")
    got = os.stat(p).st_mode & 0o777
    assert got == (0o666 & ~old), "mode %o, a plain open() would give %o (mkstemp's 0600 must not leak)" % (got, 0o666 & ~old)
cell("G4_mode_matches_plain_open", g4)

def g5():
    calls = []
    real = DW._fsync_dir
    DW._fsync_dir = lambda d: (calls.append(d), real(d))
    try:
        d = tdir(); DW.write_bytes(os.path.join(d, "M"), b"x")
    finally:
        DW._fsync_dir = real
    assert calls == [d], "the directory entry of the rename must be fsync'd: %s" % calls
cell("G5_directory_fsynced_after_rename", g5)


def g7():
    """Migrating a device from json.dump(rec, f, indent=k) to write_json(..., indent=k, allow_nan=True) must not change a byte."""
    d = tdir(); rec = {"a": float("nan"), "b": [1, 2.5, None], "c": {"x": "\u00e9"}, "inf": float("inf")}
    for k in (1, 2):
        with open(os.path.join(d, "ref%d" % k), "w") as f:  # durable-exempt: reference bytes for the equivalence check
            json.dump(rec, f, indent=k)
        DW.write_json(os.path.join(d, "dw%d" % k), rec, indent=k, allow_nan=True)
        assert open(os.path.join(d, "ref%d" % k), "rb").read() == open(os.path.join(d, "dw%d" % k), "rb").read(), k
cell("G7_write_json_allow_nan_is_byte_identical_to_json_dump", g7)

# ---- red cells: every failure raises, keeps the old file, leaves no temp ----
def r1():
    d = tdir(); p = os.path.join(d, "M.json"); os.makedirs(p)          # the target is a directory: os.replace fails
    raises(OSError, lambda: DW.write_bytes(p, b"new"))
    assert os.path.isdir(p) and leftovers(d, {"M.json"}) == [], leftovers(d, {"M.json"})
cell("R1_replace_fails_no_temp_left", r1)

def r2():
    d = tdir(); p = os.path.join(d, "M.json"); open(p, "wb").write(b"old")
    real = DW._readback
    DW._readback = lambda path: b"short"                                # the bytes on disk are not the bytes we wrote
    try:
        raises(IOError, lambda: DW.write_bytes(p, b"new-body"), "read-back")
    finally:
        DW._readback = real
    assert open(p, "rb").read() == b"old", "old file must be untouched on a failed read-back"
    assert leftovers(d, {"M.json"}) == []
cell("R2_readback_mismatch_raises_keeps_old", r2)

def r3():
    d = tdir(); p = os.path.join(d, "M.json"); open(p, "wb").write(b"old")
    real = os.fsync
    def boom(fd): raise OSError(28, "No space left on device")
    os.fsync = boom
    try:
        raises(OSError, lambda: DW.write_bytes(p, b"new"))
    finally:
        os.fsync = real
    assert open(p, "rb").read() == b"old" and leftovers(d, {"M.json"}) == []
cell("R3_fsync_enospc_raises_keeps_old", r3)

def r4():
    d = tdir(); p = os.path.join(d, "M.json"); open(p, "wb").write(b"old")
    real = DW._write_all
    def short(f, body): f.write(body[: len(body) // 2])                 # a short write that does not raise
    DW._write_all = short
    try:
        raises(IOError, lambda: DW.write_bytes(p, b"0123456789"), "read-back")
    finally:
        DW._write_all = real
    assert open(p, "rb").read() == b"old" and leftovers(d, {"M.json"}) == []
cell("R4_silent_short_write_caught_by_readback", r4)

def r5():
    d = tdir(); p = os.path.join(d, "M.json")
    raises(TypeError, lambda: DW.write_bytes(p, "a str, not bytes"))
    assert leftovers(d, set()) == []
cell("R5_non_bytes_refused_before_any_file", r5)

def r6():
    d = tdir(); p = os.path.join(d, "M.json")
    raises(ValueError, lambda: DW.write_json(p, {"x": float("nan")}))  # NaN is not JSON; json.dump would write it
    assert leftovers(d, set()) == []
cell("R6_json_nan_refused", r6)

def r7():
    raises(FileNotFoundError, lambda: DW.write_bytes(os.path.join(tdir(), "no_such_dir", "M"), b"x"))
cell("R7_missing_directory_raises", r7)


def _npz_mut(mut):
    import io as _io, numpy as np
    d = tdir(); p = os.path.join(d, "X.npz"); open(p, "wb").write(b"old")
    real = DW._npz_writer
    def w(f, arrays):
        b = _io.BytesIO(); np.savez(b, **arrays); f.write(mut(b.getvalue(), arrays))
    DW._npz_writer = w
    try:
        raises(IOError, lambda: DW.write_npz(p, a=np.arange(100000), b=np.ones(10)))
    finally:
        DW._npz_writer = real
    assert open(p, "rb").read() == b"old" and leftovers(d, {"X.npz"}) == [], leftovers(d, {"X.npz"})
cell("R8_npz_truncated_caught", lambda: _npz_mut(lambda b, a: b[: len(b) // 2]))
def _flip(b, a):
    i = len(b) // 3; return b[:i] + bytes([b[i] ^ 0xFF]) + b[i + 1:]
cell("R9_npz_corrupt_byte_caught_by_crc", lambda: _npz_mut(_flip))
def _extra(b, a):
    import io as _io, numpy as np
    x = _io.BytesIO(); np.savez(x, extra=np.zeros(1), **a); return x.getvalue()
cell("R10_npz_member_set_differs_caught", lambda: _npz_mut(_extra))

def g6():
    import numpy as np
    d = tdir(); p = os.path.join(d, "Y.npz")
    real = DW._readback
    DW._readback = lambda path: (_ for _ in ()).throw(AssertionError("write_npz must not load the whole file through _readback"))
    try:
        DW.write_npz(p, a=np.arange(10))
    finally:
        DW._readback = real
cell("G6_npz_streams_not_whole_file_readback", g6)


def main():
    ok = all(r[1] for r in RES)
    for n, p, m in RES:
        print("  [%s] %s %s" % ("PASS" if p else "FAIL", n, m))
    print("DURABLE_WRITE_TESTS %d/%d %s" % (sum(r[1] for r in RES), len(RES), "ALL_PASS" if ok else "RED"))
    if len(sys.argv) > 1:
        body = json.dumps({"device": os.path.abspath(DW.__file__),
                           "device_sha256": hashlib.sha256(open(DW.__file__, "rb").read()).hexdigest(),
                           "tests_sha256": hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest(),
                           "python": sys.version.split()[0], "cells": [{"name": n, "pass": p, "msg": m} for n, p, m in RES],
                           "ALL_PASS": ok}, indent=1).encode()
        print("receipt_sha256", DW.write_bytes(sys.argv[1], body))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
