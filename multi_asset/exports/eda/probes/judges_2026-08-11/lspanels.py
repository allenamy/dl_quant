import glob, os, numpy as np, datetime as dt
E = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports"
rows = []
for p in sorted(glob.glob(E + "/wide_dl*.npz")):
    try:
        z = np.load(p, allow_pickle=True)
        ts = z["ts"]; ch = z["CH"].shape if "CH" in z.files else None
        f = lambda x: dt.datetime.utcfromtimestamp(int(x)/1000).strftime("%Y-%m")
        yr24 = float(np.nanstd(z["YR24"][::97])) if "YR24" in z.files else float("nan")
        rows.append((os.path.basename(p), os.path.getsize(p)//1048576, ch, f(ts[0]), f(ts[-1]), yr24))
    except Exception as e:
        rows.append((os.path.basename(p), os.path.getsize(p)//1048576, "ERR "+type(e).__name__, "", "", float("nan")))
print("%-46s %6s %-20s %-9s %-9s %10s" % ("面板","MB","CH","起","止","YR24_std"))
for r in rows:
    print("%-46s %6d %-20s %-9s %-9s %10.6f" % (r[0], r[1], str(r[2]), r[3], r[4], r[5]))
