#!/usr/bin/env python3
"""r19 STEP 3 (T2/T3) — compare every outside-trackF consumer's archived output (BEFORE) with its re-run on the
corrected labels / corrected lookup (AFTER). Archive shas are asserted against the repo copies first. For each pair:
targeted tables for the claims the programme's documents cite, plus a generic recursive numeric diff.
PREREG_r19 §4 reading rules applied where a rule exists (GATE B RULE W admissibility, L1 ordering)."""
import json, hashlib, os, time, math
import numpy as np
U="/workspace/uplift_2026-09-11"; R19=U+"/r19_trackF_reindex"
def sha(p): return hashlib.sha256(open(p,'rb').read()).hexdigest()
ARCH={ # archived output -> sha as committed in the research repo (verified locally before this ran)
 U+"/r3_gates/regime_composition.json":"26313bafe2c093a1be0c9e1577a2afb0ee8e943a677a83b42e68041c48253a32",
 U+"/r4p3/RESULT_P3.json":"126dc559eecca7772a6a0588543fd8c726f006252e183f15faa555a0e29d6a0e",
 U+"/r4p3/RESULT_P3B.json":"34880d6a6237a0af131ea70334bd93d65b2e3cf24bbbc28fff29a451822d8e5c",
 U+"/r8_inbook/REGIME_GIVEBACK.json":"b02c7fbd13a45bede47729081ec19e5e52cdc047d3210d3ebf870658ab6994aa",
 U+"/r6j1/j1_regime.json":"dcc160f4e7ea64e0143c05bf5f72f1478080a0b77e47847498615880c51a8b9a",
 U+"/r7f2/R7_FUEL_RECEIPT.json":"fe09e11e25f4c2deedd4832b021219a8b6f6bbbf61c19177ac8fa5ec734eee83",
 U+"/r7f2/R7_FINAL.json":"92110f257feb867953a6866db67fed046e2d69568a8bfe79caa751af60b7f92b",
 U+"/r7f2/R7_SCREEN.json":"7145c39e9aaacf4d20fe0fd542b475dc363964d28c434079eb6365cdd4c5338c",
 U+"/r7f2/R7_SCREEN2.json":"0c1c4f7f33a1156ef1c86ce036888a70c994edd9a5bfc4ad5c0f609bd79c4bff",
 U+"/r7f2/R7_SPEC.json":"d3687a34a2538547d0a84f7c1978138374dbd06be375bea8ce5aa47db9852b4d",
 U+"/r7f2/R7_WITHINYEAR.json":"dac06d922e0185aa4ca30b566adff2e3750dec96a2c4b620255179b8e6fa1954"}
for p,s in ARCH.items(): assert sha(p)==s, (p, sha(p))
print("archived consumer outputs match repo copies: 11/11")
PAIRS={"regcomp":(U+"/r3_gates/regime_composition.json",R19+"/out_r3_gates/regime_composition.json"),
       "j1_regime":(U+"/r6j1/j1_regime.json",R19+"/out_r6j1/j1_regime.json"),
       "regime_gb":(U+"/r8_inbook/REGIME_GIVEBACK.json",R19+"/out_r8_inbook/REGIME_GIVEBACK.json"),
       "p3_an":(U+"/r4p3/RESULT_P3.json",R19+"/out_r4p3/RESULT_P3.json"),
       "p3_b":(U+"/r4p3/RESULT_P3B.json",R19+"/out_r4p3/RESULT_P3B.json"),
       "r7_fuel":(U+"/r7f2/R7_FUEL_RECEIPT.json",R19+"/out_r7f2/R7_FUEL_RECEIPT.json"),
       "r7_screen":(U+"/r7f2/R7_SCREEN.json",R19+"/out_r7f2/R7_SCREEN.json"),
       "r7_screen2":(U+"/r7f2/R7_SCREEN2.json",R19+"/out_r7f2/R7_SCREEN2.json"),
       "r7_spec":(U+"/r7f2/R7_SPEC.json",R19+"/out_r7f2/R7_SPEC.json"),
       "r7_withinyear":(U+"/r7f2/R7_WITHINYEAR.json",R19+"/out_r7f2/R7_WITHINYEAR.json"),
       "r7_final":(U+"/r7f2/R7_FINAL.json",R19+"/out_r7f2/R7_FINAL.json")}
