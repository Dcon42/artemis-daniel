"""
Alignment tests for data_pipeline.build_panel forward returns.

These tests pin the forward-return alignment so a future look-ahead /
off-by-one bug is caught. The alignment tests run on a small, synthetic,
CONTIGUOUS daily panel (no date gaps); a final test drops one middle day to
confirm build_panel measures forward returns by calendar day, not row offset.

Spec under test (per symbol, sorted by date):
    ret_Nd = forward N-day return = (close[t+N] - close[t]) / close[t]
The last N rows of each horizon are undefined (NaN) because there is no
future data, and forward returns must never cross symbol boundaries.
"""

import numpy as np
import pandas as pd

from data_pipeline import build_panel


# Horizons computed by build_panel and the column each one populates.
HORIZONS = {1: "ret_1d", 7: "ret_7d", 14: "ret_14d", 21: "ret_21d"}

N_DAYS = 25  # consecutive calendar days per symbol


def _close_series(symbol: str) -> np.ndarray:
    """
    Distinct, known, increasing-but-irregular close prices.

    Every value is unique (no equal or round-repeating numbers) so an
    off-by-one slip would change a computed return and be caught. Symbol B
    is offset into a disjoint price band so cross-symbol leakage is also
    detectable by value, not just by NaN.
    """
    base = 100.0 if symbol == "AAA" else 500.0
    # Irregular non-constant increments -> all close prices distinct, and
    # every consecutive pairwise return differs.
    increments = np.array(
        [0, 1, 2, 3, 5, 7, 4, 6, 9, 8,
         11, 13, 10, 12, 17, 14, 19, 16, 23, 18,
         29, 20, 31, 22, 37],
        dtype=float,
    )
    return base + np.cumsum(increments)


def _make_frames():
    """Build minimal contiguous ohlcv + funding_features frames for 2 symbols."""
    symbols = ["AAA", "BBB"]
    dates = pd.date_range("2021-01-01", periods=N_DAYS, freq="D")

    ohlcv_rows = []
    funding_rows = []
    closes = {}
    for sym in symbols:
        close = _close_series(sym)
        closes[sym] = close
        for i, d in enumerate(dates):
            c = close[i]
            ohlcv_rows.append(
                {
                    "symbol": sym,
                    "date": d,
                    "open": c,
                    "high": c,
                    "low": c,
                    "close": c,
                    "volume": 1000.0,
                    "quote_volume": 1000.0 * c,
                }
            )
            funding_rows.append({"symbol": sym, "date": d})

    ohlcv = pd.DataFrame(
        ohlcv_rows,
        columns=["symbol", "date", "open", "high", "low",
                 "close", "volume", "quote_volume"],
    )
    funding_features = pd.DataFrame(funding_rows, columns=["symbol", "date"])
    return ohlcv, funding_features, closes, dates


def _expected_forward_return(close: np.ndarray, t: int, n: int) -> float:
    """Independent reference: (close[t+n] - close[t]) / close[t]."""
    return (close[t + n] - close[t]) / close[t]


def _panel_for_symbol(panel: pd.DataFrame, sym: str) -> pd.DataFrame:
    return (
        panel[panel["symbol"] == sym]
        .sort_values("date")
        .reset_index(drop=True)
    )


# ---------------------------------------------------------------------------
# Invariant 1: interior forward returns match an independent computation
# ---------------------------------------------------------------------------
def test_forward_returns_match_independent_computation():
    ohlcv, funding_features, closes, _ = _make_frames()
    panel = build_panel(funding_features, ohlcv)

    for sym, close in closes.items():
        sub = _panel_for_symbol(panel, sym)
        for n, col in HORIZONS.items():
            for t in range(N_DAYS - n):  # interior rows where ret is defined
                expected = _expected_forward_return(close, t, n)
                actual = sub[col].iloc[t]
                assert np.isclose(actual, expected), (
                    f"{sym} {col} at row {t}: got {actual!r}, "
                    f"expected {expected!r}"
                )


