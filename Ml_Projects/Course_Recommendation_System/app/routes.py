from flask import Blueprint, render_template, request, jsonify
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import normalize
from .preprocess import data, vectorizer, embedding_, combined_f

main = Blueprint('main', __name__)

@main.route("/")
def home():
    return render_template("index.html")

@main.route("/results")
def results():
    return render_template("results.html")

@main.route("/recommend", methods=["POST"])
def recommend():
    try:
        input_data = request.json
        input_title = input_data.get("course_title", "").strip()

        if not input_title:
            return jsonify({"error": "Course title is required"}), 400

        # Compute TF-IDF & Word2Vec embeddings
        tfidf_title = vectorizer.transform([input_title]).toarray()
        w2vec_title = embedding_(input_title).reshape(1, -1)

        # Normalize features
        nor_tfidf_title = normalize(tfidf_title)
        nor_w2vec_title = normalize(w2vec_title)

        # Combine features
        combined_vec = np.concatenate([nor_tfidf_title, nor_w2vec_title], axis=1)

        # Compute similarity
        similarity = cosine_similarity(combined_vec, combined_f)
        data["similarity"] = similarity.flatten()

        # Popularity metric
        data["popularity_rating"] = data.apply(
            lambda row: min(5, (0.6 * (row["num_subscribers"] / 10000)) + (0.4 * (row["num_reviews"] / 500))),
            axis=1
        )

        # Get top 5 recommendations
        recommended_courses = data.sort_values(by=["similarity", "popularity_rating"], ascending=[False, False]).head(5)

        # Format recommendations
        recommendations = []
        for _, row in recommended_courses.iterrows():
            recommendations.append({
                "course_title": row["course_title"],
                "subject": row["subject"],
                "published_date": str(row.get("published_timestamp", "")),  # Handle missing timestamps
                "price": row["price"],
                "subscribers": int(row["num_subscribers"]),
                "reviews": int(row["num_reviews"]),
                "popularity_rating": round(row["popularity_rating"], 2)
            })

        return jsonify({"recommendations": recommendations})

    except Exception as e:
        print("Error in recommendation:", str(e))  # Print error in terminal
        return jsonify({"error": str(e)}), 500
