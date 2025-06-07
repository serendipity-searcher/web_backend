from glob import glob
import os

import numpy as np
import pandas as pd
from tqdm import tqdm
tqdm.pandas()

import re

import datetime as dt
from edtf import parse_edtf

import umap.umap_ as umap

# def get_latest(directory, contains=""):
#     files = [f for f in sorted(glob(directory+"/*")) if contains in f]
#     if not files: raise ValueError(f"{directory} contains no files with substring {contains}")
#     return files[-1]

# as documented here: https://pandas.pydata.org/docs/development/extending.html
@pd.api.extensions.register_dataframe_accessor("emb_space")
class EmbeddingSpaceAccessor:   
    @staticmethod
    def load(emb_dir, loadXD=None, from_tsv=False, index_col="object_number", index_subset=None):
        base_path = f"{emb_dir}/embeddings"
        ext = ".tsv" if from_tsv else ".csv"
        if loadXD:
            to_load = base_path + f"_{loadXD}D" + ext
            if not os.path.exists(to_load):
                to_load = base_path + ext
        else:
            to_load = base_path + ext
        
        emb = pd.read_csv(to_load, sep="\t" if from_tsv else ",")
        emb = emb.set_index(index_col).sort_index()
        if index_subset is not None: emb = emb.loc[index_subset]
        return emb

        # # if loadXD:
        # #     emb = pd.read_csv(f"{emb_dir}/embeddings_umap_{loadXD}D.csv")
        # # else:
        # #     emb = pd.read_csv(f"{emb_dir}/embeddings.csv")

        #     pbar = tqdm(sorted(glob(f"{emb_dir}/batch_*.csv")), 
        #                 desc="[EmbeddingSpaceAccessor]: loading high-dimensional embedding space...")
        #     emb = pd.concat([pd.read_csv(f) for f in pbar])

        # emb = emb.set_index(index_col).sort_index()
        
        # return emb

    
    def __init__(self, pandas_obj):
        self._obj = pandas_obj

    def to_tsv(self, filename, **to_csv_args):
        self._obj.to_csv(filename, sep="\t", **to_csv_args)

    def umap(self, save_to=None, to_tsv=False, **umap_params):
        data = self._obj.to_numpy()
        min_dist = (data.var()**0.5/2)
        default_params = dict(metric="cosine", n_neighbors=10, 
                             min_dist=min_dist, spread=min_dist*2, n_components=32)
        default_params.update(umap_params)
        reducer = umap.UMAP(**default_params)
        red_embs = pd.DataFrame(reducer.fit_transform(data), index=self._obj.index)
        if save_to is not None:
            red_embs.to_csv(save_to, index=True, sep=("\t" if to_tsv else ","))
        return red_embs


class ImageHandler:
    def __new__(cls, collection_name, image_folder, keep_prefix=True, imploded=False):
        if collection_name == "DMG":
            self = DMGImageHandler(image_folder, keep_prefix=keep_prefix, imploded=True)
        elif collection_name == "MKG":
            self = MKGImageHandler(image_folder, keep_prefix=keep_prefix, imploded=False)
        else:
            ValueError(f"ImageHandler doesn't know a collection called {collection_name}!")

        return self
        
    # def __init__(se

class MKGImageHandler:
    def __init__(self, image_folder, keep_prefix=True, imploded=False):
        paths = pd.Series(glob(image_folder+"/*"), name="image_path").fillna("")
        if paths.isna().all() or len(paths) < 1:
            print(f"WARNING: {image_folder} is empty! Is the path correct?")
        
        if not keep_prefix: 
            paths = paths.str.replace(image_folder+"/", "")

        obj_nums = self.object_number_from_path(paths)
        paths.index = obj_nums
        if imploded:
            paths = paths.groupby(paths.index).apply(list)
        self._obj = paths

    @classmethod
    def object_number_from_path(cls, path_series):
        obj_nums = path_series.apply(lambda f: os.path.splitext(os.path.basename(f))[0])
        obj_nums.name = "object_number"
        return obj_nums



