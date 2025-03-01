from dataclasses import dataclass
import pandas as pd
import numpy as np
import tensorflow as tf
import matplotlib.pyplot as plt
import seaborn as sb
import nltk
import string
import pickle
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

class recModel :
    def __init__(self) : pass
    def search(self, q, data):
        df, df_combine_only, combine_arr, title_arr, t_arr = prepDataBase(data)
        docs_combine_clean = cleanData(combine_arr)
        docs_title_clean = cleanData(title_arr)
        docs_t_clean = cleanData(t_arr)

        tfidf_t, feature_vectors_t, vocab_t = prepDBModel(docs_t_clean)
        tfidf_title, feature_vectors_title, vocab_title = prepDBModel(docs_title_clean)
        tfidf_combine, feature_vectors_combine, vocab_combine = prepDBModel(docs_combine_clean)
        query_title_clean, query_combine_clean = cleanGetQuery(q)
        query_feature_vector_t, query_feature_vector_title, query_feature_vector_combine = prepQueryModel(
            tfidf_t, tfidf_title, tfidf_combine, 
            query_title_clean, query_combine_clean, 
            vocab_t, vocab_title, vocab_combine)
        sorted_series, goodResult = getSimilarity(query_feature_vector_t, feature_vectors_t, 
                                                query_feature_vector_title, feature_vectors_title, 
                                                query_feature_vector_combine, feature_vectors_combine, 
                                                df, q)
        resultFoodEntryId = getResult(sorted_series, df_combine_only, combine_arr)
        resultFoodEntryId.append(goodResult)
        return resultFoodEntryId

def recmodel():
    recModel_ = recModel()
    modelFile = open("recmodel", "wb")
    pickle.dump(recModel_, modelFile)

def prepDataBase(data):
    df = data
    def rename_ontrack(x):
        if (x == 1):
            return "ontrack"
        elif (x == 0):
            return "offtrack"
    df["track_score"] = df["track_score"].apply(rename_ontrack)
    df_combine = df.copy()
    df_combine["combine"] = df_combine["title"] + ", " + df_combine["description"] + ", " + df_combine["track_score"]+ ", " + df_combine["feeling"]
    df_combine["title_desc"] = df_combine["title"] + ", " + df_combine["description"]

    #To compare title only
    df_t_only = df_combine.loc[:,["id", "title"]]
    t_arr = df_t_only["title"].values
    #To compare titledesc only
    df_title_only = df_combine.loc[:,["id", "title_desc"]]
    title_arr = df_title_only["title_desc"].values
    #To compare full query
    df_combine_only = df_combine.loc[:, ["id", "combine"]]
    combine_arr = df_combine_only["combine"].values
    return df, df_combine_only, combine_arr, title_arr, t_arr

def preprocess(docs):
    lemmatizer = WordNetLemmatizer()
    stop_words = stopwords.words("english")
    docs_clean = []
    punc = str.maketrans("", "", string.punctuation)
    for doc in docs:
        doc_no_punc = doc.translate(punc)
        words = doc_no_punc.lower().split()
        words = [lemmatizer.lemmatize(word, 'n')
                for word in words if word not in stop_words]
        docs_clean.append(' '.join(words))

    return docs_clean

def cleanData(combine_arr):
    docs_clean = preprocess(combine_arr)
    return docs_clean

def prepDBModel(docs_clean):
    tfidf = TfidfVectorizer()
    feature_vectors = tfidf.fit_transform(docs_clean).toarray()
    vocab = tfidf.get_feature_names()
    df_vocab = pd.DataFrame(data=feature_vectors,
                    columns=vocab)
    return tfidf, feature_vectors, vocab

def cleanGetQuery(q):
    query_title = [q[0]]
    #combine = title + track + feeling
    query_combine = [q[0] + ", " + q[2] + ", " + q[1]]
    cleaned = []
    for query in [query_title, query_combine]:
        query_clean = preprocess(query)
        if ("cry" in query_clean[0] or "pensive" in query_clean[0]):
            query_clean[0] = query_clean[0].replace("cry", "")
            query_clean[0] = query_clean[0].replace("pensive", "")
            query_clean[0] = query_clean[0] + " happy joy"
        query_clean[0] = " ".join(query_clean[0].split())
        query = query_clean
        print(query)
        cleaned.append(query)
        
    return(cleaned[0], cleaned[1])

def prepQueryModel(tfidf_t, tfidf_title, tfidf_combine, query_title_clean, query_combine_clean, vocab_t, vocab_title, vocab_combine):

    #title only
    query_feature_vector_t = tfidf_t.transform(query_title_clean).toarray()
    query_t_df = pd.DataFrame(data=query_feature_vector_t,
                        columns=vocab_t)

    #titledesc only
    query_feature_vector_title = tfidf_title.transform(query_title_clean).toarray()
    query_title_df = pd.DataFrame(data=query_feature_vector_title,
                        columns=vocab_title)

    #combine
    query_feature_vector_combine = tfidf_combine.transform(query_combine_clean).toarray()
    query_combine_df = pd.DataFrame(data=query_feature_vector_combine,
                        columns=vocab_combine)

    return query_t_df, query_title_df, query_combine_df

