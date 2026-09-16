"""fm_dlw_features_fund.py -- FX-MODEL new builder for FEA-01. Base: retrain_2026-09/pod_dlw_features_ext.py
(sha256 e86725cc2768bb6265dd8fb2b3580629706166da012298768b1c0788e8f5a624), copied VERBATIM except for ONE region:
the funding write at the base's L90-94. Everything else -- channel order, window arithmetic, cumsum dtypes, rank rule,
clipping, float16 storage, long-format layout, assertion text -- is unchanged, so that `diff` against the base shows
exactly one changed region and the legacy arm is the same machine.

KNOBS (all REQUIRED env; there are no defaults, deliberately -- a missing knob refuses rather than guessing):
  FMF_CACHE       5m cache npz                       (base: F171_CACHE)
  FMF_PANEL       4h panel npz the funding comes from (base: F171_PANEL)
  FMF_OUT         output dir; reads {OUT}/data/dlw_targets.npz, writes {OUT}/data/dlw_fea82.npz
  FMF_FUND_FILL   legacy_zero | nan_preserve
                    legacy_zero  == the base expression byte-for-byte: absent funding and an uncovered anchor both
                                    become a hard 0.0, indistinguishable from a true zero rate.
                    nan_preserve == absent stays NaN. This is NOT a cosmetic change: the trainer standardises THEN
                                    clips THEN nan_to_num (pod_f10_train_monthly_v4.py L200), so a NaN lands on the
                                    column mean in standardised space, whereas a raw 0.0 lands at (0-mu)/sd. Unknown
                                    is therefore imputed at the mean instead of asserted to be a specific wrong value.

WHAT THIS BUILDER DOES NOT DO, on purpose (independent review narrowing iii -- do not bundle interventions):
  - it does not add an availability column: that changes the model's input width (82 -> 84) and is a SEPARATE
    intervention needing its own arm;
  - it does not touch the member screens, the clock, the class filter or tradability -- those are other builders;
  - it does not choose the panel. Coverage is supplied by WHICH panel the caller points FMF_PANEL at, and that choice
    is recorded in the artifact's meta as panel_sha256. The FEA-01 fix is "point it at a full-coverage panel", and the
    legacy arm is "point it at the same v3splice panel the September chain used".

POSITIVE CONTROL (the thing that makes this builder admissible): with FMF_FUND_FILL=legacy_zero and FMF_PANEL set to
the panel the base consumed, the arrays X / pair_a / pair_s / names must be BITWISE identical to the base's output.
`fm_newbuilder_control.py` asserts exactly that. Note the scope of the word bitwise: the ARRAYS are bitwise identical;
the .npz FILE is not, and cannot be, because meta_json records self_sha256 and so necessarily names whichever device
produced it. Claiming file-level bitwise equality here would be false.
"""
import os, json, time, hashlib
import numpy as np
from scipy.stats import rankdata

_REQ = ("FMF_CACHE", "FMF_PANEL", "FMF_OUT", "FMF_FUND_FILL")
_missing = [k for k in _REQ if not os.environ.get(k)]
if _missing:
    raise SystemExit("FMF_REFUSED: required env not set, and this builder has no defaults: %s" % _missing)
CACHE = os.environ["FMF_CACHE"]
PANEL = os.environ["FMF_PANEL"]
OUT = os.environ["FMF_OUT"]
FUND_FILL = os.environ["FMF_FUND_FILL"]
if FUND_FILL not in ("legacy_zero", "nan_preserve"):
    raise SystemExit("FMF_REFUSED: FMF_FUND_FILL=%r not in {legacy_zero, nan_preserve}" % FUND_FILL)

CHN = ["ret5", "range", "cpos", "log_qv", "log_cnt", "log_avgsz", "tbf"]
WINS = (48, 288, 864, 2016, 8640)
T0 = time.time()


def log(*a):
    print(f"[{time.time()-T0:7.1f}s]", *a, flush=True)


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 24), b""):
            h.update(ch)
    return h.hexdigest()


