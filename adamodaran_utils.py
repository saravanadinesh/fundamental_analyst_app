# ------------------------------------------------------------------------------------------------------------------
# adamodaran_utils.py 
# Description:
#   This file contains all the API code for accessing data from Prof. Aswath Damodaran's website
# ------------------------------------------------------------------------------------------------------------------

import sys
import os
import pandas as pd
import numpy as np 

from urllib3.exceptions import InsecureRequestWarning
import urllib3
import requests

# ------------------------------------------------------------------------------------------------------------------
# get_raw_industry_df
# Description: Basically converts the excel sheet for US companies in Prof. Damodaran's indname.xlsx data
# 
# Inputs
#   None
# Output
#   industry_df: A pandas dataframe containing columns such as company name, tickers, industry the belong to etc.
# ------------------------------------------------------------------------------------------------------------------
def get_raw_industry_df():
    industry_df = pd.read_excel("indname.xlsx", sheet_name="By country") 
    return(industry_df)


# ------------------------------------------------------------------------------------------------------------------
# get_adamodar_file
# Description:
#   Acquire a particular spreadsheet from the professor's site
# Input
#   filename: A string containing the filename on the professor's website that you want to download
#   stale_period: If the data in local cache is older than this number in days, we fetch fresh data form the
#                 site. Otherwise we simply return the data in the cache
#   country: At the moment only United States is supported. TODO: Implement for other countries/global
#   year: If unspecified, lastest year's data will be returned. You can specify, as an integer, a past year using
#         the last two digits. Data from the Prof.'s archive will be returned (data that was calculated at the end 
#         of the specified year). Ex. If you specify 15, the data computed at the end of 2015 will be returned
# ------------------------------------------------------------------------------------------------------------------
def get_adamodar_file(filename, country="United States", year = None):


    # sheets_df = pd.read_excel(local_dir_name+"\\adamodar_specifics.xlsx", sheet_name="sheetnames", engine="openpyxl", index_col=0)
    # sheetname = sheets_df.loc[filename,'sheet name']
    skiprows_df = pd.read_excel("adamodar_specifics.xlsx", sheet_name="skiprows", engine="openpyxl", index_col=0)
    skiprows = skiprows_df.loc[filename, 'skiprows']
    headers_df = pd.read_excel("adamodar_specifics.xlsx", sheet_name="header levels", engine="openpyxl", index_col=0)
    header_levels = headers_df.loc[filename, 'header levels']

    file_path = "{}.xls".format(filename)
    excel_file = pd.ExcelFile(file_path, engine="xlrd")
    sheet_names = excel_file.sheet_names

    if "Industry Averages" in sheet_names: 
        sheetname = "Industry Averages"
    else:
        sheetname = "Sheet1"

    if (header_levels ==1):
        data_df = pd.read_excel(file_path, sheet_name=sheetname, engine="xlrd", skiprows=int(skiprows), index_col=0) 
    else:
        data_df = pd.read_excel(file_path, sheet_name=sheetname, engine="xlrd", skiprows=int(skiprows), index_col=0, header=[0,1]) 

    return(data_df)

# ------------------------------------------------------------------------------------------------------------------
# extract_industry_tickers
# Description:
#   The function collects the stock tickers for all the U.S. companies that belong to one or more industries.
# The industry names are based on Prof. Damodaran's classification of industries( which can be obtained by using 
# the get_industry_list utility function) and not other methods such # as SIC code. In general it is better to use
# Professor's classification as it is based on careful study of what the company's actually do
#
# Inputs
#   industry_list: A python list of industry names
#   country_list: A python list of the names of the country. Optional argument. Use get_country_list() to see all 
#                 country names
# Output
#   ticker_list: A list of stock tickers corresponding to all the companies that belong to all the industries
# user supplied in the input
# ------------------------------------------------------------------------------------------------------------------
def extract_industry_tickers(industry_list, country_list=["United States"]):
    industry_df = get_raw_industry_df()
    valid_industry_values = industry_df["Industry Group"].unique()
    valid_country_values = industry_df["country"].unique()

    # Sanity check
    if not set(industry_list).issubset(set(valid_industry_values)):
        print("One or more industry values you input is wrong. The following are valid values")
        for indname in valid_industry_values:
            print(indname)
        sys.exit("Input Error")

    if not set(country_list).issubset(set(valid_country_values)):
        print("One or more country values you input is wrong. The following are valid values")
        for country in valid_country_values:
            print(country)
        sys.exit("Input Error")
    
    exchange_ticker_list = list(industry_df.loc[(industry_df["Industry Group"].isin(industry_list)) & (industry_df["Country"].isin(country_list)), 'Exchange:Ticker'])   # Extract only rows that correspond 
                                                                                                # to the industries we are interested in  
    ticker_list = list(map(lambda s:s.split(":")[1], exchange_ticker_list))
    return(ticker_list)

