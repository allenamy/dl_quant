#!/usr/bin/env python3
"""d10_dryrun_compare.py -- the comparator for the rebuild-device dry run (docs/PLAN_rebuild_devices_dry_run_2026-09-27.md, frozen by
lead acd2303b6). Same inputs as the delivered run -> are the outputs the same?

  npz    every key present on both sides, same dtype, same shape, bitwise equal. Floats compared through the same-width unsigned
         integer view; NaN vs NaN counts as equal whatever its payload (plan s1.1). The npz FILE sha is not compared (zip entries
         carry the write time). Differences are counted per key and split into nan-vs-finite and both-finite |diff| buckets --
         never one total (a single count mixes coverage, float noise and real defects).
  json   key-by-key after removing the row's volatile paths (exact dotted paths, e.g. "output.sha256", "argv[13]"; never matched by
         leaf name: "utc" inside an examples list is DATA). Keys that only the NEW side has are allowed only if named one-way
         (argv / python, added by lead's decision 1 to three devices).
  bytes  byte for byte.
One anchored line per comparison: `DRYRUN_CMP <IDENTICAL|DIFFERS> <kind> ...`; any crash prints `DRYRUN_CMP ERROR ...`.

selftest (plan s1.5, must pass before any row is read): the reference against itself is IDENTICAL, and a 1-ULP change in one
element of one float array, a 1-ULP change in one JSON number, a flipped byte, a dtype change and a changed non-volatile JSON path
are each detected; a changed volatile path is not.
usage:
  d10_dryrun_compare.py npz   REF NEW OUT.json
  d10_dryrun_compare.py json  REF NEW OUT.json [--volatile p1,p2] [--oneway k1,k2]
  d10_dryrun_compare.py bytes REF NEW OUT.json
  d10_dryrun_compare.py selftest REF.npz REF.json OUT.json
"""
import hashlib, json, os, sys

import numpy as np

for _c in (os.path.dirname(os.path.realpath(__file__)),
           os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), "common"),
           os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))), "common")):
    if os.path.exists(os.path.join(_c, "durable_write.py")):
        sys.path.insert(0, _c)
        break
else:
    raise ImportError("common/durable_write.py not found next to or above this device; deploy it with the device")
import durable_write as DW  # every file this device writes goes through it (news2 class fix 2026-09-27)

BUCKETS = (("le_1e-12", 1e-12), ("le_1e-9", 1e-9), ("le_1e-6", 1e-6), ("le_1e-3", 1e-3))


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 24), b""):
            h.update(b)
    return h.hexdigest()


def cmp_array(a, b):
    r = {"dtype_ref": str(a.dtype), "dtype_new": str(b.dtype), "shape_ref": list(a.shape), "shape_new": list(b.shape)}
    if a.dtype != b.dtype or a.shape != b.shape:
        r["n_differ"] = -1
        r["why"] = "dtype or shape differs"
        return r
    if a.dtype.kind == "f":
        u = {2: np.uint16, 4: np.uint32, 8: np.uint64}[a.dtype.itemsize]
        na, nb = np.isnan(a), np.isnan(b)
        same = (a.view(u) == b.view(u)) | (na & nb)
        diff = ~same
        r["n_differ"] = int(diff.sum())
        if r["n_differ"]:
            fin = diff & ~na & ~nb
            r["nan_vs_finite"] = int((diff & (na ^ nb)).sum())
            d = np.abs(a[fin].astype(np.float64) - b[fin].astype(np.float64))
            bk, lo = {}, 0.0
            for name, hi in BUCKETS:
                bk[name] = int(((d > lo) & (d <= hi)).sum()) if lo else int((d <= hi).sum())
                lo = hi
            bk["gt_1e-3"] = int((d > 1e-3).sum())
            r["both_finite_buckets"] = bk
            r["first_flat_indices"] = [int(i) for i in np.flatnonzero(diff)[:5]]
        return r
    if a.dtype.kind == "O":
        diff = np.array([x != y for x, y in zip(a.ravel().tolist(), b.ravel().tolist())], bool)
    else:
        diff = (a != b)
    diff = np.asarray(diff)
    r["n_differ"] = int(diff.sum())
    if r["n_differ"]:
        r["first_flat_indices"] = [int(i) for i in np.flatnonzero(diff)[:5]]
    return r


