"""E-0904-C 修复备料: 从回放装置(canonpred_s42, 年折外 OOS king)导出三腿 OOS 腿收益序列 → leg_returns_oos_seed.npz(ts, king, rev24, fund), 与 bundle leg_returns.npz 同 schema。只备料, 不部署。"""
import numpy as np, json, hashlib, time
PD="probe_artifacts"; z=np.load(f"{PD}/w10_canonpred_s42.npz",allow_pickle=True); cols=[str(c) for c in z["cols"]]; rec=z["d30_n2_c42_rec"]
ts=rec[:,cols.index("ts")].astype(np.int64); g=lambda k: rec[:,cols.index(k)].astype(np.float64)
out=f"{PD}/leg_returns_oos_seed.npz"; np.savez_compressed(out, ts=ts, king=g("leg_king"), rev24=g("leg_rev24"), fund=g("leg_fund"))
B=np.load(f"{PD}/bundle_leg_returns.npz",allow_pickle=True)
print("OOS seed:", len(ts), time.strftime("%Y-%m-%d",time.gmtime(int(ts[0]))), "->", time.strftime("%Y-%m-%d %HZ",time.gmtime(int(ts[-1]))), "| bundle:", len(B["ts"]), "->", time.strftime("%Y-%m-%d %HZ",time.gmtime(int(B["ts"][-1]))))
k=g("leg_king")[-900:]; r=g("leg_rev24")[-900:]; f=g("leg_fund")[-900:]; shp=np.maximum([k.mean()/k.std(), r.mean()/r.std(), f.mean()/f.std()],0); w=shp/shp.sum(); w=w*np.array([1,0,1]); w=w/w.sum()
print(f"末 900 锚(至 08-15)OOS 席位 king/fund = {w[0]:.3f}/{w[2]:.3f} | sha {hashlib.sha256(open(out,'rb').read()).hexdigest()[:12]}")
print("SEED_BUILT")
