#!/usr/bin/env python3
"""Object B v4 arm · king (PREREG AMENDMENT 5 A5.1): king v4 yearly folds, saved, with K-REPRO-v4 (same rule as K-REPRO). Derived from king_v3_folds.py:
only the constants below change (exporter = v4, data = wide_fea_v4, pinned = shadow_bundle_v4, outputs king_v4_*).
Original v3 docstring follows.
Object B · S1: king v3 yearly folds, saved, with the reproduction gate K-REPRO.
Comparison type (3) packaging/prediction parity for the gate (no returns).

Recipe = /workspace/pod_export_bundle_v3.py (sha c210bac6…) L26–60, the in-service v3 bundle exporter: rows = members with finite y4 on anchors
with >= 50 such members; Y = centred rank of y4; features = keep columns; LGBMRegressor(n_estimators=400, learning_rate=0.05, num_leaves=63,
subsample=0.8, colsample_bytree=0.8, n_jobs=100, verbose=-1) fitted on rows with anchor-year < fold year. The code blocks below are the exporter's
text; this device asserts that each block occurs verbatim in the exporter source before running (RECIPE_BLOCKS).
Folds trained and SAVED: 2023, 2024, 2025 (object B serves them); 2026 is retrained ONLY for the gate (object B serves the in-service
slow2026.txt 8d79186b itself, which is the year<2026 fold by construction).
K-REPRO: float32(pred) of retrained folds 2024/2025/2026 on their test cells vs shadow_bundle_v3/slow_pred_pinned.npy (158cd4ac); retrained 2026
model text sha vs 8d79186b. PASS = all bitwise; REPRO_NUMERIC = max|d| <= 1e-6 and per-anchor ranks identical; else NEW_DRAW.
Negative control: the same comparator on (pinned 2024 rows, retrained fold-2025 model's predictions on 2024 test rows) must report not-equal.
Writes only /workspace/object_b_2026-09-19/{models,receipts}."""
import os, sys, json, time, hashlib
import numpy as np
from scipy.stats import rankdata

R = "/workspace/object_b_2026-09-19"
SRC = {"exporter": ("/workspace/object_b_2026-09-19/work/pod_export_bundle_v4.py", "42555a37c0cd3a7e128ac8823a8bec3e2f77a1230d205707b046aca20eed5118"),
       "fea": ("/workspace/data/wide_fea_v4.npy", "268f6c9c247cdf1fffb6cea442437ab21b3f13993f9d821cfb09f417417cad7a"),
       "meta": ("/workspace/data/wide_fea_v4_meta.npz", "12ea42c4557093f10f954f648db9239f4dd8283ea365ba299f31bd81e7e5ab51"),
       "pins": ("/workspace/live_pins.json", "fd27fe485417d307e5bc41ee382a2db098118bee1fe2a13ebde98c7e7d3caece"),
       "pinned": ("/workspace/shadow_bundle_v4/slow_pred_pinned.npy", "dde19142d017c37dd9bae564ab4a32a4b9b068f6aef8acc91e7ea329f4f1c8a6"),
       "slow2026": ("/workspace/shadow_bundle_v4/slow2026.txt", "f23657710f3a6d0068bca8a95082965d694de805195ef143be64951c0f2f203a")}
RECIPE_BLOCKS = [
    'keep = [k for k, nm in enumerate(names) if not (nm.startswith("ret5_sum_48") or nm.startswith("ret5_sum_288"))]',
    """for i in range(nA):
    m = members[i]
    yv = y4[i, m]; ok = np.isfinite(yv)
    if ok.sum() < 50: continue
    rr = rankdata(yv[ok]) / max(ok.sum() - 1, 1) - 0.5
    rows_X.append(FEA[i, m[ok]][:, keep].astype(np.float32))
    rows_y.append(rr.astype(np.float32)); rows_a.append(np.full(ok.sum(), i, np.int32))""",
    "X = np.concatenate(rows_X); Y = np.concatenate(rows_y); A = np.concatenate(rows_a)",
    """    g2 = lgb.LGBMRegressor(n_estimators=400, learning_rate=0.05, num_leaves=63,
                           subsample=0.8, colsample_bytree=0.8, n_jobs=100, verbose=-1).fit(X[tr_], Y[tr_])
    pv = g2.predict(X[te_]); a_te = A[te_]""",
    """        sel = a_te == a; m = members[a]; okm = np.isfinite(y4[a, m])
        PRED[a, m[okm]] = pv[sel]""",
]


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 24), b""): h.update(ch)
    return h.hexdigest()
