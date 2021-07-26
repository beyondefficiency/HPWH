# -*- coding: utf-8 -*-
"""
Created on Tue May 25 19:48:38 2021

@author: Peter Grant
"""

import pandas as pd
import os

Minutes_In_Hour = 60
prices = {'0': 0.20, '1': 0.20, '2': 0.20, '3': 0.20, '4': 0.20, '5': 0.20, 
              '6': 0.20, '7': 0.20, '8': 0.20, '9': 0.20, '10': 0.25, '11': 
               0.25, '12': 0.25, '13': 0.25, '14': 0.25, '15': 0.25, '16':
               0.3, '17': 0.3, '18': 0.3, '19': 0.3, '20': 0.3, '21': 0.2, 
               '22': 0.2, '23': 0.2}

cwd = os.getcwd()
File = cwd + r'\Output\Output_Creekside Data for 3CFA.csv'

Data = pd.read_csv(File, index_col = 'Timestamp')
Data.index = pd.to_datetime(Data.index)

# Calculate a weighted average for parameters as necessary
columns = ['Set Temperature (deg C)', 'Tank Temperature (deg C)', 
           'Ambient Temperature (deg C)', 'Inlet Water Temperature (deg C)']

for column in columns:
    Data[column] = Data[column] * (Data['Timestep (min)'] / Minutes_In_Hour)

# It's possible the file does not contain all of these columns. Edit this line
# as necessary
Data = Data.drop(columns=['Time (s)', 'Timestep (min)', 'COP', 
                          'Power_PowerSum_W', 'Power_EnergySum_kWh'])

Hourly = Data.resample('H').sum()
