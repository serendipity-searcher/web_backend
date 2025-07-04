import os
from datetime import datetime

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from dotenv import load_dotenv
load_dotenv()

from contextlib import asynccontextmanager
import uvicorn
import json

import numpy as np
import pandas as pd



from data.data import CollectionAccessor, ImageHandler, EmbeddingSpaceAccessor

from search import Search, Randomiser, Equaliser, GraphSearcher, EmbeddingSearcher, TextEmbeddingSearcher
from moon import MOON, Moon

def init_MKG():
    MKG_DIR = "./data/MKG"
    image_folder = MKG_DIR+"/images"
    image_handler = ImageHandler("MKG", image_folder=image_folder, keep_prefix=False)

    # time_stamp, pub_file, priv_file = CollectionAccessor.get_latest_dump("./data/dumps")

    time_stamp = "2025-06-05"
    mkg_meta = dict(name="Museum Kunst & Gewerbe", id_="MKG_"+time_stamp,
                    creation_timestamp=time_stamp, language="de")
    df = CollectionAccessor.get_MKG(metadata_path=MKG_DIR+"/dumps/extraction_v0_1.csv",
                                    image_handler=image_handler,
                                    **mkg_meta)
    kg_searcher = GraphSearcher(df)
    
    sem_embs = EmbeddingSpaceAccessor.load(MKG_DIR+"/generated_data/distiluse-base-multilingual-cased-v2",
                                       loadXD=None)
    concept_search = TextEmbeddingSearcher(sem_embs, name="ConceptSearcher")


    sem_embs = EmbeddingSpaceAccessor.load(MKG_DIR+"/generated_data/distiluse-base-multilingual-cased-v2",
                                       loadXD=32)
    sem_searcher = EmbeddingSearcher(sem_embs, name="SemanticSearcher")
    
    viz_embs = EmbeddingSpaceAccessor.load(MKG_DIR+"/generated_data/vitmae", loadXD=32)
    viz_searcher = EmbeddingSearcher(viz_embs, name="VisualSearcher")

    s = Search([kg_searcher, sem_searcher, viz_searcher])
    return df, s, concept_search



def init_DMG():
    DMG_DIR = "./data/DMG"
    image_folder = DMG_DIR+"/images"
    image_handler = ImageHandler("DMG", image_folder=image_folder, keep_prefix=False)

    time_stamp, pub_file, priv_file = CollectionAccessor.get_latest_dump(DMG_DIR+"/dumps")


    dmg_meta = dict(name="Design Museum Gent (public & private)", id_="DMG_"+time_stamp,
                creation_timestamp=time_stamp, language="nl")
    df = CollectionAccessor.get_DMG(pub_path=pub_file, #get_latest("./data/dumps", contains="public"),
                                     priv_path=priv_file, #get_latest("./data/dumps", contains="private"),
                                     rights_path=DMG_DIR+"/rights.csv",
                                     image_handler=image_handler,
                                     **dmg_meta)

    kg_searcher = GraphSearcher(df)


    sem_embs = EmbeddingSpaceAccessor.load(DMG_DIR+"/generated_data/distiluse-base-multilingual-cased-v2",
                                       loadXD=None)
    concept_search = TextEmbeddingSearcher(sem_embs, name="ConceptSearcher")


    sem_embs = EmbeddingSpaceAccessor.load(DMG_DIR+"/generated_data/distiluse-base-multilingual-cased-v2",
                                       loadXD=32)
    sem_searcher = EmbeddingSearcher(sem_embs, name="SemanticSearcher")
    
    viz_embs = EmbeddingSpaceAccessor.load(DMG_DIR+"/generated_data/vitmae", loadXD=32)
    viz_searcher = EmbeddingSearcher(viz_embs, name="VisualSearcher")

    s = Search([kg_searcher, sem_searcher, viz_searcher])
    return df, s, concept_search


@asynccontextmanager
async def lifespan(app: FastAPI):
    global moon
    global collections
    global searches
    global concept_searches


    moon = Moon()

    DMG, DMG_searcher, DMG_concept_search = init_DMG()
    MKG, MKG_searcher, MKG_concept_search = init_MKG()


    collections = [DMG, MKG]
    searches = [DMG_searcher, MKG_searcher]
    concept_searches = [DMG_concept_search, MKG_concept_search]

    searches = {c.attrs["id_"]: s for c, s in zip(collections, searches)}
    concept_searches = {c.attrs["id_"]: cs for c, cs in zip(collections, concept_searches)}
    collections = {c.attrs["id_"]: c for c in collections}

    yield
    print("have a lunar day 🌕‬")



app = FastAPI(lifespan=lifespan)

app.mount("/DMG/images", StaticFiles(directory="data/DMG/images"), name="static_DMG")
app.mount("/MKG/images", StaticFiles(directory="data/MKG/images"), name="static_DMG")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# HELPERS
def get_collection(collection_id):
    if not collection_id in collections:
        raise ValueError(f"{collection_id=} unknown. Available collection IDs are {available_collections()}")
    return collections[collection_id]

def parse_id_list(id_list_str):
    try:
        return list(map(str.strip, id_list_str.split(",")))
    except ValueError:
        raise s


