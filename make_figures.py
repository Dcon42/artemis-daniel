"""
make_figures.py — Regenerate all charts used in the research report and pitch deck.
================================================================================
Reads the committed parquet data in `data/` and reproduces the canonical
funding-rate mean-reversion analysis (21d/90d z-score, top-35 universe, 14-day
horizon), saving PNG figures to `figures/`.

This mirrors the backtest logic in `signal_analysis.ipynb` (discovery layer) and
`validation.ipynb` (honesty layer) so the report/deck visuals reproduce exactly
from data with one command:

    python make_figures.py

Outputs (figures/):
  fig1_equity_curve.png   Long-Q1 / short-Q5 cumulative return + rolling Sharpe
  fig2_quintiles.png      Mean 14d forward return by funding-z-score quintile
  fig3_ic.png             Daily rank IC (14d) with 30-day rolling mean
  fig4_oos.png            In-sample vs out-of-sample (sealed Feb 15, 2026)
  fig5_monthly.png        Monthly L/S returns (the regime story)
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

# --------------------------------------------------------------------------- #
# Config — must match signal_analysis.ipynb / validation.ipynb
# --------------------------------------------------------------------------- #
SHORT_WINDOW = 21
LONG_WINDOW = 90
HORIZON = 14
TOP_N = 35
OOS_START = pd.Timestamp("2026-02-15")  # sealed out-of-sample boundary

DATA_DIR = Path(__file__).parent / "data"
FIG_DIR = Path(__file__).parent / "figures"
FIG_DIR.mkdir(exist_ok=True)

plt.style.use("seaborn-v0_8-whitegrid")
plt.rcParams.update({"font.size": 12, "figure.dpi": 130, "savefig.bbox": "tight"})

COLORS = ["#2ecc71", "#82e0aa", "#bdc3c7", "#f1948a", "#e74c3c"]


# --------------------------------------------------------------------------- #
# Build the panel exactly as the discovery notebook does
# --------------------------------------------------------------------------- #
def build_panel():
    funding_raw = pd.read_parquet(DATA_DIR / "funding_rates_raw.parquet")
    ohlcv = pd.read_parquet(DATA_DIR / "ohlcv_daily.parquet")
    with open(DATA_DIR / "symbols.json") as f:
        symbols = json.load(f)[:TOP_N]

    funding_raw = funding_raw[funding_raw["symbol"].isin(symbols)]
    ohlcv = ohlcv[ohlcv["symbol"].isin(symbols)]

    fr = funding_raw.copy()
    fr["date"] = pd.to_datetime(fr["timestamp"]).dt.normalize()
    daily = fr.groupby(["symbol", "date"])["fundingRate"].sum().reset_index()
    daily.columns = ["symbol", "date", "daily_funding"]
    daily = daily.sort_values(["symbol", "date"])

    grp = daily.groupby("symbol")["daily_funding"]
    daily["funding_short"] = grp.transform(
        lambda x: x.rolling(SHORT_WINDOW, min_periods=SHORT_WINDOW // 2).mean())
    daily["funding_long"] = grp.transform(
        lambda x: x.rolling(LONG_WINDOW, min_periods=LONG_WINDOW // 3).mean())
    rolling_std = grp.transform(
        lambda x: x.rolling(LONG_WINDOW, min_periods=LONG_WINDOW // 3).std())
    daily["funding_zscore"] = (daily["funding_short"] - daily["funding_long"]) / rolling_std
    daily["funding_zscore"] = daily["funding_zscore"].replace([np.inf, -np.inf], np.nan)

    panel = ohlcv.merge(daily, on=["symbol", "date"], how="left")
    panel = panel.sort_values(["symbol", "date"]).copy()
    close_grp = panel.groupby("symbol")["close"]
    # The committed panel is gap-free (contiguous daily candles per symbol over the
    # window), so this row-shift forward return equals the calendar-day forward return
    # that data_pipeline.build_panel guarantees by reindexing onto a daily grid — these
    # figures therefore match the pipeline's NaN-on-gap returns exactly.
    for h in (1, 7, 14, 21):
        panel[f"ret_{h}d"] = close_grp.transform(lambda x: x.pct_change(h).shift(-h))
    return panel.reset_index(drop=True)


def assign_quintiles(df, value_col="funding_zscore"):
    df = df.copy()
    df["quintile"] = df.groupby("date")[value_col].transform(
        lambda x: pd.qcut(x, 5, labels=False, duplicates="drop") if x.notna().sum() >= 5 else np.nan)
    return df.dropna(subset=["quintile"])


def long_short_returns(panel):
    """Daily long-Q1 / short-Q5 equal-weight return series (1-day P&L).

    Mirrors signal_analysis.ipynb exactly: quintiles are formed on the frame
    filtered to rows with a valid HORIZON-day forward return (so the equity
    curve ends ~HORIZON days before the data end), then the portfolio earns the
    next-day (ret_1d) return. This reproduces the canonical 63.6% / Sharpe 1.91.
    """
    df = panel.dropna(subset=["funding_zscore", f"ret_{HORIZON}d"]).copy()
    df = assign_quintiles(df)
    daily_q = df.groupby(["date", "quintile"])["ret_1d"].mean().unstack()
    q_lo, q_hi = daily_q.columns.min(), daily_q.columns.max()
    ls = (daily_q[q_lo] - daily_q[q_hi]).dropna()
    return ls


def long_short_returns_validation(panel):
    """L/S series as built in validation.ipynb: drop only on ret_1d (no horizon
    filter) so the z-score is "warmed" on full history; used for the IS/OOS split
    so the sealed-OOS figure reproduces validation's +12.72% headline."""
    df = panel.dropna(subset=["funding_zscore", "ret_1d"]).copy()
    df = assign_quintiles(df)
    daily_q = df.groupby(["date", "quintile"])["ret_1d"].mean().unstack()
    q_lo, q_hi = daily_q.columns.min(), daily_q.columns.max()
    return (daily_q[q_lo] - daily_q[q_hi]).dropna()


