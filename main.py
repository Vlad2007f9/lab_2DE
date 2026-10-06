import pandas as pd
import numpy as np
import requests
import json
from datetime import date, timedelta, datetime
from bs4 import BeautifulSoup
import yfinance as yf


def mathhey_data(start_date, end_date, metals=['Pt', 'Pd', 'Rh', 'Ir', 'Ru'], market='London'):

    data = {
        '_jm_metal_price_portlet_JmMetalPricePortlet_start_Date': start_date,
        '_jm_metal_price_portlet_JmMetalPricePortlet_end_Date': end_date,
        '_jm_metal_price_portlet_JmMetalPricePortlet_IntervalType': 'DAILY'
    }

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'X-Requested-With': 'XMLHttpRequest', 'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'
    }

    for idx, metal in enumerate(metals):
        data[f'_jm_metal_price_portlet_JmMetalPricePortlet_selectedMetal{idx}'] = metal

    zone_mapping = {
        'LONDON': 'LONDON',
        'ASIA': 'HONGKONG',
        'HONGKONG': 'HONGKONG',
        'USA': 'NEWYORK',
        'NEWYORK': 'NEWYORK',
    }

    data['_jm_metal_price_portlet_JmMetalPricePortlet_zone'] = zone_mapping.get(market.upper(), 'LONDON')

    response = requests.post(url='https://matthey.com/products-and-markets/pgms-and-circularity/pgm-management?p_p_id=jm_metal_price_portlet_JmMetalPricePortlet&p_p_lifecycle=2&p_p_state=normal&p_p_mode=view&p_p_cacheability=cacheLevelPage', data=data, headers=headers)

    if response.status_code == 200:
        response_json = json.loads(response.text)
        csv_json = response_json['url']

        df_matthey = pd.read_csv(csv_json, header=[1])
        df_matthey['Date'] = pd.to_datetime(df_matthey['Date'])
        return df_matthey
    else:
        print(f"Error Matthey: {response.status_code}")
        return None

df_matthey = mathhey_data('01-01-1990', date.today().strftime('%d-%m-%Y'), metals=['Pd', 'Pt', 'Ir'], market='London')
df_matthey = df_matthey.rename(columns={'Palladium': 'Palladium_Matthey', 'Platinum': 'Platinum_Matthey', 'Iridium' : "Iridium_Matthey"})
print(df_matthey)
print("\n")

def kitco_data(hubs, curr):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json',
        'Origin': 'https://www.kitco.com',
        'Referer': 'https://www.kitco.com/',
        'X-Requested-With': 'XMLHttpRequest'
    }

    all_data = {}

    for year in range(2014, 2027):
        params = {'year': year}

        response = requests.get(url='https://www.kitco.com/api/proxy-historical-data', headers=headers, params=params)

        if response.status_code == 200:
            all_data[year] = response.json()
        else:
            print(f"Error: {response.status_code})")

    rows = []
    for year, year_data in all_data.items():
        if not isinstance(year_data, dict) or "data" not in year_data:
            continue

        for date, date_info in year_data['data'].items():
            for hub, hub_info in date_info.get('hubs', {}).items():
                if hub != hubs:
                    continue

                for metal, currencies in hub_info.get('lookup', {}).items():
                    if curr in currencies:
                        rows.append({'Date' : date, "Metal" : metal, "Price" : currencies[curr]})
    df = pd.DataFrame(rows)
    metal_names = {
        'AU': 'Gold',
        'AG': 'Silver',
        'PT': 'Platinum',
        'PD': 'Palladium'
    }
    df['Metal'] = df['Metal'].map(metal_names).fillna(df['Metal'])

    df_wide = df.pivot(index='Date', columns='Metal', values='Price').reset_index()
    df_wide['Date'] = pd.to_datetime(df_wide['Date'])
    df_wide = df_wide.sort_values('Date').reset_index(drop=True)
    df_wide = df_wide[['Date', 'Gold', 'Silver', 'Platinum', 'Palladium']]

    return df_wide

df_kitco = kitco_data("London", "USD")
df_kitco = df_kitco.rename(columns={'Gold' : 'Gold_Kitco', 'Silver' : 'Silver_Kitco', 'Platinum' : 'Platinum_Kitco', 'Palladium' : 'Palladium_Kitco'})
print(df_kitco)
print("\n")

def yahoo_data():
    df_y = yf.download(tickers=["GLD", "SLV"], start="2019-01-01")['Close'].reset_index()

    df_y['Date'] = pd.to_datetime(df_y['Date'])
    df_y.columns.name = None
    return df_y

df_yahoo = yahoo_data()
df_yahoo = df_yahoo.rename(columns={'GLD' : 'Gold_Yahoo', 'SLV' : 'Silver_Yahoo'})
print(df_yahoo)
print("\n")

df_indices = pd.read_csv('final_harmonized_dataset.csv', usecols=['Date', 'SP_500', 'FTSE_100'])
df_indices['Date'] = pd.to_datetime(df_indices['Date'])
print(df_indices)
print("\n")

df_main = pd.merge(df_kitco, df_matthey, on='Date', how='outer')
df_main = pd.merge(df_main, df_yahoo, on='Date', how='outer')
df_main = pd.merge(df_main, df_indices, on='Date', how='outer')
df_main = df_main.sort_values('Date').reset_index(drop=True)
df_main = df_main.ffill()
df_main.to_csv('main_dataset.csv', index=False, encoding='utf-8')

print(df_main)