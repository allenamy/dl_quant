#!/usr/bin/env python3
"""ad_inventory.py -- AUDIT_DATA 2026-09-13, device A (pod2, CPU, READ-ONLY).

For every panel / cache / meta / target / OOF / mask / funding source that research, evaluation or retrain devices
committed since 2026-09-09 read (list below, assembled from `git grep` over those devices + the replay-tree symlinks),
record: exists, symlink realpath, bytes, mtime (UTC), sha256 GUARDED (bytes read must equal st_size, same rule as
uplift_r2 T6 t6_sha_guard.py), and cheap structure facts:
  .npz  member list + every member's npy header (shape, dtype) read from the zip stream WITHOUT decompressing the data;
        small axis arrays (ts / E_ts / symbols, <= 64 MB uncompressed) are loaded to give n, first and last UTC.
  .npy  shape / dtype via mmap.
  .json.gz funding pulls: symbols, rows, min/max UTC, size of the `intervals` dict (+ first 12 entries).
  directories: file counts by suffix + sha256 of the sorted "relpath<TAB>bytes" listing (a LISTING hash, not a content hash).
Nothing is written anywhere except the receipt path given as argv[1]. No network. nice 19, <= 6 worker processes.
Usage: python3 ad_inventory.py <out_receipt.json>
"""
import os, sys, json, time, glob, gzip, hashlib, zipfile, io, stat
from concurrent.futures import ProcessPoolExecutor
import numpy as np

ENV_WHITELIST = set()   # the device reads no environment variable
os.nice(19)
OUT = sys.argv[1]
SELF = os.path.abspath(__file__)

