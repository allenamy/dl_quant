"""One-time tiny cache of the LAST-TIMESTEP slice of the spot/perp npz panels.

Why: ``data/npz_{spot,perp}/<day>.npz`` store ``X`` as a (N,600,64) float32
member that is *uncompressed* (stored) but 73 MB each. The Stage-C1 Ridge gate
only ever needs ``X[:, -1, :]`` (last timestep, 64-dim) plus ``timestamps`` (and
the perp ``y_600`` / ``y_mask_600``). Reading the full 73 MB member per day, for
both venues, on every gate pass (block + 2 sentinel passes) is ~365 GB of
network-storage reads and dominates runtime (>25 min, killed).

This builder memory-maps ONLY the ``X.npy`` member (located by its zip byte
offset; the member is stored uncompressed so mmap is valid) and copies out
``X[:, -1, :]`` — mmap pages in only the touched last-timestep rows, not the full
tensor. It writes a ~120 KB/day cache:

    data/lastts_cache/<day>.npz
        spot_last  (N,64) float32   spot  X[:, -1, :]
        perp_last  (N,64) float32   perp  X[:, -1, :]
        timestamps (N,)   int64     spot timestamps (perp shift asserted constant)
        perp_ts    (N,)   int64     perp timestamps (for the constant-shift guard)
        y_600      (N,)   float32   perp y_600 (the target)
        y_mask_600 (N,)   bool      spot y_mask_600 (same mask GATE A uses)

The gate then reads these tiny files. Bit-identical to slicing the full arrays
(verified by --verify on a few days).

  python multi_asset/data/build_lastts_cache.py --all
  python multi_asset/data/build_lastts_cache.py --verify
"""
from __future__ import annotations

import argparse
import glob
import os
import os.path as p
import struct
import time
import zipfile

import numpy as np

DATA_DIR = "/mnt/storage/private/work_hsy/quant_research_multi_asset/data"
SPOT_DIR = p.join(DATA_DIR, "npz_spot")
PERP_DIR = p.join(DATA_DIR, "npz_perp")
OUT_DIR = p.join(DATA_DIR, "lastts_cache")


def _read_member_array(npz_path: str, member: str, mmap: bool = True):
    """Return a numpy view/array of one .npy member inside an (uncompressed) npz.

    Locates the member's data offset in the zip and parses the .npy header, then
    np.memmap's the data region (member must be STORED, compress_type==0). Falls
    back to a normal np.load member read if the member is compressed."""
    with zipfile.ZipFile(npz_path) as z:
        info = z.getinfo(member)
        if info.compress_type != 0 or not mmap:
            with z.open(member) as f:
                return np.lib.format.read_array(f, allow_pickle=False)
        # offset of the local file header; data starts after header + name + extra
        with open(npz_path, "rb") as f:
            f.seek(info.header_offset)
            sig = f.read(4)
            assert sig == b"PK\x03\x04", f"bad local header sig {sig!r}"
            f.seek(info.header_offset + 26)
            n_name, n_extra = struct.unpack("<HH", f.read(4))
            data_off = info.header_offset + 30 + n_name + n_extra
            # parse the .npy header at data_off
            f.seek(data_off)
            magic = f.read(6)
            assert magic == b"\x93NUMPY", f"bad npy magic {magic!r}"
            major, _minor = struct.unpack("<BB", f.read(2))
            if major == 1:
                (hlen,) = struct.unpack("<H", f.read(2))
                hdr_start = data_off + 10
            else:
                (hlen,) = struct.unpack("<I", f.read(4))
                hdr_start = data_off + 12
            hdr = f.read(hlen).decode("latin1")
        d = eval(hdr, {"__builtins__": {}}, {"False": False, "True": True})
        dtype = np.dtype(d["descr"])
        shape = d["shape"]
        arr_off = hdr_start + hlen
        mm = np.memmap(npz_path, dtype=dtype, mode="r", offset=arr_off,
                       shape=shape, order="F" if d["fortran_order"] else "C")
        return mm


def _last_ts(npz_path: str) -> np.ndarray:
    """X[:, -1, :] as a contiguous float32 copy, via mmap (touches last ts only)."""
    mm = _read_member_array(npz_path, "X.npy", mmap=True)
    out = np.ascontiguousarray(mm[:, -1, :]).astype(np.float32)
    del mm
    return out


def _plain_member(npz_path: str, member: str):
    with zipfile.ZipFile(npz_path) as z:
        with z.open(member) as f:
            return np.lib.format.read_array(f, allow_pickle=False)


def build_day(day: str, force=False) -> str | None:
    out = p.join(OUT_DIR, f"{day}.npz")
    if p.exists(out) and not force:
        return None
    sp = p.join(SPOT_DIR, f"{day}.npz")
    pp = p.join(PERP_DIR, f"{day}.npz")
    if not (p.exists(sp) and p.exists(pp)):
        return None
    spot_last = _last_ts(sp)
    perp_last = _last_ts(pp)
    sts = _plain_member(sp, "timestamps.npy").astype(np.int64)
    pts = _plain_member(pp, "timestamps.npy").astype(np.int64)
    y600 = _plain_member(pp, "y_600.npy").astype(np.float32)
    ymask = _plain_member(sp, "y_mask_600.npy").astype(bool)
    tmp = out + ".tmp.npz"
    np.savez(tmp, spot_last=spot_last, perp_last=perp_last, timestamps=sts,
             perp_ts=pts, y_600=y600, y_mask_600=ymask)
    os.replace(tmp, out)
    return out


def verify(n=3):
    days = sorted(p.basename(f)[:-4] for f in glob.glob(p.join(SPOT_DIR, "*.npz")))
    import random
    random.seed(0)
    sample = random.sample(days, min(n, len(days)))
    ok = True
    for day in sample:
        sp = p.join(SPOT_DIR, f"{day}.npz")
        full = _read_member_array(sp, "X.npy", mmap=False)[:, -1, :].astype(np.float32)
        mmv = _last_ts(sp)
        same = np.array_equal(full, mmv)
        ok &= same
        print(f"[verify] {day} spot X[:,-1,:] mmap==full: {same} "
              f"(shape {mmv.shape})")
    print(f"[verify] {'ALL OK' if ok else 'FAIL'}")
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    if a.verify:
        raise SystemExit(0 if verify() else 1)
    os.makedirs(OUT_DIR, exist_ok=True)
    days = sorted(p.basename(f)[:-4] for f in glob.glob(p.join(SPOT_DIR, "*.npz")))
    perp = {p.basename(f)[:-4] for f in glob.glob(p.join(PERP_DIR, "*.npz"))}
    days = [d for d in days if d in perp]
    print(f"[lastts] {len(days)} days -> {OUT_DIR}", flush=True)
    t0, done, skip = time.time(), 0, 0
    for i, d in enumerate(days):
        r = build_day(d, force=a.force)
        if r is None:
            skip += 1
        else:
            done += 1
        if (i + 1) % 100 == 0 or i == len(days) - 1:
            el = time.time() - t0
            print(f"  [{i+1}/{len(days)}] done={done} skip={skip} {el:.0f}s "
                  f"({(i+1)/max(el,1e-9):.1f}/s)", flush=True)
    print(f"[lastts] done={done} skip={skip} in {time.time()-t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
