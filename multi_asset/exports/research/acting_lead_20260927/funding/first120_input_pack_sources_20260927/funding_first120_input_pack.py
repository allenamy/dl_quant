"""Bounded first120 input materialization, no network forward or optimizer."""
import os
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[k]='1'
os.environ['CUDA_VISIBLE_DEVICES']=''
import ast,hashlib,importlib.util,json,pathlib,struct,sys,time,zipfile
ROOT=pathlib.Path(__file__).resolve().parent
SHARED=ROOT.parent
OUT=SHARED/'first120_input_pack_20260927'


def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()


def dump(p,v):
 with open(p,'x') as f:json.dump(v,f,indent=2,allow_nan=False);f.write('\n')


def identity(st):return (st.st_dev,st.st_ino,st.st_size,st.st_mtime_ns,st.st_ctime_ns)


class BoundFile:
 def __init__(self,path,expected):
  self.path=pathlib.Path(path);self.f=self.path.open('rb');self.before=identity(os.fstat(self.f.fileno()));h=hashlib.sha256()
  for b in iter(lambda:self.f.read(1<<20),b''):h.update(b)
  if h.hexdigest()!=expected:raise ValueError('source SHA differs:'+str(path))
  self.sha=expected;self.f.seek(0);self.z=zipfile.ZipFile(self.f) if self.path.suffix=='.npz' else None
 def check(self):
  if identity(os.fstat(self.f.fileno()))!=self.before or identity(self.path.stat())!=self.before:raise ValueError('bound file changed')
 def header(self,stream):
  if stream.read(6)!=b'\x93NUMPY':raise ValueError('not NPY')
  v=tuple(stream.read(2));k=2 if v==(1,0) else 4
  if v not in ((1,0),(2,0),(3,0)):raise ValueError('NPY version')
  size=struct.unpack('<H' if k==2 else '<I',stream.read(k))[0]
  if size>1<<20:raise ValueError('header too large')
  h=ast.literal_eval(stream.read(size).decode('utf-8' if v==(3,0) else 'latin1'))
  if h['fortran_order']:raise ValueError('unsupported column-major array')
  return h
 def rows(self,np,key,start=0,end=None):
  if self.z:
   info=self.z.getinfo(key+'.npy')
   if info.flag_bits&1:raise ValueError('encrypted member')
   if info.compress_type==zipfile.ZIP_STORED:
    self.f.seek(info.header_offset);local=self.f.read(30)
    if local[:4]!=b'PK\x03\x04':raise ValueError('local ZIP header')
    h=struct.unpack('<IHHHHHIIIHH',local)
    if h[2]&1 or h[3]!=info.compress_type:raise ValueError('local ZIP method/flags differ')
    self.f.seek(h[-2]+h[-1],1);stream=self.f
   elif info.compress_type==zipfile.ZIP_DEFLATED:stream=self.z.open(info)
   else:raise ValueError('unsupported ZIP compression')
  else:self.f.seek(0);stream=self.f
  npy_start=stream.tell();h=self.header(stream);header_bytes=stream.tell()-npy_start;dt=np.dtype(h['descr']);shape=tuple(h['shape'])
  if dt.hasobject or not shape or any(type(v)!=int or v<0 for v in shape):raise ValueError('object/scalar/invalid shape input')
  end=shape[0] if end is None else end
  if not 0<=start<=end<=shape[0]:raise ValueError('invalid first dimension slice')
  stride=dt.itemsize
  for v in shape[1:]:stride*=v
  declared=(info.file_size if self.z else self.before[2])
  if header_bytes+shape[0]*stride!=declared:raise ValueError('NPY payload size differs')
  if (end-start)*stride>64<<20:raise ValueError('single loaded block exceeds64MiB')
  stream.seek(start*stride,1);b=stream.read((end-start)*stride)
  if len(b)!=(end-start)*stride:raise ValueError('truncated slice')
  result=np.frombuffer(b,dtype=dt).reshape((end-start,)+shape[1:]).copy()
  if stream is not self.f:stream.close()
  self.check();return result,h
 def close(self):
  self.check()
  if self.z:self.z.close()
  self.f.close()


