import numpy as np, hashlib, os
R = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports/train"
def h(a): return hashlib.sha256(np.ascontiguousarray(a)).hexdigest()[:12]
runs = ["wideA_lamorth0_xattn_5yr", "wideA_lamorth0_xattn_5yr_causal_v1",
        "wideA_lamorth0_xattn_5yr_corrfund_v1", "wideA_lamorth0_5yr_corrfund_v1",
        "wideA_lamorth0_xattn_5yr_PRODFOLD_corrfund_v1", "wideA_lamorth0_5yr_PRODFOLD_corrfund_v1",
        "wideA_s2_y24_5yr", "wideA_s2_y24_5yr_corrfund_v1"]
print("%-46s %-14s %-14s %-14s %s" % ("run", "funding", "YR", "CL", "horizon"))
print("-" * 108)
out = {}
for d in runs:
    p = "%s/%s/panel_ref.npz" % (R, d)
    if not os.path.exists(p):
        print("%-46s (missing)" % d); continue
    z = np.load(p, allow_pickle=True)
    r = {k: h(z[k]) for k in ("funding", "YR", "CL", "horizon") if k in z.files}
    out[d] = r
    print("%-46s %-14s %-14s %-14s %s" % (d, r.get("funding"), r.get("YR"), r.get("CL"), r.get("horizon")))
print()
s2c = out.get("wideA_s2_y24_5yr_corrfund_v1", {}).get("funding")
print("clean s2 funding = %s" % s2c)
for d, r in out.items():
    if d.startswith("wideA_lamorth0") and "funding" in r:
        print("  %-46s funding %s  -> %s" % (d, r["funding"],
              "SAME CALIBER as clean s2" if r["funding"] == s2c else "DIFFERENT caliber"))