W = "/workspace"
FILES = [
    # --- raw sources / funding ---
    f"{W}/fund_aug.json.gz", f"{W}/uplift_2026-09-11/r6/dl/r6_fund_sep.json.gz", f"{W}/uplift_r2_2026-09-13/P2/work/ledger_full.npz",
    f"{W}/panel_symbols_wide.txt", f"{W}/live_pins.json",
    # --- 5m caches + patches + hole cells ---
    f"{W}/data/dlnative_5m_wide829_f16_fresh.npz", f"{W}/data/dlnative_5m_wide829_f16_ext.npz", f"{W}/data/dlnative_5m_wide829_f16_holefix.npz",
    f"{W}/data/dlnative_5m_wide829_f16_holefix2.npz", f"{W}/data/dlnative_5m_wide829_f16_holefix2_x0910.npz", f"{W}/data/dlnative_5m_wide829_f16_holefix_raw.npz",
    f"{W}/review_scratch/raw_patch.npz", f"{W}/uplift_2026-09-11/r6/out/raw_patch_x0910.npz", f"{W}/review_scratch/holefix2_cells.npz",
    # --- 4h panels + EMA state ---
    f"{W}/data/wide_panel_4h_v1.npz", f"{W}/data/wide_panel_4h_v2ext.npz", f"{W}/data/wide_panel_4h_v3splice.npz", f"{W}/data/wide_panel_4h_v2holefix.npz",
    f"{W}/uplift_2026-09-11/r6/out/wide_panel_4h_v2ext_x0910.npz", f"{W}/uplift_2026-09-11/r6/out/wide_panel_4h_v3splice_x0910.npz",
    f"{W}/uplift_2026-09-11/r6/out/wide_panel_4h_rawbuild_x0910.npz",
    f"{W}/fund_state_canoncont.json", f"{W}/uplift_2026-09-11/r6/out/fund_state_canoncont_v2ext_x0910.json", f"{W}/uplift_2026-09-11/r6/out/fund_state_canoncont_v3splice_x0910.json",
    # --- king features / metas ---
    f"{W}/data/wide_fea_v4.npy", f"{W}/data/wide_fea_v4_meta.npz", f"{W}/data/wide_fea_v2ext.npy", f"{W}/data/wide_fea_v2ext_meta.npz",
    f"{W}/data/wide_fea_v2ext_clamp.npy", f"{W}/data/wide_fea_v2ext_clamp_meta.npz", f"{W}/data/wide_fea_v4e.npy", f"{W}/data/wide_fea_v4e_meta.npz",
    f"{W}/uplift_2026-09-11/r6/out/wide_fea_v4_x0910.npy", f"{W}/uplift_2026-09-11/r6/out/wide_fea_v4_meta_x0910.npz",
    # --- accounting metas ---
    f"{W}/review_scratch/refute_C6_2/altrun/meta_newprod_v4.npz", f"{W}/review_scratch/refute_C6_2/altrun/meta_newprod_raw.npz",
    f"{W}/review_scratch/refute_C6_2/altrun/meta_newprod_hf2.npz", f"{W}/review_scratch/refute_C6_2/altrun/meta_newprod.npz",
    f"{W}/uplift_2026-09-11/r6/out/meta_newprod_v4_x0910.npz",
    # --- DL targets / features / legs ---
    f"{W}/dlw_v4raw/data/dlw_targets.npz", f"{W}/dlw_v4raw/data/dlw_fea82.npz", f"{W}/dlw_hf3/data/dlw_targets.npz", f"{W}/dlw_hf3/data/dlw_fea82.npz",
    f"{W}/dlw_ext/data/dlw_targets.npz", f"{W}/dlw_ext/data/dlw_fea82.npz", f"{W}/f8_v4/data/f8_fea89.npz", f"{W}/f8_v4/data/f10v2_legs.npz",
    f"{W}/f8_ext/data/f8_fea89.npz", f"{W}/f8_ext/data/f10v2_legs.npz",
    f"{W}/uplift_2026-09-11/r6/out/dlw_v4raw_x0910/data/dlw_targets.npz", f"{W}/uplift_2026-09-11/r6/out/dlw_targets_x0910.npz",
    f"{W}/uplift_2026-09-11/r6/out/f10v2_legs_x0910.npz", f"{W}/uplift_2026-09-11/r6/out/f10v2_legs_x0910_repair5.npz",
    # --- OOF predictions ---
    f"{W}/review_scratch/king_v4/SLOW_v4.npy", f"{W}/review_scratch/king_v4/SLOW_v3_on_v4axis.npy", f"{W}/review_scratch/king_v4/SLOW_v4e.npy",
    f"{W}/uplift_2026-09-11/r6/out/SLOW_v4_x0910.npy", f"{W}/shadow_bundle_v3/slow_pred_pinned.npy", f"{W}/shadow_bundle_v4/slow_pred_pinned.npy",
    f"{W}/shadow_bundle_v3/slow2026.txt", f"{W}/shadow_bundle_v4/slow2026.txt", f"{W}/shadow_bundle_v3/leg_returns.npz", f"{W}/shadow_bundle_v4/leg_returns.npz",
    f"{W}/shadow_bundle_v3/funding_ledger_seed.json", f"{W}/shadow_bundle_v4/funding_ledger_seed.json",
    f"{W}/review_scratch/health_check/dev_v4/f8_2026-08-22/preds/f10_A0_s42.npy", f"{W}/review_scratch/health_check/dev_v4/f8_2026-08-22/preds/f10_A0_s2027.npy",
    f"{W}/review_scratch/health_check/dev_v4/f8_2026-08-22/preds/f10_v4RAW_s42.npy", f"{W}/review_scratch/health_check/dev_v4/f8_2026-08-22/preds/f10_v4RAW_s2027.npy",
    f"{W}/f8_ext/preds/f10_V2MAIN_s42.npy", f"{W}/f8_ext/preds/f10_V2MAIN_s2027.npy",
    f"{W}/review_scratch/health_check/dev_v4_x0910/f8_2026-08-22/preds/f10_A0_s42.npy",
    # --- masks ---
    f"{W}/review_scratch/health_check/masks/umask_UPIT.npz", f"{W}/review_scratch/health_check/masks/umask_UPIT_CRYPTO.npz",
    f"{W}/review_scratch/health_check/masks/umask_UFROZEN.npz", f"{W}/review_scratch/health_check/masks/crypto_mask_note.json",
    f"{W}/uplift_r2_2026-09-13/T5c/masks/umask_UPIT_CRYPTO_cf_x0910.npz",
    # --- A0 / NW reference books (derived, but the reference every paired verdict uses) ---
    f"{W}/uplift_2026-09-11/r3k/arms/A0_PWR230k_s42.npz", f"{W}/uplift_2026-09-11/r3k/arms/A0_PWR230k_s2027.npz",
    f"{W}/uplift_2026-09-11/r18_foundation/arms/NW_s42.npz", f"{W}/uplift_2026-09-11/r18_foundation/arms/NW_s2027.npz",
    # --- builders present on pod2 (compared against git blobs off-device) ---
    f"{W}/fund_pull_pod.py", f"{W}/pod_fund_zips.py", f"{W}/pod_merge_cache_ext.py", f"{W}/pod_panel_ext.py", f"{W}/pod_panel_splice.py",
    f"{W}/pod_fea_ext.py", f"{W}/pod_dlw_targets_ext.py", f"{W}/pod_dlw_features_ext.py", f"{W}/pod_f8_build_ext.py", f"{W}/pod_umask_build.py",
    f"{W}/pod_extend_vision.py", f"{W}/zload.py",
    f"{W}/review_scratch/pod_fea_ext_clamp.py", f"{W}/review_scratch/pod_dlw_targets_raw.py", f"{W}/review_scratch/build_dev_v4.py",
    f"{W}/review_scratch/pod_legs_v4b.py", f"{W}/review_scratch/pod_export_bundle_v4.py", f"{W}/review_scratch/make_raw_patch.py",
    f"{W}/review_scratch/build_crypto_mask.py",
] + sorted(glob.glob(f"{W}/uplift_2026-09-11/r6/*.py")) + sorted(glob.glob(f"{W}/uplift_2026-09-11/r6/*.sh"))
DIRS = [f"{W}/wide_multisrc/funding"]
SYMLINK_TREES = [f"{W}/review_scratch/health_check/dev_v4", f"{W}/review_scratch/health_check/dev_v4_x0910", f"{W}/review_scratch/health_check/dev_alt"]

