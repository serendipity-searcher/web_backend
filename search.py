from glob import glob
from tqdm import tqdm
import os.path


import numpy as np
import numpy.random as rand
from scipy.stats import spearmanr

import csv
import pandas as pd

import matplotlib.pyplot as plt
import seaborn as sns
import imageio.v3 as iio
# from PIL import Image


# import torch
# from sentence_transformers import SentenceTransformer, util


from collections import Counter
import networkx as nx



class Search:
    def __init__(self, searchers):
        self.searchers = searchers
        self.cur_recs = None
        self.cur_scores = None

    def cache_search(self, recs, searcher_ids, scores):
        self.cur_recs = recs
        self.cur_searcher_ids = searcher_ids
        self.cur_scores = scores

    def get_cached_search(self, recs, searcher_ids):
        if recs.equals(self.cur_recs) and (searcher_ids == self.cur_searcher_ids):
            return self.cur_scores
        return None
    
    def __call__(self, recs, searcher_ids=None, return_df=False):
        cached_scores = self.get_cached_search(recs, searcher_ids)
        if cached_scores is not None: return cached_scores
        
        if searcher_ids is not None:
            if len(searcher_ids) < 1:
                raise ValueError("Searching with no searcher (aka model) not defined! (This logic is implemented externally.)")
            else:
                cur_searchers = [s for s in self.searchers for s_id in searcher_ids if id(s) == s_id]
        else:
            cur_searchers = self.searchers
            
        searcher_scores = [s(recs) for s in self.searchers]
        searcher_scores = pd.DataFrame({s.name: s for s in searcher_scores})
        searcher_scores.loc[recs.index] = 0.
        
        merged_scores = self.merge_scores(searcher_scores)        

        self.cache_search(recs, searcher_ids, merged_scores)
        
        if return_df:
            searcher_scores["avg"] = merged_scores
            return searcher_scores
        return merged_scores 

    
    def merge_scores(self, scores):
        return scores.mean(axis=1)


    def sample(self, coll, scores=None, temp=1.0, size=1):
        assert (self.cur_scores is not None) or (scores is not None)
        if scores is None: 
            scores = self.cur_scores 
        tempered_scores = np.exp((scores/temp))
        tempered_scores = tempered_scores/tempered_scores.sum()
        return coll.sample(n=size, weights=tempered_scores)
        # return rand.choice(coll.index, p=tempered_scores, size=size)


    def order(self, coll, scores=None, reverse=False):
        assert (self.cur_scores is not None) or (scores is not None)
        if scores is None: 
            scores = self.cur_scores

        sort_idx = scores.argsort()
        if reverse:
            return coll.iloc[sort_idx].iloc[::-1]
        return coll.iloc[sort_idx]

    
class Searcher:
    serial_number = 0
    def __init__(self, name):
        self.name = name

        self.id = name + str(Searcher.serial_number)
        Searcher.serial_number += 1

    def __id__(self):
        print("HELLO", self)
        return self.id


class Randomiser(Searcher):
    def __init__(self, coll, name="Randomiser"):
        super().__init__(name)
        self.index = coll.index

    def __call__(self, records):
        rand_scores = pd.Series(rand.random(size=len(self.index)), index=self.index, name=self.id)
        return rand_scores


class GraphSearcher(Searcher):
    @staticmethod
    def iter_values(r):
        for v in r:
            if isinstance(v, list): yield from v
            elif v: yield v
            else: pass
    
    def _build(self, collection):
        pbar = tqdm(collection[collection.coll.categorical_cols].iterrows(), 
                    total=len(collection), desc='[GraphSearcher]: building graph...')
        cat_obj_links = [(r.name, v) for i, r in pbar for v in GraphSearcher.iter_values(r)]
        
        pbar = tqdm(collection[collection.coll.categorical_cols].iterrows(), 
                    total=len(collection), desc='[GraphSearcher]: building graph...')
        cat_cat_links = [tuple(sorted((v1, v2)))for i, r in pbar 
                         for v1 in GraphSearcher.iter_values(r) for v2 in GraphSearcher.iter_values(r) 
                         if (v1 and v2) and (not v1 == v2)]
        return nx.from_edgelist(cat_obj_links+list(set(cat_cat_links)))
    
    def __init__(self, coll, name="KGSearcher"):
        super().__init__(name)    
        
        self.obj_nodes = set(coll.index)
        self.G = self._build(coll)

    
    def __call__(self, records):
        assert all((obj_num in self.obj_nodes) for obj_num in records.index)
        
        dists = [nx.shortest_path_length(self.G, source=objnum, target=None) for objnum in records.index]

        raw_scores = pd.Series([np.mean([(d[obj_num] if obj_num in d else 10) for d in dists]) for obj_num in self.obj_nodes], 
                       index=self.obj_nodes, name=self.id)
        return self.dist2sim(raw_scores)

    @staticmethod
    def unit_norm(s):
        unit_normed = (s - s.min())/(s.max()- s.min())
        return unit_normed #/unit_normed.sum()

    @staticmethod
    def dist2sim(d):
        return GraphSearcher.unit_norm(d.max() - d)


