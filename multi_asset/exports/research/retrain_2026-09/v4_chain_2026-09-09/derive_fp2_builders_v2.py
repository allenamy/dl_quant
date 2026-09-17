#!/usr/bin/env python3
"""derive_fp2_builders_v2.py — FP2-8 (2026-09-17): derive pod_fea_ext_clamp_v2.py / pod_dlw_targets_raw_v2.py from the FROZEN v1 files by
exact-once hunk replacement. v2 == v1 + the hunks below and nothing else; this script IS the receipt (re-run it: the outputs must be byte-identical).

Hunks (pre-registered, DESIGN_FP2-8 §2 + AMENDMENT 1):
  K1  king member-statistics window: v1 indexed `E - 2016` unclamped for n7/qvm/m7/v7 (numpy negative index wraps to the cache tail ⇒ v7 == 0 ⇒ the 30
      anchors with 576 <= E < 2016 were silently dropped), and normalised covr by the CONSTANT 2016. v2 clamps to S7 = max(E-2016, 0) — the same
      E-0909-A clamp v1 already applied to every per-feature window — and normalises coverage by the ACTUAL window, which is pod_dlw_targets_raw.py's
      frozen convention P.1 ([max(E-2016,0), E)). For E >= 2016 every array is bitwise unchanged (S7 == E-2016; /2016 == /max(E-S7,1)).
  M   both builders: optional MEMBER_MASK_NPZ (ts, symbols, mask) ANDed into the member rule; absent ⇒ all True (bitwise v1 behaviour); a mask that
      lacks an anchor row or whose symbol axis differs is REFUSED (exit 3), never skipped; the mask path + sha256 + false-cell count are self-reported.
"""
import hashlib, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
V1 = {"king": "pod_fea_ext_clamp.py", "dl": "pod_dlw_targets_raw.py"}
V2 = {"king": "pod_fea_ext_clamp_v2.py", "dl": "pod_dlw_targets_raw_v2.py"}
V1_SHA = {"king": "b9f9c72816241715fc4b767950420e74f50adbbbcfc4ea77b362407ab5efa4ac", "dl": None}   # king pinned (October template PREV_CLAMP_BUILDER_SHA256); dl recorded below

HELPER = '''
def _member_mask_rows(ts_rows, syms, _osm={OS}):
    """FP2-8 v2: optional training member mask. env MEMBER_MASK_NPZ = npz with ts (int64 s), symbols, mask (bool [T, N]).
    Absent/empty env ⇒ all-True (bitwise v1 behaviour). Present ⇒ symbols must equal the cache symbols and EVERY anchor ts must have a row
    (a missing anchor is refused with exit 3 — never skipped, never filled). Returns (mask_rows[bool, nE x N], record dict)."""
    p = _osm.environ.get("MEMBER_MASK_NPZ", "")
    n = len(ts_rows); N = len(syms)
    if not p:
        return np.ones((n, N), bool), {"path": None, "sha256": None, "applied": False}
    h = hashlib.sha256(open(p, "rb").read()).hexdigest()
    Mz = np.load(p, allow_pickle=True)
    msy = [str(s) for s in Mz["symbols"]]
    if msy != list(syms):
        print("MEMBER_MASK_REFUSED symbols axis != cache symbols (%d vs %d; first diff %s)" % (len(msy), N, next(((a, b) for a, b in zip(msy, syms) if a != b), None)), flush=True); sys.exit(3)
    mts = Mz["ts"].astype(np.int64); row = {int(t): i for i, t in enumerate(mts)}
    miss = [int(t) for t in ts_rows if int(t) not in row]
    if miss:
        print("MEMBER_MASK_REFUSED %d anchors have no mask row (first %s)" % (len(miss), miss[:5]), flush=True); sys.exit(3)
    M = np.asarray(Mz["mask"])
    if M.dtype != bool or M.shape != (len(mts), N):
        print("MEMBER_MASK_REFUSED mask dtype/shape %s %s" % (M.dtype, M.shape), flush=True); sys.exit(3)
    out = M[[row[int(t)] for t in ts_rows]]
    return out, {"path": p, "sha256": h, "applied": True, "n_anchor_rows": int(n), "false_cells": int((~out).sum()),
                 "definition": str(Mz["definition"]) if "definition" in Mz.files else None}
'''

def replace_once(text, old, new, tag):
    k = text.count(old)
    if k != 1:
        sys.exit("HUNK %s: expected exactly 1 occurrence, found %d" % (tag, k))
    return text.replace(old, new)

