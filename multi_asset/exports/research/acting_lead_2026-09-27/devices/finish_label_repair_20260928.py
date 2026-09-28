"""Wait for the bounded experiment, independently verify raw cash and archive once."""
from pathlib import Path
import time,subprocess,json,os,hashlib,traceback,sys,zipfile
H=Path(__file__).resolve().parent
ROOT=Path('/dev/shm/f10_label_repair_20260928_attempt2')
OUT=Path('/dev/shm/f10_label_repair_20260928_finish')
DEADLINE=1790617419  # 2026-09-28T17:43:39Z, original batch budget plus artifact verification

def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def dump(name,x):
 with open(OUT/name,'x') as f:json.dump(x,f,indent=2,allow_nan=False)
def run(name,args,timeout):
 with open(OUT/(name+'.log'),'x') as f:
  p=subprocess.Popen(args,stdout=f,stderr=subprocess.STDOUT,start_new_session=True,env={'PATH':'/usr/bin:/bin','HOME':'/root'})
  dump(name+'_PROCESS.json',{'pid':p.pid,'pgid':os.getpgid(p.pid),'start_ticks':Path(f'/proc/{p.pid}/stat').read_text().split()[21],'argv':args})
  try:rc=p.wait(timeout=timeout)
  except subprocess.TimeoutExpired:
   # Created group only; never select a process by name.
   os.killpg(p.pid,15)
   try:p.wait(timeout=5)
   except subprocess.TimeoutExpired:os.killpg(p.pid,9);p.wait(timeout=5)
   raise
  if rc:raise RuntimeError(name+' rc '+str(rc))
 return {'rc':rc,'log_sha256':sha(OUT/(name+'.log'))}
def main():
 OUT.mkdir(exist_ok=False);src={str(p):sha(p) for p in H.glob('*.py')};dump('SOURCES.json',src)
 while not (ROOT/'TERMINAL.json').exists():
  if time.time()>DEADLINE:raise TimeoutError('parent terminal absent at bound')
  time.sleep(15)
 parent=json.loads((ROOT/'TERMINAL.json').read_text());dump('PARENT_TERMINAL.json',parent)
 if parent['rc']!=0:raise RuntimeError('parent failed, no partial economic inference')
 py='/workspace/venv/bin/python'
 v=run('verify',[py,'-B',str(H/'verify_label_repair_cash_20260928.py'),str(ROOT),str(OUT/'INDEPENDENT_RAW_CHECK.json')],300)
 dump('VERIFY_STEP.json',v)
 a=run('archive',[py,'-B',str(H/'archive_label_repair_cash_20260928.py'),str(ROOT),str(OUT/'F10_LABEL_REPAIR_CASH_20260928')],300)
 dump('ARCHIVE_STEP.json',a)
 receipt=json.loads((OUT/'F10_LABEL_REPAIR_CASH_20260928_RECEIPT.json').read_text());verified={}
 for kind in ('small','large'):
  p=Path(receipt[kind]['path']);assert sha(p)==receipt[kind]['sha256']
  with zipfile.ZipFile(p) as z:
   m=json.loads(z.read('ARCHIVE_MANIFEST.json'))
   for n,fact in m.items():
    h=hashlib.sha256();size=0
    with z.open(n) as f:
     for b in iter(lambda:f.read(1048576),b''):h.update(b);size+=len(b)
    assert h.hexdigest()==fact['sha256'] and size==fact['bytes'],n
   verified[kind]={'members_verified':len(m),'zip_sha256':sha(p),'bytes':p.stat().st_size}
 dump('POD_ARCHIVE_VERIFIED.json',verified)
 assert src=={p:sha(p) for p in src},'post source changed'
if __name__=='__main__':
 rc=1;err=None
 try:main();rc=0
 except BaseException as e:err=repr(e);traceback.print_exc()
 if OUT.exists():dump('TERMINAL.json',{'rc':rc,'error':err,'utc':time.strftime('%FT%TZ',time.gmtime()),'status':'INDEPENDENT_CHECK_AND_POD_ARCHIVE_DONE_NEEDS_LOCAL_TRANSFER' if rc==0 else 'FAILED'})
 sys.exit(rc)
