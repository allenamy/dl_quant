"""Stream only named completed panel/screen roots and source files, bounded 1GiB."""
from pathlib import Path
import sys,json,hashlib,zipfile
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def main(roots):
 files={}
 for r in map(Path,roots):
  tp=r/'TERMINAL.json'
  if tp.exists():
   t=json.loads(tp.read_text());v=json.loads((r/'RESULT.json').read_text());assert t['rc']==0 and t['result_sha256']==sha(r/'RESULT.json')
   for n,h in v['outputs'].items():assert sha(r/n)==h
  for p in list(r.iterdir())+[r.with_suffix('.run.log'),r.with_suffix('.LAUNCH.json')]:
   if p.is_file() and not p.is_symlink():files[str(p)]={'sha256':sha(p),'bytes':p.stat().st_size}
 assert sum(v['bytes'] for v in files.values())<2**30
 with zipfile.ZipFile(sys.stdout.buffer,'w',zipfile.ZIP_DEFLATED,compresslevel=1) as z:
  for p,v in sorted(files.items()):
   z.write(p,p.lstrip('/'));assert sha(p)==v['sha256']
  z.writestr('MANIFEST.json',json.dumps(files,indent=2))
if __name__=='__main__':main(sys.argv[1:])
