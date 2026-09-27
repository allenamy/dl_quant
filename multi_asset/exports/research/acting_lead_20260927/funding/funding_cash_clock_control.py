#!/usr/bin/env python3
import ast,hashlib,heapq,collections,json,math,types,time,pathlib
ROOT=pathlib.Path('/Users/haosiyu/.codex/worktrees/acting-lead-20260927/quant_research')
p=ROOT/'multi_asset/exports/research/replay_exec_2026-09-19/exec_sim.py';src=p.read_text();h=hashlib.sha256(src.encode()).hexdigest();assert h=='29679672e68d4842a62616e40c5fc57143f724b9ebfa6bbde927670624247c24'
tree=ast.parse(src);klass=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Sim');names=['on_funding','push','step_until'];nodes=[n for n in klass.body if isinstance(n,ast.FunctionDef) and n.name in names];pr=next(n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='PRI' for t in n.targets));PRI=ast.literal_eval(pr.value)
ns={'heapq':heapq,'PRI':PRI,'L':types.SimpleNamespace(floor_b=lambda t:int(t)//300*300)}
for n in nodes:exec(compile(ast.Module(body=[n],type_ignores=[]),str(p),'exec'),ns)
class Fixture:
 on_funding=ns['on_funding'];push=ns['push'];step_until=ns['step_until']
 def __init__(self,x=1.,rate_mult=1.,same_time_wrong=False,backdate_new=False):
  self.q={'S':100.+(100*x if backdate_new else 0)};self.K=0.;self.acc=collections.Counter();self.fund_log=[];self.k={};self.ev=[];self.seq=0
  self.F=types.SimpleNamespace(rate={('S',int(t)):r*rate_mult for t,r in [(A+.001,.0001),(A+3600,-.0002),(A+14400+.001,.0003)]})
  for t in [A+.001,A+3600,A+14400+.001]:self.push(t,'funding',None)
  if not backdate_new:self.push(A+1450,'fill',100*x)
  self.push(A+3600,'fill',-50.)
  if same_time_wrong:self.ev=[(t,1 if kind=='fill' else pri,n,kind,arg) for t,pri,n,kind,arg in self.ev];heapq.heapify(self.ev)
 def px(self,s,b):return 11. if b>=A+14400 else 12. if b>=A+3600 else 10.
 def dispatch(self,t,kind,arg):
  if kind=='funding':self.on_funding(t)
  else:self.q['S']+=arg
A=1787702400

def run(**kw):
 s=Fixture(**kw);s.step_until();return s
s=run();cash=[v[-1] for v in s.fund_log];expect=[-.1,.48,-.495];assert max(abs(x-y) for x,y in zip(cash,expect))<1e-12
analytic=100*12*.0002-100*11*.0003
fd=(run(x=1.0001).K-run(x=.9999).K)/.0002
assert abs(fd-analytic)<1e-9 and run(rate_mult=0).K==0 and abs(run(rate_mult=-1).K+s.K)<1e-12
wrong1=run(backdate_new=True).K;wrong2=run(same_time_wrong=True).K;assert abs(wrong1-s.K)>1e-6 and abs(wrong2-s.K)>1e-6
# Distinct ms events cannot share one int-key lookup unless the adapter explicitly models aggregation and calls once.
rates={("S",A):.0001};rates[("S",A)]=.0003
int_key_twice=-100*10*(rates[('S',A)]+rates[('S',A)]);event_sum=-100*10*(.0001+.0003)
assert abs(int_key_twice-event_sum)>1e-8
out={'utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'source_sha':h,'methods':names,'priority':PRI,'cash_each':cash,'cash_total':s.K,'analytic_derivative_d_cash_d_newfill_scale':analytic,'finite_difference_derivative':fd,'first_event_derivative_newfill':0.,'controls':{'literal_cash':True,'zero_funding':True,'sign_flip':True,'backdate_new_red':wrong1,'wrong_same_time_fill_red':wrong2,'ms_int_key_collision_red':{'wrong_cash':int_key_twice,'true_event_cash':event_sum}},'verdict':'IMPLEMENTATION_CONTROL_PASS','economic_gate':'UNAVAILABLE_FIXED_V3_PATH_MIRROR_MISSING','limitations':['Synthetic fixed fill path; no learned scores or actual strategy change','Does not claim existing integer-second funding adapter violates its stated source contract','No full-engine differentiability requirement; actual cash path still required before training smoke']}
print(json.dumps(out,indent=2))
