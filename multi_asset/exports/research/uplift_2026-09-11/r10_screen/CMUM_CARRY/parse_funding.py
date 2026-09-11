"""CMUM_CARRY STEP1 parser. Reads the bulk-archive monthly fundingRate zips pulled from
data.binance.vision (static CDN; NOT fapi/api) and writes one npz of per-symbol funding series.
NO network. NO live touch. env -i clean."""
import os,sys,io,zipfile,glob,json
import numpy as np
ENV_WHITELIST={"LC_CTYPE","LANG","PATH","PWD","SHLVL","_","__CF_USER_TEXT_ENCODING","HOME","TMPDIR","CPATH","LIBRARY_PATH","MANPATH","SDKROOT"}
assert set(os.environ)<=ENV_WHITELIST, sorted(set(os.environ)-ENV_WHITELIST)
for _v in ("CAL","WRULE","LOOK","MEMBERS_TOPN","UMASK_SCOPE","UMASK_NPZ","COSTB_JSON","SLOW_NPY","LEGS","PHI","FTRIM","FEMAT_NPZ","OUT_TAG","TRADE_TOPN","KMOD_F10","KMOD_AGREE","KTAIL","EXPORT_PANEL","EMA_STATE_JSON","JUDGE_HC","PANEL_IN","JUDGE_REQUIRE_W"): assert _v not in os.environ, _v
W=os.path.dirname(os.path.abspath(__file__))
def read_dir(d):
    out={}
    for z in sorted(glob.glob(os.path.join(d,"*.zip"))):
        base=os.path.basename(z)[:-4]
        sym,mon=base.rsplit("-",2)[0], base[-7:]
        try:
            zf=zipfile.ZipFile(z)
        except Exception as e:
            print("BADZIP",z,e); continue
        n=zf.namelist()[0]
        txt=zf.read(n).decode()
        rows=[]
        for ln in txt.strip().split("\n"):
            if ln.startswith("calc_time"): continue
            p=ln.split(",")
            if len(p)<3: continue
            rows.append((int(p[0]),float(p[1]),float(p[2])))
        out.setdefault(sym,[]).extend(rows)
    for s in out:
        a=np.array(sorted(set(out[s])),dtype=np.float64)
        out[s]=a
    return out
cm=read_dir(os.path.join(W,"dl","cm"))
um=read_dir(os.path.join(W,"dl","um"))
print("cm syms",len(cm),"um syms",len(um))
np.savez_compressed(os.path.join(W,"funding_raw.npz"),
    cm_syms=np.array(sorted(cm)),um_syms=np.array(sorted(um)),
    **{"CM_"+s:cm[s] for s in cm},**{"UM_"+s:um[s] for s in um})
summ={}
for s,a in cm.items():
    summ["CM:"+s]=dict(n=len(a),t0=int(a[0,0]),t1=int(a[-1,0]),intervals=sorted(set(a[:,1].tolist())))
for s,a in um.items():
    summ["UM:"+s]=dict(n=len(a),t0=int(a[0,0]),t1=int(a[-1,0]),intervals=sorted(set(a[:,1].tolist())))
json.dump(summ,open(os.path.join(W,"funding_summary.json"),"w"),indent=1)
print("env_seen",sorted(os.environ))