def reader_controls(np,out):
 import tempfile
 with tempfile.TemporaryDirectory(dir=out,prefix='reader_control_') as d:
  p=pathlib.Path(d);x=np.arange(300,dtype=np.float32).reshape(100,3);passed=[]
  for name,save in (('stored',np.savez),('deflated',np.savez_compressed)):
   q=p/(name+'.npz');save(q,X=x);b=BoundFile(q,sha(q));got,_=b.rows(np,'X',22,32);assert np.array_equal(got,x[22:32]);passed.append(name+'_slice')
   try:b.rows(np,'X',-1,3)
   except ValueError:passed.append(name+'_negative_range')
   else:raise AssertionError('range accepted')
   b.close()
  q=p/'fortran.npz';np.savez(q,X=np.asfortranarray(x));b=BoundFile(q,sha(q))
  try:b.rows(np,'X',0,3)
  except ValueError:passed.append('fortran_rejected')
  else:raise AssertionError('fortran accepted')
  b.close()
  q=p/'mutation.npz';np.savez(q,X=x);b=BoundFile(q,sha(q))
  with open(q,'ab') as f:f.write(b'X')
  try:b.check()
  except ValueError:passed.append('source_mutation_rejected')
  else:raise AssertionError('source mutation accepted')
  b.z.close();b.f.close()
  assert len(passed)==6;dump(out/'READER_CONTROLS.json',{'passed':passed,'n':6,'domain_arrays_read':False})


