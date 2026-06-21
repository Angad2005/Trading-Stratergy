# Trading Strategy Backtesting Project

This project implements and backtests various trading strategies, with a primary focus on Bollinger Bands strategy enhanced with multiple technical indicators, risk management, and regime analysis.

## Features

- **Bollinger Band Strategy**: Classic 20-day SMA ± 2 standard deviations approach
- **Enhanced Risk Management**: 
  - ATR-based position sizing (2% risk per trade)
  - Dynamic stop-loss and take-profit levels
- **Multiple Technical Indicators**:
  - Bollinger Bands (primary signal)
  - RSI (Relative Strength Index) for overbought/oversold filtering
  - Volume confirmation filters
- **Market Regime Analysis**:
  - Automatic classification of Bull/Bear/Sideways markets
  - Performance breakdown by market regime
- **Realistic Trading Costs**:
  - Commission modeling ($1 per share)
  - Slippage modeling (0.1% of trade value)
- **Multi-Asset Testing**:
  - Backtested on AAPL, MSFT, GOOGL, AMZN, META
  - Aggregated performance statistics
- **GPU Acceleration**:
  - Optional CuPy support for faster indicator calculations
  - Automatic fallback to CPU if GPU not available
- **Comprehensive Testing**:
  - Unit test suite for core functions
  - Synthetic data testing for validation
- **Visualization**:
  - Equity curve plots for each stock
  - Bollinger Band charts with signal markers

## Files

- `bollinger_band_backtest.py`: Main backtesting script with all enhancements
- `test_bollinger_backtest.py`: Unit tests for the backtesting functions
- `bollinger_band_backtest_original.py`: Original version before enhancements
- `debug_data.py`: Script used for debugging data structure
- `*.png`: Output visualization charts (equity curves, signal charts)

## Requirements

- Python 3.7+
- Core dependencies:
  - yfinance
  - pandas
  - numpy
  - matplotlib
- Optional for GPU acceleration:
  - cupy-cuda12x (or appropriate CUDA version)

Install with:
```bash
pip install yfinance pandas numpy matplotlib
# For GPU acceleration (optional):
pip install cupy-cuda12x  # or appropriate version for your CUDA toolkit
```

## Usage

Run the full backtesting analysis:
```bash
python3 bollinger_band_backtest.py
```

This will:
1. Download 2 years of historical data for AAPL, MSFT, GOOGL, AMZN, META
2. Run the enhanced Bollinger Band strategy with:
   - ATR-based position sizing and risk management
   - RSI and volume filters
   - Transaction costs and slippage
   - Market regime analysis (Bull/Bear/Sideways)
3. Generate equity curve charts for each stock
4. Print comprehensive performance metrics including:
   - Total return
   - Sharpe ratio
   - Win rate
   - Profit factor
   - Regime-specific performance
5. Save all plots as PNG files in the directory

Run unit tests:
```bash
python3 -m unittest test_bollinger_backtest.py
```

## Key Features Explained

### Position Sizing & Risk Management
- Uses Average True Range (ATR) to dynamically set stop-loss and take-profit levels
- Risks a fixed percentage (2%) of equity per trade
- Calculates appropriate position size based on risk per share

### Technical Indicator Filters
- **RSI Filter**: Only takes Bollinger Band buy signals when RSI < 30 (oversold) and sell signals when RSI > 70 (overbought)
- **Volume Filter**: Only acts on signals that occur on above-average trading volume

### Market Regime Analysis
- Classifies each day as Bull, Bear, or Sideways based on price relative to 200-day moving average
- Bull: Price > 200-day MA × 1.05
- Bear: Price < 200-day MA × 0.95
- Sideways: Price within ±5% of 200-day MA
- Reports strategy performance separately for each regime

### Performance Metrics
- Total return (%)
- Sharpe ratio (annualized, assuming 0% risk-free rate)
- Win rate (%)
- Average win/loss amounts
- Profit factor (gross profit / gross loss)
- Trade count and breakdown by exit reason

## Sample Output

The script produces output similar to:

```
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
```

## Next Steps for Enhancement

As noted in the script's output, potential improvements include:
1. Implement walk-forward optimization to avoid overfitting
2. Consider machine learning models for signal prediction
3. Add more sophisticated risk management (e.g., volatility targeting)
4. Incorporate fundamental data and sentiment analysis
5. Execute live trading with paper trading account
6. Add more sophisticated order types (limit orders, etc.)
7. Implement portfolio-level risk management across multiple positions

## Disclaimer

This project is for educational and research purposes only. Past performance is not indicative of future results. Trading involves risk, including the possible loss of principal. The author is not responsible for any financial losses incurred from using this code. Always conduct your own research and consider consulting with a financial advisor before making investment decisions.

## License

MIT License - feel free to use, modify, and distribute this code for personal or educational purposes.