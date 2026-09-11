"""CMUM_CARRY STEP 1: universe count + spread magnitude. First-hand, no network, no live touch."""
import os,json,numpy as np
ENV_WHITELIST={"LC_CTYPE","LANG","PATH","PWD","SHLVL","_","__CF_USER_TEXT_ENCODING","HOME","TMPDIR","CPATH","LIBRARY_PATH","MANPATH","SDKROOT"}
assert set(os.environ)<=ENV_WHITELIST, sorted(set(os.environ)-ENV_WHITELIST)
for _v in ("CAL","WRULE","LOOK","MEMBERS_TOPN","UMASK_SCOPE","UMASK_NPZ","COSTB_JSON","SLOW_NPY","LEGS","PHI","FTRIM","FEMAT_NPZ","OUT_TAG","TRADE_TOPN"): assert _v not in os.environ
W=os.path.dirname(os.path.abspath(__file__))
F=np.load(W+"/funding_raw.npz",allow_pickle=True)
cm_syms=[str(s) for s in F["cm_syms"]]; um_syms=[str(s) for s in F["um_syms"]]
A0=np.load(W+"/pin/A0_PWR230k_s42.npz",allow_pickle=True)
print("A0 keys",list(A0.keys()))
cols=[str(c) for c in A0["cols"]]; rec=A0["rec"]
print("cols",cols); print("rec shape",rec.shape, "W",A0["W"].shape if hasattr(A0["W"],'shape') else A0["W"])
cfg=json.loads(str(A0["config_json"]))
print("config",json.dumps(cfg)[:800])
ts=rec[:,cols.index("ts")].astype(np.int64)
import datetime as dt
print("A0 raw n",len(ts), dt.datetime.utcfromtimestamp(ts[0]), dt.datetime.utcfromtimestamp(ts[-1]))
