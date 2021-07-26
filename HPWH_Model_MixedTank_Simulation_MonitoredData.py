# -*- coding: utf-8 -*-
"""
Created on Mon Apr 01 12:53:33 2019

This model is a wrapper providing input and outpur cofe for HPWHP_Model.py
HPWH_Model.py contains the code that simulates the heat transfer, control 
logic, and performance of a single family residential electric HPWH. That
script contains only the code describing a generic HPWH, and a wrapper script
that defines the HPWH, provides input data, and processes the output data is
necessary to operate it. This code provides that wrapper for analyzing the
monitored data collected in the Creekside project. It performs the following:
    
    1. Set the parameters as identified during calibration to match the Rheem 
    PROPH80 HPWHs installed at Creekside (See "HPWH PARAMETERS" section)
    2. Read the .csv file representing a specific Creekside data set, filter
    the data as needed (Minimal, but the code to do more exists) and set some
    logic conditions based on the available data (See "INPUTS")
    3. Defines constants, performs unit conversions, and sets parameters for
    input into HPWH_Model.py (See "CONSTANT DECLARATIONS AND CALCULATIONS")
    4. Formats the data for modeling and creates the dataframe necessary for
    the model. This includes creating a data frame with the necessary time
    steps for the model, filling in blank cells in the monitored data set, 
    setting initial conditions for modeled values (E.g. temperature of water
    in the tank), and passing the data to HPWH_Python.py for analysis.
    5. Plots the data as specified by the user. Note that there are no flags to
    select which plots need to be generated; instead the user must add the code
    for new plots as needed for a given project.

This model has one specific implementation that was necessary for the project
but should not be used in other models unless necessary. One line calculates
the volume of hot water withdrawn from the storage tank in each draw. This is 
the line that starts with "Model['Hot Water Draw Volume (L)']". Ideally this
would not be a calculated value because it would be measured in the monitoring 
data. Calculating it instead of measuring it adds some error to the model. 
Further, the temperature of hot water leaving the tank was not measured and the
calculation assumes that the water leaving the tank is at the temperature 
reported by the upper tank thermostat. This is probably pretty accurate, but
there is room for errors in the claculation because of this as well.

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
from Set_Temperature_Profiles import get_profile

#%%--------------------------HPWH PARAMETERS------------------------------
Time_At_Start_Of_Simulation = time.time()
#These inputs are a series of constants describing the conditions of the simulation. Many of them are overwritten with measurements
#if Compare_To_MeasuredData = 1

# Select the model for the set temperature
# Monitored reads it from monitored data
# Simulated reads it from the dictionary specified above
Set_Temperature_Model = 'Monitored'
if Set_Temperature_Model == 'Simulated':
    Set_Temperature_Profile = 'Static_140' #Read list of profile options in Set_Temperature_Profiles.get_profile
    Temperature_Tank_Set = get_profile(Set_Temperature_Profile)
#    Threshold_Deactivation_Backup = Temperature_Tank_Set #Deg C, sets the temperature when the backup element disengages after it has been engaged (115 F is the default)
Temperature_Tank_Initial = 50.5 #deg C, initial temperature of water in the storage tank (120 F is the current default)
Temperature_Tank_Set_Deadband = 3.5 #deg C, deadband on the thermostat (20 F is the default)
Temperature_Water_Inlet = 4.4 #deg C, inlet water temperature in this simulation (40 F is the default)
Temperature_Ambient = 20 #deg C, temperature of the ambient air, placeholder for now, 68 F is the default
Volume_Tank = 290 #L, volume of water held in the storage tank, based on 72 gal rating at https://www.energystar.gov/productfinder/product/certified-water-heaters/details/2317252
Coefficient_JacketLoss = 2.8 #W/K, Adjusted to match monitored data
Power_Backup = 3800 #W, electricity consumption of the backup resistance elements
Threshold_Activation_Backup = 16 #deg C, backup element operates when tank temperature is this far below the set temperature. This parameter operates as a deadband. Note that this operate at the same time as the heat pump (100 F is the default)
HeatAddition_HeatPump = 1230.9 #W, heat consumed by the heat pump
ElectricityConsumption_Active = 158.5 #W, electricity consumed by the fan when the heat pump is running
ElectricityConsumption_Idle = 18 #W, electricity consumed by the HPWH when idle
CO2_Output_Electricity = 0.212115 #ton/MWh, CO2 production when the HPWH consumes electricity. Default value is the average used in California
Coefficient_2ndOrder_COP = 0 #The 2nd order coefficient in the COP equation
Coefficient_1stOrder_COP = -0.037 #The 1st order coefficient in the COP equation
Constant_COP = 7.67 #The constant in the COP equation
Coefficient_2ndOrder_COP_Adjust_Tamb = 0.000055 # The 2nd order coefficient in the COP derate for ambient temperature equation
Coefficient_1stOrder_COP_Adjust_Tamb = -0.0077 # The 2nd order coefficient in the COP derate for ambient temperature equation
Constant_COP_Adjust_Tamb = 0.2874 # The 2nd order coefficient in the COP derate for ambient temperature equation
COP_Adjust_Reference_Temperature = 19.7222 # The ambient temperature that the COP coefficients represent
Temperature_MixingValve_Set = 48.9 #deg C, set temperature of the mixing valve

#%%--------------------------INPUTS-------------------------------------------

#This first variable provides the path to the data set itself. This means you should fill in the path with the specific location 
#of your data file. Note that this works best if the file is on your hard drive, not a shared network drive
cwd = os.getcwd()
Path_DrawProfile = cwd + r'\Input\Creekside Data for B9AE.csv'

Filename = Path_DrawProfile.split('Input\\')[1]
Path_Output = os.path.dirname(__file__) + os.sep + 'Output' + os.sep + 'Output_' + Filename

print('Path_DrawProfile is {}'.format(Path_DrawProfile))
print('Filename is {}'.format(Filename))
print('Path_Output is {}'.format(Path_Output))

Shift_On_Weekends = True # True if load shifting on weekends, false if not

#Set this = 1 if you want to compare model predictions to measured data results. This is useful for model validation and error
#checking. If you want to only input the draw profile and see what the data predicts, set this = 0. Note that =1 mode causes the
#calculations to take much longer
Compare_To_MeasuredData = 0

#Time filetering inputs. Use these if you want to look at a specified portion of the data set
Time_Filtering = 0 #Tells the program that time filtering is active
Start_Time = 35 #Hours
End_Time = 90 #Hours

Reading_Inputs = time.time()
print('Reading inputs takes {} seconds'.format(Reading_Inputs - Time_At_Start_Of_Simulation))

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
CO2_Production_Rate_Electricity = CO2_Output_Electricity * Pounds_In_Ton * kWh_In_MWh

#Calculating the thermal mass of the water in the storage tank
ThermalMass_Tank = Volume_Tank * Density_Water * SpecificHeat_Water

#Stores the parameters in a list for use in the model. The # comments after each row keep track of the number corresponding to each parameter, helping identify them when working in HPWH_Model.py
Parameters = [Coefficient_JacketLoss, #0
                Power_Backup, #1
                HeatAddition_HeatPump, #2
                Temperature_Tank_Set_Deadband, #3
                ThermalMass_Tank, #4
                CO2_Production_Rate_Electricity, #5
                COP_Adjust_Reference_Temperature] #6

Constant_Declarations = time.time()
print('Declaring constants takes {} seconds'.format(Constant_Declarations - Reading_Inputs))

#%%--------------------------MODELING-----------------------------------------

#Creates a 1 dimensional regression stating the COP of the gas heat pump as a function of the temperature of water in the tank
Coefficients_COP = [Coefficient_2ndOrder_COP, Coefficient_1stOrder_COP, Constant_COP] #combines the coefficient and the constant into an array
Regression_COP = np.poly1d(Coefficients_COP) #Creates a 1-d linear regression stating the COP of the heat pump as a function of the temperature of water in the tank

Coefficients_COP_Derate_Tamb = [Coefficient_2ndOrder_COP_Adjust_Tamb, Coefficient_1stOrder_COP_Adjust_Tamb, 
                                Constant_COP_Adjust_Tamb] #combines the coefficient and the constant into an array
Regression_COP_Derate_Tamb = np.poly1d(Coefficients_COP_Derate_Tamb) #Creates a 1-d linear regression stating the COP of the heat pump as a function of the temperature of water in the tank

Draw_Profile = pd.read_csv(Path_DrawProfile, index_col = 0) #Reads the input data, setting the first row (measurement name) of the .csv file as the header
Draw_Profile['Timestamp'] = Draw_Profile.index
Draw_Profile.index = pd.to_datetime(Draw_Profile.index)
Draw_Profile['Time (s)'] = (Draw_Profile.index - Draw_Profile.index[0]).total_seconds()
Draw_Profile['Time (min)'] = Draw_Profile['Time (s)'] / 60.
Draw_Profile['Hour'] = pd.DatetimeIndex(Draw_Profile['Timestamp']).hour

Model = Draw_Profile[['Timestamp', 'Time (s)', 'Time (min)', 'Hour', 'Power_PowerSum_W', 'Power_EnergySum_kWh', 
                      'Water_FlowRate_gpm', 'Water_FlowTotal_gal', 'Water_FlowTemp_F', 'Water_RemoteTemp_F', 
                      'T_Setpoint_F', 'T_Ambient_EcoNet_F', 'T_Cabinet_F', 'T_TankUpper_F', 'T_TankLower_F',
                      ]].copy() 
Model = Model.fillna(method='ffill') #Fills empty cells by projecting the most recent reading forward to the next reading
Model = Model.fillna(method='bfill') #Fills empty cells by copying the following reading into these cells. Note that this only happens for cells at the start of the data set because all other cells were filled by the previous line
#Model = Model.drop([0, 1]) #This line removes the first x (As defined by user) lines of code from the dataframe. It can be used if there are issues with the first few rows
#These two lines of code can be used to force data points to exist if no monitored data is available. Use with caution as this will introduce errors into the calculations!
#Model['T_TankUpper_F'] = 125
#Model['T_TankLower_F'] = 125

Model['Time (hr)'] = Model['Time (min)'] / Minutes_In_Hour #Creates new column representing the simulation time in hours instead of minutes

#This filter is ONLY for working with Creekside, 3FCA data. Comment out and/or delete as needed
if Time_Filtering == 1:
    Model = Model[Model['Time (hr)'] > Start_Time]
    Model = Model[Model['Time (hr)'] < End_Time]

#These lines calculate the time change between two rows in the data set and calculate the timestep for use in calculations
Model['Time shifted (min)'] = Model['Time (min)'].shift(1)
Model['Time shifted (min)'].iloc[0] = Model['Time (min)'].iloc[0]
Model['Timestep (min)'] =  Model['Time (min)'] - Model['Time shifted (min)']
Model = Model[Model['Timestep (min)'] != 0]
Model = Model.reset_index() #Do not delete this when removing the Creekside, 3FCA filter
del Model['index'] #Do not delete this when removing the Creekside, 3FCA filter

Model['Water_FlowRate_LPerMin'] = Model['Water_FlowRate_gpm'] * Liters_In_Gallon #Creates a new column representing the measured water flow rate, converted from gal/min to L/min
Model['Water_FlowTotal_L'] = Model['Water_FlowTotal_gal'] * Liters_In_Gallon #Creates a new column representing the total measured water flow, converted from gal to L
Model['Water_FlowTemp_C'] = (Model['Water_FlowTemp_F']-32) * 1/K_To_F_MagnitudeOnly #Creates a new column representing the outlet water temperature, converted from F to C
Model['Water_RemoteTemp_C'] = (Model['Water_RemoteTemp_F']-32) * 1/K_To_F_MagnitudeOnly #Creates a new column representing the inlet water temperature, converted from F to C
Model['Set Temperature (deg C)'] = (Model['T_Setpoint_F']-32) * 1/K_To_F_MagnitudeOnly #Create a column in the model representing the user-supplied, possibly varying, set temperature in deg C. If Variable_Set_Temperature == 1 this will be the set temperature used in the model
Model['Power_EnergySum_kWh'] = Model['Power_EnergySum_kWh'] - Model.loc[0, 'Power_EnergySum_kWh'] #Resets the cumulative electricity consumption column to use 0 as the value at the start of the monitoring period
Model['T_Ambient_EcoNet_C'] = (Model['T_Ambient_EcoNet_F']-32) * 1/K_To_F_MagnitudeOnly #Creates a new column representing the ambient temperature, converted from F to C
Model['T_Cabinet_C'] = (Model['T_Cabinet_F']-32) * 1/K_To_F_MagnitudeOnly #Creates a new column representing the air temperature in the cabinet, converted from F to C
Model['T_Tank_Upper_C'] = (Model['T_TankUpper_F']-32) * 1/K_To_F_MagnitudeOnly #Creates a new column representing the water temperature reported by the upper thermostat in the tank, converted from F to C
Model['T_Tank_Lower_C'] = (Model['T_TankLower_F']-32) * 1/K_To_F_MagnitudeOnly #Creates a new column representing the water temperature reported by the lower thermostat in the tank, converted from F to C
Model['Timestamp'] = pd.to_datetime(Model['Timestamp'])

if Set_Temperature_Model == 'Simulated': #If the user has opted to use an assumed set temperature
    Model['Hour'] = Model['Hour'].astype(str)
    Model['Set Temperature (deg C)'] = Model['Hour'].map(Temperature_Tank_Set)
    Model['Weekday?'] = Model['Timestamp'].dt.weekday
    Model['Weekday?'] = Model['Weekday?'] < 5
    if Shift_On_Weekends == False:
        Model.loc[Model['Weekday?'] == False, 'Set Temperature (deg C)'] = Temperature_Tank_Set['0']

Model['Temperature Activation Backup (deg C)'] = Model['Set Temperature (deg C)'] - Threshold_Activation_Backup #Set the activation temperature for the backup resistance element equal to the set temperature minus an additional delta before the resistance element engages

Preparing_Inputs = time.time()
print('Preparing inputs takes {} seconds'.format(Preparing_Inputs - Constant_Declarations))

#Fill the model dataframe with 0s so the cells are filled. Also specify specific initial values for a few specific cells, as initial values are available
Model['Tank Temperature (deg C)'] = 0 #Creates a row for the temperature of water in the tank, all cells set to 0 deg C
Model.loc[0, 'Tank Temperature (deg C)'] = Temperature_Tank_Initial #Sets the first row of water temperature to the user-specified initial water temperature
Model.loc[1, 'Tank Temperature (deg C)'] = Temperature_Tank_Initial #Sets the second row of water temperature to the user-specified initial water temperature
Model['Jacket Losses (J)'] = 0 #Creates a column for the jacket losses and sets all cells equal to 0 J
Model['Energy Withdrawn (J)'] = 0 #Creates a column for the energy withdrawn from the tank and sets all cells equal to 0 J
Model['Energy Added Backup (J)'] = 0 #Creates a column for the energy provided by the backup electric resistance elements and sets all cells to 0 J
Model['Energy Added Heat Pump (J)'] = 0 #Creates a column for the energy added by the heat pump and sets all cells to 0 J
Model['Energy Added Total (J)'] = 0 #Creates a column for the energy added by all sources and sets all cells to 0 J
Model['COP'] = 0 #Creates a column representing the calculated coefficient of performance of the heat pump and sets all cells to 0 J
Model['Total Energy Change (J)'] = 0 #Creates a column representing the total energy change in the storage tank over each timestep and sets all cells to 0 J
Model['COP Adjust Tamb'] = 0 # Adjustment for the COP based on how T_Amb differs from 67.5 deg C

#Sets the following two parameters equal to the monitored data for the entire simulation
Model['Ambient Temperature (deg C)'] = Model['T_Cabinet_C'] #Sets ambient temperature in the simulation model equal to the monitored temperature in the cabinet
Model['Inlet Water Temperature (deg C)'] = Model['Water_RemoteTemp_C'] #Set the inlet water temperature in the model equal to the monitored inlet water temperature

#This section calculates the volume of hot water removed from the tank during
#each timestep. First it creates a new column showing the cumulative water flow
#shifted by one timestep and fills the initial value of that new column. Then
#it creates another column equal to the difference between those two columns
#and representing the volume of water withdrawn during each timestep. The final
#line calculates the estimated hot water flow based on the calculated total
#water draw volume and assumed hot water temperatures. See the comments at the
#top for more comments about this
Model['Water_FlowTotal_L shifted'] = Model['Water_FlowTotal_L'].shift(1)
Model['Water_FlowTotal_L shifted'].iloc[0] = Model['Water_FlowTotal_L'].iloc[0]
Model['Water Draw Volume (L)'] =  Model['Water_FlowTotal_L'] - Model['Water_FlowTotal_L shifted']
Model['Hot Water Draw Volume (L)'] = (Model['Water Draw Volume (L)'] * Model['Water_RemoteTemp_C'] - 
     Model['Water Draw Volume (L)'] * Temperature_MixingValve_Set) / (Model['Water_RemoteTemp_C'] - 
     Model['T_Tank_Upper_C'])

Model = HPWH.Model_HPWH_MixedTank(Model, Parameters, Regression_COP, Regression_COP_Derate_Tamb) #Passes the data to the mixed tank HPWH simulation model

Model['Timestamp'] = pd.to_datetime(Model['Timestamp'])
Model = Model.set_index('Timestamp')

Simulation_End = time.time() #Identify the time at the end of the simulation

Simulated = Model['Electricity Consumed (kWh)'].sum()
Measured = Model.loc[Model.index[-1], 'Power_EnergySum_kWh']
PercentError = (Simulated - Measured) / Measured * 100

print('Simulation time is {} seconds'.format(Simulation_End - Preparing_Inputs)) #Print the total time elapsed during the simulation for diagnostic purposes

Model_Reduced = Model[['Time (s)', 'Timestep (min)', 'Set Temperature (deg C)', 'Tank Temperature (deg C)', 
                       'Energy Withdrawn (J)', 'Energy Added Total (J)', 'Ambient Temperature (deg C)', 
                       'Inlet Water Temperature (deg C)', 'Water Draw Volume (L)', 
                       'Hot Water Draw Volume (L)', 'Electricity Consumed (kWh)',
                       'Energy Added Backup (J)', 'Energy Added Heat Pump (J)', 'Power_PowerSum_W', 'COP',
                       'Power_EnergySum_kWh']]

Model_Reduced.to_csv(Path_Output) #Save the model to the declared file
print('Results saved to {}'.format(Path_Output))

Saving_Results = time.time()
print('Saving results takes {} seconds'.format(Saving_Results - Simulation_End))
print('PercentError is {}'.format(PercentError))

#%%--------------------------MODEL COMPARISON-----------------------------------------

#This code is only run when comparing the model results to field measurements. It is typically used for model validation
if Compare_To_MeasuredData == 1:
    #Calculate the electricity consumed over the simulation and the % error for validation purposes
    Model['Total Electricity Consumption (kWh)'] = Model['Electricity Consumed (kWh)'].cumsum()
    Model['Cumulative Percent Error (%)'] = (Model['Total Electricity Consumption (kWh)'] - 
         Model['Power_EnergySum_kWh']) / (Model['Power_EnergySum_kWh'] + 0.000000000001) * 100
    
    tools = [LassoSelectTool(), WheelZoomTool(), BoxZoomTool(), ResetTool()]    
    
    #The rest of the code creates and saves plots comparing the HPWH model to the monitored data. Detailed comments will not be provided.
    p1 = figure(width=1200, height= 600, x_axis_label='Time (hr)', y_axis_label = 'Electric Power (W)', tools = tools)
    p1.title.text_font_size = '12pt'
    p1.line(x = Model['Time (hr)'], y = Model['Electric Power (W)'], legend = 'Model', color = 'red')
    p1.circle(x = Model['Time (hr)'], y = Model['Power_PowerSum_W'], legend = 'Data', color = 'blue')   
    p1.circle(x = Model['Time (hr)'], y = Model['Set Temperature (deg C)'], legend = 'Set Temperature', color = 'orange')
    p1.legend.label_text_font_size = '18pt'
    p1.legend.location = 'bottom_right'
    p1.xaxis.axis_label_text_font_size = '18pt'
    p1.yaxis.axis_label_text_font_size = '18pt'
    p1.xaxis.major_label_text_font_size = '12pt'
    p1.yaxis.major_label_text_font_size = '12pt'

    p2 = figure(width=1200, height= 600, x_axis_label='Time (hr)', y_axis_label = 
                'Cumulative Electricity Consumption (kWh)', tools = tools)
    p2.title.text_font_size = '12pt'
    p2.line(x = Model['Time (hr)'], y = Model['Total Electricity Consumption (kWh)'], legend = 'Model', 
                      color = 'red')
    p2.circle(x = Model['Time (hr)'], y = Model['Power_EnergySum_kWh'], legend = 'Data', color = 'blue')    

    p3 = figure(width=1200, height= 600, x_axis_label='Time (hr)', y_axis_label = 'Water Temperature (deg C)', 
                tools = tools)
    p3.title.text_font_size = '12pt'
    p3.line(x = Model['Time (hr)'], y = Model['Tank Temperature (deg C)'], legend = 'Model, Tank Average', 
                      color = 'red')
    p3.circle(x = Model['Time (hr)'], y = Model['T_Tank_Upper_C'], legend = 'Data, Upper', color = 'blue') 
    p3.circle(x = Model['Time (hr)'], y = Model['T_Tank_Lower_C'], legend = 'Data, Lower', color = 'purple') 
    p3.circle(x = Model['Time (hr)'], y = Model['Set Temperature (deg C)'], legend = 'Set Temperature', 
                        color = 'orange')
    p3.legend.label_text_font_size = '18pt'
    p3.legend.location = 'bottom_right'
    p3.xaxis.axis_label_text_font_size = '18pt'
    p3.yaxis.axis_label_text_font_size = '18pt'
    p3.xaxis.major_label_text_font_size = '12pt'
    p3.yaxis.major_label_text_font_size = '12pt'    

#    p4 = figure(width=1200, height= 600, x_axis_label='Time (hr)', y_axis_label = 
#                'Cumulative Water Consumption (L)', tools = tools)
#    p4.title.text_font_size = '12pt'
#    p4.circle(x = Model['Time (hr)'], y = Model['Water_FlowTotal_L'], legend = 'Water', color = 'blue') 
#
#    p5 = figure(width=1200, height= 600, x_axis_label='Time (hr)', y_axis_label = 
#                'Water Consumption Each Timestep (L)', tools = tools)
#    p5.title.text_font_size = '12pt'
#    p5.circle(x = Model['Time (hr)'], y = Model['Water Draw Volume (L)'], legend = 'From MV', color = 'blue') 
#    p5.circle(x = Model['Time (hr)'], y = Model['Hot Water Draw Volume (L)'], legend = 
#                        'From WH - Calculated', color = 'red') 
#
#    p6 = figure(width=1200, height= 600, x_axis_label='Time (hr)', y_axis_label = 
#                'Water Temperatures (deg C)', tools = tools)
#    p6.title.text_font_size = '12pt'
#    p6.circle(x = Model['Time (hr)'], y = Model['T_Tank_Upper_C'], legend = 'T_Tank_Upper_C', color = 'red') 
#    p6.circle(x = Model['Time (hr)'], y = Model['Water_FlowTemp_C'], legend = 'Water_FlowTemp_C', 
#                        color = 'purple') 
#    p6.circle(x = Model['Time (hr)'], y = Model['Water_RemoteTemp_C'], legend = 'Water_RemoteTemp_C', 
#                        color = 'blue') 
#
#    p7 = figure(width=1200, height= 600, x_axis_label='Time (hr)', y_axis_label = 
#                'Monitored Ambient Temperature (deg C)', tools = tools)
#    p7.title.text_font_size = '12pt'
#    p7.circle(x = Model['Time (hr)'], y = Model['T_Cabinet_C'], legend = 'T_Cabinet_C', color = 'blue') 
#    p7.circle(x = Model['Time (hr)'], y = Model['T_Ambient_EcoNet_C'], legend = 'T_Ambient_EcoNet_C', 
#                        color = 'red') 
#
#    p8 = figure(width=1200, height= 600, x_axis_label='Time (hr)', y_axis_label = 
#                'Error in Electricity Consumption (%)', tools = tools)
#    p8.title.text_font_size = '12pt'
#    p8.circle(x = Model['Time (hr)'], y = Model['Cumulative Percent Error (%)'], legend = 'Error', 
#                        color = 'black') 

    p = gridplot([[p1],[p2],[p3]])#,[p4],[p5],[p6],[p7], [p8]])
    if Time_Filtering == 0:
        output_file(os.path.dirname(__file__) + os.sep + 'Validation Data\Validation Plots_' + 
                    Filename + '.html', title = 'Validation Data')
    elif Time_Filtering == 1:
        output_file(os.path.dirname(__file__) + os.sep + 'Validation Data\Validation Plots_' + Filename + 
                    '_Start=' + str(Start_Time) + '_End=' + str(End_Time) + '.html', title = 'Validation Data')
    save(p)

Validation_Results = time.time()
print('Creating validation plots takes {} seconds'.format(Validation_Results - Saving_Results))