def compare_npz(ref, new, mutate=None):
    A = np.load(ref, allow_pickle=True)
    B = np.load(new, allow_pickle=True)
    ka, kb = set(A.files), set(B.files)
    out = {"kind": "npz", "ref": ref, "new": new, "ref_file_sha256": sha(ref), "new_file_sha256": sha(new),
           "keys_only_ref": sorted(ka - kb), "keys_only_new": sorted(kb - ka), "per_key": {}}
    for k in sorted(ka & kb):
        b = B[k]
        if mutate is not None:
            b = mutate(k, b)
        out["per_key"][k] = cmp_array(A[k], b)
    bad = [k for k, v in out["per_key"].items() if v["n_differ"] != 0]
    out["differing_keys"] = bad
    out["verdict"] = "IDENTICAL" if not bad and not out["keys_only_ref"] and not out["keys_only_new"] else "DIFFERS"
    return out


def _walk(x, p=""):
    if isinstance(x, dict):
        if not x:
            yield p, x
        for k, v in x.items():
            yield from _walk(v, f"{p}.{k}" if p else str(k))
    elif isinstance(x, list):
        if not x:
            yield p, x
        for i, v in enumerate(x):
            yield from _walk(v, f"{p}[{i}]")
    else:
        yield p, x


def _flat(x):
    return dict(_walk(x))


def _same(u, v):
    if isinstance(u, float) and isinstance(v, float) and u != u and v != v:
        return True
    return type(u) == type(v) and u == v


def compare_json(ref, new, volatile=(), oneway=(), mutate=None, argv_out=()):
    """argv_out: indices i of argv whose value is the output path. Exempt ONLY after asserting, on both sides, that argv[i-1] ==
    "--out" and that the two argv lists have the same length (lead freeze addendum 1, item 2); a failed assertion is DIFFERS."""
    R = json.load(open(ref))
    N = json.load(open(new))
    if mutate is not None:
        N = mutate(N)
    vol = set(volatile)
    argv_fail = []
    if argv_out:
        ra, na = R.get("argv"), N.get("argv")
        if not isinstance(ra, list) or not isinstance(na, list):
            argv_fail.append("argv missing or not a list on one side")
        else:
            if len(ra) != len(na):
                argv_fail.append(f"argv length {len(ra)} != {len(na)}")
            for i in argv_out:
                for side, a in (("ref", ra), ("new", na)):
                    if not (0 < i < len(a)) or a[i - 1] != "--out":
                        argv_fail.append(f"{side} argv[{i - 1}] is {a[i - 1] if 0 < i <= len(a) else '<out of range>'!r}, not '--out'")
            if not argv_fail:
                vol |= {f"argv[{i}]" for i in argv_out}
    fr, fn = _flat(R), _flat(N)

    def is_vol(p):
        return any(p == v or p.startswith(v + ".") or p.startswith(v + "[") for v in vol)

    def is_oneway(p):
        top = p.split(".")[0].split("[")[0]
        return top in oneway

    only_ref = sorted(p for p in fr if p not in fn and not is_vol(p))
    only_new = sorted(p for p in fn if p not in fr and not is_vol(p) and not is_oneway(p))
    differ = sorted(p for p in fr if p in fn and not is_vol(p) and not _same(fr[p], fn[p]))
    out = {"kind": "json", "ref": ref, "new": new, "volatile": sorted(vol), "oneway": sorted(oneway),
           "argv_out": list(argv_out), "argv_out_failures": argv_fail,
           "paths_compared": sum(1 for p in fr if p in fn and not is_vol(p)),
           "only_ref": only_ref[:50], "n_only_ref": len(only_ref), "only_new": only_new[:50], "n_only_new": len(only_new),
           "differ": [{"path": p, "ref": fr[p], "new": fn[p]} for p in differ[:50]], "n_differ": len(differ),
           "volatile_seen": {v: [p for p in fr if p == v or p.startswith(v + ".") or p.startswith(v + "[")][:3] for v in sorted(vol)}}
    out["verdict"] = "IDENTICAL" if not (only_ref or only_new or differ or argv_fail) else "DIFFERS"
    return out


