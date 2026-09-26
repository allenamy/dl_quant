"""durable_io — state files are written so that a failed write is LOUD and never replaces good bytes.

WHY (E-0925-A class, census quant_research docs/receipts/write_point_census_2026-09-25, 501d80737; DESIGN_executor_durable_state_2026-09-25 B-2):
the idiom `json.dump(obj, open(path, "w"))` never closes its handle explicitly, so the last buffer is flushed by the
implicit close at garbage collection, where a write error is NOT raised to the caller (measured, gc_close_probe.py:
/usr/bin/python3 3.9 loses ENOSPC for an object smaller than the buffer; python 3.14 for every size). Behind a
`tmp + os.replace` that turns a full disk into a SILENT replacement of the good state by an empty / truncated file —
and anchor_loop._load's `except Exception: return default` then turned the damaged file into a silent reset.

`write_json_durable` / `write_bytes_durable`:
  1. the bytes are produced in memory first;
  2. written to a private temporary file in the SAME directory inside `with` (close is explicit, so its errors raise),
     flushed and fsync'ed;
  3. READ BACK and compared byte for byte with the in-memory bytes (catches silent truncation / a short write that
     reported success — the pod2 quota failure shape: same size, zero tail, or a short file);
  4. only then `os.replace` onto the target, and the directory is fsync'ed;
  5. any failure BEFORE the rename: the temporary file is removed, the TARGET IS UNTOUCHED, and `DurableWriteNotReplaced` is raised;
     a failure AFTER the rename (the directory fsync): the TARGET ALREADY HOLDS THE NEW BYTES but the rename may not survive a power
     loss, and `DurableWriteReplacedNotDurable` is raised (R25-10, independent review 7cbe907ba: the single error class used to say
     "the target was NOT replaced" for this case too, which was false). Both subclass `DurableWriteError`, so `except DurableWriteError`
     callers are unchanged; a caller that must know whether the new bytes are in place reads `.replaced`.
The returned sha256 is of the in-memory bytes — a receipt that certifies what was meant, verified to be what was written.
"""
from __future__ import annotations

import hashlib
import json
import os
from typing import Any

__all__ = ["DurableWriteError", "DurableWriteNotReplaced", "DurableWriteReplacedNotDurable", "write_bytes_durable", "write_json_durable"]


class DurableWriteError(OSError):
    """a durable state write failed; see the subclass (and `.replaced`) for whether the target holds the old or the new bytes"""
    replaced = None


class DurableWriteNotReplaced(DurableWriteError):
    """the write failed BEFORE the rename: the target file was left exactly as it was"""
    replaced = False


class DurableWriteReplacedNotDurable(DurableWriteError):
    """the rename SUCCEEDED (the target holds the new, verified bytes) but the directory fsync failed: the rename may not survive a crash"""
    replaced = True


def _fsync_dir(d: str) -> None:
    fd = os.open(d, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def write_bytes_durable(path: str, data: bytes) -> str:
    """write `data` to `path` durably (see module doc). Returns sha256(data). Raises DurableWriteError."""
    if not isinstance(data, (bytes, bytearray)):
        raise TypeError(f"write_bytes_durable needs bytes, got {type(data).__name__}")
    data = bytes(data)
    d = os.path.dirname(os.path.abspath(path)) or "."
    os.makedirs(d, exist_ok=True)
    tmp = os.path.join(d, f".{os.path.basename(path)}.durable-tmp.{os.getpid()}")
    try:
        with open(tmp, "wb") as f:
            n = f.write(data)
            f.flush()
            os.fsync(f.fileno())
        if n != len(data):
            raise DurableWriteNotReplaced(f"short write to {tmp}: {n} of {len(data)} bytes — the target {path} was NOT replaced")
        with open(tmp, "rb") as f:
            back = f.read()
        if back != data:
            raise DurableWriteNotReplaced(f"read-back of {tmp} differs from the bytes written "
                                          f"({len(back)} vs {len(data)} bytes) — the target {path} was NOT replaced")
        os.replace(tmp, path)
    except DurableWriteError:
        _remove_quietly(tmp)
        raise
    except OSError as e:
        _remove_quietly(tmp)
        raise DurableWriteNotReplaced(f"durable write of {path} failed ({type(e).__name__}: {e}) — the target was NOT replaced") from e
    try:                                         # R25-10: after the rename the target HOLDS the new bytes; only the rename's durability is open
        _fsync_dir(d)
    except OSError as e:
        raise DurableWriteReplacedNotDurable(f"durable write of {path}: the target WAS replaced with the new, verified bytes, but the directory "
                                             f"fsync failed ({type(e).__name__}: {e}) — the rename may not survive a power loss") from e
    return hashlib.sha256(data).hexdigest()


def write_json_durable(path: str, obj: Any, *, encoding: str = "utf-8", **dump_kw: Any) -> str:
    """json.dumps(obj, **dump_kw) encoded with `encoding` (UTF-8 unless a caller must keep its former on-disk bytes, e.g. an
    ensure_ascii=False writer that used the locale's encoding), written with write_bytes_durable. Returns sha256 of those bytes."""
    return write_bytes_durable(path, json.dumps(obj, **dump_kw).encode(encoding))


def _remove_quietly(p: str) -> None:
    try:
        if os.path.exists(p):
            os.remove(p)
    except OSError:
        pass