J={k:(json.load(open(a)),json.load(open(b))) for k,(a,b) in PAIRS.items()}
OUT={"utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),"self_sha256":sha(__file__),"archive_sha256":ARCH,
     "after_sha256":{k:sha(b) for k,(a,b) in PAIRS.items()},"tables":{},"generic_diff":{}}
def leaves(o,p=""):
    if isinstance(o,dict):
        for k,v in o.items(): yield from leaves(v,p+"/"+str(k))
    elif isinstance(o,list):
        for i,v in enumerate(o): yield from leaves(v,p+f"[{i}]")
    else: yield p,o
def gdiff(a,b,skip=("self_sha256","utc","read_utc","path","built_utc")):
    A=dict(leaves(a)); B=dict(leaves(b)); n=0; ch=[];
    for k,v in A.items():
        if any(s in k for s in skip): continue
        n+=1; w=B.get(k,"<missing>")
        if isinstance(v,(int,float)) and isinstance(w,(int,float)) and not isinstance(v,bool):
            if not (math.isclose(v,w,rel_tol=0,abs_tol=1e-12) or (isinstance(v,float) and isinstance(w,float) and math.isnan(v) and math.isnan(w))): ch.append((k,v,w,abs(v-w)))
        elif v!=w: ch.append((k,v,w,float('nan')))
    ch.sort(key=lambda x: -(x[3] if x[3]==x[3] else 1e18))
    return {"n_leaves":n,"n_changed":len(ch),"top":[{"path":k,"before":v,"after":w} for k,v,w,_ in ch[:40]]}
for k,(a,b) in J.items(): OUT["generic_diff"][k]=gdiff(a,b)
print("\n##### generic diff: leaves / changed")
for k,v in OUT["generic_diff"].items(): print(f"  {k:14s} {v['n_changed']:6d} / {v['n_leaves']:6d}")

# ---------- GATE B (regcomp) ----------
A,B=J["regcomp"]; T={}
print("\n##### GATE B regime_composition: before -> after")
WINS=["FROZEN_2025-03-01..2026-08-10_20Z","2024on..2026-08-10","F23_2023-01-01..2026-08-10","FULLCYCLE_postwarm..2026-08-10","FULLCYCLE_postwarm_ALL(incl 08-31)","REF_full_history_all_anchors","REF_full_history_LABELLED_only"]
for key,tag in (("labelling_expanding_median_round2","A"),("labelling_fullsample_median_contrast","B")):
    T[tag]={"REF_before":A[key]["_REFERENCE_MIX_LLLHHLHH"],"REF_after":B[key]["_REFERENCE_MIX_LLLHHLHH"],"windows":{}}
    print(f"== labelling {tag}  REF mix {A[key]['_REFERENCE_MIX_LLLHHLHH']} -> {B[key]['_REFERENCE_MIX_LLLHHLHH']}")
    for w in WINS:
        a=A[key][w]; b=B[key][w]
        T[tag]["windows"][w]={f:(a[f],b[f]) for f in ("n_anchors","n_labelled","HH_share_of_labelled","L1_vs_reference","maxcell_share","eff_cells_1_over_sumsq","LL","LH","HL","HH","UNLAB","g_mean_bps","sharpe")}
        print(f"  {w:38s} n={a['n_anchors']:5d} HH_lab {a['HH_share_of_labelled']}->{b['HH_share_of_labelled']}  L1 {a['L1_vs_reference']}->{b['L1_vs_reference']}  eff {a['eff_cells_1_over_sumsq']}->{b['eff_cells_1_over_sumsq']}  after cells LL {b['LL']} LH {b['LH']} HL {b['HL']} HH {b['HH']}")
