"""Raw-return patch COVERAGE rules — one implementation (FX-TRAIN TRN-02, 2026-09-13; AUDIT_TRAIN 7e1ecf9a TRN-02; docs/fixprogram_2026-09-13/FX_TRAIN/FACT_TABLE_TRN.md §TRN-02).

WHY: the 5m cache stores ret5 clipped at +-0.30 (float16). DLWT_RAW_PATCH puts the exact return back on clipped bars before 4h labels are compounded (the
E-0908-B fix: clip-then-compound wrote -48% as +55%). Nothing checked that the patch covers every clipped bar of the cache it is applied to: the September
patch on the r6 x0910 cache leaves AKEUSDT +42.5%, BULLAUSDT +55.8%, WOOUSDT +30.06% at +0.30 (pod2 measurement, FACT_TABLE 02.6). The candidate rule cannot
separate a clipped bar from an UNCLIPPED bar whose true return rounds to float16(0.3) = 0.30004883 (NMRUSDT 2025-10-10 21:35Z: rv 0.29993, FACT_TABLE 02.7),
so "candidates ⊆ patch" is wrong and coverage needs an EVIDENCED not-clipped class.

Used by: pod_dlw_targets_raw.py (refuses to build patched targets unless verify() PASSes), v4_gate_rawpatch.py (standalone gate, receipt through
v4_gate_common.finalize), v4_rawpatch_manifest.py (writes the manifest this module verifies). The manifest lives at manifest_path_for(<patch>) — a fixed
sibling rule, not a month-contract key (FACT_TABLE 02.12).

PASS iff (every check below is unconditional; nothing is skipped because a field is absent):
  G1 patch schema: arrays row, col (integer kind), ts (integer), symbol (str), raw32 (float32), clip16 (float16), all 1-D, equal length
  G2 addressing: 0 <= row < TT, 0 <= col < NW, CTS[row] == ts, symbols[col] == symbol, cache ch0[row, col] bitwise == clip16, |clip16| == float16(0.3)
  G3 values: raw32 finite, |raw32| > 0.3, sign(raw32) == sign(clip16)
  G4 (row, col) unique in the patch
  G5 manifest binding: schema == MANIFEST_SCHEMA, cache_sha256 == sha256(cache file), raw_patch_sha256 == sha256(patch file)
  G6 every patch row has exactly one manifest `kept` entry whose close pair, RE-READ from the recorded source files (each file's sha256 == the manifest's
     `sources` record), gives float32(close_t / close_prev - 1) bitwise == raw32 and |rv| > 0.3
  G7 every manifest `not_clipped` entry: a candidate, not a patch row, unique, source re-read gives |rv| <= 0.3 and float16(rv) bitwise == the cache cell
  G8 `clipped_missing` and `unresolved` are empty lists
  G9 candidates {(r, c): isfinite(ch0) and ch0 == +-float16(0.3)} == patch rows ∪ not_clipped rows, exactly (no candidate unaccounted, no extra row)
Close convention (make_raw_patch.py 7716e7d3 L12-24 / r6_raw_patch_ext.py 808d2f66 L36): 5m kline CSV rows (open_time_ms, o, h, l, c, …); close time =
open_time // 1000 + 300; close = column 4; header iff the first byte is alphabetic; parsed with pandas.read_csv exactly as those builders did."""
import hashlib, io, json, os, time, zipfile
import numpy as np

MANIFEST_SCHEMA = "v4_raw_patch_manifest/1"
CLIP16 = np.float16(0.3)
CAP = 50   # listed violations per class (counts are always complete)


def manifest_path_for(patch_path):
    return (patch_path[:-4] if patch_path.endswith(".npz") else patch_path) + ".manifest.json"


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 24), b""):
            h.update(b)
    return h.hexdigest()


def utc(t):
    return time.strftime("%Y-%m-%d %H:%MZ", time.gmtime(int(t)))


