"""
Data Pipeline for Funding-Rate Mean Reversion Strategy
=======================================================
Pulls from Hyperliquid (no API key needed, works in the US):
  1. Universe of all available perp markets
  2. Historical funding rates (hourly snapshots)
  3. OHLCV daily candles for each perp

Usage:
  python data_pipeline.py                # pull all data with defaults
  python data_pipeline.py --days 180     # last 180 days
  python data_pipeline.py --top 30       # top 30 perps by volume
"""

import time
import json
import argparse
import requests
import pandas as pd
from datetime import datetime, timedelta, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
DATA_DIR = Path(__file__).parent / "data"
HL_INFO_URL = "https://api.hyperliquid.xyz/info"

# Rate limit: Hyperliquid allows 1200 weight/min. fundingHistory=20, candleSnapshot=20.
# With 0.5s sleep between calls we stay well under.
SLEEP_BETWEEN_CALLS = 0.5


def hl_post(payload: dict) -> dict | list:
    """POST to Hyperliquid info endpoint with basic retry."""
    for attempt in range(3):
        try:
            resp = requests.post(HL_INFO_URL, json=payload, timeout=30)
            resp.raise_for_status()
            return resp.json()
        except (requests.RequestException, json.JSONDecodeError) as e:
            if attempt == 2:
                raise
            print(f"    Retry {attempt+1} after error: {e}")
            time.sleep(2)


# ---------------------------------------------------------------------------
# 1. Get all available perps and pick top N by 24h volume
# ---------------------------------------------------------------------------
def get_top_perp_symbols(top_n: int = 30) -> list[str]:
    """
    Fetch Hyperliquid perp universe ranked by current 24h USD volume.
    Returns coin names like ['BTC', 'ETH', 'SOL', ...].

    KNOWN BIASES:
    - Survivorship bias: this pulls the LIVE universe; coins delisted before
      this call are silently excluded. Their returns (often large losses) are
      never recorded, inflating measured factor returns.
    - Point-in-time bias: rankings use today's volume, not historical volume.
      A coin that is now top-35 but was obscure 12 months ago is included
      with its historical data — a form of selection-on-outcome.
    These biases cannot be fixed without a historical universe snapshot API
    that Hyperliquid does not currently provide. They must be disclosed.
    """
    print(f"Fetching perp universe and ranking top {top_n} by volume...")

    # metaAndAssetCtxs gives us both the universe list and live context (volume, etc.)
    data = hl_post({"type": "metaAndAssetCtxs"})
    universe = data[0]["universe"]   # list of {name, szDecimals, ...}
    asset_ctxs = data[1]             # parallel list of context dicts

    # Pair them up and sort by 24h volume
    pairs = []
    for asset, ctx in zip(universe, asset_ctxs):
        vol_24h = float(ctx.get("dayNtlVlm", 0))
        pairs.append({"coin": asset["name"], "volume_24h": vol_24h})

    pairs.sort(key=lambda x: x["volume_24h"], reverse=True)
    top = pairs[:top_n]

    for i, p in enumerate(top[:10]):
        print(f"  {i+1}. {p['coin']:>8s}  ${p['volume_24h']:>15,.0f} 24h vol")
    if top_n > 10:
        print(f"  ... and {top_n - 10} more")

    return [p["coin"] for p in top]


# ---------------------------------------------------------------------------
# 2. Fetch historical funding rates from Hyperliquid
# ---------------------------------------------------------------------------
def fetch_funding_rates(coin: str, start_ms: int, end_ms: int) -> list[dict]:
    """
    Pull all funding rate records for a coin between start_ms and end_ms.
    Hyperliquid returns max 500 records per request, so we paginate.
    Funding is charged hourly (~24 records/day), each hour at 1/8 of the
    computed 8h rate.
    """
    all_records = []
    current_start = start_ms

    while current_start < end_ms:
        payload = {
            "type": "fundingHistory",
            "coin": coin,
            "startTime": current_start,
            "endTime": end_ms,
        }
        data = hl_post(payload)

        if not data:
            break

        all_records.extend(data)

        # Move past the last record
        last_time = data[-1]["time"]
        if isinstance(last_time, str):
            last_time = int(pd.Timestamp(last_time).timestamp() * 1000)
        current_start = last_time + 1

        # Stop if we got fewer than 500 (no more pages)
        if len(data) < 500:
            break

        time.sleep(SLEEP_BETWEEN_CALLS)

    return all_records


