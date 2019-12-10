# %%

class StopNone:
    @property
    def descr(self):
        return 'none'

    def calc_stop(self, prc15, trd):
        return None, None


class StopSimple:
    def __init__(self, prcCol : str, prcPct : str):
        self.prcCol = prcCol
        self.prcPct = prcPct
        
    @property
    def descr(self):
        return f'simple {self.prcCol} {self.prcPct:0.2%}'
    
    def calc_stop(self, prc15, trd):
        stopPrc = trd[self.prcCol]
        sideBuy = trd['sigVal'] > 0
        if sideBuy:
            stopPrc *= (1 - self.prcPct)
            stops = prc15['lowPrc'] < stopPrc
        else:
            stopPrc *= (1 + self.prcPct)
            stops = prc15['higPrc'] > stopPrc
        
        if stops.any():
            stopTime = stops.idxmax()
            stopTrig = prc15.loc[stopTime, 'lowPrc'] if sideBuy else prc15.loc[stopTime, 'higPrc']
            return stopTime, stopTrig
        
        return None, None


class StopTrail:
    def __init__(self, prcPct: str):
        self.prcPct = prcPct

    @property
    def descr(self):
        return f'trailing {self.prcPct:0.2%}'

    def calc_stop(self, prc15, trd):
        stopPrc = trd['inPrc']
        sideBuy = trd['sigVal'] > 0
        if sideBuy:
            for row in prc15.itertuples():
                if row.lowPrc < stopPrc * (1 - self.prcPct):
                    return row.Index, row.lowPrc
                elif row.clsPrc > stopPrc:
                    stopPrc = row.clsPrc
        else:
            for row in prc15.itertuples():
                if row.higPrc > stopPrc * (1 + self.prcPct):
                    return row.Index, row.higPrc
                elif row.clsPrc < stopPrc:
                    stopPrc = row.clsPrc

        return None, None