# ---------------------------------------------------------------------------
# Invariant 2: the trailing N rows of each horizon are NaN (no future data)
# ---------------------------------------------------------------------------
def test_trailing_rows_are_nan_per_horizon():
    ohlcv, funding_features, closes, _ = _make_frames()
    panel = build_panel(funding_features, ohlcv)

    for sym in closes:
        sub = _panel_for_symbol(panel, sym)
        for n, col in HORIZONS.items():
            tail = sub[col].iloc[N_DAYS - n:]
            assert tail.isna().all(), (
                f"{sym} {col}: expected last {n} rows NaN, got {tail.tolist()}"
            )
            # And the row immediately before the tail must be defined.
            assert not np.isnan(sub[col].iloc[N_DAYS - n - 1]), (
                f"{sym} {col}: row {N_DAYS - n - 1} should be defined"
            )


# ---------------------------------------------------------------------------
# Invariant 3: no cross-symbol leakage at the boundary
# ---------------------------------------------------------------------------
def test_no_cross_symbol_leakage():
    ohlcv, funding_features, closes, _ = _make_frames()
    panel = build_panel(funding_features, ohlcv)

    # Symbol A's final row has no next-day price within A, so ret_1d is NaN.
    # If forward returns leaked across symbols it would (wrongly) use B's
    # first close and produce a finite number instead.
    a = _panel_for_symbol(panel, "AAA")
    last_ret_1d = a["ret_1d"].iloc[-1]
    assert np.isnan(last_ret_1d), (
        f"AAA last ret_1d should be NaN (no cross-symbol leakage), "
        f"got {last_ret_1d!r}"
    )

    # Stronger check: the finite value that leakage would produce must NOT appear.
    leaked = (closes["BBB"][0] - closes["AAA"][-1]) / closes["AAA"][-1]
    assert not np.isclose(last_ret_1d, leaked, equal_nan=False), (
        "AAA last ret_1d matches the cross-symbol leaked value"
    )


# ---------------------------------------------------------------------------
# Invariant 4: a gap breaks the forward return whose endpoint lands on it
# (regression guard for build_panel's calendar-day reindex, Fix 2)
# ---------------------------------------------------------------------------
GAP_POS = 12  # calendar position of the middle day dropped from symbol AAA


def test_gap_breaks_spanning_forward_return():
    """
    Drop one middle daily candle and confirm a forward return whose N-day-ahead
    endpoint lands on the missing day is NaN -- not a return silently measured
    over the wrong number of calendar days (the pre-fix row-shift bug). A horizon
    on the same row whose endpoint clears the gap stays finite.
    """
    ohlcv, funding_features, closes, dates = _make_frames()

    # Drop one middle day for AAA only; BBB stays contiguous as a control.
    gap_date = dates[GAP_POS]
    keep = ~((ohlcv["symbol"] == "AAA") & (ohlcv["date"] == gap_date))
    ohlcv_gapped = ohlcv[keep].reset_index(drop=True)

    panel = build_panel(funding_features, ohlcv_gapped)
    a = _panel_for_symbol(panel, "AAA")

    # The dropped day is absent from the panel entirely.
    assert (a["date"] == gap_date).sum() == 0

    # Row right before the gap: its 1-day-ahead endpoint IS the missing day, so
    # ret_1d must be NaN. Under the old row-shift code this was a finite
    # 2-calendar-day return mislabeled as a 1-day return.
    before = a.loc[a["date"] == dates[GAP_POS - 1]].iloc[0]
    assert np.isnan(before["ret_1d"]), (
        f"ret_1d whose endpoint is the gap day should be NaN, "
        f"got {before['ret_1d']!r}"
    )

    # Same row, a horizon whose 7-day-ahead endpoint clears the gap is finite.
    assert np.isfinite(before["ret_7d"]), (
        f"ret_7d not landing on the gap should be finite, got {before['ret_7d']!r}"
    )

    # Control: the untouched symbol's first row is still fully defined.
    b = _panel_for_symbol(panel, "BBB")
    assert np.isfinite(b["ret_1d"].iloc[0])


if __name__ == "__main__":
    test_forward_returns_match_independent_computation()
    test_trailing_rows_are_nan_per_horizon()
    test_no_cross_symbol_leakage()
    test_gap_breaks_spanning_forward_return()
    print("OK: all alignment tests passed")
