from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from os.path import exists
#src: https://github.com/space-physics/wmm2020
#This is the same model used by NOAA
import wmm2020
from skyfield.api import load
import pytz

data = pd.read_csv('data.csv')

#Get the time (in ns) when the experiment started
t0  = data['time'].iloc[0]

#Convert the entire data colommn to hours relativelly to t0
#Used for the first look at the data
#data['time'] = (data['time'] - t0) / 3600 * 1e-9

#Download the Word Magnetic Model 2020 from NOAA or use the local version if available
if exists('model.npy'):
    model = np.load('model.npy')
else:
    model = []
    glat, glon, alt_km = data['lat'], data['long'], data['elev']
    for (lat, lon, alt) in zip(glat, glon, alt_km):
        point = wmm2020.wmm_point(lat, lon, alt, 2020)
        xyz = (point['north'], point['east'], point['down'])
        model.append(xyz)
    model = np.array(model)
    np.save('model.npy', model)


#Compute the magnetic intensity modulus from the x, y, z components of the vector
data['abs_mag'] = (data['magnet_x']**2 + data['magnet_y']**2 + data['magnet_z']**2)**0.5

model = model * 1e-3 #convert from nT to uT

#Read the ISS TLE data from web
stations_url = 'http://celestrak.com/NORAD/elements/stations.txt'
satellites = load.tle_file(stations_url)
by_name = {sat.name: sat for sat in satellites}


#Load the ISS and Sun data into objects and create an object for time
eph = load('de421.bsp')
iss = by_name['ISS (ZARYA)']
ts = load.timescale()

#Create arrays for every graph we need to plot
mlat = []
mlong = []
daylat = []
daylong = []
nightlat = []
nightlong = []
daylatdif = []
daylongdif = []
nightlatdif = []
nightlongdif = []

for ti, ab, m, lat, long in zip(data["time"], data["abs_mag"], model, data['lat'], data['long']):

    #Convert time from nanoseconds to datetime type
    t = datetime.fromtimestamp(ti / 1e9, pytz.UTC)

    #Find out wether or not the ISS is in the Earth's shadow
    sunlit = iss.at(ts.from_datetime(t)).is_sunlit(eph)

    #Calculete the magnetic intensity and difference
    m_ab = (m[0]**2 + m[1]**2 + m[2]**2)**0.5
    dif = m_ab - ab

    if sunlit:
        #Compute the data during daylight
        sample = (dif, lat)
        daylatdif.append(sample)
        sample = (dif, long)
        daylongdif.append(sample)

        sample = (ab, lat)
        daylat.append(sample)
        sample = (ab, long)
        daylong.append(sample)
    else:
        #Compute the data during night
        sample = (dif, lat)
        nightlatdif.append(sample)
        sample = (dif, long)
        nightlongdif.append(sample)

        sample = (ab, lat)
        nightlat.append(sample)
        sample = (ab, long)
        nightlong.append(sample)
    
    #Save the model to be used for reference in the graphs
    sample = (m_ab, lat)
    mlat.append(sample)
    sample = (m_ab, long)
    mlong.append(sample)


col = ['#ff5400', '#390099', '#cef740']
figure, axis = plt.subplots(4)

y, x = zip(*daylat)
axis[0].scatter(x,y, color=col[0], s=1, label="Daylight mesurements")
y, x = zip(*nightlat)
axis[0].scatter(x,y, color=col[1], s=1, label="Nighttime mesurements")
y, x = zip(*mlat)
axis[0].scatter(x,y, color=col[2], s=1, label="Word magnetic model")
axis[0].set_title("Magnetic field intesity as a function of latitude")
axis[0].set_xlabel("Latitude(degrees)")
axis[0].set_ylabel("Magnetic field intesity(µT)")
axis[0].legend()
axis[0].grid(True)

y, x = zip(*daylong)
axis[1].scatter(x,y, color=col[0], s=1, label="Daylight mesurements")
y, x = zip(*nightlong)
axis[1].scatter(x,y, color=col[1], s=1, label="Nighttime mesurements")
y, x = zip(*mlong)
axis[1].scatter(x,y, color=col[2], s=1, label="Word magnetic model")
axis[1].set_title("Magnetic field intesity as a function of longitude")
axis[1].set_xlabel("Longitude(degrees)")
axis[1].set_ylabel("Magnetic field intesity(µT)")
axis[1].legend()
axis[1].grid(True)
  
y, x = zip(*daylatdif)
axis[2].scatter(x,y, color=col[0], s=1, label="Daylight difference")
y, x = zip(*nightlatdif)
axis[2].scatter(x,y, color=col[1], s=1, label="Nighttime difference")
axis[2].set_title("Absolute difference between the model and current mesurements as a function of latitude")
axis[2].set_xlabel("Latitude(degrees)")
axis[2].set_ylabel("Magnetic field intesity(µT)")
axis[2].legend()
axis[2].grid(True)
  
y, x = zip(*daylongdif)
axis[3].scatter(x,y, color=col[0], s=1, label="Daylight difference")
y, x = zip(*nightlongdif)
axis[3].scatter(x,y, color=col[1], s=1, label="Nighttime difference")
axis[3].set_title("Absolute difference between the model and current mesurements as a function of longitude")
axis[3].set_xlabel("Longitude(degrees)")
axis[3].set_ylabel("Magnetic field intesity(µT)")
axis[3].legend()
axis[3].grid(True)


plt.show()