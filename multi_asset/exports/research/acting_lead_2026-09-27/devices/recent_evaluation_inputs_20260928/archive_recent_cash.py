"""Stream a bounded cash evidence ZIP to stdout; never copy shared feature/price files."""
import hashlib,json,sys,zipfile
from pathlib import Path
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def main(root):
 r=Path(root);t=json.loads((r/'TERMINAL.json').read_text());v=json.loads((r/'RESULT.json').read_text())
 assert t['rc']==0 and t['result_sha256']==sha(r/'RESULT.json')
 assert json.loads((r/'INDEPENDENT_CHECK.json').read_text())['status']=='PASS'
 e=json.loads((r/'ECONOMIC.json').read_text());files={Path(p):h for p,h in e['inputs'].items()}
 parent=next(p for p in files if p.name=='RESULT.json');pr=json.loads(parent.read_text())
 for c in pr['configs'].values():files[Path(c['path'])]=c['sha256']
 for d in (r,parent.parent,Path(__file__).parent):
  for p in d.iterdir():
   if p.is_file() and not p.is_symlink() and p.suffix in ('.json','.npz','.py','.sh'):files[p]=sha(p)
 for p,h in files.items():assert p.is_file() and not p.is_symlink() and sha(p)==h,str(p)
 assert sum(p.stat().st_size for p in files)<2**30,'archive one-GiB budget'
 manifest={str(p):{'sha256':h,'bytes':p.stat().st_size} for p,h in sorted(files.items())}
 with zipfile.ZipFile(sys.stdout.buffer,'w',zipfile.ZIP_DEFLATED,compresslevel=1) as z:
  for p,h in sorted(files.items()):
   z.write(p,str(p).lstrip('/'));assert sha(p)==h,'source changed '+str(p)
  z.writestr('MANIFEST.json',json.dumps(manifest,indent=2))
if __name__=='__main__':main(*sys.argv[1:])
