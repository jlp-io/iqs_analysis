# %%
from datetime import date, time, datetime
import numpy as np
import pandas as pd

# tolerance is set as difference between early close @ 13:30 to 17:00 -> 03:30 
def daily_snap(in_df: pd.DataFrame, out_df: pd.DataFrame, in_col: str, out_col: str, offset, tz):
    # We use an asof merge here as it allows for a tolerance, not possible with the .asof() function.
    idx_df = pd.DataFrame(index=(out_df.index + offset).tz_localize(tz))
    #ValueError: can not merge DataFrame with instance of type <class 'pandas.core.series.Series'>
    #This is the end of the stack trace
    #idx_df is a dataframe, in_df[in_col] is a series
    in_df2 = pd.DataFrame(in_df[in_col])        #my line 
    snap = pd.merge_asof(idx_df, in_df2,
                  left_index=True, right_index=True, direction='backward',
                  tolerance=pd.offsets.Timedelta('03:30:00'))
    snap.index = snap.index.date 
    out_df[out_col] = snap


def daily_snapshots(bars: pd.DataFrame, col_name : str, hh_mm: list, tz: str):
    # output dataframe index is business days, add each offset to grab asof() data
    dly_idx = pd.bdate_range(bars.index[0].date(), bars.index[-1].date())
    out = pd.DataFrame(index=dly_idx, dtype=np.float64)

    if not isinstance(col_name, list):
        col_name = [col_name]

    if not isinstance(hh_mm, list):
        hh_mm = [hh_mm]
        
    for col in col_name:
        for t in hh_mm:
            daily_snap(bars, out, col, col + '-' + t, pd.offsets.Timedelta(t + ':00'), tz)

    return out.dropna()


# look for steady rising or falling prices given the input series
def rise_or_fall(prices : list):
    signs = pd.Series(index=prices[0].index, data=0, dtype=np.int32)
    for i in range(len(prices)-1):
        signs += np.sign(prices[i+1] - prices[i])
    signs.loc[np.abs(signs) < len(prices)-1] = 0
    signs /= len(prices)
    return signs.fillna(0)


# look for steady rising or falling prices given the input dataframe and columns
def rise_or_fall_df(snap : pd.DataFrame, cols):
    signs = pd.Series(index=snap.index, data=0, dtype=np.int32)
    for i in range(len(cols)-1):
        #RuntimeWarning: invalid value encountered in sign
        signs += np.sign(snap[cols[i+1]] - snap[cols[i]])
    signs.loc[np.abs(signs) < len(cols)-1] = 0
    signs /= (len(cols)-1)
    return signs.fillna(0)


# 1. If the price rises/falls consistently through 9.15am, 9.30am, 9.45am, 10am and 10.15am, go long/short
#    and close position at 4pm.
# 
# adding strategy 19, 20 (Rise, Fall 900 - 915 - 930 - 945 - 1000 close)
#
#
# 2. If the price rises /falls consistently through 10am, 3.30pm and 4.15pm on day 1, and through 9.45am
#    and 10am on day 2, go long/short and close position at 4pm on day 2.
# 
# adding strategy 21, 22 (Rise, Fall 945 - 1515 - 1600 - 930 - 945 close)
#
# 3. If the price rises/falls from 9.45am to 10am and the volume is greater than the volume in any 15-minute
#    period in the previous 10 days, go long and close position at 4pm. 
#
# adding strategy 32 (10 day high in 9.45 volume, long/short)
# 
#    If the 15min volume at 0945 is max for that time slot over 10 days then go long/short depending on 
#    whether 0930->0945 is up or down.  In price is close for 0945 and out price is open for 1600 - $0.10 costs.
#

