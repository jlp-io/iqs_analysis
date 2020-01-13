# %%
from datetime import date, time, datetime
import numpy as np
import pandas as pd
import emini_bokeh as plts
from emini_stops import StopNone, StopSimple, StopTrail
from emini_strategies import (
    RiseFall, RiseFallVolume, Overnight,
    NewRule2, NewRule3, NewRule4, NewRule5, NewRule6, NewRule7, NewRule8,
)
from emini_scenarios import run_scenario, run_scenarios

# %%

# Read Old Data
old = pd.read_csv('S&P eMini 15min II.csv')
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
# Strategies for trading the e-mini while the cash market is open
# 
# 1. If the prices of both the e-mini and S&P 500 fall (or rise) between 4pm and 9.30am and fall (or rise) again
#    between 9.30am and 9.45am, go short (or long) at 9.45am and exit the position at 4pm.
# 

scenarios = {
    'unw 16:00, in-stop':
        [
            RiseFall('1', 'CME SP500 eMini', 'clsPrc', StopNone(), '16:00', hmPre='16:00', hmCur='09:30, 09:45'),
            #NewRule2('2', 'CME SP500 eMini', 'clsPrc', StopNone()),
            #NewRule3('3', 'CME SP500 eMini', 'clsPrc', StopNone()),            
            #NewRule4('4', 'CME SP500 eMini', 'clsPrc', StopNone()),
            #NewRule5('5', 'CME SP500 eMini', 'clsPrc', StopNone()),
            #NewRule6('6', 'CME SP500 eMini', 'clsPrc', StopNone()),            
            NewRule7('7', 'CME SP500 eMini', 'clsPrc', StopNone()),            
            NewRule8('8', 'CME SP500 eMini', 'clsPrc', StopNone()),
        ],

    'unw 16:00, no-stop':
        [
            RiseFall('1', 'CME SP500 eMini', 'clsPrc', StopSimple('inPrc', 0.008), '16:00', hmPre='16:00', hmCur='09:30, 09:45'),
            #NewRule2('2', 'CME SP500 eMini', 'clsPrc', StopSimple('inPrc', 0.008)),
            #NewRule3('3', 'CME SP500 eMini', 'clsPrc', StopSimple('inPrc', 0.008)),                        
            #NewRule4('4', 'CME SP500 eMini', 'clsPrc', StopSimple('inPrc', 0.008)),
            #NewRule5('5', 'CME SP500 eMini', 'clsPrc', StopSimple('inPrc', 0.008)),
            #NewRule6('6', 'CME SP500 eMini', 'clsPrc', StopSimple('inPrc', 0.008)),            
            NewRule7('7', 'CME SP500 eMini', 'clsPrc', StopSimple('inPrc', 0.008)),            
            NewRule8('8', 'CME SP500 eMini', 'clsPrc', StopSimple('inPrc', 0.008)),
        ],
}

old_out = run_scenarios(old_data, scenarios)
plts.do_plot(*old_out[1:], 'emini-new-day.html')