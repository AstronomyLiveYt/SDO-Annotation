from __future__ import print_function
import ephem
import cv2
import sys
import math
import datetime
import time
import cv2
import numpy as np
from PIL import Image
import pytesseract
import os
import urllib.request as url
import youtubeuploadprediction as ytup

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"

def horizon_to_equatorial(alt, az, lat):
    dec = math.asin(math.sin(alt)*math.sin(lat)+math.cos(alt)*math.cos(lat)*math.cos(az))
    H = math.acos((math.sin(alt)-math.sin(lat)*math.sin(dec))/(math.cos(lat)*math.cos(dec)))
    if math.sin(az)>0:
        H = (360 - (H * 180/math.pi))*(math.pi/180)
    return(dec, H)

def equatorial_to_ecliptic(ra, dec, observer):
    T = get_T(observer)
    E = (23.439291666666666666666666666667 - 0.01300416666666666666666666666667 * T - 0.00000016666666666666666666666666666667 * (T**2) + 0.00000050277777777777777777777777777778 * (T**3))*math.pi/180
    lon = math.atan2((math.sin(ra)*math.cos(E)+math.tan(dec)*math.sin(E)),math.cos(ra))
    lat = math.asin(math.sin(dec)*math.cos(E)-math.cos(dec)*math.sin(E)*math.sin(ra))
    return(lon, lat, E)

def position_angle(alpha1, sigma1, alpha2, sigma2):
    positionangle = math.atan2((math.cos(sigma2)*math.sin(alpha2-alpha1)),
    (math.cos(sigma1)*math.sin(sigma2)-math.sin(sigma1)*math.cos(sigma2)*math.cos(alpha2-alpha1)))
    return(positionangle)

def get_T(observer):
    T = (ephem.julian_date(observer)-2451545)/36525
    return(T)

if len(sys.argv) != 1:
    print('Proper usage: python sdopredictbot.py')
    exit()
    
def predict_positions(start, end, d, observer, line1, line2, line3):
    earthradius = 6371000
    mooneclipse = False
    eartheclipse = False
    timel = []
    sunsizel = [] 
    moonsizel = [] 
    earthsizel = [] 
    moonxl = [] 
    moonyl = [] 
    earthxl = [] 
    earthyl = [] 
    startearth = [] 
    endearth = [] 
    startmoon = [] 
    endmoon = [] 
    eeclipsestart = [] 
    meclipsestart = []
    separationl = []
    moonsizel = []
    sunsizel = []
    earthsunsepl = []
    for t in range(start,end,1):
        observer.date = (d.datetime() + datetime.timedelta(seconds=t))
        timel.append(str(observer.date))
        print(str(observer.date), end='\r')
        sun = ephem.Sun(observer)        
        sdo = ephem.readtle(line1,line2,line3)
        try:
            sdo.compute(observer)
        except:
            print('TLE epoch is too far out from detected image date', end='\r')
        observer.lat = sdo.sublat
        observer.lon = sdo.sublong
        observer.elevation = sdo.elevation
        moon = ephem.Moon(observer)
        sun = ephem.Sun(observer)
        #calculate the ecliptic lon and lat of earth
        siderealtime = observer.sidereal_time()
        earthdec, earthra = horizon_to_equatorial((-89.9999*math.pi/180), (60*math.pi/180), observer.lat)
        #convert what is actually the hour angle to right ascension
        earthra = siderealtime - earthra
        earthlon, earthlat, E = equatorial_to_ecliptic(earthra, earthdec, observer)
        moonlon, moonlat, E = equatorial_to_ecliptic(moon.ra, moon.dec, observer)
        sunlon, sunlat, E = equatorial_to_ecliptic(sun.ra, sun.dec, observer)
        separation = ephem.separation((sunlon, sunlat),(moonlon,moonlat))
        sunsize = int(((sun.radius)*180/math.pi)*1506)
        moonsize = int(((moon.radius)*180/math.pi)*1506)
        earthdist = earthradius + observer.elevation
        earthsunsep = ephem.separation((sunlon, sunlat), (earthlon, earthlat))
        earthappradius = math.asin((earthradius+200000)/earthdist)
        earthsize = int(((earthappradius)*180/math.pi)*1506)
        posangle = position_angle(sunlon, sunlat, moonlon, moonlat)
        moonyangle = (moonlat - sunlat)
        moonxangle = (moonlon - sunlon)*math.cos(moonyangle)
        moonx = int(512-(moonxangle*180/math.pi)*1506)
        moony = int(512-(moonyangle*180/math.pi)*1506)
        earthyangle = (earthlat - sunlat)
        earthxangle = (earthlon - sunlon)*math.cos(earthyangle)
        earthx = int(512-(earthxangle*180/math.pi)*1506)
        earthy = int(512-(earthyangle*180/math.pi)*1506)
        #check if the earth eclipsed the sun
        if earthsunsep < (earthappradius + sun.radius):
            if eartheclipse is False:
                startearth.append(t)
                eeclipsestart.append(str(observer.date)+'\n')
            eartheclipse = True
        elif eartheclipse is True:
            endearth.append(t)
            eartheclipse = False
        if separation < (moon.radius + sun.radius):
            if mooneclipse is False:
                startmoon.append(t)
                meclipsestart.append(str(observer.date)+'\n')
            mooneclipse = True
        elif mooneclipse is True:
            endmoon.append(t)
            mooneclipse = False
        separationl.append(separation)
        earthsunsepl.append(earthsunsep)
        sunsizel.append(sunsize)
        moonsizel.append(moonsize)
        earthsizel.append(earthsize)
        moonxl.append(moonx)
        moonyl.append(moony)
        earthxl.append(earthx)
        earthyl.append(earthy)
        moonsizel.append(moon.radius)
        sunsizel.append(sun.radius)
        earthsizel.append(earthappradius)
    return(timel, sunsizel, moonsizel, earthsizel, moonxl, moonyl, earthxl, earthyl, startearth, endearth, startmoon, endmoon, earthappradius, eeclipsestart, meclipsestart, moonsizel, sunsizel, separationl, earthsunsepl, earthsizel)

