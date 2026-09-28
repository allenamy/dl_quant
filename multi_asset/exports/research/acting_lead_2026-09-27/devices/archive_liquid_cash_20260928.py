"""Archive completed LQ evidence without duplicating immutable U controls."""
from pathlib import Path
import hashlib,json,zipfile,sys
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(4<<20),b''):h.update(b)
 return h.hexdigest()
def run(root,out):
 root=Path(root);out=Path(out);t=json.loads((root/'TERMINAL.json').read_text())
 if t['rc']!=0 or not (root/'receipts/BOOK_DECISION.json').is_file():raise ValueError('not complete')
 small={};large={};external={}
 def add(p,name):
  if p.is_file():
   if p.is_symlink():
    external[name]={'source':str(p),'resolved':str(p.resolve()),'sha256':sha(p),'bytes':p.stat().st_size}
    return
   d=large if p.suffix in ('.npz','.pt') else small
   if name in d:raise ValueError('duplicate archive name')
   d[name]=p
 for name in ('logs','steps','processes','receipts','models'):
  for p in (root/name).rglob('*'):add(p,str(p.relative_to(root)))
 for p in root.glob('*.json'):add(p,p.name)
 for p in root.with_name(root.name+'_sources').glob('*'):add(p,'sources/'+p.name)
 for kind in ('LQ',):
  for seed in (42,2027):
   logical=root/f'cells/{kind}_s{seed}';actual=logical.resolve()
   for p in actual.rglob('*'):add(p,f'cells/{kind}_s{seed}/'+str(p.relative_to(actual)))
 if sum(Path(n).name.startswith('PATH_') for n in large)!=64:raise ValueError('cash population')
 if sum(p.stat().st_size for p in large.values())>3*2**30:raise ValueError('archive unexpectedly exceeds 3GiB; inspect duplicate inputs')
 result={}
 for name,files in [('small',small),('large',large)]:
  p=Path(str(out)+'_'+name+'.zip');manifest={}
  with zipfile.ZipFile(p,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=1) as z:
   for n,f in sorted(files.items()):
    h=sha(f);size=f.stat().st_size;z.write(f,n)
    if f.stat().st_size!=size or sha(f)!=h:raise ValueError('source changed during archive')
    manifest[n]={'sha256':h,'bytes':size}
   z.writestr('ARCHIVE_MANIFEST.json',json.dumps(manifest,indent=2)+'\n')
   if name=='small':z.writestr('EXTERNAL_INPUTS.json',json.dumps(external,indent=2)+'\n')
  result[name]={'path':str(p),'sha256':sha(p),'bytes':p.stat().st_size,'members':len(manifest)}
 result['status']='ARCHIVED_ON_POD_REQUIRES_LOCAL_VERIFICATION'
 result['external_symlink_inputs_retained_in_place']=external
 Path(str(out)+'_RECEIPT.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
if __name__=='__main__':run(*sys.argv[1:])
