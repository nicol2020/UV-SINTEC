# -*- coding: utf-8 -*-
"""
Created on Mon Jun 24 14:18:32 2019
@author: emlon
"""
import os, csv, re
import numpy as np
import matplotlib.pyplot as plt
from scipy import stats
import Database_Update_LED

def interp(x, y, x1):
    '''
    Linearly interpolates the curve given by lists x and y at point x1.
    The list x must be increasing
    '''
    # Find where x crosses x1
    i = next((idx - 1 for idx, val in enumerate(x) if val > x1), len(x) - 2)
    # dx is the distance past x[i] we need to go
    dx = x1 - x[i];
    # Use the slope to figure out dy, and add to y[i]
    slope = (y[i+1] - y[i]) / (x[i+1] - x[i])
    dy = slope * dx
    y1 = y[i] + dy

    return y1

# Save calibration file for calculations
if 'SpecValsFinal1.txt' in os.listdir('.'):
    specfilename = 'SpecValsFinal1.txt'
    
    with open(specfilename) as f:
        specfile = csv.reader(f)
        # Save wavelength and factor values as a dict of lists
        specdata = {
            'wavelen': [],
            'factor': [],
        } 
        for row in specfile:
                specdata['wavelen'].append(float(row[0]))
                specdata['factor'].append(float(row[1]))    
else:
    raise Exception('File SpecValsFinal1.txt not found!')

summarydata = [] # Create array to save final values for summary file

