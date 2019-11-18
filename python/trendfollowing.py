import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import quandl

#this function stores all the trading logic and does all the signal generation
def trade():
    #removed all trading ban logic
    lower_band_trading_ban = False
    upper_band_trading_ban = False
    #booleans to prevent concurrent positionings
    long_exposure = False
    short_exposure = False
    # generate signals
    for i in range(0, len(item['Settle'])):

        if (item['Settle'][i] >= item['MA'][i]):
            lower_band_trading_ban = False

        #generate short position
        if (item['Settle'][i] <= item['Lower Band'][i]
                and lower_band_trading_ban is False and long_exposure is False and short_exposure is False):
            #adding short_exposure helps prevent P&L miscalculations
            #2.0 refers to short and 1.0 refers to long in the signals dataframe
            signals['signal'][i] = 2.0
            #calculate stop loss as 1 percent below the entry price
            item['Short Position Stop'][i:] = item['Settle'][i] + (item['Settle'][i] * 0.01)
            #dataframe is cloned due to type issues when doing arithmetic 
            item['Short Position Stop Clone'][i:] = item['Settle'][i] + (item['Settle'][i] * 0.01)
            #clone stop loss to signals dataframe
            signals['Short Position Stop'][i:] = item['Settle'][i] + (item['Settle'][i] * 0.01)
            orders['Settle'][i] = item['Settle'][i]
            orders['signal'][i] = 2.0
            short_exposure = True
            lower_band_trading_ban = False
            print("entered short position", i, "Open:", item['Settle'][i], "Lower Band: ", item['Lower Band'][i])

        if (item['Settle'][i] <= item['MA'][i]):
            upper_band_trading_ban = False

        #generate long position
        if (item['Settle'][i] >= item['Upper Band'][i]
                and upper_band_trading_ban is False and short_exposure is False and long_exposure is False):
            signals['signal'][i] = 1.0
            item['Long Position Stop'][i:] = item['Settle'][i] - (item['Settle'][i] * 0.01)
            item['Long Position Stop Clone'][i:] = item['Settle'][i] - (item['Settle'][i] * 0.01)
            signals['Long Position Stop'][i:] = item['Settle'][i] - (item['Settle'][i] * 0.01)
            orders['Settle'][i] = item['Settle'][i]
            orders['signal'][i] = 1.0
            long_exposure = True
            upper_band_trading_ban = False
            print("entered long position", i, "Open:", item['Settle'][i], "Upper Band: ", item['Upper Band'][i])

        #every entry corresponds with an identical exit
        if (long_exposure is True):            
            #exit buy positions
            if (item['Settle'][i] <= item['Long Position Stop Clone'][i] or item['Settle'][i] <= item['MA'][i]):
                orders['Settle'][i] = item['Settle'][i]
                #-1 and -2 indicate the closing of long/short positions
                orders['signal'][i] = -1.0
                signals['signal'][i] = -1.0
                lower_band_trading_ban = False
                long_exposure = False
                print("exit long position", i, "Open:", item['Settle'][i], "Sell Point: ", item['Long Position Stop Clone'][i], "Moving Average:", item['MA'][i])

        if (short_exposure is True):
            #exit short positions
            if (item['Settle'][i] >= item['Short Position Stop Clone'][i] or item['Settle'][i] >= item['MA'][i]):
                orders['Settle'][i] = item['Settle'][i]
                orders['signal'][i] = -2.0
                signals['signal'][i] = -2.0
                upper_band_trading_ban = False
                short_exposure = False
                print("exit short posiion", i, "Open:", item['Settle'][i], "Sell Point: ", item['Short Position Stop Clone'][i], "Moving Average:", item['MA'][i])

#plotting the equity curve and the technical charts
def matplotlib():
    fig = plt.figure()
    ax1 = fig.add_subplot(111, ylabel='Price in $')
    security[['Settle', 'MA', 'Upper Band', 'Lower Band', 'Short Position Stop',
              'Long Position Stop']].plot(ax=ax1, figsize=(12, 6))
    plt.title('Trend Following System for ' + data_store)
    plt.ylabel('Price (USD)')

    fig = plt.figure()
    ax2 = fig.add_subplot(111, ylabel='Price (USD)')    
    signals[['index']].plot(ax=ax2, figsize=(12,6))
    plt.title('Equity Curve')

    plt.show()

    # Plot the equity curve in dollars
    #portfolio_equity = pd.read_csv('portfolio_equity_trend.csv')
    '''
    if (portfolio_equity['Equity'][0] == capital):
        fig = plt.figure()
        ax1 = fig.add_subplot(111, ylabel='Portfolio value in $')
        portfolio_equity[['Equity']].plot(ax=ax1, figsize=(12,6))
        plt.show()
    '''

#loading relevant data based on the data_store parameter
def dataLoader(data_store):
    quandl.ApiConfig.api_key = "HAQ5HX1UH9eB9virjnGF"
    starting_period = pd.Timestamp('2013-1-1')
    ending_period = pd.Timestamp('2019-9-1')    
    if (data_store is 'DXY'):
        try:
            security = quandl.get(
                "CHRIS/ICE_DX1",
                start_date=starting_period,
                end_date=ending_period)
        except BaseException:
            exit()
        if security.empty:
            exit()
    if (data_store is 'IQS'):
        try:
            security = pd.read_csv('modified-leverage-iqs-curve.csv')
            security.set_index('Date')
        except:
            print("exception")
            exit()
        if security.empty:
            print("empty")
            exit()
    if (data_store is 'EURUSD'):
        try:
            security = pd.read_csv('EUR_USD_Historical_Data.csv')
        except:
            print("exception")
            exit()
        if security.empty:
            print("empty")
            exit()

    return security

