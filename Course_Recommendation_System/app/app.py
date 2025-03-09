from flask import Flask, jsonify, request
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from gensim.models import Word2Vec
from sklearn.preprocessing import normalize
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  

data = pd.read_csv(r"C:\Users\Devab\OneDrive\Desktop\Course_Recommendation_System\data\udemy_courses.csv")
data.drop_duplicates(inplace=True)
data["course_data"] = data["course_title"].astype(str) + " " + data["subject"].astype(str)
data.drop(["course_id", "is_paid"], axis=1, inplace=True)

vectorizer = TfidfVectorizer(stop_words="english", max_features=2000)
tf_idf = vectorizer.fit_transform(data["course_data"])


tokenized_courses = data["course_data"].apply(lambda x: x.split())  # Tokenize text
w2vec = Word2Vec(sentences=tokenized_courses, vector_size=100, window=5, min_count=1, workers=4)


def embedding_(text):
    words = text.split()  
    vecs = [w2vec.wv[word] for word in words if word in w2vec.wv]
    
    if len(vecs) > 0:
        return np.mean(vecs, axis=0) 
    else:
        return np.zeros(100)  

data["embedding"] = data["course_data"].apply(embedding_)
word2vec_matrix = np.vstack(data["embedding"].values)

combined_f = np.hstack([tf_idf.toarray(), word2vec_matrix])


@app.route("/recommend", methods=["POST"])
def recommend():
    try:
        input_data = request.json
        input_title = input_data.get("course_title", "")

        if not input_title:
            return jsonify({"error": "Course title is required"}), 400

        
        tfidf_title = vectorizer.transform([input_title]).toarray()
        w2vec_title = embedding_(input_title).reshape(1, -1)

        
        nor_tfidf_title = normalize(tfidf_title)
        nor_w2vec_title = normalize(w2vec_title)

        
        combined_vec = np.concatenate([nor_tfidf_title, nor_w2vec_title], axis=1)

        
        similarity = cosine_similarity(combined_vec, combined_f)
        data["similarity"] = similarity.flatten()

    
        data["popularity_rating"] = data.apply(
            lambda row: min(5, (0.6 * (row["num_subscribers"] / 10000)) + (0.4 * (row["num_reviews"] / 500))),
            axis=1
        )

        
        recommended_courses = data.sort_values(by=["similarity", "popularity_rating"], ascending=[False, False]).head(5)

    
        recommendations = []
        for _, row in recommended_courses.iterrows():
            recommendations.append({
                "course_title": row["course_title"],
                "subject": row["subject"],
                "published_date": str(row["published_timestamp"]),  # Convert datetime to string
                "price": row["price"],
                "subscribers": int(row["num_subscribers"]),
                "reviews": int(row["num_reviews"]),
                "popularity_rating": round(row["popularity_rating"], 2)
            })

        return jsonify({"recommendations": recommendations})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
