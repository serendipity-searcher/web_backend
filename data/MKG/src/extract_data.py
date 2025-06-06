"""
### TODO

    maybe for adding to text field?:
     - `<lido:objectDescriptionSet lido:type="Erhaltungszustand">/<lido:descriptiveNoteValue>`
     - `<lido:objectDescriptionSet lido:type="Objektgeschichte">/<lido:descriptiveNoteValue>`
    
    for display:
    
     - [x] `<lido:eventDate>/<lido:displayDate>`
    
    <lido:conceptID lido:source="xTree" lido:type="http://terminology.lido-schema.org/identifier_type/uri">http://digicult.vocnet.org/ikonographie/3.2729</lido:conceptID>
    <lido:conceptID lido:source="GND" lido:type="http://terminology.lido-schema.org/identifier_type/uri">http://d-nb.info/gnd/4568024-3</lido:conceptID>
    <lido:conceptID lido:source="Iconclass" lido:type="local">25G41(POPPY)</lido:conceptID>
    <lido:term lido:addedSearchTerm="no" lido:pref="preferred" xml:lang="de">Mohnblume</lido:term>
"""

from tqdm import tqdm
from glob import glob

from lxml import etree

import csv
import pandas as pd

from datetime import datetime

from extraction_sparql import *



BASE_DIR = "../dumps"


def is_singleton(column, min_singleton_percentage=1.0):
    return (column.apply(len) < 2).sum()/len(column) > min_singleton_percentage

def unpack_singletons(column):
    return column.apply(lambda ls: ls[0] if ls else "")

# def unpack_singletons(column, min_singleton_percentage=1.0):
#     if (column.apply(len) < 2).sum()/len(column) > min_singleton_percentage:
#         return column.apply(lambda ls: ls[0] if ls else None)
#     return column

def lists_to_semicolonsv(column, sep="&semi;"):
    def proc(ls):
        try:
            return sep.join(ls)
        except TypeError:
            print(ls)
    return column.apply(lambda ls: proc(ls))# if isinstance(ls, tuple) and all(ls) else f"WHATTHEFUCK: {ls}")



today_interval = "/"+datetime.today().strftime("%Y-%m-%d")

def pad(x):
    try:
        i = int(x)
        return f'{i:04}' if i >= 0 else f'{i:05}'
    except (TypeError, ValueError):
        return x
        
def create_time(row):
    d1, d2 = pad(row.date_begin), pad(row.date_end)
    if not d1 and not d2:
        return today_interval
    if d1 == d2:
        return d1
    return f"{d1}/{d2}"
    


def extract_from_pages():
    ts = [etree.parse(f) for f in tqdm(glob(BASE_DIR + "/pages/*.xml"))]
    print(len(ts), flush=True)
    
    df = pd.DataFrame(
        build_record(rt)
        for t in tqdm(ts)
        for rt in t.xpath("//oai:record/oai:metadata", namespaces=ns)
    )
    
    df = df.drop_duplicates()

    def ten_percent(col, min_singleton_percentage=0.8):
        return is_singleton(col, min_singleton_percentage=min_singleton_percentage)

    simple_cols = df.apply(ten_percent)
    simple_cols = simple_cols[simple_cols].index
    list_cols = [c for c in df.columns if not c in simple_cols]

    df[simple_cols] = df[simple_cols].apply(unpack_singletons)
    

    # df.title = df.title.apply(lambda ls: ls[:1])

    # df.maker = df.maker.apply(lambda ls: ls[:1])
    # df.maker_role = df.maker_role.apply(lambda ls: ls[:1])
    # df.date_begin = df.date_begin.apply(lambda ls: ls[:1])
    # df.date_end = df.date_end.apply(lambda ls: ls[:1])
    # df.place = df.place.apply(lambda ls: ls[:1])
    
    
    # list_cols = df.apply(lambda col: (col.apply(len) > 1).any())
    # list_cols = list_cols[list_cols].index
    # print(list_cols)
    # simple_cols = [c for c in df.columns if c not in list_cols]

    # def unpack_10_perceent(column):
    #     return unpack_singletons(column, min_singleton_percentage=0.9)
    # df = df.apply(unpack_10_percent)


    df["time"] = df.fillna("").apply(create_time, axis=1)
    
    
    
    #### RENAME COLUMNS TO MATCH data.py requirements
    
    # MINNIMAL:
    # object_number
    # - title, descriptiion -> get_texts
    # - object name, material, technique
    # - date -> parse as EDTF
    # - maker, etc

    # THE STRATEGY IS: MAKE MKG SEMANTICS MATCH DMG SEMANTICS
    # SPECIFICALLY:
    # - CREATOR (MAKER)/COINER DISTINCTION -> MAKER_ROLE IS USED TO INTERPRET AND DISTRIBUTE
    #   (FOR NOW: EVERY MAKING/COINING EVENT IS BOTH MAKING AND COINING EVENT
    # - LABELS ARE URIs
    # - IMAGE RIGHTS ARE USED TO FILL RECORDV RIGHTS (WHEREVER THE LATTER IS MISSING)
    # - INTRICACIES BETWEEN OBJECTNAME, OBJECTTYPE AND ARTSTYLE ARE IGNORED
    # - CATEGORIES ARTSTYLE AND SUBJECT ARE IGNORED

    

    df[list_cols] = df[list_cols].apply(lists_to_semicolonsv)

    df = df.rename(dict(
                collection="subcollection_name",
                creditline="attribution",
                recordrights="rights",
                objectname="objectname_label",
                material="material_label",
                technique="technique_label",
                maker="maker_label",
                place="creation_place_label",
            ), axis=1    
        )

    df["rights"] = df.rights.fillna(df.img_rights)

    df["subcollection_URI"] = df.subcollection_name

    df["objectname_URI"] = df.objectname_label
    df["material_URI"] = df.material_label
    df["technique_URI"] = df.technique_label
    
    df["maker_URI"] = df.maker_label
    df["creation_place_URI"] = df.creation_place_label

    df["coiner_label"] = df.maker_label
    df["coiner_URI"] = df.maker_label
    df["coin_place_label"] = df.creation_place_label
    df["coin_place_URI"] = df.creation_place_label

    df["creation_time"] = df.time
    df["coin_time"] = df.time


    # df = df.set_index("object_number")
    df = df[~df.object_number.isna()]
    df = df[~(df.object_number.str.contains(" ") | df.object_number.str.contains(","))]

    
    df.to_csv(f"{BASE_DIR}/extraction_v0_1.csv", quoting=csv.QUOTE_ALL, quotechar='"', index=True)


if __name__ == "__main__":
    extract_from_pages()
    