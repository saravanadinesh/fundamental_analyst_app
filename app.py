"""Streamlit app for viewing industry information by company ticker"""
import streamlit as st
import pandas as pd
from industry_info import get_industry_info
from av_client import compute_financial_metrics

# Page config
st.set_page_config(page_title="Fundamental Analyst App", layout="wide")

st.title("Fundamental Analyst App")
st.markdown("Data courtesy of [Prof. Aswath Damodaran](https://pages.stern.nyu.edu/~adamodar/) and Alpha Vantage.")
st.markdown(
    "Enter a company ticker in the side panel (use >> to expand) to view the company in the context of industry metrics including market size, profitability, efficiency and risk."
)

# Sidebar for input
with st.sidebar:
    st.header("Input")

    # when the user presses Enter in the text_input, this callback will run
    def _submit_from_input():
        st.session_state.submitted_ticker = st.session_state.get("ticker_input", "").strip().upper()

    # text_input uses session state key so on_change can set submitted_ticker
    st.text_input(
        "Company Ticker",
        placeholder="e.g., CROX, CMG",
        help="Enter a valid stock ticker",
        key="ticker_input",
        on_change=_submit_from_input,
    )

    if st.button("Get Industry Info", type="primary"):
        st.session_state.submitted_ticker = st.session_state.get("ticker_input", "").strip().upper()

    st.markdown("---")
    st.markdown("**Sample Tickers**: CROX, CMG, AAPL")

