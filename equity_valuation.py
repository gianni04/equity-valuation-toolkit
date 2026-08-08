"""
Equity Valuation & Screening Tool
-----------------------------------
Student project: estimate the intrinsic value of a basket of stocks using
two classic sell-side methods, then screen the basket by upside/downside.

1) Discounted Cash Flow (DCF): project free cash flow 5 years forward,
   discount by WACC, add a Gordon-growth terminal value.
2) Comparable multiples (comps): apply the peer-group median EV/EBITDA
   multiple to each company's own EBITDA.
3) Sensitivity table: DCF value grid across WACC and terminal growth
   assumptions, for the largest name in the basket.

Data source: Yahoo Finance fundamentals (real, but simplified - a real
Rothschild-style model would also use analyst consensus estimates and
normalize one-off items, which is out of scope here).
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import yfinance as yf

# ----------------------------------------------------------------------
# 1. CONFIG
# ----------------------------------------------------------------------

UNIVERSE = ["AAPL", "MSFT", "GOOGL", "JPM", "XOM", "JNJ", "PG", "KO", "NVDA", "UNH"]

RISK_FREE_RATE = 0.04       # approx 10Y US Treasury yield
MARKET_RISK_PREMIUM = 0.05  # long-run equity risk premium assumption
COST_OF_DEBT = 0.05         # simplified flat assumption
TAX_RATE = 0.21              # US statutory corporate tax rate

FORECAST_YEARS = 5
TERMINAL_GROWTH = 0.025      # long-run GDP-like growth assumption

OUTPUT_DIR = "output"


# ----------------------------------------------------------------------
# 2. DATA
# ----------------------------------------------------------------------

def fetch_fundamentals(ticker):
    """Pull the raw inputs needed for the DCF and comps from Yahoo Finance."""
    info = yf.Ticker(ticker).info
    return {
        "ticker": ticker,
        "price": info.get("currentPrice", np.nan),
        "shares_out": info.get("sharesOutstanding", np.nan),
        "market_cap": info.get("marketCap", np.nan),
        "beta": info.get("beta", 1.0) or 1.0,
        "free_cashflow": info.get("freeCashflow", np.nan),
        "revenue_growth": info.get("revenueGrowth", 0.05) or 0.05,
        "total_debt": info.get("totalDebt", 0) or 0,
        "total_cash": info.get("totalCash", 0) or 0,
        "ebitda": info.get("ebitda", np.nan),
        "enterprise_value": info.get("enterpriseValue", np.nan),
    }


# ----------------------------------------------------------------------
# 3. WACC
# ----------------------------------------------------------------------

def compute_wacc(row):
    """CAPM cost of equity + after-tax cost of debt, weighted by capital structure."""
    cost_of_equity = RISK_FREE_RATE + row["beta"] * MARKET_RISK_PREMIUM

    equity_value = row["market_cap"]
    debt_value = row["total_debt"]
    total_capital = equity_value + debt_value

    if total_capital == 0 or np.isnan(total_capital):
        return cost_of_equity  # fallback: all-equity company

    weight_equity = equity_value / total_capital
    weight_debt = debt_value / total_capital

    wacc = weight_equity * cost_of_equity + weight_debt * COST_OF_DEBT * (1 - TAX_RATE)
    return wacc


# ----------------------------------------------------------------------
# 4. DCF MODEL
# ----------------------------------------------------------------------

def project_fcf(fcf0, growth_stage1, years, terminal_growth):
    """Fade the growth rate linearly from stage-1 growth down to terminal growth."""
    growth_path = np.linspace(growth_stage1, terminal_growth, years)
    fcf_projection = []
    fcf = fcf0
    for g in growth_path:
        fcf = fcf * (1 + g)
        fcf_projection.append(fcf)
    return np.array(fcf_projection)


def dcf_value(row, wacc, forecast_years=FORECAST_YEARS, terminal_growth=TERMINAL_GROWTH):
    fcf0 = row["free_cashflow"]
    if np.isnan(fcf0) or fcf0 <= 0:
        return np.nan, np.nan

    # cap the starting growth rate to a sane range (avoid garbage from the data source)
    growth_stage1 = float(np.clip(row["revenue_growth"], -0.05, 0.20))

    fcf_projection = project_fcf(fcf0, growth_stage1, forecast_years, terminal_growth)
    discount_factors = [(1 + wacc) ** -t for t in range(1, forecast_years + 1)]
    pv_fcf = np.sum(fcf_projection * discount_factors)

    terminal_value = fcf_projection[-1] * (1 + terminal_growth) / (wacc - terminal_growth)
    pv_terminal = terminal_value * discount_factors[-1]

    enterprise_value = pv_fcf + pv_terminal
    net_debt = row["total_debt"] - row["total_cash"]
    equity_value = enterprise_value - net_debt

    if row["shares_out"] and row["shares_out"] > 0:
        value_per_share = equity_value / row["shares_out"]
    else:
        value_per_share = np.nan

    return value_per_share, enterprise_value


# ----------------------------------------------------------------------
# 5. COMPARABLE MULTIPLES (COMPS)
# ----------------------------------------------------------------------

def comps_value(df):
    """Apply the peer-group median EV/EBITDA multiple to each company's own EBITDA."""
    df = df.copy()
    df["ev_ebitda"] = df["enterprise_value"] / df["ebitda"]
    peer_median_multiple = df["ev_ebitda"].median()

    implied_ev = peer_median_multiple * df["ebitda"]
    net_debt = df["total_debt"] - df["total_cash"]
    implied_equity_value = implied_ev - net_debt
    implied_price = implied_equity_value / df["shares_out"]

    return implied_price, peer_median_multiple


