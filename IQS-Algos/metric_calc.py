import calendar
from datetime import date
import numpy as np
import pandas as pd

#------------------
# private functions
#------------------

_freq_count = {
    'B'  : 252, # business day frequency
    'D'  : 365, # calendar day frequency
    'W'  :  52, # weekly frequency
    'M'  :  12, # month end frequency
    'BM' :  12, # business month end frequency
    'MS' :  12, # month start frequency
    'BMS':  12, # business month start frequency
    'Q'  :   4, # quarter end frequency
    'BQ' :   4, # business quarter endfrequency
    'QS' :   4, # quarter start frequency
    'BQS':   4, # business quarter start frequency
    'A'  :   1, # year end frequency
    'BA' :   1, # business year end frequency
    'AS' :   1, # year start frequency
    'BAS':   1, # business year start frequency
}

def _get_freq_count(data=None,freq=None):
    """Return count for annualising numbers using either the freq passed in or the index freq of the data."""
    if freq is None and (isinstance(data,pd.Series) or isinstance(data,pd.DataFrame)):
        freq = data.index.freq.name       

    if freq is None:
        raise ValueError('freq required if data not a Series or DataFrame')

    return _freq_count[freq]


def _check_vector(x):
    """Check that input is a column vector."""
    s = x.shape
    if len(s) == 1 or (len(s) == 2 and s[1] == 1):
        return True
    return False

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

# aka semi-std
def _downside_risk(log_returns, rmin=0):
    """
    aka semi-std
    :param log_returns: vector, pd.Series, 1d pd.DataFrame of log returns
    :param rmin: optional scalar minimum return per period 
    :return: the semi-std as a scalar
    """
    return np.sqrt((np.minimum(log_returns - rmin, 0)).pow(2).sum() / log_returns.count())


# --------------------
# conversion functions
# --------------------

def price_from_logret(r, start=100):
    """
    Calculate a synthetic price line from log returns and a starting value.
    :param r: vector of log returns 
    :param start: start value, defaults to 100
    :return: synthetic series
    """
    return np.exp(r.cumsum()) * start


def log_returns(x, col : str = None) -> pd.Series:
    """
    Calculate log returns for a Series or DataFrame column.  The first return is zero.
    :param x: pandas.Series or pandas.DataFrame
    :param col: None for a pandas Series, column name for a DataFrame    
    :return: pandas.Series with the log returns of the given Series or Dataframe column 
    """
    out = pd.Series(index=x.index, dtype=np.float64)

    if isinstance(x, pd.Series):
        if col is not None:
            raise ValueError(f"calc_logret called on pandas Series with col = {col}")
        out = np.log(x)
    elif isinstance(x, pd.DataFrame):
        if col is None:
            raise ValueError(f"calc_logret called on pandas DataFrame with col = None")
        out = np.log(x[col])
    else:
        raise ValueError(f"calc_logret needs a pandas Series or DataFrame")

    # calc returns and set first row to zero rather than NaN
    out = out - out.shift(1)
    out.iloc[0] = 0
    return out


# ----------------------
# risk metrics functions
# ----------------------

def annual_sortino(log_returns, min_ann_ret=0, freq=None):
    """
    Calculate annualised Sortino Ratio from a series of log returns with optional minimum target.
    :param log_returns: vector, pd.Series, 1d pd.DataFrame of log returns
    :param min_ann_ret: scalar annualised minimum target return as an arithmetic return
    :param freq: freq string per pandas "offset alias", if None then index of ret is expected to have a frequency set
    :return: scalar
    """
    if not _check_vector(log_returns):
        raise ValueError("log_returns must be a vector: either a Series or 1d DataFrame")

    # convert min_ret from arithmetic to log
    min_ann_ret = np.log1p(min_ann_ret)

    # for annualisation multiplier
    p = _get_freq_count(log_returns, freq)
    
    # the calculation
    return np.sqrt(p) * (log_returns.mean() - min_ann_ret / p) / _downside_risk(log_returns, min_ann_ret / p)