def perf_stats(ls):
    cum = (1 + ls).cumprod()
    total = cum.iloc[-1] - 1
    ann = (1 + total) ** (365 / len(ls)) - 1
    vol = ls.std() * np.sqrt(365)
    sharpe = ann / vol if vol > 0 else 0
    max_dd = (cum / cum.cummax() - 1).min()
    return dict(total=total, ann=ann, vol=vol, sharpe=sharpe, max_dd=max_dd, cum=cum)


# --------------------------------------------------------------------------- #
# Figures
# --------------------------------------------------------------------------- #
def fig_equity_curve(ls, stats):
    cum = stats["cum"]
    fig, axes = plt.subplots(2, 1, figsize=(11, 8), height_ratios=[2, 1])

    axes[0].plot(cum.index, cum.values, color="#2c6fbb", linewidth=2)
    axes[0].axhline(1, color="gray", ls="--", lw=0.6)
    axes[0].axvspan(OOS_START, cum.index.max(), color="orange", alpha=0.10,
                    label="Out-of-sample (sealed Feb 15, 2026)")
    # annotate the Jan-2026 drawdown (regime story)
    peak = cum[:OOS_START].idxmax()
    axes[0].annotate("BTC rally / trend regime\n→ mean-reversion bleeds",
                     xy=(pd.Timestamp("2026-01-20"), cum.get(pd.Timestamp("2026-01-20"), cum.loc[peak])),
                     xytext=(pd.Timestamp("2025-09-01"), cum.max() * 0.72),
                     arrowprops=dict(arrowstyle="->", color="#c0392b"),
                     fontsize=10, color="#c0392b")
    axes[0].set_title(f"Long Low-Funding / Short High-Funding  "
                      f"(z-score {SHORT_WINDOW}d/{LONG_WINDOW}d, top {TOP_N}, daily rebalance)",
                      fontsize=13, fontweight="bold")
    axes[0].set_ylabel("Cumulative return")
    axes[0].yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{(x-1)*100:.0f}%"))
    txt = (f"Total return: {stats['total']*100:.1f}%\n"
           f"Sharpe: {stats['sharpe']:.2f}\n"
           f"Max drawdown: {stats['max_dd']*100:.1f}%")
    axes[0].text(0.015, 0.97, txt, transform=axes[0].transAxes, va="top", fontsize=11,
                 bbox=dict(boxstyle="round", fc="white", ec="#cccccc"))
    axes[0].legend(loc="lower right", fontsize=10)

    roll = ls.rolling(30).mean() / ls.rolling(30).std() * np.sqrt(365)
    axes[1].plot(roll.index, roll.values, color="#e67e22", lw=1.4)
    axes[1].axhline(0, color="gray", ls="--", lw=0.6)
    axes[1].set_title("Rolling 30-day annualized Sharpe", fontsize=12)
    axes[1].set_ylabel("Sharpe")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "fig1_equity_curve.png")
    plt.close(fig)


