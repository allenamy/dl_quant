"""King leg on the corrected features: frozen booster slow2026.txt (deployed v3), NO retraining.
GATE K1: re-predict every 2026 anchor from the OLD features (wide_fea_v2ext.npy) with the same support rule
         (members ∩ finite(y4), 78 cols = names[4:82] == live_pins.keep_names) and require BITWISE equality with
         the deployed /workspace/shadow_bundle_v3/slow_pred_pinned.npy on those anchors.  Fail -> stop.
Then predict 2026 anchors >= 2026-08-12 00:00Z from the NEW features (wide_fea_v2holefix), keep all other rows
verbatim from the pinned file, and write SLOW_hf2.npy on the 10182-anchor axis. Report first changed anchor."""
import numpy as np, json, time, calendar, hashlib, sys, os
import lightgbm as lgb
OUT = "/workspace/review_scratch/king_hf2"; os.makedirs(OUT, exist_ok=True)
def T(s): return time.strftime("%F %H:%MZ", time.gmtime(int(s)))
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 24), b""): h.update(b)
    return h.hexdigest()
BOOST = "/workspace/shadow_bundle_v3/slow2026.txt"; PIN = "/workspace/shadow_bundle_v3/slow_pred_pinned.npy"
assert sha(BOOST).startswith("8d79186b6380132c"), "booster identity"
PINS = json.load(open("/workspace/live_pins.json"))
MO = np.load("/workspace/data/wide_fea_v2ext_meta.npz", allow_pickle=True); MN = np.load("/workspace/data/wide_fea_v2holefix_meta.npz", allow_pickle=True)
eo = MO["E_ts"].astype(np.int64); en = MN["E_ts"].astype(np.int64); assert (en[:len(eo)] == eo).all()
names = [str(x) for x in MO["names"]]; keep = [k for k, nm in enumerate(names) if not (nm.startswith("ret5_sum_48") or nm.startswith("ret5_sum_288"))]
assert [names[k] for k in keep] == PINS["keep_names"] and keep == list(range(4, 82)), (keep[:5], len(keep))
FO = np.load("/workspace/data/wide_fea_v2ext.npy", mmap_mode="r"); FN = np.load("/workspace/data/wide_fea_v2holefix.npy", mmap_mode="r")
PINNED = np.load(PIN); assert PINNED.shape == (len(eo), 829)
bst = lgb.Booster(model_file=BOOST)
yrs_o = np.array([time.gmtime(int(t)).tm_year for t in eo]); yrs_n = np.array([time.gmtime(int(t)).tm_year for t in en])
MEMO, Y4O = MO["members"], MO["y4"]; MEMN, Y4N = MN["members"], MN["y4"]      # materialise once
def predict_anchor(FEA, meta, i):
    mem, y4 = (MEMO, Y4O) if meta is MO else (MEMN, Y4N)
    m = np.asarray(mem[i]); yv = y4[i, m]; ok = np.isfinite(yv)
    if ok.sum() == 0: return None, None
    X = np.asarray(FEA[i, m[ok]])[:, keep].astype(np.float32)
    return m[ok], bst.predict(X)
# ---- GATE K1 on OLD features, all 2026 anchors ----
te = np.where(yrs_o == 2026)[0]; bad = 0; n_cells = 0; first_bad = None; maxabs = 0.0
for i in te:
    cols, pv = predict_anchor(FO, MO, i)
    if cols is None: continue
    ref = PINNED[i, cols]; cand = pv.astype(np.float32)
    d = cand.view(np.uint32) != ref.view(np.uint32); n_cells += len(cols)
    if d.any():
        bad += int(d.sum()); maxabs = max(maxabs, float(np.abs(cand - ref).max()))
        if first_bad is None: first_bad = eo[i]
    # support identity: pinned must be NaN exactly outside cols
    outside = np.ones(829, bool); outside[cols] = False
    assert not np.isfinite(PINNED[i, outside]).any(), "pinned has scores outside members∩finite(y4) at %s" % T(eo[i])
print("K1 old-feature re-prediction vs deployed pinned: 2026 anchors %d, cells %d, different uint32 %d, maxabs %.3e, first bad %s -> %s"
      % (len(te), n_cells, bad, maxabs, T(first_bad) if first_bad is not None else "-", "PASS" if bad == 0 else "FAIL"), flush=True)
if bad: sys.exit(3)
# ---- corrected features: re-predict 2026 anchors >= 2026-08-12 00:00Z on the NEW axis ----
CH = calendar.timegm((2026, 8, 12, 0, 0, 0))
SLOW = np.full((len(en), 829), np.nan, np.float32); SLOW[:len(eo)] = PINNED
first_changed = None; n_changed_anchors = 0; n_changed_cells = 0; new_anchor_finite = []
for i in range(len(en)):
    if en[i] < CH or yrs_n[i] != 2026: continue
    cols, pv = predict_anchor(FN, MN, i)
    row = np.full(829, np.nan, np.float32)
    if cols is not None: row[cols] = pv.astype(np.float32)
    if i < len(eo):
        old = PINNED[i]; ch = (np.isfinite(old) ^ np.isfinite(row)) | (np.isfinite(old) & np.isfinite(row) & (old != row))
        if ch.any():
            n_changed_anchors += 1; n_changed_cells += int(ch.sum())
            if first_changed is None: first_changed = en[i]
    else:
        new_anchor_finite.append(int(np.isfinite(row).sum()))
    SLOW[i] = row
np.save(OUT + "/SLOW_hf2.npy", SLOW)
res = {"booster_sha256": sha(BOOST), "pinned_sha256": sha(PIN), "axis": int(len(en)), "K1_pass": True,
       "changed_anchors_vs_pinned": n_changed_anchors, "changed_cells": n_changed_cells, "first_changed": T(first_changed) if first_changed else None,
       "new_anchors_08-31_finite": new_anchor_finite, "out": OUT + "/SLOW_hf2.npy", "out_sha256": sha(OUT + "/SLOW_hf2.npy")}
json.dump(res, open(OUT + "/RESULT.json", "w"), indent=1)
print("corrected-feature re-prediction: changed anchors %d, cells %d, FIRST changed %s ; 08-31 new anchors finite %s" % (n_changed_anchors, n_changed_cells, res["first_changed"], new_anchor_finite), flush=True)
print("KING_EXTEND_DONE", flush=True)