def annual_sharpe(log_returns, min_ann_ret=0, freq=None):
    """
    Calculate annualised Sharpe Ratio from a series of log returns with optional minimum target.
    :param log_returns: vector, pd.Series, 1d pd.DataFrame of log returns
    :param min_ann_ret: scalar annualised minimum target return as an arithmetic return
    :param freq: freq string per pandas "offset alias", if None then index of ret is expected to have a frequency set
    :return: scalar
    """
    if not _check_vector(log_returns):
        raise ValueError("log_returns must be a vector: either a Series or 1d DataFrame")

    # convert min_ret from arithmetic to log
    min_ann_ret = np.log1p(min_ann_ret)

    # for annualisation multiplier
    p = _get_freq_count(log_returns, freq)

    # note: to get np.std to match you have to use np.std(ret, ddof=1)
    return np.sqrt(p) * (log_returns.mean() - min_ann_ret / p) / log_returns.std()


def annual_volatility(log_returns, freq=None):
    """
    Calculate annualised Volatility from a series of returns.
    :param log_returns: vector, pd.Series, 1d pd.DataFrame of log returns
    :param freq: freq string per pandas "offset alias", if None then index of ret is expected to have a frequency set
    :return: scalar
    """
    if not _check_vector(log_returns):
        raise ValueError("log_returns must be a vector: either a Series or 1d DataFrame")

    # for annualisation multiplier
    p = _get_freq_count(log_returns, freq)

    # note: to get np.std to match you have to use np.std(ret, ddof=1)
    return np.sqrt(p) * log_returns.std()


def max_drawdown(log_returns):
    """Max drawdown pct, date, start, and end dates returned.  Note that this expects a log return series and returns
    the max drawdown as a log return.

    Arguments:
      ret  log returns
    """
    if not _check_vector(log_returns):
        raise ValueError("log_returns must be a vector: either a Series or 1d DataFrame")

    # if a multiindex, assume (year, month) and convert to DatetimeIndex
    if isinstance(log_returns.index, pd.MultiIndex):
        log_returns = log_returns.copy()
        log_returns.index = pd.DatetimeIndex([pd.Timestamp(date(x[0], x[1], calendar.monthrange(*x)[1])) for x in log_returns.index])

    # cret_dd max value is 0 (i.e.: no drawdown)
    cret = log_returns.cumsum()
    cret_max = pd.expanding_max(cret)
    cret_max[cret_max < 0] = 0
    cret_dd = cret - cret_max

    # mdd as a log return
    mdd_pct = cret_dd.min()

    if mdd_pct < 0:
        mdd_date = cret_dd.argmin()
        mdd_sdate = cret_dd.iloc[cret_dd.index.get_loc(mdd_date)::-1].argmax()
        mdd_edate = cret_dd.loc[mdd_date:].argmax()
    else:
        mdd_date = mdd_sdate = mdd_edate = cret.index[0]

    return mdd_pct, mdd_date, mdd_sdate, mdd_edate


def risk_summary(log_returns):
    """
    Output a dict with metrics.
    :param log_returns: pd.Series, 1d pd.DataFrame of log returns
    :return: dict 
    """
    # assume business day returns unless freq set
    freq = log_returns.index.freq
    if freq is None: freq = 'BD'
    
    # all annualised
    out = {}  
    out['Return'] = np.expm1(log_returns.mean() * _get_freq_count(freq))   
    out['Volatility']  = annual_volatility(log_returns, freq)
    out['Sharpe']      = annual_sharpe(log_returns, freq)
    out['Sortino']     = annual_sortino(log_returns, freq)
    out['Sharpe 2%']   = annual_sharpe(log_returns, freq, min_ann_ret=0.02)
    out['Sortino 2%']  = annual_sortino(log_returns, freq, min_ann_ret=0.02)

    (mdd_pct, mdd_date, mdd_sdate, mdd_edate) = max_drawdown(log_returns)
    out['MDD %'] = np.expm1(mdd_pct)
    out['MDD Date'] = mdd_date.date()
    out['MDD SDate'] = mdd_sdate.date()
    out['MDD EDate'] = mdd_edate.date()

    return out
