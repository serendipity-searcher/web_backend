#!/bin/bash

python -m venv "backend_env"

source backend_env/bin/activate

pip install -r requirements.txt


echo "INSTALLING SEARCHER FOR DMG..."

echo "(1 of 3) DOWNLOADING DATA... (this takes up to 30 minutes)"
./data/DOWNLOAD_DATA.sh

exitCode=$?
if [ $exitCode -ne 0 ]; then
    echo "API dump failed! Exiting"
    exit 1
fi

echo "(2 of 3) EXTRACTING & PROCESSING DATA... (this takes a few minutes)"
./data/EXTRACT_DATA.sh


echo "(3 of 3) DOWNLOADING IMAGES... (this takes a few hours)"
echo "NEED TO INSTALL AND SET UP AWS CLI"
echo "BUCKET DETAILS: 
    bucket name: dmg-images-searcher
    region: eu-west-2"
echo "see https://boto3.amazonaws.com/v1/documentation/api/latest/guide/quickstart.html#configuration"
./data/DOWNLOAD_IMAGES.sh


echo "INSTALLING SEARCHER FOR DMG DONE!"
