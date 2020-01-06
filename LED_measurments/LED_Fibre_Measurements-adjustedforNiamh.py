# -*- coding: utf-8 -*-
"""
Created on Mon Jun 24 14:18:32 2019
@author: emlon


nikolina - update 06/01/2020 - split column Location into Locationx and locationy
"""
import os, csv, re

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
    
    # check file names are correct format
    if not (len(fileparts) == 10 or len(fileparts) == 11):
        print('Ignoring file {0}, not named in the correct format'.format(filename))
        continue
        
    elif len(fileparts) == 10:
        [productcode, wavelen, current, inttime, boxcaravg, nscans, bgsignal, locationx, locationy, num] = fileparts 
        devnum = num
        
        
    elif len(fileparts)== 11:
        [productcode1, productcode2, wavelen, current, inttime, boxcaravg, nscans, bgsignal,  locationx, locationy, num] = fileparts
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
    
    # calculate photon density (m^-2 s^-1)    
    photondens = [intirradList[i] / ((6.626e-34 * 2.997e8) / (data['wavelen'][i] * 1e-9)) for i, _ in enumerate(irrad)]
    data['photondens'] = photondens
    
    # calculate photon flux density (umol/m^2/s)
    flux = [photondens[i]/(6.022e23/1e6) for i, _ in enumerate(irrad)]
    data['flux'] = flux
                
    # Add each area slice to the integral
    for i in range(len(photondens) - 1):
        irradavg = (irrad[i] + irrad[i+1]) / 2
        wavelenrange = data['wavelen'][i+1] - data['wavelen'][i]
    
    #Interpolate where the count reaches half its maximum on both sides. The data for the right 
    #side is reversed so that wavelength is increasing and interp likes it
    FWHM = interp(data['count'][:peakidx:-1], data['wavelen'][:peakidx:-1], peakcount/2) - \
           interp(data['count'][:peakidx], data['wavelen'][:peakidx], peakcount/2)
        
    rangeVal = float(2.5)  
    upper = float((FWHM*rangeVal)/2)  # range of 2.5 times FWHM value
   
    upperLimit = float(peakwavelen + upper)
    lowerLimit = float(peakwavelen - upper)
                              
    topIndex = min(enumerate(data['wavelen']),key=lambda x: abs(x[1]-upperLimit))[0]
    bottomIndex = min(enumerate(data['wavelen']),key=lambda x: abs(x[1]-lowerLimit))[0]
    
    # total integrated irradiance    
    totalintIrradList = []
    for i in range (bottomIndex, topIndex +1):
         intirrad = intirradList[i]
         totalintIrradList.append(intirrad)
                   
    totalIntIrrad =sum(totalintIrradList)/1E4
    
    # total photon flux density
    photonFluxList = []
    for i in range (bottomIndex, topIndex +1):
        photonfluxdensity = photondens[i]/(6.022e23/1e6)
        photonFluxList.append(photonfluxdensity)
    
    totalphotonFlux = sum(photonFluxList)   
        
    # Append the data for the summary so we can write it later
    summarydata.append([num, productcode, locationx, locationy, current, peakwavelen, FWHM, lowerLimit, upperLimit, totalIntIrrad, totalphotonFlux])
        
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

# Print peak wavelength, FWHM bandwidth, and integrated photon flux and irradiance
with open(os.path.join('Output', 'Summary.csv'), 'w') as f:
    outfile = csv.writer(f,delimiter=',')
    outfile.writerow(['Device Number', 'Product Code', 'Locationx', 'Locationy', 'Current (mA)', 'Peak Wavelength (nm)', 'FWHM Bandwidth (nm)', 'Lower Integration Limit (nm)', 'Upper Integration Limit (nm)', 'Integrated Irradiance (W/m^2)', 'Photon Flux Density (umol/m^2/s)'])
    for d in summarydata:
        outfile.writerow(d)
