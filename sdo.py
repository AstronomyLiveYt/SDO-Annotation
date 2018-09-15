from __future__ import print_function
import ephem
import cv2
import sys
import math
import datetime
import cv2
import numpy as np
from PIL import Image
import pytesseract
import os
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"

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

if len(sys.argv) != 3:
    print('Proper usage: python sdo.py video.mp4 tle.txt ')
    exit()
font = cv2.FONT_HERSHEY_SIMPLEX
observer = ephem.Observer()
observer.pressure = 0
cap = cv2.VideoCapture(str(sys.argv[1]))
fourcc = cv2.VideoWriter_fourcc(*str('WMV1'))
out = cv2.VideoWriter('SDOvideo.wmv',fourcc, 3, (1024,1024))

with open(str(sys.argv[2])) as f:
    lines = [line.rstrip('\n') for line in f]
ret = True
while ret is True:
    ret, vidframe = cap.read()
    if ret is True:
        dateframe = vidframe[980:1012,195:460]
        gray = cv2.cvtColor(dateframe, cv2.COLOR_BGR2GRAY)
        filename = 'temp.png'
        cv2.imwrite(filename, gray)
        text = pytesseract.image_to_string(Image.open(filename))
        print(text, end='\r')
        observer.date = (str(text))
        sun = ephem.Sun(observer)
        sdo = ephem.readtle(lines[0],lines[1],lines[2])
        try:
            sdo.compute(observer)
            observer.lat = sdo.sublat
            observer.lon = sdo.sublong
            observer.elevation = sdo.elevation
            moon = ephem.Moon(observer)
            sun = ephem.Sun(observer)
            moonlon, moonlat, E = equatorial_to_ecliptic(moon.ra, moon.dec, observer)
            sunlon, sunlat, E = equatorial_to_ecliptic(sun.ra, sun.dec, observer)
            separation = ephem.separation((sunlon, sunlat),(moonlon,moonlat))
            sunsize = int(((sun.radius)*180/math.pi)*1506)
            moonsize = int(((moon.radius)*180/math.pi)*1506)
            posangle = position_angle(sunlon, sunlat, moonlon, moonlat)
            moonyangle = (moonlat - sunlat)
            moonxangle = (moonlon - sunlon)*math.cos(moonyangle)
            moonx = int(512-(moonxangle*180/math.pi)*1506)
            moony = int(512-(moonyangle*180/math.pi)*1506)
            img = vidframe
            cv2.circle(img,(512,512), sunsize, (0,0,255), 2)
            cv2.putText(img,'Sun',(460,512), font, 2,(0,0,255),2,cv2.LINE_AA)
            cv2.circle(img, (moonx,moony), moonsize, (255,0,0), 2)
            cv2.putText(img,'Moon',((moonx-74),moony), font, 2,(255,0,0),2,cv2.LINE_AA)
            cv2.putText(img,str(observer.date),(0,50), font, 1,(0,0,255),2,cv2.LINE_AA)
            cv2.imshow('image', img)
            out.write(img)
            cv2.waitKey(1)
        except:
            print('TLE epoch is too far out from detected image date', end='\r')
out.release()
exit()

    