earthradius = 6371000    
font = cv2.FONT_HERSHEY_SIMPLEX
observer = ephem.Observer()
observer.pressure = 0
start_time = (time.time() - 86400)
print('Initialization complete.')
while True:
    time.sleep(1)
    elapsed_time = time.time() - start_time
    print('Next prediction in: ', str(int(start_time+86400) - time.time()), end='\r')
    if elapsed_time > 86400:
        print('Wakey, wakey, time to go to work!')
        start_time = time.time()
        timenow = datetime.datetime.utcnow()
        d = ephem.Date(timenow)
        fourcc = cv2.VideoWriter_fourcc(*str('WMV1'))
        #First try to open and load tle from celestrak
        try:
            tle = str(url.urlopen('https://www.celestrak.com/NORAD/elements/science.txt').read().decode("utf-8"))
            tle_file = open('SDOtle.txt', 'w')
            tle_file.write(tle)
            tle_file.close()
            tle = tle.splitlines()
            lines = []
            for line in tle:
                lines.append(line)
            for idx, line in enumerate(lines):
                if "SDO" in line:
                    line1 = line
                    line2 = lines[idx+1]
                    line3 = lines[idx+2]  
                    print(line1)
                    print(line2)
                    print(line3)
        #failing that, try to load tle from existing text file saved from the previous round
        except:
            with open('SDOtle.txt') as f:
                lines = [line.rstrip('\n') for line in f]
            for idx, line in enumerate(lines):
                if "SDO" in line:
                    line1 = line
                    line2 = lines[idx+1]
                    line3 = lines[idx+2]
                    print('Failed to load TLE from Celestrak, using latest TLE file instead!')  
                    print(line1)
                    print(line2)
                    print(line3)
        #initialize all eclipses as not happening, until we detect one
        start = 0
        end = int(86400 * 7)
        timel, sunsizel, moonsizel, earthsizel, moonxl, moonyl, earthxl, earthyl, startearth, endearth, startmoon, endmoon, earthappradius, eeclipsestart, meclipsestart, moonsizel, sunsizel, separationl, earthsunsepl, earthsizel = predict_positions(start, end, d, observer, line1, line2, line3)
        eef_file = []
        mef_file = []
        mooneclipse = False
        eartheclipse = False
        #load previous earth and moon eclipses to compare later and make sure this isn't a repeat
        with open('eeclipselist.txt') as g:
            eef_file.append([line.rstrip('\n') for line in g])
        with open('meclipselist.txt') as h:
            mef_file.append([line.rstrip('\n') for line in h])
        if len(startearth) > 0:
            for e in range(0, len(startearth), 1):
                out = cv2.VideoWriter('SDOpredictvideo.wmv',fourcc, 60, (1024,1024))
                for t in range(int(startearth[e]),int(endearth[e]),1):
                    observer.date = timel[t]
                    sdo = ephem.readtle(line1,line2,line3)
                    try:
                        sdo.compute(observer)
                    except:
                        print('TLE epoch is too far out from detected image date', end='\r')
                    observer.lat = sdo.sublat
                    observer.lon = sdo.sublong
                    observer.elevation = sdo.elevation
                    moon = ephem.Moon(observer)
                    sun = ephem.Sun(observer)
                    #calculate the ecliptic lon and lat of earth
                    siderealtime = observer.sidereal_time()
                    earthdec, earthra = horizon_to_equatorial((-89.9999*math.pi/180), (60*math.pi/180), observer.lat)
                    #convert what is actually the hour angle to right ascension
                    earthra = siderealtime - earthra
                    earthlon, earthlat, E = equatorial_to_ecliptic(earthra, earthdec, observer)
                    moonlon, moonlat, E = equatorial_to_ecliptic(moon.ra, moon.dec, observer)
                    sunlon, sunlat, E = equatorial_to_ecliptic(sun.ra, sun.dec, observer)
                    separation = ephem.separation((sunlon, sunlat),(moonlon,moonlat))
                    sunsize = int(((sun.radius)*180/math.pi)*1506)
                    moonsize = int(((moon.radius)*180/math.pi)*1506)
                    earthdist = earthradius + observer.elevation
                    earthsunsep = ephem.separation((sunlon, sunlat), (earthlon, earthlat))
                    earthappradius = math.asin((earthradius+200000)/earthdist)
                    earthsize = int(((earthappradius)*180/math.pi)*1506)
                    posangle = position_angle(sunlon, sunlat, moonlon, moonlat)
                    moonyangle = (moonlat - sunlat)
                    moonxangle = (moonlon - sunlon)*math.cos(moonyangle)
                    moonx = int(512-(moonxangle*180/math.pi)*1506)
                    moony = int(512-(moonyangle*180/math.pi)*1506)
                    earthyangle = (earthlat - sunlat)
                    earthxangle = (earthlon - sunlon)*math.cos(earthyangle)
                    earthx = int(512-(earthxangle*180/math.pi)*1506)
                    earthy = int(512-(earthyangle*180/math.pi)*1506)
                    img = np.zeros((1024,1024,3), np.uint8)
                    img[:,:] = (255, 255, 255)
                    cv2.circle(img,(512,512), sunsize, (0,0,255), 2)
                    cv2.putText(img,'Sun',(460,512), font, 2,(0,0,255),2,cv2.LINE_AA)
                    cv2.circle(img, (moonx,moony), moonsize, (255,0,0), 2)
                    cv2.circle(img, (earthx,earthy), earthsize, (0, 255,0), 2)
                    if earthsunsepl[t] < (earthsizel[t] + sun.radius):
                        eartheclipse = True
                        for line in eef_file:
                            for l in line:
                                S = ephem.Date(str(eeclipsestart[e]).rstrip('\n'))
                                S1 = (S.datetime() - datetime.timedelta(seconds=30))
                                S2 = (S.datetime() + datetime.timedelta(seconds=30))
                                P = ephem.Date(l)
                                if S1 <= P.datetime() <= S2:
                                    eartheclipse = False
                        cv2.putText(img,'Earth Eclipsing Sun',(200,100), font, 2,(0,255,0),2,cv2.LINE_AA)
                    cv2.putText(img,'Moon',((moonx-74),moony), font, 2,(255,0,0),2,cv2.LINE_AA)
                    #check if the moon eclipsed the sun
                    cv2.putText(img,str(observer.date),(0,50), font, 1,(0,0,255),2,cv2.LINE_AA)
                    #cv2.imshow('image', img)
                    out.write(img)
                    #cv2.waitKey(1)
                #Keep trying to uploaded the video until you succeed
                videouploaded = False
                if eartheclipse is True:
                    eartheclipse = False
                    print('Detected New Eclipse!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
                    while videouploaded is False:
                        try:
                            ytup.initialize_upload("SDOpredictvideo.wmv", str('Earth Eclipse Predicted to Start at ' + str(eeclipsestart[e])))
                            videouploaded = True
                        except:
                            videouploaded = False
                            print("Upload to YouTube failed!", end='\r')
                            time.sleep(60)
                out.release()
        if len(startmoon) > 0:
            for e in range(0, len(startmoon), 1):
                out = cv2.VideoWriter('SDOpredictvideo.wmv',fourcc, 60, (1024,1024))
                for t in range(int(startmoon[e]),int(endmoon[e]),1):
                    observer.date = timel[t]
                    sdo = ephem.readtle(line1,line2,line3)
                    try:
                        sdo.compute(observer)
                    except:
                        print('TLE epoch is too far out from detected image date', end='\r')
                    observer.lat = sdo.sublat
                    observer.lon = sdo.sublong
                    observer.elevation = sdo.elevation
                    moon = ephem.Moon(observer)
                    sun = ephem.Sun(observer)
                    #calculate the ecliptic lon and lat of earth
                    siderealtime = observer.sidereal_time()
                    earthdec, earthra = horizon_to_equatorial((-89.9999*math.pi/180), (60*math.pi/180), observer.lat)
                    #convert what is actually the hour angle to right ascension
                    earthra = siderealtime - earthra
                    earthlon, earthlat, E = equatorial_to_ecliptic(earthra, earthdec, observer)
                    moonlon, moonlat, E = equatorial_to_ecliptic(moon.ra, moon.dec, observer)
                    sunlon, sunlat, E = equatorial_to_ecliptic(sun.ra, sun.dec, observer)
                    separation = ephem.separation((sunlon, sunlat),(moonlon,moonlat))
                    sunsize = int(((sun.radius)*180/math.pi)*1506)
                    moonsize = int(((moon.radius)*180/math.pi)*1506)
                    earthdist = earthradius + observer.elevation
                    earthsunsep = ephem.separation((sunlon, sunlat), (earthlon, earthlat))
                    earthappradius = math.asin((earthradius+200000)/earthdist)
                    earthsize = int(((earthappradius)*180/math.pi)*1506)
                    posangle = position_angle(sunlon, sunlat, moonlon, moonlat)
                    moonyangle = (moonlat - sunlat)
                    moonxangle = (moonlon - sunlon)*math.cos(moonyangle)
                    moonx = int(512-(moonxangle*180/math.pi)*1506)
                    moony = int(512-(moonyangle*180/math.pi)*1506)
                    earthyangle = (earthlat - sunlat)
                    earthxangle = (earthlon - sunlon)*math.cos(earthyangle)
                    earthx = int(512-(earthxangle*180/math.pi)*1506)
                    earthy = int(512-(earthyangle*180/math.pi)*1506)
                    img = np.zeros((1024,1024,3), np.uint8)
                    img[:,:] = (255, 255, 255)
                    cv2.circle(img,(512,512), sunsize, (0,0,255), 2)
                    cv2.putText(img,'Sun',(460,512), font, 2,(0,0,255),2,cv2.LINE_AA)
                    cv2.circle(img, (moonx,moony), moonsize, (255,0,0), 2)
                    cv2.circle(img, (earthx,earthy), earthsize, (0, 255,0), 2)
                    if separationl[t] < (moon.radius + sun.radius):
                        mooneclipse = True
                        for line in mef_file:
                            for l in line:
                                S = ephem.Date(str(meclipsestart[e]).rstrip('\n'))
                                S1 = (S.datetime() - datetime.timedelta(seconds=30))
                                S2 = (S.datetime() + datetime.timedelta(seconds=30))
                                P = ephem.Date(l)
                                if S1 <= P.datetime() <= S2:
                                    mooneclipse = False
                    cv2.putText(img,'Moon',((moonx-74),moony), font, 2,(255,0,0),2,cv2.LINE_AA)
                    #check if the moon eclipsed the sun
                    cv2.putText(img,str(observer.date),(0,50), font, 1,(0,0,255),2,cv2.LINE_AA)
                    #cv2.imshow('image', img)
                    out.write(img)
                    #cv2.waitKey(1)
                #Keep trying to uploaded the video until you succeed
                videouploaded = False
                if mooneclipse is True:
                    mooneclipse = False
                    print('Detected New Eclipse!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
                    while videouploaded is False:
                        try:
                            ytup.initialize_upload("SDOpredictvideo.wmv", str('Moon Eclipse Predicted to Start at ' + str(meclipsestart[e])))
                            videouploaded = True
                        except:
                            videouploaded = False
                            print("Upload to YouTube failed!", end='\r')
                            time.sleep(60)
                out.release()
        eef = open('eeclipselist.txt', 'a')
        for e in eeclipsestart:
            eef.write(e)
        eef.close()
        mef = open('meclipselist.txt', 'a')
        for e in meclipsestart:
            mef.write(e)
        mef.close()

exit()
    
