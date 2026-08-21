"""W2 · 第二路径复算(pandas 实现, 与 two_book_allocation.py 不同代码路径; 同作者 ⇒ 只能抓实现滑误, 不等于独立装置)。
读同一对瘦身序列, 以 DataFrame merge 对齐, 重算主口径: 单书夏普 / ρ / 逐年夏普 / w=0.5,0.7 混合夏普 / 判据 c1 与逐年计数, 与 JSON 逐项比对(容差 2e-3)。
用法: python3 w2_second_check.py
"""
import os, json, numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); RES = os.path.join(HERE, "results")
J = json.load(open(os.path.join(RES, "two_book_allocation_2026-08-21.json")))
G = J["meta"]["G"]; ANN = np.sqrt(2190)
L = np.load(os.path.join(RES, "series", "w2_live_series_slim.npz"), allow_pickle=True)
Wd = np.load(os.path.join(RES, "series", "w2_wide_series_slim.npz"), allow_pickle=True)
cols = [str(c) for c in Wd["cols"]]
dl = pd.DataFrame({"ts": L["ts"].astype("int64"), "net": L["S1_net"], "carry": L["S1_carry"], "g0": L["S0_gross"]})
dw = pd.DataFrame(Wd["d30_n2_c42_rec"], columns=cols); dw0 = pd.DataFrame(Wd["S0_rec"], columns=cols)
dw["ts"] = dw["ts"].astype("int64"); dw0["ts"] = dw0["ts"].astype("int64")
dw = dw.merge(dw0[["ts", "gross_total"]].rename(columns={"gross_total": "g0"}), on="ts")
d = dl.merge(dw[["ts", "net", "g0"]].rename(columns={"net": "wnet", "g0": "wg0"}), on="ts").sort_values("ts").reset_index(drop=True)
d["yr"] = pd.to_datetime(d["ts"], unit="s").dt.year
d["L"] = (d["net"] - d["carry"].fillna(0)) / d["g0"]; d["W"] = d["wnet"] / d["wg0"]
def sh(x): return float(x.mean() / x.std(ddof=1) * ANN)
P = J["variants"]["primary"]; fails = []
def cmp(name, got, exp, tol=2e-3):
    ok = abs(got - exp) <= tol; print(("OK  " if ok else "FAIL"), name, round(got, 4), "json", exp)
    if not ok: fails.append(name)
cmp("n_common", len(d), J["meta"]["coverage"]["common"]["n"], 0)
cmp("live_sharpe", sh(d["L"]), P["single"]["live"]["sharpe"]); cmp("wide_sharpe", sh(d["W"]), P["single"]["wide"]["sharpe"])
cmp("rho", float(d["L"].corr(d["W"])), P["rho"]["all_pearson"])
for y, g in d.groupby("yr"):
    cmp(f"live_sharpe_{y}", sh(g["L"]), P["single"]["live"]["by_year_sharpe"][str(y)]); cmp(f"wide_sharpe_{y}", sh(g["W"]), P["single"]["wide"]["by_year_sharpe"][str(y)])
    cmp(f"rho_{y}", float(g["L"].corr(g["W"])), P["rho"]["by_year"][str(y)])
maxS = max(sh(d["L"]), sh(d["W"]))
for w in (0.5, 0.6, 0.7, 0.8):
    b = (1 - w) * d["L"] + w * d["W"]; cmp(f"blend_sharpe_w{w}", sh(b), P["grid"][str(w)]["sharpe"])
    c1 = sh(b) >= maxS + 0.15; nb = sum(1 for y, g in d.groupby("yr") if sh((1 - w) * g["L"] + w * g["W"]) >= max(sh(g["L"]), sh(g["W"])))
    print("   crit w", w, "c1", c1, "json", P["grid"][str(w)]["criteria"]["c1_sharpe_ge_maxsingle_plus_0.15"], "| years_ge_max", nb, "json", P["grid"][str(w)]["criteria"]["years_ge_max_single"])
    if c1 != P["grid"][str(w)]["criteria"]["c1_sharpe_ge_maxsingle_plus_0.15"] or f"{nb}/5" != P["grid"][str(w)]["criteria"]["years_ge_max_single"]: fails.append(f"crit_w{w}")
print("SECOND_CHECK", "PASS" if not fails else f"FAIL {fails}")