# Iterate all led files
for filename in os.listdir('.'):
    # Validate all file names, make sure we're only reading LED data
    if os.path.isdir(filename):
        continue    
    if filename == os.path.basename(__file__):
        print('Ignoring file {0}, it is me!'.format(filename))
        continue  
    if filename == 'SpecValsFinal1.txt':
        continue
    if not filename.endswith(".txt"):
        print('Ignoring file {0}, not a .txt file'.format(filename))
        continue
                
    # Get led info from file name
    ledname = os.path.splitext(filename)[0]
    fileparts = re.split('-|_', ledname)
    
    # Check file names are correct format
    if not (len(fileparts) == 9 or len(fileparts) == 8): 
        print('Ignoring file {0}, not named in the correct format'.format(filename))
        continue
    elif len(fileparts) == 8: # If product code is one word
        [productcode, wavelen, current, inttime, boxcaravg, nscans, bgsignal, num] = fileparts
        devnum = num 
    else: # If product code is in form abc-def
        [productcode1, productcode2, wavelen, current, inttime, boxcaravg, nscans, bgsignal, num] = fileparts
        productcode = productcode1 + '-' + productcode2 
        devnum = num

    print('Processing file {0}'.format(filename))

    # Convert inttime to a float so we can use it later
    if inttime.endswith('ms'):
        inttime = float(inttime[:-2])
    else:
        inttime = float(inttime) 

    if current.endswith('mA') or current.endswith('ma'):
        current = float(current[:-2])
    else:
        current = float(current)
                   
    # Read the wavelength and raw count data from the file
    with open(filename) as f:
        datafile = csv.reader(f, delimiter=' ')
        for i in range(271):   # count from 0 to 271, index of 250.093
            next(datafile)     # and discard the rows
           
        data = {
            'wavelen': [],
            'count': [],
        }
        
        for row in datafile:
            data['wavelen'].append(float(row[0]))
            data['count'].append(float(row[1]))  
            
    # Get the peak count and the wavelength at which it occurs    
    peakcount = max(data['count'])
    peakidx = data['count'].index(peakcount)
    peakwavelen = data['wavelen'][peakidx]
    #peakwavelenList.append(peakwavelen)
        
    # Interpolate correction factor for each wavelength point
    factor = [interp(specdata['wavelen'], specdata['factor'], wl) for wl in data['wavelen']]
    
    # Do the calculations 
    expN = inttime * 100
    expcorrect = expN * 0.184
    
    # Irradiance(uW/cm^2/nm)
    irrad = [(data['count'][i] * factor[i]) / expcorrect for i, _ in enumerate(factor)]
    data['irradiance'] = irrad
      
    # Find the peak irradiance
    peakirrad = irrad[peakidx]
    
    # Convert to Irradiance (W/m^2/nm)
    newirrad = [irrad[i]*0.000001*10000 for i, _ in enumerate(irrad)]
    data['newirrad']=newirrad
    
    # Convert to integrated irradiance (W/m^2)
    intirradList = []
    for i in range(len(irrad) - 1):
        newirradavg = (newirrad[i] + newirrad[i+1]) / 2
        wavelenrange = data['wavelen'][i+1] - data['wavelen'][i]
        intirrad = newirradavg * wavelenrange
        intirradList.append(intirrad)
    
    intirradList.append(0)   
    
    # Calculate photon density (m^-2 s^-1)    
    photondens = [intirradList[i] / ((6.626e-34 * 2.997e8) / (data['wavelen'][i] * 1e-9)) for i, _ in enumerate(irrad)]
    data['photondens'] = photondens
    
    # Calculate photon flux density (umol/m^2/s)
    flux = [photondens[i]/(6.022e23/1e6) for i, _ in enumerate(irrad)]
    data['flux'] = flux
                
    # Add each area slice to the integral
    for i in range(len(photondens) - 1):
        irradavg = (irrad[i] + irrad[i+1]) / 2
        wavelenrange = data['wavelen'][i+1] - data['wavelen'][i]
    
    # Interpolate where the count reaches half its maximum on both sides. The data for the right 
    # side is reversed so that wavelength is increasing and interp likes it
    FWHM = interp(data['count'][:peakidx:-1], data['wavelen'][:peakidx:-1], peakcount/2) - \
           interp(data['count'][:peakidx], data['wavelen'][:peakidx], peakcount/2)
        
    rangeVal = float(2.5)  
    upper = float((FWHM*rangeVal)/2)  # range of 2.5 times FWHM value
   
    upperLimit = float(peakwavelen + upper)
    lowerLimit = float(peakwavelen - upper)                   
        
    topIndex = min(enumerate(data['wavelen']),key=lambda x: abs(x[1]-upperLimit))[0]
    bottomIndex = min(enumerate(data['wavelen']),key=lambda x: abs(x[1]-lowerLimit))[0]
    
    # Total integrated irradiance    
    totalintIrradList = []
    for i in range (bottomIndex, topIndex +1):
         intirrad = intirradList[i]
         totalintIrradList.append(intirrad)
                   
    #totalIntIrrad =sum(totalintIrradList)/1E4 # Emilys code
    totalIntIrrad =sum(totalintIrradList) # changed by nikolina
    print(totalIntIrrad)
    
    # Total photon flux density
    photonFluxList = []
    for i in range (bottomIndex, topIndex +1):
        photonfluxdensity = photondens[i]/(6.022e23/1e6)
        photonFluxList.append(photonfluxdensity)
    
    totalphotonFlux = sum(photonFluxList)   
       
    # Append the data for the summary so we can write it later
    summarydata.append([num, productcode, current, peakwavelen, totalIntIrrad, totalphotonFlux, FWHM, lowerLimit, upperLimit])  

    # Create our results file
    # Ensure our output dir exists
    if not os.path.exists('Output'):
        os.makedirs('Output')
    
    # Create a CSV file and print wavelength, count, irradiance, and photon density
    with open(os.path.join('Output', ledname + '.csv'), 'w') as f:
        outfile = csv.writer(f)
        outfile.writerow(['Wavelength (nm)', 'Raw Counts', 'Photon Density (m^-2 s^-1)','Irradiance(uW/cm^2/nm)', 'Irradiance (W/m^2/nm)', 'Integrated Irradiance (W/m^2)',' Photon Flux Density (umol/m^2/s)'])
    
        for i in range(len(data['wavelen'])):
            outfile.writerow([data['wavelen'][i], data['count'][i], data['photondens'][i], data['irradiance'][i], data['newirrad'][i], intirradList[i], data['flux'][i]])

if not os.path.exists('Output'):
    os.makedirs('Output') 

# Save list of device numbers,currents, total integrated irradiances, product codes, peak wavelengths, FWHM
devicenumbers = []
integratedirradiances = []
currents=[]
productcodes = []
peakwavelenList = []
FWHMList = []
for i in range (0,len(summarydata)):
    
    newdevicenumber = summarydata[i][0]
    devicenumbers.append(newdevicenumber)
    
    newintegratedirradiance = summarydata[i][4]
    integratedirradiances.append(newintegratedirradiance)
    
    newpeakwavelen = summarydata[i][3]
    peakwavelenList.append(newpeakwavelen)
    
    newcurrent = summarydata[i][2]
    currents.append(newcurrent)
    
    newproductcode = summarydata[i][1]
    productcodes.append(newproductcode)
    
    newFWHM = summarydata[i][6]
    FWHMList.append(newFWHM)
   
# Save list of device numbers, no duplicates
numberofdevicesList = []     
for x in devicenumbers: 
    # check if exists in unique_list or not 
    if x not in numberofdevicesList: 
        numberofdevicesList.append(x) 

numberofdevices = len(numberofdevicesList) #how many devices are there

numberofproductcodes = []
for i in range(len(numberofdevicesList)):
    numberofproductcodes.append(productcodes[i])  

