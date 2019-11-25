import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import quandl

quandl.ApiConfig.api_key = "HAQ5HX1UH9eB9virjnGF "
starting_period = pd.Timestamp('2019-1-1')
ending_period = pd.Timestamp('2019-6-1')
moving_average_window = 20
initial_capital = 100000
security = quandl.get(
    "CHRIS/ICE_DX1", start_date=starting_period, end_date=ending_period)

# trading signal generation
signals = pd.DataFrame(index=security.index)
signals['signal'] = 0.0

# Calculate 30 Day Moving Average, Std Deviation, Upper Band and Lower Band
for item in security, security, security:
    item['MA'] = item['Open'].rolling(window=moving_average_window).mean()
    item['STD'] = item['Open'].rolling(window=moving_average_window).std(ddof=0)
    item['Upper Band'] = item['MA'] + (item['STD'] * 2)
    item['Lower Band'] = item['MA'] - (item['STD'] * 2)
    item['Upper Sell Band'] = item['Open'] + (item['Open'] * 0.01)
    item['Lower Sell Band'] = item['Open'] - (item['Open'] * 0.01)

    signals['Open'] = item['Open']
    signals['MA'] = item['Open'].rolling(window=moving_average_window).mean()
    signals['Upper Band'] = item['MA'] + (item['STD'] * 2)
    signals['Lower Band'] = item['MA'] - (item['STD'] * 2)
    signals['Upper Sell Band'] = item['Open'] + (item['Open'] * 0.01)
    signals['Lower Sell Band'] = item['Open'] - (item['Open'] * 0.01)
    
# buy position signals
# signal when the short moving average crosses the long moving average, but only for the period greater than the shortest moving average window
signals['signal'][moving_average_window:] = np.where(item['Open'][moving_average_window:]
                                                     > item['Upper Band'][moving_average_window:], 1.0, 0.0)

signals['Upper Sell Band'][moving_average_window:] = np.where(item['Open'][moving_average_window:]
                                                     > item['Upper Band'][moving_average_window:], item['Open'][moving_average_window:] + (item['Open'][moving_average_window:] * 0.01))

signals['signal'][moving_average_window:] = np.where(item['Open'][moving_average_window:]
                                                     < item['Lower Band'][moving_average_window:], 2.0, 0.0)

signals['Lower Sell Band'][moving_average_window:] = np.where(item['Open'][moving_average_window:]
                                                     > item['Lower Band'][moving_average_window:], item['Open'][moving_average_window:] - (item['Open'][moving_average_window:] * 0.01))

# sell position signals
signals['positions'] = signals['signal'].diff()

# Create a DataFrame `positions`
positions = pd.DataFrame(index=signals.index).fillna(0.0)

# Buy a 100 shares
positions['security'] = 100*signals['signal']

# Initialize the portfolio with value owned
portfolio = positions.multiply(security['Open'], axis=0)

# Store the difference in shares owned
pos_diff = positions.diff()

# Add `holdings` to portfolio
portfolio['holdings'] = (positions.multiply(
    security['Open'], axis=0)).sum(axis=1)

# Add `cash` to portfolio
portfolio['cash'] = initial_capital - \
    (pos_diff.multiply(security['Open'], axis=0)).sum(axis=1).cumsum()

# Add `total` to portfolio
portfolio['total'] = portfolio['cash'] + portfolio['holdings']

# Add `returns` to portfolio
portfolio['returns'] = portfolio['total'].pct_change()

fig = plt.figure()
ax1 = fig.add_subplot(111,  ylabel='Price in $')
security[['Open', 'MA', 'Upper Band', 'Lower Band', 'Upper Sell Band', 'Lower Sell Band']].plot(
    ax=ax1, figsize=(12, 6))
plt.title('Bollinger Band for DXY')
plt.ylabel('Price (USD)')
plt.show()

# Plot the equity curve in dollars
fig = plt.figure()
ax1 = fig.add_subplot(111, ylabel='Portfolio value in $')
plt.plot(portfolio[['total']])
plt.show()

signals.to_csv('signals.csv')
positions.to_csv('positions.csv')
portfolio.to_csv('portfolio.csv')