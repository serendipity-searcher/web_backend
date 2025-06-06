#!/bin/bash

python -m venv "backend_venv"

source backend_venv/bin/activate

pip install -r requirements.txt

cd ./data

datadir=$(pwd)

echo "INSTALLING SEARCHER FOR DMG..."

cd ./DMG

echo "(1 of 3) DOWNLOADING DATA... (this takes up to 30 minutes)"
# ./DOWNLOAD_DATA.sh

exitCode=$?
if [ $exitCode -ne 0 ]; then
    echo "API dump failed! Exiting"
    exit 1
fi

echo "(2 of 3) EXTRACTING & PROCESSING DATA... (this takes a few minutes)"
# ./EXTRACT_DATA.sh


echo "(3 of 3) DOWNLOADING IMAGES... (this takes a few hours)"
echo "NEED TO INSTALL AND SET UP AWS CLI"
echo "BUCKET DETAILS: 
    bucket name: dmg-images-searcher
    region: eu-west-2"
echo "see https://boto3.amazonaws.com/v1/documentation/api/latest/guide/quickstart.html#configuration"
# ./DOWNLOAD_IMAGES.sh


# ./EMBED.sh

echo "INSTALLING SEARCHER FOR DMG DONE!"

cd $datadir

echo "INSTALLING SEARCHER FOR MKG..."

cd ./MKG

./INSTALL_MKG.sh

echo "INSTALLING SEARCHER FOR DMG DONE!"


rm -rf ./backend_venv

