#!/workspace/venv/bin/python
"""Independent check of no_trade_within_60s rows: pure csv scan; for 10 random such rows (seed 20260905) print the last
trade before target and the first trade after target, and assert that no trade has T in [target, target+60s]."""
import csv, io, json, random, zipfile, urllib.request, hashlib, datetime as dt
ROOT="/workspace/review_scratch/markout_cdn"; BASE="https://data.binance.vision/data/futures/um/daily/aggTrades/{sym}/{fname}"
def iso(ms): return dt.datetime.fromtimestamp(ms/1000, tz=dt.timezone.utc).strftime("%H:%M:%S.%f")[:-3]
marks=json.load(open(f"{ROOT}/out/marks.json")); rows=json.load(open(f"{ROOT}/input/pending_fills.json"))["rows"]
nt=[r for r in rows if marks[str(r["trade_id"])]["status"]=="no_trade_within_60s"]
rng=random.Random(20260905); sample=rng.sample(nt, 10); n_ok=0
for r in sample:
    m=marks[str(r["trade_id"])]; fname=m["source"].split()[-1]
    data=urllib.request.urlopen(BASE.format(sym=r["symbol"], fname=fname), timeout=180).read()
    sha=hashlib.sha256(data).hexdigest(); z=zipfile.ZipFile(io.BytesIO(data)); name=[n for n in z.namelist() if n.endswith(".csv")][0]
    target=int(round(r["fill_ts"]*1000))+60000; hi=target+60000; before=None; after=None; inwin=0; n=0
    with io.TextIOWrapper(z.open(name), encoding="utf-8", newline="") as f:
        for line in csv.reader(f):
            if line[0]=="agg_trade_id": continue
            T=int(line[5]); n+=1
            if T<target: before=line
            elif T<=hi: inwin+=1
            elif after is None: after=line
    ok=(inwin==0); n_ok+=int(ok)
    print(f"--- trade_id={r[chr(116)+chr(114)+chr(97)+chr(100)+chr(101)+chr(95)+chr(105)+chr(100)]} {r[chr(115)+chr(121)+chr(109)+chr(98)+chr(111)+chr(108)]} day={r[chr(100)+chr(97)+chr(121)]} target={target} ({iso(target)}Z) window_end={iso(hi)}Z archive={fname} sha={sha[:16]}.. {chr(115)+chr(104)+chr(97)} {chr(79)+chr(75) if sha==m[chr(102)+chr(105)+chr(108)+chr(101)+chr(95)+chr(115)+chr(104)+chr(97)+chr(50)+chr(53)+chr(54)] else chr(77)+chr(73)+chr(83)+chr(77)+chr(65)+chr(84)+chr(67)+chr(72)} rows={n}")
    print(f"    last before target : {before[0] if before else None} px={before[1] if before else None} T={before[5] if before else None} ({iso(int(before[5])) if before else None}Z) lag={(int(before[5])-target)/1000 if before else None:.3f}" if before else "    last before target : none")
    print(f"    first after window : {after[0] if after else None} px={after[1] if after else None} T={after[5] if after else None} ({iso(int(after[5])) if after else None}Z) lag={(int(after[5])-target)/1000 if after else None:.3f}" if after else "    first after window : none (end of file)")
    print(f"    trades inside [target, target+60s]: {inwin} -> {chr(65)+chr(71)+chr(82)+chr(69)+chr(69) if ok else chr(77)+chr(73)+chr(83)+chr(77)+chr(65)+chr(84)+chr(67)+chr(72)}")
print(f"SUMMARY: {n_ok}/{len(sample)} no_trade rows confirmed (zero trades inside the 60 s window)")
