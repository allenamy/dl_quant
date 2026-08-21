import zipfile, io
import numpy as np
class _Z(dict):
    @property
    def files(self): return list(self.keys())
def zload(path, **kw):
    z = zipfile.ZipFile(path)
    out = _Z()
    for n in z.namelist():
        key = n[:-4] if n.endswith('.npy') else n
        with z.open(n) as f:
            out[key] = np.lib.format.read_array(io.BytesIO(f.read()), allow_pickle=True)
    return out