# RULE W admissibility (n>=5000 and L1<=0.15 in BOTH labellings) and L1 ordering among the 4 candidate windows
CAND=WINS[:4]
def adm(D):
    return {w: bool(D["labelling_expanding_median_round2"][w]["n_anchors"]>=5000 and D["labelling_expanding_median_round2"][w]["L1_vs_reference"]<=0.15 and D["labelling_fullsample_median_contrast"][w]["L1_vs_reference"]<=0.15) for w in CAND}
def order(D,key): return sorted(CAND, key=lambda w: D[key][w]["L1_vs_reference"])
T["RULE_W_admissible"]={"before":adm(A),"after":adm(B)}
T["L1_order"]={tag:{"before":order(A,key),"after":order(B,key)} for key,tag in (("labelling_expanding_median_round2","A"),("labelling_fullsample_median_contrast","B"))}
T["L1_order_reversed"]={tag:(T["L1_order"][tag]["before"]!=T["L1_order"][tag]["after"]) for tag in ("A","B")}
T["meta"]={"before":A["_meta"],"after":B["_meta"]}
print("RULE W admissible:", T["RULE_W_admissible"]); print("L1 order A:", T["L1_order"]["A"]); print("L1 order B:", T["L1_order"]["B"]); print("L1 order reversed:", T["L1_order_reversed"])
print("meta:", A["_meta"], "->", B["_meta"])
OUT["tables"]["GATE_B"]=T

# ---------- r6 judge1 Q4 ----------
A,B=J["j1_regime"]; T={"meta":{"before":{k:A["meta"][k] for k in ("label_regression_identical","label_regression_n","umask_rows_carried_forward")},"after":{k:B["meta"][k] for k in ("label_regression_identical","label_regression_n","umask_rows_carried_forward")}},"windows":{}}
print("\n##### r6 judge1 Q4 (j1_regime): before -> after;  meta", T["meta"])
for w in A["windows"]:
    a=A["windows"][w]; b=B["windows"][w]
    T["windows"][w]={f:(a[f],b[f]) for f in ("n","n_labelled","HH_of_labelled","L1_vs_full_history","sig_fund_mean","sig_fund_med","disp24_med","shares")}
    print(f"  {w:40s} n={a['n']:5d} HH {a['HH_of_labelled']}->{b['HH_of_labelled']} L1 {a['L1_vs_full_history']}->{b['L1_vs_full_history']} sigf_med {a['sig_fund_med']}->{b['sig_fund_med']} shares(after) {b['shares']}")
OUT["tables"]["R6_J1"]=T

# ---------- r8 REGIME_GIVEBACK ----------
A,B=J["regime_gb"]; T={"regime_n":(A["regime_n"],B["regime_n"]),"arms":{}}
print("\n##### r8 REGIME_GIVEBACK: regime_n", A["regime_n"], "->", B["regime_n"])
same_unc=all(A["arms"][k]["rho_g_to_A0_full"]==B["arms"][k]["rho_g_to_A0_full"] and A["arms"][k]["rho_marginal_to_A0_full"]==B["arms"][k]["rho_marginal_to_A0_full"] and A["arms"][k]["giveback"]==B["arms"][k]["giveback"] for k in A["arms"])
T["label_independent_fields_identical"]=same_unc; print("unconditional rho / giveback identical:", same_unc)
for arm in A["arms"]:
    a=A["arms"][arm]; b=B["arms"][arm]; T["arms"][arm]={c:{f:(a["cells"][c][f],b["cells"][c][f]) for f in ("n","rho_g","rho_marginal","dg")} for c in ("LL","LH","HL","HH")}
    print(f"  {arm:16s} " + " ".join(f"{c}: dg {a['cells'][c]['dg']:+.4f}->{b['cells'][c]['dg']:+.4f} rm {a['cells'][c]['rho_marginal']:+.3f}->{b['cells'][c]['rho_marginal']:+.3f}" for c in ("LL","LH","HL","HH")))
