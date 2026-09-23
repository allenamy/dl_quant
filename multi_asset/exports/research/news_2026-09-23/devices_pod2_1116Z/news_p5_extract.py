"""NEWS P5: extract the training-build rows at the parity anchors 2026-09-17T16Z..09-19T00Z (features, OOF scores, legs, evaluation
combo state) into one small npz for the Mac parity run. Read-only on the build artifacts; sha of every source recorded."""
import os, sys, json, hashlib
import numpy as np
W = "/dev/shm/news_2026-09-23"; ANCH = [1789660800 + 14400 * k for k in range(9)]


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


def main():
    src = {k: f"{W}/{p}" for k, p in (("features", "work/NEWS_FEATURES.npz"), ("king_oof", "work/king/KING_OOF.npz"), ("f10_oof", "work/f10_s42/F10_OOF.npz"),
                                       ("legs", "work/legs.npz"), ("combo", "work/combo_s42/scaled_diagnostic.npz"))}
    F = np.load(src["features"]); K = np.load(src["king_oof"]); G = np.load(src["f10_oof"]); L = np.load(src["legs"]); C = np.load(src["combo"])
    import sys as _s; _s.path.insert(0, f"{W}/devices")
    from book_universe import align, PATH as UP, SHA as US
    assert sha(UP) == US; U = np.load(UP)
    mk = np.load("/workspace/axis_0919/x0918r/masks/member_mask_tradable_AND_live_W24H_cachegrid.npz"); crypto = np.load(f"{W}/receipts/P1_members_2025H2on.npz")["crypto"]
    a = F["anchors"].astype(np.int64); off = F["off"]; ca = C["E_ts"].astype(np.int64); out = {}
    for A in ANCH:
        i = int(np.searchsorted(a, A)); assert a[i] == A; sl = slice(off[i], off[i + 1]); m = F["m"][sl].astype(np.int64)
        out[f"m_{A}"] = m
        for k in ("X78", "X82", "X89", "fe_v", "fn_v", "rev24", "qvm"): out[f"{k}_{A}"] = F[k][sl]
        out[f"base_val_{A}"] = F["base_val"][i]
        out[f"king_oof_{A}"] = K["P"][i, m].astype(np.float64); out[f"f10_oof_{A}"] = G["P"][i, m].astype(np.float64)
        for k in ("KZ", "Z24", "ZFD"): out[f"{k}_{A}"] = L[k][i, m].astype(np.float64)
        out[f"WL_{A}"] = L["WL"][i].astype(np.float64)
        j = int(np.searchsorted(ca, A)); assert ca[j] == A
        out[f"kc_prev_{A}"] = C["kc"][j - 1]; out[f"fc_prev_{A}"] = C["fc"][j - 1]; out[f"raw_{A}"] = C["raw"][j]; out[f"trade_mask_{A}"] = C["trade_mask"][j]
        out[f"book_legal_{A}"] = align(np.array([A]), F["symbols"], U)[0] & mk["mask"][int(np.searchsorted(mk["ts"], A))] & crypto
    p = f"{W}/work/NEWS_TRAIN_PARITY_ROWS.npz"; np.savez(p, anchors=np.array(ANCH), **out)
    json.dump({"sources": {k: {"path": v, "sha256": sha(v)} for k, v in src.items()}, "output": p, "sha256": sha(p)}, open(f"{W}/receipts/P5_TRAIN_PARITY_ROWS.json", "w"), indent=1)
    print("EXTRACTED", p, sha(p))


if __name__ == "__main__":
    main()
