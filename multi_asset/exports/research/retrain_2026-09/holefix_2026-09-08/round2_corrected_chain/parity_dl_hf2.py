"""Input-layer parity gate for the CORRECTED chain (dlw_hf2 / f8_hf2, PANEL=v3splice) vs the ORIGINAL (dlw_ext / f8_ext).
Read-only. Reports, per artifact: axis prefix identity, per-anchor bitwise equality, FIRST changed anchor, changed columns.
Nothing is assumed about where the boundary should be — it is measured and then compared to the expected boundaries."""
import numpy as np, json, time, calendar, sys
def T(s): return time.strftime("%F %H:%MZ", time.gmtime(int(s)))
OLD_T = np.load("/workspace/dlw_ext/data/dlw_targets.npz", allow_pickle=True)
NEW_T = np.load("/workspace/dlw_hf2/data/dlw_targets.npz", allow_pickle=True)
eo = OLD_T["E_ts"].astype(np.int64); en = NEW_T["E_ts"].astype(np.int64)
print("== TARGETS ==", flush=True)
print("  anchors old %d new %d ; old is a prefix of new: %s ; extra new anchors: %s"
      % (len(eo), len(en), bool(len(en) >= len(eo) and (en[:len(eo)] == eo).all()), [T(x) for x in en[len(eo):]]), flush=True)
assert (en[:len(eo)] == eo).all()
mo, mn = OLD_T["members"], NEW_T["members"]; yo, yn = OLD_T["y4s"], NEW_T["y4s"]
first_m = None; n_m = 0; first_y = None; n_y = 0; y_cells = 0; y_lost = 0
for i in range(len(eo)):
    if not np.array_equal(np.asarray(mo[i]), np.asarray(mn[i])):
        n_m += 1
        if first_m is None: first_m = eo[i]
    a = yo[i].astype(np.float64); b = yn[i].astype(np.float64)
    fa, fb = np.isfinite(a), np.isfinite(b)
    d = (fa ^ fb) | (fa & fb & (a != b))
    if d.any():
        n_y += 1; y_cells += int(d.sum()); y_lost += int((fa & ~fb).sum())
        if first_y is None: first_y = eo[i]
print("  members : anchors changed %d ; FIRST changed anchor %s" % (n_m, T(first_m) if first_m is not None else "-"), flush=True)
print("  y4s     : anchors changed %d ; cells %d ; finite->NaN (lost) %d ; FIRST changed anchor %s" % (n_y, y_cells, y_lost, T(first_y) if first_y is not None else "-"), flush=True)
for k in ("YR4s", "YRZ", "qvk", "btcv"):
    if k in OLD_T.files and k in NEW_T.files:
        a = np.asarray(OLD_T[k]); b = np.asarray(NEW_T[k])[:len(eo)] if np.asarray(NEW_T[k]).shape[0] == len(en) else np.asarray(NEW_T[k])
        try:
            a = a.astype(np.float64); b = b.astype(np.float64)
            d = (np.isfinite(a) ^ np.isfinite(b)) | (np.isfinite(a) & np.isfinite(b) & (a != b))
            rows = np.where(d.reshape(d.shape[0], -1).any(1))[0] if d.ndim > 1 else np.where(d)[0]
            print("  %-6s : shape %s ; changed rows %d ; FIRST %s" % (k, a.shape, len(rows), T(eo[rows[0]]) if len(rows) else "-"), flush=True)
        except Exception as ex:
            print("  %-6s : skipped (%s)" % (k, type(ex).__name__), flush=True)
def feat(old_p, new_p, label):
    O = np.load(old_p, allow_pickle=True); N = np.load(new_p, allow_pickle=True)
    no = [str(x) for x in O["names"]]; nn = [str(x) for x in N["names"]]
    print("== %s == names identical: %s (%d cols) ; X dtype old %s new %s" % (label, no == nn, len(no), O["X"].dtype, N["X"].dtype), flush=True)
    assert no == nn
    pao = O["pair_a"].astype(np.int64); pso = O["pair_s"].astype(np.int64)
    pan = N["pair_a"].astype(np.int64); psn = N["pair_s"].astype(np.int64)
    ko = eo[pao] * 1000 + pso; kn = en[pan] * 1000 + psn
    # rows keyed by (E_ts, symbol) — index shift-proof
    common, io, in_ = np.intersect1d(ko, kn, return_indices=True)
    only_old = len(ko) - len(common); only_new = len(kn) - len(common)
    print("  rows old %d new %d common %d ; only-old %d ; only-new %d" % (len(ko), len(kn), len(common), only_old, only_new), flush=True)
    if only_old:
        oo = np.setdiff1d(ko, kn); print("    only-old FIRST anchor %s" % T(oo.min() // 1000), flush=True)
    if only_new:
        on = np.setdiff1d(kn, ko); print("    only-new FIRST anchor %s  LAST %s" % (T(on.min() // 1000), T(on.max() // 1000)), flush=True)
    Xo = O["X"]; Xn = N["X"]
    cells_changed = 0; rows_changed = 0; first = None; cols = np.zeros(len(no), np.int64); per_anchor = {}
    CH = 200000
    for s in range(0, len(common), CH):
        a = Xo[io[s:s+CH]].astype(np.float64); b = Xn[in_[s:s+CH]].astype(np.float64)
        d = (np.isfinite(a) ^ np.isfinite(b)) | (np.isfinite(a) & np.isfinite(b) & (a != b))
        if d.any():
            r = d.any(1); cells_changed += int(d.sum()); rows_changed += int(r.sum()); cols += d.sum(0)
            ts = common[s:s+CH][r] // 1000
            if first is None: first = ts.min()
            for t in np.unique(ts): per_anchor[int(t)] = per_anchor.get(int(t), 0) + int(d[r][ts == t].sum())
    print("  common rows: changed rows %d cells %d ; FIRST changed anchor %s" % (rows_changed, cells_changed, T(first) if first is not None else "-"), flush=True)
    if cells_changed:
        cc = [(no[j], int(cols[j])) for j in np.argsort(-cols) if cols[j] > 0]
        print("  changed columns (%d): %s" % (len(cc), cc[:12]), flush=True)
        ks = sorted(per_anchor)
        print("  changed anchors %d ; first 6: %s" % (len(ks), [(T(k), per_anchor[k]) for k in ks[:6]]), flush=True)
    return first
f82 = feat("/workspace/dlw_ext/data/dlw_fea82.npz", "/workspace/dlw_hf2/data/dlw_fea82.npz", "FEA82")
f89 = feat("/workspace/f8_ext/data/f8_fea89.npz", "/workspace/f8_hf2/data/f8_fea89.npz", "FEA89")
B1 = calendar.timegm((2026, 8, 12, 0, 5, 0))
print("\n== VERDICT ==", flush=True)
print("  first changed 5m bar in cache (D1'): %s" % T(B1), flush=True)
ok = True
for lab, f in (("members", first_m), ("y4s", first_y), ("fea82", f82), ("fea89", f89)):
    good = (f is None) or (f >= calendar.timegm((2026, 8, 12, 0, 0, 0)))
    ok &= good
    print("  %-8s first change %s -> %s" % (lab, T(f) if f is not None else "-", "OK (not before 2026-08-12 00:00Z)" if good else "*** BEFORE the repair region ***"), flush=True)
print("INPUT_PARITY_GATE %s" % ("PASS" if ok else "FAIL"), flush=True)
sys.exit(0 if ok else 3)
