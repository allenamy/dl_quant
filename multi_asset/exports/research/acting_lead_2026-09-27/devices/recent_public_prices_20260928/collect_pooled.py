"""Existing fixed-population collector with a pinned persistent public transport."""
from pathlib import Path
import json,sys,datetime
import collect_label_proofs as C
import public_transport as P
import download as D

def main(path):
 c=json.loads(Path(path).read_text())
 for name,h in c['additional_sources'].items():
  if D.digest(Path(__file__).with_name(name).read_bytes())!=h:raise ValueError('transport/source identity')
 D.read_url=P.reader.read
 C.main(path)
if __name__=='__main__':
 try:main(sys.argv[1])
 except BaseException as e:
  c=json.loads(Path(sys.argv[1]).read_text());r=Path(c['root']);r.mkdir(exist_ok=True)
  if not (r/'TERMINAL.json').exists():D.write(r/'TERMINAL.json',(json.dumps({'rc':1,'status':'FAILED','error':repr(e),'utc':datetime.datetime.now(datetime.timezone.utc).isoformat()})+'\n').encode())
  raise
