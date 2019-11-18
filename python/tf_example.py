import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


def trade(dly: pd.DataFrame, stop_pct: np.float64, tplusone : bool = False):
    # add columns
    dly['pos_qty'] = 0
    dly['trd_qty'] = 0
    dly['trd_prc'] = 0

    # useful for debugging
    dly['stop_prc'] = np.nan

    # current position, order
    pos_qty = 0
    ord_qty = 0
    stop_prc = 0

    # loop through time
    for t in dly.index:

        # if tplusone then order was generated last night, execute at open
        if tplusone and ord_qty != 0:
            dly.loc[t, 'trd_qty'] = ord_qty
            dly.loc[t, 'trd_prc'] = dly.loc[t, 'oprc']
            print(f"{t} execute order(t+1), old_pos={pos_qty} ord={ord_qty} prc={dly.loc[t, 'trd_prc']}")
            pos_qty += ord_qty
            ord_qty = 0

        # current settlement price
        sprc = dly.loc[t, 'sprc']

        # check for stops
        if (pos_qty < 0 and sprc > stop_prc) or (pos_qty > 0 and sprc < stop_prc):
            ord_qty = -pos_qty
            print(f"{t} stopped pos={pos_qty} sprc={sprc} stop_prc={stop_prc}")

        # check for normal unwind
        elif (pos_qty < 0 and sprc > dly.loc[t, 'sig_mu']) or (pos_qty > 0 and sprc < dly.loc[t, 'sig_mu']):
            ord_qty = -pos_qty
            print(f"{t} unwind pos={pos_qty} sprc={sprc} sig_mu={dly.loc[t, 'sig_mu']}")

        # allow immediate entry of a new position
        if pos_qty == 0 and sprc <= dly.loc[t, 'sig_lower']:
            ord_qty += -1
            stop_prc = sprc * (1 + stop_pct)
            dly.loc[t, 'stop_prc'] = stop_prc
            print(f"{t} short pos={pos_qty} ord={ord_qty} sprc={sprc} sig_lower={dly.loc[t, 'sig_lower']}")
        elif pos_qty == 0 and sprc >= dly.loc[t, 'sig_upper']:
            ord_qty += 1
            stop_prc = sprc * (1 - stop_pct)
            dly.loc[t, 'stop_prc'] = stop_prc
            print(f"{t} long pos={pos_qty} ord={ord_qty} sprc={sprc} sig_upper={dly.loc[t, 'sig_upper']}")

        # if not tplusone we execute orders immediately, accuracy could be improved by using the closing price which
        # is after the settlement price used for the signal
        if not tplusone and ord_qty != 0:
            dly.loc[t, 'trd_qty'] = ord_qty
            dly.loc[t, 'trd_prc'] = dly.loc[t, 'sprc']
            print(f"{t} execute order(t), old_pos={pos_qty} ord={ord_qty} prc={dly.loc[t, 'trd_prc']}")
            pos_qty += ord_qty
            ord_qty = 0

        # save position
        dly.loc[t, 'pos_qty'] = pos_qty

    return dly


def pnl(dly : pd.DataFrame):
    # cumulative cashflows from trades, note opposite sign
    dly['cf'] = -(dly['trd_qty'] * dly['trd_prc']).cumsum()

    # mark positions at settle price
    dly['mtm'] = dly['pos_qty'] * dly['sprc']

    # pnl is sum of cashflows + positions, in this case with unit positions it is also the (arithmetic) return
    dly['pnl'] = dly['cf'] + dly['mtm']

    # above is a cumulative arithmetic return.  Add daily log returns 
    logret = np.expm1(dly['pnl'])
    
    logret = logret - logret.shift(1)
    logret.iloc[0] = 0
    dly['logret'] = logret
    
    return dly


#plotting the equity curve and the technical charts
# def matplotlib():
#     fig = plt.figure()
#     ax1 = fig.add_subplot(111, ylabel='Price in $')
#     security[['sprc', 'MA', 'Upper Band', 'Lower Band', 'Short Position Stop',
#               'Long Position Stop']].plot(ax=ax1, figsize=(12, 6))
#     plt.title('Trend Following System')
#     plt.ylabel('Price (USD)')
#
#     fig = plt.figure()
#     ax2 = fig.add_subplot(111, ylabel='Price (USD)')
#     signals[['index']].plot(ax=ax2, figsize=(12,6))
#     plt.title('Equity Curve')
#
#     plt.show()
#
#     # Plot the equity curve in dollars
#     #portfolio_equity = pd.read_csv('portfolio_equity_trend.csv')
#     '''
#     if (portfolio_equity['Equity'][0] == capital):
#         fig = plt.figure()
#         ax1 = fig.add_subplot(111, ylabel='Portfolio value in $')
#         portfolio_equity[['Equity']].plot(ax=ax1, figsize=(12,6))
#         plt.show()
#     '''

if __name__ == '__main__':
    #pd.options.mode.chained_assignment = None
    moving_average_window = 20
    buy_quantity = 100
    leverage = 3
    capital = 1000

    # read daily data, columns are:
    # tdate  trade date
    # oprc, hprc, lprc, cprc, sprc  open, hi, lo, close, settle prices
    # tvol  trade volume
    # oint  open interest
    # padj  price adjustment which was used to synthesise from underlying contracts
    # futc  underlying contract identifier
    dly = pd.read_csv('c:/git-projects/ctl/python/misc/tf_jamie/usdeur.csv')
    dly.set_index('tdate', inplace=True)

    # moving average, upper and lower bands
    dly['sig_mu'] = dly['sprc'].rolling(window=moving_average_window).mean()
    dly['sig_std'] = dly['sprc'].rolling(window=moving_average_window).std(ddof=0)
    dly['sig_upper'] = dly['sig_mu'] + dly['sig_std'] * 2 
    dly['sig_lower'] = dly['sig_mu'] - dly['sig_std'] * 2

    trade(dly, 0.01)
    pnl(dly)

    # matplotlib()
