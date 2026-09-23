"""DESIGN A5 open question: do the fund panel's HISTORICAL rows reach anything the model consumes?

A5 says "F10 面板只填当前锚那一行; 历史锚那几行此前填 0 ... 若 news2 确认历史行不进特征则保持".
Source reading says no: dlw_features writes them into X82 columns 80/81 for every anchor row, f8 never
reads columns 80/81, and combo_stage extracts only pair_a == a_i. This checks it instead of asserting
it: fill every NON-extracted row of the panel with a large sentinel and see whether the extracted
X82/X89 row moves.
"""
import json, os, sys, time
import numpy as np
W2 = "/dev/shm/news2_2026-09-23"
sys.path.insert(0, f"{W2}/devices")
import news2_hist_features as H

PAR = f"{W2}/inputs"
C = np.load(f"{PAR}/parity_cache_slice.npz", allow_pickle=True)
ts = C["ts"].astype(np.int64); D = C["data"]; row0 = int(C["row0"])
syms = [str(s) for s in C["symbols"]]; chn = [str(c) for c in C["ch"]]
with np.load(f"{PAR}/parity_holes_slice.npz") as z: hz = {"row": z["row"], "col": z["col"]}
o = np.lexsort((hz["col"], hz["row"])); holes = (hz["row"][o].astype(np.int64) - row0, hz["col"][o].astype(np.int64))
with np.load(f"{PAR}/parity_mask_slice.npz") as z: mk = {"ts": z["ts"].astype(np.int64), "mask": z["mask"]}
with np.load(f"{PAR}/parity_fund_slice.npz") as z: fr = {k: z[k] for k in ("anchors","ema_acc","last_ft","last_rate","last_iv")}
with np.load(f"{PAR}/P1_members_2025H2on.npz") as z: crypto = z["crypto"]
cfg = json.load(open(f"{PAR}/bundle_config.json"))
fa = fr["anchors"].astype(np.int64); mts = mk["ts"]

ORIG = H.replay_anchor
def patched(*a, **kw):
    return ORIG(*a, **kw)

rows = []
for A in (1789660800, 1789689600):
    i = int(np.searchsorted(fa, A)); mi = int(np.searchsorted(mts, A))
    cand = mk["mask"][mi] & crypto
    ema = {syms[j]: {"acc": float(fr["ema_acc"][i, j])} for j in np.flatnonzero(np.isfinite(fr["ema_acc"][i]))}
    led = {syms[j]: [[int(fr["last_ft"][i, j]), float(fr["last_rate"][i, j]), float(fr["last_iv"][i, j])]]
           for j in np.flatnonzero(fr["last_ft"][i] >= 0)}
    H.set_tree(f"{W2}/work/gate/tree_all")
    base = ORIG(A, D, ts, syms, chn, cand, ema, led, cfg["params"], cfg, f"{W2}/work/gate/mini", holes=holes, cols="members")
    # monkeypatch np.savez so the panel written for the mini pipeline has poisoned historical rows
    real_savez = np.savez
    def poisoned(file, *a, **kw):
        if str(file).endswith("xfer_panel_live.npz") and "f_fund_ema" in kw:
            fe = np.array(kw["f_fund_ema"]); fn = np.array(kw["f_fund_now"])
            fe[:-1] = 12345.0; fn[:-1] = -678.0
            kw = dict(kw); kw["f_fund_ema"] = fe; kw["f_fund_now"] = fn
        return real_savez(file, *a, **kw)
    np.savez = poisoned
    try:
        pois = ORIG(A, D, ts, syms, chn, cand, ema, led, cfg["params"], cfg, f"{W2}/work/gate/mini", holes=holes, cols="members")
    finally:
        np.savez = real_savez
    def d(x, y):
        x = np.asarray(x, np.float64); y = np.asarray(y, np.float64)
        return int((~((x == y) | (np.isnan(x) & np.isnan(y)))).sum())
    r = {"anchor": A, "n_members": int(len(base["m"])),
         "X82_cells_changed": d(base["X82"], pois["X82"]), "X89_cells_changed": d(base["X89"], pois["X89"]),
         "kingX78_cells_changed": d(base["king_X78"], pois["king_X78"]),
         "same_members": bool(np.array_equal(base["m"], pois["m"]))}
    rows.append(r); print(A, r, flush=True)
tot = sum(r["X82_cells_changed"] + r["X89_cells_changed"] + r["kingX78_cells_changed"] for r in rows)
out = {"question": "DESIGN A5: do the fund panel's historical rows reach the extracted row?",
       "method": "every non-extracted panel row poisoned with fund_ema=12345, fund_now=-678",
       "rows": rows, "total_cells_changed": tot,
       "ANSWER": "NO - historical fund-panel rows do not reach any feature the model consumes" if tot == 0
                 else "YES - %d cells changed" % tot}
print(json.dumps({k: out[k] for k in ("total_cells_changed", "ANSWER")}))
open(f"{W2}/receipts/A5_FUND_PANEL_HISTORICAL_ROWS.json", "w").write(json.dumps(out, indent=1))
