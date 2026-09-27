import hashlib, io, json, os
def _write_all(f, body): f.write(body)
def _readback(path): return open(path, "rb").read()
def _fsync_dir(d): pass
def write_bytes(path, body):
    with open(path + ".tmp", "wb") as f:
        _write_all(f, body); f.flush(); os.fsync(f.fileno())
    if _readback(path + ".tmp") != body: raise IOError("manifest read-back differs")
    os.replace(path + ".tmp", path)
    return hashlib.sha256(body).hexdigest()
def write_json(path, obj, **kw): return write_bytes(path, json.dumps(obj, **kw).encode())
def write_npz(path, **a):
    import numpy as np; b = io.BytesIO(); np.savez(b, **a); return write_bytes(path, b.getvalue())