def main():
 import signal
 cmd=json.loads((OUT/'COMMAND.json').read_text());signal.setitimer(signal.ITIMER_REAL,max(.001,cmd['deadline_monotonic']-time.monotonic()))
 t0=time.monotonic();os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
 import numpy as np
 reader_controls(np,OUT)
 ip=SHARED/'IDENTITY_MANIFEST.json';assert sha(ip)=='9a7de4e6cb0a02b9b8fff94c232635bce6aec8ba15ba06cb2baca3522c920b78'
 assets=json.loads(ip.read_text())['assets'];opened={}
 def bind(key):
  if key not in opened:
   e=assets[key];opened[key]=BoundFile(e['path'],e['sha256'])
   if key=='features':
    for name in ('anchors','symbols','off','m','X82','X89'):
     zi=opened[key].z.getinfo(name+'.npy');assert zi.compress_type==zipfile.ZIP_STORED and not zi.flag_bits&1
  return opened[key]
 def rows(key,name,a=0,b=None):return bind(key).rows(np,name,a,b)[0]
 base=SHARED/'first120_canonical_20260927';config=json.loads((base/'RUN_CONFIG.json').read_text());assert sha(base/'RUN_CONFIG.json')=='3a482d58c3adbc3f42ddf92c05539594ab078f6a7f5c589babc9060830b4fb63'
 anchors=np.array(config['anchors'],dtype=np.int64);all_a=rows('features','anchors');ix=np.searchsorted(all_a,anchors);assert np.array_equal(all_a[ix],anchors) and np.array_equal(ix,np.arange(2190,2310))
 symbols=rows('features','symbols');off=rows('features','off',2190,2311);assert off.dtype==np.dtype('<i8') and len(np.unique(symbols))==829;lo,hi=int(off[0]),int(off[-1]);assert (lo,hi)==(299280,316800)
 members=rows('features','m',lo,hi);x82=rows('features','X82',lo,hi);x89=rows('features','X89',lo,hi);X=np.concatenate((x82,x89),1);del x82,x89
 assert X.shape==(17520,171) and X.dtype==np.float32 and np.isfinite(X).all()
 assert members.min()>=0 and members.max()<len(symbols) and np.all(np.diff(off)>=50)
 for j in range(120):assert len(np.unique(members[int(off[j]-lo):int(off[j+1]-lo)]))==off[j+1]-off[j]
 np.save(OUT/'X171.npy',X,allow_pickle=False);del X
 np.savez(OUT/'AXES.npz',anchors=anchors,symbols=symbols,off=off-lo,m=members)
 assert np.array_equal(rows('legs','E_ts'),all_a) and np.array_equal(rows('legs','symbols'),symbols)
 legs={k:rows('legs',k,2190,2310) for k in ('KZ','ZFD','WL','RN8','QV','ready')};np.savez(OUT/'LEGS.npz',**legs)
 assert np.array_equal(rows('f10_oof','E_ts'),all_a) and np.array_equal(rows('f10_oof','symbols'),symbols)
 np.save(OUT/'REFERENCE_F10_OOF.npy',rows('f10_oof','P',2190,2310),allow_pickle=False)
 # Retain producer legal source, not an all-true approximation.
 mask=rows('combo_input_member_mask_tradable_AND_live_W24H_cachegrid.npz','mask',2190,2310)
 assert np.array_equal(rows('combo_input_member_mask_tradable_AND_live_W24H_cachegrid.npz','ts'),all_a)
 assert np.array_equal(rows('combo_input_member_mask_tradable_AND_live_W24H_cachegrid.npz','symbols'),symbols)
 assert np.array_equal(rows('combo_input_P1_members_2025H2on.npz','symbols'),symbols)
 crypto=rows('combo_input_P1_members_2025H2on.npz','crypto').astype(bool)
 ua=rows('target_universe','ts');us=rows('target_universe','symbols');ui=np.searchsorted(ua,anchors);assert np.array_equal(ua[ui],anchors) and np.array_equal(us,symbols)
 assert np.array_equal(ui,np.arange(ui[0],ui[-1]+1));pit=rows('target_universe','pit',int(ui[0]),int(ui[-1])+1)
 legal=pit&mask&crypto[None,:];np.save(OUT/'LEGAL.npy',legal,allow_pickle=False)
 # The original exact-ms checker is the sole ledger loader; all q=0 events remain.
 cp=SHARED/'d10_first_span_identity.py';assert sha(cp)=='5f1ba04e22ac45ae4b7c632a9df1ae11f8f55b164c59ba33e7bc0fc62800c104'
 spec=importlib.util.spec_from_file_location('pack_checker',cp);checker=importlib.util.module_from_spec(spec);spec.loader.exec_module(checker)
 contract=json.loads((base/'INPUT_CONTRACT.json').read_text());ev,ir=checker.check_and_load(contract,ip,sha(ip));np.savez(OUT/'EVENTS.npz',**ev);dump(OUT/'EVENT_INPUT_RECEIPT.json',ir)
 cr=json.loads((base/'cash/RESULT.json').read_text());assert sha(base/'cash/RESULT.json')=='617ba3ba0f12e22eee884af7c8f62e65d514f4374480bf541ad68dd10a3d9d57'
 a,b=cr['price_row_block']['row_start'],cr['price_row_block']['row_end_exclusive'];price=rows('price_full_raw','unused',a,b);assert price.nbytes==38213584
 meta=bind('price_full_meta');mts=meta.rows(np,'grid',a,b)[0];ms=meta.rows(np,'symbols')[0];assert np.array_equal(ms,symbols)
 assert price.shape==(5762,829) and price.dtype==np.float64 and np.all(np.diff(mts)==300) and mts[0]<=anchors[0] and mts[-1]>=config['terminal_B']
 np.save(OUT/'PRICE_RAW.npy',price,allow_pickle=False);np.save(OUT/'PRICE_TS.npy',mts,allow_pickle=False)
 price_valid=np.isfinite(price)&(price>0);dump(OUT/'PRICE_OBSERVABILITY.json',{'rows':list(price.shape),'finite_positive_cells':int(price_valid.sum()),'missing_cells':int((~price_valid).sum()),'missing_not_imputed':True})
 del price,price_valid
 for n in ('TARGETS.npz','scaled_diagnostic.npz','literal.npz'):
  p=base/n;(OUT/n).write_bytes(p.read_bytes())
 dump(OUT/'INITIAL_STATE.json',{'canonical_sealed':cr['initial_state'],'canonical_sealed_sha256':cr['initial_state_sha256'],'producer_kc_fc':'zero at original Jan1 origin; prefix0','actual_q_stopgrad':True,'producer_h_distinct_from_quantity_q':True})
 # Checkpoint is a read-only initialization/normalization reference, not new fitted output.
 model=pathlib.Path('/workspace/dlarch_2026-09-24/f10d10_2026-09-27/runs/d10/G1_T0_nomask/f10_s42/202608/model.pt');assert sha(model)=='e8ed6a3eeed417a97826ac580422e0e57bd2e0c3c6fa4bd50484fd6b0257f97f'
 import torch
 torch.set_num_threads(1);torch.set_num_interop_threads(1);assert not torch.cuda.is_initialized()
 ck=torch.load(model,map_location='cpu',weights_only=True);mu=ck['mu'].detach().numpy();sd=ck['sd'].detach().numpy();assert mu.shape==sd.shape==(171,) and np.isfinite(mu).all() and np.isfinite(sd).all() and (sd>0).all()
 np.savez(OUT/'NORMALIZATION.npz',mu=mu,sd=sd)
 state_sha={k:hashlib.sha256(v.detach().numpy().tobytes()).hexdigest() for k,v in ck['state_dict'].items()}
 dump(OUT/'NORMALIZATION_SOURCE.json',{'model_path':str(model),'model_sha256':sha(model),'state_tensors_sha256':state_sha,'trained_features_sha256':'f1cd3fa2b48e96ddf202a5098e08b9cc0ebcffda3bfc42c347743b9a5cd7d5fd','current_feature_sha256':assets['features']['sha256'],'scope':'service-consistent implementation initialization; not retrained ad80 candidate','standardization':'float32 concat(X82,X89), assert all finite; torch.clamp((X-mu)/sd,-5,5); no raw NaN imputation', 'moments_population':'original tr1 first85% of pre-cutoff ready anchors, tr1[::7] member rows then [::3]; mu=mean,sd=sample_std+1e-6; not refit in this pack','fold_receipt_sha256':'11ca8e7d0711ad7e7a581828dc6e9d5b4869ac9030363a38a80016ccebb6a087','forward_calls':0,'optimizer_updates':0})
 bindings={k:{'path':str(v.path),'sha256':v.sha,'fstat_before_and_after':v.before} for k,v in opened.items()}
 for v in opened.values():v.close()
 artifacts={p.name:{'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(OUT.iterdir()) if p.is_file() and p.suffix in ('.npy','.npz','.json')}
 result={'utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'status':'INPUT_PACK_ONLY_NO_FORWARD_NO_OPTIMIZER','source_sha256':sha(__file__),'bindings':bindings,'artifacts':artifacts,'X_shape':[17520,171],'X_bytes':11983680,'n_anchors':120,'n_world_symbols':829,'n_events':len(ev['ft_ms']),'first_A':int(anchors[0]),'terminal_B':config['terminal_B'],'published':9,'hold':111,'normalization_scope':'frozen early-D10 training moments; current ad80 evaluation inputs, implementation only','elapsed_seconds':time.monotonic()-t0,'cuda_initialized':torch.cuda.is_initialized(),'total_output_bytes':sum(p.stat().st_size for p in OUT.iterdir() if p.is_file()),'limits':['No labels, no forward/backward, no candidate','F0 strict byte identity unresolved','all missing raw prices retained, not zero filled','new forward/backward device requires separate root review']}
 dump(OUT/'RESULT.json',result);print(json.dumps({k:result[k] for k in ('status','X_bytes','n_events','total_output_bytes','elapsed_seconds')},indent=2))


if __name__=='__main__':main()
