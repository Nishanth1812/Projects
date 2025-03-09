import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from gensim.models import Word2Vec
import numpy as np

# Load dataset
data = pd.read_csv("data/udemy_courses.csv")
data.drop_duplicates(inplace=True)
data["course_data"] = data["course_title"].astype(str) + " " + data["subject"].astype(str)
data.drop(["course_id", "is_paid"], axis=1, inplace=True)

# TF-IDF Vectorization
vectorizer = TfidfVectorizer(stop_words="english", max_features=2000)
tf_idf = vectorizer.fit_transform(data["course_data"])

# Word2Vec Model
tokenized_courses = data["course_data"].apply(lambda x: x.split())
w2vec = Word2Vec(sentences=tokenized_courses, vector_size=100, window=5, min_count=1, workers=4)

# Embedding Function
def embedding_(text):
    words = text.split()
    vecs = [w2vec.wv[word] for word in words if word in w2vec.wv]
    return np.mean(vecs, axis=0) if vecs else np.zeros(100)

# Apply Embeddings
data["embedding"] = data["course_data"].apply(embedding_)
word2vec_matrix = np.vstack(data["embedding"].values)

# Combine Features
combined_f = np.hstack([tf_idf.toarray(), word2vec_matrix])
