# %%
from datetime import date, time, datetime
import numpy as np
import pandas as pd

import emini_bokeh as plts
from emini_stops import StopNone, StopSimple, StopTrail
from emini_strategies import (
    RiseFall, RiseFallVolume, Overnight,
    NewRule2, NewRule4, NewRule5, NewRule8,
)

from emini_scenarios import run_scenario, run_scenarios

# Read new data

hist_sdate = date(2016, 1, 4)
hist_edate = date(2018, 12, 28)  # friday before Christmas
bar_sdate = date(2016, 1, 4)

# univ to load
univ = [
    900037, #             CBOT DJIA eMini
    900061, #  CME NASDAQ 100 Index eMini
    #900063, #    CME Nikkei 225 Index USD
    900065, #      CME S&P500 Index eMini
    #900175, #    CME Nikkei 225 Index JPY
    900181, # CME S&P Mid 400 Index eMini
    900029, # COMEX Gold 100 Troy Ounces
]

univ = [900065, 900029]

hdf_fn = 'c:/tmp/blp/emini.h5'

# load
if False:
    import strat.fut.fut_utils as u

    # start date for historical data (TSUM flag start)
    tgt_vol_ann = 0.01 * np.sqrt(252)  # 0.25  # annualised target volatility ~ 1% per day * sqrt(252)

    # fser, data = u.load_univ_data(ctl.univ.fut_tsum[:3], hist_sdate, bar_sdate, hist_edate, tgt_vol_ann)
    fser, data = u.load_univ_data(univ, hist_sdate, bar_sdate, hist_edate, tgt_vol_ann)

    pd.set_option('io.hdf.default_format', 'table')
    hdf = pd.HDFStore(hdf_fn, complib='zlib', complevel=6, mode='w')
    hdf.put('fser', fser)
    for fut in data.keys():
        for freq in '1m,15m,dly'.split(','):
            hdf.put(f"f{fut}_{freq}", data[fut][freq])
    hdf.close()
else:
    hdf = pd.HDFStore(hdf_fn, mode='r')
    fser = hdf.get('fser')
    data = {}
    for fut in univ:
        data[fut] = {}
        for freq in '1m,15m,dly'.split(','):
            data[fut][freq] = hdf.get(f"f{fut}_{freq}")
    hdf.close()

new_data = data


# %%

def new_synthetic_prices(bars):
    # synthetic prices, based off trdRet for new data
    synth = pd.DataFrame(index=bars.index, columns='bbt,opnPrc,higPrc,lowPrc,clsPrc,trdQty'.split(','))
    lr = bars['trdRet']
    synth['clsPrc'] = np.around(np.exp(lr.cumsum()) * 2000, decimals=4)

    # o,h,l as offsets
    for col in 'higPrc,lowPrc,opnPrc'.split(','):
        r = np.log(bars[col] / bars['clsPrc'])
        synth[col] = np.around(np.exp(r + lr.cumsum()) * 2000, decimals=4)

    synth['trdQty'] = bars['trdQty']
    synth['futc'] = bars['futc']

    return synth


raw_data = {
    'CME SP500 eMini': {
        '15m': new_data[900065]['15m']
    },
    'COMEX Gold 100oz': {
        '15m': new_data[900029]['15m']
    }
}

syn_data = {
    'CME SP500 eMini': {
        '15m': new_synthetic_prices(new_data[900065]['15m'])
    },
    'COMEX Gold 100oz': {
        '15m': new_synthetic_prices(new_data[900029]['15m'])
    }
}

# ToDo: offset by 1 minute


