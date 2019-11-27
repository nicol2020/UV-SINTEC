import serial
import time
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from matplotlib import cm
import pandas as pd
import numpy as np
import Gaussian_Power_Model
import Cosine_Power_Model
#import Database_Update_Diode
import Database_Update
import centering

#wavelength = str(input("Enter Manufacturer Wavelength in nm :")).replace(" ", "")+"nm"
product_code = str(input("Enter Full Product Code of the photodiode:")).replace(" ", "")
noofsweeps = int(input("Enter Number of Sweeps Completed in integers:"))
boxcar = int(input("Please Enter Boxcar Value :"))
filename = product_code + r'_sweeps'+str(noofsweeps)+ '_boxcar'+ str(boxcar)+'_.xlsx'
print("")
print("The filename is %s" % filename)
print("")
DiodeAngles = []
noofangles = 4
normalised = pd.DataFrame()
#LEDAngles = pd.DataFrame()
lengthIndex=400
norm = pd.DataFrame()
difAngle = 0
for difAngle in range (0, noofangles):
    DiodeAngle = int(input("Please Enter Angle of Photodiode:"))
    dir = '1'
    reset ='3'
    ser = serial.Serial("COM4", 9600, timeout = 5)
    time.sleep(3)


    
    ser.write(str.encode(reset))
    try:
        line = ser.readline()

        data = np.zeros([2*noofsweeps, lengthIndex-1])
        for j in range (0, 2*noofsweeps):
            ser.write(str.encode(dir))
            time.sleep(3)
            
            line = ser.readline()
            # print(line)
            
            for i in range (0,lengthIndex-1):
                line = ser.readline()
                #  print(line)
                data[j, i] = float(line)
                
                if ((j%2)==0):
                    data[j] = np.flip(data[j])
                    
                if(dir == '1'):
                    dir = '2'
                elif(dir=='2'):
                    dir='1'
                            
    finally:
        ser.close()    
    
    data = np.transpose(data)
    angle = np.arange(-89.55, 90, 0.45)   
    export = pd.DataFrame()
    export['Angle'] = angle
    
  
    #fig, (ax1, ax2) = plt.subplots(1,2)
    #ax1.plot(angle, data)
    #ax1.set_title('Different Sweeps')
    #ax1.set_xlabel('Angle (degrees)')
    #ax1.grid()
    
    avg = np.mean(data, axis = 1)
    #ax2.plot(angle, avg)
    #ax2.set_title("Average of Sweeps")
    #ax2.set_xlabel ("Angle (degrees)")
    #ax2.grid()
    #plt.show()
    
    
    df= pd.DataFrame(avg)
    filt = df.rolling(boxcar, min_periods=1).mean()
    background = filt.min()
    shifted = (filt-background)
    peak = shifted.max()
    normalised = (shifted/peak)
    #norm = (shifted/peak)
    normalised = np.array(normalised[0])
    
    #export['Response (normalised)'+difAngle] = normalised

    newnormalised = centering.centerdata(normalised, lengthIndex)
    # result = np.where(newnormalised == np.amax(newnormalised))
    #export_excel = export.to_excel (filename, index = False, header=True) #Don't forget to add '.xlsx' at the end of the path

    #normalised = np.array(difAngle, newnormalised) 
    norm[difAngle] = newnormalised
    DiodeAngles.append(DiodeAngle)
    
X1 = np.zeros((noofangles+1,399))
Y1 = np.zeros((noofangles+1,399))
#Z1 = np.zeros((noofangles+1,399))
norm = np.transpose(norm)


for k in range (0, noofangles):
    X1[k] = angle*np.cos(np.deg2rad(DiodeAngles[k]))
    Y1[k] = angle*np.sin(np.deg2rad(DiodeAngles[k]))

X1[noofangles] = np.flip(X1[0])
Y1[noofangles] = np.flip(Y1[0])

temp = np.array(norm.loc[0])

#norm.append(temp)
norm.loc[len(norm)] = np.flip(temp)
Z1 = np.array(norm)

fig = plt.figure()
ax = plt.axes(projection='3d')
surf = ax.plot_surface(X1, Y1, Z1, cmap=cm.coolwarm,
                       linewidth=0, antialiased=False)
ax.set_title('Nomalised 3D Response of a photodiode ('+ product_code +')')
ax.set_xlabel('Angle in the x-direction')
ax.set_ylabel('Angle in the y-direction')
ax.set_zlabel('Normalised Beam Profile of the LED')
fig.colorbar(surf, shrink=0.5, aspect=5)
norm = np.transpose(norm)


bound_gauss = [[.1 , [1 , 1] , [0 ,90] , [0 , 90]] , [.2 ,[0,.2] , [0 , 90] , [0 , 90]] , [.2, [0 , 0.2] , [0 ,90] , [0 , 90]] , [.2, [0 , 0.2] , [0 ,90] , [0 , 90]]]
bound_cos = [[.1 , [1 , 1] , [0 ,0] , [0 , 10]] , [.1,[0,.2] , [45 , 90] , [0 , 200]] , [.1, [0 , 0.2] , [0 ,45] , [0 , 200]] , [.1,[0 , 0.2] , [0 ,90] , [0 , 200]]]
RMSE_array = []
model_array = []
Param_array = []
#Param = np.zeros((noofangles,0))

for w in range (0, noofangles):
    Power_g , Error_g , Param_g = Gaussian_Power_Model.model_fit(angle , norm[w] , .02 , bound_gauss)
    Gaussian_Power_Model.model_plot(Param_g , angle , norm[0])


    Power_c , Error_c , Param_c = Cosine_Power_Model.model_fit(angle , norm[w] , .02 , bound_cos)
    Cosine_Power_Model.model_plot(Param_c , angle , norm[0])

    Param , model , RMSE = Gaussian_Power_Model.model_choice(Param_c , Power_c , Param_g , Power_g , norm[w])
    model_array.insert(w, model)
    RMSE_array.insert(w, RMSE)
    Param_array.insert(w, Param)
    print("The optimal RMSE is: ")
    print(RMSE)
    
add_model = str(input("Do you want to add this model to the Database (y/n) :")).replace(" ","")
check = False
while check == False :
    if add_model.lower() == "y" :
        Database_Update.write_to_database_diode(product_code 
                                          , DiodeAngles[0] , Param_array[0] , RMSE_array[0] , norm[0].tolist()
                                          , DiodeAngles[1] , Param_array[1] , RMSE_array[1] , norm[1].tolist()
                                          , DiodeAngles[2] , Param_array[2] , RMSE_array[2] , norm[2].tolist()
                                          , DiodeAngles[3] , Param_array[3] , RMSE_array[3] , norm[3].tolist()
                                          , model_array[0] , model_array[1] , model_array[2] , model_array[3]
                                          )
        check = True
    elif add_model.lower() == "n" :
        check = True
    else :
        print("")
        print("Error please select y/n")
        check = False
        
print (DiodeAngles)



