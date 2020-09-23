# -*- coding: utf-8 -*-
"""
Created on Tue Nov 19 09:51:40 2019

This module contains the a model of a HPWH with an external tank. It assumes that the thermostat on the tank fires when the water
near the bottom of the tank gets cold, and begins a pumping loop pushing the water through a heat pump. The water is withdrawn from
the bottom of the tank, user specified height, passed through the heat pump, COP calcualted based on the water temperature at the
bottom of the tank, and returned to the top of the tank, user-specified height.

Note that a lot of the above is more talking about future goals than about the current state. The currently available model uses
a mixed tank assumption, and is not yet capable of modeling the stratified tank needed for the above description.

This model does not include an electric resistance element. It assumes that the storage tanks do not contain them.

Currently this module holds only Model_HPWH_MixedTank, representing a 1-node model with a fully mixed tank. The plan is to later add additional functions
for different assumptions as needed, creating a library of relevant simulation models.

This model has now been modified to include an occupant behavior learning algorithm. As currently implemented it tracks the electricity consumption
of the HPWH during the full day, peak period, and off peak period. It gradually builds an understanding of how the water heater consumes electricity
enabling the development of load shifting controls tailored to each specific site. To use this algorithm the input data must have timesteps
at midnight (Not close to midnight, AT midnight)

Notes for when creating the full version of the model:
-Add new columns to the data frame representing the water temperature in each node of the tank. The code will look similar to the following

-for i in Nodes:
    Column_Name = 'Water Temperature, Node' + str(Nodes[i]) + ' (deg C)'
    Model[Column_Name] = 0

-The model can then use similar logic to reference the correct cells to calculate the temperature of the water in each node of the tank
-This naming convention can also be used to identify the temperature of water passed to the heat pump, and calculate the impacts of water returning to the heat pump
--The temperature of water passed to the heat pump is currently a placeholder, using the average tank temperature. It will need to be updated when we have a multi-node
    tank and an algorithm identifying the correct water temperature

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
#The following items are likely to be passed in as parameters. I envision dictionaries containing the parameters for specific HPWHs. Then the user selects a HPWH model, the script reads these parameters from the dictionary, passes it into the simulation model
Tank_Node_ToHeatPump = 1 #Node of the tank from which cold water is removed and delivered to the heat pump
Tank_Node_FromHeatPump = 1 #Node to which heated water is delivered by the heat pump
FlowRate_Volumetric_CirculationPump = 15.1416 #L/min, volumetric flow rate of the pump circulating water between the tank and the heat pump. Default value = 4 gal/min expressed in L/min

def Model_HPWH_MixedTank(Model, Parameters, Regression_COP):

    #The following two columns should be created in the wrapper calling this function when development has progressed that far
    Model['Temperature_Water_ToHeatPump (deg C)'] = 0 #The temperature of water passed from the tank to the heat pump
    Model['Temperature_Water_FromHeatPump (deg C)'] = 0 #The temperature of water returned from the heat pump to the tank
    
    data = Model.to_numpy() #convert the dataframe to a numpy array for EXTREME SPEED!!!! (numpy opperates in C)
    col_indx = dict(zip(Model.columns, list(range(0,len(Model.columns))))) #create a dictionary to provide column index references while using numpy in following loop
    
    for i  in range(1, len(data)): #Perform the modeling calculations for each row in the index
        # 1- Calculate the jacket losses through the walls of the tank in Btu:       
        data[i, col_indx['Jacket Losses (J)']] = -Parameters[0] * (data[i,col_indx['Tank Temperature (deg C)']] - data[i,col_indx['Ambient Temperature (deg C)']]) * (data[i, col_indx['Timestep (min)']] * Seconds_In_Minute)
        # 3- Calculate the energy withdrawn by the occupants using hot water:
        data[i, col_indx['Energy Withdrawn (J)']] = -data[i, col_indx['Hot Water Draw Volume (L)']] * Density_Water * SpecificHeat_Water * (data[i, col_indx['Tank Temperature (deg C)']] - data[i, col_indx['Inlet Water Temperature (deg C)']])
        # 4 - Calculate the energy added by the heat pump during the previous timestep
        
        if int(data[i, col_indx['Tank Temperature (deg C)']] < (data[i, col_indx['T_Setpoint_C']] - Parameters[6]) or data[i-1, col_indx['Energy Added Heat Pump (J)']] > 0 and data[i, col_indx['Tank Temperature (deg C)']] < data[i, col_indx['T_Setpoint_C']]):
            data[i, col_indx['Energy Added Heat Pump (J)']] = Parameters[4] * data[i, col_indx['Timestep (min)']] * Seconds_In_Minute
            data[i, col_indx['Temperature_Water_FromHeatPump (deg C)']] = Parameters[4] / (FlowRate_Volumetric_CirculationPump / Seconds_In_Minute * Density_Water * SpecificHeat_Water) + data[i, col_indx['Tank Temperature (deg C)']] #Uses Q_dot = m_dot * C_p * dT to identify the temperature of water leaving the heat pump and being returned to the storage tank. NOTE: THIS CURRENTLY USES THE AVERAGE TANK TEMPERATURE, INSTEAD OF THE COLD WATER AT THE BOTTOM OF THE TANK, AS A PLACEHOLDER
        else:
            data[i, col_indx['Energy Added Heat Pump (J)']] = 0 #Sets the energy added by the heat pump to 0 if the heat pump wasn't active/didn't add heat during the timestep
            data[i, col_indx['Temperature_Water_FromHeatPump (deg C)']] = 'N/A' #States that this value is not relevant if the heat pump was not active during the timestep. THIS MAY NOT BE THE BEST WAY TO HANDLE THIS ISSUE, AND PERHAPS IT'S BETTER TO SET IT TO A DUMMY VALUE. WE'LL SEE
        
        # 5 - Calculate the energy change in the tank during the previous timestep
        data[i, col_indx['Total Energy Change (J)']] = data[i, col_indx['Jacket Losses (J)']] + data[i, col_indx['Energy Withdrawn (J)']] + data[i, col_indx['Energy Added Backup (J)']] + data[i, col_indx['Energy Added Heat Pump (J)']]        
#        data[i, col_indx['Electricity CO2 Multiplier (lb/kWh)']] = Parameters[10][data[i, col_indx['Hour of Year (hr)']]]
        # 6 - #Calculate the tank temperature during the final time step
        #NOTE: THIS CODE WILL NEED TO CHANGE WHEN CREATING A MULTI-NODE MODEL
        if i < len(data) - 1:
            data[i + 1, col_indx['Tank Temperature (deg C)']] = data[i, col_indx['Total Energy Change (J)']] / Parameters[7] + data[i, col_indx['Tank Temperature (deg C)']]
            
    Model = pd.DataFrame(data=data[0:,0:],index=Model.index,columns=Model.columns) #convert Numpy Array back to a Dataframe to make it more user friendly
    
    Model['COP'] = Regression_COP(1.8 * Model['Tank Temperature (deg C)'] + 32)
    Model['Electric Power (W)'] = np.where(Model['Timestep (min)'] > 0, (Model['Energy Added Heat Pump (J)']) / (Model['Timestep (min)'] * Seconds_In_Minute), 0)/Model['COP'] + np.where(Model['Timestep (min)'] > 0, Model['Energy Added Backup (J)']/(Model['Timestep (min)'] * Seconds_In_Minute), 0)
    Model['Electricity Consumed (kWh)'] = (Model['Electric Power (W)'] * Model['Timestep (min)']) / (Watts_In_kiloWatt * Minutes_In_Hour)
    Model['Energy Added Total (J)'] = Model['Energy Added Heat Pump (J)'] + Model['Energy Added Backup (J)'] #Calculate the total energy added to the tank during this timestep
    
    return Model    