# -*- coding: utf-8 -*-
"""
Created on Mon Apr 01 12:53:33 2019

@author: pgrant
"""

#%%--------------------------IMPORT STATEMENTS--------------------------------

import pandas as pd
import numpy as np
from bokeh.plotting import figure, output_file, save, gridplot
from bokeh.models import LassoSelectTool, WheelZoomTool, BoxZoomTool, ResetTool
import os
import time
import HPWH_Model as HPWH
from linetimer import CodeTimer

#%%--------------------------HPWH PARAMETERS------------------------------

#These inputs are a series of constants describing the conditions of the simulation. Many of them are overwritten with measurements
#if Compare_To_MeasuredData = 1. The constants describing the gas HPWH itself come from communications with Alex of GTI, and may
#need to be updated if he sends new values
Temperature_Tank_Initial = 50.5 #deg C, initial temperature of water in the storage tank (120 F is the current default)
Temperature_Tank_Set = 50.5 #deg C, set temperature of the HPWH (120 F is the current default)
Temperature_Tank_Set_Deadband = 3.5 #deg C, deadband on the thermostat (20 F is the default)
Temperature_Water_Inlet = 4.4 #deg C, inlet water temperature in this simulation (40 F is the default)
Temperature_Ambient = 20 #deg C, temperature of the ambient air, placeholder for now, 68 F is the default
Volume_Tank = 290 #L, volume of water held in the storage tank, based on 72 gal rating at https://www.energystar.gov/productfinder/product/certified-water-heaters/details/2317252
Coefficient_JacketLoss = 2.8 #W/K, Adjusted to match monitored data
Power_Backup = 3800 #W, electricity consumption of the backup resistance elements
Threshold_Activation_Backup = 15 #deg C, backup element operates when tank temperature is this far below the set temperature. This parameter operates as a deadband. Note that this operate at the same time as the heat pump (100 F is the default)
Threshold_Deactivation_Backup = Temperature_Tank_Set #Deg C, sets the temperature when the backup element disengages after it has been engaged (115 F is the default)
HeatAddition_HeatPump = 1230.9 #W, heat consumed by the heat pump
ElectricityConsumption_Active = 158.5 #W, electricity consumed by the fan when the heat pump is running
ElectricityConsumption_Idle = 18 #W, electricity consumed by the HPWH when idle
CO2_Output_Electricity = 0.212115 #ton/MWh, CO2 production when the HPWH consumes electricity. Default value is the average used in California
Coefficient_2ndOrder_COP = 0 #The 2nd order coefficient in the COP equation
Coefficient_1stOrder_COP = -0.037 #The 1st order coefficient in the COP equation
Constant_COP = 7.67 #The constant in the COP equation
Temperature_MixingValve_Set = 48.9 #deg C, set temperature of the mixing valve

#%%--------------------------INPUTS-------------------------------------------

#This first variable provides the path to the data set itself. This means you should fill in the path with the specific location 
#of your data file. Note that this works best if the file is on your hard drive, not a shared network drive
Path_DrawProfile = r'C:\Users\Peter Grant\Dropbox (Beyond Efficiency)\Peter\Python Scripts\HPWH_Python\Data\MonitoredData\3CFA_LoadShifting_Aug2020' + os.sep +  'Aug20_To_Aug26.csv'
Filename_Start = -18
Filename_End = -4
Filename = Path_DrawProfile[Filename_Start:Filename_End]

Variable_Set_Temperature = 1 #Set this =1 if using a varying set temperature for the water heater, or =0 if using a static set temperature for the water heater

#Set this = 1 if you want to compare model predictions to measured data results. This is useful for model validation and error
#checking. If you want to only input the draw profile and see what the data predicts, set this = 0. Note that =1 mode causes the
#calculations to take much longer
Compare_To_MeasuredData = 1

#Time filetering inputs. Use these if you want to look at a specified portion of the data set
Time_Filtering = 0 #Tells the program that time filtering is active
Start_Time = 35 #Hours
End_Time = 90 #Hours

#%%---------------CONSTANT DECLARATIONS AND CALCULATIONS-----------------------
#Constants used in water-based calculations
SpecificHeat_Water = 4.190 #J/g-C
Density_Water = 1000 #g/L

