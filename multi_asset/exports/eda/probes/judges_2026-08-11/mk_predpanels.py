"""Rename-only shim: PanelSource wants keys `king_pred`/`s2_pred`; the certified files use `pred`.

★ NEW GENERATION = 5-fold WALK-FORWARD OOS predictions (team-lead ruling, #31):
    king = wideA_lamorth0_xattn_5yr_corrfund_v1   (S1F, certified)
    s2   = wideA_s2_y24_5yr_corrfund_emb10        (clean s2 @ embargo 10 = deployment caliber)
  NOT the production folds: their predictions over 2022-2026 are IN-SAMPLE, which would put the
  baseline ~18% high and make the guard fire on a healthy model.
"""
import numpy as np, hashlib
SRC = {"/tmp/vs5_pred_s1f_SERVE.npz": ("/tmp/king_pred_newgen.npz", "king_pred"),
       "/tmp/vs5_pred_s2c10_SERVE.npz": ("/tmp/s2_pred_newgen.npz", "s2_pred")}
for src, (dst, key) in SRC.items():
    z = np.load(src)
    p = z["pred"]
    np.savez(dst, **{key: p}, ts=z["ts"])
    h = hashlib.sha256(np.ascontiguousarray(p)).hexdigest()[:16]
    print("%-34s -> %-28s key=%-10s finite=%d  pred_sha=%s"
          % (src.split("/")[-1], dst.split("/")[-1], key, int(np.isfinite(p).sum()), h))
