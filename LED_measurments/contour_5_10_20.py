# -*- coding: utf-8 -*-
"""
Created on Mon Jan  6 09:43:52 2020

@author: Nikolina

script for getting 5%, 10%, 20% , 50% of data in z/mW column
depend which % we need -> change in 'new_value = max_value * 0.90'
values that is less then 5% or 10 % set on 0
and then plot results 
"""

from mpl_toolkits.mplot3d import Axes3D
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np


# plot
fig = plt.figure()
ax = plt.axes(projection='3d')

#read data from csv file
my_csv = pd.read_csv('13LEDs_with_plastic_cover.csv')

#find max of mW
max_value = my_csv['z'].max()

#get new dataframe with % mW less then origin
new_value = max_value * 0.95
#values less then new_value set on 0
my_csv['z'].values[my_csv['z'].values < new_value] = 0


column1 = my_csv['x']
column2 = my_csv['y']
column3 = my_csv['z']      # my_csv['z'] for voltage/current value
                            # my_csv['mW'] for power in milliwatts
#print(my_csv)
                            
surf = ax.plot_trisurf(column1, column2, column3, cmap='viridis', linewidth=0.005)
ax.set_title('13LEDs_with_cover')
ax.set_xlabel('x coordinates')
ax.set_ylabel('y coordinates')
ax.set_zlabel('Amplitude')
ax.view_init(90,0)          # for bird's eye view of contour heat map
fig.colorbar(surf)
plt.show()


#get data in new dateframe and plot in  29*29 
fig = plt.figure()
ax = plt.axes(projection='3d')

data_5cut = my_csv[my_csv['z'] > 0]
column1 = data_5cut['x']
column2 = data_5cut['y']
column3 = data_5cut['z']      # my_csv['z'] for voltage/current value
                            # my_csv['mW'] for power in milliwatts
#print(my_csv)
                            
surf = ax.plot_trisurf(column1, column2, column3, cmap='viridis', linewidth=0.005)
ax.set_title('13LEDs_with_cover')
ax.set_xlabel('x coordinates')
ax.set_ylabel('y coordinates')
ax.set_zlabel('Amplitude')
ax.set_xlim(0,29)
ax.set_ylim(0,29)
ax.view_init(90,0)          # for bird's eye view of contour heat map
fig.colorbar(surf)
plt.show()

#scatter of cut data 
data_5cut.plot.scatter("x","y", xlim = (0,29), ylim = (0,29), grid = True, title = '5%')

plt.show()