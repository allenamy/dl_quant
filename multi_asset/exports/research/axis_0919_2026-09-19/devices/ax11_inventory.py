"""AX11 (axis_0919): inventory + axis audit of every component under the new root (pure reads, one JSON receipt).
Per artifact: path, sha256, bytes, first/last timestamp, shape of the main arrays.
Axis audit (X5-type): each anchor axis (targets RAW/CLIP, king meta, accounting meta) must be strictly 4h-regular except for NAMED missing anchors;
the missing anchors inside [first, last] are listed with their member-mask row sums (a mask row with < 50 True cells explains a builder drop, MIN_MEM=50).
Dead-contract check: member-mask cells that are True more than 24h after the symbol's last TRADED bar (tradability last_traded_ts) must be 0.
Funding completeness (X4-type): per anchor after AX_X4_FROM, share of king members with finite f_fund_ema in the v2ext panel (panel rows only).
env: AXR, AX_X4_FROM (ts), AX_RECEIPT
"""
import os, json, time, hashlib, zipfile
import numpy as np
R = os.environ["AXR"]; RPT = os.environ["AX_RECEIPT"]; X4_FROM = int(os.environ["AX_X4_FROM"]); assert not os.path.exists(RPT)
U = lambda t: time.strftime("%Y-%m-%d %H:%MZ", time.gmtime(int(t)))
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 24), b""): h.update(c)
    return h.hexdigest()
inv = {}
def add(name, path, tkey=None, arrays=(), npy=False):
    if not os.path.exists(path): inv[name] = {"path": path, "MISSING": True}; return
    r = {"path": path, "sha256": sha(path), "bytes": os.path.getsize(path)}
    if npy:
        a = np.load(path, mmap_mode="r"); r["shape"] = list(a.shape); r["dtype"] = str(a.dtype)
    elif not path.endswith(".npz"):
        pass                                             # json receipts/state: sha + bytes only
    else:
        with zipfile.ZipFile(path) as z:
            names = [n[:-4] for n in z.namelist()]
        Z = np.load(path, allow_pickle=True)
        if tkey and tkey in names:
            t = Z[tkey].astype(np.int64); r.update(first=U(t.min()), last=U(t.max()), n_t=int(len(t)))
        for k in arrays:
            if k in names:
                a = Z[k]; r.setdefault("shapes", {})[k] = list(a.shape)
    inv[name] = r
C = f"{R}/data/dlnative_5m_wide829_f16_holefix2_x0918.npz"
add("cache_5m", C, "ts", ("data",))
add("raw_patch", f"{R}/data/raw_patch.npz", "ts", ("row",)); add("raw_patch_manifest", f"{R}/data/raw_patch.manifest.json")
add("funding_ledger", f"{R}/funding/funding_ledger.npz", "ts", ("rate", "iv")); add("funding_4h_accounting", f"{R}/funding/funding_4h_accounting.npz", "ts", ("f_fund_now", "next4h_sum"))
for b in ("rawbuild", "v2ext", "v3splice"): add(f"panel_{b}", f"{R}/panels/wide_panel_4h_{b}_x0918.npz", "ts", ("f_fund_now", "f_fund_iv", "Y4", "elig"))
for b in ("v2ext", "v3splice"): add(f"ema_state_{b}", f"{R}/panels/fund_state_canoncont_{b}_x0918.json")
add("tradability", f"{R}/trd/tradability_v1.npz", "anchor_ts", ("state_W24H", "ts5"))
add("mask_tradable_W24H", f"{R}/masks/member_mask_tradable_W24H_cachegrid.npz", "ts", ("mask",))
add("mask_tradable_AND_live_W24H", f"{R}/masks/member_mask_tradable_AND_live_W24H_cachegrid.npz", "ts", ("mask",))
add("hole_cells_copy", f"{R}/inputs/holefix2_cells.npz")
add("dl_targets_RAW", f"{R}/dlw_v4raw/data/dlw_targets.npz", "E_ts", ("y4s", "YR4s", "qvk"))
add("dl_targets_CLIP", f"{R}/dlw_hf3/data/dlw_targets.npz", "E_ts", ("y4s",))
add("dl_fea82", f"{R}/dlw_hf3/data/dlw_fea82.npz", None, ("X", "pair_a")); add("dl_fea82_copy_in_raw", f"{R}/dlw_v4raw/data/dlw_fea82.npz")
add("f8_fea89", f"{R}/f8_v4/data/f8_fea89.npz", None, ("X", "pair_a"))
add("king_fea", f"{R}/data/wide_fea_v4.npy", npy=True); add("king_meta", f"{R}/data/wide_fea_v4_meta.npz", "E_ts", ("y4", "qvk"))
add("meta_newprod_v4", f"{R}/meta/meta_newprod_v4_x0918.npz", "E_ts", ("y4", "qvk"))
out = {"device": "ax11_inventory.py", "self_sha256": sha(os.path.abspath(__file__)), "root": R, "inventory": inv, "axis": {}}
# ---- axis audit
MK = np.load(f"{R}/masks/member_mask_tradable_AND_live_W24H_cachegrid.npz", allow_pickle=True); mts = MK["ts"].astype(np.int64); MM = np.asarray(MK["mask"])
mrow = {int(t): i for i, t in enumerate(mts)}
for name, p in (("dl_targets_RAW", f"{R}/dlw_v4raw/data/dlw_targets.npz"), ("dl_targets_CLIP", f"{R}/dlw_hf3/data/dlw_targets.npz"),
                ("king_meta", f"{R}/data/wide_fea_v4_meta.npz"), ("meta_newprod_v4", f"{R}/meta/meta_newprod_v4_x0918.npz")):
    if not os.path.exists(p): continue
    E = np.load(p, allow_pickle=True)["E_ts"].astype(np.int64)
    full = np.arange(E[0], E[-1] + 1, 14400); miss = np.setdiff1d(full, E)
    out["axis"][name] = {"n": int(len(E)), "first": U(E[0]), "last": U(E[-1]), "strictly_increasing": bool(np.all(np.diff(E) > 0)),
                         "n_grid_first_to_last": int(len(full)), "n_missing_inside": int(len(miss)),
                         "missing_inside": [{"anchor": U(t), "mask_row_true": (int(MM[mrow[int(t)]].sum()) if int(t) in mrow else None)} for t in miss[:40]],
                         "anchors_after_2026_08_31T20Z": int((E > 1788206400).sum())}
