"""
Optimal Crypto Trading Strategy Based on Liquidity and Momentum

This script implements a strategy inspired by the paper
"Optimal Bitcoin Trading Strategy Development Using Quantitative Models for the Current Market Regime".

The strategy combines four key factors:
1. Liquidity Ratio: Volume / Market Capitalization
2. Momentum: 5-day, 10-day, and 20-day returns
3. Position Score: The average of standardized (z-score) versions of the above factors
4. Buy/Sell signals based on Position Score thresholds

Optimization:
- buy_thresh ∈ [0.1, 1.0]
- sell_thresh ∈ [-1.0, -0.1]
- gp_minimize is used to find thresholds that maximize cumulative strategy return

Assets Supported:
- BTC-USD, ETH-USD, LTC-USD (via CoinGecko API for circulating supply)

Data:
- Daily candles from Yahoo Finance
- Evaluation from 2017 to mid-2024

Usage:
- Run main() to execute optimization and backtest
- Output is a cumulative returns plot vs. the market
"""

import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from src.analyzer.tickers_list import get_circulating_supply

# -------------------------------
# Load BTC data
# -------------------------------
import requests


def load_data(ticker='BTC-USD'):
    df = yf.download(ticker, start='2017-01-01', end='2024-06-30')
    df = df[['Close', 'Volume']].dropna()
    supply = get_circulating_supply(ticker)  # fallback
    df['MarketCap'] = df['Close'] * supply  # Approx circulating BTC supply
    df['Liquidity'] = df['Volume'] / df['MarketCap']
    df['Return_5d'] = df['Close'].pct_change(5)
    df['Return_10d'] = df['Close'].pct_change(10)
    df['Return_20d'] = df['Close'].pct_change(20)
    df.dropna(inplace=True)
    return df

# -------------------------------
# Compute Position Score
# -------------------------------
def compute_score(df):
    for col in ['Return_5d', 'Return_10d', 'Return_20d', 'Liquidity']:
        df[f'z_{col}'] = (df[col] - df[col].rolling(252).mean()) / df[col].rolling(252).std()
    df['PositionScore'] = df[['z_Return_5d', 'z_Return_10d', 'z_Return_20d', 'z_Liquidity']].mean(axis=1)
    return df.dropna()

# -------------------------------
# Generate Buy/Sell Signals
# -------------------------------
def generate_signals(df, buy_thresh=0.5, sell_thresh=-0.5):
    df['Signal'] = 0
    df.loc[df['PositionScore'] > buy_thresh, 'Signal'] = 1
    df.loc[df['PositionScore'] < sell_thresh, 'Signal'] = -1
    return df

# -------------------------------
# Simulate Strategy
# -------------------------------
def backtest(df):
    df['Position'] = df['Signal'].shift().fillna(0)
    df['StrategyReturn'] = df['Position'] * df['Close'].pct_change()
    df['CumulativeStrategy'] = (1 + df['StrategyReturn']).cumprod()
    df['CumulativeMarket'] = (1 + df['Close'].pct_change()).cumprod()
    return df

# -------------------------------
# Visualization
# -------------------------------
def plot_strategy(df):
    plt.figure(figsize=(14, 6))
    plt.plot(df.index, df['CumulativeStrategy'], label='Strategy')
    plt.plot(df.index, df['CumulativeMarket'], label='Market', linestyle='--')
    plt.title('Cumulative Returns')
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.show()

# -------------------------------
# Optimization using gp_minimize
# -------------------------------
from skopt import gp_minimize
from skopt.space import Real

def evaluate_strategy(params):
    buy_thresh, sell_thresh = params
    df = load_data('LTC-USD')
    df = compute_score(df)
    df = generate_signals(df, buy_thresh=buy_thresh, sell_thresh=sell_thresh)
    df = backtest(df)
    final_value = df['CumulativeStrategy'].iloc[-1]
    return -final_value  # Negative because we minimize

def optimize_thresholds():
    space = [
        Real(0.1, 1.0, name='buy_thresh'),
        Real(-1.0, -0.1, name='sell_thresh')
    ]
    res = gp_minimize(evaluate_strategy, space, n_calls=30, random_state=42)
    print("Best buy threshold:", res.x[0])
    print("Best sell threshold:", res.x[1])
    return res.x

def main():
    best_buy, best_sell = optimize_thresholds()
    df = load_data('LTC-USD')
    df = compute_score(df)
    df = generate_signals(df, buy_thresh=best_buy, sell_thresh=best_sell)
    df = backtest(df)
    plot_strategy(df)

if __name__ == '__main__':
    main()
