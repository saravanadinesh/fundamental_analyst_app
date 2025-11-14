"""industry_info module

Provides get_industry_info(company_ticker) -> dict

This file was converted from the notebook `industry_info.ipynb` and exposes
a single function that returns structured industry information for the
industry of the given company ticker.
"""
from pprint import pprint
import json
import pandas as pd
import numpy as np

# import helper functions from the existing project module
from adamodaran_utils import (
    get_industry_df,
    get_ind_demand,
    get_ind_fundamentals,
    get_ind_profitability,
    get_ind_efficiency,
    get_ind_risk,
    get_ind_multiples,
)


def _safe_get(df: pd.DataFrame, idx, col: str, cast=None):
    """Safely get a value from df.loc[idx, col].

    Returns None for NaN/NaT. If cast provided, will attempt to call cast(value)
    and return the result; on failure returns the original value.
    """
    try:
        val = df.loc[idx, col]
    except Exception:
        return None
    if pd.isna(val):
        return None
    if cast:
        try:
            return cast(val)
        except Exception:
            return val
    return val


def get_industry_info(company_ticker: str) -> dict:
    """Return structured industry information for the company ticker.

    Args:
        company_ticker: ticker string present in the industry dataframe.

    Returns:
        dict with keys: company_name, industry_name, market_size, profitability, efficiency, risk, multiples

    Raises:
        ValueError if the ticker is not found.
    """
    ind_df = get_industry_df()
    # find industry name and company name for ticker
    matched = ind_df[ind_df["ticker"] == company_ticker]
    if matched.empty:
        raise ValueError(f"Ticker '{company_ticker}' not found in industry dataframe")
    indname = matched.industry.values[0]
    company_name = matched.company.values[0]

    # fetch industry-level dataframes (functions from adamodaran_utils)
    demand_df = get_ind_demand(industry_list=[indname])
    fundamentals_df = get_ind_fundamentals(industry_list=[indname])
    profitability_df = get_ind_profitability(industry_list=[indname])
    efficiency_df = get_ind_efficiency(industry_list=[indname])
    risk_df = get_ind_risk(industry_list=[indname])
    multiples_df = get_ind_multiples(industry_list=[indname])

    industry_info = {
        "company_name": company_name,
        "industry_name": indname,
        "market_size": {
            "marketsize": _safe_get(fundamentals_df, indname, "Revenue"),
            "past_cagr_5y": _safe_get(demand_df, indname, "Revenue CAGR (past 5y)"),
            "next_cagr_2y": _safe_get(demand_df, indname, "Revenue CAGR (next 2y)"),
            "next_cagr_5y": _safe_get(demand_df, indname, "Revenue CAGR (next 5y)"),
        },
        "profitability": {
            "gross_margin": _safe_get(profitability_df, indname, "Gross Margin"),
            "ebit_margin": _safe_get(profitability_df, indname, "EBIT Margin"),
            "net_margin": _safe_get(profitability_df, indname, "Net Margin"),
            "roc": _safe_get(profitability_df, indname, "ROC"),
            "roe": _safe_get(profitability_df, indname, "ROE"),
        },
        "efficiency": {
            "receivable_days": _safe_get(efficiency_df, indname, "DSO", cast=lambda v: int(np.int64(v))),
            "inventory_days": _safe_get(efficiency_df, indname, "DSI", cast=lambda v: int(np.int64(v))),
            "payable_days": _safe_get(efficiency_df, indname, "DPO", cast=lambda v: int(np.int64(v))),
        },
        "risk": {
            "number_of_firms": _safe_get(risk_df, indname, "Number of firms"),
            "beta": _safe_get(risk_df, indname, "Beta"),
            "de": _safe_get(risk_df, indname, "D/E"),
            "cost_of_equity": _safe_get(risk_df, indname, "Cost of Equity"),
        },
        "multiples": {
            "current_pe": _safe_get(multiples_df, indname, "Current PE"),
            "forward_pe": _safe_get(multiples_df, indname, "Forward PE"),
            "ev_ebitda": _safe_get(multiples_df, indname, "EV/EBITDA"),
            "pbv": _safe_get(multiples_df, indname, "PBV"),
            "ev_sales": _safe_get(multiples_df, indname, "EV/Sales"),
        },
    }

    return industry_info


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Get industry_info for a company ticker")
    parser.add_argument("ticker", help="Company ticker (e.g. CROX)")
    parser.add_argument("--json", action="store_true", help="Print JSON output")
    args = parser.parse_args()
    info = get_industry_info(args.ticker)
    if args.json:
        print(json.dumps(info, indent=2, default=str))
    else:
        pprint(info)