def pull_funding_rates(coins: list[str], days: int = 365) -> pd.DataFrame:
    """Pull funding rates for all coins and return a tidy DataFrame."""
    now = datetime.now(timezone.utc)
    end_ms = int(now.timestamp() * 1000)
    start_ms = int((now - timedelta(days=days)).timestamp() * 1000)

    frames = []
    for i, coin in enumerate(coins):
        print(f"  [{i+1}/{len(coins)}] Funding rates: {coin}")
        records = fetch_funding_rates(coin, start_ms, end_ms)
        if records:
            df = pd.DataFrame(records)
            df["symbol"] = coin
            frames.append(df)
        time.sleep(SLEEP_BETWEEN_CALLS)

    if not frames:
        print("  WARNING: No funding rate data returned!")
        return pd.DataFrame(columns=["symbol", "timestamp", "fundingRate"])

    result = pd.concat(frames, ignore_index=True)

    # Normalize column names — Hyperliquid returns: coin, fundingRate, premium, time
    if "time" in result.columns:
        result["timestamp"] = pd.to_datetime(result["time"], unit="ms")
    result["fundingRate"] = result["fundingRate"].astype(float)
    result = result[["symbol", "timestamp", "fundingRate"]].sort_values(
        ["symbol", "timestamp"]
    )
    print(f"  Total funding records: {len(result):,}")
    return result


# ---------------------------------------------------------------------------
# 3. Fetch OHLCV daily candles from Hyperliquid
# ---------------------------------------------------------------------------
def fetch_candles(coin: str, start_ms: int, end_ms: int, interval: str = "1d") -> list:
    """
    Fetch daily candle data. Hyperliquid returns max 5000 candles per request.
    For daily data over 1 year that's ~365 candles, so one call is enough.
    """
    payload = {
        "type": "candleSnapshot",
        "req": {
            "coin": coin,
            "interval": interval,
            "startTime": start_ms,
            "endTime": end_ms,
        },
    }
    return hl_post(payload)


def pull_ohlcv(coins: list[str], days: int = 365) -> pd.DataFrame:
    """Pull daily OHLCV for all coins."""
    now = datetime.now(timezone.utc)
    end_ms = int(now.timestamp() * 1000)
    start_ms = int((now - timedelta(days=days)).timestamp() * 1000)

    frames = []
    for i, coin in enumerate(coins):
        print(f"  [{i+1}/{len(coins)}] OHLCV: {coin}")
        candles = fetch_candles(coin, start_ms, end_ms)
        if candles:
            df = pd.DataFrame(candles)
            df["symbol"] = coin

            # Hyperliquid candle fields: t (open time ms), T (close time ms),
            # s (symbol), i (interval), o, h, l, c, v (volume in coin units), n (num trades)
            for col in ["o", "h", "l", "c", "v"]:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce")

            df["date"] = pd.to_datetime(df["t"], unit="ms").dt.normalize()
            df = df.rename(columns={"o": "open", "h": "high", "l": "low",
                                    "c": "close", "v": "volume"})

            # Compute quote volume (volume * close price as approximation)
            df["quote_volume"] = df["volume"] * df["close"]

            frames.append(df[["symbol", "date", "open", "high", "low", "close",
                              "volume", "quote_volume"]])
        time.sleep(SLEEP_BETWEEN_CALLS)

    if not frames:
        print("  WARNING: No candle data returned!")
        return pd.DataFrame(columns=["symbol", "date", "open", "high", "low",
                                      "close", "volume", "quote_volume"])

    result = pd.concat(frames, ignore_index=True)
    result = result.sort_values(["symbol", "date"]).drop_duplicates(
        subset=["symbol", "date"], keep="last"
    )
    print(f"  Total daily candles: {len(result):,}")
    return result


