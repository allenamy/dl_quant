"""Research-only bridge to pinned production pure functions; no live imports."""
from pathlib import Path
import ast,copy,hashlib,json,types

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def dust_names(result,held):
 # POP's disposition survives even when no reshape population remains.
 # A nonzero held name can only be popped by the pinned dust predicate.
 return sorted(s for s in result[0]['popped'] if float((held or {}).get(s,0.) or 0.)!=0.)

def verified_sources(root):
 root=Path(root);m=json.loads((root/'SOURCES.json').read_text())
 for name,rec in m.items():
  if sha(root/name)!=rec['sha256']:raise ValueError('source identity '+name)
  nodes=ast.parse((root/name).read_text()).body
  if not all(isinstance(n,ast.FunctionDef) for n in nodes) or sorted(n.name for n in nodes)!=rec['names']:raise ValueError('pure function source shape')
 return m

def compiled(root,label,kind,env):
 p=Path(root)/f'{label}_{kind}.py.txt';ns=dict(env)
 exec(compile('from __future__ import annotations\n'+p.read_text(),str(p),'exec'),ns)
 return ns

def install_pure(X,root):
 m=verified_sources(root)
 if m['old_legs.py.txt']['parent_sha256']!=m['current_legs.py.txt']['parent_sha256']:raise ValueError('shared legs changed')
 ns=compiled(root,'current','anchor',vars(X.AL));es=compiled(root,'current','external',vars(X.EXT))
 X.AL=types.SimpleNamespace(**vars(X.AL));X.EXT=types.SimpleNamespace(**vars(X.EXT))
 for name in m['current_anchor.py.txt']['names']:setattr(X.AL,name,ns[name])
 X.EXT.below_min_notional=es['below_min_notional']
 return X

def install(C,CFG,check):
 spec=CFG['executor_semantic_bridge'];root=Path(spec['source_root']);m=verified_sources(root)
 if spec['mode'] not in ('old_control','current_pure'):raise ValueError('bridge mode')
 for n in m:
  rec=CFG['pins']['bridge_'+n]
  if Path(rec['path']).resolve()!= (root/n).resolve() or sha(root/n)!=rec['sha256']:raise ValueError('bridge unpinned source')
 if sha(__file__)!=CFG['pins']['bridge_helper']['sha256'] or sha(root/'SOURCES.json')!=CFG['pins']['bridge_manifest']['sha256']:raise ValueError('bridge helper/manifest pin')
 if sha(C.X.LG.__file__)!=m['current_legs.py.txt']['parent_sha256']:raise ValueError('shared live legs mismatch')
 check('bridge.current_source_provenance',True,{'mode':spec['mode'],'commit':m['current_anchor.py.txt']['git_commit'],'manifest_sha256':sha(root/'SOURCES.json')})
 if spec['mode']=='old_control':return
 old=compiled(root,'old','anchor',vars(C.X.AL))['apply_withhold_and_reshape']
 install_pure(C.X,root);new=C.X.AL.apply_withhold_and_reshape;context={};base_anchor=C.ES.Sim.on_anchor
 def anchor(self,A):
  context['A']=int(A)
  return base_anchor(self,A)
 def apply(target,held,untradable,sizing_gross,*args,**kw):
  before=copy.deepcopy(target);old_t=copy.deepcopy(target)
  old(old_t,held,untradable,sizing_gross,*args,**kw)
  result=new(target,held,untradable,sizing_gross,*args,**kw)
  names=sorted(set(target)|set(old_t));d={s:target.get(s,0.)-old_t.get(s,0.) for s in names};rs=result[1] or {}
  rec={'anchor':context['A'],'sizing_gross':sizing_gross,'n_before':len(before),'n_after':len(target),
       'dust_popped':dust_names(result,held),'same_state_target_l1_delta':sum(abs(v) for v in d.values()),
       'same_state_target_max_delta':max([abs(v) for v in d.values()]+[0.]),
       'old_target_net':sum(old_t.values()),'new_target_net':sum(target.values()),
       'old_target_gross':sum(abs(v) for v in old_t.values()),'new_target_gross':sum(abs(v) for v in target.values()),
       'residual_held_usdt':{s:held[s] for s in dust_names(result,held)},
       'caller_defaulted_floor_names':[s for s in before if (C.X.filters.f.get(s) or {}).get('min_notional') is None],
       'scope':'same decision input; targets are not actual holdings or fills'}
  with Path(spec['trace']).open('a') as f:f.write(json.dumps(rec,allow_nan=False)+'\n')
  return result
 C.X.AL.apply_withhold_and_reshape=apply;C.ES.Sim.on_anchor=anchor

def patch_driver(source):
 line='    c.BOOKS = {}; c.target_info = {}; c.PIT_by_tag = {}'
 if source.count(line)!=1:raise ValueError('driver injection identity')
 return source.replace(line,'    if "executor_semantic_bridge" in CFG:\n        import executor_bridge\n        executor_bridge.install(c, CFG, check)\n'+line)
