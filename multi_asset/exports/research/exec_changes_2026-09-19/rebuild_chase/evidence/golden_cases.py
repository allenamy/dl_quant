# ── REBUILD golden cases (shared verbatim with live/tests_chase_policy.py §12) ─────────────────
_GW = {"chase": 1.0, "no_chase": 1.0}
_GW2 = {"chase": 0.5, "no_chase": 0.5}
GOLDEN_CASES = [
    ("in_sample_6",   dict(residuals=[("AAAUSDT", -60.0), ("BBBUSDT", -50.0), ("CCCUSDT", -40.0), ("DDDUSDT", -30.0),
                                      ("EEEUSDT", -20.0), ("FFFUSDT", -15.0)],
                           seed="A1785600000", book_net_usdt=180.0, book_gross_usdt=4300.0, net_basis="g", weights=_GW)),
    ("two_sided_14",  dict(residuals=[(f"M{i:02d}USDT", (-1) ** i * (7.0 + 3.1 * i)) for i in range(14)],
                           seed="A1789215839", book_net_usdt=-55.5, book_gross_usdt=9800.0, net_basis="g", weights=_GW2)),
    ("tilted_fill",   dict(residuals=[(f"T{i}USDT", -(90.0 - 7.0 * i)) for i in range(10)],
                           seed="A1788452640", book_net_usdt=420.0, book_gross_usdt=12000.0, net_basis="g", weights=_GW2)),
    ("stop_excluded", dict(residuals=[("AAAUSDT", -60.0), ("BBBUSDT", -50.0), ("LSKUSDT", 85.77), ("DDDUSDT", -30.0),
                                      ("EEEUSDT", -20.0), ("FFFUSDT", -15.0)],
                           seed="A1789302239", book_net_usdt=100.0, book_gross_usdt=5000.0, net_basis="g", weights=_GW,
                           exclude={"LSKUSDT": "per_name_stop"})),
    ("min_eligible",  dict(residuals=[("AAAUSDT", -100.0)], seed="A1785600000", book_net_usdt=100.0,
                           book_gross_usdt=4300.0, net_basis="g", weights=_GW)),
    ("no_book_net",   dict(residuals=[(f"S{i}USDT", -10.0) for i in range(6)], seed="A1785600000", book_net_usdt=None,
                           book_gross_usdt=4300.0, net_basis="UNAVAILABLE", weights=_GW)),
    ("tilt_abort",    dict(residuals=[(f"B{i}USDT", -400.0) for i in range(6)], seed="A1785600000", book_net_usdt=0.0,
                           book_gross_usdt=4300.0, net_basis="g", weights=_GW)),
]
