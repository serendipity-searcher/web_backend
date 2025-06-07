#!/bin/bash

cd ./src

# python dump_MKG_API.py

# python extract_data.py

# python dump_images.py


echo "##################"
echo "################## INNSIDE OF $(pwd)"
echo "##################"
python embed.py --embed_texts --do_umap
python embed.py --do_umap --embed_images --images_path ./images
