import hashlib, io, json, os
def _write_all(f, body): f.write(body)
def _readback(path): return open(path, "rb").read()
def _fsync_dir(d): pass
def write_bytes(path, body):
    with open(path, "wb") as f: _write_all(f, body)
    return hashlib.sha256(body).hexdigest()
def write_json(path, obj, **kw): return write_bytes(path, json.dumps(obj, **kw).encode())
def write_npz(path, **a):
    import numpy as np; np.savez(path, **a); return hashlib.sha256(open(path if path.endswith(".npz") else path + ".npz", "rb").read()).hexdigest()