def compare_bytes(ref, new):
    a, b = open(ref, "rb").read(), open(new, "rb").read()
    out = {"kind": "bytes", "ref": ref, "new": new, "ref_sha256": hashlib.sha256(a).hexdigest(),
           "new_sha256": hashlib.sha256(b).hexdigest(), "len_ref": len(a), "len_new": len(b)}
    out["verdict"] = "IDENTICAL" if a == b else "DIFFERS"
    if a != b:
        out["first_differing_byte"] = next((i for i, (x, y) in enumerate(zip(a, b)) if x != y), min(len(a), len(b)))
    return out


def selftest(ref_npz, ref_json):
    res = {}
    r = compare_npz(ref_npz, ref_npz)
    res["S1_npz_self_IDENTICAL"] = r["verdict"] == "IDENTICAL"
    A = np.load(ref_npz, allow_pickle=True)
    fkey = next((k for k in A.files if A[k].dtype.kind == "f" and np.isfinite(A[k]).any()), None)
    if fkey is None:
        res["S2_npz_1ulp_detected"] = False
        res["S2_note"] = "reference has no float array with a finite element -- control has no power"
    else:
        idx = int(np.flatnonzero(np.isfinite(A[fkey]).ravel())[0])

        def ulp(k, b):
            if k != fkey:
                return b
            b = b.copy()
            flat = b.reshape(-1)
            flat[idx] = np.nextafter(flat[idx], np.inf, dtype=b.dtype)
            return b
        r = compare_npz(ref_npz, ref_npz, mutate=ulp)
        pk = r["per_key"][fkey]
        res["S2_npz_1ulp_detected"] = r["verdict"] == "DIFFERS" and pk["n_differ"] == 1 and r["differing_keys"] == [fkey]
        res["S2_key"] = fkey
        res["S2_bucket"] = pk.get("both_finite_buckets")

        def dt(k, b):
            return b.astype(np.float32) if k == fkey and b.dtype == np.float64 else (b.astype(np.float64) if k == fkey else b)
        r = compare_npz(ref_npz, ref_npz, mutate=dt)
        res["S3_npz_dtype_change_detected"] = r["verdict"] == "DIFFERS"
    r = compare_json(ref_json, ref_json)
    res["S4_json_self_IDENTICAL"] = r["verdict"] == "IDENTICAL"
    fl = _flat(json.load(open(ref_json)))
    num = next((p for p, v in fl.items() if isinstance(v, float) and v == v and v != 0.0), None)
    anyp = next(iter(fl))

    def setp(obj, path, fn):
        import re
        toks = re.findall(r"[^.\[\]]+|\[\d+\]", path)
        cur = obj
        for t in toks[:-1]:
            cur = cur[int(t[1:-1])] if t.startswith("[") else cur[t]
        last = toks[-1]
        if last.startswith("["):
            cur[int(last[1:-1])] = fn(cur[int(last[1:-1])])
        else:
            cur[last] = fn(cur[last])
        return obj
    if num is None:
        res["S5_json_1ulp_detected"] = False
        res["S5_note"] = "reference JSON has no nonzero float leaf"
    else:
        r = compare_json(ref_json, ref_json, mutate=lambda o: setp(o, num, lambda v: float(np.nextafter(v, np.inf))))
        res["S5_json_1ulp_detected"] = r["verdict"] == "DIFFERS" and r["n_differ"] == 1
        res["S5_path"] = num
    r = compare_json(ref_json, ref_json, mutate=lambda o: setp(o, anyp, lambda v: "__changed__"))
    res["S6_json_nonvolatile_change_detected"] = r["verdict"] == "DIFFERS"
    r = compare_json(ref_json, ref_json, volatile=[anyp], mutate=lambda o: setp(o, anyp, lambda v: "__changed__"))
    res["S7_json_volatile_change_ignored"] = r["verdict"] == "IDENTICAL"
    r = compare_json(ref_json, ref_json, oneway=["argv"], mutate=lambda o: (o.__setitem__("argv", {"x": 1}) or o) if "argv" not in o else o)
    res["S8_json_oneway_new_key_ignored"] = r["verdict"] == "IDENTICAL"
    r = compare_json(ref_json, ref_json, mutate=lambda o: (o.__setitem__("zz_new_key", 1) or o))
    res["S9_json_unlisted_new_key_detected"] = r["verdict"] == "DIFFERS"
    import tempfile
    td = tempfile.mkdtemp(prefix="dryrun_cmp_")
    b = open(ref_json, "rb").read()
    p = os.path.join(td, "flip")
    open(p, "wb").write(b[:-2] + bytes([b[-2] ^ 1]) + b[-1:])  # durable-exempt: selftest fixture in a mkdtemp dir, read back here
    res["S10_bytes_flip_detected"] = compare_bytes(ref_json, p)["verdict"] == "DIFFERS"
    res["S11_bytes_self_IDENTICAL"] = compare_bytes(ref_json, ref_json)["verdict"] == "IDENTICAL"
    base = json.load(open(ref_json))
    base["argv"] = ["--x", "1", "--out", "/old/out.json"]
    pa = os.path.join(td, "argv_ref.json")
    DW.write_json(pa, base, allow_nan=True)

    def newout(o):
        o["argv"] = ["--x", "1", "--out", "/new/out.json"]; return o
    res["S12_argv_out_exempt_when_flag_matches"] = compare_json(pa, pa, argv_out=[3], mutate=newout)["verdict"] == "IDENTICAL"
    res["S13_argv_out_wrong_index_is_DIFFERS"] = compare_json(pa, pa, argv_out=[1], mutate=newout)["verdict"] == "DIFFERS"

    def longer(o):
        o["argv"] = ["--x", "1", "--out", "/new/out.json", "--extra"]; return o
    res["S14_argv_length_change_is_DIFFERS"] = compare_json(pa, pa, argv_out=[3], mutate=longer)["verdict"] == "DIFFERS"
    res["S15_argv_out_value_change_without_exemption_is_DIFFERS"] = compare_json(pa, pa, mutate=newout)["verdict"] == "DIFFERS"
    import shutil
    shutil.rmtree(td, ignore_errors=True)   # rev 1 (lead 2026-09-27): the selftest's scratch is removed; TMPDIR decides where it lives
    ok = all(v for k, v in res.items() if k.startswith("S") and isinstance(v, bool))
    return {"kind": "selftest", "ref_npz": ref_npz, "ref_json": ref_json, "cells": res, "verdict": "SELFTEST_PASS" if ok else "SELFTEST_RED"}