class DMGImageHandler:
    def __init__(self, image_folder, keep_prefix=True, imploded=True):
        paths = pd.Series(glob(image_folder+"/*/*"), name="image_path").fillna("")
        if paths.isna().all() or len(paths) < 1:
            print(f"WARNING: {image_folder} is empty! Is the path correct?")
            
        if not keep_prefix: 
            paths = paths.str.replace(image_folder, "")

        
        obj_nums = self.object_number_from_path(paths)
        paths.index = obj_nums
        if imploded:
            paths = paths.groupby(paths.index).apply(list)
        self._obj = paths

    
    @staticmethod
    def parse_filepath(s):#     folder, file = s.rsplit("/", maxsplit=2)#[1:]

        *_, folder, file = s.rsplit("/", maxsplit=2)#[1:]
        try:
            obj_rendition, extension = file.rsplit(".", maxsplit=1)
        except ValueError:
            obj_rendition = file
            extension = None
            
        try:
            obj_num, rendition_ind =  obj_rendition.rsplit("$", maxsplit=1)
        except ValueError:
            obj_num = obj_rendition
            rendition_ind = None
        # rendition_id = ((rendition_ind[0] if rendition_ind[0] else None) if rendition_ind else None)
        return dict(path=folder, object_number=obj_num, 
                    rendition_index=rendition_ind, file_extension=extension)

    # applies directly to Series objects
    @classmethod
    def object_number_from_path(cls, path_series):
        get_obj_num = lambda s: cls.parse_filepath(s)["object_number"]
        obj_nums = path_series.apply(get_obj_num)
        obj_nums.name = "object_number"
        return obj_nums

    
    # def align_with_other(self, other, how="right"):
    #     pass

    
    def merge_with_other(self, other, how="right"):
        return self._obj.join(other, how=how)
        

class StaticTextTranslator:
    en = ["and_", "collection_of", "made_of", "unknown", "before", "after"]
    
    nl = ["en", "verzameling van", "gemaakt van", "onbekend", "voor", "na"]

    de = ["und", "Sammlung von", "gemacht aus", "unbekannt", "vor", "nach"]
          
    def __init__(self, language_code):
        implemented = "en", "nl", "de"
        assert language_code in implemented

        # keys = [k.replace(" ", "_") for k in StaticTextTranslator.en]
        en_vals = [k.replace("_", " ").strip() for k in StaticTextTranslator.en]
        vals = (en_vals if (language_code == "en") else \
            (StaticTextTranslator.nl if (language_code == "nl") else StaticTextTranslator.de))

        self.__dict__.update(dict(zip(self.en, vals)))
          