def iso(t): return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(t)))
T0 = time.time()
def log(*a): print(f"[{time.time()-T0:7.1f}s]", *a, flush=True)


def main():
    assert set(os.environ) <= {"PATH", "HOME", "LC_CTYPE", "PWD", "SHLVL", "_", "OLDPWD"}, sorted(os.environ)
    shas = {}
    for k, (p, s) in SRC.items():
        got = sha(p); assert got == s, (k, got); shas[k] = got
    exsrc = open(SRC["exporter"][0]).read()
    for b in RECIPE_BLOCKS: assert exsrc.count(b) == 1, ("recipe block not verbatim in exporter", b[:70])
    PINS = json.load(open(SRC["pins"][0]))
    # ── exporter L26–47 (verbatim semantics; blocks asserted above) ──
    FEA = np.load(SRC["fea"][0])
    MT = np.load(SRC["meta"][0], allow_pickle=True)
    E_ts = MT["E_ts"].astype(np.int64); members = MT["members"]; y4 = MT["y4"]
    names = [str(n) for n in MT["names"]]
    yrs = np.array([time.gmtime(int(t)).tm_year for t in E_ts])
    nA = len(E_ts); NW = 829
    keep = [k for k, nm in enumerate(names) if not (nm.startswith("ret5_sum_48") or nm.startswith("ret5_sum_288"))]
    assert [names[k] for k in keep] == PINS["keep_names"], "keep_names 与在役不一致"
    rows_X, rows_y, rows_a = [], [], []
    for i in range(nA):
        m = members[i]
        yv = y4[i, m]; ok = np.isfinite(yv)
        if ok.sum() < 50: continue
        rr = rankdata(yv[ok]) / max(ok.sum() - 1, 1) - 0.5
        rows_X.append(FEA[i, m[ok]][:, keep].astype(np.float32))
        rows_y.append(rr.astype(np.float32)); rows_a.append(np.full(ok.sum(), i, np.int32))
    X = np.concatenate(rows_X); Y = np.concatenate(rows_y); A = np.concatenate(rows_a)
    del FEA, rows_X
    YRA = yrs[A]
    log(f"rows {X.shape} anchors {nA} axis {iso(E_ts[0])} .. {iso(E_ts[-1])}")
    import lightgbm as lgb
    PINNED = np.load(SRC["pinned"][0])
    assert PINNED.shape == (nA, NW), PINNED.shape
    fold_meta = {}; preds = {}; models = {}
    # label end of fold Y = last anchor with year < Y that has >= 50 finite labels among members, + 4h (the fold's training rows end there)
    for YV in (2023, 2024, 2025, 2026):
        tr_ = YRA < YV; te_ = YRA == YV
        last_tr = int(E_ts[int(A[tr_].max())])
        t1 = time.time()
        g2 = lgb.LGBMRegressor(n_estimators=400, learning_rate=0.05, num_leaves=63,
                               subsample=0.8, colsample_bytree=0.8, n_jobs=100, verbose=-1).fit(X[tr_], Y[tr_])
        fit_s = round(time.time() - t1, 1)
        pv = g2.predict(X[te_]); a_te = A[te_]
        P = np.full((nA, NW), np.nan, np.float32)
        for a in np.unique(a_te):
            sel = a_te == a; m = members[a]; okm = np.isfinite(y4[a, m])
            P[a, m[okm]] = pv[sel]
        preds[YV] = P; models[YV] = g2
        out = f"{R}/models/king_v4_fold{YV}.txt" if YV < 2026 else f"{R}/work/king_v4_fold2026_REPRO_ONLY.txt"
        g2.booster_.save_model(out)
        fold_meta[str(YV)] = {"train_rows": int(tr_.sum()), "train_anchors": int(len(np.unique(A[tr_]))), "last_train_anchor": iso(last_tr),
                              "label_end": iso(last_tr + 14400), "label_end_ts": last_tr + 14400, "test_rows": int(te_.sum()),
                              "fit_s": fit_s, "model_file": out, "model_sha256": sha(out), "served_in_object_B": YV < 2026}
        log(f"fold {YV}: train rows {int(tr_.sum())} last train anchor {iso(last_tr)} fit {fit_s}s -> {out}")

    def compare(ref, new, rows):
        a = ref[rows]; b = new[rows]; fa = np.isfinite(a); fb = np.isfinite(b)
        same_support = bool(np.array_equal(fa, fb))
        both = fa & fb
        bitwise = same_support and bool(np.array_equal(a[both], b[both]))
        mx = float(np.abs(a[both].astype(np.float64) - b[both].astype(np.float64)).max()) if both.any() else 0.0
        ranks_equal = True
        for r in np.where(both.any(1))[0]:
            cols = both[r]
            if not np.array_equal(rankdata(a[r, cols]), rankdata(b[r, cols])): ranks_equal = False; break
        verdict = "PASS" if bitwise else ("REPRO_NUMERIC" if (same_support and mx <= 1e-6 and ranks_equal) else "NEW_DRAW")
        return {"n_cells": int(both.sum()), "same_support": same_support, "bitwise": bitwise, "max_abs": mx, "ranks_equal": ranks_equal, "verdict": verdict}

    gate = {}
    for YV in (2024, 2025, 2026):
        rows = np.where(yrs == YV)[0]
        gate[str(YV)] = compare(PINNED, preds[YV], rows)
        log(f"K-REPRO {YV}: {gate[str(YV)]}")
    txt26 = sha(fold_meta["2026"]["model_file"])
    gate["2026_model_text_sha_equal_inservice"] = (txt26 == SRC["slow2026"][1])
    # negative control: fold-2025 model predictions on the 2024 test rows vs pinned 2024 rows
    rows24 = np.where(yrs == 2024)[0]; a_te = A[YRA == 2024]
    Pn = np.full((nA, NW), np.nan, np.float32); pvn = models[2025].predict(X[YRA == 2024])
    for a in np.unique(a_te):
        sel = a_te == a; m = members[a]; okm = np.isfinite(y4[a, m]); Pn[a, m[okm]] = pvn[sel]
    neg = compare(PINNED, Pn, rows24)
    neg_ok = neg["verdict"] == "NEW_DRAW"
    verdicts = [gate[k]["verdict"] for k in ("2024", "2025", "2026")]
    overall = ("PASS" if all(v == "PASS" for v in verdicts) and gate["2026_model_text_sha_equal_inservice"] else
               ("REPRO_NUMERIC" if all(v in ("PASS", "REPRO_NUMERIC") for v in verdicts) else "NEW_DRAW"))
    doc = {"device": os.path.abspath(__file__), "self_sha256": sha(os.path.abspath(__file__)), "comparison_type": "(3) packaging/prediction parity — not a return",
           "inputs_sha256": shas, "env": dict(os.environ), "python": sys.version.split()[0], "numpy": np.__version__, "lightgbm": lgb.__version__,
           "folds": fold_meta, "K_REPRO": gate, "K_REPRO_VERDICT": overall, "negative_control": {"rule": "pinned 2024 rows vs fold-2025 model on 2024 rows must be NEW_DRAW", "result": neg, "ok": neg_ok},
           "gate_ok_to_use": neg_ok, "utc": iso(time.time()), "runtime_s": round(time.time() - T0, 1)}
    json.dump(doc, open(f"{R}/receipts/K_REPRO_v4.json", "w"), indent=1)
    print(f"K_REPRO_V4_VERDICT {overall} per-year {verdicts} text26_equal {gate['2026_model_text_sha_equal_inservice']} negctrl_ok {neg_ok}", flush=True)
    sys.exit(0 if neg_ok else 3)


if __name__ == "__main__":
    main()
