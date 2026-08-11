def apply_no_trade_band(target: Dict[str, float], positions: Dict[str, float],
                        band_notional: float, exempt=()):
    """中性保持型免交易带(PROPOSAL_neutral_band_2026-08-10 SHA 8e499dac, 用户裁定 2026-08-10)。

    |target − current| ≤ band 的名字保持现仓(现仓为 0 则不开新小仓); 由此产生的书级净额残差
    只均摊到仍要交易的名字上 —— 未交易名字零扰动。这是与场所隐性地板带的全部差别: 隐带
    skip 而不恢复中性, 实测让书携带 max 2.1% 净敞口漂移(提案 §1)。
    exempt = 场所约束名(reduced / add_blocked / flatten_only): 原样通过且不参与摊派 ——
    对它们加常数会把 clamp 刚刚禁止的方向重新打开。
    band_notional ≤ 0 ⇒ 恒等直通(b=0 即回放保真门, 回放与实盘共用本函数)。
    不重归一: gross 因带住旧仓而漂移是【观测量】(回放 p5≈0.969 @b=.002); 重归一会把
    整本书重新交易掉(PREREG_turnover_shaping §1 教训)。
    交易集为空时净额残差保留并报告, 不强制归零 —— 整锚保持的书继承上锚中性。
    """
    stats = {"applied": band_notional > 0, "band_notional": float(band_notional),
             "n_in": len(target), "n_held": 0, "n_traded": 0, "n_exempt": 0,
             "resid_before": 0.0, "adj_per_name": 0.0, "net_after": None}
    out = {s: float(t) for s, t in target.items()}
    if band_notional <= 0 or not target:
        stats["n_traded"] = len(target)
        stats["net_after"] = float(sum(out.values())) if out else 0.0
        return out, stats
    traded = []
    for s, t in target.items():
        if s in exempt:
            stats["n_exempt"] += 1
            continue
        cur = float((positions or {}).get(s, 0.0) or 0.0)
        if abs(float(t) - cur) <= band_notional:
            out[s] = cur
            stats["n_held"] += 1
        else:
            traded.append(s)
    stats["n_traded"] = len(traded)
    resid = float(sum(out.values()))
    stats["resid_before"] = resid
    if traded:
        adj = resid / len(traded)
        stats["adj_per_name"] = adj
        for s in traded:
            out[s] = float(out[s]) - adj
    stats["net_after"] = float(sum(out.values()))
    return out, stats
