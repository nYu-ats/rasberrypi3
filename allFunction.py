import RPi.GPIO as GPIO
import requests
import urllib
import http.client
import json
from linebot import LineBotApi
from linebot.models import ImageSendMessage
from linebot.models import LocationSendMessage
import smbus
import math
from time import time,sleep
from oauth2client.service_account import ServiceAccountCredentials
import gspread

'''GPIO_SET'''
BUTTON=25
GPIO.setmode(GPIO.BCM)
GPIO.setup(BUTTON,GPIO.IN,pull_up_down=GPIO.PUD_DOWN)

'''I2C_SET'''
DEV_ADDR=0x68
ACCEL_XOUT=0x3b
ACCEL_YOUT=0x3d
ACCEL_ZOUT=0x3f
TEMP_OUT=0x41
GYRO_XOUT=0x43
GYRO_YOUT=0x45
GYRO_ZOUT=0x47
PWR_MGMT_1=0x6b
PWR_MGMT_2=0x6c

bus=smbus.SMBus(1)
bus.write_byte_data(DEV_ADDR,PWR_MGMT_1,0)

'''WORD_LIST_DICT'''
keyword_list=["May~October",
              "May~September",
              "August~September",
              "May~November",
              "April~June",
              "Always"]
threewords_dict={"May~October":"sea cloouds terrace",
                 "May~September":"twelve lake pond",
                 "August~September":"yellow knife aurora",
                 "May~November":"hill christ rio",
                 "April~June":"angelo michel sculpture",
                 "Always":"cute cat baby"}

'''SENSOR_FUNC_DEF'''
def read_byte(adr):
    return bus.read_byte_data(DEV_ADDR,adr)

def read_word(adr):
    high=bus.read_byte_data(DEV_ADDR,adr)
    low=bus.read_byte_data(DEV_ADDR,adr+1)
    val=(high<<8)+low
    return val

def read_word_sensor(adr):
    val=read_word(adr)
    if(val>=0x8000):
        return -((65535-val)+1)
    else:
        return val

def get_yaw_data_lsb():
    z=read_word_sensor(GYRO_ZOUT)
    return z

def get_yaw_data_deg():
    z=get_yaw_data_lsb()
    z=z/131.0
    return z

def get_accel_data_lsb():
    x=read_word_sensor(ACCEL_XOUT)
    y=read_word_sensor(ACCEL_YOUT)
    z=read_word_sensor(ACCEL_ZOUT)
    return[x,y,z]

def get_accel_data_g():
    x,y,z=get_accel_data_lsb()
    x=x/16384.0
    y=y/16384.0
    z=z/16384.0
    return[x,y,z]

def calc_slope_for_accel_3axis_deg(x,y,z):
    try:
        theta=math.atan(math.sqrt(x*x+y*y)/z)
    except ZeroDivisionError:
        if(x<0):
            theta=90.0
        elif(x>0):
            theta=-90.0

    deg_theta=math.degrees(theta)
    return deg_theta

'''API_FUNC'''
def main1(ido,keido,map_title,map_threewords):
    messages=LocationSendMessage(
    title=map_title,
    address=map_threewords,
    latitude=ido,
    longitude=keido
    )
    line_bot_api.push_message(user_id,messages=messages)

def get_headers(subscriptionKey):
    return{"Ocp-Apim-Subscription-Key" : subscriptionKey}

def get_params(searchTerm,required_image_num):
    return{"q":searchTerm,
           "license":"ALL",
           "imageType":"photo",
           "count":required_image_num,
           "mkt":"ja-JP"}

def get_images_url_list(search_url,headers,params):
    response=requests.get(search_url,headers=headers,params=params)
    search_results=response.json()
    return [image["contentUrl"] for image in search_results["value"]]

def send_googlespreadsheet(keido_value,ido_value):
    scope=["https://spreadsheets.google.com/feeds","https://www.googleapis.com/auth/drive"]
    json_file=""
    credentials=ServiceAccountCredentials.from_json_keyfile_name(json_file,scopes=scope)
    gc=gspread.authorize(credentials)
    wks=gc.open("gyrocalc").sheet1
    values=wks.get_all_values()
    lastrow=len(values)
    insert_row=lastrow+1
    insert_cell_keido="A"+str(insert_row)
    insert_cell_ido="B"+str(insert_row)
    wks.update_acell(insert_cell_keido,str(keido_value))
    wks.update_acell(insert_cell_ido,str(ido_value))