# Main content area
if "submitted_ticker" in st.session_state and st.session_state.submitted_ticker:
    ticker = st.session_state.submitted_ticker
    
    try:
        # Fetch industry info
        with st.spinner(f"Loading industry data for {ticker}..."):
            industry_info = get_industry_info(ticker)
        
        # Display success message with company and industry names
        company_name = industry_info.get("company_name", "Unknown")
        industry_name = industry_info.get("industry_name", "Unknown")
        st.success(f"✅ **{company_name}** ({ticker}) | Industry: **{industry_name}**")
        
        # Create a 2x2 grid layout for the four sections
        col1, col2 = st.columns(2)
        
        # Market Size (top-left)
        with col1:
            st.subheader("📊 Market Size")
            market_data = industry_info["market_size"]
            # Format market size as $<n>B (with commas). The source values are in billions.
            ms = market_data.get("marketsize")
            # fetch company metrics (may be missing)
            try:
                company_metrics = compute_financial_metrics(ticker, av_key="YD9VPN2U7FKOT5VT")
            except Exception as e:
                st.warning(f"⚠️ Failed to fetch company metrics: {str(e)}")
                company_metrics = {}

            # company revenue from compute_financial_metrics is in raw dollars; convert to billions
            comp_rev = company_metrics.get("revenue")
            comp_rev_display = None
            if comp_rev is not None:
                try:
                    v = float(comp_rev) / 1e9
                    if abs(v - int(v)) < 1e-6:
                        comp_rev_display = f"${int(v):,}B"
                    else:
                        comp_rev_display = f"${v:,.1f}B"
                except Exception:
                    comp_rev_display = str(comp_rev)
            if ms is None:
                ms_display = None
            else:
                try:
                    v = float(ms)
                    # show integer values without decimal, otherwise one decimal place
                    if abs(v - int(v)) < 1e-6:
                        ms_display = f"${int(v):,}B"
                    else:
                        ms_display = f"${v:,.1f}B"
                except Exception:
                    ms_display = str(ms)

            df_market = pd.DataFrame({
                "Metric": ["Revenue", "Past CAGR (5y)", "Next CAGR (2y)", "Next CAGR (5y)"],
                industry_name: [
                    ms_display,
                    f"{market_data.get('past_cagr_5y')}%" if market_data.get("past_cagr_5y") is not None else None,
                    f"{market_data.get('next_cagr_2y')}%" if market_data.get("next_cagr_2y") is not None else None,
                    f"{market_data.get('next_cagr_5y')}%" if market_data.get("next_cagr_5y") is not None else None,
                ],
                company_name: [
                    comp_rev_display,
                    f"{int(company_metrics.get('rev cagr 5y')*100)}%" if company_metrics.get("rev cagr 5y") is not None else None,
                    None,
                    None,
                ],
            })
            st.dataframe(df_market, use_container_width=True, hide_index=True)
        
        # Profitability (top-right)
        with col2:
            st.subheader("📈 Profitability")
            profit_data = industry_info["profitability"]
            # Profitability table with company column
            # company metrics for margins are returned as ratios (e.g., 0.3) so convert to percent
            def fmt_pct(x):
                if x is None:
                    return None
                try:
                    # if fraction (<=1) treat as fraction, else assume already percent
                    xv = float(x)
                    if abs(xv) <= 1:
                        return f"{int(round(xv*100))}%"
                    return f"{int(round(xv))}%"
                except Exception:
                    return str(x)

            comp_gross = company_metrics.get("gross margin")
            comp_ebit = company_metrics.get("ebit margin")
            comp_net = company_metrics.get("net margin")
            comp_roc = company_metrics.get("return on capital")
            comp_roe = company_metrics.get("return on equity")

            df_profit = pd.DataFrame({
                "Metric": ["Gross Margin", "EBIT Margin", "Net Margin", "ROC", "ROE"],
                industry_name: [
                    f"{profit_data.get('gross_margin')}%" if profit_data.get("gross_margin") is not None else None,
                    f"{profit_data.get('ebit_margin')}%" if profit_data.get("ebit_margin") is not None else None,
                    f"{profit_data.get('net_margin')}%" if profit_data.get("net_margin") is not None else None,
                    f"{profit_data.get('roc')}%" if profit_data.get("roc") is not None else None,
                    f"{profit_data.get('roe')}%" if profit_data.get("roe") is not None else None,
                ],
                company_name: [
                    fmt_pct(comp_gross),
                    fmt_pct(comp_ebit),
                    fmt_pct(comp_net),
                    fmt_pct(comp_roc),
                    fmt_pct(comp_roe),
                ],
            })
            st.dataframe(df_profit, use_container_width=True, hide_index=True)
        
        # Create second row
        col3, col4 = st.columns(2)
        
        # Efficiency (bottom-left)
        with col3:
            st.subheader("⚙️ Efficiency")
            eff_data = industry_info["efficiency"]
            comp_rec = company_metrics.get("receivable days")
            comp_inv = company_metrics.get("inventory days")
            comp_pay = company_metrics.get("payable days")

            df_eff = pd.DataFrame({
                "Metric": ["Receivable Days (DSO)", "Inventory Days (DSI)", "Payable Days (DPO)"],
                industry_name: [
                    str(eff_data.get("receivable_days")) if eff_data.get("receivable_days") is not None else None,
                    str(eff_data.get("inventory_days")) if eff_data.get("inventory_days") is not None else None,
                    str(eff_data.get("payable_days")) if eff_data.get("payable_days") is not None else None,
                ],
                company_name: [
                    str(comp_rec) if comp_rec is not None else None,
                    str(comp_inv) if comp_inv is not None else None,
                    str(comp_pay) if comp_pay is not None else None,
                ],
            })
            st.dataframe(df_eff, use_container_width=True, hide_index=True)
        
        # Risk (bottom-right)
        with col4:
            st.subheader("⚠️ Risk")
            risk_data = industry_info["risk"]
            comp_beta = company_metrics.get("beta")
            comp_de = company_metrics.get("debt to equity ratio")

            df_risk = pd.DataFrame({
                "Metric": ["Number of Firms", "Beta", "D/E Ratio", "Cost of Equity"],
                industry_name: [
                    str(risk_data.get("number_of_firms")) if risk_data.get("number_of_firms") is not None else None,
                    str(risk_data.get("beta")) if risk_data.get("beta") is not None else None,
                    f"{risk_data.get('de')}%" if risk_data.get("de") is not None else None,
                    f"{risk_data.get('cost_of_equity')}%" if risk_data.get("cost_of_equity") is not None else None,
                ],
                company_name: [
                    None,
                    str(comp_beta) if comp_beta is not None else None,
                    f"{int(round(comp_de*100))}%" if comp_de is not None else None,
                    None,
                ],
            })
            st.dataframe(df_risk, use_container_width=True, hide_index=True)
        
        # Raw JSON view (optional)
        with st.expander("📋 View Raw JSON"):
            import json
            st.json(industry_info)
    
    except ValueError as e:
        st.error(f"❌ Error: {str(e)}")
        st.info("Please enter a valid company ticker and try again.")
    except Exception as e:
        st.error(f"❌ An unexpected error occurred: {str(e)}")
        st.info("Please check your input and try again.")
else:
    st.info("👈 Enter a company ticker in the sidebar to get started!")