#Constants used for unit conversions
Hours_In_Day = 24 #The number of hours in a day
Minutes_In_Hour = 60 #The number of minutes in an hour
Seconds_In_Minute = 60 #The number of seconds in a minute
W_To_BtuPerHour = 3.412142 #Converting from Watts to Btu/hr
K_To_F_MagnitudeOnly = 1.8/1. #Converting from K/C to F. Only applicable for magnitudes, not actual temperatures (E.g. Yes for "A temperature difference of 10 C" but not for "The water temperature is 40 C")
Btu_Per_CubicFoot_NaturalGas = 1015 #Energy density of natural gas, in Btu/ft^3
Btu_Per_WattHour = 3.412142 #Conversion factor between Btu nad W-h
Btu_In_Therm = 100000 #The number of Btus in a therm
Pounds_In_MetricTon = 2204.62 #Pounds in a metric ton
Pounds_In_Ton = 2000 #Pounds in a US ton
kWh_In_MWh = 1000 #kWh in MWh
Liters_In_Gallon = 3.78541 #The number of liters in a gallon

#Calculating the CO2 produced per kWh of electricity consumed
CO_Production_Rate_Electricity = CO2_Output_Electricity * Pounds_In_Ton * kWh_In_MWh

#This section commented out b/c keeping HPWH model is SI as much as possible
#Converting quantities from SI units provided by Alex to (Incorrect, silly, obnoxious) IP units
#Coefficient_JacketLoss = Coefficient_JacketLoss * W_To_BtuPerHour * K_To_F_MagnitudeOnly #Converts Coefficient_JacketLoss from W/K to Btu/hr-F
#Power_Backup = Power_Backup * W_To_BtuPerHour #Btu/hr
#ElectricityConsumption_HeatPump = ElectricityConsumption_HeatPump * W_To_BtuPerHour #Btu/hr

#Calculating the thermal mass of the water in the storage tank
ThermalMass_Tank = Volume_Tank * Density_Water * SpecificHeat_Water

#Stores the parameters in a list for use in the modelParameters = [Coefficient_JacketLoss, Power_Backup, Threshold_Activation_Backup, Threshold_Deactivation_Backup, FiringRate_HeatPump, Temperature_Tank_Set, Temperature_Tank_Set_Deadband, ThermalMass_Tank, ElectricityConsumption_Active, ElectricityConsumption_Idle, NOx_Production_Rate]
Parameters = [Coefficient_JacketLoss, #0
                Power_Backup, #1
                Threshold_Activation_Backup, #2
                Threshold_Deactivation_Backup, #3
                HeatAddition_HeatPump, #4
                Temperature_Tank_Set, #5
                Temperature_Tank_Set_Deadband, #6
                ThermalMass_Tank, #7
                ElectricityConsumption_Active, #8
                ElectricityConsumption_Idle, #9
                CO_Production_Rate_Electricity] #10

#%%--------------------------MODELING-----------------------------------------

#Creates a 1 dimensional regression stating the COP of the gas heat pump as a function of the temperature of water in the tank
Coefficients_COP = [Coefficient_2ndOrder_COP, Coefficient_1stOrder_COP, Constant_COP] #combines the coefficient and the constant into an array
Regression_COP = np.poly1d(Coefficients_COP) #Creates a 1-d linear regression stating the COP of the heat pump as a function of the temperature of water in the tank

#This section of the code creates a data frame that can be used to represent the simulation model
#The first step is putting the draw profile data into the right format (E.g. If it's CBECC data, we need to convert from event-based to timestep-based)
#The following if-statement takes care of this for 2 different data formats

Start_ProfileCreation = time.time()

Draw_Profile = pd.read_csv(Path_DrawProfile) #Reads the input data, setting the first row (measurement name) of the .csv file as the header

Model = Draw_Profile[['Timestamp', 'Time (s)', 'Time (min)', 'Power_PowerSum_W', 'Power_EnergySum_kWh', 'Water_FlowRate_gpm', 'Water_FlowTotal_gal', 'Water_FlowTemp_F', 'Water_RemoteTemp_F', 'T_Setpoint_F', 'T_Ambient_EcoNet_F', 'T_Cabinet_F', 'T_TankUpper_F', 'T_TankLower_F']].copy() #Creates a new dataframe with the same index as DrawProfile, keeping only the needed columns. NOTE: THIS CURRENTLY DOES NOT KEEP ALL NEEDED COLUMNS. WILL NEED TO MODIFY TO INCLUDE INLET TEMPERATURE, CLOSET AIR TEMPERATURE, CLOSET RELATIVE HUMIDITY WHEN THOSE COLUMNS ARE AVILABLE AND IDENTIFIED
Model = Model.fillna(method='ffill')
Model = Model.fillna(method='bfill')
#Model = Model.drop([0, 1])
#Model['T_TankUpper_F'] = 125
#Model['T_TankLower_F'] = 125

Model['Time (hr)'] = Model['Time (min)'] / Minutes_In_Hour

#This filter is ONLY for working with Creekside, 3FCA data. Comment out and/or delete as needed
if Time_Filtering == 1:
    Model = Model[Model['Time (hr)'] > Start_Time]
    Model = Model[Model['Time (hr)'] < End_Time]

