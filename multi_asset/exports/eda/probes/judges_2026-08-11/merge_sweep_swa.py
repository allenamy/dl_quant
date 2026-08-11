"""Merge S4-sweep logs (/tmp/sweep_<menu>.log) + SWA logs (/tmp/swa_<menu>.log)
into the 3-way table (shipped / S4 / best-SWA) + the D5 aggregate verdict.
Run:  python merge_sweep_swa.py /tmp   (dir holding sweep_*.log + swa_*.log)
"""
import sys, os, re, glob

FL = r"([+-]\d+\.\d+)"   # signed float

def parse_sweep(path):
    """-> dict(shipped_cd, shipped_dn, s4_pick, s4_cd, s4_dn, s4_delta, oracle_cd, oracle_gap)"""
    d = {}
    for line in open(path):
        line = line.rstrip("\n")
        if line.startswith("SHIPPED"):
            f = re.findall(FL, line)
            if len(f) >= 2: d["shipped_cd"], d["shipped_dn"] = float(f[0]), float(f[1])
        elif line.startswith("S4 "):
            pk = re.search(r"(raw|ema) ep\d+", line); f = re.findall(FL, line)
            if pk: d["s4_pick"] = pk.group(0)
            if len(f) >= 3: d["s4_cd"], d["s4_dn"], d["s4_delta"] = float(f[0]), float(f[1]), float(f[2])
        elif line.startswith("ORACLE"):
            f = re.findall(FL, line)
            if len(f) >= 1: d["oracle_cd"] = float(f[0])
        elif "oracle gap" in line:
            f = re.findall(FL, line)
            if f: d["oracle_gap"] = float(f[0])
    return d

def parse_swa(path):
    """-> dict(shipped_cd, rows={name:(cd,dn,beta,delta)}, best_name, best_cd)"""
    d = {"rows": {}}
    for line in open(path):
        line = line.rstrip("\n")
        if line.startswith("SHIPPED"):
            f = re.findall(FL, line)
            if f: d["shipped_cd"] = float(f[0])
        elif line.startswith("SWA-"):
            nm = line.split()[0]; f = re.findall(FL, line)
            if len(f) >= 4: d["rows"][nm] = (float(f[0]), float(f[1]), float(f[2]), float(f[3]))
        elif line.startswith("best SWA"):
            m = re.search(r"best SWA = (\S+) cd=" + FL, line)
            if m: d["best_name"], d["best_cd"] = m.group(1), float(m.group(2))
    return d

def main():
    d = sys.argv[1] if len(sys.argv) > 1 else "/tmp"
    menus = sorted({os.path.basename(p).replace("sweep_", "").replace("swa_", "")[:-4]
                    for p in glob.glob(f"{d}/sweep_*.log") + glob.glob(f"{d}/swa_*.log")})
    print(f"{'menu':16s} {'shipCD':>8s} | {'S4pick':>8s} {'S4cd':>8s} {'ΔS4':>8s} | "
          f"{'bestSWA':>12s} {'SWAcd':>8s} {'ΔSWA':>8s} | {'SWA≥S4':>6s} {'oracle':>7s}")
    agg = {"s4_win": 0, "swa_win": 0, "swa_ge_s4": 0, "n": 0}
    for m in menus:
        sw = parse_sweep(f"{d}/sweep_{m}.log") if os.path.exists(f"{d}/sweep_{m}.log") else {}
        sa = parse_swa(f"{d}/swa_{m}.log") if os.path.exists(f"{d}/swa_{m}.log") else {}
        ship = sw.get("shipped_cd", sa.get("shipped_cd", float("nan")))
        s4cd = sw.get("s4_cd", float("nan")); s4d = sw.get("s4_delta", float("nan"))
        bswa = sa.get("best_name", "-"); bcd = sa.get("best_cd", float("nan"))
        dswa = bcd - ship if bcd == bcd and ship == ship else float("nan")
        ge = "YES" if (bcd == bcd and s4cd == s4cd and bcd >= s4cd) else "no"
        agg["n"] += 1
        agg["s4_win"] += int(s4d > 0) if s4d == s4d else 0
        agg["swa_win"] += int(dswa > 0) if dswa == dswa else 0
        agg["swa_ge_s4"] += int(ge == "YES")
        print(f"{m:16s} {ship:+8.4f} | {sw.get('s4_pick','-'):>8s} {s4cd:+8.4f} {s4d:+8.4f} | "
              f"{bswa:>12s} {bcd:+8.4f} {dswa:+8.4f} | {ge:>6s} {sw.get('oracle_gap',float('nan')):+7.4f}")
    print(f"\nAGG over {agg['n']} menus: S4 beats shipped {agg['s4_win']}/{agg['n']} | "
          f"SWA beats shipped {agg['swa_win']}/{agg['n']} | SWA≥S4 {agg['swa_ge_s4']}/{agg['n']}")
    print("D5 rule: selection rule needs >=3/5 held-out wins + no >0.003 harm on strong months.")

if __name__ == "__main__":
    main()
