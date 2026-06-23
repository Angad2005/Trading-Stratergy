import yfinance as yf
import pandas as pd

ticker = "AAPL"
data = yf.download(ticker, period="2y")
print("Columns:", data.columns)
print("Index:", data.index)
print("\nFirst 5 rows:")
print(data.head())
print("\nData types:")
print(data.dtypes)