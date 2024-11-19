#!/usr/bin/python3
# -*- coding: utf-8 -*-

############################################################
# Written by T.HOSHINO @ Takada Laboratory on 2022.07
#
# Environment: Python 3.7.3
#              OS: Raspbian 10.11
#              on Raspberry Pi 4
# 
# Used sensor: SHT35
#              LPS25HB
#              SCD30
#              PVSS-03
# 
# I2Cアドレスの確認コマンド
#     $ i2cdetect -y 1
#
# データ計測時間は　SAMPLING_TIME x TIMES
############################################################

import os
import sys
import datetime
import spidev
import csv
import smbus
import subprocess
import psutil
from scd30_i2c import SCD30
import picamera


# データ計測時間は　SAMPLING_TIME x TIMES
SAMPLING_TIME = 10    # データ取得の時間間隔[sec]
# TIMES = 1000000        # データの計測回数

# I2Cアドレス 設定
SHT_AIR_ADDR = 0x45        # SHT35
LPS25HB_ADDR = 0x5C        # LPS25HB

# Raspberry Pi カメラ 使用フラグ
if len(sys.argv) == 2:
    RASPI_CAMERA = sys.argv[1] == "1"
else:
    print("ERROR: 引数が不足しています")
    sys.exit(1)


# ADコンバータ クラス宣言
class  ADConverter:
    def __init__(self, ref_volts, ch):
        self.ref_volts = ref_volts
        self.spi = spidev.SpiDev()
        self.spi.open(0, 0)
        self.spi.max_speed_hz = 1000000
        self.ch = ch

    def get_voltage(self, ch):
        raw = self.spi.xfer2([((0b1000 + ch) >> 2) + 0b100, ((0b1000 + ch) & 0b0011) << 6, 0])
        raw2 = ((raw[1] & 0b1111) << 8) + raw[2]
        volts = (raw2 * self.ref_volts) / float(4095)
        volts = round(volts, 4)
        return volts

    def Cleanup(self):
        self.spi.close()


# 各機器初期化処理
def device_init():
    # SHT35 初期設定
    i2c = smbus.SMBus(1)
    i2c.write_byte_data(SHT_AIR_ADDR, 0x21, 0x30)

    # LPS25HB 初期設定
    i2c.write_byte_data(LPS25HB_ADDR, 0x20, 0x90)

    # SCD30初期設定
    scd30 = SCD30()
    scd30.set_measurement_interval(2)
    scd30.start_periodic_measurement()
    
    return i2c, scd30

# SHT35 気温データ取得
def tempChanger(msb, lsb):
    mlsb = ((msb << 8) | lsb)
    return (-45 + 175 * int(str(mlsb), 10) / (pow(2, 16) - 1))

# SHT35 湿度データ取得
def humidChanger(msb, lsb):
    mlsb = ((msb << 8) | lsb)
    return (100 * int(str(mlsb), 10) / (pow(2, 16) - 1))

# SCD30 二酸化炭素濃度・温湿度(搭載されているSHT31)
def get_scd30():
    if scd30.get_data_ready():
        m = scd30.read_measurement()
        if m is not None:
            return m

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


if __name__ == '__main__':

    # ADコンバータ準備
    ad_conv = ADConverter(ref_volts=5, ch=0)
    
    # 各機器の初期化
    i2c, scd30 = device_init()
    
    # カメラ撮影タイミング
    camera_cnt = 60

    # データ取得
    while True:
    # for _i in range(TIMES):
        try:
            # 現在時刻の取得
            date = datetime.datetime.now()  #now()メソッドで現在日付・時刻のdatetime型データの変数を取得 世界時：UTCnow
            
            # SHT35 データ取得
            i2c.write_byte_data(SHT_AIR_ADDR, 0xE0, 0x00)
            sht_air_data = i2c.read_i2c_block_data(SHT_AIR_ADDR, 0x00, 6)
            sht_air_temp = tempChanger(sht_air_data[0], sht_air_data[1])
            sht_air_humid = humidChanger(sht_air_data[3], sht_air_data[4])
            
            # LPS25HB データ取得
            lps_val = i2c.read_i2c_block_data(LPS25HB_ADDR, 0x28 | 0x80, 3)
            lps_pres = (lps_val[2] * 65536 + lps_val[1] * 256 + lps_val[0]) / 4096.0
            
            # SCD30 データ取得
            scd_val = get_scd30()
            
            # 日照センサ データ取得
            volts = ad_conv.get_voltage(ch=0)
            volts = float(volts * 1000)
            
            # 標準出力へ表示
            print(date)
            print(f'気温(SHT35)：{sht_air_temp:.4g} ℃')
            print(f'湿度(SHT35)：{sht_air_humid:.4g} %')
            print(f'気圧(LPS25HB)：{lps_pres:.2f} hPa')
            print(f'二酸化炭素濃度(SCD30)：{scd_val[0]:.2f} ppm')
            print(f'温度(SCD30)：{scd_val[1]:.2f} ℃')
            print(f'湿度(SCD30)：{scd_val[2]:.2f} %')
            print(f'日射量：{volts:.2f} W/m2')
            print()
            
            # ファイルへ書出し
            fname     = f'/home/pi/PepperHouse/data/inAir_logs_{date:%Y%m%d}.csv'
            fname_cpu = f'/home/pi/PepperHouse/data/cpu_logs_{date:%Y%m%d}.csv'
            
            with open(fname, 'a') as f:
                writer = csv.writer(f)
                
                # [測定日時,
                #  気温[℃](SHT35), 湿度[%](SHT35),
                #  気圧[hPa](LPS25HB),
                #  二酸化炭素濃度[ppm](SCD30), 気温[℃](SCD30), 湿度[%](SCD30),　
                #  日射量[W/m2]]
                writer.writerow([date.strftime("%Y-%m-%d %H:%M:%S.%f"),
                                 round(sht_air_temp, 2), round(sht_air_humid, 2),
                                 round(lps_pres, 2),
                                 round(scd_val[0], 2), round(scd_val[1], 2), round(scd_val[2], 2),
                                 round(volts, 2)])
            
            with open(fname_cpu, 'a') as f:
                writer = csv.writer(f)
                # [CPU温度, CPU使用率, CPU周波数, ディスク使用率]
                writer.writerow([date.strftime("%Y-%m-%d %H:%M:%S.%f")] + get_CPUinfo())
            
            # Picameraの撮影と保存
            if RASPI_CAMERA and camera_cnt == 60: # 1 time / 10 min
                dname_pic = f'/home/pi/PepperHouse/img/img_{date:%Y%m%d}/'
                fname_pic = dname_pic + f'img_{date:%Y%m%d_%H%M}.jpg'
                
                if not os.path.isdir(dname_pic):
                    os.makedirs(dname_pic)
                
                with picamera.PiCamera() as camera:
                    camera.resolution = (1920, 1080)
                    camera.capture(fname_pic)
                
                camera_cnt = 0
            else:
                camera_cnt += 1
            
            # 指定秒数の一時停止
            while datetime.datetime.now() < date + datetime.timedelta(seconds=SAMPLING_TIME):
                continue
        
        except KeyboardInterrupt:
            break