class RiseFall:
    def __init__(self, name, instr, prcType: str, stopper, hmUnw: str, *, hmCur: str, hmPre: str = None, hmHiLo=None):
        self.name = name
        self.instr = instr
        self.prcType = prcType
        self.stopper = stopper
        self.hmUnw = hmUnw
        self.hmCur = [x.strip() for x in hmCur.split(',')]
        self.hmPre = [x.strip() for x in hmPre.split(',')] if hmPre is not None else None
        self.hmHiLo = [x.strip() for x in hmHiLo.split(',')] if hmHiLo is not None else None

    @property
    def descr(self):
        if self.hmPre is not None:
            samples = ', '.join([c + '-p' for c in self.hmPre] + self.hmCur)
        else:
            samples = ', '.join(self.hmCur)

        if self.hmHiLo is not None:
            samples = f"{samples} HiLo {', '.join(self.hmHiLo)}"
        return {'instr': self.instr, 'samples': samples, 'unwind': self.hmUnw, 'stop': self.stopper.descr}

    @property
    def unwind_time(self):
        return self.hmUnw

    @property
    def last_sample(self):
        if self.hmHiLo is not None:
            return max(self.hmCur[-1], self.hmHiLo[-1])
        return self.hmCur[-1]

    def signals(self, bars : pd.DataFrame):      
        # previous day's data
        if self.hmPre is not None:
            # copy shifted so t -> t+1
            day1 = daily_snapshots(bars, self.prcType, self.hmPre, 'America/New_York') 
            day1 = day1.shift(1)
            day1.columns = [f"prev-{c}" for c in day1.columns]
            day2 = daily_snapshots(bars, self.prcType, self.hmCur, 'America/New_York') 
            test = pd.concat([day1, day2], axis=1)
        else:
            test = daily_snapshots(bars, self.prcType, self.hmCur, 'America/New_York') 

        out = rise_or_fall_df(test, test.columns)
        if self.hmHiLo is not None:
            testLow = daily_snapshots(bars, 'lowPrc', self.hmHiLo, 'America/New_York')
            testHig = daily_snapshots(bars, 'higPrc', self.hmHiLo, 'America/New_York')
            flagLow = rise_or_fall_df(testLow, testLow.columns)
            flagHig = rise_or_fall_df(testHig, testHig.columns)
            zeroLong = (out > 0) & (flagLow <= 0)
            zeroShrt = (out < 0) & (flagHig >= 0)
            out.loc[zeroLong] = 0
            out.loc[zeroShrt] = 0

        return out

    def trades(self, data: dict):
        tz = 'America/New_York'
        
        bars = data[self.instr]['15m']

        # our signals, trimmed to active ones
        signal = self.signals(bars)
        signal = signal.loc[signal != 0]

        # trand and unwind times
        hm_t = self.last_sample
        hm_x = self.unwind_time

        # signal time offset from tdate
        sig_time = pd.offsets.Timedelta(self.last_sample + ':00')
        sig_type = self.prcType
        sig_indx = (signal.index + sig_time).tz_localize(tz)

        # trade time offset from tdate, note +15m for next bar
        trd_time = pd.offsets.Timedelta(self.last_sample + ':00') + pd.offsets.Minute(15)
        trd_type = 'opnPrc'
        trd_indx = (signal.index + trd_time).tz_localize(tz)

        # exit time, can be next day        
        xit_time = pd.offsets.Timedelta(hm_x + ':00')
        xit_type = 'clsPrc'
        if xit_time > trd_time:
            xit_indx = (signal.index + xit_time).tz_localize(tz)
        else:
            xit_indx = (signal.index + xit_time+ pd.offsets.BDay(1)).tz_localize(tz)


        out = pd.DataFrame(index=range(len(signal)), columns=['strat'], data=self.name)
        out['tdate'] = signal.index
        out['sigTS'] = sig_indx
        out['sigTyp'] = sig_type
        out['sigVal'] = signal.values

        # this is the underlying price for stop loss purposes, not the adjusted price used by the strat  
        #sig_idx = (signal.index + pd.offsets.Timedelta(hm_t + ':00')).tz_localize('America/New_York')
        bars[self.prcType].asof(sig_indx)
        #out['sigPrc'] = bars[self.prcType].asof(sig_indx).values

        # just set the trade prices according to the overrides...
        out['inTS'] = trd_indx
        out['inTyp'] = trd_type
        out['inPrc'] = bars[trd_type].asof(trd_indx).values
        out['inVol'] = bars['trdQty'].asof(trd_indx).values
           
        out['outTS'] = xit_indx
        out['outTyp'] = xit_type
        out['outPrc'] = bars[xit_type].asof(xit_indx).values
        out['outVol'] = bars['trdQty'].asof(xit_indx).values

        # loop through and output trade by trade, including stops
        for i in range(len(out)):
            tdate = signal.index[i]
            trd = out.iloc[i]
            # prc15 entry index, use next value if no match
            # ToDo: Add a tolerance (manually, the get_loc function can't handle time tolerances). 
            trd_i = bars.index.get_loc(trd['inTS'], 'bfill')

            # prc15 exit index, use previous value if no match
            xit_i = bars.index.get_loc(trd['outTS'], 'ffill')

            # integer indices as timestamps from index, note stops skip the current bar(!)
            trd_t = bars.index[trd_i + 1]
            xit_t = bars.index[xit_i]

            # stopped out?
            stopTime, stopTrig = self.stopper.calc_stop(bars.loc[trd_t:xit_t, :], trd)

            if stopTime is not None:
                out.loc[i, 'stopTime'] = stopTime
                out.loc[i, 'stopTrig'] = stopTrig
                out.loc[i, 'outPrc'] = bars.loc[stopTime, 'clsPrc']

        return out


