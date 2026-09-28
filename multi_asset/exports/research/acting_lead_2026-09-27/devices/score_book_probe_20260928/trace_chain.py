"""Read-only observers inserted after exact source-bound AST statements."""
import ast
import numpy as np

def compile_trace(source):
    templates={
        'demean':('w = np.where(sel, w - (w[sel].mean() if sel.any() else 0), w)','w'),
        'normalize':('w = w / g','w'),
        'cap_normalize':('if g2 > 1e-9: w = w / g2','w'),
        'ema':('smv = H + P["alpha"] * (tgt - H)','smv'),
        'band':('smv = np.where(np.abs(trade) < P["band"], H, smv)','smv'),
        'eligible':('smv = np.where(leave, 0.0, smv)','smv'),
    }
    wanted={ast.dump(ast.parse(v[0]).body[0]):(k,v[1]) for k,v in templates.items()}
    tree=ast.parse(source);funcs=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='chain']
    if len(funcs)!=1:raise ValueError('one chain required')
    f=funcs[0];body=[];seen=[]
    for node in f.body:
        body.append(node);match=wanted.get(ast.dump(node))
        if match:
            label,var=match;seen.append(label)
            body.append(ast.parse(f'__tap__({label!r}, {var})').body[0])
    if seen!=list(templates):raise ValueError('chain observation structure drift: '+repr(seen))
    f.body=body;tree.body=[f]+[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='exec_reshape'];ast.fix_missing_locations(tree)
    traces=[];ns={'np':np,'__tap__':lambda label,value:traces.append((label,value.copy()))}
    exec(compile(tree,'<pinned-chain-with-observers>','exec'),ns)
    return ns,traces

def price_metric(w,y):
    w=np.asarray(w);y=np.asarray(y);nz=w!=0
    if not np.isfinite(w).all() or not np.isfinite(y[nz]).all():return None
    g=np.abs(w).sum()
    return float(np.dot(w[nz],y[nz])/g*1e4) if g>0 else None
