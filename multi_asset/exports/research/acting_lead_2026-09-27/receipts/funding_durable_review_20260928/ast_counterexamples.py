"""Read selected AST definitions only. No module imports, filesystem writes or executor suite."""
import ast, copy, hashlib, json, math, os, pathlib, stat, sys, time, types, typing
ROOT = pathlib.Path(sys.argv[1] if len(sys.argv)>1 else '/Users/haosiyu/cc_tmp/funding_durable_ack_exec_20260927')
EXPECTED = {'binance_funding.py':'7e92718e3af06c729c38ca7dd38b865cd5cd9b6d1a1d6d3081e6780f7c650ec1',
            'pilot_log.py':'73a69a4f14e833ea3a598ffa31fa8b482e787219ba466c0c9a7be68df898bda7'}
trees={}
for name,sha in EXPECTED.items():
 raw=(ROOT/'live'/name).read_bytes()
 assert hashlib.sha256(raw).hexdigest()==sha, 'reviewed source changed: '+name
 trees[name]=ast.parse(raw)
class NoImports(ast.NodeTransformer):
 def visit_Import(self,node): return None
 def visit_ImportFrom(self,node): return None
names={'_finite','_GapEvidence','carried_position','positions_at'}
nodes=[NoImports().visit(copy.deepcopy(n)) for n in trees['binance_funding.py'].body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name in names]
g={'Dict':typing.Dict,'Any':typing.Any,'List':typing.List,'Optional':typing.Optional,'time':time,'math':math,'RETENTION_DAYS':90}
exec(compile(ast.fix_missing_locations(ast.Module(body=nodes,type_ignores=[])),'<selected AST definitions>','exec'),g)
A=1000000.;B=A+600;t=A+300;day=time.strftime('%Y%m%d',time.gmtime(A))
r1={'symbol':'XUSDT','read_ts':A,'venue_position_qty':10.,'venue_position_notional':200.}
r2=dict(r1,venue_position_qty=5.,venue_position_notional=100.);rB=dict(r2,read_ts=B)
results=[]
for order in ([r1,r2,rB],[r2,r1,rB]):
 ev=object.__new__(g['_GapEvidence']);ev.days=[day];ev._rb={day:order};ev._fills=[];ev.now_s=B+60
 g['_PL']=types.SimpleNamespace(read_day=lambda root,d,**kw:{'position_readback':order if d==day else []})
 gap=g['carried_position'](ev,'XUSDT',int(t*1000),{'XUSDT':1.})
 fresh=g['positions_at']('/IN_MEMORY',int(t*1000),1000,strict_evidence=True)
 results.append({'ordered_A_qty':[r['venue_position_qty'] for r in order[:2]],'gap':gap,'fresh_strict':fresh})
assert results[0]['gap'][0]['notional']==100 and results[1]['gap'][0] is None
assert results[0]['fresh_strict']['positions']['XUSDT']==100 and results[1]['fresh_strict']['positions']['XUSDT']==200
node=next(n for n in trees['pilot_log.py'].body if isinstance(n,ast.FunctionDef) and n.name=='available_days')
fakeos=types.SimpleNamespace(path=os.path,listdir=lambda root:['20260924','20260925','20260926'],stat=lambda path:types.SimpleNamespace(st_mode=stat.S_IFREG if path.endswith('20260925') else stat.S_IFDIR))
h={'os':fakeos,'stat':stat,'List':typing.List};exec(compile(ast.Module(body=[node],type_ignores=[]),'<AST available_days>','exec'),h)
days=h['available_days']('/IN_MEMORY',strict=True);assert days==['20260924','20260926']
c=next(n for n in trees['pilot_log.py'].body if isinstance(n,ast.ClassDef) and n.name=='PilotLogger')
methods=[copy.deepcopy(n) for n in c.body if isinstance(n,ast.FunctionDef) and n.name in ('_w','funding')]
cl=ast.ClassDef(name='SelectedLogger',bases=[],keywords=[],body=methods,decorator_list=[])
class MemoryAppend:
 def __init__(self,partial=False):self.text='';self.partial=partial;self.fd=101
 def write(self,s):
  if self.partial:self.partial=False;self.text+=s[:10];raise OSError('injected partial append then I/O error')
  self.text+=s;return len(s)
 def flush(self):pass
 def fileno(self):return self.fd
fh=MemoryAppend(partial=True);acks=[]
k={'Any':typing.Any,'Dict':typing.Dict,'json':json,'os':os,'validate':lambda *a:None,'ack_funding_file':lambda root,day:acks.append(fh.text)}
exec(compile(ast.fix_missing_locations(ast.Module(body=[cl],type_ignores=[])),'<AST logger>','exec'),k)
def logger(handle):
 lg=object.__new__(k['SelectedLogger']);lg._funding_root_preexisting=True;lg._fh={'funding':handle};lg.root='/IN_MEMORY';lg.day='20260927';return lg
lg=logger(fh);written=[];pending=[]
for s in ['XUSDT','YUSDT']:
 r={'settlement_ts':1000,'symbol':s,'position_notional_at_settlement':1,'funding_rate':.01,'funding_paid':-.01}
 try:lg.funding(**r);written.append(s)
 except OSError:pending.append(s)
try:json.loads(fh.text.splitlines()[0]);parse_error=None
except json.JSONDecodeError as e:parse_error=str(e)
assert written==['YUSDT'] and pending==['XUSDT'] and parse_error and len(acks)==1
# Path replacement model: cached writer fd=101, current path resolves to fd=202.
# This is an explicit fault assumption, not a live-file observation.
fh2=MemoryAppend();synced=[]
fakefs=types.SimpleNamespace(path=os.path,O_RDONLY=os.O_RDONLY,open=lambda p,f:202 if p.endswith('funding.jsonl') else 303 if p.endswith('20260927') else 404,fsync=lambda fd:synced.append(fd),close=lambda fd:None)
ack=next(n for n in trees['pilot_log.py'].body if isinstance(n,ast.FunctionDef) and n.name=='ack_funding_file')
a={'os':fakefs};exec(compile(ast.Module(body=[ack],type_ignores=[]),'<AST ack>','exec'),a)
k['ack_funding_file']=a['ack_funding_file'];lg2=logger(fh2)
lg2.funding(settlement_ts=1000,symbol='YUSDT',position_notional_at_settlement=1,funding_rate=.01,funding_paid=-.01)
assert fh2.text and synced==[202,303,404] and fh2.fileno() not in synced
print(json.dumps({'source_sha256':EXPECTED,'scope':'selected AST and in-memory fakes; no actual module import, executor suite, network, state read or filesystem mutation',
 'snapshot_conflict':results,'strict_calendar_regular_file':{'listed':['20260924 dir','20260925 regular file','20260926 dir'],'returned':days},
 'partial_append':{'caller_written':written,'caller_pending':pending,'ack_count':len(acks),'jsonl_parse_error':parse_error,'limitation':'synthetic partial-write fault; no actual ENOSPC experiment'},
 'different_fd_ack':{'append_fd':fh2.fileno(),'synced_fds':synced,'funding_returned_success':True,'limitation':'assumes an external path replacement; no such live occurrence was inspected or established'}},indent=2))
