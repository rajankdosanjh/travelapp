import csv
import pickle
from app import app, db
from app.models import Location, Review, User
from nltk.tokenize import word_tokenize


def document_features(document, word_features):
    document_words = set(document)
    features = {}
    for word in word_features:
        features['has({})'.format(word)] = (word in document_words)
    return features


def classify_review(text, classifier, vectorizer, word_features):
    if not text:
        return 0.0

    cleaned_words = [w.lower() for w in word_tokenize(text) if w.isalpha()]

    features = document_features(cleaned_words, word_features)

    # Uses the vectorizer to transform the new features
    X_new = vectorizer.transform([features])

    # Gets probabilities from the classifier
    prob_dist = classifier.predict_proba(X_new)[0]

    # Finds the probabilities for 'positive' and 'negative' classes
    pos_index = list(classifier.classes_).index('positive')
    neg_index = list(classifier.classes_).index('negative')

    prob_pos = prob_dist[pos_index]
    prob_neg = prob_dist[neg_index]

    # Calculates a compound score
    nuanced_score = prob_pos - prob_neg
    return nuanced_score


def reset_db():
    with app.app_context():
        try:
            print("--- Dropping all database tables... ---")
            db.drop_all()
            print("--- Creating all database tables... ---")
            db.create_all()

            #Loads the classifier, vectorizer, and word features
            print("--- Loading custom sentiment classifier and features... ---")
            with open('sentiment_classifier.pkl', 'rb') as f:
                model_data = pickle.load(f)
                classifier = model_data["classifier"]
                vectorizer = model_data["vectorizer"]
                word_features = model_data["word_features"]
            print("--- Model loaded successfully. ---")

            # 1. Loads Locations
            locations_csv_path = 'app/data/locations.csv'
            with open(locations_csv_path, mode='r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    location = Location(
                        id=int(row['id']),
                        name=row['name'],
                        latitude=float(row['latitude']),
                        longitude=float(row['longitude']),
                        category_id=int(row['category_id']),
                    )
                    db.session.add(location)
            print(f"--- Loaded locations from {locations_csv_path} ---")
            db.session.commit()

            # 2. Loads Reviews and Calculate Sentiment
            tweets_csv_path = 'app/data/tweets.csv'
            with open(tweets_csv_path, mode='r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # --- THIS IS THE FIX ---
                    # Skips any row where the location_id is not a digit (i.e., the header row)
                    if not row['location_id'].isdigit():
                        continue

                    review_text = row['tweet_text']

                    # Uses classifier to get the nuanced sentiment score
                    nuanced_sentiment_score = classify_review(review_text, classifier, vectorizer, word_features)

                    review = Review(
                        location_id=int(row['location_id']),
                        text=review_text,
                        sentiment=nuanced_sentiment_score,
                        username=row['username']
                    )
                    db.session.add(review)
            print(f"--- Loaded and analyzed reviews from {tweets_csv_path} ---")
            db.session.commit()

            users_csv_path = 'app/data/users.csv'
            with open(users_csv_path, mode='r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    user = User(
                        name = row['name'],
                        username = row['username'],
                    )
                    user.set_password(row['password'])
                    db.session.add(user)
            print(f"--- Loaded users from {users_csv_path} ---")
            db.session.commit()


            print("--- Database reset and population complete. ---")

        except Exception as e:
            print(f"An error occurred during database reset: {e}")
            db.session.rollback()