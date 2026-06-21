import unittest
import pandas as pd
import numpy as np
from bollinger_band_backtest import calculate_rsi, backtest_ticker

class TestBollingerBacktest(unittest.TestCase):
    
    def test_calculate_rsi(self):
        # Create a simple price series
        prices = pd.Series([10, 11, 12, 13, 14, 13, 12, 11, 10, 9, 8, 7, 6, 5, 4])
        rsi = calculate_rsi(prices, window=3)
        # The first 3 values will be NaN due to rolling window
        # We'll check that the RSI is between 0 and 100
        self.assertTrue(all((rsi.dropna() >= 0) & (rsi.dropna() <= 100)))
        
    def test_backtest_ticker_runs(self):
        # Create a small synthetic dataset for one ticker
        dates = pd.date_range('2024-01-01', periods=100, freq='D')
        # Create data with multi-index columns as expected by yfinance download
        # We'll create a DataFrame with columns: (Price, Ticker) for Close, High, Low, Open, Volume
        ticker = 'TEST'
        close = pd.Series(np.random.randn(100).cumsum() + 100, index=dates)
        high = close + np.random.rand(100) * 2
        low = close - np.random.rand(100) * 2
        open_price = close + (np.random.rand(100) - 0.5) * 0.5
        volume = pd.Series(np.random.randint(1000, 10000, 100), index=dates)
        
        # Build multi-index columns
        columns = pd.MultiIndex.from_product([['Close', 'High', 'Low', 'Open', 'Volume'], [ticker]])
        data = pd.DataFrame({
            ('Close', ticker): close,
            ('High', ticker): high,
            ('Low', ticker): low,
            ('Open', ticker): open_price,
            ('Volume', ticker): volume
        }, index=dates)
        
        # Run the backtest with minimal parameters to avoid long runtime
        result = backtest_ticker(
            ticker, data,
            risk_per_trade=0.02,
            atr_sl_multiplier=2.0,
            atr_tp_multiplier=3.0,
            commission_per_trade=0.0,  # No commission for test
            slippage_percent=0.0,      # No slippage for test
            use_rsi_filter=False,
            use_volume_filter=False
        )
        
        # Check that the result has the expected keys
        expected_keys = ['ticker', 'starting_equity', 'ending_equity', 'total_return', 
                        'sharpe_ratio', 'num_trades', 'win_rate', 'avg_win', 'avg_loss', 
                        'profit_factor', 'equity_curve', 'trades']
        for key in expected_keys:
            self.assertIn(key, result)
        
        # Check types
        self.assertEqual(result['ticker'], ticker)
        self.assertIsInstance(result['starting_equity'], (int, float))
        self.assertIsInstance(result['ending_equity'], (int, float))
        self.assertIsInstance(result['total_return'], (int, float))
        self.assertIsInstance(result['equity_curve'], pd.Series)
        self.assertIsInstance(result['trades'], list)
        
        # Check that equity_curve has the right length (100 days + 1 for starting point)
        self.assertEqual(len(result['equity_curve']), len(dates) + 1)

if __name__ == '__main__':
    unittest.main()