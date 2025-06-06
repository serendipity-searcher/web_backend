import argparse
from tqdm import tqdm
tqdm.pandas()
from glob import glob
import datetime as dt

import json

import csv
import numpy as np
import pandas as pd
from collections import Counter

import rdflib
from rdflib import Graph

from extraction_sparql import core_query, creation_prov_query, coining_prov_query, acquisition_query
# time_cols = ['acquisition_time', 'creation_time', 'coin_time']



def compact(series, keep_repetitions=False, as_string=True, sep="&semi;"):
    u = series.unique()
    if len(u) == 0:
        return "" if as_string else None
    elif len(u) == 1:
        return series.iloc[0]
    else:
        x = series if keep_repetitions else u
        return sep.join(x) if as_string else list(x)


def implode(df, on="object_number", as_string=True, sep="&semi;"):
    def _implode(subdf):
        return [compact(subdf[col].dropna(), as_string=as_string, sep=sep) for col in subdf.columns]
    rows = df.groupby(on).progress_apply(_implode)
    return pd.DataFrame(rows.tolist(), index=rows.index, columns=df.columns)





G = Graph(store="Oxigraph")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", help="JSON-LD file to extract data from")
    parser.add_argument("--is_public", help="added as a flag to the rows in the extracted table whether the source data is public", action="store_true")
    
    args = parser.parse_args()
    save_name= args.file.rsplit(".", maxsplit=1)[0] + "_extracted.csv"
    # save_name = args.file.rsplit(".", maxsplit=1)[0] + "_extracted.parquet"
    print(f"SAVING TO {save_name}")
    
    with open(args.file) as orig_handle:
        txt = orig_handle.read()
        new_txt = txt.replace("http://www.w3.org/2001/XMLSchema#dateTime",
                            "http://id.loc.gov/datatypes/edtf/EDTF")
        new_txt = new_txt.replace("^", "p") # occurs once - a corrupted character?
        new_obj = json.loads(new_txt)
        # new_obj = new_obj[:10]
        with open("TEMP_extract_data.json", "w") as new_handle:
            json.dump(new_obj, new_handle)
    
    # G.parse(source="../data/API_dump_13-01-2025_small.json", format="json-ld")
    # G.parse(source="../data/API_dump_public_10-03-2025_parseable_small.json", format="json-ld")
    G.parse(source="TEMP_extract_data.json", format="json-ld")

    # CORE
    prepped_q = rdflib.plugins.sparql.prepareQuery(core_query)
    qres = G.query(prepped_q)
    core = pd.DataFrame([r for r in qres], columns=list(map(str, qres.vars))).drop_duplicates()

    print("EXTRACTING CREATION PROV...")

    # CREATION PROV
    prepped_q = rdflib.plugins.sparql.prepareQuery(creation_prov_query)
    qres = G.query(prepped_q)
    creation_prov = pd.DataFrame([r for r in qres], columns=list(map(str, qres.vars))).drop_duplicates()

    print("EXTRACTING COINING PROV...")

    # COINING PROV
    prepped_q = rdflib.plugins.sparql.prepareQuery(coining_prov_query)
    qres = G.query(prepped_q)
    coining_prov = pd.DataFrame([r for r in qres], columns=list(map(str, qres.vars))).drop_duplicates()

    print("EXTRACTING ACQUISITION PROV...")
    # print(acquisition_query)
    # ACQUISITION PROV
    prepped_q = rdflib.plugins.sparql.prepareQuery(acquisition_query)
    qres = G.query(acquisition_query)
    acquisition = pd.DataFrame([r for r in qres], columns=list(map(str, qres.vars))
                              ).drop_duplicates().set_index("object_number")
 

    both_provs = creation_prov.set_index("object_number").join(coining_prov.set_index("object_number"),
                                                               how="outer")

    full = core.set_index("object_number").join(other=both_provs, how="outer")
    full = full.join(other=acquisition, how="left")
    full = full.reset_index()
    
    
    # PARSING & CLEANING UP

    full["part_label"] = full.part_label.replace("https://apidgdv.gent.be/opendata/eventstream-api-private/v1/dmg/", "", regex=True)
    
    full = full[~full.title.fillna("").str.lower().str.startswith("dossier")]
    full = full[full.object_URI.str.startswith("https://stad.gent/id/mensgemaaktobject/dmg/530")]
    full = full[~(full.object_number.str.endswith(r"_ORANJE") | 
                full.object_number.str.endswith(r"_ROOD") |
                full.object_number.str.endswith(r"_ARCHIEF"))]


    # PARSEABLE EDTF DATES
    # today_interval = "/"+dt.datetime.today().strftime("%Y-%m-%d")
    # full[time_cols] = full[time_cols].replace({"/": today_interval, "..": today_interval}).fillna(today_interval)
    time_cols = ['coin_time', 'creation_time', 'acquisition_time']
    print(f"WTF: {full[time_cols]}")
    full[time_cols] = full[time_cols].replace({"/": None, "..": None})#.fillna("")
    print(f"WTF 2: {full[time_cols]}")
    # print(f"WTF 2: {full[time_cols].replace({"/": None, "..": None})}")

    
    full["is_public"] = bool(args.is_public)
    # full.to_csv(save_name, index=False, quoting=csv.QUOTE_ALL, quotechar='"')


    imploded = implode(full)
    
    # # this_minute = dt.datetime.today().strftime("%Y-%m-%dT%H-%M")
    imploded.to_csv(save_name, index=False, quoting=csv.QUOTE_ALL, quotechar='"')
    # imploded.to_parquet(save_name, index=False, compression=None)