OUT["tables"]["R8_GB"]=T

# ---------- r4p3 RESULT_P3 ----------
A,B=J["p3_an"]; T={"Q2_rho_by_cell":{},"Q3":{},"label_independent_identical":{"Q1_pairwise_rho":A["Q1_pairwise_rho"]==B["Q1_pairwise_rho"],"Q1_levels":A["Q1_levels"]==B["Q1_levels"],"Q2_rho_by_year":A["Q2_rho_by_year"]==B["Q2_rho_by_year"]}}
print("\n##### r4p3 RESULT_P3: label-independent sections identical:", T["label_independent_identical"])
for sd in A["Q2_rho_by_cell"]:
    T["Q2_rho_by_cell"][sd]={}
    for c in ("UNLAB","LL","LH","HL","HH","LABELLED_ALL","FROZEN_WINDOW"):
        a=A["Q2_rho_by_cell"][sd][c]; b=B["Q2_rho_by_cell"][sd][c]; ka=[k for k in a["SR"] if k.startswith("A0")][0]; kx=[k for k in a["SR"] if k.startswith("XIB")][0]
        T["Q2_rho_by_cell"][sd][c]={"n":(a["n"],b["n"]),"rho_A0_AMI":(a["rho_A0_AMI"],b["rho_A0_AMI"]),"rho_A0_XIB":(a["rho_A0_XIB"],b["rho_A0_XIB"]),"rho_XIB_AMI":(a["rho_XIB_AMI"],b["rho_XIB_AMI"]),
                                     "SR_A0":(a["SR"][ka],b["SR"][ka]),"SR_XIB":(a["SR"][kx],b["SR"][kx]),"SR_AMI":(a["SR"]["AMI"],b["SR"]["AMI"]),"N_eff":(a["N_eff_eig"],b["N_eff_eig"])}
        print(f"  {sd:6s} {c:14s} n {a['n']:5d}->{b['n']:5d} rho(A0,AMI) {a['rho_A0_AMI']:+.4f}->{b['rho_A0_AMI']:+.4f} rho(A0,XIB) {a['rho_A0_XIB']:+.4f}->{b['rho_A0_XIB']:+.4f} SR_A0 {a['SR'][ka]:+.3f}->{b['SR'][ka]:+.3f} SR_AMI {a['SR']['AMI']:+.3f}->{b['SR']['AMI']:+.3f} SR_XIB {a['SR'][kx]:+.3f}->{b['SR'][kx]:+.3f}")
for sd in A["Q3_portfolio"]:
    T["Q3"][sd]={}
    for pr in ("A0+AMI","A0+XIB+AMI"):
        a=A["Q3_portfolio"][sd]["REGIME_CONDITIONAL"][pr]; b=B["Q3_portfolio"][sd]["REGIME_CONDITIONAL"][pr]
        T["Q3"][sd][pr]={f:(a[f],b[f]) for f in ("SR_static_mvo_insample","SR_cellwise_mvo_insample","SR_cellwise_walkforward","n_wf","n_wf_cellfitted","SR_cellwise_wf_CI95_k0","cell_weights_insample")}
        print(f"  Q3 {sd} {pr:12s} SR static {a['SR_static_mvo_insample']:.4f}->{b['SR_static_mvo_insample']:.4f}  cellwise-IS {a['SR_cellwise_mvo_insample']:.4f}->{b['SR_cellwise_mvo_insample']:.4f}  cellwise-WF {a['SR_cellwise_walkforward']:.4f}->{b['SR_cellwise_walkforward']:.4f} CI {a['SR_cellwise_wf_CI95_k0']}->{b['SR_cellwise_wf_CI95_k0']}")
