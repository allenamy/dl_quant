"""pod_f8_build_stable.py = /workspace/pod_f8_build_ext.py verbatim with ONLY the trend block (L204-L216) replaced by stable_trend_block (PREREG §2)."""
import hashlib
s = open("/workspace/pod_f8_build_ext.py").read()
old = '''        # 趋势: 对数价格 p 对时间的带号 R²(p 预上市 NaN)
        p = np.cumsum(np.log1p(rz), 0)
        first = np.where(fin.any(0), fin.argmax(0), TT)
        pm = (np.arange(TT)[:, None] >= first[None, :])
        pz = np.where(pm, p, 0.0); pmf = pm.astype(np.float64)
        CSpm = cs(pmf); CSp = cs(pz); CSp2 = cs(pz ** 2); CSt = cs(tidx[:, None] * pmf); CSt2 = cs(tidx[:, None] ** 2 * pmf); CStp = cs(tidx[:, None] * pz)
        for w in (288, 2016):
            lo = lo_of(w); n = wsum(CSpm, hi, lo); nn = np.maximum(n, 1)
            Sp = wsum(CSp, hi, lo); Sp2 = wsum(CSp2, hi, lo); St = wsum(CSt, hi, lo); St2 = wsum(CSt2, hi, lo); Stp = wsum(CStp, hi, lo)
            cov = Stp / nn - (St / nn) * (Sp / nn); vt = St2 / nn - (St / nn) ** 2; vp = Sp2 / nn - (Sp / nn) ** 2
            rho = cov / np.sqrt(np.maximum(vt * vp, 1e-30)); rho = np.clip(rho, -1, 1)
            tr = np.sign(rho) * rho ** 2; tr[(n < w // 2) | (vp <= 1e-20)] = np.nan; put(f"C:trend_{w}", tr, chunk)
        del CSpm, CSp, CSp2, CSt, CSt2, CStp
'''
new = '''        # 趋势: 对数价格 p 对时间的带号 R²(p 预上市 NaN) —— STABLE LOCAL version (PREREG_fea89_stable_trend §2): window-local cumulative log price & local time, no global cumsums
        p = np.cumsum(np.log1p(rz), 0)
        first = np.where(fin.any(0), fin.argmax(0), TT)
        pm = (np.arange(TT)[:, None] >= first[None, :])
        pz = np.where(pm, p, 0.0); pmf = pm.astype(np.float64)     # kept: used by later families
        from stable_trend import stable_trend_block
        for w in (288, 2016):
            put(f"C:trend_{w}", stable_trend_block(np.log1p(rz), pm, hi, w), chunk)
'''
assert old in s, "trend block not found verbatim"; s2 = s.replace(old, new)
s2 = s2.replace('import numpy as np', 'import numpy as np\nimport sys; sys.path.insert(0, "/workspace/review_scratch")', 1)
open("/workspace/review_scratch/pod_f8_build_stable.py", "w").write(s2)
print("written; sha16", hashlib.sha256(s2.encode()).hexdigest()[:16], "| base sha16", hashlib.sha256(s.encode()).hexdigest()[:16], "| diff lines:", sum(1 for a, b in zip(s.splitlines(), s2.splitlines()) if a != b), "(+ block size change)")
