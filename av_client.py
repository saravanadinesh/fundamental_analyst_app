"""AlphaVantage helper: fetch overview and build TTM statements with local cache.

Provides fetch_company_ttm(ticker, av_key=None, use_cache=True, cache_dir=None)
which returns a dict with keys: overview, income_ttm, balance_ttm, cashflow_ttm

The implementation mirrors the notebook workflow: it fetches (or loads from
cache) the OVERVIEW, INCOME_STATEMENT, BALANCE_SHEET, and CASH_FLOW endpoints
and constructs TTM statements by summing the latest 4 quarterlyReports.
"""
from pathlib import Path
import json
import os
from typing import Optional, Dict, Any
import requests


def _get_cache_dir(cache_dir: Optional[str]) -> Path:
    if cache_dir:
        p = Path(cache_dir)
    else:
        p = Path.cwd() / "av_cache"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _get_cache_file(cache_dir: Path, symbol: str, data_type: str) -> Path:
    return cache_dir / f"{symbol}_{data_type}.json"


def _load_from_cache(cache_dir: Path, symbol: str, data_type: str) -> Optional[Dict[str, Any]]:
    p = _get_cache_file(cache_dir, symbol, data_type)
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None


def _save_to_cache(cache_dir: Path, symbol: str, data_type: str, data: Dict[str, Any]) -> None:
    p = _get_cache_file(cache_dir, symbol, data_type)
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _convert_num(s: Optional[str]):
    """Convert AlphaVantage numeric strings to int/float or None.

    Handles commas and parenthesis for negatives. Returns None for empty strings.
    """
    if s is None:
        return None
    s = str(s).strip()
    if s == "" or s.lower() == "none":
        return None
    s = s.replace(",", "")
    if s.startswith("(") and s.endswith(")"):
        s = "-" + s[1:-1]
    try:
        if "." in s:
            return float(s)
        return int(s)
    except Exception:
        try:
            return float(s)
        except Exception:
            return None


