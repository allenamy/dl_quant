"""导出 fold_4 训练口径的 mu/sd — 走训练器【同一条代码路径】(import 同模块调用 set_fold),
不手写第二遍(duplication-without-assertion 家规)。mu/sd 只依赖面板+折切分, 与臂无关。"""
import sys
import numpy as np

ROOT = "/mnt/storage/private/work_hsy/quant_research_multi_asset"
sys.path.insert(0, ROOT)
from multi_asset.data.wide_panel_dataset import WidePanelData          # noqa: E402
sys.path.insert(0, f"{ROOT}/multi_asset/train")
import train_wide_harness as TW                                        # noqa: E402

data = WidePanelData(
    target_horizon=24,
    path=f"{ROOT}/multi_asset/exports/wide_dl_full_corrfund_causal_0731.npz")
folds = TW.year_folds(data, embargo_days=8)
f4 = folds[4]
print(f"fold_4 year={f4['year']}  n_train_days={len(f4['tr'])}")
data.set_fold(f4["tr"])
np.savez("/tmp/norm_stats_fold4.npz", mu=data.mu, sd=data.sd)
print(f"mu[:4]={data.mu[:4]}  sd[:4]={data.sd[:4]}")
print("saved /tmp/norm_stats_fold4.npz")
