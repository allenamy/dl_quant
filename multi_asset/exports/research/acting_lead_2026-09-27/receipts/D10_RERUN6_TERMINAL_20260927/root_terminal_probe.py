import json,hashlib,pathlib,datetime,base64
R=pathlib.Path('/workspace/codex_research/QNT-2026-0907/acting_lead_20260927/d10_rerun6_queue')
def sha(p):
 p=pathlib.Path(p); h=hashlib.sha256();a=p.stat()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(4<<20),b''):h.update(b)
 z=p.stat();assert (a.st_dev,a.st_ino,a.st_size,a.st_mtime_ns)==(z.st_dev,z.st_ino,z.st_size,z.st_mtime_ns),str(p)
 return h.hexdigest()
cfg=json.loads((R/'d10_rerun6_config.json').read_text());man=json.loads((R/'d10_rerun6_manifest.json').read_text());done=json.loads((R/'DONE.json').read_text())
assert sha(R/'d10_rerun6_config.json')=='d5a3216d59fd915f5198402ac59dcefc1ec4e314e4b177c7a55f112409418c0b'
assert sha(cfg['manifest'])==done['manifest_sha256']=='4ad2da4a4b30160cee541b7c660dea4afbd3420b1d29cf9e1db39ac8bdf68a36'
assert sha(done['result_path'])==done['result_sha256']=='7eca58f29075a165b68fa4b52ab51f9cbbed5bd0ba7fbed6cbcfc7013ea9ffe0'
checked={}
for p,h in {**man['pins'],**cfg['queue_pins']}.items():
 g=sha(p); assert g==h,(p,g,h);checked[p]=g
for p in man['must_remain_absent']:assert not pathlib.Path(p).exists(),p
for p,names in man['code_inventory'].items():assert sorted(q.name for q in pathlib.Path(p).iterdir() if q.is_file() and q.suffix in ('.py','.sh'))==names,p
j=json.loads(pathlib.Path(done['result_path']).read_text());rows=j['rows'];assert len(rows)==15 and len({r['row'] for r in rows})==15
assert all(r['verdict'] in {'PASS','IDENTICAL','IDENTICAL_EXCEPT_DECLARED'} for r in rows)
assert [r['row'] for r in rows if r['rc']!=0]==['D4b_parity_common_window']
paths=[]
for r in rows:
 for c in r.get('comparisons',[]):
  if c.get('kind')=='json':paths.append(c['new'])
paths+= [str(pathlib.Path(cfg['exp'])/'out/D10_PARITY_POSITIVE_CONTROL.json')]
raw={};art={}
for p in paths:
 b=pathlib.Path(p).read_bytes();assert len(b)<5<<20,p;raw[p]=base64.b64encode(b).decode();art[p]=hashlib.sha256(b).hexdigest()
common=json.loads(pathlib.Path(cfg['exp']+'/out/D10_PARITY_COMMON_WINDOW.json').read_text())
out={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'REPRODUCTION_COMPLETE_NOT_DEPLOYMENT_APPROVAL','result_sha256':done['result_sha256'],'pins_checked':checked,'pins_n':len(checked),'row_summary':[{k:r.get(k) for k in ('row','verdict','rc','seconds','detail')} for r in rows],'artifact_sha256':art,'raw_receipts_base64':raw,'common_window_verdict':common.get('verdict'),'source_sha256':hashlib.sha256(__import__('sys').stdin.read().encode()).hexdigest() if False else 'see_local_probe_sha'}
print(json.dumps(out))