def utc(t): return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(t)))

def guarded_sha(p):
    st = os.stat(p); h = hashlib.sha256(); n = 0
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 24), b""): h.update(b); n += len(b)
    return h.hexdigest(), n, st.st_size

def npy_header_from_stream(fh):
    ver = np.lib.format.read_magic(fh)
    if ver == (1, 0): shape, fortran, dtype = np.lib.format.read_array_header_1_0(fh)
    elif ver == (2, 0): shape, fortran, dtype = np.lib.format.read_array_header_2_0(fh)
    else: raise ValueError("npy version %s" % (ver,))
    return list(shape), str(dtype)

def facts(p):
    r = {"path": p, "exists": os.path.lexists(p)}
    if not r["exists"]: return r
    r["is_symlink"] = os.path.islink(p); r["realpath"] = os.path.realpath(p)
    if os.path.isdir(p): r["is_dir"] = True; return r
    st = os.stat(p); r["bytes"] = st.st_size; r["mtime_utc"] = utc(st.st_mtime)
    try:
        d, n, sz = guarded_sha(p)
        if n != sz: r["sha256"] = None; r["sha_refused"] = "read %d bytes != st_size %d" % (n, sz)
        else: r["sha256"] = d
    except Exception as e: r["sha_error"] = repr(e)
    try:
        if p.endswith(".npz"):
            zf = zipfile.ZipFile(p); mem = {}
            for zi in zf.infolist():
                with zf.open(zi) as fh:
                    try: shp, dt = npy_header_from_stream(fh)
                    except Exception as e: shp, dt = None, "unreadable:%r" % (e,)
                mem[zi.filename[:-4] if zi.filename.endswith(".npy") else zi.filename] = {"shape": shp, "dtype": dt, "zip_bytes": zi.compress_size, "raw_bytes": zi.file_size}
            r["members"] = mem
            Z = np.load(p, allow_pickle=True)
            for k in ("ts", "E_ts", "cache_ts"):
                if k in mem and mem[k]["raw_bytes"] <= (64 << 20):
                    a = np.asarray(Z[k]).astype(np.int64).ravel()
                    if a.size: r[k + "_axis"] = {"n": int(a.size), "first_utc": utc(a[0]), "last_utc": utc(a[-1]), "strictly_increasing": bool(np.all(np.diff(a) > 0))}
            if "symbols" in mem and mem["symbols"]["raw_bytes"] <= (64 << 20):
                s = [str(x) for x in Z["symbols"]]; r["symbols_n"] = len(s); r["symbols_sha256"] = hashlib.sha256("|".join(s).encode()).hexdigest()
            if "ch" in mem:
                r["channels"] = [str(x) for x in Z["ch"]]
        elif p.endswith(".npy"):
            a = np.load(p, mmap_mode="r"); r["shape"] = list(a.shape); r["dtype"] = str(a.dtype)
        elif p.endswith(".json.gz"):
            J = json.loads(gzip.open(p, "rt").read()); rates = J.get("rates") or {}; iv = J.get("intervals")
            allt = [int(t) for v in rates.values() for t, _ in v]
            r["funding_pull"] = {"n_symbols": len(rates), "n_rows": len(allt), "min_utc": utc(min(allt) / 1000) if allt else None,
                                 "max_utc": utc(max(allt) / 1000) if allt else None, "intervals_type": type(iv).__name__,
                                 "intervals_n": (len(iv) if isinstance(iv, dict) else None),
                                 "intervals_head": (dict(sorted(iv.items())[:12]) if isinstance(iv, dict) else None), "meta": J.get("meta")}
        elif p.endswith(".txt") and os.path.basename(p) == "panel_symbols_wide.txt":
            s = open(p).read().strip().split("|"); r["symbols_n"] = len(s); r["symbols_sha256"] = hashlib.sha256("|".join(s).encode()).hexdigest()
    except Exception as e:
        r["structure_error"] = repr(e)
    return r