# %%
scenarios = {
    'unw 16:00, in-stop, strat1 09:45':
        [
            RiseFall('1', 'CME SP500 eMini', 'clsPrc', StopSimple('inPrc', 0.008), '16:00',
                     hmCur='09:00, 09:15, 09:30, 09:45'),
            RiseFall('2', 'CME SP500 eMini', 'clsPrc', StopSimple('inPrc', 0.008), '16:00', hmPre='09:45, 15:15, 16:00',
                     hmCur='09:30, 09:45'),
            RiseFallVolume('3', 'CME SP500 eMini', 'clsPrc', StopSimple('inPrc', 0.008), '16:00', hmCur='09:30, 09:45'),
            Overnight('4', 'CME SP500 eMini', 'clsPrc', StopSimple('inPrc', 0.008), '16:00', '09:30'),
            Overnight('5', 'COMEX Gold 100oz', 'clsPrc', StopSimple('inPrc', 0.008), '16:00', '09:30'),
        ],

    'unw 16:00, in-stop, hilo, strat1 09:45':
        [
            RiseFall('1', 'CME SP500 eMini', 'clsPrc', StopSimple('inPrc', 0.008), '16:00',
                     hmCur='09:00, 09:15, 09:30, 09:45',
                     hmHiLo='09:30, 09:45'),
            RiseFall('2', 'CME SP500 eMini', 'clsPrc', StopSimple('inPrc', 0.008), '16:00', hmPre='09:45, 15:15, 16:00',
                     hmCur='09:30, 09:45', hmHiLo='09:30, 09:45'),
            RiseFallVolume('3', 'CME SP500 eMini', 'clsPrc', StopSimple('inPrc', 0.008), '16:00', hmCur='09:30, 09:45',
                           hmHiLo='09:30, 09:45'),
            Overnight('4', 'CME SP500 eMini', 'clsPrc', StopSimple('inPrc', 0.008), '16:00', '09:30'),
            Overnight('5', 'COMEX Gold 100oz', 'clsPrc', StopSimple('inPrc', 0.008), '16:00', '09:30'),
        ],

    'unw 16:00, no-stop, strat1 09:45':
        [
            RiseFall('1', 'CME SP500 eMini', 'clsPrc', StopNone(), '16:00',
                     hmCur='09:00, 09:15, 09:30, 09:45'),
            RiseFall('2', 'CME SP500 eMini', 'clsPrc', StopNone(), '16:00', hmPre='09:45, 15:15, 16:00',
                     hmCur='09:30, 09:45'),
            RiseFallVolume('3', 'CME SP500 eMini', 'clsPrc', StopNone(), '16:00', hmCur='09:30, 09:45'),
            Overnight('4', 'CME SP500 eMini', 'clsPrc', StopNone(), '16:00', '09:30'),
            Overnight('5', 'COMEX Gold 100oz', 'clsPrc', StopNone(), '16:00', '09:30'),
        ],

    'unw 16:00, no-stop, hilo, strat1 09:45':
        [
            RiseFall('1', 'CME SP500 eMini', 'clsPrc', StopNone(), '16:00',
                     hmCur='09:00, 09:15, 09:30, 09:45',
                     hmHiLo='09:30, 09:45'),
            RiseFall('2', 'CME SP500 eMini', 'clsPrc', StopNone(), '16:00', hmPre='09:45, 15:15, 16:00',
                     hmCur='09:30, 09:45', hmHiLo='09:30, 09:45'),
            RiseFallVolume('3', 'CME SP500 eMini', 'clsPrc', StopNone(), '16:00', hmCur='09:30, 09:45',
                           hmHiLo='09:30, 09:45'),
            Overnight('4', 'CME SP500 eMini', 'clsPrc', StopNone(), '16:00', '09:30'),
            Overnight('5', 'COMEX Gold 100oz', 'clsPrc', StopNone(), '16:00', '09:30'),
        ],
}

raw_out = run_scenarios(raw_data, scenarios)
plts.do_plot(*raw_out[1:], 'c:/tmp/plots/emini-hilo-onight-raw-ii.html')

syn_out = run_scenarios(syn_data, scenarios)
plts.do_plot(*syn_out[1:], 'c:/tmp/plots/emini-hilo-onight-syn.html')


# %%

# Read Old Data
old = pd.read_csv('c:/tmp/S&P eMini 15min II.csv')
old['ts'] = pd.to_datetime(old['ts'], format='%Y-%m-%d %H:%M')
old.set_index('ts', inplace=True, verify_integrity=True)
old.index = old.index.tz_localize('America/New_York')
old.columns = 'bbt,clsPrc,higPrc,lowPrc,opnPrc,trdQty'.split(',')

old_data = {
    'CME SP500 eMini': {
        '15m': old
    }
}