def build_ttm_from_statement(stmt: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Construct a TTM statement by summing the latest 4 quarterlyReports.

    Returns a dict representing the TTM statement or None if stmt missing.
    """
    if not stmt:
        return None
    qreports = stmt.get("quarterlyReports") or []
    if len(qreports) == 0:
        return None
    latest4 = qreports[:4]

    # gather all keys present
    keys = set()
    for q in latest4:
        keys.update(q.keys())

    ttm: Dict[str, Any] = {}
    for k in keys:
        if k in ("fiscalDateEnding", "reportedCurrency"):
            ttm[k] = latest4[0].get(k)
            continue
        vals = [_convert_num(q.get(k)) for q in latest4]
        if all(v is None for v in vals):
            ttm[k] = None
            continue
        total = 0
        any_float = False
        for v in vals:
            if v is None:
                continue
            if isinstance(v, float):
                any_float = True
            total += v
        ttm[k] = float(total) if any_float else int(total)

    ttm["_ttm_from_quarters"] = [q.get("fiscalDateEnding") for q in latest4]
    return ttm


def compute_5yr_cagr_from_annuals(stmt: Optional[Dict[str, Any]], value_key: str = "totalRevenue") -> Optional[float]:
    """Compute 5-year CAGR from annualReports in a statement.

    The function expects `stmt` to contain an "annualReports" key with a list
    of dictionaries ordered with the most recent report first (AlphaVantage
    format). It converts the `value_key` for the latest report (index 0) and
    the report five years earlier (index 5) to numbers and returns the CAGR
    as a floating point (e.g. 0.12 for 12%). Returns None if data is
    unavailable or not convertible.
    """
    if not stmt:
        return None
    areports = stmt.get("annualReports") or []
    # need at least 6 annual reports (latest + 5 years ago)
    if len(areports) < 6:
        return None

    latest = areports[0].get(value_key)
    earlier = areports[5].get(value_key)
    v_latest = _convert_num(latest)
    v_earlier = _convert_num(earlier)
    if v_latest is None or v_earlier is None:
        return None
    try:
        # values must be positive for CAGR calculation
        if v_earlier <= 0 or v_latest <= 0:
            return None
        years = 5
        cagr = (float(v_latest) / float(v_earlier)) ** (1.0 / years) - 1.0
        return round(float(cagr),2)
    except Exception:
        return None


def fetch_company_overview(ticker: str, av_key: Optional[str] = None, use_cache: bool = True, cache_dir: Optional[str] = None) -> Dict[str, Any]:
    """Fetch company OVERVIEW from AlphaVantage (uses cache if enabled).

    Returns the parsed JSON dict for the OVERVIEW endpoint.
    """
    symbol = ticker.upper()
    key = av_key or os.environ.get("AV_KEY")
    if not key:
        raise ValueError("AlphaVantage API key not provided and AV_KEY not set in environment")

    cdir = _get_cache_dir(cache_dir)
    dtype = "overview"
    if use_cache:
        cached = _load_from_cache(cdir, symbol, dtype)
        if cached is not None:
            return cached

    url = f"https://www.alphavantage.co/query?function=OVERVIEW&symbol={symbol}&apikey={key}"
    resp = requests.get(url)
    data = resp.json()
    # Convert numeric-looking strings to numbers for sensible keys.
    # Keep clearly textual or date fields as strings.
    keep_as_str = {
        "Address",
        "Description",
        "AssetType",
        "Country",
        "Currency",
        "Exchange",
        "FiscalYearEnd",
        "Industry",
        "Name",
        "OfficialSite",
        "Sector",
        "Symbol",
        "CIK",
    }

    for k in list(data.keys()):
        # Preserve explicit keep-as-string keys
        if k in keep_as_str:
            continue
        # Preserve any date-like fields (endswith Date or contains 'Date' or 'Quarter')
        if k.lower().endswith("date") or "date" in k.lower() or "quarter" in k.lower():
            continue
        # Try converting using the shared _convert_num helper
        try:
            conv = _convert_num(data.get(k))
        except Exception:
            conv = None
        if conv is not None:
            data[k] = conv
    # Attempt to compute 5-year revenue CAGR and attach to the overview.
    # We try to reuse a cached INCOME_STATEMENT when available to avoid
    # additional API calls; otherwise fetch it (respecting use_cache flag).
    income_stmt = None
    if use_cache:
        try:
            income_stmt = _load_from_cache(cdir, symbol, "income_statement")
        except Exception:
            income_stmt = None

    if income_stmt is None:
        try:
            url_inc = f"https://www.alphavantage.co/query?function=INCOME_STATEMENT&symbol={symbol}&apikey={key}"
            resp_inc = requests.get(url_inc)
            income_stmt = resp_inc.json()
            # save a copy of the income statement to cache for future runs
            try:
                _save_to_cache(cdir, symbol, "income_statement", income_stmt)
            except Exception:
                pass
        except Exception:
            income_stmt = None

    try:
        rev_cagr = compute_5yr_cagr_from_annuals(income_stmt, value_key="totalRevenue")
    except Exception:
        rev_cagr = None
    # store as a float or None
    data["RevCAGR5y"] = rev_cagr

    try:
        _save_to_cache(cdir, symbol, dtype, data)
    except Exception:
        pass
    return data


def fetch_company_ttm(ticker: str, av_key: Optional[str] = None, use_cache: bool = True, cache_dir: Optional[str] = None) -> Dict[str, Any]:
    """Fetch INCOME_STATEMENT, BALANCE_SHEET and CASH_FLOW, construct TTM statements.

    Args:
        ticker: Stock ticker (e.g., 'CROX')
        av_key: AlphaVantage API key. If None, reads AV_KEY env var.
        use_cache: If True, load from local cache when available.
        cache_dir: Directory path to store cache files (default ./av_cache)

    Returns:
        dict with keys: overview, income_ttm, balance_ttm, cashflow_ttm
    """
    symbol = ticker.upper()
    key = av_key or os.environ.get("AV_KEY")
    if not key:
        raise ValueError("AlphaVantage API key not provided and AV_KEY not set in environment")

    cdir = _get_cache_dir(cache_dir)

    functions = {
        "INCOME_STATEMENT": "income_statement",
        "BALANCE_SHEET": "balance_sheet",
        "CASH_FLOW": "cash_flow",
    }

    raw: Dict[str, Any] = {}
    for func, dtype in functions.items():
        if use_cache:
            cached = _load_from_cache(cdir, symbol, dtype)
            if cached is not None:
                raw[dtype] = cached
                continue
        url = f"https://www.alphavantage.co/query?function={func}&symbol={symbol}&apikey={key}"
        resp = requests.get(url)
        data = resp.json()
        raw[dtype] = data
        # save to cache
        try:
            _save_to_cache(cdir, symbol, dtype, data)
        except Exception:
            pass

    income_ttm = build_ttm_from_statement(raw.get("income_statement"))
    balance_ttm = build_ttm_from_statement(raw.get("balance_sheet"))
    cashflow_ttm = build_ttm_from_statement(raw.get("cash_flow"))

    return {
        "income_ttm": income_ttm,
        "balance_ttm": balance_ttm,
        "cashflow_ttm": cashflow_ttm,
    }


def compute_financial_metrics(ticker: str, av_key: str, use_cache: bool = True, cache_dir: Optional[str] = None) -> Dict[str, Any]:
    """Compute a small set of financial ratios using TTM statements and overview.

    Returns a dictionary with the following keys (all lowercase with spaces):
      - revenue
      - gross margin
      - ebit margin
      - net margin
      - receivable days
      - inventory days
      - payable days
      - debt to equity ratio
      - return on capital (from ReturnOnAssetsTTM in overview)
      - return on equity (from ReturnOnEquityTTM in overview)
      - beta (from overview Beta)
      - rev cagr 5y

    The function is defensive: missing data yields None for each metric that
    cannot be computed.
    """
    # Fetch TTM statements and overview (these functions handle caching)
    ttm = fetch_company_ttm(ticker, av_key=av_key, use_cache=use_cache, cache_dir=cache_dir)
    overview = fetch_company_overview(ticker, av_key=av_key, use_cache=use_cache, cache_dir=cache_dir)

    income = ttm.get("income_ttm") or {}
    bal = ttm.get("balance_ttm") or {}

    def _num(x):
        if x is None:
            return None
        if isinstance(x, (int, float)):
            return x
        return _convert_num(x)

    def _pick(d: Dict[str, Any], *keys):
        for k in keys:
            if k in d and d.get(k) is not None:
                return d.get(k)
        return None

    # Revenue and related income statement items (use canonical AlphaVantage keys)
    # build_ttm_from_statement returns numeric values where available, so we can
    # directly read the expected keys from the TTM dict.
    revenue = income.get("totalRevenue")
    gross_profit = income.get("grossProfit")
    operating_income = income.get("operatingIncome")
    net_income = income.get("netIncome")
    cost_of_revenue = income.get("costOfRevenue")

    # Balance sheet items (point-in-time) — use canonical quarterly report keys
    net_receivables = bal.get("currentNetReceivables")
    inventory = bal.get("inventory")
    accounts_payable = bal.get("currentAccountsPayable")
    short_term_debt = bal.get("shortTermDebt")
    long_term_debt = bal.get("longTermDebt")
    # AlphaVantage sometimes provides a combined shortLongTermDebtTotal
    total_debt = bal.get("shortLongTermDebtTotal") 
    total_equity = bal.get("totalShareholderEquity")

    # Derive total debt if needed
    if total_debt is None:
        parts = [v for v in (short_term_debt, long_term_debt) if v is not None]
        if parts:
            total_debt = sum(parts)

    # Compute margins (guard against division by zero)
    def _safe_div(a, b):
        try:
            if a is None or b is None:
                return None
            if b == 0:
                return None
            return float(a) / float(b)
        except Exception:
            return None

    gross_margin = round(_safe_div(gross_profit, revenue), 2) if _safe_div(gross_profit, revenue) is not None else None
    ebit_margin = round(_safe_div(operating_income, revenue), 2) if _safe_div(operating_income, revenue) is not None else None
    net_margin = round(_safe_div(net_income, revenue), 2) if _safe_div(net_income, revenue) is not None else None

    # For days calculations we use annualized TTM revenue or COGS
    cogs = cost_of_revenue
    if cogs is None and revenue is not None and gross_profit is not None:
        # fallback: COGS = Revenue - GrossProfit
        try:
            cogs = float(revenue) - float(gross_profit)
        except Exception:
            cogs = None

    receivable_days = None
    if net_receivables is not None and revenue is not None and revenue != 0:
        receivable_days = int(float(net_receivables) / float(revenue) * 365.0)

    inventory_days = None
    if inventory is not None and cogs is not None and cogs != 0:
        inventory_days = int(float(inventory) / float(cogs) * 365.0)

    payable_days = None
    if accounts_payable is not None and cogs is not None and cogs != 0:
        payable_days = int(float(accounts_payable) / float(cogs) * 365.0)

    debt_to_equity = None
    if total_debt is not None and total_equity is not None and total_equity != 0:
        debt_to_equity = round(float(total_debt) / float(total_equity),1)

    # Overview-derived items
    return_on_capital = overview.get("ReturnOnAssetsTTM")
    return_on_equity = overview.get("ReturnOnEquityTTM")
    beta = round(overview.get("Beta"),2) if overview.get("Beta") is not None else None
    # revenue 5-year CAGR is computed and stored in the overview as rev_cagr_5y
    rev_cagr = overview.get("RevCAGR5y")

    result = {
        "revenue": revenue,
        "gross margin": gross_margin,
        "ebit margin": ebit_margin,
        "net margin": net_margin,
        "receivable days": receivable_days,
        "inventory days": inventory_days,
        "payable days": payable_days,
        "debt to equity ratio": debt_to_equity,
        "return on capital": return_on_capital,
        "return on equity": return_on_equity,
        "beta": beta,
        "rev cagr 5y": rev_cagr,
    }

    return result


if __name__ == "__main__":
    import argparse
    from pprint import pprint

    parser = argparse.ArgumentParser(description="Fetch AlphaVantage overview and TTM statements for a ticker")
    parser.add_argument("ticker", help="Company ticker symbol")
    parser.add_argument("--apikey", help="AlphaVantage API key (optional)")
    parser.add_argument("--no-cache", action="store_true", help="Disable cache and fetch fresh data")
    parser.add_argument("--cache-dir", help="Directory to store cache files")
    args = parser.parse_args()
    overview = fetch_company_overview(args.ticker, av_key=args.apikey, use_cache=not args.no_cache, cache_dir=args.cache_dir)
    ttm_data = fetch_company_ttm(args.ticker, av_key=args.apikey, use_cache=not args.no_cache, cache_dir=args.cache_dir)

    print("\n--- COMPANY OVERVIEW ---")
    pprint(overview)
    print("\n--- TTM INCOME STATEMENT ---")
    pprint(ttm_data.get("income_ttm"))
    print("\n--- TTM BALANCE SHEET ---")
    pprint(ttm_data.get("balance_ttm"))
    print("\n--- TTM CASH FLOW STATEMENT ---")
    pprint(ttm_data.get("cashflow_ttm"))