Model['Time shifted (min)'] = Model['Time (min)'].shift(1)
Model['Time shifted (min)'].iloc[0] = Model['Time (min)'].iloc[0]
Model['Timestep (min)'] =  Model['Time (min)'] - Model['Time shifted (min)']
Model = Model[Model['Timestep (min)'] != 0]
Model = Model.reset_index() #Do not delete this when removing the Creekside, 3FCA filter
del Model['index'] #Do not delete this when removing the Creekside, 3FCA filter

Model['Water_FlowRate_LPerMin'] = Model['Water_FlowRate_gpm'] * Liters_In_Gallon
Model['Water_FlowTotal_L'] = Model['Water_FlowTotal_gal'] * Liters_In_Gallon
Model['Water_FlowTemp_C'] = (Model['Water_FlowTemp_F']-32) * 1/K_To_F_MagnitudeOnly
Model['Water_RemoteTemp_C'] = (Model['Water_RemoteTemp_F']-32) * 1/K_To_F_MagnitudeOnly
Model['T_Setpoint_C'] = (Model['T_Setpoint_F']-32) * 1/K_To_F_MagnitudeOnly #Create a column in the model representing the user-supplied, possibly varying, set temperature in deg C. If Variable_Set_Temperature == 1 this will be the set temperature used in the model
Model['Power_EnergySum_kWh'] = Model['Power_EnergySum_kWh'] - Model.loc[0, 'Power_EnergySum_kWh']
Model['T_Ambient_EcoNet_C'] = (Model['T_Ambient_EcoNet_F']-32) * 1/K_To_F_MagnitudeOnly
Model['T_Cabinet_C'] = (Model['T_Cabinet_F']-32) * 1/K_To_F_MagnitudeOnly
Model['T_Tank_Upper_C'] = (Model['T_TankUpper_F']-32) * 1/K_To_F_MagnitudeOnly
Model['T_Tank_Lower_C'] = (Model['T_TankLower_F']-32) * 1/K_To_F_MagnitudeOnly

if Variable_Set_Temperature == 0: #If the user has opted to use a static set temperature
    Model['T_Setpoint_C'] = Temperature_Tank_Set #Make the set temperature at all times equal the static set temperature specified by the user

Model['T_Activation_Backup_C'] = Model['T_Setpoint_C'] - Threshold_Activation_Backup


