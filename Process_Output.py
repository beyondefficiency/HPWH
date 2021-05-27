# -*- coding: utf-8 -*-
"""
Created on Tue May 25 19:48:38 2021

@author: Peter Grant
"""

import pandas as pd
import os

prices = {'0': 0.20, '1': 0.20, '2': 0.20, '3': 0.20, '4': 0.20, '5': 0.20, 
              '6': 0.20, '7': 0.20, '8': 0.20, '9': 0.20, '10': 0.25, '11': 
               0.25, '12': 0.25, '13': 0.25, '14': 0.25, '15': 0.25, '16':
               0.3, '17': 0.3, '18': 0.3, '19': 0.3, '20': 0.3, '21': 0.2, 
               '22': 0.2, '23': 0.2}

cwd = os.getcwd()
File = cwd + r'\Output\Output_30_P30104_3CFA.csv'

Data = pd.read_csv(File, index_col = 'Timestamp')
Data.index = pd.to_datetime(Data.index)

Hourly_Consumption = Data[['Electricity Consumed (kWh)']].resample('H').sum()
Hourly_Consumption['Hour'] = Hourly_Consumption.index.hour
Hourly_Consumption['Hour'] = Hourly_Consumption['Hour'].astype(str)
Hourly_Consumption['Price ($/kWh)'] = Hourly_Consumption['Hour'].map(prices)
Hourly_Consumption['Cost ($)'] = Hourly_Consumption['Electricity Consumed (kWh)'] * Hourly_Consumption['Price ($/kWh)']

Energy_Cost = Hourly_Consumption['Cost ($)'].sum()

#Add masking code to create a new dataframe showing only consumption durign a user defined peak period