import os
from glob import glob
from tqdm import tqdm
from datetime import datetime

import requests as rq
from bs4 import BeautifulSoup
from lxml import etree

import pandas as pd
from collections import Counter

base_url = "https://oamh.digicult-verbund.de/cv/RJnShJCe64TUp1iB"
today = datetime.today().strftime("%Y-%m-%d")
BASE_DIR = "../dumps"


def harvest(base_url,  max_recs = -1, **params):
    resp = rq.get(base_url, params=params)
    cur_page = BeautifulSoup(resp.text, features="xml")
    full_size = int(cur_page.find_all("resumptionToken")[0]["completeListSize"])

    if max_recs < 0: max_recs = full_size

    if max_recs < full_size: 
        print(f"{full_size=} but {max_recs=}")
        full_size = max_recs

    resumption_token = cur_page.find_all("resumptionToken")[0].text
    pgs = [cur_page]
    cursor = 0
    pbar = tqdm(total=full_size)
    while cursor < full_size:
        resp = rq.get(base_url, params=(params | dict(resumptionToken=resumption_token)))
        cur_page = BeautifulSoup(resp.text, features="xml")
        if len(cur_page.find_all("resumptionToken")) < 1:
            break
        resumption_token = cur_page.find_all("resumptionToken")[0].text
        pbar.update(int(cur_page.find_all("resumptionToken")[0]["cursor"]) - cursor)
        cursor = int(cur_page.find_all("resumptionToken")[0]["cursor"])
        yield cur_page
        # pgs.append(cur_page)

    # return pgs

def get_record(base_url, record_id):
    params = dict(verb="GetRecord",
                  metadataPrefix="lido",
                  identifier=record_id)

    resp = rq.get(base_url, params=params)
    return BeautifulSoup(resp.text, features="xml")

################################################################################################
### GET IDENTFIERS
################################################################################################
def dump_identifiers():
    params = dict(verb="ListIdentifiers", metadataPrefix="lido")
    
    pgs = harvest(base_url, **params)
    ids = [a.text for p in pgs for a in p.find_all("identifier")]
    pd.Series(ids, name="identifiers").to_csv(f"{BASE_DIR}/identifiers_{today}.csv", index=False)
    


################################################################################################
### GET PAGES
################################################################################################

def dump_pages():
    params = dict(verb="ListRecords", metadataPrefix="lido")
    
    pg_iter = harvest(base_url, **params)
    
    if not os.path.isdir(BASE_DIR+"/pages"):
        os.makedirs(BASE_DIR+"/pages")
    
    for i, pg in enumerate(pg_iter):
        with open(f"{BASE_DIR}/pages/page_{i:03}.xml", "w") as handle:
            handle.write(str(pg))

if __name__ == "__main__":
    dump_pages()
    