class RiseFallVolume(RiseFall):
    def __init__(self, name, instr, prcType: str, stopper, hmUnw: str, *, hmCur: str, hmPre: str = None, hmHiLo=None):
        super().__init__(name, instr, prcType, stopper, hmUnw, hmCur=hmCur, hmPre=hmPre, hmHiLo=hmHiLo)

    def signals(self, bars):
        # signals from prices
        flag = super().signals(bars)
        
        # trade volume
        tqty = daily_snapshots(bars, 'trdQty', ['09:45'], 'America/New_York')
        
        # remove holidays
        tqty = tqty.loc[tqty['trdQty-09:45'] > 500]

        # series can be slightly different due to holidays and nan's being dropped, align them
        tqty = tqty.loc[tqty.index.intersection(flag.index)]
        flag = flag.loc[tqty.index]
        
        # rolling 10 day (using 9 to more or less match original implementaion)
        tqty['trdQty-09:45-10day'] = tqty['trdQty-09:45'].rolling(9).max()

        flag.loc[tqty['trdQty-09:45'] < tqty['trdQty-09:45-10day']] = 0
        flag.loc[np.isnan(tqty['trdQty-09:45-10day'])] = 0
        return flag


class Overnight(RiseFall):
    def __init__(self, name, instr, prcType: str, stopper, hmTrd : str, hmUnw: str):
        super().__init__(name, instr, prcType, stopper, hmUnw, hmCur=hmTrd)

    def signals(self, bars):
        # simply go long every day, has to be a pd.Series
        flag = daily_snapshots(bars, self.prcType, self.hmCur, 'America/New_York') > 0
        return pd.Series(index=flag.index, data = 1.0)


class NewRule1(RiseFall):
    def __init__(self, name, instr, prcType: str, stopper, hmUnw: str='16:00', *, hmCur: str, hmPre: str = None, hmHiLo=None, qtyDays=None):
        super().__init__(name, instr, prcType, stopper, hmUnw, hmCur=hmCur, hmPre=hmPre, hmHiLo=hmHiLo)
        self.qtyDays = qtyDays
        
    @property
    def descr(self):
        descr = super().descr
        if self.qtyDays is not None:
            descr['qtyDays'] = self.qtyDays
        return descr
        
    def signals(self, bars):
        # signals from prices
        flag = super().signals(bars)

        if self.qtyDays is None:
            return flag
        
        # trade volume
        tqty = daily_snapshots(bars, 'trdQty', ['09:45'], 'America/New_York')

        # remove holidays
        tqty = tqty.loc[tqty['trdQty-09:45'] > 500]

        # series can be slightly different due to holidays and nan's being dropped, align them
        tqty = tqty.loc[tqty.index.intersection(flag.index)]
        flag = flag.loc[tqty.index]

        # rolling 10 day (using 9 to more or less match original implementaion)
        tqty['trdQty-09:45-10day'] = tqty['trdQty-09:45'].rolling(self.qtyDays).max()

        flag.loc[tqty['trdQty-09:45'] < tqty['trdQty-09:45-10day']] = 0
        flag.loc[np.isnan(tqty['trdQty-09:45-10day'])] = 0
        return flag


