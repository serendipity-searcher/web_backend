#!/bin/bash

cd ./src/

# source ~/home2-env/bin/activate
# PYTHON3_VENV_PATH=$(which python3)


# sudo $PYTHON3_VENV_PATH dump_from_S3bucket.py --save_path /mnt/DMG/ --confirmed


# python dump_from_S3bucket.py --save_path "../images_mnt/DMG/" --confirmed

python dump_from_S3bucket.py --confirmed
