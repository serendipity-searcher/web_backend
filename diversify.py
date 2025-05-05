import numpy as np



class Diversifier:
    def __init__(self):
        pass



class UniformDiversifier:
    def __init__(self, coll):
        self.num_cats = len(df[cat_name].unique())


    def __call__(self, scores, cat_name):
        new_probs = df.groupby(cat_name).apply(lambda sub: sub.score/sub.score.sum()/num_cats)
        return new_probs.reset_index(cat_name).score.sort_index()




# diversify
def unif_renorm(df, cat_name):
    num_cats = len(df[cat_name].unique())
    new_probs = df.groupby(cat_name).apply(lambda sub: sub.score/sub.score.sum()/num_cats)
    return new_probs.reset_index(cat_name).score.sort_index()



def bayes_renorm(df, cat_name):
    cat_probs = df[cat_name].value_counts()/len(df)
    new_probs = df.groupby(cat_name).apply(lambda sub: sub.score/sub.score.sum()*cat_probs.loc[sub.name])
    return new_probs.reset_index(cat_name).score.sort_index()


def bayes_renorm_multiclass(df, *cat_names):
    cat_probs = {c: df[c].value_counts()/len(df) for c in cat_names}
    def get_prob(row):
        ps = [c_prob.loc[row[c]] for c, c_prob in cat_probs.items()]
        return row.score * np.prod(ps)
    new_probs = df.apply(get_prob, axis=1)
    new_probs = new_probs/new_probs.sum()
    return new_probs.reset_index(cat_name).score.sort_index()