# 2. If the difference between the opening and high prices for the period from 9.45am to 10am hits a 30-day low and
#    the price falls during the period, go short.  If the difference between the opening and low prices for the period
#    from 9.45am to 10am hits a 30-day low and the price rises during the period, go long.
class NewRule2(RiseFall):
    def __init__(self, name, instr, prcType: str, stopper, hmUnw: str='16:00', *, hmCur: str='09:45,10:00'):
        super().__init__(name, instr, prcType, stopper, hmUnw, hmCur=hmCur)

    def signals(self, bars):
        # signals from prices
        flag = super().signals(bars)

        # grab open, high, low
        test = daily_snapshots(bars, 'opnPrc,higPrc,lowPrc'.split(','), self.hmCur[-1], 'America/New_York')

        # series can be slightly different due to holidays and nan's being dropped, align them
        test = test.loc[test.index.intersection(flag.index)]
        flag = flag.loc[test.index]

        # open vs high and low
        test['opnHi'] = test[f'higPrc-{self.hmCur[-1]}'] - test[f'opnPrc-{self.hmCur[-1]}']
        test['opnLo'] = test[f'opnPrc-{self.hmCur[-1]}'] - test[f'lowPrc-{self.hmCur[-1]}']

        # 21 business days ~= 30 calendar days
        test['opnHi-30'] = test['opnHi'].rolling(21).min() 
        test['opnLo-30'] = test['opnLo'].rolling(21).min() 

        # boolean for when test is false
        zero = (test['opnHi'] > test['opnHi-30']) & (test['opnLo'] > test['opnLo-30'])
        flag[zero] = 0
        return flag

# 3. Measure the price range for all 15, 30, 45 and 60-minute periods from 9am to 12pm.  If the range hits a 30-day
#    low and the volume is equal to or greater than the mean for this period, then go short if the price falls by 70%
#    of the range and long if the price rises by 70% of the range.

#    array of integers from start to finish, ordered by value and then subtract highest from lowest 
#    ranges[i] < 30_day_low_of_ranges
#        ranges[i][vol] >= ranges[i].mean()
#            short

class NewRule3(RiseFall):
    def __init__(self, name, instr, prcType: str, stopper, hmUnw: str='16:00', *, 
                hmPre='09:30,16:00', hmCur: str='09:45,10:00'):
        super().__init__(name, instr, prcType, stopper, hmUnw, hmPre=hmPre, hmCur=hmCur)

    def signals(self, bars):
        #length of hmPre array causes a KeyError
        ranges_15 = ['9:00','9:15','9:30','9:45','10:00','10:15','10:30','10:45','11:00','11:15','11:30','11:45','12:00']
        ranges_30 = ['9:00','9:30','10:00','10:30','11:00','11:30','12:00']
        ranges_45 = ['9:00','9:45','10:30','11:15','12:00']
        ranges_60 = ['9:00','10:00','11:00','12:00']
        # signals from prices
        flag = super().signals(bars)
        # grab prev day at 09:00 to 12:00, in 15 min increments
        day1 = daily_snapshots(bars, 'opnPrc,higPrc,lowPrc,clsPrc,trdQty'.split(','), ranges_15, 'America/New_York')

        ranges_df = day1.copy()
        long_orders = list()
        short_orders = list()

        #create range values for everything
        #need to reverse loop structure 
        for j in range(0, len(ranges_15)):
            ranges_df['range-'+ranges_15[j]] = None
            for i in range(0, len(day1)):
                ranges_df['range-'+ranges_15[j]][i] = (ranges_df['higPrc-'+ranges_15[j]][i] - day1['lowPrc-'+ranges_15[j]][i])
                #30 day low calculation
                if i >= 30 & j-1 >= 0:
                    ranges_df_30 = ranges_df['range-'+ranges_15[j]][i-30:i]
                    volume_df_30 = ranges_df['trdQty-'+ranges_15[j]][i-30:i]
                    if ranges_df['range-'+ranges_15[j]][i] <= ranges_df_30.min(): 
                        if ranges_df['trdQty-'+ranges_15[j]][i] >= volume_df_30.mean():
                            price_range = abs(ranges_df['clsPrc-'+ranges_15[j]][i] - ranges_df['opnPrc-'+ranges_15[j]][i])
                            if price_range >= (ranges_df['range-'+ranges_15[j-1]][i] * 0.7):
                                long_orders.append([ranges_df.index[i],ranges_15[j],ranges_df['clsPrc-'+ranges_15[j]][i]])
                            elif price_range <= (ranges_df['range-'+ranges_15[j-1]][i] * 0.3):
                                short_orders.append([ranges_df.index[i],ranges_15[j],ranges_df['clsPrc-'+ranges_15[j]][i]])
        #sort dictionaries
        def takeFirst(elem):
            return elem[0]

        long_orders.sort(key=takeFirst)
        short_orders.sort(key=takeFirst)

        print(long_orders)
        print("----")
        print(short_orders)

        return flag

