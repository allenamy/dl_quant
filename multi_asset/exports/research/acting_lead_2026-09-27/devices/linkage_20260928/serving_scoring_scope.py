"""Post-diagnostic scope check: do not confuse market population with model members."""
from pathlib import Path
import json,hashlib,sys,time
import numpy as np

def h(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

root=Path(sys.argv[1]);p=Path('/dev/shm/recent_king_features_20260928/KING_FEATURES_AND_MEMBERS.npz')
assert h(p)=='0a8f4bb1f9a01d5c6ecd7047e4f63a72fe627809186dbb176b9d202ff36b6855'
R=json.loads((root/'RESULT.json').read_text());assert h(root/'COMPARISON.npz')==R['outputs']['COMPARISON.npz']
with np.load(p) as z:k={n:z[n] for n in ('anchors','symbols','off','m')}
with np.load(root/'COMPARISON.npz') as z:a={n:z[n] for n in z.files}
assert np.array_equal(k['symbols'],a['symbols']);ix=np.flatnonzero(k['anchors']==R['day']);assert len(ix)==1
i=int(ix[0]);m=k['m'][k['off'][i]:k['off'][i+1]];scope=np.zeros(len(a['symbols']),bool);scope[m]=True
assert scope.sum()==len(m)==400 and np.all(a['scope'][scope])
columns={}
for base,names in [('own',['own_residual4h','own_residual24h']),('X',['peer_residual4h','peer_residual24h','own_minus_peer24h','peer_up_breadth'])]:
 for j,n in enumerate(names):
  d=np.abs(a[base+'_full'][:,j]-a[base+'_fetch'][:,j]);assert np.isfinite(d[scope]).all()
  worst=int(m[np.argmax(d[m])]);columns[n]={'median':float(np.median(d[scope])),'p95':float(np.quantile(d[scope],.95)),
     'max':float(d[worst]),'max_symbol':str(a['symbols'][worst])}
output={'utc':time.strftime('%FT%TZ',time.gmtime()),'source_sha256':h(__file__),'member_input':str(p),'member_sha256':h(p),
        'original_result_sha256':h(root/'RESULT.json'),'anchor':R['day'],'members':len(m),'USDCUSDT_is_member':bool(scope[np.flatnonzero(a['symbols']=='USDCUSDT')[0]]),
        'absolute_differences':columns,'scope':'Post-diagnostic refinement to fixed NC research scoring members; not current production target state or a redefinition of the original 519-name diagnostic'}
(root/'SCORING_SCOPE.json').write_text(json.dumps(output,indent=2,allow_nan=False)+'\n');print(json.dumps(output))
