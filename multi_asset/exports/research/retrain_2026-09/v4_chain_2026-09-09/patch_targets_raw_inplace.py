p = "/workspace/review_scratch/pod_dlw_targets_raw.py"; s = open(p).read()
anchor = "    CS_L = np.concatenate([z1, np.cumsum(np.log1p(_rtz.astype(np.float64)), 0)]); del _rt, _rtz"
assert anchor in s
if "DLWT_RAW_PATCH" not in s:
    block = ('    _pp = os.environ.get("DLWT_RAW_PATCH")\n'
             '    if _pp:\n'
             '        _P = np.load(_pp); assert RET_CH == 0; _rtz[_P["row"], _P["col"]] = _P["raw32"].astype(np.float32)   # exact float32 raw returns on the clipped bars (PREREG_caliber_program section 3)\n'
             '        log("raw patch applied: %d bars from %s" % (len(_P["row"]), _pp))\n')
    s = s.replace(anchor, block + anchor); open(p, "w").write(s)
import py_compile; py_compile.compile(p, doraise=True); print("pod_dlw_targets_raw.py: RAW_PATCH block present, compiles")
