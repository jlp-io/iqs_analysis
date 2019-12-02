# %%
# To Create File

from datetime import date, time, datetime
import numpy as np
import pandas as pd
import strat.fut.fut_utils as u


univ_jp = [
    #900139, # NYBOT Dollar Index (Gen  1)
    900055, # CME Currency EUR (Gen  1)
    900032, # NYMEX WTI Crude Oil (Gen  1)
    900030, # COMEX Silver 5000 Oz (Gen  1)
    900035, # CBOT Corn (Gen  1)
]

hdf5_fn = 'jp-univ.h5'

# start and end dates
hist_sdate = date(2015, 1, 4)
hist_edate = date(2018, 12, 28)  # friday before Christmas

bar_sdate = date(2016, 1, 4)

tgt_vol_ann = 0.01 * np.sqrt(252)  # 0.25  # annualised target volatility ~ 1% per day * sqrt(252)

fser, data = u.load_univ_data(univ_jp, hist_sdate, bar_sdate, hist_edate, tgt_vol_ann)

pd.set_option('io.hdf.default_format', 'table')
hdf = pd.HDFStore(hdf5_fn, complib='zlib', complevel=6)
hdf.put('fser', fser)
for fut in data.keys():
    for freq in '15m,dly'.split(','):
        hdf.put(f"f{fut}_{freq}", data[fut][freq])
hdf.close()


# %%
# To Load File
import pandas as pd

hdf5_fn = 'jp_univ.h5'

hdf = pd.HDFStore(hdf5_fn, complib='zlib', complevel=6)
fser = hdf.get('fser')
data = {}
for fut in fser.index:
    data[fut] = {}
    for freq in '15m,dly'.split(','):
        data[fut][freq] = hdf.get(f"f{fut}_{freq}")
hdf.close()

# drop useless columns from descriptive df
fser.drop('is_gbx,ric,bbid,frst_tdate,last_tdate,fser,fmth,undl,isin,icb'.split(','), axis=1)
