import json,hashlib,pathlib,datetime
pins={'/dev/shm/d10_2026-09-25/ms/ledger_full_ms.npz': 'e179071d595521987450f89e1774a95775a2593d76277a9c9dc6d86dcbc31a88', '/workspace/d10_dryrun_rerun6_20260927T133902Z/out/ms/ledger_full_ms.npz': 'e179071d595521987450f89e1774a95775a2593d76277a9c9dc6d86dcbc31a88', '/dev/shm/d10_2026-09-25/lineD/stage2/fund_state_snap.npz': '35cc8f309267ea7b7019595178a8367947700c07f39ee6512ea42e2ec8069542', '/workspace/d10_dryrun_rerun6_20260927T133902Z/out/fund_state_snap.npz': '35cc8f309267ea7b7019595178a8367947700c07f39ee6512ea42e2ec8069542', '/dev/shm/d10_2026-09-25/lineD/stage2/fund_state_d10.npz': 'f07e4ebdfa4310b10ee8ac6e1f631d0787adaa10a1803507f81e95539ccd46c7', '/workspace/d10_dryrun_rerun6_20260927T133902Z/out/fund_state_d10.npz': 'f07e4ebdfa4310b10ee8ac6e1f631d0787adaa10a1803507f81e95539ccd46c7', '/workspace/d10_lineD_2026-09-26/stage2/NEWS_FEATURES_D10.npz': 'f1cd3fa2b48e96ddf202a5098e08b9cc0ebcffda3bfc42c347743b9a5cd7d5fd', '/workspace/d10_dryrun_rerun6_20260927T133902Z/out/NEWS_FEATURES_D10.npz': 'f1cd3fa2b48e96ddf202a5098e08b9cc0ebcffda3bfc42c347743b9a5cd7d5fd'}
out={}
for p,h in pins.items():
 q=pathlib.Path(p);a=q.stat();s=hashlib.sha256()
 with q.open('rb') as f:
  for b in iter(lambda:f.read(4<<20),b''):s.update(b)
 z=q.stat();assert (a.st_dev,a.st_ino,a.st_size,a.st_mtime_ns)==(z.st_dev,z.st_ino,z.st_size,z.st_mtime_ns)
 assert s.hexdigest()==h,(p,s.hexdigest(),h);out[p]={'sha256':h,'bytes':a.st_size}
print(json.dumps({'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'verified':out,'bytes_read':sum(x['bytes'] for x in out.values())}))
