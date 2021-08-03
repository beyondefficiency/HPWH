# -*- coding: utf-8 -*-
"""
Created on Fri Jul 30 20:36:26 2021

This script contains equations used to adjust the ambient air temperature
used when calculating the COP of the HPWH. It performs different calculations
based on the type of ducting used.

@author: Peter Grant
"""

def get_compressor_temperature(Model, Installation):
    
    if Installation == 'Open_Area':
        # Representing a scenario when the HPWH is installed in an area
        # with adequate air flow, does not impact the ambient temperature, and
        # the assumed ambient temperature matches the surroundings
        Model['Ambient Temperature (deg C)'] = Model['Ambient Temperature (deg C)']
        Model['Air Inlet Temperature (deg C)'] = Model['Ambient Temperature (deg C)']
    elif Installation == 'Unducted_Closet:
    # Represents a scenario where the HPWH is in a closet with restricted air
    # flow. The closet will have different ambient temperatures than the
    # outdoor air, both impacted by the HPWH and by insulation & thermal mass
    # Change this code to reference correlation when Marc sends it
        Model['Ambient Temperature (deg C)'] = Model['Ambient Temperature (deg C)']
        Model['Air Inlet Temperature (deg C)'] = Model['Ambient Temperature (deg C)']
    elif Installation == 'Ducted_Exhaust':
        # Represents a case where a HPWH is installed in a closet with exhaust
        # air ducted outside of the building. The closet temperature is 
        # different from the OAT. The HPWH receives reduced airflow due to
        # constraints in the closet
        # Add calculations to adjust ambient temperature when Marc sends it
        Model['Air Inlet Temperature (deg C)'] = Model['Ambient Temperature (deg C)'] - 4.2
    elif Installation == 'Ducted_Both':
        # Represents a case where a HPWH is installed in a closet with both
        # inlet and exhaust air outside of the building. The close temperature
        # is different from the OAT. The HPWH receives reduced air flow due to
        # constraints in the closet
        # Add calculations to adjust ambient temperature when Marc sends it
        Model['Air Inlet Temperature (deg C)'] = Model['Ambient Temperature (deg C)']
        Model['Ambient Temperature (deg C)'] = Model['Ambient Temperature (deg C)']