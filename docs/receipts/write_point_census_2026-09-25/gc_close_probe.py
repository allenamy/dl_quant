#!/usr/bin/env python3
"""gc_close_probe.py — does a write error reach the caller under the idiom `json.dump(obj, open(path, "w"))` (handle never closed
explicitly, so the final buffer is flushed by the implicit close at garbage collection)? A raw file whose every write fails with ENOSPC
stands in for a full disk (macOS has no /dev/full). Control: the same dump inside `with open(...)`. No file is written."""
import errno, gc, io, json, sys


class FullDisk(io.RawIOBase):
    def writable(self): return True
    def write(self, b): raise OSError(errno.ENOSPC, "No space left on device (simulated)")


def opened():
    return io.TextIOWrapper(io.BufferedWriter(FullDisk()), encoding="utf-8")


for label, obj in (("small object (< buffer)", {"k": 1}), ("large object (> buffer)", {"k": "x" * 100000})):
    try:
        json.dump(obj, opened()); gc.collect()
        print(f"IDIOM json.dump(obj, open(p,'w')) {label}: NO exception reached the caller")
    except OSError as e:
        print(f"IDIOM json.dump(obj, open(p,'w')) {label}: exception propagated: {e}")
    try:
        with opened() as f:
            json.dump(obj, f)
        print(f"CONTROL with-block {label}: NO exception reached the caller")
    except OSError as e:
        print(f"CONTROL with-block {label}: exception propagated: {e}")
print("python", sys.version.split()[0])
