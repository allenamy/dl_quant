"""#64 代币解锁/归属日程(供给侧) —— 数据获取 + 特征构建。
源: DefiLlama emissions dataset(免费): /emissionsProtocolsList + /emissions/{slug}
机制: 解锁 = 可预期的供给冲击。与价量族的独立性来自【它不是价格的函数】——
     日程是合约写死的, 在 t 时刻【公开可知】⇒ 用未来日程不是前视, 是 ex-ante 公开信息。
★ 泄漏风险(必须记录): unlockUsdChart 的 USD 值内嵌了价格, 且 DefiLlama 可能事后修订日程。
  ⇒ 特征优先用【日程形状】(时间+代币量比例), USD 值仅作辅助并单独打门。
"""
import urllib.request, json, time, os, sys
OUT = "/workspace/data/unlocks_raw"
os.makedirs(OUT, exist_ok=True)
UA = {"User-Agent": "research/1.0"}
def get(u, tries=3):
    for i in range(tries):
        try:
            return json.load(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=30))
        except Exception as e:
            if i == tries-1: raise
            time.sleep(2*(i+1))
lst = get("https://defillama-datasets.llama.fi/emissionsProtocolsList")
print("协议 %d 个" % len(lst), flush=True)
ok = err = skip = 0
for i, slug in enumerate(lst):
    f = f"{OUT}/{slug}.json"
    if os.path.exists(f): skip += 1; continue
    try:
        r = get(f"https://defillama-datasets.llama.fi/emissions/{slug}")
        keep = {k: r.get(k) for k in ("name","gecko_id","protocolCategory","unlockUsdChart","supplyMetrics")}
        keep["metadata"] = r.get("metadata")
        keep["documentedData"] = (r.get("documentedData") or {}).get("data")
        json.dump(keep, open(f, "w"))
        ok += 1
    except Exception as e:
        err += 1
        if err <= 5: print("  ERR %s %s" % (slug, type(e).__name__), flush=True)
    if (i+1) % 50 == 0: print("  %d/%d  ok=%d err=%d skip=%d" % (i+1, len(lst), ok, err, skip), flush=True)
    time.sleep(0.15)
print("FETCH_DONE ok=%d err=%d skip=%d -> %s" % (ok, err, skip, OUT), flush=True)