class EmbeddingSearcher(Searcher):
    # @classmethod
    # def load(cls, emb_dir, loadXD, **init_kwargs):
    #     if loadXD:
    #         emb = pd.read_csv(f"{emb_dir}/embs_umap_{loadXD}D.csv").set_index("object_number")#.sort_index()
    #     else:
    #         emb = pd.concat([pd.read_csv(f) for f in tqdm(sorted(glob(f"{emb_dir}/embs_batch_*.csv")))]).set_index("object_number")#.sort_index()
    #     return cls(emb, **init_kwargs)
    
    @staticmethod
    def unit_norm(s):
        unit_normed = (s - s.min())/(s.max()- s.min())
        return unit_normed #/unit_normed.sum()
    
    @staticmethod
    def USE_sim(p, vs):
        return 1 - torch.arccos(
                            torch.clamp(
                                util.cos_sim(p, vs), -1, 1
                            )
                        )/torch.pi

    # @staticmethod
    # def euclidean_sim(p, v2):
    #     return 1-(((p-v2)**2).sum(0))**0.5

    
    @staticmethod
    def euclidean_sim(p, v2):
        return 1-torch.cdist(torch.as_tensor(p), torch.tensor(v2))


    
    def __init__(self, space_df, sim_func=None, norm_scores=True, name="EmbeddingSeacher"):
        super().__init__(name)
        sim_funcs = dict(cos=util.cos_sim, dot=util.dot_score, USE=self.USE_sim, euclid=self.euclidean_sim)
        if sim_func is None:
            sim_func = "USE"
            
        self.space = space_df
        self.f = sim_funcs[sim_func]
        self.do_norm = norm_scores


    def rank_vector(self, vec):
        point = torch.as_tensor(vec)
        sims = self.f(point, self.space.to_numpy()).numpy().reshape((-1,))    
        return self.unit_norm(sims) if self.do_norm else sims
    
    # def rank_multiple_vectors(self, vecs):
    #     return self.rank_vector(vecs.mean(axis=0))

    def rank_multiple_vectors(self, vecs):
        sims = self.f(vecs, self.space.values) # shape = (len(vecs), len(self.space))
        sims_pool = sims.mean(axis=0).numpy()
        return self.unit_norm(sims_pool) if self.do_norm else sims

    def __call__(self, records):
        vecs = self.space.loc[records.index].to_numpy()
        return pd.Series(self.rank_multiple_vectors(vecs), 
                         index=self.space.index, name=self.name)
    
    def get_neighbours(self, vecs, k):    
        sims = self.rank_multiple_vectors(vecs)
        inds = list(reversed(np.argsort(sims)))
        sims, inds = sims[inds][:k], inds[:k]

        neigh_index = self.space.iloc[inds].index
        neigh_embs = self.space.loc[neigh_index]
        
        # cur_coll = coll.iloc[inds]
        # cur_embs = self.space[inds] #.numpy()[inds]
        
        return neigh_index, neigh_embs, sims




class TextEmbeddingSearcher(EmbeddingSearcher):
    def __init__(self, space_df, sim_func=None, norm_scores=True, name="TextEmbeddingSeacher"):
        super().__init__(space_df, sim_func, norm_scores, name)
        self.embedder = SentenceTransformer('distiluse-base-multilingual-cased-v2')
        
    def __call__(self, text):
        vec = self.embedder.encode(text)
        return pd.Series(self.rank_vector(vec), index=self.space.index, name=self.id)

  