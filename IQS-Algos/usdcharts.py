import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import quandl
import pandas as pd
import numpy as np

def main():
    quandl.ApiConfig.api_key = "HAQ5HX1UH9eB9virjnGF"
    starting_periods = ['2008-01-01', '2009-01-01', '2010-01-01', '2011-01-01', '2012-01-01', '2013-01-01', '2014-01-01', '2015-01-01', '2016-01-01', '2017-01-01', '2018-01-01']
    ending_periods = ['2008-06-02', '2009-06-01', '2010-06-01', '2011-06-01', '2012-06-01', '2013-06-03', '2014-06-02', '2015-06-01', '2016-06-01', '2017-06-01', '2018-06-01']
    year_ending_periods = ['2009-01-01', '2010-01-01', '2011-01-01', '2012-01-01', '2013-01-01', '2014-01-01', '2015-01-01', '2016-01-01', '2017-01-01', '2018-01-01', '2018-12-18']
    start_dates = [3198, 3460, 3721, 3982, 4242, 4503, 4764, 5025, 5286, 5547, 5807]
    end_dates = [3307, 3567, 3828, 4089, 4351, 4612, 4872, 5132, 5394, 5655, 5916]
    year_end_dates = [3460, 3721, 3982, 4242, 4503, 4764, 5025, 5286, 5547, 5807, 6058]

    for i in range(0,len(starting_periods)):
        try:
            starting_period = pd.Timestamp(starting_periods[i])
            ending_period = pd.Timestamp(ending_periods[i])
            dollar_index = quandl.get(
                "CHRIS/ICE_DX1", start_date=starting_period, end_date=ending_period)
            iqs_daily_returns = pd.read_csv('iqs-daily-ror.csv')
            
            plt.figure()
            plt.title("Dollar index: " + starting_periods[i] + " to " + ending_periods[i])
            
            

            #blue_patch = mpatches.Patch(color='blue', label='High')
            #orange_patch = mpatches.Patch(color='orange', label='Low')
            #green_patch = mpatches.Patch(color='green', label='Open')
            #red_patch = mpatches.Patch(color='red', label='Close')

            #plt.legend(handles=[blue_patch, orange_patch, green_patch, red_patch])

            #plt.plot(dollar_index['High'])
            #plt.plot(dollar_index['Low'])
            #plt.plot(dollar_index['Open'])
            #plt.plot(dollar_index['Settle'])

            #dollar_index.to_csv("dollar-index.csv")

            plt.figure()
            plt.title("IQS Equity Curve: " + starting_periods[i] + " to " + ending_periods[i])
            plt.plot(iqs_daily_returns['Index'][start_dates[i]:end_dates[i]])
            plt.show()

            #short timeframes for iqs daily ror index values
            '''
            security = quandl.get(
                "SRF/CME_SPZ2017", start_date=starting_period, end_date=ending_period)
            print(security)
            plt.figure()
            plt.plot(security['High'])
            plt.plot(security['Low'])
            plt.plot(security['Open'])
            # plt.plot(security['Close'])
            '''

        except:
            return 0

if __name__ == "__main__":
    main()