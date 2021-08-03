# -*- coding: utf-8 -*-
"""
Created on Thu Jul 15 18:38:32 2021

# This script contains a single function used to implement different forms of 
# load shifting controls in heat pump water heaters (HPWHs). The profiles can
# be read by the simulation models to use as needed.

@author: Peter Grant
"""

def get_profile(profile):
    if profile == 'Static_48.9':
        set_temperatures = {'0': 48.9, '1': 48.9, '2': 48.9, '3': 48.9, '4': 
            48.9, '5': 48.9, '6': 48.9, '7': 48.9, '8': 48.9, '9': 48.9, '10': 
            48.9, '11': 48.9, '12': 48.9, '13': 48.9, '14': 48.9, '15': 48.9, 
            '16': 48.9, '17': 48.9, '18': 48.9, '19': 48.9, '20': 48.9, '21': 
            48.9, '22': 48.9, '23': 48.9}
    elif profile == 'Static_54.4':
        set_temperatures = {'0': 54.4, '1': 54.4, '2': 54.4, '3': 54.4, '4': 
            54.4, '5': 54.4, '6': 54.4, '7': 54.4, '8': 54.4, '9': 54.4, '10': 
            54.4, '11': 54.4, '12': 54.4, '13': 54.4, '14': 54.4, '15': 54.4, 
            '16': 54.4, '17': 54.4, '18': 54.4, '19': 54.4, '20': 54.4, '21': 
            54.4, '22': 54.4, '23': 54.4}        
    elif profile == 'Static_60':
        set_temperatures = {'0': 60, '1': 60, '2': 60, '3': 60, '4': 
            60, '5': 60, '6': 60, '7': 60, '8': 60, '9': 60, '10': 
            60, '11': 60, '12': 60, '13': 60, '14': 60, '15': 60, 
            '16': 60, '17': 60, '18': 60, '19': 60, '20': 60, '21': 
            60, '22': 60, '23': 60}
    elif profile == '8A-4P LoadShift, 48.9 & 60 deg C':
        set_temperatures = {'0': 48.9, '1': 48.9, '2': 48.9, '3': 48.9, '4': 
            48.9, '5': 48.9, '6': 48.9, '7': 48.9, '8': 60, '9': 60, '10': 
            60, '11': 60, '12': 60, '13': 60, '14': 60, '15': 60, 
            '16': 48.9, '17': 48.9, '18': 48.9, '19': 48.9, '20': 48.9, '21': 
            48.9, '22': 48.9, '23': 48.9}
    elif profile == '8A-2P LoadShift, 48.9 & 60 deg C':
        set_temperatures = {'0': 48.9, '1': 48.9, '2': 48.9, '3': 48.9, '4': 
            48.9, '5': 48.9, '6': 48.9, '7': 48.9, '8': 60, '9': 60, '10': 
            60, '11': 60, '12': 60, '13': 60, '14': 48.9, '15': 48.9, 
            '16': 48.9, '17': 48.9, '18': 48.9, '19': 48.9, '20': 48.9, '21': 
            48.9, '22': 48.9, '23': 48.9}        
    elif profile == '8A-4P LoadShift, 48.9 & 56.1 deg C':
        set_temperatures = {'0': 48.9, '1': 48.9, '2': 48.9, '3': 48.9, '4': 
            48.9, '5': 48.9, '6': 48.9, '7': 48.9, '8': 56.1, '9': 56.1, '10': 
            56.1, '11': 56.1, '12': 56.1, '13': 56.1, '14': 56.1, '15': 56.1, 
            '16': 48.9, '17': 48.9, '18': 48.9, '19': 48.9, '20': 48.9, '21': 
            48.9, '22': 48.9, '23': 48.9}        
    return set_temperatures

if __name__ == '__main__':
    import matplotlib.pyplot as plt
    plt.figure(figsize = (12, 5))
    profiles = ['Static_48.9', 'Static_54.4', 'Static_60', 
                '8A-4P LoadShift, 48.9 & 60 deg C', 
                '8A-2P LoadShift, 48.9 & 60 deg C',
                '8A-4P LoadShift, 48.9 & 56.1 deg C']
    
    for profile in profiles:
        output = get_profile(profile)
        print(profile)
        print(output)
        print(output.keys())
        print(output.values)
        plt.plot(list(output.keys()), list(output.values()), label = profile)
    
    plt.legend()    
    plt.xlabel ('Time of Day (hr)')
    plt.ylabel('Set Temperature (deg C)')
        
    
    