# 4. If the price falls from 9.30am to 4pm by more than it has in any of the previous 90 days, go long the following
#    day at 9.45am if (i) the price rises from 4pm to 9.30am, and (ii) the price rises from 9.30am to 9.45am.
class NewRule4(RiseFall):
    def __init__(self, name, instr, prcType: str, stopper, hmUnw: str='16:00', *, 
                 hmPre='09:30,16:00', hmCur: str='09:30,09:45'):
        super().__init__(name, instr, prcType, stopper, hmUnw, hmPre=hmPre, hmCur=hmCur)

    def signals(self, bars):
        # signals from prices
        flag = super().signals(bars)

        # grab prev day at 09:30 and 16:00
        day1 = daily_snapshots(bars, self.prcType, self.hmPre, 'America/New_York')
        day1 = day1.shift(1)

        # series can be slightly different due to holidays and nan's being dropped, align them
        day1 = day1.loc[day1.index.intersection(flag.index)]
        flag = flag.loc[day1.index]

        # calc difference, 65 business days ~= 90 calendar days
        day1['diff'] = day1[f'{self.prcType}-{self.hmPre[-1]}'] - day1[f'{self.prcType}-{self.hmPre[0]}']
        day1['diff-90'] = day1['diff'].rolling(65).min() 

        # zero out shorts
        flag[flag < 0] = 0

        # remove where condition not met
        zero = (day1['diff'] > day1['diff-90'])
        flag[zero] = 0

        return flag

# 5. If the price hits a 30-day high between 9.30am and 4pm, go long the following day at 9.45am if (i) the price 
#    rises from 4pm to 9.30am, and (ii) the price rises from 9.30am to 9.45am.
class NewRule5(RiseFall):
    def __init__(self, name, instr, prcType: str, stopper, hmUnw: str='16:00', *, 
                 hmPre='16:00', hmCur: str='09:30,09:45'):
        super().__init__(name, instr, prcType, stopper, hmUnw, hmPre=hmPre, hmCur=hmCur)

    def signals(self, bars):
        # signals from prices
        flag = super().signals(bars)

        # high prices
        hi = bars['higPrc'].copy()
        
        # cut down to time interval (the 'time' is tz naive but the correct value)
        hi = hi[(hi.index.time >= time(9,45)) & (hi.index.time <= time(16,0))]
        hi = hi.groupby(hi.index.date).max()        

        # shift to previous day
        hi = hi.shift(1)

        # 21 business days ~= 30 calendar days
        hi_30 = hi.rolling(21).max()

        # zero out shorts
        flag[flag < 0] = 0

        # series can be slightly different due to holidays and nan's being dropped, align them
        zero = (hi < hi_30)
        zero = zero.loc[zero.index.intersection(flag.index)]
        flag = flag.loc[zero.index]
        flag[zero] = 0
        flag.to_clipboard()
        return flag

# 6. Take the opening and closing prices of each 15 (or 30, 45, 60) consecutive one-minute periods from 9am to 12pm
#    and calculate the number of times the price changes direction.  If the number is a 7 (or 14, 21, 30) -day high,
#    go short; if the number is a 7 (or 14, 21, 30) –day low, go long.
class NewRule6(RiseFall):
    def __init__(self, name, instr, prcType: str, stopper, hmUnw: str='16:00', *, 
                 hmPre='9:30,16:00', hmCur: str='09:30,09:45'):
        super().__init__(name, instr, prcType, stopper, hmUnw, hmPre=hmPre, hmCur=hmCur)

    def signals(self, bars):
        ranges_15 = ['9:00','9:15','9:30','9:45','10:00','10:15','10:30','10:45','11:00','11:15','11:30','11:45','12:00']        
        flag = super().signals(bars)
        day1 = daily_snapshots(bars, self.prcType, ranges_15, 'America/New_York')


        return flag

# 7. Measure the standard deviation for all 15, 30, 45 and 60-minute periods from 9am to 12pm.  If the value is a
#    30-day high for the relevant timeframe, go short; if the value is a 30-day low for the relevant timeframe, go long.
class NewRule7(RiseFall):
    def __init__(self, name, instr, prcType: str, stopper, hmUnw: str='16:00', *, 
                 hmPre='9:30,16:00', hmCur: str='09:30,09:45'):
        super().__init__(name, instr, prcType, stopper, hmUnw, hmPre=hmPre, hmCur=hmCur)

    def signals(self, bars):
        flag = super().signals(bars)
        return flag

