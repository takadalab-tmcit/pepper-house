#!/bin/bash

if [ -z $DEVICE ]; then
	echo "環境変数DEVICEが設定されていません"
	exit 1
fi

# 環境・CPUデータ同期
src="/home/pi/PepperHouse/data"
dst="gd_pepper:/取得データ/Ver2/${DEVICE:0:-1}/$DEVICE"
rclone sync $src $dst

# 画像データアップロード
if [[ $DEVICE = "InsideAir1" && -e $src ]]; then
	src="/home/pi/PepperHouse/img"
	dst="gd_pepper:/取得データ/Ver2/Picture/Picture${DEVICE: -1}"
	rclone sync $src $dst
fi