import sys; sys.path.insert(0, '/workspace')
import zipfile
import numpy as np
from zload import zload
p = '/workspace/data/dlnative_5m_k7_f16.npz'
z = zipfile.ZipFile(p)
assert z.testzip() is None, 'zip corrupt'
d = zload(p)
arr = d['data']; ts = d['ts'].astype(np.int64)
assert arr.shape == (484705, 140, 7), f'shape {arr.shape}'
assert int(ts[0]) == 1640995200, f'ts0 {ts[0]}'
assert int(ts[1]-ts[0]) == 300, f'step {ts[1]-ts[0]}'
fin = np.isfinite(arr[::37].astype(np.float32)).mean()
print('finite frac (subsampled) %.4f' % fin)
assert fin > 0.4, 'mostly NaN'
a0 = np.abs(np.nan_to_num(arr[::37,:,0].astype(np.float32))).mean()
print('ch0 |ret5| mean %.6f' % a0)
assert 1e-6 < a0 < 0.1, 'ch0 insane'
print('VERIFY_OK', flush=True)
