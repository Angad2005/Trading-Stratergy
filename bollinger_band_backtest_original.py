import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
try:
    import cupy as cp
    GPU_AVAILABLE = True
except ImportError:
    GPU_AVAILABLE = False
    cp = np  # fallback

# Download data
ticker = "AAPL"
data = yf.download(ticker, period="2y")  # last 2 years

# Extract the close series (and other series) from the multi-index columns
close = data[('Close', ticker)]
high = data[('High', ticker)]
low = data[('Low', ticker)]
open_price = data[('Open', ticker)]
volume = data[('Volume', ticker)]

# Calculate Bollinger Bands on close prices
window = 20
# Convert to cupy arrays if GPU available
close_vals = cp.asarray(close.values) if GPU_AVAILABLE else close.values
# Compute rolling mean and std using cupy? cupy doesn't have built-in rolling, we can use convolution or use pandas then transfer.
# Simpler: compute using pandas then transfer to GPU for signal generation.
SMA = close.rolling(window=window).mean()
STD = close.rolling(window=window).std()
Upper = SMA + (STD * 2)
Lower = SMA - (STD * 2)

# Convert bands to cupy for comparison
upper_vals = cp.asarray(Upper.values) if GPU_AVAILABLE else Upper.values
lower_vals = cp.asarray(Lower.values) if GPU_AVAILABLE else Lower.values
close_vals = cp.asarray(close.values) if GPU_AVAILABLE else close.values

# Generate signals using cupy
Signal = cp.zeros_like(close_vals, dtype=cp.int8)
Signal = cp.where(close_vals < lower_vals, 1, Signal)
Signal = cp.where(close_vals > upper_vals, -1, Signal)

# If GPU, bring back to numpy for pandas series
if GPU_AVAILABLE:
    Signal = cp.asnumpy(Signal)
else:
    Signal = Signal  # already numpy

Signal = pd.Series(Signal, index=close.index)

# Debug: print signal counts
print(f"Number of buy signals: {(Signal == 1).sum()}")
print(f"Number of sell signals: {(Signal == -1).sum()}")

# To avoid consecutive signals, we can only change position when signal changes
# Replace 0 with NaN, forward fill, then fill remaining NaN with 0
Position = Signal.replace(0, np.nan).ffill().fillna(0)

# Debug: print position changes
print(f"Number of position changes: {(Position.diff() != 0).sum()}")

# Calculate returns
Market_Return = close.pct_change()
Strategy_Return = Market_Return * Position.shift(1)

# Calculate cumulative returns
Cumulative_Market = (1 + Market_Return).cumprod()
Cumulative_Strategy = (1 + Strategy_Return).cumprod()

# Plot price and Bollinger Bands
plt.figure(figsize=(14, 7))
plt.plot(close, label='Close Price', alpha=0.5)
plt.plot(Upper, label='Upper Band', alpha=0.5)
plt.plot(Lower, label='Lower Band', alpha=0.5)
plt.fill_between(close.index, Upper, Lower, alpha=0.1)
plt.title(f'{ticker} Bollinger Band Strategy')
plt.legend()
plt.savefig(f'/home/angad/Trading-Stratergy/{ticker}_bollinger_bands.png')
plt.close()

# Plot cumulative returns
plt.figure(figsize=(14, 7))
plt.plot(Cumulative_Market, label='Buy and Hold')
plt.plot(Cumulative_Strategy, label='Bollinger Band Strategy')
plt.title(f'{ticker} Cumulative Returns')
plt.legend()
plt.savefig(f'/home/angad/Trading-Stratergy/{ticker}_cumulative_returns.png')
plt.close()

# Print performance metrics
total_market_return = Cumulative_Market.iloc[-1] - 1
total_strategy_return = Cumulative_Strategy.iloc[-1] - 1
print(f"Total Market Return: {total_market_return:.2%}")
print(f"Total Strategy Return: {total_strategy_return:.2%}")

# Also calculate Sharpe ratio (assuming risk-free rate 0)
# Avoid division by zero
if Strategy_Return.std() != 0:
    sharpe_strategy = np.sqrt(252) * Strategy_Return.mean() / Strategy_Return.std()
else:
    sharpe_strategy = np.nan
if Market_Return.std() != 0:
    sharpe_market = np.sqrt(252) * Market_Return.mean() / Market_Return.std()
else:
    sharpe_market = np.nan
print(f"Sharpe Ratio (Market): {sharpe_market:.2f}")
print(f"Sharpe Ratio (Strategy): {sharpe_strategy:.2f}")

# Show the last few rows of data with signals and positions
print("\nLast 10 rows:")
df_plot = pd.DataFrame({
    'Close': close,
    'Upper': Upper,
    'Lower': Lower,
    'Signal': Signal,
    'Position': Position
})
print(df_plot.tail(10))

if GPU_AVAILABLE:
    print("\nGPU acceleration used via CuPy.")
else:
    print("\nGPU not available, using CPU.")