OUT["tables"]["R4P3_P3"]=T
A,B=J["p3_b"]; T={"C_percell":{},"label_independent_identical":{"A":A["A_pairwise_Neff"]==B["A_pairwise_Neff"],"B":A["B_peryear_arith"]==B["B_peryear_arith"],"D":A["D_ranker_hole"]==B["D_ranker_hole"]}}
print("\n##### r4p3 RESULT_P3B: label-independent identical:", T["label_independent_identical"])
for sd in A["C_percell_portfolio"]:
    T["C_percell"][sd]={}
    for c in ("UNLAB","LL","LH","HL","HH","FROZEN_WINDOW","2024on"):
        a=A["C_percell_portfolio"][sd][c]; b=B["C_percell_portfolio"][sd][c]; T["C_percell"][sd][c]={f:(a[f],b[f]) for f in ("n","rho","SR_A0","SR_AMI","SR_port","N_eff")}
        print(f"  {sd:6s} {c:14s} n {a['n']:5d}->{b['n']:5d} rho {a['rho']:+.4f}->{b['rho']:+.4f} SR_A0 {a['SR_A0']:+.3f}->{b['SR_A0']:+.3f} SR_AMI {a['SR_AMI']:+.3f}->{b['SR_AMI']:+.3f} SR_port {a['SR_port']:+.3f}->{b['SR_port']:+.3f}")
OUT["tables"]["R4P3_P3B"]=T

# ---------- r7 FUEL gauge ----------
A,B=J["r7_fuel"]; T={"carried_mask_rows":(A["carried_mask_rows"],B["carried_mask_rows"]),"prefix_regression_bitwise":(A["prefix_regression_bitwise"],B["prefix_regression_bitwise"]),"monthly":{}}
print("\n##### r7 FUEL gauge: carried rows", A["carried_mask_rows"], "->", B["carried_mask_rows"], "; prefix regression", A["prefix_regression_bitwise"], "->", B["prefix_regression_bitwise"])
for k in sorted(A["monthly"]):
    T["monthly"][k]=(A["monthly"][k],B["monthly"][k])
    if k>="2026-01": print(f"  {k} sig_fund_med {A['monthly'][k]['sig_fund_med']:.4f}->{B['monthly'][k]['sig_fund_med']:.4f}  mean8h {A['monthly'][k]['mean8h_bps_mean']:+.4f}->{B['monthly'][k]['mean8h_bps_mean']:+.4f}")
FA=np.load(U+"/r7f2/R7_FUEL.npz",allow_pickle=True); FB=np.load(R19+"/out_r7f2/R7_FUEL.npz",allow_pickle=True)
for tag,key in (("inc","inc"),("x0910","x0910")):
    a=FA[key]; b=FB[key]; T[f"{tag}_sig_fund_changed_rows"]=int((~np.isclose(a[:,2],b[:,2],equal_nan=True)).sum()); T[f"{tag}_n"]=int(len(a))
    T[f"{tag}_median_all"]=(float(np.nanmedian(a[:,2])),float(np.nanmedian(b[:,2])))
    print(f"  {tag}: sig_fund rows changed {T[f'{tag}_sig_fund_changed_rows']}/{len(a)}; median all {T[f'{tag}_median_all'][0]:.4f}->{T[f'{tag}_median_all'][1]:.4f}")
T["x0910_sept_median"]=(float(np.nanmedian(FA["x0910"][FA["x0910"][:,0]>=1788220800,2])),float(np.nanmedian(FB["x0910"][FB["x0910"][:,0]>=1788220800,2])))
print(f"  SEP 2026 (>=2026-09-01) sig_fund median {T['x0910_sept_median'][0]:.4f}->{T['x0910_sept_median'][1]:.4f}")
OUT["tables"]["R7_FUEL"]=T

