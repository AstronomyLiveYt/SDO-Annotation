from __future__ import print_function
import ephem
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
import youtubeuploadannotation as ytup

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
    print('Proper usage: python sdoytbot.py')
    exit()

earthradius = 6371000
font = cv2.FONT_HERSHEY_SIMPLEX
observer = ephem.Observer()
observer.pressure = 0
start_time = (time.time() - 86400)
print('Initialization complete.')
while True:
    time.sleep(1)
    elapsed_time = time.time() - start_time
    print('Next annotation in: ', str((start_time+86400) - time.time()), end='\r')
    if elapsed_time > 86400:
        print('Wakey, wakey, time to go to work!')
        start_time = time.time()
        try:
            cap = cv2.VideoCapture('https://sdo.gsfc.nasa.gov/assets/img/latest/mpeg/latest_1024_0171_synoptic.mp4')
        except:
            print('Failed to load SDO video, trying again!', end='\r')
            continue
        fourcc = cv2.VideoWriter_fourcc(*str('WMV1'))
        out = cv2.VideoWriter('SDOvideo.wmv',fourcc, 30, (1024,1024))
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
        ret = True
        firstframe = True
        firstframetime = ''
        #Remember what minute it is right now to make sure to properly check later if tesseract has skipped 20 minutes or not.
        now = datetime.datetime.now()
        textminutelast = int(now.minute)
        while ret is True:
            try:
                ret, vidframe = cap.read()
            except:
                print('Problem reading video frame, skipping frame.')
                continue
            if ret is True:
                dateframe = vidframe[980:1012,195:460]
                gray = cv2.cvtColor(dateframe, cv2.COLOR_BGR2GRAY)
                filename = 'temp.png'
                cv2.imwrite(filename, gray)
                text = pytesseract.image_to_string(Image.open(filename))
                try:
                    #check to see if tesseract confused 30's minutes for 50's minutes like it seems to do and fix if so.
                    textminute = text.split(':')
                    if int(textminutelast) < 40 and int(textminute[1]) > 49:
                        textminute[1] = str(int(textminute[1]) - 20)
                        text = ":".join(textminute)
                    #remember what minute it was on this round to check next round if it jumped 20 minutes
                    textminutelast = textminute[1]
                    print(text, end='\r')
                    observer.date = (str(text))
                    if firstframe is True:
                        firstframe = False
                        firstframetime = str(text)
                except:
                    print('Tesseract did not read the date correctly')
                    print(text)
                    continue
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
                img = vidframe
                cv2.circle(img,(512,512), sunsize, (0,0,255), 2)
                cv2.putText(img,'Sun',(460,512), font, 2,(0,0,255),2,cv2.LINE_AA)
                cv2.circle(img, (moonx,moony), moonsize, (255,0,0), 2)
                cv2.circle(img, (earthx,earthy), earthsize, (0, 255,0), 2)
                cv2.putText(img,'Moon',((moonx-74),moony), font, 2,(255,0,0),2,cv2.LINE_AA)
                cv2.putText(img,str(observer.date),(0,50), font, 1,(0,0,255),2,cv2.LINE_AA)
                if earthsunsep < (earthappradius + sun.radius):
                    cv2.putText(img,'Earth Eclipsing Sun',(200,100), font, 2,(0,255,0),2,cv2.LINE_AA)
                #cv2.imshow('image', img)
                out.write(img)
                #cv2.waitKey(1)
        out.release()
        #Keep trying to uploaded the video until you succeed
        videouploaded = False
        while videouploaded is False:
            try:
                ytup.initialize_upload("SDOvideo.wmv", firstframetime)
                videouploaded = True
            except:
                videouploaded = False
                print("Upload to YouTube failed, trying again!", end='\r')
                time.sleep(60)
exit()

    
