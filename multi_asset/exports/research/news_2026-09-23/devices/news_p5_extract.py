"""NEWS P5: extract the EVALUATION side at the acceptance anchors (A0 = 2026-09-17T12Z and the nine anchors 09-17T16Z..09-19T00Z) into one
npz for the Mac candidate-package acceptance (mac_candidate_acceptance.py): members, training features, OOF scores (King; F10 s42 and
s2027), leg z / seats / rn8 / qv, the evaluation combo state (kc, fc, raw, weights, trade_mask, reason) and the leg-return series up to
each anchor (seat seeding). Also exports the F10 s2027 202609 fold in the production numpy format (mutation control only, never deployed).
Read-only on the build artifacts; every source sha recorded."""
import os, sys, json, hashlib
import numpy as np
W = "/dev/shm/news_2026-09-23"; A0 = 1789646400; ANCH = [A0 + 14400 * k for k in range(10)]


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


def export_np(mp, out):
    import torch
    ck = torch.load(mp, map_location="cpu", weights_only=False); sd = ck["state_dict"]
    Wt = {"w0": sd["f.0.weight"].numpy(), "b0": sd["f.0.bias"].numpy(), "w1": sd["f.3.weight"].numpy(), "b1": sd["f.3.bias"].numpy(),
          "w2": sd["f.6.weight"].numpy(), "b2": sd["f.6.bias"].numpy()}
    np.savez(out, **{k: v.astype(np.float32) for k, v in Wt.items()}, mu=ck["mu"].cpu().numpy().astype(np.float32), sd_=ck["sd"].cpu().numpy().astype(np.float32),
             alpha=np.float32(float((.02 + .88 * torch.sigmoid(sd["a"])).item())), n_cols=np.int64(171), trained_through=np.int64(0))


def main():
    src = {k: f"{W}/{p}" for k, p in (("features", "work/NEWS_FEATURES.npz"), ("king_oof", "work/king/KING_OOF.npz"), ("f10_oof_s42", "work/f10_s42/F10_OOF.npz"),
                                       ("f10_oof_s2027", "work/f10_s2027/F10_OOF.npz"), ("legs", "work/legs.npz"), ("combo_s42", "work/combo_s42/scaled_diagnostic.npz"))}
    F = np.load(src["features"]); K = np.load(src["king_oof"]); G = np.load(src["f10_oof_s42"]); G2 = np.load(src["f10_oof_s2027"]); L = np.load(src["legs"]); C = np.load(src["combo_s42"])
    sys.path.insert(0, f"{W}/devices")
    from book_universe import align, PATH as UP, SHA as US
    assert sha(UP) == US; U = np.load(UP)
    mk = np.load("/workspace/axis_0919/x0918r/masks/member_mask_tradable_AND_live_W24H_cachegrid.npz"); crypto = np.load(f"{W}/receipts/P1_members_2025H2on.npz")["crypto"]
    a = F["anchors"].astype(np.int64); off = F["off"]; ca = C["E_ts"].astype(np.int64); out = {}
    LR = L["LR"]; ready = L["ready"]
    for A in ANCH:
        i = int(np.searchsorted(a, A)); assert a[i] == A; sl = slice(off[i], off[i + 1]); m = F["m"][sl].astype(np.int64)
        out[f"m_{A}"] = m
        for k in ("X78", "X82", "X89", "fe_v", "fn_v", "rev24", "qvm"): out[f"{k}_{A}"] = F[k][sl]
        out[f"base_val_{A}"] = F["base_val"][i]
        out[f"king_oof_{A}"] = K["P"][i, m].astype(np.float64); out[f"f10_oof_{A}"] = G["P"][i, m].astype(np.float64); out[f"f10_oof_s2027_{A}"] = G2["P"][i, m].astype(np.float64)
        for k in ("KZ", "Z24", "ZFD", "RN8", "QV"): out[f"{k}_{A}"] = L[k][i, m].astype(np.float64)
        out[f"WL_{A}"] = L["WL"][i].astype(np.float64); out[f"ready_{A}"] = bool(ready[i])
        j = int(np.searchsorted(ca, A)); assert ca[j] == A
        for k in ("kc", "fc", "raw", "weights"): out[f"{k}_{A}"] = C[k][j]
        out[f"kc_prev_{A}"] = C["kc"][j - 1]; out[f"fc_prev_{A}"] = C["fc"][j - 1]
        out[f"trade_mask_{A}"] = bool(C["trade_mask"][j]); out[f"reason_{A}"] = str(C["reason"][j])
        out[f"book_legal_{A}"] = align(np.array([A]), F["symbols"], U)[0] & mk["mask"][int(np.searchsorted(mk["ts"], A))] & crypto
        # leg-return series the producer would hold AFTER finishing A (values appended at anchors <= A, i.e. LR rows k with anchor[k] <= A-4h)
        keep = np.flatnonzero((a <= A - 14400) & np.isfinite(LR[:, 0]))
        out[f"LR_upto_{A}"] = LR[keep]
    p = f"{W}/work/NEWS_ACCEPT_ROWS.npz"; np.savez(p, anchors=np.array(ANCH), symbols=F["symbols"], **out)
    mp27 = f"{W}/work/f10_s2027/202609/model.pt"; fr27 = json.load(open(f"{W}/work/f10_s2027/202609/FOLD_RECEIPT.json")); assert sha(mp27) == fr27["model_sha256"]
    e27 = f"{W}/work/f10_live_s2027_np_MUTATION_ONLY.npz"; export_np(mp27, e27)
    json.dump({"sources": {k: {"path": v, "sha256": sha(v)} for k, v in src.items()}, "output": p, "sha256": sha(p),
               "mutation_f10_s2027_export": {"path": e27, "sha256": sha(e27), "from_model_pt": fr27["model_sha256"], "use": "mutation control only; never deployed"}},
              open(f"{W}/receipts/P5_ACCEPT_ROWS.json", "w"), indent=1)
    print("EXTRACTED", p, sha(p), e27, sha(e27))


if __name__ == "__main__":
    main()