def fig_quintiles(panel):
    ret_col = f"ret_{HORIZON}d"
    df = panel.dropna(subset=["funding_zscore", ret_col]).copy()
    df = assign_quintiles(df)
    q = df.groupby("quintile")[ret_col].mean() * 100

    fig, ax = plt.subplots(figsize=(9, 5.5))
    labels = ["Q1\n(low FR)", "Q2", "Q3", "Q4", "Q5\n(high FR)"]
    ax.bar(range(len(q)), q.values, color=COLORS, edgecolor="white")
    ax.set_xticks(range(len(q)))
    ax.set_xticklabels(labels[:len(q)])
    ax.axhline(0, color="black", lw=0.6)
    ax.set_title(f"Mean {HORIZON}-day forward return by funding-z-score quintile",
                 fontsize=13, fontweight="bold")
    ax.set_ylabel("Mean forward return (%)")
    for i, v in enumerate(q.values):
        ax.text(i, v + (0.03 if v >= 0 else -0.06), f"{v:.2f}%", ha="center", fontsize=10)
    spread = q.iloc[0] - q.iloc[-1]
    ax.text(0.985, 0.97, f"Q1−Q5 spread: {spread:.2f}%\nNon-monotone — Q2 anomalously weak\n(tail effect, not a clean linear factor)",
            transform=ax.transAxes, va="top", ha="right", fontsize=10,
            bbox=dict(boxstyle="round", fc="#fff8e1", ec="#cccccc"))
    fig.tight_layout()
    fig.savefig(FIG_DIR / "fig2_quintiles.png")
    plt.close(fig)
    return spread


def fig_ic(panel):
    ret_col = f"ret_{HORIZON}d"
    df = panel.dropna(subset=["funding_zscore", ret_col]).copy()

    def row_ic(g):
        return g["funding_zscore"].corr(g[ret_col], method="spearman") if len(g) >= 5 else np.nan
    ic = df.groupby("date").apply(row_ic).dropna()

    fig, ax = plt.subplots(figsize=(11, 5))
    ax.bar(ic.index, ic.values, width=1, alpha=0.4,
           color=["#c0392b" if x > 0 else "#27ae60" for x in ic.values])
    roll = ic.rolling(30).mean()
    ax.plot(roll.index, roll.values, color="black", lw=2, label="30-day rolling mean")
    ax.axhline(ic.mean(), color="#2c6fbb", ls="--", lw=1.2, label=f"Full-period mean = {ic.mean():.4f}")
    ax.axhline(0, color="gray", lw=0.6)
    ax.set_title(f"Daily rank IC: funding z-score vs {HORIZON}-day forward return",
                 fontsize=13, fontweight="bold")
    ax.set_ylabel("Spearman IC")
    ax.legend(loc="upper right", fontsize=10)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "fig3_ic.png")
    plt.close(fig)
    return ic.mean()


