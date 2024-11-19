#!/bin/bash

if [ -z $DEVICE ]; then
	echo "環境変数DEVICEが設定されていません"
	exit 1
fi

date=`date +%Y%m%d -d '30 minute ago'`

# 環境データアップロード
src="/home/pi/PepperHouse/data/inAir_logs_${date}.csv"
dst="gd_pepper:/取得データ/Ver2/${DEVICE:0:-1}/$DEVICE"
if [ -e $src ]; then
	rclone copy $src $dst
fi

# CPUデータアップロード
src="/home/pi/PepperHouse/data/cpu_logs_${date}.csv"
dst="gd_pepper:/取得データ/Ver2/${DEVICE:0:-1}/$DEVICE"
if [ -e $src ]; then
	rclone copy $src $dst
fi

# 画像データアップロード
src="/home/pi/PepperHouse/img/img_${date}"
dst="gd_pepper:/取得データ/Ver2/Picture/Picture${DEVICE: -1}/img_${date}"
if [[ $DEVICE = "InsideAir1" && -e $src ]]; then
	rclone copy $src $dst
fi