# ---- dead-contract check on the member mask
T = np.load(f"{R}/trd/tradability_v1.npz", allow_pickle=True); lt = T["last_traded_ts"].astype(np.int64)
dead_after = (mts[:, None] > (lt[None, :] + 86400)) & (lt[None, :] >= 0)
never = (lt < 0)[None, :] & np.ones((len(mts), 1), bool)
out["dead_contract_check"] = {"mask_true_more_than_24h_after_last_trade": int((MM & dead_after).sum()), "mask_true_never_traded": int((MM & never).sum()),
                              "dead_symbols_in_data": int(((lt >= 0) & (lt < int(T["data_end_ts"]) - 86400)).sum())}
MT = np.load(f"{R}/masks/member_mask_tradable_W24H_cachegrid.npz", allow_pickle=True)["mask"]
out["dead_contract_check"]["tradable_mask_true_more_than_24h_after_last_trade"] = int((np.asarray(MT) & dead_after).sum())
# ---- X4-type funding completeness on king members
KM = f"{R}/data/wide_fea_v4_meta.npz"
if os.path.exists(KM):
    M = np.load(KM, allow_pickle=True); P = np.load(f"{R}/panels/wide_panel_4h_v2ext_x0918.npz", allow_pickle=True)
    prow = {int(t): i for i, t in enumerate(P["ts"].astype(np.int64))}; fe = P["f_fund_ema"]; fn = P["f_fund_now"]
    rows = []; MMEM = M["members"]                       # materialise once
    for i, t in enumerate(M["E_ts"].astype(np.int64)):
        if t < X4_FROM: continue
        j = prow.get(int(t)); m = np.asarray(MMEM[i], int)
        rows.append({"anchor": U(t), "members": int(len(m)), "panel_row": j is not None,
                     "fund_ema_finite_share": (float(np.isfinite(fe[j, m]).mean()) if j is not None else None),
                     "fund_now_finite_share": (float(np.isfinite(fn[j, m]).mean()) if j is not None else None)})
    sh = [r["fund_ema_finite_share"] for r in rows if r["fund_ema_finite_share"] is not None]
    out["X4_fund_completeness_king_members"] = {"from": U(X4_FROM), "n_anchors": len(rows), "n_with_panel_row": len(sh), "min_share": min(sh) if sh else None,
                                                "median_share": float(np.median(sh)) if sh else None, "anchors_below_0.95": [r for r in rows if r["fund_ema_finite_share"] is not None and r["fund_ema_finite_share"] < 0.95][:20],
                                                "anchors_without_panel_row": [r["anchor"] for r in rows if not r["panel_row"]]}
json.dump(out, open(RPT, "w"), indent=1, default=str)
print("AX11_DONE", json.dumps({"axis": out["axis"], "dead": out["dead_contract_check"], "X4": {k: v for k, v in out.get("X4_fund_completeness_king_members", {}).items() if k != "anchors_below_0.95"}}, default=str)[:3000], flush=True)