def fig_oos(ls):
    is_ls = ls[ls.index < OOS_START]
    oos_ls = ls[ls.index >= OOS_START]
    is_cum = (1 + is_ls).cumprod()
    oos_cum = (1 + oos_ls).cumprod()

    fig, ax = plt.subplots(figsize=(11, 5.5))
    ax.plot(is_cum.index, (is_cum.values - 1) * 100, color="#2c6fbb", lw=2,
            label=f"In-sample ({len(is_ls)} days)")
    ax.plot(oos_cum.index, (oos_cum.values - 1) * 100, color="#e67e22", lw=2,
            label=f"Out-of-sample ({len(oos_ls)} days), rebased")
    ax.axhline(0, color="gray", lw=0.6)
    ax.axvline(OOS_START, color="black", ls=":", lw=1)
    ax.set_title("In-sample vs out-of-sample cumulative L/S return",
                 fontsize=13, fontweight="bold")
    ax.set_ylabel("Cumulative return (%)")
    oos_total = oos_cum.iloc[-1] - 1
    ax.text(0.015, 0.97,
            f"OOS held its sign: +{oos_total*100:.1f}% cumulative\n"
            f"(does NOT collapse — the edge fails on\nsignificance, not on OOS decay)",
            transform=ax.transAxes, va="top", fontsize=10,
            bbox=dict(boxstyle="round", fc="#e8f6ef", ec="#cccccc"))
    ax.legend(loc="lower right", fontsize=10)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "fig4_oos.png")
    plt.close(fig)
    return oos_total


def fig_monthly(ls):
    monthly = ls.resample("ME").apply(lambda x: (1 + x).prod() - 1) * 100
    fig, ax = plt.subplots(figsize=(11, 5))
    ax.bar(monthly.index.strftime("%Y-%m"), monthly.values,
           color=["#27ae60" if x > 0 else "#c0392b" for x in monthly.values],
           edgecolor="white")
    ax.axhline(0, color="black", lw=0.6)
    ax.set_title("Monthly long/short returns — the regime story", fontsize=13, fontweight="bold")
    ax.set_ylabel("Return (%)")
    plt.xticks(rotation=45, ha="right")
    win = (monthly > 0).sum()
    ax.text(0.015, 0.97, f"Winning months: {win}/{len(monthly)} ({win/len(monthly):.0%})",
            transform=ax.transAxes, va="top", fontsize=10,
            bbox=dict(boxstyle="round", fc="white", ec="#cccccc"))
    fig.tight_layout()
    fig.savefig(FIG_DIR / "fig5_monthly.png")
    plt.close(fig)


# --------------------------------------------------------------------------- #
def main():
    print("Building panel from data/ ...")
    panel = build_panel()
    print(f"  {panel.shape[0]:,} rows, {panel['symbol'].nunique()} coins, "
          f"{panel['date'].min().date()} → {panel['date'].max().date()}")

    ls = long_short_returns(panel)
    stats = perf_stats(ls)
    ls_val = long_short_returns_validation(panel)  # warmed series for the OOS split

    fig_equity_curve(ls, stats)
    spread = fig_quintiles(panel)
    mean_ic = fig_ic(panel)
    oos_total = fig_oos(ls_val)
    fig_monthly(ls)

    print("\n=== Reproduced headline numbers (verify against report) ===")
    print(f"  L/S total return : {stats['total']*100:6.2f}%")
    print(f"  Sharpe (naive)   : {stats['sharpe']:6.2f}")
    print(f"  Max drawdown     : {stats['max_dd']*100:6.2f}%")
    print(f"  Q1-Q5 spread 14d : {spread:6.2f}%")
    print(f"  Mean IC (14d)    : {mean_ic:6.4f}")
    print(f"  OOS cumulative   : {oos_total*100:6.2f}%")
    print(f"\nFigures written to {FIG_DIR}/")


if __name__ == "__main__":
    main()
