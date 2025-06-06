from tqdm import tqdm

import numpy as np
import numpy.random as rand
import pandas as pd

import os
import sys
sys.path.append("../../../")

from data.data import CollectionAccessor, EmbeddingSpaceAccessor, ImageHandler

from sentence_transformers import SentenceTransformer, util

MKG_DIR = ".."


def embed_texts(texts, model_name, chunk_size=512):
    todo = np.array_split(texts, int(len(texts)/chunk_size))

    # l = len(str(len(todo)))
    
    # model = SentenceTransformer('EMBEDDIA/sloberta')
    # model = SentenceTransformer('all-MiniLM-L6-v2')
    model = SentenceTransformer(model_name)
    
    embs = []
    for i, chunk in tqdm(enumerate(tqdm(todo))):
        cur_embs = model.encode(chunk)
    
        cur_embs = pd.DataFrame(cur_embs, index=chunk.index)
        cur_embs.index.name = mkg.index.name
    
        embs.append(cur_embs)
    
    embs = pd.concat(embs)
    return embs



# import json
# import os.path
# import csv

import imageio.v3 as iio
from PIL import Image
from PIL import ImageFile
ImageFile.LOAD_TRUNCATED_IMAGES = True

import torch
from torch.nn import Module
from transformers import AutoImageProcessor, ViTImageProcessor, ViTMAEModel


class Embedder(Module):
    def __init__(self):
        super(Embedder, self).__init__()
        self.image_processor = AutoImageProcessor.from_pretrained("facebook/vit-mae-base")
        # self.image_processor = ViTImageProcessor(do_resize=False, padding=True)
        self.model = ViTMAEModel.from_pretrained("facebook/vit-mae-base")

    
    def forward(self, images):
        inputs = self.image_processor(images=images, return_tensors="pt")#, padding=True)
        outputs = self.model(**inputs)
        return torch.sum(outputs.last_hidden_state, dim=1).detach().numpy()



def my_resize(image):
    fixed_w = 224
    r = image.height/image.width 
    # .thumbnail DOESN'T RETURN ANYTHING
    image.thumbnail((fixed_w, fixed_w*r))#,Image.ANTIALIAS)

def embed_images_(paths, model_name, chunk_size=64):
    todo = np.array_split(paths, int(len(paths)/chunk_size))

    embedder = Embedder()

    for i, chunk in tqdm(enumerate(todo), total=len(todo)):
        imgs = [Image.open(p).convert("RGB") if p else Image.new(mode="RGB", size=(512,512))
                for p in chunk]

        for i in imgs:
            my_resize(i) #IN-PLACE OPERATION
        
        embs = embedder(imgs)
        yield pd.DataFrame(embs, index=chunk.index)
        

def embed_images(out_dir, paths, model_name, chunk_size=64):
    batches = []
    for i, emb_batch in enumerate(embed_images_(paths, model_name, chunk_size=chunk_size)):
        batches.append(emb_batch)
        emb_batch.to_csv(f"{OUT_DIR}/{model_name}/batch_{i:03}.csv", index=True)
    
    batches = pd.concat(batches)
    return batches


def init_MKG():
    image_folder = MKG_DIR+"/images"
    image_handler = ImageHandler("MKG", image_folder=image_folder, keep_prefix=True)

    # time_stamp, pub_file, priv_file = CollectionAccessor.get_latest_dump("./data/dumps")

    time_stamp = "2025-06-05"
    mkg_meta = dict(name="Museum Kunst & Gewerbe", id_="MKG_"+time_stamp,
                    creation_timestamp=time_stamp, language="de")
    mkg = CollectionAccessor.get_MKG(metadata_path=MKG_DIR+"/dumps/extraction_v0_1.csv",
                                    image_handler=image_handler,
                                    **mkg_meta)
    return image_handler, mkg

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--embed_texts", help="whether to do text embeddings (takes up to an hour)", action="store_true")
    parser.add_argument("--embed_images", help="whether to do image embeddings (takes several hours)", action="store_true")
    parser.add_argument("--images_path", help="path to images")
    parser.add_argument("--do_umap", help="perform UMAP embedding space reduction", action="store_true")
    args = parser.parse_args()
    
    if args.embed_images and (args.images_path is None):
            raise ValueError("Image embedding requires images_path but was not provided!")


    
    OUT_DIR = MKG_DIR+"/generated_data"

    image_handler, mkg = init_MKG()#args.images_path)
    # dmg = dmg.sample(1000)
    
    if args.embed_texts:
        texts = dmg.coll.get_texts()
        model_name = 'distiluse-base-multilingual-cased-v2'
        
        if not os.path.isdir(f"{OUT_DIR}/{model_name}"):
            os.makedirs(f"{OUT_DIR}/{model_name}")
        text_embs = embed_texts(texts, model_name)
        text_embs.to_csv(f"{OUT_DIR}/{model_name}/embeddings.csv", index=True)

        
        if args.do_umap:
            text_embs.emb_space.umap(save_to=f"{OUT_DIR}/{model_name}/embeddings_32D.csv")

    

    if args.embed_images:
        model_name = "vitmae"
        if not os.path.isdir(f"{OUT_DIR}/{model_name}"):
            os.makedirs(f"{OUT_DIR}/{model_name}")

        # paths = dmg.image_path.fillna([])
        # paths = dmg.image_path.apply(lambda ls: ls[0])
        paths = mkg.image_path.fillna("")#.apply(lambda ls: (ls[0] if ls else None))
        # paths = dmg.image_path

        print(list(paths))
        
        img_embs = embed_images(OUT_DIR, paths, model_name, chunk_size=32)
        img_embs.to_csv(f"{OUT_DIR}/{model_name}/embeddings.csv", index=True)
    
        if args.do_umap:
            img_embs.emb_space.umap(save_to=f"{OUT_DIR}/{model_name}/embeddings_32D.csv")

