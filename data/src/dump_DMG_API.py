from tqdm import tqdm
from time import sleep

import requests as rq
import urllib.parse as urlparse
import json

import numpy as np
import pandas as pd

import datetime as dt


k = 1113

params = dict(apiKey="00B12959739EE8AF657D9D31DDEB1E0403D554EBB276B0537AD1",
              itemsPerPage=k)
              
base_url = "https://data.designmuseumgent.be/v1/id/"
private = "private-objects/" # trailing backslash necessary?
public = "objects"


def connect(endpoint, params): 
    r = rq.get(endpoint, params=params)
    print("used URL", r.url)
    #check status code 
    if r.status_code == 200:
        data = r.json()
        return data 
    else:
        print("error connecting to API")
        raise ConnectionError(f" GET request failed: {endpoint} \n\n {params} \n\n {r.headers} \n\n {r.status_code}")

def crawl(endpoint, params): 
    payload = connect(endpoint, params)
    sleep(1)
    # print(payload["hydra:view"]["@id"])
    ## DO SOMETHING HERE

    yield from payload["GecureerdeCollectie.bestaatUit"]


    # iterate over pages of payload
    if payload["hydra:view"].get("hydra:next"):
        next_endpoint, next_params = payload["hydra:view"]["hydra:next"].split("?")
        # next_params = params & dict(urlparse.parse_qsl(next_endpoint))
        next_params = dict(urlparse.parse_qsl(next_params))
        # next_params.update(params)
        params.update(next_params)
        
        # next_endpoint = next_endpoint[:next_endpoint.find("?")]
        # + f"&itemsPerPage={k}"
        print("next page: ", next_endpoint)
        print("next params", params)
        print("")
        yield from crawl(next_endpoint, params)
    else:
        # print(payload)
        print("done")
        return


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--save_path", help="path for saving downloaded images")
    args = parser.parse_args()

    save_path = args.save_path if (args.save_path is not None) else "./dumps"


    ## PUBLIC DATA
    endpoint = base_url + public
    data = list(tqdm(crawl(endpoint, params))) #dict(itemsPerPage=1113))))
    
    today = dt.datetime.today().strftime("%Y-%m-%d")
    with open(save_path + f"/API_dump_public_{today}.json", "w") as handle:
        json.dump(data, handle)

    
    ## PRIVATE DATA
    endpoint = base_url + private
    data = list(tqdm(crawl(endpoint, params)))
    
    today = dt.datetime.today().strftime("%Y-%m-%d")
    with open(save_path +  f"/API_dump_private_{today}.json", "w") as handle:
        json.dump(data, handle)




## USEFUL FUNCTION

# def find_in_obj(obj, x):
#     primitives = str, int, float
#     complexes = set, list, dict

#     if type(obj) in primitives:
#         # print(obj)
#         if obj == x:
#             return True
#         else:
#             return False
            
#     if isinstance(obj, dict):
#         # found = False
#         for k, v in obj.items():
#             k_found = find_in_obj(k, x)
#             v_found = find_in_obj(v, x)
#             if k_found or v_found:
#                 return True
#         return False
            
#     elif isinstance(obj, set) or isinstance(obj, list):
#         for v in obj:
#             if find_in_obj(v, x):
#                 return True
#         return False
#     else: 
#         raise ValueError
    # raise ValueError
# USAGE EXAMPLE
# find_in_obj(data[0], '2006-02')