def main():
    try:
        kind = sys.argv[1]
        if kind == "selftest":
            out = selftest(sys.argv[2], sys.argv[3]); outp = sys.argv[4]
        elif kind == "npz":
            out = compare_npz(sys.argv[2], sys.argv[3]); outp = sys.argv[4]
        elif kind == "bytes":
            out = compare_bytes(sys.argv[2], sys.argv[3]); outp = sys.argv[4]
        elif kind == "json":
            vol = one = ()
            rest = sys.argv[5:]
            for i, t in enumerate(rest):
                if t == "--volatile":
                    vol = [x for x in rest[i + 1].split(",") if x]
                if t == "--oneway":
                    one = [x for x in rest[i + 1].split(",") if x]
            out = compare_json(sys.argv[2], sys.argv[3], vol, one); outp = sys.argv[4]
        else:
            print(f"DRYRUN_CMP ERROR unknown kind {kind!r}"); return
        out["comparator_sha256"] = sha(os.path.realpath(__file__))
        out["python"] = sys.version.split()[0]
        s = DW.write_json(outp, out, indent=1, allow_nan=True, default=str)
        extra = ""
        if out["kind"] == "npz":
            extra = f" differing_keys={','.join(out['differing_keys'][:6])} only_ref={len(out['keys_only_ref'])} only_new={len(out['keys_only_new'])}"
        elif out["kind"] == "json":
            extra = f" compared={out['paths_compared']} differ={out['n_differ']} only_ref={out['n_only_ref']} only_new={out['n_only_new']}"
        print(f"DRYRUN_CMP {out['verdict']} {out['kind']}{extra} receipt_sha256={s}")
    except BaseException as e:
        print(f"DRYRUN_CMP ERROR {type(e).__name__}: {e}")
    sys.stdout.flush()


if __name__ == "__main__":
    main()
