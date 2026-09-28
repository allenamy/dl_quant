"""Archive completed small continuation roots; verify every output and ZIP member."""
from pathlib import Path
import json,hashlib,zipfile,sys
from funding_overlap import sha

def main(dest,roots):
    dest=Path(dest);manifest={}
    if dest.exists():raise FileExistsError(dest)
    for r in map(Path,roots):
        if (r/'TERMINAL.json').exists():
            t=json.loads((r/'TERMINAL.json').read_text())
            if t.get('rc')==0:
                assert t['result_sha256']==sha(r/'RESULT.json')
                for n,v in json.loads((r/'RESULT.json').read_text()).get('outputs',{}).items():assert sha(r/n)==(v['sha256'] if isinstance(v,dict) else v)
        for p in sorted(r.iterdir()):
            if p.is_file() and not p.is_symlink():manifest[str(p)]={'sha256':sha(p),'bytes':p.stat().st_size}
    with zipfile.ZipFile(dest,'w',zipfile.ZIP_DEFLATED) as z:
        for p in manifest:z.write(p,p.lstrip('/'))
        z.writestr('MANIFEST.json',json.dumps(manifest,indent=2))
    with zipfile.ZipFile(dest) as z:
        for p,v in manifest.items():
            b=z.read(p.lstrip('/'));assert len(b)==v['bytes'] and hashlib.sha256(b).hexdigest()==v['sha256']
    rec={'path':str(dest),'sha256':sha(dest),'bytes':dest.stat().st_size,'members':len(manifest),'all_members_verified':True}
    Path(str(dest)+'.receipt.json').write_text(json.dumps(rec,indent=2)+'\n');print(rec)

if __name__=='__main__':main(sys.argv[1],sys.argv[2:])