# ------------------------------------------------------------------------------------------------------------------
# get_industry_list
# Description:
#   The function gathers the industry names as Prof. Damodaran uses. 
# Inputs
#   None
# Output
#   indlist = A list of industry names
# ------------------------------------------------------------------------------------------------------------------
def get_industry_list():
    industry_df = get_raw_industry_df()
    indlist = industry_df["Industry Group"].unique()
    return(indlist)

# ------------------------------------------------------------------------------------------------------------------
# get_country_list
# Description:
#   The function gathers the country names as Prof. Damodaran uses. 
# Inputs
#   None
# Output
#   countrylist = A list of country names
# ------------------------------------------------------------------------------------------------------------------
def get_country_list():
    industry_df = get_raw_industry_df()
    countrylist = industry_df["Country"].unique()
    return(countrylist)

# ------------------------------------------------------------------------------------------------------------------
# get_sector_list
# Description:
#   The function gathers sectors different companies in an industry serve. Remember that, most often, the same sector
# would be connected to several industries. For instance, some companies in the "Apparel" industry as well as the
# "Autoparts" industry are both connected to the "Consumer Discretionary" sector. 
# Inputs
#   industry: The name of the industry as a string. To get a list of industries, use get_industry_list()
# Output
#   sectorlist = A list of sector names
# ------------------------------------------------------------------------------------------------------------------
def get_sector_list(industry):
    industry_df = get_industry_df()
    sectorlist = industry_df[industry_df.industry==industry]['sector'].unique()
    return(sectorlist)

# ------------------------------------------------------------------------------------------------------------------
# get_industry_df
# Description:
#   The function collects the company names, stock tickers, industry group, primary sector format for all the U.S. 
# companies that belong to one or more industries. The industry names are based on Prof. Damodaran's classification  
# of industries( which can be obtained by using the get_industry_list utility function) and not other methods such # 
# as SIC code. In general it is better to useProfessor's classification as it is based on careful study of what the 
# company's actually do
#
# Inputs
#   industry_list: A python list of industry names. This input is optional. If not provided, data is returned for 
#                  industries.
#   country_list: A python list of the names of the country. Optional argument. Use get_country_list() to see all 
#                 country names, if not provided, it defaults to only the United States.
#   no_pink: Tells the function to discard pink sheet stocks
# Output
#   industry_df: A pandas data frame containing the following columns:
#       'company_name': The name of the company
#       'exchange': NYSE, NASDAQ etc. (extended exchange tag, like "NASDAQGS")
#       '
# user supplied in the input
# ------------------------------------------------------------------------------------------------------------------
def get_industry_df(industry_list=None, country_list=["United States"], no_pink=True):
    rawdf = get_raw_industry_df()
    rawdf.drop(columns=['Broad Group', 'Sub Group'], inplace=True)
    if no_pink:
        subdf = rawdf[rawdf['Exchange:Ticker'].str.contains("OTCPK")==False]
    else:
        subdf = rawdf.copy()

    del rawdf

    if country_list==["All"]:
        if industry_list is None:
            industry_df = subdf.copy()
        else:
            industry_df = subdf[subdf["Industry Group"].isin(industry_list)].copy()
    else:
        if industry_list is None:
            industry_df = subdf[subdf['Country'].isin(country_list)].copy()
        else:
            industry_df = subdf[subdf["Industry Group"].isin(industry_list) & (subdf['Country'].isin(country_list))].copy()

        del subdf
    
    industry_df[['exchange', 'ticker']] = industry_df['Exchange:Ticker'].str.split(":", expand=True)
    industry_df.drop(columns=['Exchange:Ticker'],inplace=True)
    industry_df.rename(columns={'Company Name':'company', 'Industry Group':'industry', 'Primary Sector':'sector'}, inplace=True)

    return(industry_df)

