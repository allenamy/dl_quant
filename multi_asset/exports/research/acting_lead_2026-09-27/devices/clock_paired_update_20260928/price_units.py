"""Explicit log-table boundary for the fixed clock proxy; no trading entrypoint.

The historical NPY named price_full_raw contains cumulative log returns, not
absolute prices. Decode through the pinned historical FullPanel implementation.
Unknown listings remain NaN; unsupported unavailable bars refuse this proxy.
"""
import ast
import hashlib
import math
from pathlib import Path


def panel_class(np, path, expected_sha):
    raw=Path(path).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=expected_sha:
        raise ValueError('canonical price source drift')
    nodes=[n for n in ast.parse(raw).body if isinstance(n,ast.ClassDef) and n.name=='FullPanel']
    if len(nodes)!=1:raise ValueError('canonical FullPanel missing')
    ns={'np':np,'math':math,'ROW':300}
    exec(compile(ast.Module(body=nodes,type_ignores=[]),str(path),'exec'),ns)
    return ns['FullPanel']


def decode_log_prices(np, raw, ts, symbols, meta, Panel):
    syms=[str(s) for s in symbols]
    if syms!=[str(s) for s in meta['symbols']] or len(set(syms))!=len(syms):
        raise ValueError('price symbol axis mismatch')
    if ts.ndim!=1 or ts.dtype.kind not in 'iu' or len(ts)<2:
        raise ValueError('price times must be integer seconds')
    if np.any(ts%300) or not np.all(np.diff(ts)==300):
        raise ValueError('price time grid mismatch')
    grid=meta['grid']
    if grid.ndim!=1 or grid.dtype.kind not in 'iu' or np.any(grid%300) or not np.all(np.diff(grid)==300):
        raise ValueError('metadata grid mismatch')
    ii=np.searchsorted(grid,ts)
    if np.any(ii>=len(grid)) or not np.array_equal(grid[ii],ts):
        raise ValueError('price slice not covered by metadata grid')
    if raw.shape!=(len(ts),len(syms)) or raw.dtype!=np.dtype('float64') or not np.isfinite(raw).all():
        raise ValueError('cumulative log table shape/dtype/finite contract')
    first,cref,ref=(np.asarray(meta[k]) for k in ('first_fin','cref_raw','ref_px'))
    if any(x.shape!=(len(syms),) for x in (first,cref,ref)) or first.dtype.kind not in 'iu':
        raise ValueError('reference axes mismatch')
    known=first>=0
    if not np.isfinite(cref[known]).all() or not np.isfinite(ref[known]).all() or np.any(ref[known]<=0):
        raise ValueError('invalid price reference')
    ur=np.asarray(meta['unavail_grid_row']);uc=np.asarray(meta['unavail_col'])
    if ur.shape!=uc.shape or ur.ndim!=1 or ur.dtype.kind not in 'iu' or uc.dtype.kind not in 'iu':
        raise ValueError('unavailable metadata axes')
    if np.any(ur<0) or np.any(ur>=len(grid)) or np.any(uc<0) or np.any(uc>=len(syms)):
        raise ValueError('unavailable metadata index')
    ua=(grid[ur]>=ts[0])&(grid[ur]<=ts[-1])
    if ua.any():
        raise ValueError('unavailable bars require explicit UA-FREEZE-EXCLUDE support; proxy refuses')
    panel=Panel(raw,int(ts[0]),syms,first,cref,ref)
    price=np.full(raw.shape,np.nan,dtype=np.float64)
    for j,s in enumerate(syms):
        if first[j]<0:continue
        for i in range(int(np.searchsorted(ts,first[j])),len(ts)):
            v=panel.px(s,int(ts[i]))
            if v is None:raise ValueError('unexpected unknown after first finite bar')
            if not math.isfinite(v) or v<=0:raise ValueError('nonpositive/nonfinite decoded price')
            price[i,j]=v
    return price,{'encoding':'absolute_price_from_cumulative_log_v1',
                  'decoder':'pinned FullPanel.px; ref_px * exp(logcum - cref_raw)',
                  'cells':int(raw.size),'known_cells':int(np.isfinite(price).sum()),
                  'unknown_cells':int(np.isnan(price).sum()),'unavailable_cells_in_slice':int(ua.sum()),
                  'log_table_nonpositive_cells':int((raw<=0).sum()),
                  'before_listing_unknown_not_zero':True,'no_last_fin_mask_added':True}
