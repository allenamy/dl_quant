"""Capacity profile for batch_002 CANDIDATEs (lead's firewall ask: this batch targets capacity).
For each candidate, per anchor split the member&CL universe by dvol_24h into a LARGE (liquid) half and
a SMALL (illiquid) half, and report the factor's rank-IC vs YR4B in each half + the full universe.
Capacity-friendly = large-half IC ~ small-half IC (signal survives in liquid names, not lottery-tail)."""
import sys
import numpy as np

FAC = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/factory"
sys.path.insert(0, FAC)
import dsl
import pipeline as P

CANDS = [
    ("I?", "xsec_z(mul(ema(ret_4h, 24), neg(rvol_6h)))"),
    ("I?", "neg(xsec_z(ts_std(ret_4h, 168)))"),
    ("J?", "neg(xsec_z(ema(rvol_72h, 168)))"),
    ("J?", "neg(xsec_z(ema(abs(ret_24h), 168)))"),
]


def main():
    C = P.load_context(4, 1)
    tg = C["target"]; mem = C["member"]; CL = C["CL"]; rows = C["rows"]
    dvol = C["ctx"]["dvol_24h"]
    print(f"[cap] {len(rows)} anchors | split member&CL by dvol_24h median per anchor", flush=True)
    print(f"{'candidate':52s} {'full':>8s} {'small':>8s} {'large':>8s} {'large/full':>10s}", flush=True)
    for tag, f in CANDS:
        fac = dsl.evaluate(dsl.parse(f), C["ctx"])
        full, small, large = [], [], []
        for t in rows:
            b = np.where(mem[t] & CL[t] & np.isfinite(tg[t]) & np.isfinite(fac[t]) & np.isfinite(dvol[t]))[0]
            if b.size < 16:
                continue
            med = np.median(dvol[t, b])
            lo = b[dvol[t, b] < med]; hi = b[dvol[t, b] >= med]
            full.append(P._ric(fac[t, b], tg[t, b]))
            if lo.size >= 8:
                small.append(P._ric(fac[t, lo], tg[t, lo]))
            if hi.size >= 8:
                large.append(P._ric(fac[t, hi], tg[t, hi]))
        ff = np.nanmean(full); ss = np.nanmean(small); ll = np.nanmean(large)
        print(f"{f[:52]:52s} {ff:>8.4f} {ss:>8.4f} {ll:>8.4f} {ll/ff:>10.2f}", flush=True)


if __name__ == "__main__":
    main()
