"""Read-only frame observations of the pinned numerical step; no cloned formula."""
import hashlib, pathlib, sys

def observed_step(fn, expected_sha, *args):
    source=pathlib.Path(fn.__code__.co_filename)
    if hashlib.sha256(source.read_bytes()).hexdigest()!=expected_sha:raise ValueError('source drift')
    if sys.gettrace() is not None:raise ValueError('another tracer already installed')
    observation={'chains':[]}; calls={}
    def snapshot(v):
        if hasattr(v,'detach'):return v.detach().cpu().clone()
        return v
    def tracer(frame,event,arg):
        if frame.f_code.co_filename!=fn.__code__.co_filename:return None
        if frame.f_code.co_name not in ('step','chain'):return None
        d=frame.f_locals
        if frame.f_code.co_name=='chain':
            if event=='call':calls[id(frame)]={'input_z':snapshot(d['z']),'previous_state':snapshot(d['h'])}
            if event=='return':
                row=calls.pop(id(frame))
                for k in ('blocked','z','v','target','band','leave','sm'):
                    if k in d:row[k]=snapshot(d[k])
                row['output']=snapshot(arg);observation['chains'].append(row)
        elif event=='return':
            for k in ('zf','w0','w2','sel','keep','gross','names','raw'):
                if k in d:observation[k]=snapshot(d[k])
        return tracer
    try:
        sys.settrace(tracer);result=fn(*args)
    finally:sys.settrace(None)
    if calls:raise ValueError('incomplete chain observation')
    return result,observation
