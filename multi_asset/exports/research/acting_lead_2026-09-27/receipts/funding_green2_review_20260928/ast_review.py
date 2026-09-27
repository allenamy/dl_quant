"""Review four known defects using selected source AST and pure in-memory I/O models.
No production module import, executor suite, network, live state or file mutation.
"""
import ast,copy,hashlib,io,json,math,os,pathlib,stat,sys,time,types,typing
ROOT=pathlib.Path(sys.argv[1] if len(sys.argv)>1 else '/Users/haosiyu/cc_tmp/funding_durable_ack_exec_20260927')
PINS={'binance_funding.py':'d96b377f86e9d55a1ddd7f63d94a60d872256b97d1b5cfa513c214292c9dfd69','pilot_log.py':'6e5ccf3ef25a190c8290a2e1058bfff9454e6e7f72fd1f6d48204e6ac48dd83a'}
trees={}
for name,sha in PINS.items():
 raw=(ROOT/'live'/name).read_bytes();assert hashlib.sha256(raw).hexdigest()==sha,('source drift',name);trees[name]=ast.parse(raw)
class NoImports(ast.NodeTransformer):
 def visit_Import(self,node):return None
 def visit_ImportFrom(self,node):return None
def run_nodes(nodes,g,label):exec(compile(ast.fix_missing_locations(ast.Module(body=nodes,type_ignores=[])),label,'exec'),g)
def defs(tree,names):return [copy.deepcopy(n) for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name in names]
def refused(fn,word):
 try:fn()
 except (ValueError,RuntimeError,OSError) as e:
  assert word in str(e),str(e);return str(e)
 raise AssertionError('unsafe success; expected '+word)
checks={};details={}
g={'Dict':typing.Dict,'Any':typing.Any,'List':typing.List,'Optional':typing.Optional,'time':time,'math':math,'RETENTION_DAYS':90}
run_nodes([NoImports().visit(n) for n in defs(trees['binance_funding.py'],{'_finite','_readback_ts','_strict_snapshot','_GapEvidence','carried_position','positions_at'})],g,'<funding AST>')
A=1000000000.;B=A+600;t=A+300;day=time.strftime('%Y%m%d',time.gmtime(A))
r1={'symbol':'XUSDT','read_ts':A,'venue_position_qty':10.,'venue_position_notional':200.}
r2=dict(r1,venue_position_qty=5.,venue_position_notional=100.);rB=dict(r2,read_ts=B)
def view(rows):
 ev=object.__new__(g['_GapEvidence']);ev.days=[day];ev._rb={day:rows};ev._fills=[];ev.now_s=B+60
 g['_PL']=types.SimpleNamespace(read_day=lambda root,d,**kw:{'position_readback':rows if d==day else []})
 return (lambda:g['carried_position'](ev,'XUSDT',int(t*1000),{'XUSDT':1.})),(lambda:g['positions_at']('/IN_MEMORY',int(t*1000),1000,strict_evidence=True))
conflicts=[]
for rows in ([r1,r2,rB],[r2,r1,rB]):
 gap,fresh=view(rows);conflicts.append({'gap':refused(gap,'conflicting'),'fresh':refused(fresh,'conflicting')})
checks['fresh_and_gap_both_refuse_conflict_in_both_orders']=True
for rows in ([r2,dict(r2),rB],[dict(r2,read_ts=math.nextafter(A,math.inf)),r1,rB]):
 gap,fresh=view(rows);assert gap()[0]['notional']==100 and fresh()['positions']['XUSDT']==100
