import json
f = "multi_asset/exports/eda/xattn2_adjudication.json"
d = json.load(open(f))
d["decision"] = "FAIL / TIE -> CLOSE (do NOT queue 5yr)"
d["reasoning"] = [
    "Pre-reg 'no fold worse' VIOLATED: fold2 delta -0.0059 (though NOT significant, CI[-0.018,+0.005] "
    "includes 0 = a noise wobble, not real degradation).",
    "Mean edge +0.0035 is WITHIN single-layer seed noise: x2 0.0983 is only +1.53 sigma above the "
    "single-layer seed mean 0.0944 and +0.001 above the seed CEILING 0.0973 -- a lucky single-layer seed "
    "could reach it. One xattn2 run at +1.53 sigma does NOT establish an edge over the seed band.",
    "The gain is a SINGLE-FOLD SPIKE: fold0 +0.0123 is the ONLY significant fold (CI excludes 0) and it "
    "sits at the overfit-suspect small/earliest test block (params:sample +13%); fold1 +0.0042 and fold2 "
    "-0.0059 are both non-significant. Depth-2 did NOT deliver a uniform regime-robust lift -- it fit fold0 "
    "better but not fold1/fold2 = the pre-flagged overfit signature.",
    "dyn-share ~0.95 (no static inflation) and per-fold dispersion actually LOWER (0.0103 vs 0.0174) -- so "
    "the arm is not 'broken', it is simply single-layer-EQUIVALENT within seed noise with an overfit-flavored "
    "fold0 spike.",
    "CONCLUSION: one message-passing iteration (n_xattn=1) is sufficient; a 2nd does NOT add regime-robust "
    "alpha and costs +13% params. Team lead's prior (tie leaning FAIL) CONFIRMED. Close; queue -> ARM-MIX/FinPFN."]
json.dump(d, open(f, "w"), indent=2, default=str)
print("decision:", d["decision"])