#This commented code is from the GTI gas HPWH model. It is currently stored here for reference, in case it's needed, and will likely be deleted shortly
#Draw_Profile['ELAPSED TIME'] = Draw_Profile['ELAPSED TIME'].astype(float) #Converts string data to float so the numbers can be used in calculations
#Draw_Profile['Water Flow'] = Draw_Profile['Water Flow'].astype(float) #Converts string data to float so the numbers can be used in calculations
#Draw_Profile['TIME'] = pd.to_datetime(Draw_Profile['TIME']) #Converts string data to time data so the numbers can be used in calculations
#Draw_Profile['Gas Meter'] = Draw_Profile['Gas Meter'].astype(float) #Converts string data to float so the numbers can be used in calculations
#Draw_Profile['Power Draw'] = Draw_Profile['Power Draw'].astype(float) #Converts string data to float so the numbers can be used in calculations
#Draw_Profile['Mid Tank'] = Draw_Profile['Mid Tank'].astype(float) #Converts string data to float so the numbers can be used in calculations
#
#values = {'Water Flow': 0, 'Power Draw': 0} #These two lines set all "nan" entries in Water Flow to 0. This is needed to avoid errors when the data logger resets
#Draw_Profile = Draw_Profile.fillna(value = values)
#
#if Draw_Profile['ELAPSED TIME'].min() == 0.0: #ELAPSED TIME = 0 when the data logger resets. This code only executes if the data logger reset during the monitoring perio
#    Index_Reset = Draw_Profile.loc[Draw_Profile['ELAPSED TIME'] == 0.0].index.item() #Identifies the row in the table when the data logger reset
#    for i in range(Index_Reset, len(Draw_Profile.index)): #This for loop updates all entries after the data logger reset with new values, as if the data logger had not resest
#        Draw_Profile.loc[i, 'ELAPSED TIME'] = Draw_Profile.loc[i-1, 'ELAPSED TIME'] + (Draw_Profile.loc[i, 'TIME'] - Draw_Profile.loc[i - 1, 'TIME']).seconds #Calculates the actual time since the monitoring data started by adding the time delta to the previous value
#        if i == Index_Reset: #Execute this code only for the row that matches the time the datalogger reset
#            Delta_Next = Draw_Profile.loc[i + 1, 'Water Flow'] #Identfy the cumulative water flow as of the next entry
#            Draw_Profile.loc[i, 'Water Flow'] = Draw_Profile.loc[i-1, 'Water Flow'] #Sets the water flow in this row equal to the water flow in the previous row
#        else: #If it's an index other than the one where the dataloffer reset
#            Delta = Delta_Next #Update the delta value with the previously recorded delta_next value. This will be used to identify the amount of cumulative water flow as of the end of this timestep
#            if i < len(Draw_Profile.index) - 1: #Only do this if it's NOT the last row in the model. Because doing that would cause errors. The computer would overheat, which would ignite the oils on the keyboard from typing, which would burn the air in the office and kill everybody. Then you'd have to file a safety incident report. Sad face :-(
#                Delta_Next = Draw_Profile.loc[i + 1, 'Water Flow'] - Draw_Profile.loc[i, 'Water Flow'] #Identify the increase in cumulative water flow between the current timestep and the next one
#            Draw_Profile.loc[i, 'Water Flow'] = Draw_Profile.loc[i - 1, 'Water Flow'] + Delta #Set the cumulative water flow of this timestep equal to the cumulative water flow of the previous timestep + the previously identified delta
#
#if Draw_Profile['Power Draw'].min() == 0.0:
#    Index_Reset = Draw_Profile['Power Draw'].idxmin()
#    Draw_Profile[Index_Reset:-1]['Power Draw'] = Draw_Profile[Index_Reset:-1]['Power Draw'] + Draw_Profile.loc[Index_Reset - 1, 'Power Draw']
#    Draw_Profile['Power Draw'].iloc[-1] = Draw_Profile['Power Draw'].iloc[-1] + Draw_Profile.loc[Index_Reset - 1, 'Power Draw']
#
#Model['Time (min)'] = (Draw_Profile['ELAPSED TIME'] - Draw_Profile.loc[0, 'ELAPSED TIME'])/60. #Calculate the elapsed time in minutes, instead of seconds, and add it to the
#Model['Water Flow'] = Draw_Profile['Water Flow'] #Adds a column to Model containing the water flow information from the measured data
#Temperature_Tank_Initial = float(Draw_Profile.loc[0, 'Mid Tank']) #Sets the initial temperature of the modeled tank equal to the initial measured temperature
#Model['Hot Water Draw Volume (gal)'] = 0 #Sets the draw volume during the first timestep in the model to 0. Will be overwritten later if needed
#for i in Draw_Profile.index: #This section calculates the hot water flow during each timestep and adds it to the modeling dataframe
#    if i > 0: #This code references the previous timestep, so don't do it on the first timestep. Because that's a terrible idea
#        Model.loc[i, 'Hot Water Draw Volume (gal)'] = Draw_Profile.loc[i, 'Water Flow'] - Draw_Profile.loc[i-1, 'Water Flow'] #Find the delta between the cumulative water flow identified in the current and previous timesteps, then enter that value in the current row
#    elif i == 0: #For the very first row
#        Model.loc[i, 'Hot Water Draw Volume (gal)'] = 0 #Set it equal to 0. Because there's no previous timestep to calculate from
#
#Model['Ambient Temperature (deg F)'] = Draw_Profile['Indoor Temp'].astype(float) #Converts data frm string to float so it can be used in calculations
#Model['Inlet Water Temperature (deg F)'] = Draw_Profile['Water In Temp'].astype(float) #Converts data frm string to float so it can be used in calculations
#
#End_ProfileCreation = time.time()

#print('Profile creation time is ' + str(End_ProfileCreation - Start_ProfileCreation))

#The following code simulates the performance of the gas HPWH across different draw profiles
#Initializes a bunch of values at either 0 or initial temperature. They will be overwritten later as needed

Simulation_Start = time.time()

Model['Tank Temperature (deg C)'] = 0
Model.loc[0, 'Tank Temperature (deg C)'] = Temperature_Tank_Initial
Model.loc[1, 'Tank Temperature (deg C)'] = Temperature_Tank_Initial
Model['Jacket Losses (J)'] = 0
Model['Energy Withdrawn (J)'] = 0
Model['Energy Added Backup (J)'] = 0
Model['Energy Added Heat Pump (J)'] = 0
Model['Energy Added Total (J)'] = 0
Model['COP'] = 0
Model['Total Energy Change (J)'] = 0
Model['Ambient Temperature (deg C)'] = Model['T_Cabinet_C'] #Sets ambient temperature in the simulation model equal to the monitored temperature in the cabinet
Model['Inlet Water Temperature (deg C)'] = Model['Water_RemoteTemp_C'] #Set the inlet water temperature in the model equal to the monitored inlet water temperature
#Model['Water_FlowTotal_Hot_L'] = (Model['Water_FlowTotal_L'] * Model['Water_RemoteTemp_C'] - Model['Water_FlowTotal_L'] * Model['Water_FlowTemp_C']) / (Model['Water_FlowTemp_C'] - Temperature_Tank_Set)