checks['identical_duplicate_and_exact_nearby_timestamp_positives']=True;details['snapshot_refusals']=conflicts
# Strict calendar failure remains loud; no filesystem access.
fakeos=types.SimpleNamespace(path=os.path,listdir=lambda root:['20260924','20260925','20260926'],stat=lambda path:types.SimpleNamespace(st_mode=stat.S_IFREG if path.endswith('20260925') else stat.S_IFDIR))
h={'os':fakeos,'stat':stat,'List':typing.List};run_nodes(defs(trees['pilot_log.py'],{'available_days'}),h,'<calendar AST>')
details['regular_date_file']=refused(lambda:h['available_days']('/IN_MEMORY',strict=True),'not a directory');checks['strict_calendar_rejects_regular_file']=True
# The actual selected owner and actual selected caller loop run on memory handles.
class MemAppend:
 def __init__(self,fail_at=None):self.text='';self.n=0;self.fail_at=fail_at
 def fileno(self):return 101
 def write(self,s):
  self.n+=1
  if self.n==self.fail_at:self.text+=s[:10];raise OSError('partial append after ten bytes')
  self.text+=s;return len(s)
 def flush(self):pass
synced=[];closed=[];path_inode=101
fs=types.SimpleNamespace(path=os.path,O_RDONLY=os.O_RDONLY,
 open=lambda p,flags:202 if p.endswith('funding.jsonl') else 303 if p.endswith('20260927') else 404,
 fstat=lambda fd:types.SimpleNamespace(st_dev=1,st_ino=fd),stat=lambda p:types.SimpleNamespace(st_dev=1,st_ino=path_inode),
 fsync=lambda fd:synced.append(fd),close=lambda fd:closed.append(fd))
k={'os':fs,'Any':typing.Any,'Dict':typing.Dict,'List':typing.List,'json':json,'validate':lambda *a:None}
run_nodes(defs(trees['pilot_log.py'],{'_file_identity','ack_funding_file'}),k,'<ack AST>')
c=next(n for n in trees['pilot_log.py'].body if isinstance(n,ast.ClassDef) and n.name=='PilotLogger')
methods=[copy.deepcopy(n) for n in c.body if isinstance(n,ast.FunctionDef) and n.name in ('_w','funding')]
run_nodes([ast.ClassDef(name='SelectedLogger',bases=[],keywords=[],body=methods,decorator_list=[])],k,'<owner AST>')
def logger(fh):
 x=object.__new__(k['SelectedLogger']);x._funding_root_preexisting=True;x._funding_failed=None;x._fh={'funding':fh};x.root='/IN_MEMORY';x.day='20260927';return x
raws=[{'symbol':s,'time':1000000,'income':'-0.01'} for s in ('OKUSDT','FAILUSDT','LATERUSDT')]
rows=[{'symbol':r['symbol'],'settlement_ts':1000.,'position_notional_at_settlement':1.,'funding_rate':.01,'funding_paid':-.01} for r in raws]
fh=MemAppend(fail_at=2);lg=logger(fh)
caller=next(n for n in trees['binance_funding.py'].body if isinstance(n,ast.FunctionDef) and n.name=='write_funding_rows')
loop=next(n for n in caller.body if isinstance(n,ast.For) and isinstance(n.target,ast.Tuple) and isinstance(n.target.elts[0],ast.Name) and n.target.elts[0].id=='write_idx')
state={'to_write':list(zip(raws,rows)),'intervals':{},'carried':{},'pos_cache':{},'log':lg,'out':{'rows_written':0},'still':[],
 'entry':lambda i,why:{'row':i,'reason':why},'issue':lambda field,why:None}
