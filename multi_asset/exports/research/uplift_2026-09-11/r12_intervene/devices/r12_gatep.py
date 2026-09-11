"""GATE P: interventions OFF must be BITWISE identical to the archived R9_A1x_ext_s42."""
import numpy as np, json, hashlib, os
U="/workspace/uplift_2026-09-11"; R=f"{U}/r12_intervene"
A=np.load(f"{U}/r9/dev_ext/probe_artifacts/w10_ablation_series_R9_A1x_ext_s42.npz",allow_pickle=True)
B=np.load(f"{R}/dev_ext/probe_artifacts/w10_ablation_series_R12_GATEP_s42.npz",allow_pickle=True)
out={}
for nm in ("d30_n2_c42","S0"):
    ra,rb=np.asarray(A[nm+"_rec"]),np.asarray(B[nm+"_rec"])
    wa,wb=np.asarray(A[nm+"_W"]),np.asarray(B[nm+"_W"])
    out[nm]={"rec_shape":[list(ra.shape),list(rb.shape)],
             "rec_maxabs":float(np.max(np.abs(ra-rb))) if ra.shape==rb.shape else None,
             "rec_bitwise":bool(np.array_equal(ra,rb)),
             "W_maxabs":float(np.max(np.abs(wa-wb))) if wa.shape==wb.shape else None,
             "W_bitwise":bool(np.array_equal(wa,wb)),
             "rec_bytes_sha16":[hashlib.sha256(ra.tobytes()).hexdigest()[:16],hashlib.sha256(rb.tobytes()).hexdigest()[:16]]}
out["cols_equal"]=bool(np.array_equal(A["cols"],B["cols"]))
out["symbols_equal"]=bool(np.array_equal(A["symbols"],B["symbols"]))
cfg=json.loads(str(B["config_json"]))
out["r12_cfg"]={k:cfg.get(k) for k in ("CEM_Q","CEM_MODE","BYP_STATE","BYP_Q","BYP_A","R12_TRAIL","R12_MINH")}
out["R12_block"]=cfg.get("R12")
print(json.dumps(out,indent=1))
assert out["d30_n2_c42"]["rec_bitwise"] and out["d30_n2_c42"]["W_bitwise"], "GATE P FAILED"
assert out["S0"]["rec_bitwise"] and out["S0"]["W_bitwise"], "GATE P FAILED (S0)"
json.dump(out,open(f"{R}/out/GATE_P.json","w"),indent=1)
print("GATE_P PASS")