# ------------------------------------------------------------------------------------------------------------------
# get_industry_and_sector
# Description:
#   For a given company ticker, returns the industry and sector that company belongs to
# Inputs
#   company ticker as a string. Ex. "MSFT"
# Output
#   [industry, sector] as a python list
# ------------------------------------------------------------------------------------------------------------------
def get_industry_and_sector(ticker):
    industry_df = get_industry_df()
    industry = industry_df[industry_df.ticker == ticker].iloc[0]['industry']
    sector = industry_df[industry_df.ticker == ticker].iloc[0]['sector']
    return([industry, sector])


# ------------------------------------------------------------------------------------------------------------------
# get_ind_fundamentals
# Description:
#   Returns data about industry fundamentals
# Inputs
#   industry_list: A python list of industry names. This input is optional. If not provided, data is returned for 
#                  all industries . If provided, data is returned for the given list of industries as well as 
#                  Total Market (without financials)
#   country_list: A python list of the names of the country. Optional argument. Use get_country_list() to see all 
#                 country names, if not provided, it defaults to only the United States.
# Output
#   fundamentals_df: A pandas dataframe with the index being industry names
# ------------------------------------------------------------------------------------------------------------------
def get_ind_fundamentals(industry_list=None, country_list=["United States"]):
    data_df = get_adamodar_file("DollarUS")
    cols_of_interest = ['Revenues ($ millions)', 'Gross Profit ($ millions)', 'EBITDA ($ millions)', 'EBIT (Operating Income) ($ millions)', 'Net Income ( $ millions)']
    rename_dict = {'Revenues ($ millions)': 'Revenue', 
                   'Gross Profit ($ millions)': 'Gross Profit', 
                   'EBITDA ($ millions)':'EBITDA', 
                   'EBIT (Operating Income) ($ millions)': 'EBIT', 
                   'Net Income ( $ millions)': 'Net Income'} 
    fundamentals_df = np.round(data_df[cols_of_interest].rename(columns = rename_dict)/1000).fillna(0).astype(int)

    if industry_list is None:
        return(fundamentals_df)
    else:
        industry_list.append('Total Market (without financials')
        return(fundamentals_df[fundamentals_df.index.isin(industry_list)])


# ------------------------------------------------------------------------------------------------------------------
# get_ind_efficiency
# Description:
#   Returns data about industry efficiency
# Inputs
#   industry_list: A python list of industry names. This input is optional. If not provided, data is returned for 
#                  all industries . If provided, data is returned for the given list of industries as well as 
#                  Total Market (without financials)
#   country_list: A python list of the names of the country. Optional argument. Use get_country_list() to see all 
#                 country names, if not provided, it defaults to only the United States.
# Output
#   efficiency_df: A pandas dataframe with the index being industry names
# ------------------------------------------------------------------------------------------------------------------
def get_ind_efficiency(industry_list=None, country_list=["United States"]):
    data_df = get_adamodar_file("wcdata")

    efficiency_df = pd.DataFrame(index=data_df.index)
    efficiency_df['DSO'] = np.round(data_df['Acc Rec/ Sales']*365)

    fundamentals_df = get_ind_fundamentals(industry_list=industry_list)
    cogs_ds = fundamentals_df['Revenue'] - fundamentals_df['Gross Profit']
    efficiency_df['DSI'] = np.round(data_df['Inventory/Sales']*fundamentals_df['Revenue']*365/cogs_ds)
    efficiency_df['DPO'] = np.round(data_df['Acc Pay/ Sales']*fundamentals_df['Revenue']*365/cogs_ds)

    data_df = get_adamodar_file("Employee")
    cols_of_interest = ['Revenues per Employee  ($)']
    efficiency_df[cols_of_interest] = data_df[cols_of_interest]
    
    if industry_list is None:
        return(efficiency_df)
    else:
        industry_list.append('Total Market (without financials')
        return(efficiency_df[efficiency_df.index.isin(industry_list)])


