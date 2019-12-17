# %%
from datetime import date, time, datetime
import numpy as np
import pandas as pd
from metric_calc import risk_summary

def run_scenario(data, strategies):
    trds = []
    for strat in strategies:
        trds.append(strat.trades(data))
    trds = pd.concat(trds)
    trds['logRet'] = np.log(trds['outPrc'] / trds['inPrc']) * trds['sigVal']
    trds = trds.set_index(['tdate', 'strat'])
    return trds

def run_scenarios(data, scenarios):

    # list of all strats in all scenarios
    all_strats = [s  # return value
                  for v in scenarios.values()  # outer loop 
                  for s in v]  # inner loop

    # start and end dates for p&l, etc.
    sdate = data[all_strats[0].instr]['15m'].index[0].date()
    edate = data[all_strats[0].instr]['15m'].index[-1].date()

    trds = {}
    scenario_pnl = pd.DataFrame(index=pd.bdate_range(sdate, edate))
    scenario_stats = {}

    strategy_pnl = {}
    strategy_stats = {}

    for scen_name, strats in scenarios.items():
        print(f'running {scen_name}')
        #ValueError: can not merge DataFrame with instance of type <class 'pandas.core.series.Series'>
        trds[scen_name] = run_scenario(data, strats)

        # scenario level outputs
        scenario_pnl[scen_name] = trds[scen_name]['logRet'].groupby(level=0).sum()
        scenario_pnl[scen_name].fillna(0, inplace=True)
        scenario_stats[scen_name] = risk_summary(scenario_pnl[scen_name])
        scenario_stats[scen_name]['Trades'] = f'{trds[scen_name].shape[0]}'

        # strategy level outputs, in a dict by strategy and scenario
        level1 = trds[scen_name].index.unique(level=1)

        # initialize pnl and descriptions for strategies
        for strat in strats:
            if strat.name not in strategy_pnl.keys():
                strategy_pnl[strat.name] = pd.DataFrame(index=scenario_pnl.index, dtype=np.float64)
                strategy_stats[strat.name] = {}

            lr = trds[scen_name].xs(strat.name, level=1)['logRet']
            strategy_pnl[strat.name][scen_name] = lr
            strategy_pnl[strat.name][scen_name].fillna(0, inplace=True)

            strategy_stats[strat.name][scen_name] = {k.capitalize(): v for k, v in strat.descr.items()}
            strategy_stats[strat.name][scen_name].update(risk_summary(strategy_pnl[strat.name][scen_name]))
            strategy_stats[strat.name][scen_name]['Trades'] = lr.shape[0]

    scenario_stats = pd.DataFrame(scenario_stats).T
    for k in strategy_stats.keys():
        strategy_stats[k] = pd.DataFrame(strategy_stats[k]).T
    return trds, scenario_pnl, scenario_stats, strategy_pnl, strategy_stats