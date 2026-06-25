# Trading Strategy Backtesting Project

![GitHub Issues](https://img.shields.io/github/issues/Angad2005/Trading-Stratergy?style=for-the-badge)
![GitHub Stars](https://img.shields.io/github/stars/Angad2005/Trading-Stratergy?style=for-the-badge)
![GitHub Forks](https://img.shields.io/github/forks/Angad2005/Trading-Stratergy?style=for-the-badge)
![GitHub License](https://img.shields.io/github/license/Angad2005/Trading-Stratergy?style=for-the-badge)
![Python](https://img.shields.io/badge/python-3.7%2B-blue?style=for-the-badge)
![GitHub last commit](https://img.shields.io/github/last-commit/Angad2005/Trading-Stratergy?style=for-the-badge)

## What This Project Is About

This repository contains a complete, end-to-end quantitative trading strategy backtesting framework focused on a Bollinger Bands-based mean-reversion strategy enhanced with multiple technical indicators, dynamic risk management, and realistic trading costs. The project demonstrates the full lifecycle of strategy development: from data acquisition and signal generation to risk-adjusted position sizing, transaction cost modeling, regime analysis, and performance reporting.

It is designed as a portfolio piece for quantitative trading roles, showcasing both financial modeling rigor and software engineering best practices.

---

## Repository Contents

| File | Description |
|------|-------------|
| `bollinger_band_backtest.py` | **Main backtesting script**. Downloads market data, calculates indicators, generates trading signals, simulates trades with ATR-based position sizing, stop-loss/take-profit, commission & slippage, and reports performance metrics. Includes GPU acceleration via CuPy (with CPU fallback). |
| `test_bollinger_backtest.py` | **Unit test suite** using Python's `unittest` framework. Validates core functions (`calculate_rsi`, `backtest_ticker`) with synthetic data to ensure correctness and prevent regressions. |
| `requirements.txt` | Lists Python package dependencies (`yfinance`, `pandas`, `numpy`, `matplotlib`) with an optional note for GPU acceleration (`cupy-cuda12x`). |
| `README.md` | This file – comprehensive documentation of the project, workflow, outputs, and next steps. |
| `bollinger_band_backtest_original.py` | **Original version** of the backtesting script before enhancements (kept for reference/local debugging). |
| `debug_data.py` | **Debugging script** used during development to inspect the structure of data downloaded by `yfinance` (multi-index columns). |
| `*.png` | **Output visualization files** (generated when running the backtest): equity curves and Bollinger Band charts for each ticker. These are **not** tracked by Git (see `.gitignore`). |

---

## How to Run This Project

Executing `python3 bollinger_band_backtest.py` triggers the following sequence:

### 1. **Data Acquisition**
- Uses `yfinance` to download 2 years of daily OHLCV (Open, High, Low, Close, Volume) data for a predefined list of tickers: `['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META']`.
- Data is returned as a pandas DataFrame with **multi-index columns**: first level = price field (`Close`, `High`, etc.), second level = ticker symbol.
- Example: `data[('Close', 'AAPL')]` gives the closing price series for Apple.

### 2. **Indicator Calculation (Per Ticker)**
For each ticker, the script computes:
- **Bollinger Bands** (20-day SMA ± 2× standard deviation) – generates raw buy/sell signals.
- **Average True Range (ATR, 14-day)** – used for dynamic position sizing and stop-loss/take-profit levels.
- **Relative Strength Index (RSI, 14-day)** – optional filter: only take Bollinger Band buy signals when RSI < 30 (oversold) and sell signals when RSI > 70 (overbought).
- **Volume Moving Average (20-day)** – optional filter: only act on signals occurring on above-average volume.
- **Market Regime Classification** (based on 200-day MA):
  - **Bull**: Price > 200-day MA × 1.05
  - **Bear**: Price < 200-day MA × 0.95
  - **Sideways**: Price within ±5% of 200-day MA
  - Performance is later broken down by regime.

> 💡 **GPU Acceleration**: If `cupy` is installed, array comparisons for signal generation are performed on the GPU for speed; otherwise, falls back to NumPy on CPU.

### 3. **Signal Filtering & Position Logic**
- Raw Bollinger Band signals (buy = +1, sell = -1, hold = 0) are filtered by RSI and volume conditions.
- Only one position is allowed at a time (long or short).
- When a filtered signal appears and no position is open:
  - **Position Type**: Long for buy signal, short for sell signal.
  - **Entry Price**: Assumed to be the day's closing price.
  - **Stop-Loss & Take-Profit**:
    - Long: SL = Entry – (ATR × multiplier), TP = Entry + (ATR × multiplier)
    - Short: SL = Entry + (ATR × multiplier), TP = Entry – (ATR × multiplier)
    - Default multipliers: SL = 2.0× ATR, TP = 3.0× ATR (adjustable).
  - **Position Size**: Determined by risking 2% of current equity per trade.
    - Shares = (Equity × 0.02) / \|Entry Price – Stop-Loss\|
  - The position remains open until:
    - Stop-loss is hit (intra-day low ≤ SL for longs, high ≥ SL for shorts)
    - Take-profit is hit (intra-day high ≥ TP for longs, low ≤ TP for shorts)
    - An opposite filtered signal appears (exit at close)
    - End of data (exit at final close)

### 4. **Trade Execution & Cost Modeling**
- Each trade (entry + exit) incurs:
  - **Commission**: $1 per share (charged on both entry and exit).
  - **Slippage**: 0.1% of the trade price (applied to both entry and exit, based on average of entry/exit price).
- P&L is calculated after deducting these costs.
- Equity curve is updated daily, marking-to-market any open positions.

### 5. **Performance Metrics**
After processing all data, the script calculates:
- **Total Return**: (Ending Equity – Starting Equity) / Starting Equity
- **Sharpe Ratio**: Annualized (√252 × mean daily return / std daily return), assuming 0% risk-free rate.
- **Win Rate**: Percentage of trades with positive P&L.
- **Average Win / Average Loss**: Mean profit on winning trades, mean loss on losing trades.
- **Profit Factor**: (Gross Profit) / (Gross Loss)
- **Trade Statistics**: Number of trades, breakdown by exit reason (stop-loss, take-profit, opposite signal, end of data).
- **Regime Performance**: Total P&L, trade count, and average P&L per trade for Bull, Bear, Sideways, and Unknown regimes.

### 6. **Output Generation**
- **Console Output**: Detailed summary for each ticker and aggregate statistics (see [Sample Output](#sample-output)).
- **Visualizations** (saved as PNG files in the working directory):
  - `{TICKER}_enhanced_equity_curve.png`: Equity curve over time.
  - `{TICKER}_enhanced_bollinger_bands.png`: Price chart with Bollinger Bands, buy/sell signals marked (▲ for entry, ▼ for exit).
  - *(Note: Original Bollinger Band and cumulative return plots from the basic version are also generated if that script is run.)*

---

## Sample Output

When you run the script, you will see output similar to the following (values will vary slightly due to market data updates):

```
Downloading data for multiple tickers...

Backtesting AAPL with enhancements (transaction costs, slippage, RSI+volume filters) and regime analysis...
  Starting Equity: $100,000.00
  Ending Equity: $85,727.48
  Total Return: -14.27%
  Sharpe Ratio: -1.03
  Number of Trades: 16
  Win Rate: 31.25%
  Average Win: $2,381.09
  Average Loss: $-2,379.82
  Profit Factor: 0.45
  Regime Performance:
    bull: 8 trades, Total PnL: $-9,355.78, Avg PnL/trade: $-1,169.47
    bear: 1 trades, Total PnL: $2,580.48, Avg PnL/trade: $2,580.48
    sideways: 1 trades, Total PnL: $-2,558.57, Avg PnL/trade: $-2,558.57
    unknown: 6 trades, Total PnL: $-4,938.65, Avg PnL/trade: $-823.11

Backtesting MSFT with enhancements (transaction costs, slippage, RSI+volume filters) and regime analysis...
  Starting Equity: $100,000.00
  Ending Equity: $97,380.00
  Total Return: -2.62%
  Sharpe Ratio: -0.15
  Number of Trades: 18
  Win Rate: 44.44%
  Average Win: $2,637.31
  Average Loss: $-2,371.85
  Profit Factor: 0.89
  Regime Performance:
    bull: 3 trades, Total PnL: $-2,482.48, Avg PnL/trade: $-827.49
    bear: 6 trades, Total PnL: $-3,843.92, Avg PnL/trade: $-640.65
    sideways: 3 trades, Total PnL: $-2,158.15, Avg PnL/trade: $-719.38
    unknown: 6 trades, Total PnL: $5,864.55, Avg PnL/trade: $977.43

... (similar output for GOOGL, AMZN, META) ...

==================================================
AGGREGATE SUMMARY ACROSS ALL TICKERS (WITH ENHANCEMENTS AND REGIME ANALYSIS)
==================================================
Number of Tickers: 5
Average Total Return: -9.34%
Median Total Return: -11.01%
Average Sharpe Ratio: -0.66 (if available)
Average Win Rate: 35.24% (if available)
Average Profit Factor: 0.58 (if available)

Best Performer: MSFT (-2.62%)
Worst Performer: AAPL (-14.27%)

Aggregate Regime Performance Across All Tickers:
  bull: 25 trades, Total PnL: $-21,276.57, Avg PnL/trade: $-851.06
  bear: 11 trades, Total PnL: $4,040.48, Avg PnL/trade: $367.32
  sideways: 9 trades, Total PnL: $-5,871.41, Avg PnL/trade: $-652.38
  unknown: 31 trades, Total PnL: $-23,840.83, Avg PnL/trade: $-769.06

==================================================
ENHANCEMENTS SUMMARY
==================================================
✓ Position sizing and risk management (ATR-based stop-loss and take-profit)
✓ Testing on multiple stocks for robustness
✓ Transaction costs and slippage modeling
✓ Combining with other indicators (RSI and volume) to filter false signals
✓ Testing on different market regimes (bull, bear, sideways)

Next Steps for Further Improvement:
✓ Implement walk-forward optimization to avoid overfitting
✓ Consider machine learning models for signal prediction
✓ Add more sophisticated risk management (e.g., volatility targeting)
✓ Incorporate fundamental data and sentiment analysis
✓ Execute live trading with paper trading account
```

---

## Key Features Explained

### 🛡️ Position Sizing & Risk Management
- Uses **Average True Range (ATR)** to dynamically set stop-loss and take-profit levels, adapting to market volatility.
- Risks a fixed **2% of equity per trade**, ensuring consistent risk exposure regardless of signal frequency.
- Position size is calculated as:  
  `Shares = (Equity × Risk %) / \|Entry Price – Stop-Loss\|`  
  This ensures the maximum loss per trade (if stop-loss is hit) equals the predefined risk amount.

### 🔍 Technical Indicator Filters
- **RSI Filter**: Prevents buying in overbought conditions and selling in oversold conditions, increasing signal quality.
  - Buy only when RSI < 30 (oversold)
  - Sell only when RSI > 70 (overbought)
- **Volume Filter**: Confirms that price actions occur with sufficient market participation.
  - Only act on signals when today's volume ≥ 20-day average volume.
  - Reduces false signals from low-volume, noisy price movements.

### 📊 Market Regime Analysis
- Classifies each trading day into one of four regimes using a 200-day moving average:
  - **Bull**: Strong uptrend (price > 200-day MA × 1.05)
  - **Bear**: Strong downtrend (price < 200-day MA × 0.95)
  - **Sideways**: Range-bound market (price within ±5% of 200-day MA)
  - **Unknown**: Insufficient data (early in series) or invalid MA.
- Performance is reported separately for each regime, revealing how the strategy behaves in different market environments.
  - *Typical finding*: Mean-reversion strategies like Bollinger Bands often struggle in strong bull markets (trends persist) but may show value in bear or sideways regimes.

### 💰 Realistic Trading Costs
- **Commission**: Modeled as $1 per share (typical for retail brokerages; adjustable in code).
- **Slippage**: 0.1% of trade price to account for market impact and bid-ask spread (also adjustable).
- Costs are applied on both entry and exit, reflecting realistic round-trip trading expenses.
- This prevents overestimation of performance common in idealized backtests.

### 🚀 GPU Acceleration
- Attempts to use `cupy` (NumPy-compatible GPU array library) for the core signal generation step.
- If a compatible GPU and CUDA toolkit are available, this can significantly speed up indicator calculations for large universes or high-frequency data.
- Gracefully falls back to NumPy on CPU if `cupy` is not installed or no GPU is detected.
- No code changes required; the speedup is transparent.

### 🧪 Comprehensive Testing
- Includes a unit test suite (`test_bollinger_backtest.py`) that:
  - Validates the `calculate_rsi` function outputs values in the expected range [0, 100].
  - Tests the `backtest_ticker` function with synthetic data to ensure it runs without errors and returns the expected data structure.
- Enables safe refactoring and regression prevention.

---

## How to Run the Tests

To validate the core functions with synthetic data:

```bash
python3 -m unittest test_bollinger_backtest.py
```

Expected output:
```
..
----------------------------------------------------------------------
Ran 2 tests in 1.07s

OK
```

---

## Next Steps for Enhancement

As indicated in the script's output, consider these improvements to further strengthen the project:

1. **Walk-Forward Optimization**  
   Split data into in-sample (optimization) and out-of-sample (validation) periods to avoid overfitting and estimate true out-of-sample performance.

2. **Machine Learning for Signal Prediction**  
   Use classifiers (e.g., Random Forest, XGBoost) or neural networks to predict future Bollinger Band signal effectiveness based on multiple features.

3. **Advanced Risk Management**  
   Implement volatility targeting (e.g., constant volatility portfolio) or Kelly criterion-based position sizing.

4. **Fundamental & Sentiment Data**  
   Incorporate earnings data, analyst ratings, news sentiment, or macroeconomic indicators to filter or enhance signals.

5. **Live Paper Trading**  
   Connect to a paper trading API (e.g., Alpaca, Interactive Brokers) to execute the strategy in real-time with simulated capital.

6. **Order Types & Execution Logic**  
   Use limit orders instead of market orders to reduce slippage, or implement VWAP/TWAP execution algorithms.

7. **Portfolio-Level Risk Management**  
   Allow multiple concurrent positions with correlation-based diversification and aggregate risk limits (e.g., max portfolio drawdown, VaR).

---

## Disclaimer

⚠️ **This project is for educational and research purposes only.**  
Past performance is not indicative of future results. Trading involves substantial risk, including the possible loss of principal. The author is not responsible for any financial losses incurred from using this code. Always conduct your own research, consider your financial situation and risk tolerance, and consult with a qualified financial advisor before making investment decisions.

---

## License

MIT License

Copyright (c) 2026 Angad2005

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
DEALINGS IN THE SOFTWARE.

---

*Last updated: June 25, 2026*  
*Created for demonstration of quantitative trading strategy development skills.*  