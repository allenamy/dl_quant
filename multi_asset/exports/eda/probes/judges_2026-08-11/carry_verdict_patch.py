"""Record the breadth-robustness diagnostic + INCONCLUSIVE verdict on the HL carry A/B study."""
import json

MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
P = MA + "/exports/eda/hl_carry_ab.json"

j = json.load(open(P))
j["★_VERDICT"] = "INCONCLUSIVE — DO NOT USE THE ARM NUMBERS ABOVE FOR A DECISION"
j["why_inconclusive"] = {
    "problem": ("the long window (6830 anchors from 2023-05) is carried almost entirely by the ~30 "
                "coins the deep backfill happened to finish first — an arbitrary subset, not a "
                "designed universe. Requiring a genuinely broad cross-section (>=40 HL-funded "
                "members) leaves only 354 anchors, all after 2026-05-02, because that is where the "
                "60-day pull provides breadth."),
    "breadth_robustness_check": {
        "min_members_15": {"n_anchors": 6830, "from": "2023-05-12",
                           "A_net_pct_yr": 36.66, "B_net_pct_yr": 5.71, "ref_net_pct_yr": 34.06,
                           "A_price_pct_yr": 25.25},
        "min_members_40": {"n_anchors": 354, "from": "2026-05-02",
                           "A_net_pct_yr": -58.36, "B_net_pct_yr": -42.02, "ref_net_pct_yr": -54.55,
                           "A_price_pct_yr": -69.22},
        "reading": ("every arm flips sign and the price drift swings +25%/yr -> -69%/yr. Neither "
                    "window is trustworthy: the first is a thin arbitrary subset, the second is "
                    "two months of one regime. The carry-transfer ratio is not stable either "
                    "(A/ref 1.295 on the long window vs 0.74 on the short one).")},
    "also_unreconciled": ("this file's price drift (+25%/yr on the long window) disagrees in SIGN "
                          "with 0C's -11.5%/yr. Plausible causes: different universe (HL-covered "
                          "subset vs MEMBER110), different window (2023-05+ vs full history), and "
                          "the corrected-vs-broken factor. Not chased down, because the underlying "
                          "sample is not fit for the question yet."),
    "what_would_make_it_answerable": ("the deep funding backfill finishing all 177 HL perps "
                                      "(1171d each) — then a >=40-member cross-section exists back "
                                      "to 2023-05 and the arms can be compared on a stable "
                                      "universe. ETA a few hours from 2026-07-25 08:20 UTC; "
                                      "re-run this script unchanged."),
}
j["only_stable_observation"] = ("carry is positive in all three arms on both windows, and 口径 B "
                                "(HL-native ranking) collects MORE carry than 口径 A on both "
                                "(22.83 vs 11.41 long; 17.73 vs 10.85 short). That direction is "
                                "the one thing breadth does not flip — consistent with carry "
                                "concentrating where the venues agree. It is NOT sufficient to "
                                "pick an arm, because the price-drift leg dominates the net and "
                                "that is exactly what is unstable.")
json.dump(j, open(P, "w"), indent=1)
print("verdict recorded: INCONCLUSIVE pending the deep backfill")
