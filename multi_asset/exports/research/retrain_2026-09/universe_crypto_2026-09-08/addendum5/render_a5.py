import json
W=["2024","2025","2026->cut","2024->26"]
def g(t): return json.load(open("results/%s.json"%t))
rows=[]
print("=== per_gross mean bps/anchor | anchor Sharpe ===")
print("%-10s %-32s %-32s"%("window","BASE U-PIT  s42 / s2027","CRYPTO      s42 / s2027"))
for w in W:
    a=[g("M1_UPIT_prod_s%s_ccal"%s)["windows"][w]["per_gross"] for s in ("42","2027")]
    b=[g("M1_UCRYPTO_prod_s%s_ccal"%s)["windows"][w]["per_gross"] for s in ("42","2027")]
    print("%-10s %+.4f / %+.4f  S %.2f/%.2f   %+.4f / %+.4f  S %.2f/%.2f"%(w,a[0]["mean_bps_anchor"],a[1]["mean_bps_anchor"],a[0]["sharpe_anchor"],a[1]["sharpe_anchor"],b[0]["mean_bps_anchor"],b[1]["mean_bps_anchor"],b[0]["sharpe_anchor"],b[1]["sharpe_anchor"]))
print()
print("=== by_L 2.0 (NAV caliber) ===")
K=["arith_pct_yr","cagr_pct","vol_pct_yr_anchor","sharpe_daily","worst_day_pct","worst_month_pct","worst_month","months_negative","days_below_2pct","days_below_5pct","maxdd_pct","maxdd_span_days","maxdd_recovered"]
for w in ["2024->26","2026->cut"]:
    print("-- window %s --"%w)
    for k in K:
        a=[g("M1_UPIT_prod_s%s_ccal"%s)["windows"][w]["by_L"]["2.0"].get(k) for s in ("42","2027")]
        b=[g("M1_UCRYPTO_prod_s%s_ccal"%s)["windows"][w]["by_L"]["2.0"].get(k) for s in ("42","2027")]
        f=lambda v: ("%.4g"%v if isinstance(v,(int,float)) else str(v))
        print("   %-22s BASE %-22s CRYPTO %-22s"%(k, f(a[0])+" / "+f(a[1]), f(b[0])+" / "+f(b[1])))
print()
print("=== boot CI on levels (2024->26) ===")
for t in ["M1_UPIT_prod_s42_ccal","M1_UPIT_prod_s2027_ccal","M1_UCRYPTO_prod_s42_ccal","M1_UCRYPTO_prod_s2027_ccal"]:
    b=g(t)["windows"]["2024->26"]["boot"]; print("   %-28s mean_ci95 %s p>0 %.3f"%(t,b["mean_ci95"],b["p_mean_gt0"]))
print()
print("=== form (2026->cut) ===")
for t in ["M1_UPIT_prod_s42_ccal","M1_UCRYPTO_prod_s42_ccal"]:
    f=g(t)["windows"]["2026->cut"]["form"]; print("   %-28s nsel %.1f nmember %.1f turnover %.4f cost %.4f carry %.4f"%(t,f["nsel_mean"],f["nmember_mean"],f["turnover_per_gross_mean"],f["cost_ex_bps_per_gross_mean"],f["carry_paid_bps_per_gross_mean"]))
print()
print("=== slices (sigma_fund terciles), 2024->26, s42 ===")
for t in ["M1_UPIT_prod_s42_ccal","M1_UCRYPTO_prod_s42_ccal"]:
    sl=g(t).get("slices",{})
    for k,v in sl.items():
        if isinstance(v,dict) and "terciles" in json.dumps(v)[:200] or True:
            print("   %s :: %s"%(t,k), json.dumps(v)[:400])