@app.get("/moon")
def get_moon(ISO_8601_datetime=None, lat_long_degrees="51.05,3.71"): #lat_degrees=51.05, long_degrees=3.71): #location of DMG
    dt = datetime.fromisoformat(ISO_8601_datetime) if ISO_8601_datetime else datetime.now()
    lat_degrees, long_degrees = map(float, lat_long_degrees.strip().split(","))
    moon_force = moon(dt, (lat_degrees, long_degrees)) #"46.0569° N, 14.5058° E")
    return moon_force # IS in [0,1]

@app.get("/linger-time")
def linger_time_multiplier(ISO_8601_datetime=None, lat_long_degrees="51.05,3.71"):
    moon_force = get_moon(ISO_8601_datetime, lat_long_degrees)
    return 1-(moon_force/2)


@app.get("/collections")
def available_collections():
    return [dict(id=c_id, name=c.attrs["name"]) for c_id, c in collections.items()]


@app.get("/{collection_id}")
def collection_info(collection_id):
    cur_coll = get_collection(collection_id)
    return cur_coll.coll.info()


@app.get("/{collection_id}/models")
def available_models(collection_id):
    cur_search = searches[collection_id]
    return [dict(id=searcher.id, name=searcher.name) for searcher in cur_search.searchers]


@app.get("/{collection_id}/object-details")
def object_details(collection_id, object_ids):
    cur_coll = get_collection(collection_id)

    object_ids = parse_id_list(object_ids)
    sub = collections[collection_id].loc[object_ids] if object_ids else cur_coll
    return sub.coll.get_presentation_records(as_json=True)



@app.get("/{collection_id}/search")
def search_collection(collection_id, object_ids=None, concept=None, model_ids=None):
    # if is_cached(collection_id, object_ids, concept, model_ids):
    #     return get_cached(collection_id, object_ids, concept, model_ids)

    cur_coll = get_collection(collection_id)

    if (object_ids is None) or not object_ids or len(object_ids) < 1:
        object_ids = list(cur_coll.sample(4).index)
    else:
        object_ids = parse_id_list(object_ids)
        
    cur_records = cur_coll.loc[object_ids]
    cur_search = searches[collection_id]
    cur_concept_search = concept_searches[collection_id]

    used_models = False
    if (model_ids is not None) and (len(model_ids) > 0):
        model_ids = parse_id_list(model_ids)
        scores = cur_search(cur_records, model_ids)
        used_models = True
    else:
        scores = Equaliser(cur_coll)(cur_records)

    used_concept = False
    if (concept is not None) and (len(concept) > 0):
        concept_scores = cur_concept_search(concept)
        concept_scores = concept_scores/concept_scores.sum()
        scores = (scores + concept_scores)/2
        used_concept = True

    if not used_models and not used_concept:
        scores = Randomiser(cur_coll)(cur_records)
    

    # diversify(scores)
    # cache_search(object_ids, concept, model_ids, scores)

    scores = scores.loc[cur_coll.index.intersection(scores.index)]
    return scores

@app.get("/{collection_id}/search/sample")
def sample_collection(collection_id, object_ids=None, concept=None, model_ids=None,
                      k=12, ISO_8601_datetime=None, lat_long_degrees="51.05,3.71"):
    cur_coll = get_collection(collection_id)
    cur_search = searches[collection_id]
    moon_force = get_moon(ISO_8601_datetime, lat_long_degrees=lat_long_degrees)
    k = int(k)


    scores = search_collection(collection_id, object_ids, concept, model_ids)
    rand_recs = cur_search.sample(cur_coll, scores=scores, temp=moon_force, size=k)
    return rand_recs.coll.get_presentation_records(as_json=True)



@app.get("/{collection_id}/search/order")
def order_collection(collection_id, object_ids=None, concept=None, model_ids=None,
                     skip=None, limit=None, reverse=False, presentation=True):
    cur_coll = get_collection(collection_id)
    cur_search = searches[collection_id]
    reverse = str(reverse).lower() == "true"

    scores = search_collection(collection_id, object_ids, concept, model_ids)

    ordered = cur_search.order(cur_coll, scores, reverse=reverse)
    if skip: skip = int(skip)
    if limit: limit = int(limit)
    if skip and limit:
        limit = skip + limit
    ordered = ordered.iloc[skip:limit]
    return ordered.coll.get_presentation_records(as_json=True) if presentation else ordered


@app.get("/{collection_id}/search/order/filter")
def filter_collection(collection_id, object_ids=None, concept=None, model_ids=None,
                      filter_text=None, skip=None, limit=None, reverse=False):
    if filter_text is None:
        filter_text = ""
    ordered = order_collection(collection_id, object_ids, concept, model_ids, 
                               skip=skip, limit=limit, reverse=reverse, presentation=False)
    filtered = ordered.coll.filter(filter_text)
    return filtered.coll.get_presentation_records(as_json=True)#ordered[keep.loc[ordered.index]]


if __name__ == "__main__":
    is_prod = os.getenv("PROD", "false").lower() == "true"
    host = os.getenv("HOST", "0.0.0.0")
    port = os.getenv("PORT", 8080)

    uvicorn.run("app:app", host=host, port=int(port), reload=is_prod)
