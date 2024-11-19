#!/bin/bash

if [ -z $DEVICE ]; then
	echo "環境変数DEVICEが設定されていません"
	exit 1
fi

path_data="/home/pi/PepperHouse/data"
path_img="/home/pi/PepperHouse/img"

if [ ! -e $path_data ]; then
	mkdir $path_data
fi

if [[ $DEVICE = "InsideAir1" && ! -e $path_img ]]; then
	mkdir $path_img
fi

if [ $DEVICE != "InsideAir1" ]; then
	python3 /home/pi/PepperHouse/inAir.py 0
else
	python3 /home/pi/PepperHouse/inAir.py 1
fi