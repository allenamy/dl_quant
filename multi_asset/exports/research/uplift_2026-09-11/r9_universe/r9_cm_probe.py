# ENV WHITELIST (E-0826-D) = EMPTY SET.
import io,json,zipfile,urllib.request,time,csv
import numpy as np
BASE="https://data.binance.vision/data/futures"
SY=["BTC","ETH","SOL","XRP","DOGE","BNB","ADA","LINK","AVAX","LTC","NEAR","SUI","WLD","APT","TRX","UNI"]
MON=["2025-09","2025-10","2025-11","2025-12","2026-01","2026-02","2026-03","2026-04","2026-05","2026-06","2026-07"]
def get(url):
    try:
        with urllib.request.urlopen(url,timeout=25) as r: b=r.read()
    except Exception as e: return None
    try:
        zf=zipfile.ZipFile(io.BytesIO(b)); n=zf.namelist()[0]
        return zf.read(n).decode()
    except Exception: return None
def parse(txt):
    out=[]
    for row in csv.reader(io.StringIO(txt)):
        if not row or not row[0].strip().lstrip('-').isdigit(): continue
        try: out.append((int(row[0]), float(row[-1]) if len(row)>=3 else float(row[1])))
        except Exception: pass
    return out
def parse_fr(txt):
    # columns: calc_time, funding_interval_hours, last_funding_rate
    out=[]
    for row in csv.reader(io.StringIO(txt)):
        if not row or not row[0].strip().lstrip('-').isdigit(): continue
        try: out.append((int(row[0]), float(row[1]), float(row[2])))
        except Exception: pass
    return out
res={}
nreq=0
for s in SY:
    cm={}; um={}
    for m in MON:
        for fam,sym,store in (("cm",f"{s}USD_PERP",cm),("um",f"{s}USDT",um)):
            u=f"{BASE}/{fam}/monthly/fundingRate/{sym}/{sym}-fundingRate-{m}.zip"
            t=get(u); nreq+=1; time.sleep(0.3)
            if t is None: continue
            for ct,ih,fr in parse_fr(t): store[ct]=(ih,fr)
    common=sorted(set(cm)&set(um))
    if len(common)<200: res[s]={"n_common":len(common),"note":"insufficient"}; continue
    # normalise to per-hour rate (PREREG_crossvenue_2026-08-09 §1 rule: divide by measured interval)
    ch=np.array([cm[t][1]/max(cm[t][0],1e-9) for t in common])
    uh=np.array([um[t][1]/max(um[t][0],1e-9) for t in common])
    d=ch-uh
    res[s]={"n_common":len(common),
            "t0":int(common[0]),"t1":int(common[-1]),
            "mean_cm_per_h_bps":float(ch.mean()*1e4),"mean_um_per_h_bps":float(uh.mean()*1e4),
            "mean_spread_per_h_bps":float(d.mean()*1e4),"std_spread_per_h_bps":float(d.std()*1e4),
            "corr_cm_um":float(np.corrcoef(ch,uh)[0,1]),
            "frac_spread_same_sign_as_um":float(np.mean(np.sign(d)==np.sign(uh)))}
res["_nreq"]=nreq
print(json.dumps(res,indent=1))
open("/workspace/r9_cm_probe.json","w").write(json.dumps(res,indent=1))