# ---------- r7 SCREEN (§3 main table, §3.1 regime cells) ----------
A,B=J["r7_screen"]; T={"window":(A["window"],B["window"]),"tercile_breaks":(A["tercile_breaks"],B["tercile_breaks"]),"rows":{}}
print("\n##### r7 SCREEN: window", A["window"], "->", B["window"], "; tercile breaks", A["tercile_breaks"], "->", B["tercile_breaks"])
for name in A["rows"]:
    T["rows"][name]=[]
    for ra,rb in zip(A["rows"][name],B["rows"][name]):
        r={"path":os.path.basename(ra["path"]),"n":(ra["n"],rb["n"]),"sharpe_full":(ra["sharpe_full"],rb["sharpe_full"]),"beta_sig":(ra["beta_sig_bps_per_SD"],rb["beta_sig_bps_per_SD"]),"t_nw30":(ra["t_nw30"],rb["t_nw30"]),
           "beta_norm":(ra["beta_norm_ownSD_per_SD"],rb["beta_norm_ownSD_per_SD"]),"T0_sharpe":(ra["tercile"]["T0"]["sharpe"],rb["tercile"]["T0"]["sharpe"]),"T2_sharpe":(ra["tercile"]["T2"]["sharpe"],rb["tercile"]["T2"]["sharpe"]),
           "T0_n":(ra["tercile"]["T0"]["n"],rb["tercile"]["T0"]["n"]),"rho_A0":(ra["rho_A0"],rb["rho_A0"]),"regime":{c:((ra["regime"].get(c) or {}).get("rho_A0"),(rb["regime"].get(c) or {}).get("rho_A0"),(ra["regime"].get(c) or {}).get("n"),(rb["regime"].get(c) or {}).get("n"),(ra["regime"].get(c) or {}).get("sharpe"),(rb["regime"].get(c) or {}).get("sharpe")) for c in ("LL","LH","HL","HH")}}
        T["rows"][name].append(r)
        print(f"  {name[:34]:34s} {r['path'][:26]:26s} Sh {ra['sharpe_full']:.3f}->{rb['sharpe_full']:.3f} beta {ra['beta_sig_bps_per_SD']:+.3f}->{rb['beta_sig_bps_per_SD']:+.3f} (t {ra['t_nw30']:+.2f}->{rb['t_nw30']:+.2f}) T0 Sh {ra['tercile']['T0']['sharpe']:+.3f}->{rb['tercile']['T0']['sharpe']:+.3f} T2 {ra['tercile']['T2']['sharpe']:+.3f}->{rb['tercile']['T2']['sharpe']:+.3f} rhoA0 T0 {ra['rho_A0']['T0']}->{rb['rho_A0']['T0']}")
        print("      regime rho(A0) LL/LH/HL/HH: " + " ".join(f"{c} {r['regime'][c][0]}->{r['regime'][c][1]} (n {r['regime'][c][2]}->{r['regime'][c][3]})" for c in ("LL","LH","HL","HH")))
OUT["tables"]["R7_SCREEN"]=T

# ---------- r7 SCREEN2 ----------
A,B=J["r7_screen2"]; T={"common_n":(A["common_n"],B["common_n"]),"tercile_breaks":(A["tercile_breaks"],B["tercile_breaks"]),"regime":{},"tercile":{},"coverage_identical":A["coverage"]==B["coverage"]}
print("\n##### r7 SCREEN2: common n", A["common_n"], "->", B["common_n"], "; breaks", A["tercile_breaks"], "->", B["tercile_breaks"], "; coverage identical", T["coverage_identical"])
for k in A["rows"]:
    a=A["rows"][k]; b=B["rows"][k]
    T["regime"][k]={c:((a["regime"].get(c) or {}).get("rho_A0"),(b["regime"].get(c) or {}).get("rho_A0"),(a["regime"].get(c) or {}).get("sharpe"),(b["regime"].get(c) or {}).get("sharpe"),(a["regime"].get(c) or {}).get("n"),(b["regime"].get(c) or {}).get("n")) for c in ("LL","LH","HL","HH")}
    T["tercile"][k]={t:((a["tercile"][t]["sharpe"],b["tercile"][t]["sharpe"]),(a["tercile"][t]["rho_A0"],b["tercile"][t]["rho_A0"])) for t in ("T0","T1","T2")}
    T["tercile"][k]["beta_log"]=(a["beta_log"],b["beta_log"]); T["tercile"][k]["t_log"]=(a["t_log"],b["t_log"]); T["tercile"][k]["sharpe"]=(a["sharpe"],b["sharpe"])
    print(f"  {k:20s} Sh {a['sharpe']:.3f}->{b['sharpe']:.3f} b_log {a['beta_log']:+.4f}->{b['beta_log']:+.4f} (t {a['t_log']:+.2f}->{b['t_log']:+.2f}) T0 {a['tercile']['T0']['sharpe']:+.3f}->{b['tercile']['T0']['sharpe']:+.3f} T2 {a['tercile']['T2']['sharpe']:+.3f}->{b['tercile']['T2']['sharpe']:+.3f} | rho cells " + " ".join(f"{c} {T['regime'][k][c][0]}->{T['regime'][k][c][1]}" for c in ("LL","LH","HL","HH")))