'''BUTTON_PUSHED'''
def button_pushed(channel):
    ido=theta
    keido=yaw
    if(ido>0):
        ido=90-ido
    elif(ido<0):
        ido=-90-ido
    print("ok")
    print()
    keido_num=keido
    ido_num=ido
    
    map_title=""
    map_threewords=""
    if((40.0<=ido<=50.0)and(140.0<=keido<=155.0)):
        map_title=keyword_list[0]
        map_threewords=threewords_dict[map_title]
    elif((25.0<=ido<=45.0)and(120.0<=keido<=140.0)):
        map_title=keyword_list[1]
        map_threewords=threewords_dict[map_title]
    elif((50.0<=ido<=70.0)and(-120.0<=keido<=-110.0)):
        map_title=keyword_list[2]
        map_threewords=threewords_dict[map_title]
    elif((-30.0<=ido<=-10.5)and(-55.0<=keido<=-35.0)):
        map_title=keyword_list[3]
        map_threewords=threewords_dict[map_title]
    elif((30.0<=ido<=50.0)and(0.0<=keido<=25.0)):
        map_title=keyword_list[4]
        map_threewords=threewords_dict[map_title]
    else:
        map_title=keyword_list[5]
        map_threewords=threewords_dict[map_title]

    main1(ido,keido,map_title,map_threewords)

    ACCESS_TOKEN_BING_KEY=""
    search_url="https://api.cognitive.microsoft.com/bing/v7.0/images/search"
    subscriptionKey=ACCESS_TOKEN_BING_KEY
    searchTerm=map_threewords
    required_image_num=3
    headers=get_headers(subscriptionKey)
    params=get_params(searchTerm,required_image_num)
    images_url=get_images_url_list(search_url,headers,params)
    for i in images_url:
        content_url=i

        content_url_list=list(content_url)

        if(content_url_list[4]!="s"):
            content_url_list.insert(4,"s")

        content_url="".join(content_url_list)
        preview_url="".join(content_url_list)
        messages=ImageSendMessage(original_content_url=content_url,
                                     preview_image_url=preview_url)
        line_bot_api.push_message(user_id,messages=messages)
    send_googlespreadsheet(keido_num,ido_num)

'''MAIN_LOOP'''
LINE_CANNEL_TOKEN=""

line_bot_api=LineBotApi(LINE_CANNEL_TOKEN)
user_id=""
GPIO.add_event_detect(BUTTON,GPIO.RISING,callback=button_pushed,bouncetime=100)
theta=0
yaw=0
slope_xy=0
count=0
try:
    while(1):
        start=time()
        dt=0
        count+=1
        gyro_z=get_yaw_data_deg()
        accel_x3,accel_y3,accel_z3=get_accel_data_g()
        theta=calc_slope_for_accel_3axis_deg(accel_x3,accel_y3,accel_z3)
        if((gyro_z>2.0)or(gyro_z<-2.0)):
            dt=time()-start
            yaw+=(-gyro_z)*dt
        if((-90.05<theta<-89.95)or(89.95<theta<90.05)):
            try:
                slope_xy=math.atan(accel_x3/accel_y3)
                slope_xy=math.degrees(slope_xy)
                
            except ZeroDivisionError:
                if(accel_x3<0):
                    slope_xy=90.0
                if(accel_x3>0):
                    slope_xy=-90.0
            if((accel_x3<=0)and(accel_y3>0)):
                yaw=-slope_xy
            if((accel_x3<0)and(accel_y3<0)):
                yaw=180-slope_xy
            if((accel_x3>=0)and(accel_y3<0)):
                yaw=--180+(-slope_xy)
            if((accel_x3>0)and(accel_y3>0)):
                yaw=-slope_xy
        if(yaw>180):
            yaw=-180+yaw%180
        elif(yaw<-180):
            yaw=180-(-yaw)%180
        if(-12<theta<12):
            if((accel_y3<0)and(-90<yaw<90)):
                yaw+=180
            elif((accel_y3>0)and((-180<=yaw<-90)or(90<yaw<=180))):
                yaw-=180
        if(count==500):
            print("keido:%f"%yaw)
            if(theta>0):
                print("ido:%f"%(90-theta))
            elif(theta<0):
                print("ido:%f"%(-90-theta))
            count=0
            print()
            
except KeyboardInterrupt:
    print("stop.")

GPIO.remove_event_detect(BUTTON)
GPIO.cleanup()