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
from search import SORT_KIND
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
    concept_search = TextEmbeddingSearcher(sem_embs, name="concept-searcher")


    sem_embs = EmbeddingSpaceAccessor.load(MKG_DIR+"/generated_data/distiluse-base-multilingual-cased-v2",
                                       loadXD=32)
    sem_searcher = EmbeddingSearcher(sem_embs, name="semantic-searcher")
    
    viz_embs = EmbeddingSpaceAccessor.load(MKG_DIR+"/generated_data/vitmae", loadXD=32)
    viz_searcher = EmbeddingSearcher(viz_embs, name="visual-searcher")

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
    concept_search = TextEmbeddingSearcher(sem_embs, name="concept-searcher")


    sem_embs = EmbeddingSpaceAccessor.load(DMG_DIR+"/generated_data/distiluse-base-multilingual-cased-v2",
                                       loadXD=32)
    sem_searcher = EmbeddingSearcher(sem_embs, name="semantic-searcher")
    
    viz_embs = EmbeddingSpaceAccessor.load(DMG_DIR+"/generated_data/vitmae", loadXD=32)
    viz_searcher = EmbeddingSearcher(viz_embs, name="visual-searcher")

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


@app.get("/{collection_id}/object-numbers")
def object_details(collection_id):
    cur_coll = get_collection(collection_id)
    return cur_coll.index.to_list()



@app.get("/{collection_id}/object-details")
def object_details(collection_id, object_ids):
    cur_coll = get_collection(collection_id)

    object_ids = parse_id_list(object_ids)
    sub = collections[collection_id].loc[object_ids] if object_ids else cur_coll
    return sub.coll.get_presentation_records(as_json=True)



###### DEFAULT ORDERINGS

@app.get("/{collection_id}/default/sample")
def default_sample(collection_id, k=1, ISO_8601_datetime=None, lat_long_degrees="51.05,3.71"):
    """
        The `default` family of routes is based on the collection's inherent ordering, namely based on the time (of making) of an object (the actual sort order is fairly complex). 

        The `sample` sub-route samples from this inherent ordering, with sampling weight simply the inverse rank in the order, such that more recent objects are sampled more often (at a linear rate).

        :param collection_id: The ID of the current collection (see `/collections`).
        :param k: The number of object records to sample.
        :return: A list of length `k` of sampled object records. 
    """
    
    k = int(k)
    cur_coll = get_collection(collection_id)
    moon_force = get_moon(ISO_8601_datetime, lat_long_degrees=lat_long_degrees)

    
    n = len(cur_coll)
    # probs = (n-np.arange(n))+1
    # probs = probs/probs.sum()

    scores = ((n-np.arange(n))+1)/n
    tempered_scores = np.exp((scores/moon_force))
    tempered_scores = tempered_scores/tempered_scores.sum()


    sample = cur_coll.sample(n=k, weights=tempered_scores)
    order_index = pd.Series(range(n), index=cur_coll.index)
    order_index = order_index.loc[sample.index]

    return sample.coll.get_presentation_records(as_json=True, order_index=order_index)
    


@app.get("/{collection_id}/default/order")
def default_order(collection_id, skip=None, limit=None, reverse=False, presentation=True):
    """
        The `default` family of routes is based on the collection's inherent ordering, namely based on the time (of making) of an object (the actual sort order is fairly complex). 

        The `order` sub-route returns all object records from the given collection in their default collection ordering (which is according to the objects' time).  

        :param collection_id: The ID of the current collection (see `/collections`).
        
        :param skip: If given, the first `skip` object records are skipped

        :param limit: If given, the length of the return list of records is limited to `limit` many.

        :param reverse: If True, then the ordering is reversed (i.e. from earliest object to most recent). Default is False.

        :param presentation: (for internal use only)
       
        :return: A list of length of object records in their default order. 
    """
    reverse = str(reverse).lower() == "true"

    cur_coll = get_collection(collection_id)
    cur_coll = cur_coll.sort_values(by="sort_rank", kind=SORT_KIND)

    order_index = pd.Series(range(len(cur_coll)), index=cur_coll.index)

    if reverse:
        cur_coll = cur_coll.iloc[::-1]
        order_index = order_index.iloc[::-1]

    if skip: skip = int(skip)
    if limit: limit = int(limit)
    if skip and limit:
        limit = skip + limit
    cur_coll = cur_coll.iloc[skip:limit]
    order_index = order_index.iloc[skip:limit]

    if presentation:
        return cur_coll.coll.get_presentation_records(as_json=True, order_index=order_index) 
    return cur_coll, order_index
        