run_nodes([copy.deepcopy(loop)],state,'<actual caller write loop AST>')
assert state['out']['rows_written']==1 and [x['row'] for x in state['still']]==raws[1:] and fh.n==2
owner_why=refused(lambda:lg.funding(**rows[-1]),'previous failure');assert fh.n==2
checks['partial_failure_retains_failed_and_unattempted_rows']=True;checks['owner_poison_blocks_all_later_calls']=True
# Bind loop output to final real pending call by structural inspection; no durable state writer executed.
final_try=caller.body[caller.body.index(loop)+1]
final_call=next(n for n in ast.walk(final_try) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='_write_pending')
assert isinstance(final_call.args[1],ast.Dict)
pairs=list(zip(final_call.args[1].keys,final_call.args[1].values));assert any(isinstance(a,ast.Constant) and a.value=='pending' and isinstance(b,ast.Name) and b.id=='still' for a,b in pairs)
checks['caller_final_pending_uses_preserved_still_list']=True
details['partial']={'rows_written':state['out']['rows_written'],'pending_symbols':[x['row']['symbol'] for x in state['still']], 'physical_write_calls':fh.n,'owner_refusal':owner_why,'successful_ack_fds':list(synced)}
# Current path points elsewhere: owner must refuse, poison, never ack wrong inode.
path_inode=202;fh2=MemAppend();lg2=logger(fh2);synced.clear()
details['writer_path_swap']=refused(lambda:lg2.funding(**rows[-1]),'no longer names');assert lg2._funding_failed and not synced
checks['writer_uses_actual_fd_and_refuses_replacement_path']=True
# Duplicate read to ack identity handoff: open FD202 cannot satisfy recorded identity101.
synced.clear();closed.clear();details['duplicate_ack_swap']=refused(lambda:k['ack_funding_file']('/IN_MEMORY','20260927',expected_identity=(1,101)),'identity changed');assert not synced and closed==[202]
checks['duplicate_ack_refuses_inode_different_from_read']=True
# Strict reader obtains identity from open FD and checks path both before/after.
class ReadBuffer(io.StringIO):
 def __init__(self,fd):super().__init__('{"symbol":"XUSDT"}\n');self.fd=fd
 def fileno(self):return self.fd
reader_results=[]
for tag,opened,after in [('stable',101,101),('swapped_before_open',202,101),('swapped_during_read',101,202)]:
 calls=[]
 def rstat(path):calls.append(path);return types.SimpleNamespace(st_dev=1,st_ino=101 if len(calls)==1 else after)
 rf=types.SimpleNamespace(path=os.path,stat=rstat,fstat=lambda fd:types.SimpleNamespace(st_dev=1,st_ino=fd))
 q={'os':rf,'List':typing.List,'Dict':typing.Dict,'Any':typing.Any,'json':json,'open':lambda path:ReadBuffer(opened)}
 run_nodes(defs(trees['pilot_log.py'],{'_file_identity','_read_table_strict'}),q,'<reader AST>');ids={}
 if tag=='stable':
  rr=q['_read_table_strict']('/IN_MEMORY','20260927','funding',ids);assert ids=={'funding':(1,101)} and len(rr)==1;reader_results.append([tag,'identity carried'])
 else:reader_results.append([tag,refused(lambda:q['_read_table_strict']('/IN_MEMORY','20260927','funding',ids),'changed')]);assert not ids
checks['strict_read_binds_fd_and_detects_path_swap']=True;details['reader']=reader_results
# Inspect the actual duplicate-call keyword linkage, not only the standalone helper.
ack_calls=[n for n in ast.walk(caller) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='ack_funding_file']
assert len(ack_calls)==1 and any(w.arg=='expected_identity' and ast.unparse(w.value)=='disk[0][2]' for w in ack_calls[0].keywords)
assert 'identities[\'funding\']' in ast.unparse(caller) or 'identities["funding"]' in ast.unparse(caller)
checks['duplicate_caller_passes_identity_from_strict_read']=True
print(json.dumps({'status':'FOUR_REVIEW_DEFECTS_CLOSED_IN_SELECTED_AST','source_sha256':PINS,'checks':checks,'details':details,
 'limitations':['Not the full executor suite; wrapper remains root-owned.','Does not authorize rollout or waive historical disposition failures.','In-place rewriting/truncation on the same inode and arbitrary post-ack mutation remain outside append-only ledger assumptions.','Pending queue/filesystem durability is assessed by separate full-wrapper controls, not mocked memory alone.']},indent=2))
