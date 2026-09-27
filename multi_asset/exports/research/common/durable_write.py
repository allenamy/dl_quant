#!/usr/bin/env python3
"""durable_write.py -- the one way a research device writes a file that another device will read (news2, 2026-09-27).

Why: `json.dump(x, open(p, "w"))` and `np.savez(p, ...)` write straight onto the final name. On a full disk the write can come up
short without raising (E-0925 executor defect), leaving a truncated file under the real name; and a failure part-way leaves the old
file already clobbered. Puller rev 1 hand-rolled temp -> fsync -> read-back -> os.replace for its manifest, but left the temp behind
when os.replace failed (its own selftest receipt lists MANIFEST_2026-05.json.tmp while the commit said "no .tmp left") and never
fsync'd the directory. Writing that sequence by hand in each device is how each device ends up with a different subset of it.

    sha = write_bytes(path, body)          # temp in the same dir -> write -> fsync -> read-back == body -> os.replace -> fsync dir
    sha = write_json(path, obj, indent=1)  # allow_nan=False: NaN is not JSON
    sha = write_npz(path, **arrays)        # exactly `path` (np.savez(str) appends .npz when the suffix is missing)

The returned sha256 is of the bytes that were read back and matched, never of a later re-read of the file (E-0925-A).
write_npz streams (NEWS_FEATURES_D10 is 2.96 GB; holding it twice in memory is not free on a shared pod), so its read-back check is
structural instead of byte-equal: the size on disk equals the bytes written, every member passes the zip CRC check, and the member
names are exactly the arrays passed; the sha is computed from that same read-back pass.
Any failure raises, removes the temp, and leaves whatever was at `path` before untouched. The new file gets the mode a plain
open() would have given it (0666 & ~umask), not mkstemp's 0600.
"""
import hashlib
import json
import os
import tempfile
import zipfile


def _write_all(f, body):
    f.write(body)


def _readback(path):
    with open(path, "rb") as f:
        return f.read()


def _fsync_dir(d):
    fd = os.open(d, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _umask():
    old = os.umask(0o022)
    os.umask(old)
    return old


def _commit(path, write_fn, verify_fn):
    """temp in the same dir -> write_fn(f) -> flush -> fsync -> verify_fn(tmp) returns the sha -> os.replace -> fsync dir.
    Any failure removes the temp and leaves `path` as it was."""
    path = os.path.abspath(path)
    d = os.path.dirname(path)
    fd, tmp = tempfile.mkstemp(prefix="." + os.path.basename(path) + ".", suffix=".tmp", dir=d)
    try:
        os.fchmod(fd, 0o666 & ~_umask())
        with os.fdopen(fd, "wb") as f:
            write_fn(f)
            f.flush()
            os.fsync(f.fileno())
        sha = verify_fn(tmp)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass
        raise
    _fsync_dir(d)
    return sha


def write_bytes(path, body):
    if not isinstance(body, (bytes, bytearray)):
        raise TypeError("durable_write.write_bytes needs bytes, got %s" % type(body).__name__)
    body = bytes(body)

    def verify(tmp):
        back = _readback(tmp)
        if back != body:
            raise IOError("read-back differs for %s: wrote %d bytes, read %d" % (path, len(body), len(back)))
        return hashlib.sha256(back).hexdigest()
    return _commit(path, lambda f: _write_all(f, body), verify)


def write_json(path, obj, **dumps_kw):
    dumps_kw.setdefault("allow_nan", False)
    return write_bytes(path, json.dumps(obj, **dumps_kw).encode())


def _npz_writer(f, arrays):
    import numpy as np
    np.savez(f, **arrays)


def write_npz(path, **arrays):
    written = {}

    def write(f):
        _npz_writer(f, arrays)
        written["n"] = f.tell()

    def verify(tmp):
        h = hashlib.sha256()
        n = 0
        with open(tmp, "rb") as f:
            for b in iter(lambda: f.read(1 << 24), b""):
                h.update(b)
                n += len(b)
        if n != written["n"]:
            raise IOError("read-back size differs for %s: wrote %d bytes, read %d" % (path, written["n"], n))
        try:
            with zipfile.ZipFile(tmp) as z:
                bad = z.testzip()
                names = sorted(z.namelist())
        except zipfile.BadZipFile as e:
            raise IOError("read-back of %s is not a valid npz: %s" % (path, e))
        if bad is not None:
            raise IOError("read-back of %s: member %s fails its CRC" % (path, bad))
        want = sorted(k + ".npy" for k in arrays)
        if names != want:
            raise IOError("read-back of %s has members %s, expected %s" % (path, names[:6], want[:6]))
        return h.hexdigest()
    return _commit(path, write, verify)
