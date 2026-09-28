"""One CPU target job, exact own PID/process-group timeout, durable terminal."""
import hashlib,json,os,signal,subprocess,sys,time
from pathlib import Path


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def save(p,x):
    b=(json.dumps(x,indent=2)+'\n').encode()
    with open(str(p)+'.tmp','wb') as f:f.write(b);f.flush();os.fsync(f.fileno())
    os.replace(str(p)+'.tmp',p)


here=Path(__file__).resolve().parent;out=Path(sys.argv[1]);start=time.time();p=None
contract={'out':str(out),'python':sys.executable,'source_sha256':{str(f):sha(f) for f in here.glob('*.py')},
    'started_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime(start)),
    'deadline_epoch':start+1500,'max_child_rss_bytes':8*2**30,
    'environment':{k:os.environ.get(k) for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NPY_DISABLE_CPU_FEATURES')}}
save(here/'CONTRACT.json',contract);status='UNAVAILABLE';rc=None;peak=0
try:
    current=int(Path('/sys/fs/cgroup/memory.current').read_text());limit=int(Path('/sys/fs/cgroup/memory.max').read_text())
    free=os.statvfs('/dev/shm');assert limit-current>=10*2**30 and free.f_bavail*free.f_frsize>=4*2**30,'resource gate'
    with open(here/'tests.log','wb') as f:
        subprocess.run([sys.executable,'-B','-m','unittest','discover','-s',str(here),'-p','tests_*.py'],stdout=f,stderr=subprocess.STDOUT,check=True,timeout=60)
    with open(here/'run.log','wb') as f:
        p=subprocess.Popen([sys.executable,'-B',str(here/'blend_support.py'),str(out)],stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
        ticks=Path(f'/proc/{p.pid}/stat').read_text().split()[21]
        save(here/'CHILD.json',{'pid':p.pid,'pgid':os.getpgid(p.pid),'start_ticks':ticks})
        while p.poll() is None:
            st=Path(f'/proc/{p.pid}/status').read_text();rss=next((int(l.split()[1])*1024 for l in st.splitlines() if l.startswith('VmRSS:')),0);peak=max(peak,rss)
            if time.time()>contract['deadline_epoch'] or rss>contract['max_child_rss_bytes']:
                status='RESOURCE_OR_TIME_LIMIT';assert Path(f'/proc/{p.pid}/stat').read_text().split()[21]==ticks
                os.killpg(p.pid,signal.SIGTERM);p.wait(timeout=15);raise RuntimeError(status)
            time.sleep(2)
        rc=p.returncode;status='COMPLETE' if rc==0 and (out/'RESULT.json').is_file() else 'FAILED'
except Exception as e:
    save(here/'ERROR.json',{'exception':repr(e)})
finally:
    if p is not None and p.poll() is None:
        os.killpg(p.pid,signal.SIGTERM);p.wait(timeout=15)
    save(here/'TERMINAL.json',{'status':status,'returncode':rc,'seconds':time.time()-start,'peak_child_rss_bytes':peak,
        'contract_sha256':sha(here/'CONTRACT.json'),'result_sha256':sha(out/'RESULT.json') if (out/'RESULT.json').is_file() else None})