def getSimilarity(query_feature_vector_t, feature_vectors_t, 
                    query_feature_vector_title, feature_vectors_title, 
                    query_feature_vector_combine, feature_vectors_combine, 
                    df, q):


    t_similarity = np.array(cosine_similarity(query_feature_vector_t, feature_vectors_t))
    title_similarity = np.array(cosine_similarity(query_feature_vector_title, feature_vectors_title))
    combine_similarity = np.array(cosine_similarity(query_feature_vector_combine, feature_vectors_combine))
    print(len(t_similarity[0]))
    print(len(title_similarity[0]))
    print(len(combine_similarity[0]))

    t_similarity_arr = t_similarity[0]
    title_similarirty_arr = title_similarity[0]
    combine_similarity_arr = combine_similarity[0]

    query_similarity = t_similarity[0]
    goodResults = "false"

    for x in range(len(t_similarity[0])):
        #title and/or desc good enough
        if (t_similarity_arr[x] > 0.3 or title_similarirty_arr[x] > 0.3):
            if (t_similarity_arr[x] > 0.3):
                query_similarity[x] = 0.5*t_similarity_arr[x] + 0.5*title_similarirty_arr[x]
            else:
                query_similarity[x] = title_similarirty_arr[x]
            query_similarity[x] *= 1.5
        elif (combine_similarity_arr[x] > 0.3):
            query_similarity[x] = combine_similarity_arr[x]
        else: 
            query_similarity[x] = combine_similarity_arr[x]

        out = query_similarity[x]
        weight = query_similarity[x]/4
        if (weight < 0.1):
            weight = 0.1

        feel = df.loc[x,'feeling'].lower()
        track = df.loc[x,'track_score'].lower()
        if (track == q[2]):
            out += weight

        if ((q[1] != "cry" and q[1] != "pensive")):
            out += weight
        #if user is sad, add more weights to joy and happy entries
        if (q[1] == "cry" or q[1] == "pensive"):
            if (feel == "joy"):
                out += (2*weight)
            elif (feel == "happy"):
                out += weight

        query_similarity[x] = out

    #case 0 (check if title only is good enough)
    # if (t_similarity[0].max() > 0.3):
    #     goodResults = "true"
    #     query_similarity = t_similarity[0]
    #     print("word search 0: " + goodResults)
    #     print(t_similarity[0].max())

    # #case 1 (check if title + desc only is good enough)
    # if (t_similarity[0].max() > 0.3 or title_similarity[0].max() > 0.3):
    #     goodResults = "true"
    #     if (t_similarity[0].max() > 0.3):
    #         print("title is good")
    #         query_similarity = 0.5*t_similarity[0] + 0.5*title_similarity[0]
    #     else:
    #         print("only desc is good")
    #         query_similarity = title_similarity[0]
    #     print("word search 1: " + goodResults)
    #     query_similarity = query_similarity * 1.5
    #     print(query_similarity.max())
        
    # #case 2 (check if combine is good enough)
    # elif (combine_similarity[0].max() > 0.3):
    #     goodResults = "true"
    #     query_similarity = combine_similarity[0]
    #     print("word search 2: " + goodResults)
    #     query_similarity = query_similarity * 1.25
    #     print(combine_similarity[0].max())
    
    # #case 3 (all not enough)
    # else: 
    #     goodResults = "false"
    #     query_similarity = combine_similarity[0]
    #     print("word search 3: " + goodResults)

    # # query_sim_pass = query_similarity[query_similarity > 0.3]
    # # query_avg = query_sim_pass.mean()
    # # print(query_sim_pass)
    # # print(query_avg)
    # #max_sim = query_similarity.max()
    # #print(max_sim)
    # #weight = query_avg/4

    # print("adding weights")
    # print(len(query_similarity))
    # for x in range(len(query_similarity)):
    #     out = query_similarity[x]
    #     weight = query_similarity[x]/4

    #     feel = df.loc[x,'feeling'].lower()
    #     track = df.loc[x,'track_score'].lower()
    #     if (track == q[2]):
    #         out += weight

    #     if ((q[1] != "cry" and q[1] != "pensive")):
    #         out += weight
    #     #if user is sad, add more weights to joy and happy entries
    #     if (q[1] == "cry" or q[1] == "pensive"):
    #         if (feel == "joy"):
    #             out += (2*weight)
    #         elif (feel == "happy"):
    #             out += weight

    #     query_similarity[x] = out

    series = pd.Series(query_similarity, index=df.index)
    sorted_series = series.sort_values(ascending=False)

    # if (len(sorted_series[sorted_series > 0.3]) >= 5):
    #     print("good more than 5")
    #     goodResults = "true"
    #shuffle top 10 and get 5
    sorted_series_10 = sorted_series[sorted_series > 0.45].head(10)
    print(sorted_series.head(10))
    if (len(sorted_series_10) == 0):
        goodResults = "false"
        sorted_series_shuff = sorted_series.sample(frac=1)
        sorted_series_out = sorted_series_shuff.head(5).sort_values(ascending=False)
    #if dont have at least 5 scores > 0.3, result is not good
    elif (len(sorted_series_10) < 5):
        goodResults = "false" 
        print("more than 5 good: " + goodResults)
        sorted_series_out = sorted_series[sorted_series != 0].head(5).sort_values(ascending=False)
    else:
        print("good more than 5")
        goodResults = "true"
        sorted_series_shuff = sorted_series_10.sample(frac=1)
        sorted_series_out = sorted_series_shuff.head(5).sort_values(ascending=False)

    #final check if no keyword input, goodResults is true
    if (preprocess([q[0]])[0] == ""):
        goodResults = "true"

    #final check if not enough data, goodResults is false
    if (len(df) < 50):
        goodResults = "false"

    return sorted_series_out, goodResults

def getResult(sorted_series, df_combine_only, combine_arr):
    resultFoodEntryId = []
    print("Search results: \n")
    for index in sorted_series.index:
        resultFoodEntryId.append(df_combine_only.loc[index, "id"])
        print(combine_arr[index], " [score = ", sorted_series[index], "] ", "[FoodEntryId = ", df_combine_only.loc[index, "id"], "]", sep=" ")
    return resultFoodEntryId