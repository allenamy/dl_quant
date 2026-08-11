import sys
sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset")
import numpy as np
from multi_asset.data.wide_panel_dataset import WidePanelData
import multi_asset.train.train_wide_harness as TH
MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
FULL = MA + "/exports/wide_dl_full_corrfund_causal_v1.npz"
# training log (s2clean.log): fold0 tr 0..326 va 327..356 te 365..729
for aux in [(1,), (), (1, 4), (4,)]:
    for emb in (8, 10):
        d = WidePanelData(path=FULL, target_horizon=24, aux_horizons=aux)
        f = TH.year_folds(d, embargo_days=emb, val_days=30, year_from=None)[0]
        tr, va = np.asarray(f["tr"]), np.asarray(f["va"])
        print("aux=%-8s emb=%2d | tr %d..%d (n=%d)  va %d..%d | %s"
              % (str(aux), emb, tr.min(), tr.max(), len(tr), va.min(), va.max(),
                 "MATCHES LOG (tr 0..326 va 327..356)"
                 if (tr.min() == 0 and tr.max() == 326 and va.min() == 327 and va.max() == 356)
                 else "no"))