def dir_facts(d):
    r = {"path": d, "exists": os.path.isdir(d)}
    if not r["exists"]: return r
    lines = []; cnt = {}; maxmon = {}
    for root, _, fs in os.walk(d):
        for f in fs:
            fp = os.path.join(root, f); rel = os.path.relpath(fp, d); sz = os.path.getsize(fp)
            lines.append("%s\t%d" % (rel, sz)); suf = ".zip.404" if f.endswith(".zip.404") else os.path.splitext(f)[1]
            cnt[suf] = cnt.get(suf, 0) + 1
            if f.endswith(".zip"): s = os.path.basename(root); maxmon[s] = max(maxmon.get(s, ""), f[:-4])
    lines.sort()
    r["file_counts_by_suffix"] = cnt; r["n_symbol_dirs"] = len(os.listdir(d))
    r["listing_sha256"] = hashlib.sha256("\n".join(lines).encode()).hexdigest()
    hist = {}
    for v in maxmon.values(): hist[v] = hist.get(v, 0) + 1
    r["latest_zip_month_histogram"] = dict(sorted(hist.items())[-8:])
    return r

def tree_links(t):
    out = {}
    for p in sorted(glob.glob(t + "/**", recursive=True)):
        if os.path.islink(p): out[os.path.relpath(p, t)] = os.path.realpath(p)
    return out

if __name__ == "__main__":
    assert not (ENV_WHITELIST - set(os.environ)), "env whitelist"
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=6) as ex:
        res = list(ex.map(facts, FILES))
    rec = {"device": "ad_inventory.py", "self_sha256": guarded_sha(SELF)[0], "host_utc_start": utc(t0), "env_whitelist": sorted(ENV_WHITELIST),
           "files": res, "dirs": [dir_facts(d) for d in DIRS], "symlink_trees": {t: tree_links(t) for t in SYMLINK_TREES},
           "numpy": np.__version__, "python": sys.version.split()[0], "elapsed_s": round(time.time() - t0, 1), "host_utc_end": utc(time.time())}
    json.dump(rec, open(OUT, "w"), indent=1)
    missing = [r["path"] for r in res if not r["exists"]]
    print("AD_INVENTORY_DONE files=%d missing=%d sha_refused=%d elapsed=%.0fs out=%s" % (len(res), len(missing), sum(1 for r in res if r.get("sha_refused")), time.time() - t0, OUT))
    for m in missing: print("  missing:", m)