def derive_king(t):
    t = replace_once(t, 'import os as _os\n', 'import os as _os\n' + HELPER.replace("{OS}", "_os").replace("hashlib.sha256", "hashlib.sha256"), "K-helper")
    t = replace_once(t,
        'n7 = np.maximum(qv_f[E] - qv_f[E - 2016], 1)\n'
        'covr = (CS["ret5"][1][E] - CS["ret5"][1][np.maximum(E - 2016, 0)]) / 2016\n'
        'qvm = (qv_s[E] - qv_s[E - 2016]) / n7\n'
        'm7 = (CS["ret5"][0][E] - CS["ret5"][0][E - 2016])\n'
        'v7 = np.sqrt(np.maximum((r2s[E] - r2s[E - 2016]) / n7 - (m7 / n7) ** 2, 0))\n',
        'S7 = np.maximum(E - 2016, 0)   # FP2-8 v2 (K1): member-statistics window [max(E-2016,0), E) — the E-0909-A clamp the per-feature windows already had;\n'
        '                               #   v1 indexed E-2016 unclamped here (wraps to the cache tail for E<2016 ⇒ v7==0 ⇒ 30 anchors silently dropped)\n'
        'n7 = np.maximum(qv_f[E] - qv_f[S7], 1)\n'
        'covr = (CS["ret5"][1][E] - CS["ret5"][1][S7]) / np.maximum(E - S7, 1)[:, None]   # coverage over the ACTUAL window (P.1), not the constant 2016\n'
        'qvm = (qv_s[E] - qv_s[S7]) / n7\n'
        'm7 = (CS["ret5"][0][E] - CS["ret5"][0][S7])\n'
        'v7 = np.sqrt(np.maximum((r2s[E] - r2s[S7]) / n7 - (m7 / n7) ** 2, 0))\n', "K1")
    t = replace_once(t,
        'MS, keep = [], []\nfor i in range(len(E)):\n    ok = (covr[i] >= 0.95) & (v7[i] >= 1e-4) & np.isfinite(y4[i])\n',
        'MM, _mm_rec = _member_mask_rows(CTS[E], syms)   # FP2-8 v2 (M): optional training member mask, ANDed into the member rule\n'
        'MS, keep = [], []\nfor i in range(len(E)):\n    ok = (covr[i] >= 0.95) & (v7[i] >= 1e-4) & np.isfinite(y4[i]) & MM[i]\n', "K-M")
    t = replace_once(t,
        'print(f"anchors {len(E)}", flush=True)\n',
        'print(f"anchors {len(E)} (E<2016: {int((E < 2016).sum())}; member_mask {_mm_rec})", flush=True)\n', "K-print")
    t = replace_once(t,
        '                    y4=y4, qvk=qvk.astype(np.float32), names=np.array([n + s for n in val_names for s in ("_v", "_r")] + fund_names))\n',
        '                    y4=y4, qvk=qvk.astype(np.float32), names=np.array([n + s for n in val_names for s in ("_v", "_r")] + fund_names),\n'
        '                    builder=np.array("pod_fea_ext_clamp_v2.py"), member_window=np.array("[max(E-2016,0), E) coverage over actual window (FP2-8 K1)"),\n'
        '                    member_mask_json=np.array(__import__("json").dumps(_mm_rec)), n_anchors_before_2016=np.array(int((E < 2016).sum())))\n', "K-meta")
    return t

def derive_dl(t):
    t = replace_once(t, '\n\ndef main():\n', '\n' + HELPER.replace("{OS}", "os") + '\n\ndef main():\n', "D-helper")
    t = replace_once(t,
        '    MS, keep = [], []\n    for i in range(len(E)):\n        ok = (covr[i] >= 0.95) & (vstd[i] >= 1e-4) & np.isfinite(y4s[i])\n',
        '    MM, _mm_rec = _member_mask_rows(CTS[E], syms); rep["member_mask"] = _mm_rec   # FP2-8 v2 (M): optional training member mask, ANDed into the member rule\n'
        '    MS, keep = [], []\n    for i in range(len(E)):\n        ok = (covr[i] >= 0.95) & (vstd[i] >= 1e-4) & np.isfinite(y4s[i]) & MM[i]\n', "D-M")
    t = replace_once(t,
        '                years={str(k): int(v) for k, v in zip(*np.unique(yrs, return_counts=True))}, cache=CACHE, panel=PANEL)\n',
        '                years={str(k): int(v) for k, v in zip(*np.unique(yrs, return_counts=True))}, cache=CACHE, panel=PANEL,\n'
        '                builder="pod_dlw_targets_raw_v2.py", member_mask=rep["member_mask"])\n', "D-meta")
    return t

if __name__ == "__main__":
    for k, fn in (("king", derive_king), ("dl", derive_dl)):
        src = open(os.path.join(HERE, V1[k]), "rb").read(); sha1 = hashlib.sha256(src).hexdigest()
        if V1_SHA[k] and sha1 != V1_SHA[k]: sys.exit("%s: v1 sha %s != pinned %s — refuse to derive from a moved v1" % (V1[k], sha1[:8], V1_SHA[k][:8]))
        out = fn(src.decode("utf-8")).encode("utf-8"); dst = os.path.join(HERE, V2[k])
        prev = open(dst, "rb").read() if os.path.exists(dst) else None
        open(dst, "wb").write(out)
        print("%s  v1 %s  ->  %s  v2 %s%s" % (V1[k], sha1[:8], V2[k], hashlib.sha256(out).hexdigest()[:8], "" if prev is None else ("  (unchanged)" if prev == out else "  (CHANGED)")))
