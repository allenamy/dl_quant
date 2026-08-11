import numpy as np, hashlib, os
R = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports"
def h(a): return hashlib.sha256(np.ascontiguousarray(a)).hexdigest()[:12]
refs = {}
for d in ("wideA_s2_y24_5yr", "wideA_s2_y24_5yr_corrfund_v1",
          "wideA_lamorth0_xattn_5yr_causal_v1", "wideA_lamorth0_xattn_5yr"):
    p = "%s/train/%s/panel_ref.npz" % (R, d)
    if not os.path.exists(p):
        print("%-42s (no panel_ref)" % d); continue
    z = np.load(p, allow_pickle=True)
    rr = {}
    for k in z.files:
        a = z[k]
        if a.dtype == object:
            print("%-42s %-10s (object) %r" % (d, k, a.reshape(-1)[:4].tolist()))
        else:
            rr[k] = h(a)
    refs[d] = rr
    print("%-42s keys=%s" % (d, z.files))
print()
ph = {}
for p in ("wide_dl_full.npz", "wide_dl_full_causal_v1.npz", "wide_dl_full_fundfix.npz",
          "wide_dl_full_corrfund_v1.npz", "wide_dl_full_serve_v1.npz"):
    fp = "%s/%s" % (R, p)
    if not os.path.exists(fp):
        print("%-34s MISSING" % p); continue
    z = np.load(fp, mmap_mode="r")
    ph[p] = {k: h(np.asarray(z[k])) for k in z.files if k in ("FUND_EMA", "X")}
    print("%-34s %s" % (p, " ".join("%s=%s" % (k, v) for k, v in ph[p].items())))
print()
for d, r in refs.items():
    for k, v in r.items():
        m = [p for p in ph if ph[p].get(k) == v]
        print("%-42s %-10s %s -> %s" % (d, k, v, m if m else "NO MATCH"))
