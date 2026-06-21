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

def calculate_rsi(series, window=14):
    """Calculate Relative Strength Index."""
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def backtest_ticker(ticker, data, 
                    risk_per_trade=0.02, 
                    atr_sl_multiplier=2.0, 
                    atr_tp_multiplier=3.0,
                    commission_per_trade=1.0,  # $1 per share
                    slippage_percent=0.001,    # 0.1% slippage
                    use_rsi_filter=False, 
                    rsi_window=14,
                    rsi_oversold=30,
                    rsi_overbought=70,
                    use_volume_filter=False,
                    volume_ma_window=20,
                    regime_ma_window=200,
                    regime_threshold=0.05):
    """
    Backtest the enhanced Bollinger Band strategy for a single ticker.
    data: DataFrame with multi-index columns (Price, Ticker) for the given ticker.
    Returns: dict of performance metrics and equity curve.
    """
    # Extract the close series (and other series) from the multi-index columns
    close = data[('Close', ticker)]
    high = data[('High', ticker)]
    low = data[('Low', ticker)]
    open_price = data[('Open', ticker)]
    volume = data[('Volume', ticker)]
    
    # Calculate Bollinger Bands
    window = 20
    SMA = close.rolling(window=window).mean()
    STD = close.rolling(window=window).std()
    Upper = SMA + (STD * 2)
    Lower = SMA - (STD * 2)
    
    # Calculate ATR (Average True Range) for position sizing and stop-loss
    atr_window = 14
    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    ATR = tr.rolling(window=atr_window).mean()
    
    # Calculate RSI if needed
    if use_rsi_filter:
        RSI = calculate_rsi(close, window=rsi_window)
    else:
        RSI = pd.Series(50, index=close.index)  # dummy
    
    # Calculate volume moving average if needed
    if use_volume_filter:
        volume_ma = volume.rolling(window=volume_ma_window).mean()
    else:
        volume_ma = pd.Series(np.inf, index=close.index)  # dummy so condition always passes
    
    # Calculate regime based on MA
    ma = close.rolling(window=regime_ma_window).mean()
    # Avoid division by zero or NaN
    regime = pd.Series('unknown', index=close.index)
    for i in range(len(close)):
        if pd.isna(ma.iloc[i]) or ma.iloc[i] == 0:
            regime.iloc[i] = 'unknown'
        else:
            if close.iloc[i] > ma.iloc[i] * (1 + regime_threshold):
                regime.iloc[i] = 'bull'
            elif close.iloc[i] < ma.iloc[i] * (1 - regime_threshold):
                regime.iloc[i] = 'bear'
            else:
                regime.iloc[i] = 'sideways'
    
    # Generate raw Bollinger Band signals
    raw_signal = pd.Series(0, index=close.index)
    # Using GPU for comparison if available
    if GPU_AVAILABLE:
        close_vals = cp.asarray(close.values)
        lower_vals = cp.asarray(Lower.values)
        upper_vals = cp.asarray(Upper.values)
        Signal_vals = cp.where(close_vals < lower_vals, 1, 0)
        Signal_vals = cp.where(close_vals > upper_vals, -1, Signal_vals)
        raw_signal = pd.Series(cp.asnumpy(Signal_vals), index=close.index)
    else:
        raw_signal = np.where(close.values < Lower.values, 1, 0)
        raw_signal = np.where(close.values > Upper.values, -1, raw_signal)
        raw_signal = pd.Series(raw_signal, index=close.index)
    
    # Apply filters: RSI and volume
    Signal = pd.Series(0, index=close.index)
    for i in range(len(close)):
        if raw_signal.iloc[i] == 1:  # Buy signal
            # Check RSI oversold and volume above average
            if (not use_rsi_filter or RSI.iloc[i] <= rsi_oversold) and \
               (not use_volume_filter or volume.iloc[i] >= volume_ma.iloc[i]):
                Signal.iloc[i] = 1
        elif raw_signal.iloc[i] == -1:  # Sell signal
            # Check RSI overbought and volume above average
            if (not use_rsi_filter or RSI.iloc[i] >= rsi_overbought) and \
               (not use_volume_filter or volume.iloc[i] >= volume_ma.iloc[i]):
                Signal.iloc[i] = -1
    
    # Parameters for risk management
    # Initialize variables for backtesting
    equity = 100000  # Starting capital per ticker
    equity_curve = [equity]
    positions = []  # List to hold open positions as dicts
    trades = []  # List to hold completed trades
    # For regime analysis: collect PnL per regime
    regime_pnl = {'bull': 0.0, 'bear': 0.0, 'sideways': 0.0, 'unknown': 0.0}
    regime_trade_counts = {'bull': 0, 'bear': 0, 'sideways': 0, 'unknown': 0}
    
    # We'll iterate through each day
    for i in range(len(close)):
        current_date = close.index[i]
        current_close = close.iloc[i]
        current_high = high.iloc[i]
        current_low = low.iloc[i]
        current_atr = ATR.iloc[i] if not pd.isna(ATR.iloc[i]) else 0
        current_regime = regime.iloc[i]
        
        # Process open positions: check for stop-loss, take-profit, or opposite signal
        new_positions = []
        for pos in positions:
            entry_date = pos['entry_date']
            entry_price = pos['entry_price']
            position_type = pos['type']  # 'long' or 'short'
            shares = pos['shares']
            stop_loss = pos['stop_loss']
            take_profit = pos['take_profit']
            
            exit_flag = False
            exit_price = 0
            exit_reason = ''
            
            # Check stop-loss and take-profit based on intra-day high/low
            if position_type == 'long':
                if current_low <= stop_loss:
                    exit_flag = True
                    exit_price = stop_loss
                    exit_reason = 'stop_loss'
                elif current_high >= take_profit:
                    exit_flag = True
                    exit_price = take_profit
                    exit_reason = 'take_profit'
                # Also check for opposite signal (sell signal)
                elif Signal.iloc[i] == -1:
                    exit_flag = True
                    exit_price = current_close  # Exit at close
                    exit_reason = 'opposite_signal'
            else:  # short
                if current_high >= stop_loss:
                    exit_flag = True
                    exit_price = stop_loss
                    exit_reason = 'stop_loss'
                elif current_low <= take_profit:
                    exit_flag = True
                    exit_price = take_profit
                    exit_reason = 'take_profit'
                # Also check for opposite signal (buy signal)
                elif Signal.iloc[i] == 1:
                    exit_flag = True
                    exit_price = current_close  # Exit at close
                    exit_reason = 'opposite_signal'
            
            if exit_flag:
                # Calculate profit/loss before costs
                if position_type == 'long':
                    pnl = (exit_price - entry_price) * shares
                else:
                    pnl = (entry_price - exit_price) * shares
                
                # Subtract costs: commission and slippage
                # Commission: per share
                commission = commission_per_trade * shares * 2  # enter and exit
                # Slippage: percent of price * shares * 2 (enter and exit)
                slippage = (slippage_percent * (entry_price + exit_price) / 2) * shares * 2
                pnl -= (commission + slippage)
                
                equity += pnl
                # Record trade with regime at entry
                entry_regime = regime.loc[entry_date] if entry_date in regime.index else 'unknown'
                trades.append({
                    'entry_date': entry_date,
                    'exit_date': current_date,
                    'type': position_type,
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'shares': shares,
                    'pnl': pnl,
                    'exit_reason': exit_reason,
                    'commission': commission,
                    'slippage': slippage,
                    'entry_regime': entry_regime
                })
                # Update regime PnL and count
                regime_pnl[entry_regime] = regime_pnl.get(entry_regime, 0.0) + pnl
                regime_trade_counts[entry_regime] = regime_trade_counts.get(entry_regime, 0) + 1
            else:
                # Keep position open
                new_positions.append(pos)
        
        positions = new_positions
        
        # Check for new signals to enter
        if Signal.iloc[i] != 0 and len(positions) == 0:  # Only one position at a time for simplicity
            # Determine position type
            if Signal.iloc[i] == 1:
                position_type = 'long'
                entry_price = current_close  # Enter at close (or next day open? we use close for simplicity)
            else:  # Signal == -1
                position_type = 'short'
                entry_price = current_close
            
            # Calculate stop-loss and take-profit based on ATR
            if current_atr > 0:
                if position_type == 'long':
                    stop_loss = entry_price - (atr_sl_multiplier * current_atr)
                    take_profit = entry_price + (atr_tp_multiplier * current_atr)
                else:  # short
                    stop_loss = entry_price + (atr_sl_multiplier * current_atr)
                    take_profit = entry_price - (atr_tp_multiplier * current_atr)
                
                # Risk per share = |entry_price - stop_loss|
                risk_per_share = abs(entry_price - stop_loss)
                if risk_per_share > 0:
                    # Number of shares to risk 'risk_per_trade' of equity
                    shares = (equity * risk_per_trade) / risk_per_share
                else:
                    shares = 0
                
                if shares > 0:
                    positions.append({
                        'entry_date': current_date,
                        'entry_price': entry_price,
                        'type': position_type,
                        'shares': shares,
                        'stop_loss': stop_loss,
                        'take_profit': take_profit
                    })
        
        # Record equity for this day (mark-to-market)
        current_equity = equity
        for pos in positions:
            if pos['type'] == 'long':
                current_equity += (current_close - pos['entry_price']) * pos['shares']
            else:
                current_equity += (pos['entry_price'] - current_close) * pos['shares']
        equity_curve.append(current_equity)
    
    # After loop, close any remaining positions at the last close
    for pos in positions:
        exit_price = close.iloc[-1]
        if pos['type'] == 'long':
            pnl = (exit_price - pos['entry_price']) * pos['shares']
        else:
            pnl = (pos['entry_price'] - exit_price) * pos['shares']
        # Subtract costs for closing
        commission = commission_per_trade * pos['shares'] * 2  # we already paid commission on entry? Actually we pay on exit only for commission? Let's assume we pay commission on both entry and exit.
        # We didn't charge commission on entry, so we charge for both entry and exit here.
        commission = commission_per_trade * pos['shares'] * 2
        slippage = (slippage_percent * (pos['entry_price'] + exit_price) / 2) * pos['shares'] * 2
        pnl -= (commission + slippage)
        equity += pnl
        # Record trade with regime at entry
        entry_regime = regime.loc[pos['entry_date']] if pos['entry_date'] in regime.index else 'unknown'
        trades.append({
            'entry_date': pos['entry_date'],
            'exit_date': close.index[-1],
            'type': pos['type'],
            'entry_price': pos['entry_price'],
            'exit_price': exit_price,
            'shares': pos['shares'],
            'pnl': pnl,
            'exit_reason': 'end_of_data',
            'commission': commission,
            'slippage': slippage,
            'entry_regime': entry_regime
        })
        # Update regime PnL and count
        regime_pnl[entry_regime] = regime_pnl.get(entry_regime, 0.0) + pnl
        regime_trade_counts[entry_regime] = regime_trade_counts.get(entry_regime, 0) + 1
    
    # Calculate performance metrics
    total_return = (equity_curve[-1] - equity_curve[0]) / equity_curve[0]
    # Daily returns of equity curve
    equity_series = pd.Series(equity_curve, index=[close.index[0]] + list(close.index))
    daily_returns = equity_series.pct_change().fillna(0)
    if daily_returns.std() != 0:
        sharpe_ratio = np.sqrt(252) * daily_returns.mean() / daily_returns.std()
    else:
        sharpe_ratio = np.nan
    
    win_rate = np.nan
    avg_win = np.nan
    avg_loss = np.nan
    profit_factor = np.nan
    if trades:
        winning_trades = [t for t in trades if t['pnl'] > 0]
        win_rate = len(winning_trades) / len(trades) if trades else 0
        avg_win = np.mean([t['pnl'] for t in winning_trades]) if winning_trades else 0
        avg_loss = np.mean([t['pnl'] for t in trades if t['pnl'] <= 0]) if any(t['pnl'] <= 0 for t in trades) else 0
        if avg_loss != 0:
            profit_factor = abs(avg_win * len(winning_trades) / (avg_loss * (len(trades) - len(winning_trades))))
    
    # Calculate regime performance
    regime_performance = {}
    for reg in ['bull', 'bear', 'sideways', 'unknown']:
        if regime_trade_counts[reg] > 0:
            avg_reg_pnl = regime_pnl[reg] / regime_trade_counts[reg]
        else:
            avg_reg_pnl = 0.0
        regime_performance[reg] = {
            'total_pnl': regime_pnl[reg],
            'trade_count': regime_trade_counts[reg],
            'avg_pnl_per_trade': avg_reg_pnl
        }
    
    return {
        'ticker': ticker,
        'starting_equity': equity_curve[0],
        'ending_equity': equity_curve[-1],
        'total_return': total_return,
        'sharpe_ratio': sharpe_ratio,
        'num_trades': len(trades),
        'win_rate': win_rate,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'profit_factor': profit_factor,
        'equity_curve': equity_series,
        'trades': trades,
        'regime_performance': regime_performance
    }