T["bands_A0"]=(A["bands_A0"],B["bands_A0"]); T["curve_A0"]=(A["curve_A0"],B["curve_A0"])
OUT["tables"]["R7_SCREEN2"]=T

# ---------- r7 FINAL ----------
A,B=J["r7_final"]; T={"today_percentiles":(A["today_percentiles"],B["today_percentiles"]),"postwarm_sigma":(A["postwarm_sigma"],B["postwarm_sigma"]),"mechanism":(A["mechanism"],B["mechanism"]),"decisive":{},"spec":{}}
print("\n##### r7 FINAL: today percentiles", A["today_percentiles"], "->", B["today_percentiles"]); print("  postwarm sigma", A["postwarm_sigma"], "->", B["postwarm_sigma"]); print("  mechanism corr(sigma_fund, basis dispersion)", A["mechanism"], "->", B["mechanism"])
for k in A["decisive"]:
    a=A["decisive"][k]; b=B["decisive"][k]; T["decisive"][k]={"n":(a["n"],b["n"]),"T0":(a["T0"],b["T0"]),"T2":(a["T2"],b["T2"]),"gap":(a["gap_T2_minus_T0"],b["gap_T2_minus_T0"])}
    print(f"  {k:18s} T0 Sh {a['T0']['sharpe']:+.3f}{a['T0']['ci95']}->{b['T0']['sharpe']:+.3f}{b['T0']['ci95']}  T2 {a['T2']['sharpe']:+.3f}->{b['T2']['sharpe']:+.3f}  gap {a['gap_T2_minus_T0']['point']:+.3f}{a['gap_T2_minus_T0']['ci95']} P>0 {a['gap_T2_minus_T0']['P_gt0']:.3f} -> {b['gap_T2_minus_T0']['point']:+.3f}{b['gap_T2_minus_T0']['ci95']} P>0 {b['gap_T2_minus_T0']['P_gt0']:.3f}")
for (ba,a),(bb,b) in zip(A["spec"].items(),B["spec"].items()):   # band names embed the tercile break, which moved
    T["spec"][f"{ba} -> {bb}"]={f:(a[f],b[f]) for f in ("n","A0_mean_g","A0_sd_g","A0_sharpe")}
    print(f"  spec band {ba:28s}->{bb:28s} n {a['n']}->{b['n']} A0 Sharpe {a['A0_sharpe']:+.3f}->{b['A0_sharpe']:+.3f}")
OUT["tables"]["R7_FINAL"]=T
# spec / withinyear: generic diff only (structure varies) + print top changes
for k in ("r7_spec","r7_withinyear"):
    g=OUT["generic_diff"][k]; print(f"\n##### {k}: {g['n_changed']}/{g['n_leaves']} leaves changed; largest:")
    for t in g["top"][:12]: print("   ", t["path"], t["before"], "->", t["after"])
json.dump(OUT, open(R19+"/receipts/RECEIPT_r19_consumers_compare.json","w"), indent=1, default=str)
print("\nCOMPARE_DONE")
