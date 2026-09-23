import numpy as np, zipfile, json, time
ROOT='/workspace/codex_research/QNT-2026-0907/combo_20260923/corrected_combo_v1d'
R=np.load(f'{ROOT}/market/returns.npz')['R']; OBS=np.load(f'{ROOT}/market/observed.npz')['close']
p='/workspace/axis_0919/x0918r/data/dlnative_5m_wide829_f16_holefix2_x0918r.npz'
zf=zipfile.ZipFile(p); fh=zf.open('data.npy'); ver=np.lib.format.read_magic(fh)
shp,fo,dt=(np.lib.format.read_array_header_1_0(fh) if ver==(1,0) else np.lib.format.read_array_header_2_0(fh))
T,N,C=shp; r16=np.empty((T,N),np.float16); rowb=N*C*2
for r0 in range(0,T,8192):
    k=min(8192,T-r0); buf=fh.read(k*rowb); r16[r0:r0+k]=np.frombuffer(buf,np.float16).reshape(k,N,C)[:,:,0]
assert R.shape==(T,N)
B16=float(np.float16(0.3)); r32=r16.astype(np.float32)
fr=np.isfinite(R); f16=np.isfinite(r32); bound=f16&(np.abs(r32)==np.float32(B16))
both=fr&f16&~bound
eq=(R[both].view(np.uint32)==r32[both].view(np.uint32))
out={"cells":int(T*N),"R_finite":int(fr.sum()),"r16_finite":int(f16.sum()),"bound":int(bound.sum()),
     "both_nonbound":int(both.sum()),"bitwise_equal_nonbound":int(eq.sum()),"differ_nonbound":int((~eq).sum()),
     "R_finite_r16_nan":int((fr&~f16).sum()),"R_nan_r16_finite_nonbound":int((~fr&f16&~bound).sum()),
     "bound_R_finite":int((bound&fr).sum())}
d=np.flatnonzero(~eq)
if len(d):
    ii=np.argwhere(both)[d[:5]]; out["examples"]=[(int(a),int(b),float(R[a,b]),float(r32[a,b])) for a,b in ii]
    out["max_rel_diff"]=float(np.max(np.abs(R[both][~eq]-r32[both][~eq])/np.maximum(np.abs(r32[both][~eq]),1e-30)))
print(json.dumps(out))