@pd.api.extensions.register_dataframe_accessor("coll")
class CollectionAccessor:
    primary_id = "object_number"

    text_cols = ["title", "description", "objectname_label", "material_label"]
    
    time_cols = ['coin_time', 'creation_time', 'acquisition_time']
    
    # categorical_cols = ['objectname_URI', 'subcollection_URI', 
    #                     'material_URI', 'part_label', 'part_material_URI', 'creation_place_URI',
    #                     'maker_URI', 'technique_URI', 'coin_place_URI', 'coiner_URI']
    
    
    # label_cols = ['objectname_label', 'subcollection_name', 'material_label', 'part_label', 'part_material_label', 
    #                   'creation_time', 'creation_place_label', 'maker_label', 'technique_label', 'coin_time', 
    #                   'coin_place_label', 'coiner_label']


    categorical_cols = dict(objectname_URI='objectname_label',
                           subcollection_URI='subcollection_name',
                           material_URI="material_label",
                           technique_URI="technique_label",
                           # part_label="part_label",
                           # part_material_URI="part_material_label",
                           
                           creation_place_URI="creation_place_label",
                           maker_URI="maker_label",
                           coin_place_URI="coin_place_label",
                           coiner_URI="coiner_label"
                          )
                           
    
    presentation_cols = ["title", "description", 
                             'maker_label', 'creation_time', "creation_place_label",
                             'coiner_label', 'coin_time', "coin_place_label", 
                            "rights", "attribution"
                            ]

    ordering_cols = time_cols #+ CollectionAccessor.label_cols


    list_cols = []
    parsed_dates_memo = {}
    
    @classmethod
    def parse_lists(cls, series, sep="&semi;"):
        if not series.dtype == object: return series
        if not series.str.contains(sep).any(): return series
        cls.list_cols.append(series.name)
        return series.fillna("").apply(lambda s: s.split(sep))

    @classmethod
    def parse_edtf_memoised(cls, series):
        def memoised(date):
            if not date in cls.parsed_dates_memo:
                cls.parsed_dates_memo[date] = parse_edtf(date)
            return cls.parsed_dates_memo[date]
        return series.progress_apply(memoised)

    @staticmethod
    def get_latest_dump(directory):
        public = sorted(glob(directory+ "/*_public_*.json"))[-1]
        private = sorted(glob(directory+ "/*_private_*.json"))[-1]
        time_stamp = re.match(".*/API_dump_public_(.+).json", public).group(1)
        return time_stamp, public.replace(".json", "_extracted.csv"), private.replace(".json", "_extracted.csv")

    # @staticmethod
    # def metadata_from_file(f):
        
        
        
    
    @classmethod
    def get_DMG(cls, pub_path, priv_path=None, rights_path=None, 
                image_handler=None, erase_duplicates=False, **metadata):
        df = pd.read_csv(pub_path).set_index("object_number")
        if priv_path:
            priv = pd.read_csv(priv_path).set_index("object_number")
            df = pd.concat([df, priv.loc[priv.index.difference(df.index)]])

        if rights_path:
            rights = pd.read_csv(rights_path).set_index("object_number")
            df = df.join(rights)

        if image_handler is not None:
            df = df.join(image_handler._obj, how="left")
        else:
            df["image_path"] = ""

        assert ("name" in metadata) and ("id_" in metadata) and ("creation_timestamp" in metadata) and ("language" in metadata)
        df.attrs = metadata
        df.attrs.update(dict(lang=StaticTextTranslator(metadata["language"])))
        df.attrs.update(dict(reverse_names=True))

        ### PARSING
        df = df.apply(cls.parse_lists)


        ### TIME STUFF

        ### REMOVE: PART OF EXTRACTION

        df[cls.time_cols] = df[cls.time_cols].replace({"/": None, "..": None})#.fillna(None)
        ### REMOVE: PART OF EXTRACTION
                
        filled_time_col = "time"
        df[filled_time_col] = df[cls.time_cols[0]]
        for alt_time_col in cls.time_cols[1:]:
            df[filled_time_col] = df[filled_time_col].fillna(df[alt_time_col])
                  
        
        today_interval = "/"+dt.datetime.today().strftime("%Y-%m-%d")
        # df[cls.time_cols] = df[cls.time_cols].fillna(today_interval)
        df[filled_time_col] = df[filled_time_col].fillna(today_interval)

        ### REMOVE: PART OF EXTRACTION

                
        # df[cls.time_cols] = df[cls.time_cols].apply(cls.parse_edtf_memoised)
        df[filled_time_col] = cls.parse_edtf_memoised(df[filled_time_col])
        
        
        # sorted_df = df
        # for t_col in tqdm(cls.time_cols, desc="sorting by time columns"):
        #     sorted_df = sorted_df.sort_values(by=t_col, kind="stable")
        # sorted_df["sort_rank"] = pd.RangeIndex(1, len(sorted_df)+1)
        
        
        sorted_df = df.sort_index().sort_values(by=filled_time_col, kind="stable")
        sorted_df["sort_rank"] = pd.RangeIndex(1, len(sorted_df)+1)

        return sorted_df

    
    @classmethod
    def get_MKG(cls, metadata_path, image_handler=None, erase_duplicates=False, **metadata):
        df = pd.read_csv(metadata_path).set_index("object_number")

        if image_handler is not None:
            df = df.join(image_handler._obj, how="left")
        else:
            df["image_path"] = ""

        assert ("name" in metadata) and ("id_" in metadata) and ("creation_timestamp" in metadata) and ("language" in metadata)
        df.attrs = metadata
        df.attrs.update(dict(lang=StaticTextTranslator(metadata["language"])))
        df.attrs.update(dict(reverse_names=False))


        ### PARSING
        df = df.apply(cls.parse_lists)
        df.time = cls.parse_edtf_memoised(df.time)
        sorted_df = df.sort_index().sort_values(by="time", kind="stable")
        sorted_df["sort_rank"] = pd.RangeIndex(1, len(sorted_df)+1)

        return sorted_df

    def __init__(self, pandas_obj):
        self._obj = pandas_obj

    ### HELPERS

    # def explode(self, column=None):
    #     if not column: column = self.list_cols
    #     return self._obj.explode(column=column)

    # def explode(self):
    #     for c in self.list_cols:


    # def _explode(self, row):

    def explode(self, col_name):
        if col_name in self.list_cols:
            return self._obj[col_name].explode()
        return self._obj[col_name]
        
    
    def _get_texts(self, r):
        lang = self._obj.attrs["lang"]
        title = r.title if r.title else ""
        description = r.description if r.description else ""
    
        if not title and not description:
            obj_names = r.objectname_label
            mat_names = r.material_label
    
            if isinstance(obj_names, list):
                t = f"{lang.collection_of} {', '.join(obj_names[:-1])} {lang.and_} {obj_names[-1]}"
            else:
                t = f"{obj_names}"
    
            if isinstance(mat_names, list):
                t += f" {lang.made_of} {', '.join(mat_names[:-1])} {lang.and_} {mat_names[-1]}"
            elif mat_names:
                t += f" {lang.made_of} {mat_names}"
            return t
        else:
            return f"{title}\n{description}".strip()


    def get_texts(self):
        return self._obj.fillna("").apply(self._get_texts, axis=1)
    

    ### ROUTE FUNCTIONS

    def get_presentation_records(self, object_numbers=None, as_json=True):   
        lang = self._obj.attrs["lang"]

        sub = self._obj[self.presentation_cols + ["image_path"]].fillna("")
        if object_numbers is not None: sub = sub.loc[object_numbers]
        
        cutoffs = {"title": 100, "description": 500}
        for c, i in cutoffs.items():
            sub[c] = sub[c].apply(
                lambda s: ((s[:i] + " …") if len(s) > i else s)
            )

            
        if not as_json: return sub 


        def all_or_onbekend(val, map_f=lambda x: x):
            if not val:
                return lang.unknown
            elif isinstance(val, str): 
                return map_f(val)
            else: return "; ".join(map(map_f, val))

        def display_attribution(r):
            if r.rights == "rights cleared":
                return r.fillna("UNKNOWN").attribution.replace("UNKNOWN", lang.unknown) # never NaN or of type list
            elif r.rights == "public domain":
                return "CC0"
            else: return "In Copyright" 


        reverse_names = CollectionAccessor.reverse_names if self._obj.attrs["reverse_names"]\
                            else (lambda x: x)
        
        return [{"inventory_number": r.name, 
                 "title": r.title, 
                 "description": r.description,
                 "designer": all_or_onbekend(r.coiner_label, map_f=reverse_names),
                "producer": all_or_onbekend(r.maker_label, map_f=reverse_names),
                 "design_date": CollectionAccessor.human_readable_dates(r.coin_time, 
                                                                        before=lang.before, after=lang.after),
                 "production_date": CollectionAccessor.human_readable_dates(r.creation_time, 
                                                                            before=lang.before, after=lang.after),
                 "design_place": all_or_onbekend(r.coin_place_label),
                 "production_place": all_or_onbekend(r.creation_place_label),
                 "rights_attribution": display_attribution(r),
                 "image_path": r.image_path
                }
                for i, r in sub.iterrows()]


    # @staticmethod
    # def parse_query(query):
    #     return query

    
    def filter(self, text_query, return_df=True, start_time=None, end_time=None, **categorical_values):
        """
         - All operations preserve order (using boolean series, 
         whose order is the same as that of the original DF, to index), so this
         function may readily be used on on sorted (i.e. scored) data. (NOT TESTED)
        """

        # TEXTs
        
        # text_query = self.parse_query(text_query)
        
        text_search_fields = ["objectname_label", "material_label", "maker_label", "coiner_label"]
        
        text_matches = []
        for c in text_search_fields:
            cur_col = self._obj[c].apply(lambda ls: " ".join(ls)) if c in self.list_cols else self._obj[c]
            text_matches.append(cur_col.fillna("").str.contains(text_query, regex=True))

        text_matches.append(self._obj.index.str.contains(text_query, regex=True))
        text_matches.append(self.get_texts().str.contains(text_query, regex=True))

        text_matches = np.sum(text_matches, axis=0).astype(bool)        
        all_matches = [text_matches]

        # TIME WINDOW

        # if start_time or end_time:
        #     window_str = (start_time if start_time else "..") + "/" + (end_time if end_time else "..")
        #     window = parse_edtf(window_str)
        #     time_matches = 

        # CATEGORICAL
        
        # for c, val in categorical_values.items():
        #     # TODO: figure out how to go from labels to URIs (???)
        #     all_matches.append(self._obj[c] == val)
        
        all_matches = np.prod(all_matches, axis=0).astype(bool)

        if not return_df: return pd.Series(all_matches, index=self._obj.index)        
        return self._obj[all_matches]
    
    # def filter(self, text_query, return_df=True, **categorical_values):

    #     fields = object_number, material, objectname, maker_label
        
    #     if not all(c in self.categorical_cols): 
    #         raise ValueError(f"some given categories {categorical_values.keys()} not in {self.categorical_cols}!")

    #     text_query = self.parse_query(text_query)
    #     text_matches = self.get_texts().str.contains(text_query, regex=True)
        
    #     matches = [text_matches]
    #     for c, val in categorical_values.items():
    #         # TODO: figure out how to go from labels to URIs (???)
    #         matches.append(self._obj[c] == val)
    #     matches = np.prod(matches, axis=0).astype(bool)

    #     if not return_df: return pd.Series(matches, index=df.index)        
    #     return df[matches]
            
    
    # def order(self, scores=None):
    #     if scores is None:
    #         return self._obj.sort_values(by="sort_rank")

    #     if (scores.var()**0.5)/(scores.max()-scores.min()) < 0.001:
    #         print("GIVEN SCORES HAVE TOO LITTLE VARIANCE, FALLING BACK TO DEFAULT ORDERING (BY TIME)")
    #         return self._obj.sort_values(by="sort_rank")

    #     sorted_index = scores.sort_values().index
    #     return self._obj.loc[sorted_index]
    
        
    def info(self):
        # open_categories = [c for c in self.categorical_cols 
        #                      if len(exploded[c].value_counts()) > 20]
        # closed_categories = [c for c in self.categorical_cols 
        #                      if len(exploded[c].value_counts()) < 20]
        info = dict(
            name=self._obj.attrs["name"],
            id_=self._obj.attrs["id_"],
            creation_timestamp=self._obj.attrs["creation_timestamp"],
            number_of_records=len(self._obj.index.unique())
            # number_of_attributes=None,
            # categories=self.categorical_cols,
            # open_categories=open_categories,
            # closed_categories={c: sorted(exploded[c].unique()) for c in closed_categories}
        )

        return info





    ###########################
    ### PRESENTATION
    ###########################
    @classmethod
    def reverse_names(cls, s):
        if "&" in s:
            return " & ".join([cls.reverse_names(x) for x in s.split("&")])
        s = s.strip()
        if not s: return ""
        if not ", " in s:
            return s
        b, a = s.split(", ", maxsplit=1)
        return f"{a} {b}"
    
    
    @staticmethod
    def human_readable_dates(s, before, after, ca="ca."):
        if not s:
            return ""
            
        def parse_year(y):
            if y.endswith("~"):
                return f"{ca} " + y[:-1]
            else: return y
        
        if not "/" in s:
            return parse_year(s)

        
        a, b = s.split("/")
    
        if (not a) and (not b):
            return ""
        elif not b:
            return f"{after} " + parse_year(a)
        elif not a:
            return f"{before} " + parse_year(b)
        else:
            return parse_year(a) + " — " + parse_year(b)
    
        raise ValueError(f"time string {y} didn't fit into any known format!")
