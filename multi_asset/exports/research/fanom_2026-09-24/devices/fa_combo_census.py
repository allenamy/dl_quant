"""fa_combo_census.py — combination-layer census for the fanom / fresh roots (lead brief 2026-09-26): which reading consumed
which legs / model artifacts, and therefore which fund_replay CHANNELS (RN8, EMA) reach it. History is NOT recomputed; each
reading is annotated with its channel exposure and the fund_replay_guard state of its inputs (every pre-09-25 input is
UNSTAMPED, which the guard treats as not-clean).

Method: every *.json under each variant dir (and the two roots' receipts) is scanned for the LITERAL sha256 of the known artifacts
below; identity is by sha, never by path or name (two different files are both called NEWS_FEATURES.npz). A dir that references
none of them is reported UNRESOLVED, not clean.
Channels: legs 18999e16 / 486dfe37 carry RN8 (fresh_legs.py L80-81 last_rate/last_iv) AND the fund-leg z ZFD + base built from
fund_replay ema_acc (EMA channel, fa_ema_probe c07dfeaf); models bound to NEWS_FEATURES a490c294 carry the EMA/fund_now channel
in their training features. The ladder2 ends swap RN8 only (from 9ee5886f), so their EMA channel stays contaminated.
usage: python fa_combo_census.py <out.json> <dir> [<dir> ...]
"""
import os, sys, json, re, hashlib, time
KNOWN = {
    "18999e169c6b68546271f8194fd74eaa79041d1967ba44df978f4cbea33d6bd5": ("legs NEW_S", {"RN8": "CONTAM", "EMA_ZFD": "CONTAM"}),
    "486dfe3765c5ef37adb6270b7c1642305bf0d6b1da9d1930b0963e8249f524d8": ("legs FRESH", {"RN8": "CONTAM", "EMA_ZFD": "CONTAM"}),
    "9ee5886f37d1727c306d0fb692d2cad1e6400ae13f19d5cd4e280dc59f208f65": ("legs NC(news2)", {"RN8": "CLEAN", "EMA_ZFD": "CLEAN_NC_STATE"}),
    "744bc48ea1e2f3b823d4ae9268d4d791606319691da23bfa9f1d98eedf232ab9": ("KING_OOF NEW_S", {"MODEL_FEATURES": "CONTAM"}),
    "4345541e4450b24a0bdf59c11219f2e5dda4476fa6f934f2d6a0569fd7b21951": ("KING_OOF FRESH", {"MODEL_FEATURES": "CONTAM"}),
    "a10b872506ca60afcd0f69b0e43d17a548cdd7c6956075000aac954b21e3df9a": ("KING_OOF NC(news2)", {"MODEL_FEATURES": "CLEAN_NC_STATE"}),
    "aa6e30550d8079a3b6df8a4d98a7dd638c3178af1db294ab351b79ed99a91d08": ("F10 NEW_S s42", {"MODEL_FEATURES": "CONTAM"}),
    "a37dab090f173fe6b9a84d811bafe13e94226ac72cb6a367af3a18e1c69232e6": ("F10 NEW_S s2027", {"MODEL_FEATURES": "CONTAM"}),
    "1d16cbed6f2498c397173a0ca8438de1e06b79eab3c4ceda1ef57b7c88184bda": ("F10 FRESH s42", {"MODEL_FEATURES": "CONTAM"}),
    "b4a972457406147c7db9b1aaa9450518aa481d01a709b240f1a1220afdc51a65": ("F10 FRESH s2027", {"MODEL_FEATURES": "CONTAM"}),
    "2af48f7c84bfd5de2df83fa1266455ca718558a80ae68017de444b510a592d51": ("F10 NC s42", {"MODEL_FEATURES": "CLEAN_NC_STATE"}),
    "7d60074078368ddee25b301e157edb711896caef9efef1479559ebd41b486503": ("F10 NC s2027", {"MODEL_FEATURES": "CLEAN_NC_STATE"}),
    "a490c294d90e0cdb2bb1dca503f3468dc1a4384396e3f7bae3e3020e161f79ac": ("NEWS_FEATURES news (a490c294)", {"MODEL_FEATURES": "CONTAM"}),
    "3c886a2bc0ff65c10b7e0a621c9468210bbd77ef58c90e625f0a29354d63c4d8": ("NEWS_FEATURES news2 (3c886a2b)", {"MODEL_FEATURES": "CLEAN_NC_STATE"}),
    "8a73588f": ("fund_replay (prefix)", {"DIRECT_FUND_REPLAY": "CONTAM"}),
}
LEGS_ROOT = {"18999e169c6b68546271f8194fd74eaa79041d1967ba44df978f4cbea33d6bd5": "NEW_S",
             "486dfe3765c5ef37adb6270b7c1642305bf0d6b1da9d1930b0963e8249f524d8": "FRESH",
             "9ee5886f37d1727c306d0fb692d2cad1e6400ae13f19d5cd4e280dc59f208f65": "NC"}
