"""FTRIM 判官(PREREG d580eb2042ef §3 逐字): 臂−基线 Δnet 块自助CI(6锚×4000)双种子 + 逐年容忍带−0.3."""
import numpy as np, time
D="/mnt/storage/private/work_hsy/probe_artifacts"
rng=np.random.default_rng(17)
def load(p):
    z=np.load(p, allow_pickle=True)
    c=[str(x) for x in z["cols"]]; R=z["d30_n2_c42_rec"]; ix={k:i for i,k in enumerate(c)}
    ts=R[:,ix["ts"]].astype(np.int64); net=R[:,ix["net_ex"]]/np.maximum(R[:,ix["gross_member"]],1e-9)
    m=np.array([time.gmtime(t).tm_year>=2023 for t in ts])
    return ts[m], net[m]
def boot(d, nb=4000, blk=6):
    k=len(d)//blk; b=d[:k*blk].reshape(k,blk)
    idx=rng.integers(0,k,size=(nb,k))
    m=b[idx].mean(axis=(1,2))
    return float(np.percentile(m,2.5)), float(np.percentile(m,97.5))
print("臂  种子   dNet     CI_lo    CI_hi   | 23     24     25     26   | 判")
verdict={}
for tag in ("A1","A2","A3"):
    ok_seeds=[]
    for sd in (42,2027):
        t0,n0=load(f"{D}/w8b_rc_combo_s{sd}.npz")
        t1,n1=load(f"{D}/ftrim_{tag}_s{sd}.npz")
        com=np.intersect1d(t0,t1)
        d=n1[np.searchsorted(t1,com)]-n0[np.searchsorted(t0,com)]
        lo,hi=boot(d)
        yy=np.array([time.gmtime(int(x)).tm_year for x in com])
        by=[d[yy==y].mean() if (yy==y).sum()>30 else float("nan") for y in (2023,2024,2025,2026)]
        pass1=lo>0
        pass2=all((not np.isfinite(v)) or v>=-0.3 for v in by)
        ok_seeds.append(pass1 and pass2)
        print(f"{tag} s{sd:<5} {d.mean():+7.4f} {lo:+8.4f} {hi:+8.4f} | "+" ".join(f"{v:+5.2f}" for v in by)+f" | CI{'✓' if pass1 else '✗'} 年{'✓' if pass2 else '✗'}")
    verdict[tag]=all(ok_seeds)
print("\n=== 预注册判决 ===")
adm=[t for t,v in verdict.items() if v]
print("录取:", adm if adm else "无 — 三臂全负/不齐 ⇒ 该轴 DNR(2026反转+跨档非单调为终局解释)")