def read_closes(path):
    """{close_ts_seconds: close} from a monthly CSV (<SYM>_<YYYY-MM>.csv) or a daily zip (<SYM>/<YYYY-MM-DD>.zip) of 5m klines."""
    import pandas as pd
    if path.endswith(".zip"):
        with zipfile.ZipFile(path) as z:
            raw = z.read(z.namelist()[0])
    else:
        raw = open(path, "rb").read()
    k = pd.read_csv(io.BytesIO(raw), header=0 if raw[:1].isalpha() else None).iloc[:, :11]
    ts = (k.iloc[:, 0].astype(np.int64) // 1000 + 300).to_numpy(); c = k.iloc[:, 4].astype(float).to_numpy()
    return dict(zip(ts.tolist(), c.tolist()))


def candidates(ch0):
    """(rows, cols) of cells whose stored ret5 equals +-float16(0.3) — clipped OR an unclipped return that rounds to the clip value."""
    return np.nonzero(np.isfinite(ch0) & ((ch0 == CLIP16) | (ch0 == -CLIP16)))


class _Src:
    def __init__(self, sources):
        self.sources = sources if isinstance(sources, dict) else {}; self.cache = {}; self.bad = {}

    def close(self, path, t):
        """(close or None, why). The file must be recorded in the manifest's `sources` with a sha256 equal to the file on disk."""
        if not isinstance(path, str) or path not in self.sources:
            return None, f"source {path!r} not recorded in manifest.sources"
        if path not in self.cache:
            if not os.path.isfile(path):
                self.bad[path] = "missing"; self.cache[path] = None
            else:
                h = sha256_file(path)
                if h != self.sources[path]:
                    self.bad[path] = f"sha256 {h[:12]} != manifest {str(self.sources[path])[:12]}"; self.cache[path] = None
                else:
                    self.cache[path] = read_closes(path)
        d = self.cache[path]
        if d is None:
            return None, f"source {path}: {self.bad[path]}"
        v = d.get(int(t))
        return (None, f"source {path} has no close at {utc(t)}") if v is None else (v, None)


def verify(ch0, CTS, syms, patch, manifest, cache_sha256, patch_sha256):
    """Return a report dict with PASS and per-check evidence. ch0: (TT, NW) float16 cache channel 0; CTS: int64 close timestamps; syms: list[str];
    patch: mapping with the six arrays; manifest: parsed JSON (dict); *_sha256: of the files the caller loaded."""
    rep = {"rules": "v4_rawpatch_lib G1-G9", "checks": {}}; fails = []
    def chk(name, ok, **ev):
        rep["checks"][name] = dict(ok=bool(ok), **ev)
        if not ok: fails.append(name)
        return bool(ok)
    TT, NW = ch0.shape
    # G1 schema
    need = ("row", "col", "ts", "symbol", "raw32", "clip16"); files = set(getattr(patch, "files", None) or list(patch.keys()))
    miss = [k for k in need if k not in files]
    if miss:
        chk("G1_schema", False, why=f"patch arrays missing {miss}"); rep["PASS"] = False; rep["fails"] = fails; return rep
    A = {k: np.asarray(patch[k]) for k in need}; n = len(A["row"])
    kinds = {"row": "iu", "col": "iu", "ts": "iu", "symbol": "US", "raw32": "f", "clip16": "f"}
    bad_schema = [k for k in need if A[k].ndim != 1 or len(A[k]) != n or A[k].dtype.kind not in kinds[k]]
    bad_schema += [k for k, dt in (("raw32", np.float32), ("clip16", np.float16)) if A[k].dtype != dt and k not in bad_schema]
    if not chk("G1_schema", not bad_schema, n=int(n), bad=bad_schema, dtypes={k: A[k].dtype.str for k in need}):
        rep["PASS"] = False; rep["fails"] = fails; return rep
    r = A["row"].astype(np.int64); c = A["col"].astype(np.int64); inb = (r >= 0) & (r < TT) & (c >= 0) & (c < NW)
    # G2 addressing
    ts_bad, sym_bad, cell_bad, clip_bad = [], [], [], []
    c16 = A["clip16"].astype(np.float16)
    for i in range(n):
        if not inb[i]: continue
        if int(CTS[r[i]]) != int(A["ts"][i]): ts_bad.append(i)
        if syms[c[i]] != str(A["symbol"][i]): sym_bad.append(i)
        if ch0[r[i], c[i]].view(np.uint16) != c16[i].view(np.uint16): cell_bad.append(i)
        if abs(c16[i]) != CLIP16: clip_bad.append(i)
    ob = np.nonzero(~inb)[0].tolist()
    chk("G2_addressing", not (ob or ts_bad or sym_bad or cell_bad or clip_bad), out_of_bounds=ob[:CAP], ts_mismatch=ts_bad[:CAP], symbol_mismatch=sym_bad[:CAP],
        cache_cell_ne_clip16=cell_bad[:CAP], clip16_not_clip_value=clip_bad[:CAP], n_bad=len(ob) + len(ts_bad) + len(sym_bad) + len(cell_bad) + len(clip_bad))
    # G3 values
    raw = A["raw32"].astype(np.float32); rf = np.isfinite(raw); big = np.abs(raw.astype(np.float64)) > 0.3
    sgn = np.sign(raw.astype(np.float64)) == np.sign(c16.astype(np.float64))
    v_bad = np.nonzero(~(rf & big & sgn))[0].tolist()
    chk("G3_values", not v_bad, rows_bad=[{"i": i, "raw32": float(raw[i]), "clip16": float(c16[i])} for i in v_bad[:CAP]], n_bad=len(v_bad))
    # G4 unique
    keys = list(zip(r.tolist(), c.tolist())); dup = [k for k in set(keys) if keys.count(k) > 1] if len(set(keys)) != len(keys) else []
    chk("G4_unique", not dup, duplicates=[list(k) for k in dup[:CAP]])
    # G5 manifest binding
    m = manifest if isinstance(manifest, dict) else {}
    chk("G5_manifest_binding", m.get("schema") == MANIFEST_SCHEMA and m.get("cache_sha256") == cache_sha256 and m.get("raw_patch_sha256") == patch_sha256,
        schema=m.get("schema"), manifest_cache_sha256=m.get("cache_sha256"), cache_sha256=cache_sha256, manifest_raw_patch_sha256=m.get("raw_patch_sha256"), raw_patch_sha256=patch_sha256)
    src = _Src(m.get("sources"))
    def entry_rv(e):
        if not isinstance(e, dict) or not all(k in e for k in ("row", "col", "src_t", "src_prev")): return None, "entry lacks row/col/src_t/src_prev"
        er, ec = int(e["row"]), int(e["col"])
        if not (0 <= er < TT and 0 <= ec < NW): return None, "entry out of bounds"
        t = int(CTS[er]); a, why = src.close(e["src_t"], t)
        if why: return None, why
        b, why = src.close(e["src_prev"], t - 300)
        if why: return None, why
        if not (b > 0): return None, f"close_prev {b} <= 0"
        return a / b - 1.0, None
    # G6 kept
    kept = m.get("kept") if isinstance(m.get("kept"), list) else None
    kmap = {}; k_bad = []
    if kept is None:
        k_bad.append({"why": "manifest.kept is not a list"})
    else:
        for e in kept:
            try: kk = (int(e["row"]), int(e["col"]))
            except Exception: k_bad.append({"entry": str(e)[:120], "why": "kept entry without integer row/col"}); continue   # noqa: BLE001
            if kk in kmap: k_bad.append({"row": kk[0], "col": kk[1], "why": "duplicate kept entry"}); continue
            kmap[kk] = e
        pset = set(keys)
        for kk in pset - set(kmap): k_bad.append({"row": kk[0], "col": kk[1], "why": "patch row without a kept entry"})
        for kk in set(kmap) - pset: k_bad.append({"row": kk[0], "col": kk[1], "why": "kept entry that is not a patch row"})
        for i, kk in enumerate(keys):
            if kk not in kmap or not inb[i]: continue
            rv, why = entry_rv(kmap[kk])
            if why: k_bad.append({"row": kk[0], "col": kk[1], "why": why}); continue
            if not (abs(rv) > 0.3 and np.float32(rv).view(np.uint32) == raw[i].view(np.uint32)):
                k_bad.append({"row": kk[0], "col": kk[1], "ts": utc(CTS[kk[0]]), "symbol": syms[kk[1]], "rv_from_source": rv, "raw32": float(raw[i]), "why": "source return does not reproduce raw32 bitwise or |rv| <= 0.3"})
    chk("G6_kept_rederived_from_source", not k_bad, n_kept_entries=len(kmap), n_patch=int(n), bad=k_bad[:CAP], n_bad=len(k_bad), sources_bad=dict(list(src.bad.items())[:CAP]))
    # G7 not_clipped
    cr, cc = candidates(ch0); cset = set(zip(cr.tolist(), cc.tolist()))
    nc = m.get("not_clipped") if isinstance(m.get("not_clipped"), list) else None; ncset = set(); n_bad = []
    if nc is None:
        n_bad.append({"why": "manifest.not_clipped is not a list"})
    else:
        for e in nc:
            try: kk = (int(e["row"]), int(e["col"]))
            except Exception: n_bad.append({"entry": str(e)[:120], "why": "not_clipped entry without integer row/col"}); continue   # noqa: BLE001
            if kk in ncset: n_bad.append({"row": kk[0], "col": kk[1], "why": "duplicate not_clipped entry"}); continue
            ncset.add(kk)
            if kk not in cset: n_bad.append({"row": kk[0], "col": kk[1], "why": "not a clip candidate of this cache"}); continue
            if kk in set(keys): n_bad.append({"row": kk[0], "col": kk[1], "why": "also a patch row"}); continue
            rv, why = entry_rv(e)
            if why: n_bad.append({"row": kk[0], "col": kk[1], "why": why}); continue
            if not (abs(rv) <= 0.3 and np.float16(rv).view(np.uint16) == ch0[kk].view(np.uint16)):
                n_bad.append({"row": kk[0], "col": kk[1], "ts": utc(CTS[kk[0]]), "symbol": syms[kk[1]], "rv_from_source": rv, "why": "source return is clipped (|rv| > 0.3) or does not round to the cache cell"})
    chk("G7_not_clipped_evidenced", not n_bad, n_not_clipped=len(ncset), bad=n_bad[:CAP], n_bad=len(n_bad))
    # G8 nothing declared missing / unresolved
    cm = m.get("clipped_missing"); un = m.get("unresolved")
    chk("G8_no_clipped_missing_no_unresolved", cm == [] and un == [], clipped_missing=(cm or [])[:CAP] if isinstance(cm, list) else cm, unresolved=(un or [])[:CAP] if isinstance(un, list) else un,
        n_clipped_missing=len(cm) if isinstance(cm, list) else None, n_unresolved=len(un) if isinstance(un, list) else None)
    # G9 partition
    unacc = sorted(cset - set(keys) - ncset); extra = sorted((set(keys) | ncset) - cset)
    chk("G9_partition", not unacc and not extra, n_candidates=len(cset), n_patch=int(n), n_not_clipped=len(ncset),
        candidates_unaccounted=[{"row": a, "col": b, "ts": utc(CTS[a]), "symbol": syms[b]} for a, b in unacc[:CAP]], n_unaccounted=len(unacc), rows_not_candidates=[list(x) for x in extra[:CAP]], n_extra=len(extra))
    rep["PASS"] = not fails; rep["fails"] = fails
    rep["summary"] = {"TT": int(TT), "NW": int(NW), "n_candidates": len(cset), "n_patch": int(n), "n_not_clipped": len(ncset), "n_unaccounted": len(unacc)}
    return rep


def verify_files(ch0, CTS, syms, patch_path, cache_path, cache_sha256=None, manifest_path=None):
    """Load the patch and its manifest (sibling rule unless given) and verify; a missing manifest is a FAIL with a named reason, never a skip."""
    mp = manifest_path or manifest_path_for(patch_path)
    base = {"raw_patch": patch_path, "manifest": mp, "cache": cache_path}
    if not os.path.isfile(patch_path):
        return dict(base, PASS=False, fails=["patch_missing"], checks={})
    if not os.path.isfile(mp):
        return dict(base, PASS=False, fails=["manifest_missing"], checks={"manifest_missing": {"ok": False, "why": f"no manifest at {mp} (sibling rule manifest_path_for)"}})
    try:
        man = json.load(open(mp))
    except Exception as e:                                   # noqa: BLE001
        return dict(base, PASS=False, fails=["manifest_unreadable"], checks={"manifest_unreadable": {"ok": False, "why": f"{type(e).__name__}: {e}"}})
    pb = open(patch_path, "rb").read(); psha = hashlib.sha256(pb).hexdigest(); P = np.load(io.BytesIO(pb), allow_pickle=False)   # one read: the bytes hashed are the bytes verified
    rep = verify(ch0, CTS, syms, P, man, cache_sha256 or sha256_file(cache_path), psha)
    rep.update(base); rep["raw_patch_sha256"] = psha; rep["manifest_sha256"] = sha256_file(mp); rep["lib_sha256"] = sha256_file(os.path.abspath(__file__))
    return rep
