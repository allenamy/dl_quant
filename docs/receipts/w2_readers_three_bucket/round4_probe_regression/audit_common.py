"""Local frozen-source extraction and deny-trapped CLI helpers, no operational imports."""
from __future__ import annotations
import ast, builtins, contextlib, copy, hashlib, io, json, math, os, socket, subprocess, sys, time, types, typing
from collections import defaultdict, Counter
from datetime import datetime, timezone
from pathlib import Path
sys.dont_write_bytecode=True
OUT_SRC=Path('/Users/haosiyu/Desktop/quant_research/.claude/worktrees/codex-independent-20260907/multi_asset/exports/research/codex_round3_code_review_2026-09-13/monitoring')
OUT=Path(__file__).resolve().parent
ROOT=Path('/Users/haosiyu/Desktop/quant_research/.claude/worktrees/codex-independent-20260907')
assert OUT_SRC.resolve().is_relative_to(ROOT)
assert subprocess.check_output(['git','-C',str(ROOT),'branch','--show-current'],text=True).strip()=='agent/codex/QNT-2026-0907/onboarding-audit'
W1=OUT_SRC/'private/inputs/w1';W2=Path(os.environ.get('REGRESS_W2',str(OUT_SRC/'private/inputs/w2')));LIVE=OUT_SRC/'private/inputs/live'
PIN=json.loads((OUT_SRC/'input_manifest.json').read_text())
for r in PIN['files']+PIN['git_documents']:
    assert hashlib.sha256((OUT_SRC/r['snapshot']).read_bytes()).hexdigest()==r['sha256']
tree=ast.parse((OUT_SRC/'private/prior/private/previous/probe_review.py').read_text())
helpers=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in {'extracted','file_state','exact_cli_probe'}]
exec(compile(ast.Module(body=helpers,type_ignores=[]),'prior-independent-safe-helpers','exec'),globals())

def clean(x):
    if isinstance(x,float) and not math.isfinite(x):return 'NaN' if math.isnan(x) else ('+Inf' if x>0 else '-Inf')
    if isinstance(x,dict):return {str(k):clean(v) for k,v in x.items()}
    if isinstance(x,(list,tuple)):return [clean(v) for v in x]
    return x

def write(name,obj):
    (OUT/name).write_text(json.dumps(clean(obj),indent=2,ensure_ascii=False,allow_nan=False)+'\n')

def monitor(path):
    tree=ast.parse(path.read_text())
    exclude={'build_parser','_readonly_invocation','load_anchors','load_state','save_state','main','_telegram_sender','append_eval'}
    names={n.name for n in tree.body if isinstance(n,ast.FunctionDef) and n.name not in exclude}
    return extracted(path,names,extras={'COOLDOWN_S':86400},constants=True)

def cost_readers():
    cb=extracted(W2/'live/cost_buckets.py',{'usable_px','known_fee','filled_abs','partition','bucket_fills','pct_floor','coverage_note'},extras={'_INF':(float('inf'),float('-inf'))},constants=True)
    mod=types.ModuleType('cost_buckets');mod.__dict__.update(cb);sys.modules['cost_buckets']=mod
    pm=extracted(W2/'live/pilot_metrics.py',{'m1_effective_cost'},extras={'BPS':1e4})
    ds=extracted(W2/'ops/daily_summary.py',{'_finite','realised_facts','anchor_cost_facts','account_facts','render_account'},constants=True)
    sf=extracted(W2/'ops/score_post_fix.py',{'_verdict','_fin','_agree'},constants=True)
    tree=ast.parse((W2/'ops/score_post_fix.py').read_text());s=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='score')
    start=next(i for i,n in enumerate(s.body) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='regimes' for t in n.targets))
    end=next(i for i,n in enumerate(s.body) if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Subscript) and ast.literal_eval(n.targets[0].slice)=='overall')
    nodes=s.body[start:end]
    assert all(not(isinstance(n,ast.Import) and any(a.name!='cost_buckets' for a in n.names)) for n in nodes)
    def e6(rows,regimes=None,m1_override=None):
        reg=regimes or {r['anchor_ts']:'calm' for r in rows}
        pmod=types.SimpleNamespace(m1_effective_cost=pm['m1_effective_cost'] if m1_override is None else lambda *a:copy.deepcopy(m1_override))
        ns=dict(sf,mine=rows,data={'anchors':[{'anchor_ts':t,'regime_at_anchor':v} for t,v in reg.items()]},out={},PM=pmod)
        exec(compile(ast.Module(body=nodes,type_ignores=[]),'frozen-E6-only','exec'),ns)
        return ns['out']['E6_cost_comparable']
    return cb,pm,ds,sf,e6