# ----------------------------------------------------------------------
# 6. SENSITIVITY TABLE
# ----------------------------------------------------------------------

def sensitivity_table(row, base_wacc):
    wacc_range = np.linspace(base_wacc - 0.02, base_wacc + 0.02, 5)
    growth_range = np.linspace(TERMINAL_GROWTH - 0.01, TERMINAL_GROWTH + 0.01, 5)

    grid = pd.DataFrame(index=[f"{w:.1%}" for w in wacc_range],
                         columns=[f"{g:.1%}" for g in growth_range], dtype=float)

    for w in wacc_range:
        for g in growth_range:
            if w <= g:
                continue  # DCF math breaks if WACC <= terminal growth
            value_per_share, _ = dcf_value(row, w, terminal_growth=g)
            grid.loc[f"{w:.1%}", f"{g:.1%}"] = value_per_share

    grid.index.name = "WACC"
    grid.columns.name = "Terminal Growth"
    return grid


# ----------------------------------------------------------------------
# 7. MAIN
# ----------------------------------------------------------------------

def main():
    print("Downloading fundamentals for:", UNIVERSE)
    rows = [fetch_fundamentals(t) for t in UNIVERSE]
    df = pd.DataFrame(rows).set_index("ticker")

    # --- DCF for every stock in the universe ---
    dcf_prices, ev_list, wacc_list = [], [], []
    for ticker, row in df.iterrows():
        wacc = compute_wacc(row)
        value_per_share, enterprise_value = dcf_value(row, wacc)
        dcf_prices.append(value_per_share)
        ev_list.append(enterprise_value)
        wacc_list.append(wacc)

    df["wacc"] = wacc_list
    df["dcf_value_per_share"] = dcf_prices
    df["dcf_upside"] = df["dcf_value_per_share"] / df["price"] - 1

    # --- comps for every stock in the universe ---
    comps_prices, peer_multiple = comps_value(df)
    df["comps_value_per_share"] = comps_prices
    df["comps_upside"] = df["comps_value_per_share"] / df["price"] - 1

    screen = df[["price", "wacc", "dcf_value_per_share", "dcf_upside",
                 "comps_value_per_share", "comps_upside"]].sort_values("dcf_upside", ascending=False)
    print("\nValuation screen (sorted by DCF upside):\n", screen.round(3))
    screen.to_csv(f"{OUTPUT_DIR}/valuation_screen.csv")
    print(f"\nPeer-group median EV/EBITDA multiple used for comps: {peer_multiple:.2f}x")

    # --- sensitivity table for the largest name in the basket ---
    biggest_ticker = df["market_cap"].idxmax()
    grid = sensitivity_table(df.loc[biggest_ticker], df.loc[biggest_ticker, "wacc"])
    print(f"\nDCF sensitivity table for {biggest_ticker} (value per share):\n", grid.round(1))
    grid.to_csv(f"{OUTPUT_DIR}/sensitivity_{biggest_ticker}.csv")

    # --- upside/downside bar chart ---
    plt.figure(figsize=(10, 6))
    colors = ["green" if v > 0 else "red" for v in screen["dcf_upside"]]
    plt.barh(screen.index, screen["dcf_upside"] * 100, color=colors)
    plt.xlabel("DCF Implied Upside / Downside (%)")
    plt.title("Equity Valuation Screen - DCF Upside by Stock")
    plt.grid(alpha=0.3, axis="x")
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/valuation_screen.png", dpi=150)

    print(f"\nSaved charts and CSVs to {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
