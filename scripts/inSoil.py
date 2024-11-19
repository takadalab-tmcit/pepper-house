#!/usr/bin/python3
# -*- coding: utf-8 -*-

###########################################################
# Written by T.HOSHINO @ Takada Laboratory on 2022.07
#
# Environment: Python 3.7.3
#              OS: Raspbian 10.11
#              on Raspberry Pi Zero 2 W
# 
# Used sensor: SHT35
#              SEN0114
#              SEN0193
# 
# Value are not calibrated.
#
# SEN0114 value range from detasheet:
#   DRY SOIL    000 - 300
#   HUMID SOIL  300 - 700
#   IN WATER    700 - 950
#
# SEN0193 value range from detasheet:
#   DRY    520 - 430
#   WET    430 - 350
#   WATER  350 - 260
###########################################################

import time
import datetime
import csv
import smbus
import subprocess
import psutil
import RPi.GPIO as GPIO
from gpiozero import MCP3208


# SHT35のI2Cアドレス
SHT_ADDR = 0x44

# データ計測間隔[sec]
SAMPLING_TIME = 10

# PINの定義
SPICLK = 11
SPIMOSI = 10
SPIMISO = 9
SPICS = 8


# SHT35 気温データ取得
def tempChanger(msb, lsb):
    mlsb = ((msb << 8) | lsb)
    return (-45 + 175 * int(str(mlsb), 10) / (pow(2, 16) - 1))

# SHT35 湿度データ取得
def humidChanger(msb, lsb):
    mlsb = ((msb << 8) | lsb)
    return (100 * int(str(mlsb), 10) / (pow(2, 16) - 1))

# CPU情報取得
def get_CPUinfo():
    cpu_temp = subprocess.run('vcgencmd measure_temp', shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True).stdout[5:-3]
    cpu_clck = subprocess.run('vcgencmd measure_clock arm', shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True).stdout.split('=')[1].replace('\n', '')
    disk = str(psutil.disk_usage('/').percent)
    
    cpu_info = subprocess.run('cat /proc/stat | grep -m1 cpu', shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True).stdout.split()
    busy = sum(map(int, cpu_info[1:4]))
    idle = int(cpu_info[4])
    cpu_rate = str(round(busy / (busy + idle) * 100, 2))
    
    return [cpu_temp, cpu_rate, cpu_clck, disk]

# SPI通信用の入出力を定義
def set_gpio():
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(SPICLK, GPIO.OUT)
    GPIO.setup(SPIMOSI, GPIO.OUT)
    GPIO.setup(SPIMISO, GPIO.IN)
    GPIO.setup(SPICS, GPIO.OUT)

# MCP3208のディジタル値を取得
def readADconv(ch):
    GPIO.output(SPICS, GPIO.HIGH)
    GPIO.output(SPICLK, GPIO.LOW)
    GPIO.output(SPICS, GPIO.LOW)
 
    commandout = ch
    commandout |= 0x18  # スタートビット＋シングルエンドビット
    commandout <<= 3    # LSBから8ビット目を送信するようにする
    
    for i in range(5):
        # LSBから数えて8ビット目から4ビット目までを送信
        if commandout & 0x80:
            GPIO.output(SPIMOSI, GPIO.HIGH)
        else:
            GPIO.output(SPIMOSI, GPIO.LOW)
        commandout <<= 1
        GPIO.output(SPICLK, GPIO.HIGH)
        GPIO.output(SPICLK, GPIO.LOW)
    adcout = 0
    
    # 13ビット読む（ヌルビット＋12ビットデータ）
    for i in range(13):
        GPIO.output(SPICLK, GPIO.HIGH)
        GPIO.output(SPICLK, GPIO.LOW)
        adcout <<= 1
        if i > 0 and GPIO.input(SPIMISO) == GPIO.HIGH:
            adcout |= 0x1
    GPIO.output(SPICS, GPIO.HIGH)
    
    return adcout


if __name__ == '__main__':
    
    # SHT35初期化処理
    i2c = smbus.SMBus(1)
    i2c.write_byte_data(SHT_ADDR, 0x21, 0x30)
    
    # SPI通信用の入出力を定義
#     set_gpio()
    
    # Remote I/O error 防止
    time.sleep(0.5)
    
    
    # データ取得
    while True:
        try:
            # 現在時刻の取得
            date = datetime.datetime.now()
            date_str = date.strftime("%Y-%m-%d %H:%M:%S.%f")
            
            # SHT35 データ取得
            i2c.write_byte_data(SHT_ADDR, 0xE0, 0x00)
            sht35 = i2c.read_i2c_block_data(SHT_ADDR, 0x00, 6)
            sht35_temp = round(tempChanger(sht35[0], sht35[1]), 2)
            sht35_hum  = round(humidChanger(sht35[3], sht35[4]), 2)
            
            # SEN0114, SEN0193 データ取得
#             sen0114_hum = readADconv(ch=0)
#             sen0193_hum = readADconv(ch=1)
            
            # SEN0114, SEN0193 データ取得
            sen0114 = MCP3208(channel=0, max_voltage=3.3)
            sen0193 = MCP3208(channel=1, max_voltage=3.3)
            sen0114_hum = round(sen0114.value * 100, 5)
            sen0193_hum = round(sen0193.value * 100, 5)
            
            # 標準出力へ表示
            print(date)
            print(f'  SHT35(temp): {sht35_temp} [℃]')
            print(f'  SHT35(hum) : {sht35_hum} [%]')
            print(f'  SEN0114    : {sen0114_hum}')
            print(f'  SEN0193    : {sen0193_hum}')
            print()
            
            # ファイルへ書出し
            fname     = f'/home/pi/PepperHouse/data/inSoil_logs_{date:%Y%m%d}.csv'
            fname_cpu = f'/home/pi/PepperHouse/data/cpu_logs_{date:%Y%m%d}.csv'
            
            with open(fname, 'a') as f:
                writer = csv.writer(f)
                # [取得日時, SHT35:気温[℃], SHT35:湿度[%], SEN0114, SEN0193]
                writer.writerow([date_str, sht35_temp, sht35_hum, sen0114_hum, sen0193_hum])
            
            with open(fname_cpu, 'a') as f:
                writer = csv.writer(f)
                # [CPU温度, CPU使用率, CPU周波数, ディスク使用率]
                writer.writerow([date_str] + get_CPUinfo())
            
            # 指定秒数の一時停止
            while datetime.datetime.now() < date + datetime.timedelta(seconds=SAMPLING_TIME):
                continue
            
        except KeyboardInterrupt:
            GPIO.cleanup()
            break