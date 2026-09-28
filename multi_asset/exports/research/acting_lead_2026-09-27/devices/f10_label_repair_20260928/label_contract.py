"""Label repair identity and exact training-population reuse rules."""
import numpy as np

def validate_overlay(old,new):
 a,b=np.asarray(old),np.asarray(new)
 if a.shape!=b.shape or a.dtype!=b.dtype or a.dtype.kind!='f':raise ValueError('label axes/dtype')
 if np.isinf(a).any() or np.isinf(b).any():raise ValueError('infinite label')
 finite=np.isfinite(a)
 if a[finite].tobytes()!=b[finite].tobytes():raise ValueError('existing finite label changed')
 if np.any(finite&~np.isfinite(b)):raise ValueError('lost observed label')
 return int((~finite&np.isfinite(b)).sum())

def needs_refit(old_windows,new_windows):
 return [tuple(x) for x in old_windows]!=[tuple(x) for x in new_windows]

def assert_reproduction(old_state,new_state,old_samples,new_samples,old_scores,new_scores):
 if not old_state or old_state!=new_state:raise ValueError('old-input model state differs')
 if list(old_samples)!=list(new_samples):raise ValueError('old-input sampled windows differ')
 a,b=np.asarray(old_scores),np.asarray(new_scores)
 if a.dtype!=b.dtype or a.shape!=b.shape or a.tobytes()!=b.tobytes():raise ValueError('old-input score bytes differ')
