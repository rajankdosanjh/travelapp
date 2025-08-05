import nltk
import random
import pickle
import pandas as pd
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from sklearn.feature_extraction import DictVectorizer
from sklearn.linear_model import LogisticRegression


def document_features(document, word_features): #Checks which of the most common words are present in a given document.
    document_words = set(document)
    features = {}
    for word in word_features:
        features['has({})'.format(word)] = (word in document_words)
    return features


def train_and_save_classifier(): #Trains a Logistic Regression classifier on the labeled data in tweets.csv and saves the classifier, vectorizer, and word features.
    print("--- Starting Classifier Training on tweets.csv ---")

    # 1. Loads and Preprocesses Labeled Data from the CSV
    stop_words = set(stopwords.words('english'))
    df = pd.read_csv('app/data/tweets.csv')
    df.dropna(subset=['tweet_text', 'sentiment'], inplace=True)
    df = df[df['sentiment'] != 'neutral']

    documents = []
    for index, row in df.iterrows():
        words = word_tokenize(row['tweet_text'])
        cleaned_words = [w.lower() for w in words if w.isalpha() and w.lower() not in stop_words]
        documents.append((cleaned_words, row['sentiment']))

    random.shuffle(documents)
    print(f"Loaded and cleaned {len(documents)} labeled reviews for training.")

    # 2. Extracts Features
    all_words = nltk.FreqDist(w for (doc, cat) in documents for w in doc)
    word_features = list(all_words)[:2000]

    # Separates features and labels
    feature_dicts = [document_features(d, word_features) for (d, c) in documents]
    labels = [c for (d, c) in documents]
    print("Created feature sets.")

    # 3. Vectorizes Features and Train the Classifier
    vectorizer = DictVectorizer(sparse=False)
    X_train = vectorizer.fit_transform(feature_dicts)

    classifier = LogisticRegression()
    classifier.fit(X_train, labels)
    print("Classifier training complete.")

    # 4. Saves the Classifier, Vectorizer, and Word Features
    model_data = {
        "classifier": classifier,
        "vectorizer": vectorizer,
        "word_features": word_features
    }
    with open('sentiment_classifier.pkl', 'wb') as f:
        pickle.dump(model_data, f)
    print("Classifier, vectorizer, and word features saved to sentiment_classifier.pkl")


if __name__ == '__main__':
    train_and_save_classifier()