# ------------------------------------------------------------------------------------------------------------------
# get_ind_profitability
# Description:
#   Returns data about industry profitability
# Inputs
#   industry_list: A python list of industry names. This input is optional. If not provided, data is returned for 
#                  all industries . If provided, data is returned for the given list of industries as well as 
#                  Total Market (without financials)
#   country_list: A python list of the names of the country. Optional argument. Use get_country_list() to see all 
#                 country names, if not provided, it defaults to only the United States.
# Output
#   profitability_df: A pandas dataframe with the index being industry names
# ------------------------------------------------------------------------------------------------------------------
def get_ind_profitability(industry_list=None, country_list=["United States"]):
    data_df = get_adamodar_file("margin")
    cols_of_interest = ['Gross Margin', 'Net Margin', 'After-tax Lease & R&D adj Margin', 'EBITDA/Sales','R&D/Sales', 'SG&A/ Sales']
    rename_dict={'After-tax Lease & R&D adj Margin':'EBIT Margin', 
                 'EBITDA/Sales':'EBITDA_Margin',
                 'R&D/Sales':'R&D Margin', 
                 'SG&A/ Sales':'SG&A Margin'}
    profitability_df = np.round(data_df[cols_of_interest].rename(columns=rename_dict)*100).fillna(0).astype(int)

    data_df = get_adamodar_file("EVA")
    cols_of_interest = ['ROE', '(ROE - COE)', 'ROC', '(ROC - WACC)']
    profitability_df[cols_of_interest] = np.round(data_df[cols_of_interest]*100).fillna(0).astype(int)
    profitability_df['EVA'] = np.round(data_df['EVA (US $ millions)']/1000).fillna(0).astype(int)
    
    if industry_list is None:
        return(profitability_df)
    else:
        industry_list.append('Total Market (without financials')
        return(profitability_df[profitability_df.index.isin(industry_list)])


# ------------------------------------------------------------------------------------------------------------------
# get_ind_multiples
# Description:
#   Returns data about industry multiples
# Inputs
#   industry_list: A python list of industry names. This input is optional. If not provided, data is returned for 
#                  all industries . If provided, data is returned for the given list of industries as well as 
#                  Total Market (without financials)
#   country_list: A python list of the names of the country. Optional argument. Use get_country_list() to see all 
#                 country names, if not provided, it defaults to only the United States.
# Output
#   multiples_df: A pandas dataframe with the index being industry names
# ------------------------------------------------------------------------------------------------------------------
def get_ind_multiples(industry_list=None, country_list=["United States"]):
    data_df = get_adamodar_file("pbvdata")
    cols_of_interest = ['PBV', 'EV/ Invested Capital']
    multiples_df = data_df[cols_of_interest]

    data_df = get_adamodar_file("pedata")
    cols_of_interest = ['Current PE', 'Trailing PE', 'Forward PE']
    multiples_df[cols_of_interest] = data_df[cols_of_interest]

    data_df = get_adamodar_file("psdata")
    cols_of_interest = ['Price/Sales', 'EV/Sales']
    multiples_df[cols_of_interest] = data_df[cols_of_interest]

    data_df = get_adamodar_file("vebitda")
    cols_of_interest = [('Only positive EBITDA firms', 'EV/EBITDA'), ('Only positive EBITDA firms', 'EV/EBITDA')]

    multiples_df['EV/EBITDA'] = data_df[('Only positive EBITDA firms', 'EV/EBITDA')]
    multiples_df['EV/EBIT'] = data_df[('Only positive EBITDA firms', 'EV/EBIT')]

    multiples_df.loc[:,:] = np.round(multiples_df.loc[:,:],1)
    
    if industry_list is None:
        return(multiples_df)
    else:
        industry_list.append('Total Market (without financials')
        return(multiples_df[multiples_df.index.isin(industry_list)])


