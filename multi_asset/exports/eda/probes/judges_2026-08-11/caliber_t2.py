"""Settle the T2 caliber: is Yraw (raw fwd return) identical across champion / N1b / S1 grids?
If yes, ic_pooled_raw IS the apples-to-apples cross-target comparison (residual-YR differs by
training target and is NOT comparable). Also check member/CL semantic identity to resolve why
gate f trips (spurious md5 vs genuine grid difference)."""
import sys, json, hashlib, numpy as np
sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/handoff")
import acceptance_battery as ab
M = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports/train"
THR = ab.THRESHOLDS


def h(a):
    return hashlib.md5(np.ascontiguousarray(a).tobytes()).hexdigest()[:8]


champ = ab.load_any(f"{M}/wideA_lamorth0_xattn_5yr", THR)
OUT = {"champion": dict(Yraw_md5=h(champ.Yraw), YR_md5=h(champ.YR), member_md5=champ.member_md5,
                        CL_md5=champ.CL_md5, ts_md5=champ.ts_md5,
                        member_cells=int(champ.member.sum()), CL_cells=int(champ.CL.sum()))}
cic_raw, _, _ = ab.ic_series(champ, champ.pred, champ.oos_rows, "Yraw")
cic_res, _, _ = ab.ic_series(champ, champ.pred, champ.oos_rows, "YR")
OUT["champion"]["ic_raw"] = round(float(np.mean(cic_raw)), 4)
OUT["champion"]["ic_resid"] = round(float(np.mean(cic_res)), 4)
print("champion raw IC", OUT["champion"]["ic_raw"], "resid IC", OUT["champion"]["ic_resid"], flush=True)

for tag, d in [("N1b", "wideA_n1b_multirel_c1"), ("S1", "wideA_s1_yr4k_c1")]:
    c = ab.load_any(f"{M}/{d}", THR)
    shared = np.intersect1d(c.oos_rows, champ.oos_rows)
    # candidate pred scored vs CHAMPION's Yraw on shared anchors (true apples-to-apples)
    ics = []
    for t in shared:
        b = np.where(c.member[t] & c.CL[t] & np.isfinite(c.pred[t]) & np.isfinite(champ.Yraw[t]))[0]
        if b.size >= THR["min_base"]:
            ic = ab.ricorr(c.pred[t, b], champ.Yraw[t, b])
            if np.isfinite(ic):
                ics.append(ic)
    OUT[tag] = dict(Yraw_md5=h(c.Yraw), YR_md5=h(c.YR), member_md5=c.member_md5, CL_md5=c.CL_md5,
                    ts_md5=c.ts_md5, member_cells=int(c.member.sum()), CL_cells=int(c.CL.sum()),
                    Yraw_eq_champ=bool(h(c.Yraw) == h(champ.Yraw)),
                    member_eq_champ=bool(c.member_md5 == champ.member_md5),
                    CL_eq_champ=bool(c.CL_md5 == champ.CL_md5),
                    ic_vs_champ_Yraw=round(float(np.mean(ics)), 4) if ics else None,
                    ic_own_resid_YR=round(float(np.mean(ab.ic_series(c, c.pred, c.oos_rows, "YR")[0])), 4),
                    shared_anchors=int(shared.size))
    print(tag, "Yraw==champ:", OUT[tag]["Yraw_eq_champ"], "member==:", OUT[tag]["member_eq_champ"],
          "CL==:", OUT[tag]["CL_eq_champ"], "| ic_vs_champ_Yraw:", OUT[tag]["ic_vs_champ_Yraw"],
          "own_resid:", OUT[tag]["ic_own_resid_YR"], flush=True)

json.dump(OUT, open("/tmp/0c_caliber_t2.json", "w"), indent=1, default=str)
print("SAVED", flush=True)