def run_backtest():
    # List of tickers to test
    tickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META']
    # Download data for all tickers
    print("Downloading data for multiple tickers...")
    data = yf.download(tickers, period="2y")  # last 2 years

    # Initialize list to store results
    all_results = []

    # Loop over each ticker and run backtest with enhancements and regime analysis
    for ticker in tickers:
        print(f"\nBacktesting {ticker} with enhancements (transaction costs, slippage, RSI+volume filters) and regime analysis...")
        result = backtest_ticker(ticker, data, 
                                 risk_per_trade=0.02, 
                                 atr_sl_multiplier=2.0, 
                                 atr_tp_multiplier=3.0,
                                 commission_per_trade=1.0,  # $1 per share
                                 slippage_percent=0.001,    # 0.1% slippage
                                 use_rsi_filter=True, 
                                 rsi_window=14,
                                 rsi_oversold=30,
                                 rsi_overbought=70,
                                 use_volume_filter=True,
                                 volume_ma_window=20,
                                 regime_ma_window=200,
                                 regime_threshold=0.05)
        all_results.append(result)
        # Print summary for this ticker
        print(f"  Starting Equity: ${result['starting_equity']:,.2f}")
        print(f"  Ending Equity: ${result['ending_equity']:,.2f}")
        print(f"  Total Return: {result['total_return']:.2%}")
        print(f"  Sharpe Ratio: {result['sharpe_ratio']:.2f}")
        print(f"  Number of Trades: {result['num_trades']}")
        if not np.isnan(result['win_rate']):
            print(f"  Win Rate: {result['win_rate']:.2%}")
            print(f"  Average Win: ${result['avg_win']:,.2f}")
            print(f"  Average Loss: ${result['avg_loss']:,.2f}")
            if not np.isnan(result['profit_factor']):
                print(f"  Profit Factor: {result['profit_factor']:.2f}")
        
        # Print regime performance
        print("  Regime Performance:")
        for reg, perf in result['regime_performance'].items():
            if perf['trade_count'] > 0:
                print(f"    {reg}: {perf['trade_count']} trades, Total PnL: ${perf['total_pnl']:,.2f}, Avg PnL/trade: ${perf['avg_pnl_per_trade']:,.2f}")
            else:
                print(f"    {reg}: 0 trades")
        
        # Plot equity curve for this ticker
        plt.figure(figsize=(14, 7))
        plt.plot(result['equity_curve'].index, result['equity_curve'].values)
        plt.title(f'{ticker} Enhanced Bollinger Band Strategy Equity Curve')
        plt.xlabel('Date')
        plt.ylabel('Equity ($)')
        plt.grid(True)
        plt.savefig(f'/home/angad/Trading-Stratergy/{ticker}_enhanced_equity_curve.png')
        plt.close()

    # Print aggregate summary
    print("\n" + "="*50)
    print("AGGREGATE SUMMARY ACROSS ALL TICKERS (WITH ENHANCEMENTS AND REGIME ANALYSIS)")
    print("="*50)
    returns = [r['total_return'] for r in all_results]
    sharpes = [r['sharpe_ratio'] for r in all_results if not np.isnan(r['sharpe_ratio'])]
    win_rates = [r['win_rate'] for r in all_results if not np.isnan(r['win_rate'])]
    profit_factors = [r['profit_factor'] for r in all_results if not np.isnan(r['profit_factor'])]

    print(f"Number of Tickers: {len(tickers)}")
    print(f"Average Total Return: {np.mean(returns):.2%}")
    print(f"Median Total Return: {np.median(returns):.2%}")
    print(f"Average Sharpe Ratio: {np.mean(sharpes):.2f} (if available)")
    print(f"Average Win Rate: {np.mean(win_rates):.2%} (if available)")
    print(f"Average Profit Factor: {np.mean(profit_factors):.2f} (if available)")

    # List best and worst performers
    sorted_results = sorted(all_results, key=lambda x: x['total_return'], reverse=True)
    print(f"\nBest Performer: {sorted_results[0]['ticker']} ({sorted_results[0]['total_return']:.2%})")
    print(f"Worst Performer: {sorted_results[-1]['ticker']} ({sorted_results[-1]['total_return']:.2%})")

    # Aggregate regime performance across all tickers
    print("\nAggregate Regime Performance Across All Tickers:")
    aggregate_regime = {'bull': {'total_pnl': 0.0, 'trade_count': 0},
                        'bear': {'total_pnl': 0.0, 'trade_count': 0},
                        'sideways': {'total_pnl': 0.0, 'trade_count': 0},
                        'unknown': {'total_pnl': 0.0, 'trade_count': 0}}
    for result in all_results:
        for reg in ['bull', 'bear', 'sideways', 'unknown']:
            aggregate_regime[reg]['total_pnl'] += result['regime_performance'][reg]['total_pnl']
            aggregate_regime[reg]['trade_count'] += result['regime_performance'][reg]['trade_count']

    for reg in ['bull', 'bear', 'sideways', 'unknown']:
        if aggregate_regime[reg]['trade_count'] > 0:
            avg_pnl = aggregate_regime[reg]['total_pnl'] / aggregate_regime[reg]['trade_count']
            print(f"  {reg}: {aggregate_regime[reg]['trade_count']} trades, Total PnL: ${aggregate_regime[reg]['total_pnl']:,.2f}, Avg PnL/trade: ${avg_pnl:,.2f}")
        else:
            print(f"  {reg}: 0 trades")

    print("\n" + "="*50)
    print("ENHANCEMENTS SUMMARY")
    print("="*50)
    print("✓ Position sizing and risk management (ATR-based stop-loss and take-profit)")
    print("✓ Testing on multiple stocks for robustness")
    print("✓ Transaction costs and slippage modeling")
    print("✓ Combining with other indicators (RSI and volume) to filter false signals")
    print("✓ Testing on different market regimes (bull, bear, sideways)")
    print("\nNext Steps for Further Improvement:")
    print("✓ Implement walk-forward optimization to avoid overfitting")
    print("✓ Consider machine learning models for signal prediction")
    print("✓ Add more sophisticated risk management (e.g., volatility targeting)")
    print("✓ Incorporate fundamental data and sentiment analysis")
    print("✓ Execute live trading with paper trading account")
    if GPU_AVAILABLE:
        print("\nGPU acceleration used via CuPy for indicator calculations.")
    else:
        print("\nGPU not available, using CPU for indicator calculations.")

if __name__ == "__main__":
    run_backtest()