#save index of different device numbers
index_list=[]
for i in range(numberofdevices):
    index = numberofdevicesList[i]
    index_list.append(index)

listofindices = []
for i in index_list:
    indices = [y for y, x in enumerate(devicenumbers) if x == i]
    listofindices.append(indices)

plotintirradlists = [[] for i in range(0, numberofdevices)]
plotcurrentlists = [[] for i in range(0, numberofdevices)]
savepeakwavelenlists = [[] for i in range(0, numberofdevices)]
saveFWHMlists = [[] for i in range(0, numberofdevices)]
i = 0
# save info to be plotted in lists, according to device number
listofintirradlists =[]
listofcurrentlists =[]
listofpeakwavelenlists = []
listofFWHMlists = []
for list in listofindices:
    plotcurrentlist = plotcurrentlists[i]
    plotintirradlist = plotintirradlists[i]
    savepeakwavelenlist = savepeakwavelenlists[i]
    saveFWHMlist = saveFWHMlists[i]
    i += 1
    for j in list:
        plotcurrentlist.append(currents[j])
        plotintirradlist.append(integratedirradiances[j])
        savepeakwavelenlist.append(peakwavelenList[j])
        saveFWHMlist.append(FWHMList[j])
        
    listofcurrentlists.append(plotcurrentlist)
    listofintirradlists.append(plotintirradlist)
    listofpeakwavelenlists.append(savepeakwavelenlist)
    listofFWHMlists.append(saveFWHMlist)

dirpath = os.getcwd() # Get current directory path

slopelist = []
rsquaredlist = []
imagelist = []
averagepeakwavelenlist = []
averageFWHMlist = []
# Plot current vs integrated irradiance for each device
for a,b,c,d,e in zip(listofcurrentlists, listofintirradlists, numberofdevicesList,listofpeakwavelenlists, listofFWHMlists ):
    a = np.array(a)
    b = np.array(b)
    plt.figure()
    slope, intercept, r_value, p_value, std_err = stats.linregress(a,b)
    plt.plot(a, b, 'o', label='Original Data')
    plt.plot(a, intercept + slope*a, 'r', label='Fitted Line')
    plt.legend()
    #plt.show()
    plt.xlabel('Current (mA)')
    plt.ylabel('Total Integrated Irradiance (W/m^2)')
    plt.title('Device Number ' + c)
    plt.grid(True)
    image = 'Device_Number_' + c + '.jpeg'
    imagename = dirpath + '\\Output\\' + image
    plt.savefig(imagename) # save plot to figure
    # save slopes, r squared values and filenames to lists for later
    slope = round((slope*1e3), 3)
    slopelist.append(slope)
    rsquaredlist.append(round((r_value**2), 3))
    imagelist.append(imagename)
    averagepeakwavelen = round(sum(d)/len(d))
    averagepeakwavelenlist.append(averagepeakwavelen)
    averageFWHM = round(sum(e)/len(e))
    averageFWHMlist.append(averageFWHM)  

rows = zip(numberofdevicesList, numberofproductcodes, averagepeakwavelenlist, averageFWHMlist, slopelist, rsquaredlist, imagelist)
summarydatarow = []
for row in rows:
    summarydatarow = ([row])
    print ('LED Information:', summarydatarow)
    add_model = str(input("Do you want to add this LED to the Database (y/n) :")).replace(" ","")
    check = False
    while check == False :
        if add_model.lower() == "y" :
            Database_Update_LED.write_to_database(summarydatarow)
            check = True
        
        elif add_model.lower() == "n" :
            check = True
        else :
            print("")
            print("Error please select y/n")
            check = False
    
with open(os.path.join('Output', 'Summary.csv'), 'w') as f:
    outfile = csv.writer(f, delimiter = ',')
    outfile.writerow(['Device Number', 'Product Code', 'Average Peak Wavelength (nm) ', 'FWHM Bandwidth(nm)', 'Slope (W/A)', 'R-Squared', 'Graph Filename'])
    for row in summarydatarow:
        outfile.writerow(row)

# Print peak wavelength, FWHM bandwidth, and integrated photon flux and irradiance
with open(os.path.join('Output', 'Individual Device Summary.csv'), 'w') as f:
    outfile = csv.writer(f,delimiter=',')
    outfile.writerow(['Device Number', 'Product Code', 'Current (mA)', 'Peak Wavelength (nm)', 'Integrated Irradiance (W/m^2)', 'Photon Flux Density (umol/m^2/s)', 'FWHM Bandwidth (nm)', 'Lower Integration Limit (nm)', 'Upper Integration Limit (nm)'])
    for d in summarydata:
        outfile.writerow(d)