# ------------------------------------------------------------------------------------------------------------------
# get_ind_risk
# Description:
#   Returns data about industry risk
# Inputs
#   industry_list: A python list of industry names. This input is optional. If not provided, data is returned for 
#                  all industries . If provided, data is returned for the given list of industries as well as 
#                  Total Market (without financials)
#   country_list: A python list of the names of the country. Optional argument. Use get_country_list() to see all 
#                 country names, if not provided, it defaults to only the United States.
# Output
#   risk_df: A pandas dataframe with the index being industry names
# ------------------------------------------------------------------------------------------------------------------
def get_ind_risk(industry_list=None, country_list=["United States"]):
    data_df = get_adamodar_file("betas")
    average_beta_colname = data_df.filter(regex="^Average").columns[0] # Extract the column name for Average unlevered Beta corrected for cash 
    data_df.columns = data_df.columns.str.strip()
    risk_df = data_df[['Number of firms', 'D/E Ratio', average_beta_colname]].rename(columns = {average_beta_colname:'Beta', 'D/E Ratio':'D/E'})
    risk_df['Beta'] = np.round(risk_df['Beta'],2)
    risk_df['D/E'] = np.round(risk_df['D/E']*100)

    data_df = get_adamodar_file("wacc")
    cols_of_interest = ['Cost of Equity', 'After-tax Cost of Debt', 'Cost of Capital']
    risk_df[cols_of_interest] = np.round(data_df[cols_of_interest]*100,1)

    data_df = get_adamodar_file("pedata")
    risk_df['% of Money Losing firms'] = data_df['% of Money Losing firms (Trailing)']
    
    if industry_list is None:
        return(risk_df)
    else:
        industry_list.append('Total Market (without financials')
        return(risk_df[risk_df.index.isin(industry_list)])


# ------------------------------------------------------------------------------------------------------------------
# get_ind_demand
# Description:
#   Returns data about industry demand
# Inputs
#   industry_list: A python list of industry names. This input is optional. If not provided, data is returned for 
#                  all industries . If provided, data is returned for the given list of industries as well as 
#                  Total Market (without financials)
#   country_list: A python list of the names of the country. Optional argument. Use get_country_list() to see all 
#                 country names, if not provided, it defaults to only the United States.
# Output
#   demand_df: A pandas dataframe with the index being industry names
# ------------------------------------------------------------------------------------------------------------------
def get_ind_demand(industry_list=None, country_list=["United States"]):
    data_df = get_adamodar_file("histgr")
    cols_of_interest = ['CAGR in Net Income- Last 5 years', 'CAGR in Revenues- Last 5 years', 'Expected Growth in Revenues - Next 2 years', 'Expected Growth in Revenues - Next 5 years']
    rename_dict = {'CAGR in Net Income- Last 5 years': 'Net Income CAGR (past 5y)',
                   'CAGR in Revenues- Last 5 years':'Revenue CAGR (past 5y)',
                   'Expected Growth in Revenues - Next 2 years': 'Revenue CAGR (next 2y)',
                   'Expected Growth in Revenues - Next 5 years': 'Revenue CAGR (next 5y)'}
    demand_df = pd.DataFrame(index=data_df.index)
    demand_df['Net Income CAGR (past 5y)'] = np.round(data_df['CAGR in Net Income- Last 5 years']*100).fillna(0).astype(int)
    demand_df['Revenue CAGR (past 5y)'] = np.round(data_df['CAGR in Revenues- Last 5 years']*100).fillna(0).astype(int)
    demand_df['Revenue CAGR (next 2y)'] = np.round(data_df['Expected Growth in Revenues - Next 2 years']*100).fillna(0).astype(int)
    demand_df['Revenue CAGR (next 5y)'] = np.round(data_df['Expected Growth in Revenues - Next 5 years']*100).fillna(0).astype(int)

    if industry_list is None:
        return(demand_df)
    else:
        industry_list.append('Total Market (without financials')
        return(demand_df[demand_df.index.isin(industry_list)])
    

# ------------------------------------------------------------------------------------------------------------------
# get_industry_overview
# Description:
#   Returns data about industry including averages of fundamentals, ratios market values etc.
# Inputs
#   indname: Industry name
# Output
#   ind_dict: A python dictionary that has all the averages
# ------------------------------------------------------------------------------------------------------------------


