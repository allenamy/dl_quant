"""Stream completed named outputs/sources and parent identities; never mutate originals."""
import hashlib,json,sys,zipfile
from pathlib import Path

def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()

def main():
    root=Path('/dev/shm/fetch_feature_alignment_20260928')
    source=Path(str(root)+'_sources');parent=Path(str(root)+'_inputs')
    result=json.loads((root/'RESULT.json').read_text())
    terminal=json.loads((root/'TERMINAL.json').read_text())
    verify=json.loads((root/'VERIFY.json').read_text())
    assert terminal['rc']==0 and terminal['result_sha256']==sha(root/'RESULT.json')==verify['result_sha256']
    assert verify['status']=='VERIFIED_SAVED_ARRAYS_NOT_PNL'
    for name,h in result['outputs'].items():assert sha(root/name)==h
    files={}
    paths=list(root.rglob('*'))+list(source.glob('*.py'))+[Path(str(root)+'.run.log')]
    paths += [parent/name for name in ('RESULT.json','CONTINUOUS.json','CONTINUOUS_STATES.npz')]
    for p in paths:
        if p.is_symlink():raise ValueError('symlink_refused:'+str(p))
        if p.is_file():files[str(p)]={'sha256':sha(p),'bytes':p.stat().st_size}
    assert sum(x['bytes'] for x in files.values())<100*2**20
    with zipfile.ZipFile(sys.stdout.buffer,'w',zipfile.ZIP_DEFLATED,compresslevel=1) as z:
        for p,info in sorted(files.items()):
            z.write(p,p.lstrip('/'))
            assert sha(p)==info['sha256']
        z.writestr('MANIFEST.json',json.dumps(files,indent=2))

if __name__=='__main__':main()
