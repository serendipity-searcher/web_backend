import os
from datetime import datetime

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from contextlib import asynccontextmanager
import uvicorn
import json

import numpy as np
import pandas as pd



from data.data import CollectionAccessor, ImageHandler#, EmbeddingSpaceAccessor

from search import Search, Randomiser #GraphSearcher, EmbeddingSearcher
from moon import MOON, Moon


@asynccontextmanager
async def lifespan(app: FastAPI):
    global df
    global moon
    global image_handler

    moon = Moon()
    
    image_folder = "./data/images/DMG"
    image_handler = ImageHandler(image_folder=image_folder)


    dmg_meta = dict(name="DMG 2025-04-03", id_="DMG_2025-04-03",
                creation_timestamp="2025-04-03")
    df = CollectionAccessor.get_DMG(pub_path="./data/dumps/API_dump_public_2025-04-03_extracted.csv",
                                 priv_path="./data/dumps/API_dump_private_2025-04-03_extracted.csv",
                                 rights_path="./data/rights.csv",
                                 image_handler=image_handler,
                                 **dmg_meta)
    
    rand = Randomiser(df)
    s = Search([rand])

    yield
    print("have a lunar day 🌕‬")