Model['Water_FlowTotal_L shifted'] = Model['Water_FlowTotal_L'].shift(1)
Model['Water_FlowTotal_L shifted'].iloc[0] = Model['Water_FlowTotal_L'].iloc[0]
Model['Water Draw Volume (L)'] =  Model['Water_FlowTotal_L'] - Model['Water_FlowTotal_L shifted']
Model['Hot Water Draw Volume (L)'] = (Model['Water Draw Volume (L)'] * Model['Water_RemoteTemp_C'] - Model['Water Draw Volume (L)'] * Temperature_MixingValve_Set) / (Model['Water_RemoteTemp_C'] - Model['T_Tank_Upper_C'])

Model = HPWH.Model_HPWH_MixedTank(Model, Parameters, Regression_COP)

Simulation_End = time.time()

print ('Simulation time is ' + str(Simulation_End - Simulation_Start))

Model.to_csv(os.path.dirname(__file__) + os.sep + 'Output' + os.sep + 'Output_' + Filename + '.csv', index = False) #Save the model too the declared file. This should probably be replaced with a dynamic file name for later use in parametric simulations

#%%--------------------------MODEL COMPARISON-----------------------------------------

#This code is only run when comparing the model results to field measurements. It is typically used for model validation
if Compare_To_MeasuredData == 1:
  
    Model['Total Electricity Consumption (kWh)'] = Model['Electricity Consumed (kWh)'].cumsum()
    Model['Cumulative Percent Error (%)'] = (Model['Total Electricity Consumption (kWh)'] - Model['Power_EnergySum_kWh']) / (Model['Power_EnergySum_kWh'] + 0.000000000001) * 100
    
    tools = [LassoSelectTool(), WheelZoomTool(), BoxZoomTool(), ResetTool()]    
    
    p1 = figure(width=1200, height= 600, x_axis_label='Time (hr)', y_axis_label = 'Electric Power (W)', tools = tools)
    p1.title.text_font_size = '12pt'
    p1.line(x = Model['Time (hr)'], y = Model['Electric Power (W)'], legend = 'Model', color = 'red')
    p1.circle(x = Model['Time (hr)'], y = Model['Power_PowerSum_W'], legend = 'Data', color = 'blue')   
    p1.circle(x = Model['Time (hr)'], y = Model['T_Setpoint_F'], legend = 'Set Temperature', color = 'orange')
    p1.legend.label_text_font_size = '18pt'
    p1.legend.location = 'bottom_right'
    p1.xaxis.axis_label_text_font_size = '18pt'
    p1.yaxis.axis_label_text_font_size = '18pt'
    p1.xaxis.major_label_text_font_size = '12pt'
    p1.yaxis.major_label_text_font_size = '12pt'

    p2 = figure(width=1200, height= 600, x_axis_label='Time (hr)', y_axis_label = 'Cumulative Electricity Consumption (kWh)', tools = tools)
    p2.title.text_font_size = '12pt'
    p2.line(x = Model['Time (hr)'], y = Model['Total Electricity Consumption (kWh)'], legend = 'Model', color = 'red')
    p2.circle(x = Model['Time (hr)'], y = Model['Power_EnergySum_kWh'], legend = 'Data', color = 'blue')    

    p3 = figure(width=1200, height= 600, x_axis_label='Time (hr)', y_axis_label = 'Water Temperature (deg C)', tools = tools)
    p3.title.text_font_size = '12pt'
    p3.line(x = Model['Time (hr)'], y = Model['Tank Temperature (deg C)'], legend = 'Model, Tank Average', color = 'red')
    p3.circle(x = Model['Time (hr)'], y = Model['T_Tank_Upper_C'], legend = 'Data, Upper', color = 'blue') 
    p3.circle(x = Model['Time (hr)'], y = Model['T_Tank_Lower_C'], legend = 'Data, Lower', color = 'purple') 
    p3.circle(x = Model['Time (hr)'], y = Model['T_Setpoint_C'], legend = 'Set Temperature', color = 'orange')
    p3.legend.label_text_font_size = '18pt'
    p3.legend.location = 'bottom_right'
    p3.xaxis.axis_label_text_font_size = '18pt'
    p3.yaxis.axis_label_text_font_size = '18pt'
    p3.xaxis.major_label_text_font_size = '12pt'
    p3.yaxis.major_label_text_font_size = '12pt'    

    p4 = figure(width=1200, height= 600, x_axis_label='Time (hr)', y_axis_label = 'Cumulative Water Consumption (L)', tools = tools)
    p4.title.text_font_size = '12pt'
    p4.circle(x = Model['Time (hr)'], y = Model['Water_FlowTotal_L'], legend = 'Water', color = 'blue') 

    p5 = figure(width=1200, height= 600, x_axis_label='Time (hr)', y_axis_label = 'Water Consumption Each Timestep (L)', tools = tools)
    p5.title.text_font_size = '12pt'
    p5.circle(x = Model['Time (hr)'], y = Model['Water Draw Volume (L)'], legend = 'From MV', color = 'blue') 
    p5.circle(x = Model['Time (hr)'], y = Model['Hot Water Draw Volume (L)'], legend = 'From WH - Calculated', color = 'red') 

    p6 = figure(width=1200, height= 600, x_axis_label='Time (hr)', y_axis_label = 'Water Temperatures (deg C)', tools = tools)
    p6.title.text_font_size = '12pt'
    p6.circle(x = Model['Time (hr)'], y = Model['T_Tank_Upper_C'], legend = 'T_Tank_Upper_C', color = 'red') 
    p6.circle(x = Model['Time (hr)'], y = Model['Water_FlowTemp_C'], legend = 'Water_FlowTemp_C', color = 'purple') 
    p6.circle(x = Model['Time (hr)'], y = Model['Water_RemoteTemp_C'], legend = 'Water_RemoteTemp_C', color = 'blue') 

    p7 = figure(width=1200, height= 600, x_axis_label='Time (hr)', y_axis_label = 'Monitored Ambient Temperature (deg C)', tools = tools)
    p7.title.text_font_size = '12pt'
    p7.circle(x = Model['Time (hr)'], y = Model['T_Cabinet_C'], legend = 'T_Cabinet_C', color = 'blue') 
    p7.circle(x = Model['Time (hr)'], y = Model['T_Ambient_EcoNet_C'], legend = 'T_Ambient_EcoNet_C', color = 'red') 

    p8 = figure(width=1200, height= 600, x_axis_label='Time (hr)', y_axis_label = 'Error in Electricity Consumption (%)', tools = tools)
    p8.title.text_font_size = '12pt'
    p8.circle(x = Model['Time (hr)'], y = Model['Cumulative Percent Error (%)'], legend = 'Error', color = 'black') 

    p = gridplot([[p1],[p2],[p3],[p4],[p5],[p6],[p7], [p8]])
    if Time_Filtering == 0:
        output_file(os.path.dirname(__file__) + os.sep + 'Validation Data\Validation Plots_' + Filename + '.html', title = 'Validation Data')
    elif Time_Filtering == 1:
        output_file(os.path.dirname(__file__) + os.sep + 'Validation Data\Validation Plots_' + Filename + '_Start=' + str(Start_Time) + '_End=' + str(End_Time) + '.html', title = 'Validation Data')
    save(p)
    
