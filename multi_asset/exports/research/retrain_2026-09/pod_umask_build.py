"""宇宙臂掩码构建 @pod(PREREG addendum §B): U0=现役450 / U1=上市>=30d / U2=>=60d, splice 网格。"""
import json
import numpy as np
PW = np.load("/workspace/data/wide_panel_4h_v3splice.npz", allow_pickle=True)
ts = PW["ts"].astype(np.int64); syms = [str(s) for s in PW["symbols"]]
Z = np.load("/workspace/data/dlnative_5m_wide829_f16_ext.npz", allow_pickle=True)
cts = Z["ts"].astype(np.int64); fin = np.isfinite(Z["data"][:, :, 0])
first = np.argmax(fin, axis=0); has = fin.any(axis=0)
start = np.where(has, cts[np.clip(first, 0, len(cts) - 1)], 2**62)
live450 = set(json.load(open("/workspace/live_pins.json"))["symbols_live"])
m450 = np.array([s in live450 for s in syms])
NW = len(syms)
age_d = (ts[:, None] - start[None, :]) / 86400.0
np.savez_compressed("/workspace/umask_U0.npz", ts=ts, symbols=np.array(syms), mask=np.tile(m450, (len(ts), 1)))
np.savez_compressed("/workspace/umask_U1.npz", ts=ts, symbols=np.array(syms), mask=age_d >= 30)
np.savez_compressed("/workspace/umask_U2.npz", ts=ts, symbols=np.array(syms), mask=age_d >= 60)
print(f"UMASK_DONE U0 {m450.sum()}名 U1末锚 {(age_d[-1]>=30).sum()} U2末锚 {(age_d[-1]>=60).sum()}", flush=True)
