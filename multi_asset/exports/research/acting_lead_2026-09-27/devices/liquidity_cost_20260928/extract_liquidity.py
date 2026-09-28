"""Price-free NC qvm extraction; no model/return/arm outcomes read."""
import argparse, hashlib, json
from pathlib import Path
import numpy as np


def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(4<<20),b''):h.update(b)
    return h.hexdigest()


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('source');ap.add_argument('out');a=ap.parse_args()
    p=Path(a.source);out=Path(a.out);out.mkdir(exist_ok=False)
    h0=sha(p);z=np.load(p,allow_pickle=False)
    anchors=z['anchors'];off=z['off'];members=z['m'];qvm=z['qvm'];syms=z['symbols']
    use=np.where((anchors>=1787702400)&(anchors<1789776000))[0]
    counts=off[use+1]-off[use];pieces=[slice(off[i],off[i+1]) for i in use]
    np.savez_compressed(out/'LIQUIDITY.npz',anchors=anchors[use],symbols=syms,
        off=np.r_[0,np.cumsum(counts)],m=np.concatenate([members[s] for s in pieces]),
        qvm=np.concatenate([qvm[s] for s in pieces]))
    if sha(p)!=h0:raise ValueError('source changed during extraction')
    rec={'source':str(p),'source_sha256':h0,'out_sha256':sha(out/'LIQUIDITY.npz'),
         'self_sha256':sha(__file__),'n_anchors':len(use),'first_anchor':int(anchors[use[0]]),
         'last_anchor':int(anchors[use[-1]]),'features':'qvm only; no scores/returns/experiment outcomes'}
    (out/'EXTRACT.json').write_text(json.dumps(rec,indent=2)+'\n');print(json.dumps(rec))
