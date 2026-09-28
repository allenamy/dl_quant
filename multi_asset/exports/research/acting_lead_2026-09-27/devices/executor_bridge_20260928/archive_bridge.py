"""Archive named completed bridge artifacts, never source data or live trees."""
from pathlib import Path
import sys,json,hashlib,zipfile

def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()

def main(root,source):
 r=Path(root);s=Path(source)
 assert r.resolve()==Path('/dev/shm/executor_bridge_20260928')
 assert s.resolve()==Path('/dev/shm/executor_bridge_20260928_sources')
 t=json.loads((r/'TERMINAL.json').read_text());v=json.loads((r/'RESULT.json').read_text());q=json.loads((r/'INDEPENDENT.json').read_text())
 assert t['rc']==0 and t['result_sha256']==sha(r/'RESULT.json')==q['result_sha256']
 assert q['status']=='INDEPENDENT_ARITHMETIC_IDENTITY_PASS'
 for paths in v['paths'].values():
  for x in paths.values():assert sha(x['path'])==x['sha256']
 files={}
 for p in list(r.rglob('*'))+list(s.rglob('*'))+[Path(str(r)+'.run.log'),Path(str(r)+'.LAUNCH.json')]:
  if p.is_symlink():raise ValueError('archive refuses symlink '+str(p))
  if p.is_file():files[str(p)]={'sha256':sha(p),'bytes':p.stat().st_size}
 assert sum(x['bytes'] for x in files.values())<2**30
 with zipfile.ZipFile(sys.stdout.buffer,'w',zipfile.ZIP_DEFLATED,compresslevel=1) as z:
  for p,x in sorted(files.items()):
   z.write(p,p.lstrip('/'));assert sha(p)==x['sha256']
  z.writestr('MANIFEST.json',json.dumps(files,indent=2))

if __name__=='__main__':main(*sys.argv[1:])
