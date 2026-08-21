import zipfile, io, sys
import numpy as np
p = '/workspace/data/dlnative_5m_k7_f16.npz'
for attempt in range(3):
    try:
        z = zipfile.ZipFile(p)
        bad = z.testzip()
        print(f'attempt {attempt}: zip OK, entries {len(z.namelist())}, testzip bad={bad}')
        break
    except Exception as e:
        print(f'attempt {attempt}: {type(e).__name__}: {e}')
else:
    sys.exit('cache zip unreadable 3/3')
names = z.namelist(); print('entries:', names)
with z.open('data.npy') as f:
    arr = np.lib.format.read_array(io.BytesIO(f.read()), allow_pickle=True)
print('data', arr.shape, arr.dtype)
fin = np.isfinite(arr.astype(np.float32))
print('finite frac overall %.4f' % fin.mean())
for c in range(arr.shape[2]):
    print(' ch%d finite %.4f  absmean %.4f' % (c, fin[:,:,c].mean(), np.nanmean(np.abs(arr[:,:,c].astype(np.float32)))))
with z.open('idx_ms.npy') as f:
    idx = np.lib.format.read_array(io.BytesIO(f.read()), allow_pickle=True)
print('idx', idx.shape, 'first', idx[0], 'last', idx[-1], 'step', idx[1]-idx[0])
