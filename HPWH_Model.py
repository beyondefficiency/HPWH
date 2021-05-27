# -*- coding: utf-8 -*-
"""
Created on Tue Nov 19 09:51:40 2019

This module contains the actual model for a HPWH. It was pulled into this separate file to make it easier to maintain. This way it can
be referenced in both the simulation and validation scripts as needed.

Currently this module holds only Model_HPWH_MixedTank, representing a 1-node model with a fully mixed tank. The plan is to later add additional functions
for different assumptions as needed, creating a library of relevant simulation models.

This model has now been modified to include an occupant behavior learning algorithm. As currently implemented it tracks the electricity consumption
of the HPWH during the full day, peak period, and off peak period. It gradually builds an understanding of how the water heater consumes electricity
enabling the development of load shifting controls tailored to each specific site. To use this algorithm the input data must have timesteps
at midnight (Not close to midnight, AT midnight)

@author: Peter Grant
"""

import numpy as np
import pandas as pd

Minutes_In_Hour = 60 #Conversion between hours and minutes
Seconds_In_Minute = 60 #Conversion between minutes and seconds
Watts_In_kiloWatt = 1000 #Conversion between W and kW
SpecificHeat_Water = 4.190 #J/g-C
Density_Water = 1000 #g/L
kWh_In_Wh = 1/1000 #Conversion from Wh to kWh

def Model_HPWH_MixedTank(Model, Parameters, Regression_COP, Regression_COP_Derate_Tamb):

    data = Model.to_numpy() #convert the dataframe to a numpy array for EXTREME SPEED!!!! (numpy opperates in C)
    col_indx = dict(zip(Model.columns, list(range(0,len(Model.columns))))) #create a dictionary to provide column index references while using numpy in following loop

    for i  in range(1, len(data)): #Perform the modeling calculations for each row in the index
        #THESE TWO LINES OF CODE ARE ONLY APPROPRIATE WHEN SIMULATING MONITORED DATA IN THE CREEKSIDE PROJECT
        #The monitoring setup sometimes experiences data outages. We don't know the ambient temperature or hot water conusmption
        #during those outages. As a result, the model can't correctly predict what happens during those outages. To get the model
        #back on track we re-initialize the model to match the average of the tank thermostat measurements when data collection
        #returns
#        if data[i, col_indx['Timestep (min)']] > 5: #If the time since the last recording is > 5 minutes we assume there was a data collection outage
#            data[i, col_indx['Tank Temperature (deg C)']] = 0.5 * (data[i, col_indx['T_Tank_Upper_C']] + data[i, col_indx['T_Tank_Lower_C']]) #When data collection resumes we re-initialize the tank at current conditions by setting the water temperature equal to the average of the thermostat measurements
        # 1 - Calculate the jacket losses from the water in the tank to the ambient air
        data[i, col_indx['Jacket Losses (J)']] = -Parameters[0] * (data[i,col_indx['Tank Temperature (deg C)']] 
            - data[i,col_indx['Ambient Temperature (deg C)']]) * (data[i, col_indx['Timestep (min)']] * 
            Seconds_In_Minute)
        # 2- Calculate the energy added to the tank using the backup electric resistance element, if any:
        if data[i-1, col_indx['Energy Added Backup (J)']] == 0:  #If the backup heating element was NOT active during the last time step, Calculate the energy added to the tank using the backup electric resistance elements
            data[i, col_indx['Energy Added Backup (J)']] = Parameters[1] * \
                int(data[i, col_indx['Tank Temperature (deg C)']] < \
                data[i, col_indx['T_Activation_Backup_C']]) * (data[i, col_indx['Timestep (min)']] \
                * Seconds_In_Minute)
        else: #If it WAS active during the last time step, Calculate the energy added to the tank using the backup electric resistance elements
            data[i, col_indx['Energy Added Backup (J)']] = Parameters[1] * int(data[i, 
                col_indx['Tank Temperature (deg C)']] < Parameters[3]) * (data[i, 
                col_indx['Timestep (min)']] * Seconds_In_Minute)
        # 3- Calculate the energy withdrawn by the occupants using hot water:
        data[i, col_indx['Energy Withdrawn (J)']] = -data[i, col_indx['Hot Water Draw Volume (L)']] * \
            Density_Water * SpecificHeat_Water * (data[i, col_indx['Tank Temperature (deg C)']] - \
            data[i, col_indx['Inlet Water Temperature (deg C)']])
        # 4 - Calculate the energy added by the heat pump during the previous timestep
        
        data[i, col_indx['Energy Added Heat Pump (J)']] = (Parameters[4] * \
            int(data[i, col_indx['Tank Temperature (deg C)']] < (data[i, \
            col_indx['Set Temperature (deg C)']] - Parameters[6]) or data[i-1, \
            col_indx['Energy Added Heat Pump (J)']] > 0 and data[i, col_indx['Tank Temperature (deg C)']] \
            < data[i, col_indx['Set Temperature (deg C)']]) * (data[i, col_indx['Timestep (min)']] * \
            Seconds_In_Minute))
        # 5 - Calculate the energy change in the tank during the previous timestep
        data[i, col_indx['Total Energy Change (J)']] = data[i, col_indx['Jacket Losses (J)']] + \
            data[i, col_indx['Energy Withdrawn (J)']] + data[i, col_indx['Energy Added Backup (J)']] + \
            data[i, col_indx['Energy Added Heat Pump (J)']]        
#        data[i, col_indx['Electricity CO2 Multiplier (lb/kWh)']] = Parameters[10][data[i, col_indx['Hour of Year (hr)']]]
        # 6 - #Calculate the tank temperature during the final time step
        if i < len(data) - 1:
            data[i + 1, col_indx['Tank Temperature (deg C)']] = data[i, col_indx['Total Energy Change (J)']] / \
                Parameters[7] + data[i, col_indx['Tank Temperature (deg C)']]
            
    Model = pd.DataFrame(data=data[0:,0:],index=Model.index,columns=Model.columns) #convert Numpy Array back to a Dataframe to make it more user friendly
    
    Model['COP Adjust Tamb'] = Regression_COP_Derate_Tamb(Model['Tank Temperature (deg C)']) * \
        (Model['Ambient Temperature (deg C)'] - Parameters[11])
    Model['COP'] = Regression_COP(1.8 * Model['Tank Temperature (deg C)'] + 32) + Model['COP Adjust Tamb']
    Model['Electric Power (W)'] = np.where(Model['Timestep (min)'] > 0, (Model['Energy Added Heat Pump (J)']) / \
         (Model['Timestep (min)'] * Seconds_In_Minute), 0)/Model['COP'] + np.where(Model['Timestep (min)'] > 0, \
         Model['Energy Added Backup (J)']/(Model['Timestep (min)'] * Seconds_In_Minute), 0)
    Model['Electricity Consumed (kWh)'] = (Model['Electric Power (W)'] * Model['Timestep (min)']) / \
        (Watts_In_kiloWatt * Minutes_In_Hour)
    Model['Energy Added Total (J)'] = Model['Energy Added Heat Pump (J)'] + Model['Energy Added Backup (J)'] #Calculate the total energy added to the tank during this timestep
    
    return Model    