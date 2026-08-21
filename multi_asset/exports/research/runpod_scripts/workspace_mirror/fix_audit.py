p = "/workspace/book_audit.py"
s = open(p).read()

old = '''def stats(A, cost_bps):
    ret, turn = [], []
    prev = None
    for j in range(len(rows)):
        w = A[j]
        if not np.isfinite(w).any(): prev = None; continue
        y = Yraw[rows[j]]
        ok = np.isfinite(w) & np.isfinite(y)
        ret.append(float(np.nansum(w[ok] * y[ok])))
        if prev is not None:
            t = np.nansum(np.abs(np.nan_to_num(w) - np.nan_to_num(prev))) / 2.0
        else:
            t = np.nansum(np.abs(np.nan_to_num(w))) / 2.0
        turn.append(float(t)); prev = w
    ret = np.array(ret); turn = np.array(turn)
    net = ret - turn * cost_bps / 1e4
    npy = len(rows) / max(len(set(YEAR[rows].tolist())), 1)
    f = lambda x: x.mean() / (x.std() + 1e-12) * np.sqrt(npy)
    return dict(n=len(ret), ret=ret.mean(), turn=turn.mean(), gross=f(ret), net=f(net))'''

new = '''ANCHORS_PER_YEAR = 2190.0   # 4h 锚的【真实】交易频率; 不可用共同锚子集的密度代替

def stats(A, cost_bps):
    """2026-08-09 修两处口径:
    (1) 年化基数用真实 2190/年, 而非共同锚子集密度(原实现低估夏普 sqrt(2190/366)=2.45x);
    (2) 换手【只在真正相邻的锚(行距==4)上测】—— 跨了几天的两个共同锚之间的漂移不是一次调仓。
    """
    ret, turn = [], []
    for j in range(len(rows)):
        w = A[j]
        if not np.isfinite(w).any():
            continue
        y = Yraw[rows[j]]
        ok = np.isfinite(w) & np.isfinite(y)
        if ok.sum() < 25:
            continue
        ret.append(float(np.nansum(w[ok] * y[ok])))
        if j > 0 and (rows[j] - rows[j - 1]) == 4 and np.isfinite(A[j - 1]).any():
            turn.append(float(np.nansum(np.abs(np.nan_to_num(w) - np.nan_to_num(A[j - 1]))) / 2.0))
    ret = np.array(ret)
    tm = float(np.mean(turn)) if turn else float("nan")
    drag = (tm if tm == tm else 0.0) * cost_bps / 1e4
    f = lambda mu, sd: mu / (sd + 1e-12) * np.sqrt(ANCHORS_PER_YEAR)
    return dict(n=len(ret), n_turn=len(turn), ret=ret.mean(), turn=tm,
                gross=f(ret.mean(), ret.std()), net=f(ret.mean() - drag, ret.std()))'''

assert old in s, "stats 锚点未匹配"
s = s.replace(old, new, 1)

o2 = 'print("%-26s %7.4f %8.2e %8.2f %8.2f %8.2f" % (name, a["turn"], a["ret"], a["gross"], a["net"], b["net"]), flush=True)'
n2 = 'print("%-26s %7.4f %6d %8.2e %8.2f %8.2f %8.2f" % (name, a["turn"], a["n_turn"], a["ret"], a["gross"], a["net"], b["net"]), flush=True)'
assert o2 in s, "打印行未匹配"
s = s.replace(o2, n2, 1)

o3 = '%-26s %7s %8s %8s %8s %8s" % ("\u817f", "\u6362\u624b", "\u6bdb\u5747\u503c", "\u6bdbSharpe", "\u51c0@3.63", "\u51c0@5.8")'
n3 = '%-26s %7s %6s %8s %8s %8s %8s" % ("\u817f", "\u6362\u624b", "n\u6362", "\u6bdb\u5747\u503c", "\u6bdbSharpe", "\u51c0@3.63", "\u51c0@5.8")'
assert o3 in s, "表头未匹配: " + repr([l for l in s.split(chr(10)) if "毛Sharpe" in l])
s = s.replace(o3, n3, 1)

open(p, "w").write(s)
print("口径已修: 年化 2190 + 换手仅相邻锚")
