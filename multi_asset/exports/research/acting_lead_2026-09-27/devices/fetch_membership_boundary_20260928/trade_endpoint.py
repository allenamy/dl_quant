"""Separate finite zero-activity bars from bars with actual trades; same frozen eight anchors."""
import hashlib,json,sys,time
from pathlib import Path
import numpy as np
from probe import ANCHORS,file_sha,read_npz,sha

def main(root):
    root=Path(root);r=json.loads((root/'RESULT.json').read_text());wr=Path('/dev/shm/recent_rolling_inputs_20260928')
    for p,h in r['inputs'].items():
        if file_sha(p)!=h:raise ValueError('changed_research_input:'+p)
    ax=read_npz(wr/'axes.npz');sy=ax['symbols'].tolist();j=sy.index('STGUSDT');ci=ax['crypto_cols'].tolist().index(j)
    C=np.load(wr/'cache_crypto.npy',mmap_mode='r');ts=ax['ts'];rr=[]
    for a0 in ANCHORS:
        a=int(a0);d=read_npz(root/f'ACTUAL_{a}.npz');i=int(np.searchsorted(ts,a));start=max(0,i-2015)
        tt=ts[start:i+1];cc=C[start:i+1,ci];xx=d['cd'][:,j]
        good=np.isfinite(cc[:,4])&(cc[:,4]>0);old=np.isfinite(xx[:,4])&(xx[:,4]>0)
        last=int(tt[good][-1]) if good.any() else None;live_last=int(d['ts'][old][-1]) if old.any() else None
        post=tt>last if last is not None else np.zeros(len(tt),bool)
        finite_q=np.isfinite(cc[:,3]);zero_activity=np.isfinite(cc[:,4])&(cc[:,4]==0)&finite_q&(cc[:,3]==0)
        rr.append({'anchor':a,'research_last_traded_bar':last,'actual_last_traded_bar':live_last,
                   'research_bars_after_last_trade':int(post.sum()),'research_zero_activity_bars_after_last_trade':int((post&zero_activity).sum()),
                   'research_nan_trade_count_after_last_trade':int((post&~np.isfinite(cc[:,4])).sum()),
                   'research_W24H_contains_trade':bool(np.any(good&(tt>a-86400))),
                   'actual_W24H_contains_trade':bool(np.any(old&(d['ts']>a-86400)))})
    out={'scope':'TRADING_ACTIVITY_DIAGNOSTIC_NOT_VENUE_STATUS_CERTIFICATION','rows':rr,'utc':time.strftime('%FT%TZ',time.gmtime()),'source_sha256':sha(Path(__file__).read_bytes()),
         'result_sha256':sha((root/'RESULT.json').read_bytes()),'inputs':r['inputs'],'limits':['Zero-activity public bars do not prove venue TRADING status','No exchange API or external historical status inquiry','Finite quote-volume row is not proof of a trade']}
    (root/'TRADE_ENDPOINT.json').write_text(json.dumps(out,indent=2,allow_nan=False)+'\n');print(json.dumps(out,indent=2))
if __name__=='__main__':main(sys.argv[1])
