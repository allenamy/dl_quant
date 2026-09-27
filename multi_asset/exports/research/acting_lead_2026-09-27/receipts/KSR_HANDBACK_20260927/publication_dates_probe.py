import numpy as np,hashlib,json,datetime,pathlib
pins={'/workspace/ksr_2026-09-27/targets_stats/KSR_S0_m0_s42.npz': '566f0d7b5cada7ff2559e9594a7f6d2e60d899349fc6be5bd2e280ca8bebb2c8', '/workspace/ksr_2026-09-27/targets_stats/KSR_COMP_ONLY_m0_s42.npz': 'e50f7aedbfacee766ba36e169b99e83aa83b60746e12c9a927bf0e6aa853727c', '/workspace/ksr_2026-09-27/targets_stats/KSR_SEAT_ONLY_m0_s42.npz': '9b4b3257b1e3f7312ca20e7aeea3444d6ae0d30ccfe488db5553d2cfc200164b', '/workspace/ksr_2026-09-27/targets_stats/KSR_S1_m0_s42.npz': '9ad4cb2bcc7733dd1545c424d1452d356da812347cef98e7ae198aff03ca4ab7', '/workspace/ksr_2026-09-27/targets_stats/KSR_S0_m0_s2027.npz': 'a35697b26af5a4b47381429c7a0509f1677bf8566db31aa3202dd84531272351', '/workspace/ksr_2026-09-27/targets_stats/KSR_COMP_ONLY_m0_s2027.npz': '0a83c2dfe44efa4d8d38aeda4baad9d04df598da9014297d0fda05e628f7631a', '/workspace/ksr_2026-09-27/targets_stats/KSR_SEAT_ONLY_m0_s2027.npz': 'e2a9ce5768131a125c3dc8525fb9879467b7486caf568aaf776bebfcd8f18877', '/workspace/ksr_2026-09-27/targets_stats/KSR_S1_m0_s2027.npz': 'da4f2c5ece9722af91124243bb4a8b591f019156e8dc5ef71ca7001acaf22a16'}
out={}
for p,h in pins.items():
 assert hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()==h
 with np.load(p,allow_pickle=False) as z:
  a=z['anchors'];k=z['scaled_kind'];m=(a>=1735689600)&(a<1738368000)
  idx=np.flatnonzero(m&(k>0));out[pathlib.Path(p).name]=[{'utc':datetime.datetime.fromtimestamp(int(a[i]),datetime.timezone.utc).isoformat(),'kind':int(k[i]),'encoded_target_gross':float(z['gross'][i])} for i in idx]
print(json.dumps(out))