@app.get("/{collection_id}/default/order/filter")
def default_filter(collection_id, filter_text=None, skip=None, limit=None, reverse=False, presentation=True):
    """
        The `default` family of routes is based on the collection's inherent ordering, namely based on the time (of making) of an object (the actual sort order is fairly complex). 

        The `filter` sub-route returns all object records from the given collection in their default collection ordering (which is according to the objects' time) and filtered by the `filter_text` parameter (simple string matching with the data fields `objectname_label`, `material_label`, `maker_label`, `coiner_label`, the index (object numbers) and titles and descriptions).

        :param collection_id: The ID of the current collection (see `/collections`).

        :param filter_text: The text to match object records with, may be a regular expression (Python `re` syntax).
        
        :param skip: If given, the first `skip` object records are skipped

        :param limit: If given, the length of the return list of records is limited to `limit` many.

        :param reverse: If True, then the ordering is reversed (i.e. from earliest object to most recent). Default is False.

        :param presentation: (for internal use only)
       
        :return: A list of length of object records in their default order. 
    """
    if filter_text is None:
        filter_text = ""
    ordered, order_index = default_order(collection_id, skip=None, limit=None, reverse=reverse, presentation=False)
    filtered = ordered.coll.filter(filter_text)
    order_index = order_index.loc[filtered.index]

    if skip: skip = int(skip)
    if limit: limit = int(limit)
    if skip and limit:
        limit = skip + limit
    filtered = filtered.iloc[skip:limit]
    order_index = order_index.iloc[skip:limit]

    return filtered.coll.get_presentation_records(as_json=True, order_index=order_index)#ordered[keep.loc[ordered.index]]




# @app.get("/{collection_id}/random/sample")
# def random_objects(collection_id, k=1):
#     """
#         The `random` family of routes is completely randomised, ignoring any default orderings or search scores and simply assuming a uniform scoring over the collection. E.g. ordering is therefore not a well-defined action for this family. 

#         The `sample` sub-route take a number `k` and randomly samples (at uniform) k object records from the collection.

#         :param collection_id: The ID of the current collection (see `/collections`).
        
#         :param k: The number of object records to sample.
        
#         :return: A list of length of object records in their default order. 
#     """
#     k = int(k)
#     cur_coll = get_collection(collection_id)
#     return cur_coll.sample(k).coll.get_presentation_records(as_json=True)



@app.get("/{collection_id}/search")
def search_collection(collection_id, object_ids, concept=None, model_ids=None):
    """
        The `search` family of routes is based on scoring and ordering the collection according to dynamic search parameters -- objects, concepts and models.

        The family of routes has a "parent", as all other routes depend on the scores returned by it. This also implies that all its "children" inherit this functions parameters, as they need to call the parent before doing their own computations.

        :param collection_id: The ID of the current collection (see `/collections`).
        
        :param object_ids: A list of object IDs (also called "object numbers" or "catalogue numbers" to search with.

        :param concept: A string to search the collection -- titles, descriptions, etc -- with (akin to a search string passed to e.g. Google).

        :param model_ids: A list of model IDs (see `/{collection_id}/models`).
        
        :return: A list of scores for the entire collection according to their relevance to the current search parameters. 
    """
    
    # if is_cached(collection_id, object_ids, concept, model_ids):
    #     return get_cached(collection_id, object_ids, concept, model_ids)

    cur_coll = get_collection(collection_id)

    if (object_ids is None) or not object_ids or len(object_ids) < 1:
        raise ValueError(f"object_ids is required! (at least one ) but was {object_ids}")

    
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
def sample_collection(collection_id, object_ids, concept=None, model_ids=None,
                      k=12, ISO_8601_datetime=None, lat_long_degrees="51.05,3.71", temp=None):
    """
        The `search` family of routes is based on scoring and ordering the collection according to dynamic search parameters -- objects, concepts and models.

        The `sample` sub-route of this family samples `k` objects with weights according to the scores return by its parent route `/{collection_id}/search`.

        :param collection_id: The ID of the current collection (see `/collections`).
        
        :param object_ids: A list of object IDs (also called "object numbers" or "catalogue numbers" to search with. Passed to its parent.

        :param concept: A string to search the collection -- titles, descriptions, etc -- with (akin to a search string passed to e.g. Google). Passed to its parent.

        :param model_ids: A list of model IDs (see `/{collection_id}/models`). Passed to its parent. 

        :param ISO_8601_datetime: Used for computing the moon, which influences the sampling weights.

        :param lat_long_degrees: Used for computing the moon, which influences the sampling weights.
        
        :return: A list of `k` object records sampled according to the relevance scores computed for the entire collection.
    """
    
    
    cur_coll = get_collection(collection_id)
    cur_search = searches[collection_id]
    moon_force = get_moon(ISO_8601_datetime, lat_long_degrees=lat_long_degrees)
    k = int(k)
    if temp:
        moon_force = float(temp)


    scores = search_collection(collection_id, object_ids, concept, model_ids)
    # order_index = scores.argsort()
    order_index = pd.Series(range(len(scores)), index=scores.sort_values(ascending=False, kind=SORT_KIND).index)

    
    rand_recs = cur_search.sample(cur_coll, scores=scores, temp=moon_force, size=k)
    sample_order_index = order_index.loc[rand_recs.index]

    original_recs = cur_coll.loc[parse_id_list(object_ids)]
    original_order_index = order_index.loc[original_recs.index]
    
    return {"original_records": original_recs.coll.get_presentation_records(as_json=True, order_index=original_order_index),
            "sampled_records": rand_recs.coll.get_presentation_records(as_json=True, order_index=sample_order_index)}



