#!/bin/bash

# printf -v date '%(%Y-%m-%d %H:%M:%S)T\n' -1
# +%F is shortcut for YYYY-MM-DD
today=$(date +%F)
data_dir="./dumps"


python ./src/extract_data.py --file "$data_dir/API_dump_public_$today.json" --is_public

python ./src/extract_data.py --file "$data_dir/API_dump_private_$today.json"