# ---------------------------------------------------------------------------
# 4. Signal Construction: Daily funding rate features
# ---------------------------------------------------------------------------
def build_funding_features(funding_df: pd.DataFrame,
                           short_window: int = 21,
                           long_window: int = 90) -> pd.DataFrame:
    """
    Aggregate hourly funding rates into daily features per asset:
      - daily_funding: sum of funding rates that day (typically ~24 per day,
        since Hyperliquid charges funding hourly)
      - funding_short: rolling short-window mean of daily funding
      - funding_long: rolling long-window mean of daily funding
      - funding_zscore: z-score of short mean vs trailing long-window distribution

    Parameters tuned via parameter sweep (see parameter_sweep.ipynb):
      - short_window=21, long_window=90 gave strongest signal at 14-day horizon
      - IC=-0.049, Q1-Q5 spread=2.06%

    KNOWN BIASES:
    - These metrics are likely in-sample / optimistically biased: the sweep
      selected the windows and horizon on the same data used to score them, so
      IC and Q1-Q5 spread overstate true out-of-sample performance.
    """
    df = funding_df.copy()
    df["date"] = df["timestamp"].dt.normalize()

    # Sum intraday funding to get daily total
    daily = df.groupby(["symbol", "date"])["fundingRate"].sum().reset_index()
    daily.columns = ["symbol", "date", "daily_funding"]
    daily = daily.sort_values(["symbol", "date"])

    # Rolling features using transform (avoids groupby/apply index issues)
    funding_features = daily.copy()
    grp = funding_features.groupby("symbol")["daily_funding"]
    funding_features["funding_short"] = grp.transform(
        lambda x: x.rolling(short_window, min_periods=max(3, short_window // 2)).mean()
    )
    funding_features["funding_long"] = grp.transform(
        lambda x: x.rolling(long_window, min_periods=max(10, long_window // 3)).mean()
    )
    rolling_std = grp.transform(
        lambda x: x.rolling(long_window, min_periods=max(10, long_window // 3)).std()
    )
    funding_features["funding_zscore"] = (funding_features["funding_short"] - funding_features["funding_long"]) / rolling_std
    funding_features["funding_zscore"] = funding_features["funding_zscore"].replace([float("inf"), float("-inf")], float("nan"))

    return funding_features


# ---------------------------------------------------------------------------
# 5. Merge everything into a single panel dataset
# ---------------------------------------------------------------------------
def build_panel(funding_features: pd.DataFrame, ohlcv: pd.DataFrame) -> pd.DataFrame:
    """
    Merge funding features with price data to create the analysis-ready panel.
    Also computes forward returns for backtesting.
    """
    panel = ohlcv.merge(funding_features, on=["symbol", "date"], how="left")
    panel = panel.sort_values(["symbol", "date"]).copy()

    # Forward returns. .shift(-n) shifts by ROWS, so a missing daily candle would
    # let ret_Nd silently span more than N calendar days (a label-alignment bug).
    # Reindex each symbol's close onto a contiguous daily index first, compute the
    # forward return there, then map back onto the panel's actual (symbol, date)
    # rows. fill_method=None means a return spanning a real gap becomes NaN, not a
    # wrong number (and avoids pct_change's deprecated default fill).
    horizons = [1, 7, 14, 21]
    fwd = {n: {} for n in horizons}  # n -> {(symbol, date): forward return}
    for symbol, g in panel.groupby("symbol"):
        s = g.set_index("date")["close"]
        s = s[~s.index.duplicated(keep="last")]
        daily = s.reindex(pd.date_range(s.index.min(), s.index.max(), freq="D"))
        for n in horizons:
            ret_n = daily.pct_change(n, fill_method=None).shift(-n)
            for d, v in ret_n.items():
                fwd[n][(symbol, d)] = v

    keys = list(zip(panel["symbol"], panel["date"]))
    for n in horizons:
        panel[f"ret_{n}d"] = [fwd[n].get(k) for k in keys]
    panel = panel.reset_index(drop=True)

    return panel


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Funding Rate Mean Reversion Data Pipeline")
    parser.add_argument("--days", type=int, default=365, help="Lookback period in days")
    parser.add_argument("--top", type=int, default=35, help="Number of top perps by volume")
    args = parser.parse_args()

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Get universe ranked by volume
    coins = get_top_perp_symbols(args.top)

    with open(DATA_DIR / "symbols.json", "w") as f:
        json.dump(coins, f, indent=2)

    # 2. Pull funding rates
    print(f"\n--- Pulling funding rates ({args.days} days) ---")
    funding_df = pull_funding_rates(coins, days=args.days)
    funding_df.to_parquet(DATA_DIR / "funding_rates_raw.parquet", index=False)

    # 3. Pull OHLCV
    print(f"\n--- Pulling daily OHLCV ({args.days} days) ---")
    ohlcv_df = pull_ohlcv(coins, days=args.days)
    ohlcv_df.to_parquet(DATA_DIR / "ohlcv_daily.parquet", index=False)

    # 4. Build features
    print("\n--- Building funding rate features ---")
    funding_features = build_funding_features(funding_df)
    funding_features.to_parquet(DATA_DIR / "funding_features.parquet", index=False)

    # 5. Build merged panel
    print("--- Building analysis panel ---")
    panel = build_panel(funding_features, ohlcv_df)
    panel.to_parquet(DATA_DIR / "panel.parquet", index=False)
    print(f"  Panel shape: {panel.shape}")

    # 6. Quick summary
    print("\n" + "=" * 50)
    print("  PIPELINE COMPLETE")
    print("=" * 50)
    print(f"  Coins:      {len(coins)}")
    print(f"  Date range: {panel['date'].min().date()} to {panel['date'].max().date()}")
    print(f"  Total rows: {len(panel):,}")
    print(f"\n  Files saved to: {DATA_DIR.resolve()}")
    print("  - symbols.json           (coin list)")
    print("  - funding_rates_raw.parquet  (raw hourly funding snapshots)")
    print("  - ohlcv_daily.parquet    (daily candles)")
    print("  - funding_features.parquet   (daily funding signals)")
    print("  - panel.parquet          <<< USE THIS FOR ANALYSIS")


if __name__ == "__main__":
    main()
