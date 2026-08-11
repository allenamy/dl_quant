"""metrics 面板的因果门 + 信息门。判据先写死, 再看数字。

G1 因果门(ROADMAP §F 门2): 特征 vs 【未来 24h 收益】的 |xsec rank-IC| < 0.15。
    >0.15 = 泄漏签名。ch31 那个含 11h 未来的通道在此处会亮红。
G1b 时移对称检验: 同一特征对【过去 24h】与【未来 24h】的 IC。真因果特征对过去的
    相关可以任意大(它本来就由过去构成), 对未来的相关必须小。若对未来的显著大于
    对过去的 —— 那是"未来泄进来了", 比绝对阈值更灵敏。
G2 信息门: 单特征对 Y4 的 |IC| > 0.01 才算有信息。
判读: G1 任一特征 FAIL ⇒ 整族退回, 不训练。
"""
import numpy as np

P = np.load("/workspace/data/panel_targets.npz", allow_pickle=True)
M = np.load("/workspace/data/metrics_hourly.npz", allow_pickle=True)
X, FEAT = M["X"], [str(f) for f in M["feats"]]
Y4, MEM = P["Y4"], P["MEMBER110"]
T, N = Y4.shape
print(f"面板 {T:,}×{N}  特征 {len(FEAT)}  滞后 {int(M['lag_ms'])/3600000:.0f}h")

def zr(v):
    m = np.isfinite(v); o = np.full(len(v), np.nan)
    if m.sum() < 10: return o
    r = np.argsort(np.argsort(v[m])).astype(float)
    o[m] = (r - r.mean()) / (r.std() + 1e-12); return o

def xic(a, b):
    za, zb = zr(a), zr(b)
    m = np.isfinite(za) & np.isfinite(zb)
    return float((za[m] * zb[m]).mean()) if m.sum() >= 20 else np.nan

# 4h 锚点行
rows = [i for i in range(48, T - 30) if i % 4 == 0]
# 未来/过去 24h 累计收益, 由 Y4 拼(与目标同源同口径)
fut = np.full((T, N), np.nan, np.float32)
pas = np.full((T, N), np.nan, np.float32)
for i in rows:
    if i + 24 < T:
        s = np.zeros(N); ok = np.ones(N, bool)
        for k in range(6):
            v = Y4[i + 4 * k]; ok &= np.isfinite(v); s += np.where(np.isfinite(v), v, 0)
        fut[i] = np.where(ok, s, np.nan)
    if i - 24 >= 0:
        s = np.zeros(N); ok = np.ones(N, bool)
        for k in range(1, 7):
            v = Y4[i - 4 * k]; ok &= np.isfinite(v); s += np.where(np.isfinite(v), v, 0)
        pas[i] = np.where(ok, s, np.nan)

samp = rows[::5]
print(f"\n{'特征':16s} {'IC vs 未来24h':>14s} {'IC vs 过去24h':>14s} {'IC vs Y4':>10s}  判决")
red = []
for k, nm in enumerate(FEAT):
    f_ = np.nanmean([xic(np.where(MEM[i], X[i, :, k], np.nan),
                         np.where(MEM[i], fut[i], np.nan)) for i in samp])
    p_ = np.nanmean([xic(np.where(MEM[i], X[i, :, k], np.nan),
                         np.where(MEM[i], pas[i], np.nan)) for i in samp])
    y_ = np.nanmean([xic(np.where(MEM[i], X[i, :, k], np.nan),
                         np.where(MEM[i], Y4[i], np.nan)) for i in rows[::3]])
    bad = abs(f_) > 0.15
    asym = abs(f_) > abs(p_) + 0.05          # 对未来的相关显著超过对过去 = 可疑
    if bad or asym: red.append(nm)
    print(f"{nm:16s} {f_:+14.4f} {p_:+14.4f} {y_:+10.4f}  "
          f"{'★★★ 泄漏' if bad else ('★ 不对称可疑' if asym else ('信息' if abs(y_) > 0.01 else '—'))}")
print(f"\nG1 因果门: 最大 |IC vs 未来| = "
      f"{max(abs(np.nanmean([xic(np.where(MEM[i],X[i,:,k],np.nan),np.where(MEM[i],fut[i],np.nan)) for i in samp])) for k in range(len(FEAT))):.4f}"
      f"  阈值 0.15  ⇒ {'FAIL' if red else 'PASS'}")
print(f"G1b 不对称: {red if red else '无'}")
