import numpy as np
for p in ["/workspace/data/wide_fea_v1_meta.npz","/workspace/data/wide_panel_4h_v1.npz","/workspace/data/dlnative_5m_wide829_f16.npz"]:
    z=np.load(p,allow_pickle=True,mmap_mode='r')
    print("=== ",p)
    for k in z.files:
        try:
            a=z[k]
            print("  ",k,getattr(a,'shape',None),getattr(a,'dtype',None))
        except Exception as e:
            print("  ",k,"ERR",e)
    z.close()
a=np.load("/workspace/exports_train/slow_lgbm_pred.npy",mmap_mode='r')
print("=== slow_lgbm_pred",a.shape,a.dtype)
