"""Frozen, deterministic causal sampling for the F10 continuation comparison."""
import math,bisect

def probabilities(label_ends,cutoff,half_life_days):
    if not label_ends or not math.isfinite(cutoff):raise ValueError('empty or unknown cutoff')
    if any(not math.isfinite(t) or t>cutoff for t in label_ends):raise ValueError('future or unknown label')
    if half_life_days is None:return [1/len(label_ends)]*len(label_ends)
    if not math.isfinite(half_life_days) or half_life_days<=0:raise ValueError('half life')
    logs=[-(cutoff-t)/(86400*half_life_days) for t in label_ends]
    mx=max(logs);p=[2**(v-mx) for v in logs];tot=sum(p)
    return [v/tot for v in p]

def choose(p,uniforms):
    if not p or any(not math.isfinite(x) or x<0 for x in p) or not math.isclose(sum(p),1,rel_tol=1e-12,abs_tol=1e-12):raise ValueError('probabilities')
    if any(not math.isfinite(u) or not 0<=u<1 for u in uniforms):raise ValueError('uniform variates')
    c=[];tot=0
    for v in p:tot+=v;c.append(tot)
    c[-1]=1.
    return [bisect.bisect_right(c,u) for u in uniforms]

def causal_windows(anchors,ready,counts,cutoff):
    if len(anchors)!=len(ready) or len(anchors)!=len(counts) or any(not math.isfinite(t) or t!=int(t) or t%14400 for t in anchors) or any(b-a!=14400 for a,b in zip(anchors,anchors[1:])):raise ValueError('axis')
    valid=[i for i,t in enumerate(anchors) if t+14400<=cutoff and ready[i] and counts[i]>=50]
    if len(valid)<300:raise ValueError('training history too short')
    out=[]
    for s in range(valid[0]+24,valid[-1]-96,48):
        span=list(range(s-24,s+96))
        if all(ready[i] and counts[i]>=50 and anchors[i]+14400<=cutoff for i in span):out.append(span)
    return out

def align_indices(source,target):
    for axis in (source,target):
        if not len(axis) or any(not math.isfinite(t) or t!=int(t) or t%14400 for t in axis) or any(b<=a for a,b in zip(axis,axis[1:])):raise ValueError('label time axis')
    out=[]
    for t in target:
        i=bisect.bisect_left(source,t);out.append(i if i<len(source) and source[i]==t else -1)
    return out
