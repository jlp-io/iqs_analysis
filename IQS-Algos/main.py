import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import quandl
import requests

if __name__ == '__main__':
    alphavantage_api_key = "V7C9RZ8YFBHTLSBL"
    security = requests.get('https://www.alphavantage.co/query?function=FX_DAILY&from_symbol=EUR&to_symbol=USD&apikey='+alphavantage_api_key)
