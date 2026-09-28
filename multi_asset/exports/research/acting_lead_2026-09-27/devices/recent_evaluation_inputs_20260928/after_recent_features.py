"""Bounded dependency handoff; never start predictions on partial feature files."""
from pathlib import Path
from datetime import datetime,timezone
import json,subprocess,time,sys,hashlib

def main():
    root=Path('/dev/shm/recent_nc_predictions_20260928');source=Path(__file__).with_name('recent_predictions.py');term=Path('/dev/shm/recent_f10_features_20260928/TERMINAL.json')
    deadline=datetime.fromisoformat('2026-09-28T12:25:53+00:00').timestamp()
    expected=json.loads(Path(__file__).with_name('PREDICTION_SOURCE_PIN.json').read_text())['sha256']
    if hashlib.sha256(source.read_bytes()).hexdigest()!=expected:raise ValueError('prediction source changed')
    if root.exists():raise FileExistsError('prediction already attempted')
    while not term.exists():
        if time.time()>=deadline:raise TimeoutError('feature deadline expired; no restart')
        time.sleep(5)
    t=json.loads(term.read_text())
    if t.get('rc')!=0:raise ValueError('feature dependency failed '+repr(t))
    r=subprocess.run(['/workspace/venv/bin/python','-u','-B',str(source),str(root)],timeout=min(180,max(1,deadline+180-time.time())))
    if r.returncode:raise RuntimeError('prediction returned '+str(r.returncode))
    if not (root/'TERMINAL.json').is_file() or json.loads((root/'TERMINAL.json').read_text()).get('rc')!=0:raise ValueError('prediction terminal missing')
    (root/'HANDOFF_COMPLETE.json').write_text(json.dumps({'rc':0,'utc':datetime.now(timezone.utc).isoformat(),'dependency_terminal_sha256':hashlib.sha256(term.read_bytes()).hexdigest(),'prediction_source_sha256':expected},indent=2)+'\n')

if __name__=='__main__':
    try:main()
    except BaseException as e:
        p=Path('/dev/shm/recent_nc_predictions_20260928.HANDOFF_FAILED.json');p.write_text(json.dumps({'rc':1,'utc':datetime.now(timezone.utc).isoformat(),'error':repr(e)},indent=2)+'\n');raise