@app.get("/{collection_id}/search/order")
def order_collection(collection_id, object_ids, concept=None, model_ids=None,
                     skip=None, limit=None, reverse=False, presentation=True):
    cur_coll = get_collection(collection_id)
    cur_search = searches[collection_id]
    reverse = str(reverse).lower() == "true"

    scores = search_collection(collection_id, object_ids, concept, model_ids)

    # order_index = get_order_index(scores, rand_recs.index)

    ordered = cur_search.order(cur_coll, scores)
    order_index = pd.Series(range(len(ordered)), index=ordered.index)
    
    if reverse:
        ordered = ordered.iloc[::-1]
        order_index = order_index.iloc[::-1]
    
    if skip: skip = int(skip)
    if limit: limit = int(limit)
    if skip and limit:
        limit = skip + limit
    ordered = ordered.iloc[skip:limit]
    order_index = order_index.iloc[skip:limit]
    
    if presentation: 
        return ordered.coll.get_presentation_records(as_json=True, order_index=order_index)
    return ordered, order_index

@app.get("/{collection_id}/search/order/indexof")
def order_index(collection_id, object_ids_index_of, object_ids, concept=None, model_ids=None, reverse=False):
    object_ids_index_of = parse_id_list(object_ids_index_of)
    
    ordered, order_index = order_collection(collection_id, object_ids=object_ids, concept=concept, model_ids=model_ids,
                     skip=None, limit=None, reverse=reverse, presentation=False)

    return dict(order_index.loc[object_ids_index_of].items())

    # object_ids_index_of = parse_id_list(object_ids_index_of)
    # print(object_ids_index_of)
    # print(ordered
    # cur_indices = {}
    # for i in object_ids_index_of:
    #     bools = (ordered.index == i)
    #     if bools.sum() < 1:
    #         raise ValueError(f"object number {i} is not in the index!")
    #     if bools.sum() > 1:
    #         raise ValueError("DUPLICATES!?!?! (this should not happen)")

    #     cur_indices[i] = int(bools.nonzero()[0][0])
    
    # return cur_indices


@app.get("/{collection_id}/search/order/filter")
def filter_collection(collection_id, object_ids, concept=None, model_ids=None,
                      filter_text=None, skip=None, limit=None, reverse=False):
    
    if filter_text is None: filter_text = ""
    
    ordered, order_index = order_collection(collection_id, object_ids, concept, model_ids, 
                               skip=None, limit=None, reverse=reverse, presentation=False)
    
    filtered = ordered.coll.filter(filter_text)
    order_index = order_index.loc[filtered.index]


    if skip: skip = int(skip)
    if limit: limit = int(limit)
    if skip and limit:
        limit = skip + limit
    filtered = filtered.iloc[skip:limit]
    order_index = order_index.iloc[skip:limit]

    return filtered.coll.get_presentation_records(as_json=True, order_index=order_index)#ordered[keep.loc[ordered.index]]

if __name__ == "__main__":
    is_prod = os.getenv("PROD", "false").lower() == "true"
    host = os.getenv("HOST", "0.0.0.0")
    port = os.getenv("PORT", 8080)

    uvicorn.run("app:app", host=host, port=int(port), reload=is_prod)