# 8. If the e-mini rises (or falls) between 4pm and 9.30am by more than it has on any of the previous 30 days, 
#    and the S&P 500 also rises (or falls), go long (or short) at 9.30am.
class NewRule8(RiseFall):
    def __init__(self, name, instr, prcType: str, stopper, hmUnw: str = '16:00', *,
                 hmPre='16:00', hmCur: str = '09:30'):
        super().__init__(name, instr, prcType, stopper, hmUnw, hmPre=hmPre, hmCur=hmCur)

    def signals(self, bars):
        # signals from prices
        flag = super().signals(bars)

        # grab prev day at 16:00
        day1 = daily_snapshots(bars, self.prcType, self.hmPre, 'America/New_York')
        day1 = day1.shift(1)
        day1.columns = [f"prev-{c}" for c in day1.columns]
        day2 = daily_snapshots(bars, self.prcType, self.hmCur, 'America/New_York')
        test = pd.concat([day1, day2], axis=1)

        # series can be slightly different due to holidays and nan's being dropped, align them
        test = test.loc[test.index.intersection(flag.index)]
        flag = flag.loc[test.index]

        # calc difference, 21 business days ~= 30 calendar days
        test['diff'] = test[f'{self.prcType}-{self.hmCur[0]}'] - test[f'prev-{self.prcType}-{self.hmPre[-1]}']
        test['diff-30-up'] = test['diff'].rolling(21).max() 
        test['diff-30-dn'] = test['diff'].rolling(21).min() 

        flag2 = pd.Series(index=flag.index, data=0)
        long = (flag > 0) & (test['diff'] > 0) & (test['diff'] >= test['diff-30-up'])
        shrt = (flag < 0) & (test['diff'] < 0) & (test['diff'] <= test['diff-30-dn'])

        flag2[long] = 1
        flag2[shrt] = -1
        return flag2


# Strategies for trading the e-mini while the cash market is closed
#
# 1. If the price falls between 9.30am and 12pm then rises from 12pm to 4pm, go long 4pm to 9.30am.
#
# 2. If the difference between the opening and low prices hits a 30 (or 60) -day low, and the price rises 
#    from 9.30am to 4pm, go long 4pm to 9.30am.
#
# 3. If the price hits a 30-day high or a new all-time high between 9.30am and 4pm, go long 4pm to 9.30am.
#
# 4. If the price rises between 9.30am and 4pm by more than the previous 30 days then go long 4pm to 9.30am.
#
# 5. If the price rises between 9.30am and 4pm and the daily range hits a 30-day low, go long 4pm to 9.30am.
#
# 6. If the price falls between 9.30am and 3.30pm (or 4pm) by more than it has for the past 30 (or 60) days, then rises
#    between 3.30pm and 4.30pm (or between 4pm and 5pm), go long 4.30pm (or 5pm) to 9.30am.
#
# 7. Take the opening and closing prices of each 15 (or 30, 45, 60) consecutive one-minute periods from 12pm to 5pm and
#    calculate the number of times the price changes direction.  If the number is a 7 (or 14, 21, 30) -day high, go
#    short; if the number is a 7 (or 14, 21, 30) –day low, go long.
#
# 8. Measure the standard deviation for all 15, 30, 45 and 60-minute periods from 3.30pm to 4.30pm.  If the value is
#    a 30-day high for the relevant timeframe, go short; if the value is a 30-day low for the relevant timeframe, 
#    go long.
#
# 9. Measure the price range for all 15, 30, 45 and 60-minute periods from 3pm to 5pm.  If the range hits a 30-day
#    low and the volume is equal to or greater than the mean for this period, then go long if the price rises by 
#    70% of the range and short if the price falls by 70% of the range.
#
# Strategies for trading the e-mini while the cash market is open
# 
# 3. Measure the price range for all 15, 30, 45 and 60-minute periods from 9am to 12pm.  If the range hits a 30-day
#    low and the volume is equal to or greater than the mean for this period, then go short if the price falls by 70%
#    of the range and long if the price rises by 70% of the range.
# 
# 6. Take the opening and closing prices of each 15 (or 30, 45, 60) consecutive one-minute periods from 9am to 12pm
#    and calculate the number of times the price changes direction.  If the number is a 7 (or 14, 21, 30) -day high,
#    go short; if the number is a 7 (or 14, 21, 30) –day low, go long.
# 
# 7. Measure the standard deviation for all 15, 30, 45 and 60-minute periods from 9am to 12pm.  If the value is a
#    30-day high for the relevant timeframe, go short; if the value is a 30-day low for the relevant timeframe, go long.
# 