#This code is from the GTI gas HPWH simulation model validation process. It is still here for reference, in case it's useful. It's likely to be deleted later    
#    Compare_To_MeasuredData = Model.copy() #Creates a new dataframe specifically for comparing model results to measured data. Starts with the same index and data as the model results, then adds data and calculations from the measured data as necessary
#
#    Compare_To_MeasuredData['Hot Water Draw Volume, Model (gal)'] = Compare_To_MeasuredData['Hot Water Draw Volume (gal)'].cumsum() #Creates a new column in the data frame that cumulatively sums the hot water draw volume in the simulation model. This is then compared to the measured data to ensure that the two are the same
#    Compare_To_MeasuredData['Cumulative Hot Water Draw Volume, Data (gal)'] = Draw_Profile['Water Flow'] - Draw_Profile.loc[0, 'Water Flow'] #Creates a new column that represents the cumulative hot water draw volume in the data. The data does not start at 0 gal, so this column subtracts the first value from all values in the column to treat it as if it did start at 0
#    Compare_To_MeasuredData['Ambient Temperature, Data (deg F)'] = Draw_Profile['Indoor Temp'] #Creates a new column in the datframe storing the ambient temperature from the measured data
#    Compare_To_MeasuredData['Inlet Water Temperature, Data (deg F)'] = Draw_Profile['Water In Temp'] #Creates a new column in the data frame representing the measured inlet water temperature
#    Compare_To_MeasuredData['Tank Temperature, Data (deg F)'] = Draw_Profile['Mid Tank'] #Creates a new column in the data frame representing the measured temperature at the middle height of the tank
#    Compare_To_MeasuredData['COP, Data'] = Regression_COP(Draw_Profile['Mid Tank']) #Creates a new column in the data frame calculating the COP of the HPWH based on the measured tank water temperature
#
#    Compare_To_MeasuredData['Energy Added, Data (Btu)'] = 0 #Creates a new column for energy added in each timestep with a default value of 0. This value will later be overwritten when the correct value for each timestep is calculated
#    
#    Compare_To_MeasuredData['Energy Added Heat Pump, Model (Btu)'] = Model['Energy Added Heat Pump (Btu)']
#
#    Compare_To_MeasuredData['Electricity Consumed, Model (W-h)'] = Model['Electric Usage (W-hrs)'].cumsum()
#
#    for i in range(1, len(Compare_To_MeasuredData)):
#        Compare_To_MeasuredData.loc[i, 'Energy Added, Data (Btu)'] = Btu_Per_CubicFoot_NaturalGas * Compare_To_MeasuredData.loc[i, 'COP, Data'] * (Draw_Profile.loc[i, 'Gas Meter'] - Draw_Profile.loc[i-1, 'Gas Meter']) + Btu_Per_WattHour * (Draw_Profile.loc[i, 'Power Draw'] - Draw_Profile.loc[i-1, 'Power Draw']) #Calculates the energy added to the water during each timestep in the measured data
#        Compare_To_MeasuredData.loc[i, 'Energy Added Heat Pump, Data (Btu)'] = Btu_Per_CubicFoot_NaturalGas * Compare_To_MeasuredData.loc[i, 'COP, Data'] * (Draw_Profile.loc[i, 'Gas Meter'] - Draw_Profile.loc[i-1, 'Gas Meter']) #Calculates the energy added to the water by the heat pump during each time step in the measured data
#        Compare_To_MeasuredData.loc[i, 'Energy Added Heat Pump, Data (Btu/min)'] = Btu_Per_CubicFoot_NaturalGas * Compare_To_MeasuredData.loc[i, 'COP, Data'] * (Draw_Profile.loc[i, 'Gas Meter'] - Draw_Profile.loc[i-1, 'Gas Meter']) / (Compare_To_MeasuredData.loc[i, 'Time (min)'] - Compare_To_MeasuredData.loc[i-1, 'Time (min)']) #Calculates the rate of energy added to the heat pump during each timestep in the measured data
#        Compare_To_MeasuredData.loc[i, 'Timestep (min)'] = Compare_To_MeasuredData.loc[i, 'Time (min)'] - Compare_To_MeasuredData.loc[i-1, 'Time (min)']
#        Model.loc[i, 'Timestep (min)'] = Model.loc[i, 'Time (min)'] - Model.loc[i-1, 'Time (min)']
#
#    Compare_To_MeasuredData['Gas Consumption, Cumulative, Data (Btu)'] = Compare_To_MeasuredData['Energy Added Heat Pump, Data (Btu)'].cumsum() #Provides a cumulative summation of the monitored gas consumption data for validation purposes
#    Compare_To_MeasuredData['Gas Consumption, Cumulative, Simulation (Btu)'] = Compare_To_MeasuredData['Energy Added Heat Pump, Model (Btu)'].cumsum() #Provides a cumulative summation of the simulated gas consumption for validation purposes
#
#    #Generates a series of plots that can be used for comparing the model results to the measured data
#
#    tools = [LassoSelectTool(), WheelZoomTool(), BoxZoomTool(), ResetTool()]
#
#    p1 = figure(width=800, height= 400, x_axis_label='Time (min)', y_axis_label = 'Cumulative Hot Water Draw Volume (gal)', tools = tools)
#    p1.title.text_font_size = '12pt'
#    p1.line(x = Compare_To_MeasuredData['Time (min)'], y = Compare_To_MeasuredData['Hot Water Draw Volume, Model (gal)'], legend = 'Model', color = 'red')
#    p1.circle(x = Compare_To_MeasuredData['Time (min)'], y = Compare_To_MeasuredData['Cumulative Hot Water Draw Volume, Data (gal)'], legend = 'Data', color = 'blue')
#
#    p2 = figure(width=800, height= 400, x_axis_label='Time (min)', y_axis_label = 'Ambient Temperature (deg F)')
#    p2.title.text_font_size = '12pt'
#    p2.line(x = Compare_To_MeasuredData['Time (min)'], y = Compare_To_MeasuredData['Ambient Temperature (deg F)'], legend = 'Model', color = 'red')
#    p2.circle(x = Compare_To_MeasuredData['Time (min)'], y = Compare_To_MeasuredData['Ambient Temperature, Data (deg F)'], legend = 'Data', color = 'blue')
#
#    p3 = figure(width=800, height= 400, x_axis_label='Time (min)', y_axis_label = 'Inlet Temperature (deg F)')
#    p3.title.text_font_size = '12pt'
#    p3.line(x = Compare_To_MeasuredData['Time (min)'], y = Compare_To_MeasuredData['Inlet Water Temperature (deg F)'], legend = 'Model', color = 'red')
#    p3.circle(x = Compare_To_MeasuredData['Time (min)'], y = Compare_To_MeasuredData['Inlet Water Temperature, Data (deg F)'], legend = 'Data', color = 'blue')
#
#    p4 = figure(width=800, height= 400, x_axis_label='Time (min)', y_axis_label = 'Tank Temperature (deg F)')
#    p4.title.text_font_size = '12pt'
#    p4.line(x = Compare_To_MeasuredData['Time (min)'], y = Compare_To_MeasuredData['Tank Temperature (deg F)'], legend = 'Model', color = 'red')
#    p4.circle(x = Compare_To_MeasuredData['Time (min)'], y = Compare_To_MeasuredData['Tank Temperature, Data (deg F)'], legend = 'Data', color = 'blue')
#
#    p5 = figure(width=800, height= 400, x_axis_label='Time (min)', y_axis_label = 'Energy Added (Btu)')
#    p5.title.text_font_size = '12pt'
#    p5.line(x = Compare_To_MeasuredData['Time (min)'], y = Model['Energy Added Total (Btu)'], legend = 'Model', color = 'red')
#    p5.circle(x = Compare_To_MeasuredData['Time (min)'], y = Compare_To_MeasuredData['Energy Added, Data (Btu)'], legend = 'Data', color = 'blue')
#
#    p6 = figure(width=800, height= 400, x_axis_label='Time (min)', y_axis_label = 'COP')
#    p6.title.text_font_size = '12pt'
#    p6.line(x = Compare_To_MeasuredData['Time (min)'], y = Compare_To_MeasuredData['COP Gas'], legend = 'Model', color = 'red')
#    p6.circle(x = Compare_To_MeasuredData['Time (min)'], y = Compare_To_MeasuredData['COP, Data'], legend = 'Data', color = 'blue')
#
#    p7 = figure(width=800, height= 400, x_axis_label='Time (min)', y_axis_label = 'Energy Added Heat Pump (Btu)')
#    p7.title.text_font_size = '12pt'
#    p7.line(x = Compare_To_MeasuredData['Time (min)'], y = Compare_To_MeasuredData['Energy Added Heat Pump, Model (Btu)'], legend = 'Model', color = 'red')
#    p7.circle(x = Compare_To_MeasuredData['Time (min)'], y = Compare_To_MeasuredData['Energy Added Heat Pump, Data (Btu)'], legend = 'Data', color = 'blue')
#
#    p8 = figure(width=800, height= 400, x_axis_label='Time (min)', y_axis_label = 'Electricity Consumed (W-h)')
#    p8.title.text_font_size = '12pt'
#    p8.line(x = Compare_To_MeasuredData['Time (min)'], y = Compare_To_MeasuredData['Electricity Consumed, Model (W-h)'], legend = 'Model', color = 'red')
#    p8.circle(x = Compare_To_MeasuredData['Time (min)'], y = Draw_Profile['Power Draw'] - Draw_Profile['Power Draw'].iloc[0], legend = 'Data', color = 'blue')
#    p8.legend.location = 'bottom_right'
#
#    p9 = figure(width=800, height= 400, x_axis_label='Time (min)', y_axis_label = 'Natural Gas Consumed (Btu)')
#    p9.title.text_font_size = '12pt'
#    p9.line(x = Compare_To_MeasuredData['Time (min)'], y = Compare_To_MeasuredData['Gas Consumption, Cumulative, Simulation (Btu)'], legend = 'Model', color = 'red')
#    p9.circle(x = Compare_To_MeasuredData['Time (min)'], y = Compare_To_MeasuredData['Gas Consumption, Cumulative, Data (Btu)'], legend = 'Data', color = 'blue')
#    p9.legend.location = 'bottom_right'
#
#    p = gridplot([[p1],[p2], [p3], [p4], [p5], [p6], [p7], [p8], [p9]])
#    output_file(os.path.dirname(__file__) + os.sep + 'Validation Data\Validation Plots.html', title = 'Validation Data')
#    save(p)
#
#    ElectricityConsumption_Data = Draw_Profile['Power Draw'].iloc[-2] - Draw_Profile.loc[0, 'Power Draw']
#
#    PercentError_Gas = (Compare_To_MeasuredData['Energy Added Heat Pump, Model (Btu)'].sum() - Compare_To_MeasuredData['Energy Added Heat Pump, Data (Btu)'].sum()) / Compare_To_MeasuredData['Energy Added, Data (Btu)'].sum() * 100
#    PercentError_COP = (Compare_To_MeasuredData['COP Gas'].mean() - Compare_To_MeasuredData['COP, Data'].mean()) / Compare_To_MeasuredData['COP, Data'].mean() * 100
#    PercentError_Electricity = (Compare_To_MeasuredData['Electricity Consumed, Model (W-h)'].iloc[-1] - ElectricityConsumption_Data) / ElectricityConsumption_Data * 100