if __name__ == '__main__':
    pd.options.mode.chained_assignment = None
    moving_average_window = 20
    buy_quantity = 100
    leverage = 3
    #positions['security'] = (buy_quantity * leverage) * signals['signal']
    capital = 1000
    data_stores = ['IQS', 'EURUSD', 'DXY']
    data_store = 'DXY'

    security = dataLoader(data_store)

    # trading signal generation
    signals = pd.DataFrame(index=security.index)
    signals['signal'] = 0.0
    orders = pd.DataFrame(index=security.index)
    #all CSV files have relevant price column changed to Settle for convenience
    orders['Settle'] = 0.0
    orders['signal'] = 0.0
    signals['index'] = 0.0
    signals['index'][0] = capital

    # Calculate Moving Average, Std Deviation, Upper Band and Lower Band
    for item in security, security:
        item['MA'] = item['Settle'].rolling(window=moving_average_window).mean()
        item['STD'] = item['Settle'].rolling(
            window=moving_average_window).std(ddof=0)
        item['Upper Band'] = item['MA'] + (item['STD'] * 2)
        item['Lower Band'] = item['MA'] - (item['STD'] * 2)
        item['Short Position Stop'] = None
        item['Long Position Stop'] = None
        #clones used for NoneType float conversion fix
        item['Short Position Stop Clone'] = 0.0
        item['Long Position Stop Clone'] = 0.0
        signals['Settle'] = item['Settle']
        signals['MA'] = item['Settle'].rolling(window=moving_average_window).mean()
        signals['Upper Band'] = item['MA'] + (item['STD'] * 2)
        signals['Lower Band'] = item['MA'] - (item['STD'] * 2)
        signals['Short Position Stop'] = None
        signals['Long Position Stop'] = None

    trade()

    #calculate returns
    orders = orders[(orders.T != 0).any()]
    print(orders)
    profit_loss = pd.DataFrame(index=signals.index)
    profit_loss['P&L'] = 0.0
    #temporary columns for debugging purposes
    profit_loss['Settle'] = orders['Settle']
    profit_loss['signal'] = orders['signal']
    signals['P&L'] = 0.0

    #fill P&L/signals dataframe with an arithmetic return series
    #capital variable is used during non-trading periods to move the index along the time continuum i.e. have no gaps in the column
    long_entry = False
    short_entry = False
    try:
        #loop through entire time series
        for i in range(0,len(signals)):
            #if buy signal is generated
            if (signals['signal'][i] == 1.0):
                #start generating daily P&L
                long_entry = True
                signals['index'][i] = capital

            #when position is exited
            if (signals['signal'][i] == -1.0):
                profit_loss['P&L'][i] = signals['Settle'][i] - signals['Settle'][i-1]                
                signals['P&L'][i] = signals['Settle'][i] - signals['Settle'][i-1]
                #stop calculating daily P&L
                long_entry = False
                signals['index'][i] = signals['index'][i-1] + (signals['index'][i-1] * ((signals['Settle'][i]-signals['Settle'][i-1])/signals['Settle'][i])*1)
                capital = signals['index'][i]

            if (signals['signal'][i] == 2.0):
                short_entry = True
                signals['index'][i] = capital

            if (signals['signal'][i] == -2.0):
                profit_loss['P&L'][i] = (signals['Settle'][i] - signals['Settle'][i-1]) * -1
                signals['P&L'][i] = (signals['Settle'][i] - signals['Settle'][i-1]) * -1
                short_entry = False
                #calculate percentage change of index
                signals['index'][i] = signals['index'][i-1] + (signals['index'][i-1] * ((signals['Settle'][i]-signals['Settle'][i-1])/signals['Settle'][i])*-1)
                capital = signals['index'][i]

            if (signals['signal'][i] == 0.0 and long_entry is True):
                profit_loss['P&L'][i] = signals['Settle'][i] - signals['Settle'][i-1]
                signals['P&L'][i] = signals['Settle'][i] - signals['Settle'][i-1]
                #calculate new index for today
                signals['index'][i] = signals['index'][i-1] + (signals['index'][i-1] * ((signals['Settle'][i]-signals['Settle'][i-1])/signals['Settle'][i])*1)

            if (signals['signal'][i] == 0.0 and short_entry is True):
                profit_loss['P&L'][i] = (signals['Settle'][i] - signals['Settle'][i-1]) * -1
                signals['P&L'][i] = (signals['Settle'][i] - signals['Settle'][i-1]) * -1
                #calculate new index for today
                signals['index'][i] = signals['index'][i-1] + (signals['index'][i-1] * ((signals['Settle'][i]-signals['Settle'][i-1])/signals['Settle'][i])*-1)

            if (signals['signal'][i] == 0.0 and short_entry is False and long_entry is False):
                signals['index'][i] = capital

    except Exception as e:
        print(e)

    #store positive/negative outcomes of every trade as binary values
    profit_loss = profit_loss[profit_loss['P&L'] != 0]
    profit_loss['Outcome'] = None
    for i in range(0, len(profit_loss)):
        if (profit_loss['P&L'][i] > 0.0):
            profit_loss['Outcome'][i] = 1.0
        else:
            profit_loss['Outcome'][i] = 0.0 

    matplotlib()

    security.to_csv('security.csv')
    signals.to_csv('signals_trend.csv')
    orders.to_csv('orders_trend.csv')
    profit_loss.to_csv('profit_loss_trend.csv')