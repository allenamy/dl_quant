"""An implementation probe is not a candidate/policy acceptance gate."""
import math

def validate_results(result):
    expected={'A0','A1','F0_A0','F0_A1'}
    if set(result['updates'])!=expected:raise ValueError('exact four arms required')
    if result['optimizer_updates']!=4:raise ValueError('exact four one-step updates')
    rows=result['updates']
    initial=set()
    for name,r in rows.items():
        for key in ('parameter_hash_before','parameter_hash_after','loss_before_bits','gradient_sha256','optimizer_sha256'):
            if not isinstance(r[key],str) or not r[key]:raise ValueError('missing byte identity:'+key)
        initial.add(r['parameter_hash_before'])
        if r['optimizer_updates']!=1:raise ValueError('exact one step per arm')
        if r['all_finite'] is not True:raise ValueError('nonfinite result')
        err=r['hard_max_error']
        if not isinstance(err,(int,float)) or not math.isfinite(err) or err>1e-12 or err<0:raise ValueError('hard parity error')
        if r['hard_masks_equal'] is not True or r['hard_reasons_equal'] is not True:raise ValueError('hard parity routing')
    if len(initial)!=1:raise ValueError('initial model differs')
    for key in ('loss_before_bits','gradient_sha256','parameter_hash_after','optimizer_sha256'):
        if rows['F0_A0'][key]!=rows['F0_A1'][key]:raise ValueError('F0 byte mismatch:'+key)
    return 'IMPLEMENTATION_CONTROL_PASS'

def tree_digest(T,tree):
    """Hash typed values, tensor bytes (including signed zero), keys and shapes."""
    import hashlib,struct
    h=hashlib.sha256()
    def put(x):
        if isinstance(x,T.Tensor):
            x=x.detach().cpu().contiguous()
            h.update(b'tensor'+str(x.dtype).encode()+str(tuple(x.shape)).encode()+x.numpy().tobytes())
        elif isinstance(x,dict):
            h.update(b'dict')
            for k in sorted(x,key=lambda a:(type(a).__name__,str(a))):put(k);put(x[k])
        elif isinstance(x,(list,tuple)):
            h.update(type(x).__name__.encode()+str(len(x)).encode())
            for y in x:put(y)
        elif isinstance(x,float):h.update(b'float'+struct.pack('>d',x))
        elif isinstance(x,(str,int,bool)) or x is None:
            h.update(type(x).__name__.encode()+repr(x).encode()+b'\0')
        else:raise TypeError('unsupported byte carrier:'+str(type(x)))
    put(tree);return h.hexdigest()

def tree_finite(T,tree):
    if isinstance(tree,T.Tensor):return bool(T.isfinite(tree).all())
    if isinstance(tree,dict):return all(tree_finite(T,x) for x in tree.values())
    if isinstance(tree,(list,tuple)):return all(tree_finite(T,x) for x in tree)
    if isinstance(tree,(int,float)):return math.isfinite(tree)
    if tree is None or isinstance(tree,(str,bool)):return True
    raise TypeError('unknown finite carrier:'+str(type(tree)))
