"""Preserve all conditional cash outputs and demonstrate independent rejection."""
import hashlib,json,subprocess,sys,zipfile
from pathlib import Path

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
root=Path(sys.argv[1]);src=Path(__file__).parent;bad=root/'negative_summary';bad.mkdir(exist_ok=False)
r=json.loads((root/'RESULT.json').read_bytes());r['summary']['base']['compound']['S_mean']+=.01
(bad/'RESULT.json').write_text(json.dumps(r,indent=2)+'\n')
(bad/'TERMINAL.json').write_text(json.dumps({'rc':0,'result_sha256':sha(bad/'RESULT.json')})+'\n')
for p in root.glob('*.npz'):(bad/p.name).symlink_to(p)
p=subprocess.run([sys.executable,str(src/'verify_handoff_cash.py'),str(bad)],capture_output=True,text=True)
if p.returncode==0 or 'numeric_mismatch' not in p.stderr:raise ValueError('negative_did_not_detect_numeric_mutation')
(root/'NEGATIVE.json').write_text(json.dumps({'status':'MUTATED_REAL_SUMMARY_REJECTED','mutation':'S_mean compound +0.01; terminal re-signed; all real paths identical','returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr,'source_sha256':sha(__file__)},indent=2)+'\n')
output=Path(str(root)+'.zip');files=[p for p in root.iterdir() if p.is_file()]+[p for p in src.iterdir() if p.is_file() and p.suffix in ('.py','.json','.log')]+[bad/'RESULT.json',bad/'TERMINAL.json']
members={}
with zipfile.ZipFile(output,'x',compression=zipfile.ZIP_DEFLATED) as z:
 for p in files:
  if p.parent==src:n='sources/'+p.name
  elif p.parent==bad:n='negative/'+p.name
  else:n='outputs/'+p.name
  z.write(p,n);members[n]={'bytes':p.stat().st_size,'sha256':sha(p)}
manifest={'path':str(output),'sha256':sha(output),'bytes':output.stat().st_size,'members':members,'limits':['No shared inputs deleted; all source directories retained','ZIP has outputs and source pins; large price/model ancestors remain at pinned locations']}
Path(str(root)+'.ARCHIVE.json').write_text(json.dumps(manifest,indent=2)+'\n');print(json.dumps({k:v for k,v in manifest.items() if k!='members'}));print('members',len(members))