# %%
scenarios = {
    'unw 16:00, in-stop, strat1 09:45':
        [
            RiseFall('1', 'CME SP500 eMini', 'clsPrc', StopSimple('inPrc', 0.008), '16:00',
                     hmCur='09:00, 09:15, 09:30, 09:45'),
            RiseFall('2', 'CME SP500 eMini', 'clsPrc', StopSimple('inPrc', 0.008), '16:00', hmPre='09:45, 15:15, 16:00',
                     hmCur='09:30, 09:45'),
            RiseFallVolume('3', 'CME SP500 eMini', 'clsPrc', StopSimple('inPrc', 0.008), '16:00', hmCur='09:30, 09:45'),
            Overnight('4', 'CME SP500 eMini', 'clsPrc', StopSimple('inPrc', 0.008), '16:00', '09:30'),
            # Overnight('5', 'COMEX Gold 100oz', 'clsPrc', StopSimple('inPrc', 0.008), '16:00', '09:30'),
        ],

    'unw 16:00, in-stop, hilo, strat1 09:45':
        [
            RiseFall('1', 'CME SP500 eMini', 'clsPrc', StopSimple('inPrc', 0.008), '16:00',
                     hmCur='09:00, 09:15, 09:30, 09:45',
                     hmHiLo='09:30, 09:45'),
            RiseFall('2', 'CME SP500 eMini', 'clsPrc', StopSimple('inPrc', 0.008), '16:00', hmPre='09:45, 15:15, 16:00',
                     hmCur='09:30, 09:45', hmHiLo='09:30, 09:45'),
            RiseFallVolume('3', 'CME SP500 eMini', 'clsPrc', StopSimple('inPrc', 0.008), '16:00', hmCur='09:30, 09:45',
                           hmHiLo='09:30, 09:45'),
            Overnight('4', 'CME SP500 eMini', 'clsPrc', StopSimple('inPrc', 0.008), '16:00', '09:30'),
            # Overnight('5', 'COMEX Gold 100oz', 'clsPrc', StopSimple('inPrc', 0.008), '16:00', '09:30'),
        ],

    'unw 16:00, no-stop, strat1 09:45':
        [
            RiseFall('1', 'CME SP500 eMini', 'clsPrc', StopNone(), '16:00',
                     hmCur='09:00, 09:15, 09:30, 09:45'),
            RiseFall('2', 'CME SP500 eMini', 'clsPrc', StopNone(), '16:00', hmPre='09:45, 15:15, 16:00',
                     hmCur='09:30, 09:45'),
            RiseFallVolume('3', 'CME SP500 eMini', 'clsPrc', StopNone(), '16:00', hmCur='09:30, 09:45'),
            Overnight('4', 'CME SP500 eMini', 'clsPrc', StopNone(), '16:00', '09:30'),
            # Overnight('5', 'COMEX Gold 100oz', 'clsPrc', StopNone(), '16:00', '09:30'),
        ],

    'unw 16:00, no-stop, hilo, strat1 09:45':
        [
            RiseFall('1', 'CME SP500 eMini', 'clsPrc', StopNone(), '16:00',
                     hmCur='09:00, 09:15, 09:30, 09:45',
                     hmHiLo='09:30, 09:45'),
            RiseFall('2', 'CME SP500 eMini', 'clsPrc', StopNone(), '16:00', hmPre='09:45, 15:15, 16:00',
                     hmCur='09:30, 09:45', hmHiLo='09:30, 09:45'),
            RiseFallVolume('3', 'CME SP500 eMini', 'clsPrc', StopNone(), '16:00', hmCur='09:30, 09:45',
                           hmHiLo='09:30, 09:45'),
            Overnight('4', 'CME SP500 eMini', 'clsPrc', StopNone(), '16:00', '09:30'),
            # Overnight('5', 'COMEX Gold 100oz', 'clsPrc', StopNone(), '16:00', '09:30'),
        ],
}

old_out = run_scenarios(old_data, scenarios)
plts.do_plot(*old_out[1:], 'c:/tmp/plots/emini-hilo-onight-old.html')

# %%
# Strategies for trading the e-mini while the cash market is open
# 
# 1. If the prices of both the e-mini and S&P 500 fall (or rise) between 4pm and 9.30am and fall (or rise) again
#    between 9.30am and 9.45am, go short (or long) at 9.45am and exit the position at 4pm.
# 

scenarios = {
    'unw 16:00, in-stop':
        [
            RiseFall('1', 'CME SP500 eMini', 'clsPrc', StopNone(), '16:00', hmPre='16:00', hmCur='09:30, 09:45'),
            NewRule2('2', 'CME SP500 eMini', 'clsPrc', StopNone()),
            NewRule4('4', 'CME SP500 eMini', 'clsPrc', StopNone()),
            NewRule5('5', 'CME SP500 eMini', 'clsPrc', StopNone()),
            NewRule8('8', 'CME SP500 eMini', 'clsPrc', StopNone()),
        ],

    'unw 16:00, no-stop':
        [
            RiseFall('1', 'CME SP500 eMini', 'clsPrc', StopSimple('inPrc', 0.008), '16:00', hmPre='16:00', hmCur='09:30, 09:45'),
            NewRule2('2', 'CME SP500 eMini', 'clsPrc', StopSimple('inPrc', 0.008)),
            NewRule4('4', 'CME SP500 eMini', 'clsPrc', StopSimple('inPrc', 0.008)),
            NewRule5('5', 'CME SP500 eMini', 'clsPrc', StopSimple('inPrc', 0.008)),
            NewRule8('8', 'CME SP500 eMini', 'clsPrc', StopSimple('inPrc', 0.008)),
        ],
}

old_out = run_scenarios(old_data, scenarios)
plts.do_plot(*old_out[1:], 'c:/tmp/plots/emini-new-day.html')