def main():
    TG = np.load(f"{OUT}/data/dlw_targets.npz", allow_pickle=True)
    E = TG["E_row"].astype(np.int64); E_ts = TG["E_ts"].astype(np.int64); MS = TG["members"]; syms = [str(s) for s in TG["symbols"]]
    nA = len(E); NW = len(syms)
    Z = np.load(CACHE, allow_pickle=True)
    CD = Z["data"]; CTS = Z["ts"].astype(np.int64)
    assert [str(s) for s in Z["symbols"]] == syms and [str(c) for c in Z["ch"]] == CHN
    assert np.array_equal(CTS[E], E_ts), "E_row ↔ E_ts 不一致"
    TT = CD.shape[0]
    hi = E + 1                                   # CS 半开区间上界 ⇒ 最后一行 = E(收盘于 N)
    assert int((hi - 1 - E).max()) == 0, "max_feature_row 必须 == E"
    VAL, val_names = [], []
    z1 = np.zeros((1, NW))
    for c, nm in enumerate(CHN):
        x = CD[:, :, c].astype(np.float32); fin = np.isfinite(x)
        CSf = np.concatenate([z1.astype(np.int32), np.cumsum(fin, 0, dtype=np.int32)])
        CSx = np.concatenate([z1, np.cumsum(np.where(fin, x, 0).astype(np.float64), 0)])
        CS2 = np.concatenate([z1, np.cumsum(np.where(fin, x, 0).astype(np.float64) ** 2, 0)]) if c == 0 else None
        for w in WINS:
            lo = np.maximum(hi - w, 0)
            nf = np.maximum(CSf[hi] - CSf[lo], 1)
            if c == 0:
                VAL.append((CSx[hi] - CSx[lo]).astype(np.float32)); val_names.append(f"{nm}_sum_{w}")
            else:
                VAL.append(((CSx[hi] - CSx[lo]) / nf).astype(np.float32)); val_names.append(f"{nm}_mean_{w}")
        if c == 0:
            VOLS = []
            for w in WINS:
                lo = np.maximum(hi - w, 0); nf = np.maximum(CSf[hi] - CSf[lo], 1)
                mm = (CSx[hi] - CSx[lo]) / nf
                VOLS.append(np.sqrt(np.maximum((CS2[hi] - CS2[lo]) / nf - mm ** 2, 0)).astype(np.float32))
        del x, fin, CSf, CSx, CS2
        log(f"channel {nm} done")
    for w, v in zip(WINS, VOLS):
        VAL.append(v); val_names.append(f"vol_{w}")
    del CD
    PW = np.load(PANEL, allow_pickle=True)
    pw_row = {int(t): j for j, t in enumerate(PW["ts"].astype(np.int64))}
    FUND = [PW["f_fund_ema"].astype(np.float32), PW["f_fund_now"].astype(np.float32)]; fund_names = ["fund_ema", "fund_now"]
    NVAL = len(VAL); NF = NVAL * 2 + 2
    names = [n + s for n in val_names for s in ("_v", "_r")] + fund_names
    assert NF == 82 and len(names) == 82, (NF, len(names))
    n_pairs = int(sum(len(m) for m in MS))
    X = np.zeros((n_pairs, NF), np.float16); pair_a = np.zeros(n_pairs, np.int32); pair_s = np.zeros(n_pairs, np.int16)
    pos = 0; n_nofund = 0
    n_absent_cells = 0; n_nofund_cells = 0
    for i in range(nA):
        m = MS[i]; n = len(m); sl = slice(pos, pos + n)
        col = 0
        for v in VAL:
            xv = v[i, m]
            X[sl, col] = np.clip(np.nan_to_num(xv, nan=0.0), -1e4, 1e4); col += 1
            ok = np.isfinite(xv); rr = np.zeros(n, np.float32)
            if ok.sum() >= 10:
                rr[ok] = rankdata(xv[ok]) / max(ok.sum() - 1, 1) - 0.5
            X[sl, col] = rr; col += 1
        j = pw_row.get(int(E_ts[i]))
        if j is None:
            n_nofund += 1
        # ─────────────────────────── THE ONE CHANGED REGION (base L90-94) ───────────────────────────
        for fv in FUND:
            if FUND_FILL == "legacy_zero":
                X[sl, col] = 0.0 if j is None else np.nan_to_num(fv[j, m], nan=0.0)   # base expression, byte-for-byte
            else:                                                                     # nan_preserve
                if j is None:
                    X[sl, col] = np.nan
                    n_nofund_cells += n
                else:
                    vals = fv[j, m]
                    n_absent_cells += int((~np.isfinite(vals)).sum())
                    X[sl, col] = vals            # NaN stays NaN: unknown is not asserted to be zero
            col += 1
        # ────────────────────────────────── end changed region ──────────────────────────────────────
        pair_a[sl] = i; pair_s[sl] = m; pos += n
        if i % 2000 == 0:
            log(f"fea {i}/{nA}")
    assert pos == n_pairs
    meta = dict(n_pairs=n_pairs, n_anchors=int(nA), NF=NF, names=names, feature_row_window="[E-w+1, E] (max_feature_row == E)",
                anchors_without_panel_row=int(n_nofund), cache_sha256=sha(CACHE), panel_sha256=sha(PANEL), targets_sha256=sha(f"{OUT}/data/dlw_targets.npz"),
                self_sha256=sha(os.path.abspath(__file__)))
    meta["fm_knobs"] = {"FMF_FUND_FILL": FUND_FILL, "FMF_PANEL": PANEL, "FMF_CACHE": CACHE}
    meta["fm_base"] = {"file": "retrain_2026-09/pod_dlw_features_ext.py",
                       "sha256": "e86725cc2768bb6265dd8fb2b3580629706166da012298768b1c0788e8f5a624",
                       "changed_region": "funding write (base L90-94); every other line verbatim"}
    meta["fm_counts"] = {"absent_funding_cells_left_nan": int(n_absent_cells),
                         "uncovered_anchor_cells_left_nan": int(n_nofund_cells)}
    np.savez(f"{OUT}/data/dlw_fea82.npz", X=X, pair_a=pair_a, pair_s=pair_s, names=np.array(names), meta_json=json.dumps(meta))
    meta["fea_sha256"] = sha(f"{OUT}/data/dlw_fea82.npz")
    json.dump(meta, open(f"{OUT}/results/dlw_features_report.json", "w"), indent=1)
    log("FEATURES_DONE", X.shape, "no-panel anchors", n_nofund, "fill", FUND_FILL,
        "absent_cells_nan", n_absent_cells, "nofund_cells_nan", n_nofund_cells)


if __name__ == "__main__":
    main()