ROOT_STATE = {"NEW_S": "CONTAM", "FRESH": "CONTAM", "NC": "CLEAN_NC_STATE"}


def by_binding(d):
    """precise path: a FA_COMBO receipt names the base legs actually used and, for ladder arms, where each array came from.
    Returns None when no such receipt exists (then the sha grep, which can include listed-but-unused donors, is used)."""
    p = os.path.join(d, "FA_COMBO_RECEIPT.json")
    if not os.path.exists(p): return None
    j = json.load(open(p)); b = j.get("legs_f10_binding") or {}
    base = LEGS_ROOT.get(b.get("legs_sha256"))
    if base is None: return None
    src = (j.get("LADDER") or {}).get("per_array_source") or {}
    donor = LEGS_ROOT.get((j.get("LADDER") or {}).get("donor_legs_sha256"))
    root_of = lambda arr: donor if src.get(arr) == "donor" else base
    return {"base_legs_root": base, "per_array_root": {a: root_of(a) for a in ("KZ", "WL", "ZFD", "RN8", "F10")},
            "channels": {"RN8": [ROOT_STATE[root_of("RN8")]], "EMA_ZFD": [ROOT_STATE[root_of("ZFD")]],
                         "MODEL_FEATURES": sorted({ROOT_STATE[root_of("KZ")], ROOT_STATE[root_of("F10")]})},
            "method": "FA_COMBO_RECEIPT legs_f10_binding + LADDER.per_array_source"}
HEX = re.compile(r"[0-9a-f]{64}")


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


out = {"device": "fa_combo_census.py", "self_sha256": sha(os.path.abspath(__file__)), "argv": sys.argv,
       "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "dirs": {}}
for top in sys.argv[2:]:
    for d, _, fs in sorted(os.walk(top)):
        js = [f for f in fs if f.endswith(".json")]
        if not js: continue
        hits = {}
        for f in js:
            t = open(os.path.join(d, f), errors="replace").read()
            for k, (lab, _) in KNOWN.items():
                if (len(k) == 64 and k in t) or (len(k) < 64 and re.search(k + r"[0-9a-f]{56}", t)):
                    hits.setdefault(lab, []).append(f)
        if not hits: continue
        ch = {}
        for k, (lab, c) in KNOWN.items():
            if lab in hits:
                for kk, v in c.items(): ch.setdefault(kk, set()).add(v)
        bb = by_binding(d)
        out["dirs"][d] = {"artifacts": {k: sorted(set(v)) for k, v in hits.items()},
                          "channels": bb["channels"] if bb else {k: sorted(v) for k, v in ch.items()},
                          "method": bb["method"] if bb else "literal-sha grep over the dir's json (may include listed-but-unused donors)",
                          "per_array_root": bb["per_array_root"] if bb else None,
                          "fund_replay_guard": "UNSTAMPED (input predates the 2026-09-25 stamp; not re-run)"}
json.dump(out, open(sys.argv[1] + ".tmp", "w"), indent=1); os.replace(sys.argv[1] + ".tmp", sys.argv[1])
back = json.load(open(sys.argv[1])); assert back["self_sha256"] == out["self_sha256"]
print("FA_COMBO_CENSUS dirs=%d sha=%s" % (len(out["dirs"]), sha(sys.argv[1])))
for d, v in out["dirs"].items():
    print("  %-70s %s" % (d[-70:], json.dumps(v["channels"])))
