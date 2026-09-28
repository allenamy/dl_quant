"""Archive a completed fixed C5 result; keep original source and parent artifacts."""
from pathlib import Path
import json,sys,zipfile
from run import sha

def main():
    root=Path('/dev/shm/gap_history_propagation_20260928');source=Path('/dev/shm/fetch_feature_alignment_20260928_sources')
    result=json.loads((root/'RESULT.json').read_text());term=json.loads((root/'TERMINAL.json').read_text());v=json.loads((root/'VERIFY.json').read_text())
    assert term['rc']==0 and term['result_sha256']==sha(root/'RESULT.json')==v['result_sha256']
    assert v['status']=='SAVED_ARRAYS_VERIFIED'
    for name,h in result['outputs'].items():assert sha(root/name)==h
    paths=list(root.rglob('*'))+[source/n for n in ('run.py','gap_history.py','verify_gap.py','archive_gap.py','test_gap_history.py','test_run.py')]
    paths += [Path(str(root)+'.run.log'),Path(str(root)+'.tests.log')]
    files={}
    for p in paths:
        if p.is_symlink():raise ValueError('symlink_refused')
        if p.is_file():files[str(p)]={'sha256':sha(p),'bytes':p.stat().st_size}
    assert sum(v['bytes'] for v in files.values())<100*2**20
    with zipfile.ZipFile(sys.stdout.buffer,'w',zipfile.ZIP_DEFLATED,compresslevel=1) as z:
        for p,info in sorted(files.items()):
            z.write(p,p.lstrip('/'));assert sha(p)==info['sha256']
        z.writestr('MANIFEST.json',json.dumps(files,indent=2))

if __name__=='__main__':main()
