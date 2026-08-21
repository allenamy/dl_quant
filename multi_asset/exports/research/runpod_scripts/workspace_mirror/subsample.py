import numpy as np
R=np.load("/workspace/data/wide_dl_rebuilt32.npz",allow_pickle=True)
CH=R["CH"]
rows=np.arange(0,CH.shape[0],97)          # 确定性子采样: 每 97 小时一行
np.savez_compressed("/workspace/data/rb32_sample.npz",CH=CH[rows],rows=rows,
                    ch_names=R["ch_names"])
import os
print("sample:",CH[rows].shape, f"{os.path.getsize('/workspace/data/rb32_sample.npz')/1048576:.1f} MB")
