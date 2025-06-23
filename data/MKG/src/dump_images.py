from tqdm import tqdm 

import requests as req
import pandas as pd
from time import sleep
import os

BASE_DIR = "../dumps"
IMG_DIR = "../images"


from joblib import Parallel, delayed


def dump_image(r, i):
        
    if r.img_url:
        if os.path.exists(f"{IMG_DIR}/{r.object_number}.jpg"):
                # print(f"{r.inventory_number} exists! skipping...")
            return (0, r.object_number)
        if i % 173 == 0:
            print(i, "taking a breather for 3 secs")
            sleep(3)

        resp = req.get(r.img_url)
        with open(f"{IMG_DIR}/{r.object_number}.jpg", "wb") as handle:
            handle.write(resp.content)
        return (1, r.object_number)


if __name__ == "__main__":
    df = pd.read_csv(BASE_DIR + "/extraction_v0_1.csv")
    
    cur_df = df.dropna(subset="img_url")

    parallel_ = Parallel(n_jobs=3, verbose=10)

    delayed_dl = delayed(dump_image)

    
    results = parallel_(delayed_dl(r, i) for i, r in tqdm(cur_df.iterrows(), total=len(cur_df)))


        # if r.img_url:
        #     if os.path.exists(f"{IMG_DIR}/{r.object_number}.jpg"):
        #         # print(f"{r.inventory_number} exists! skipping...")
        #         continue
        #     resp = req.get(r.img_url)
        #     with open(f"{IMG_DIR}/{r.object_number}.jpg", "wb") as handle:
        #         handle.write(resp.content)

