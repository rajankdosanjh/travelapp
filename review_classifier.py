import nltk
import random
import pickle # Used to save the trained model to a file (.pkl)
import pandas as pd
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from sklearn.feature_extraction import DictVectorizer # Converts text features into numerical vectors.
from sklearn.linear_model import LogisticRegression # The machine learning algorithm used for classification.


def document_features(document, word_features): #Feature Extractor Function
    document_words = set(document) # Creates a set of the unique words in the review for efficient lookup.
    features = {}
    for word in word_features: #word_features is a predefined list of the top 2000 words in text (See below)
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

    random.shuffle(documents) #Shuffles the data so the model doesn't learn from any accidental order in the CSV file
    print(f"Loaded and cleaned {len(documents)} labeled reviews for training.")

    # 2. Extracts Features
    all_words = nltk.FreqDist(w for (doc, cat) in documents for w in doc)    #Frequency distribution of all words across all reviews to find the most common ones
    word_features = list(all_words)[:2000]

    # Separates features and labels
    feature_dicts = [document_features(d, word_features) for (d, c) in documents] #takes key words (from word_features) as dictionary key and the sentiment as the value. repeats this for every tweet to create a list of dictionaries
    labels = [c for (d, c) in documents]
    print("Created feature sets.")

    # 3. Vectorizes Features and Trains the Classifier
    vectorizer = DictVectorizer(sparse=False) #Vectorizer turns feature dictionaries into a numerical array
    X_train = vectorizer.fit_transform(feature_dicts) #fits training data and then applies binary numbers

    classifier = LogisticRegression()
    classifier.fit(X_train, labels)     # Trains the model by fitting it to the numerical features (X_train) and the corresponding labels
    print("Classifier training complete.")

    # 4. Saves the Classifier, Vectorizer, and Word Features in a dictionary - needed to predict new, unseen data
    model_data = {
        "classifier": classifier,
        "vectorizer": vectorizer,
        "word_features": word_features
    }
    with open('sentiment_classifier.pkl', 'wb') as f:
        pickle.dump(model_data, f)  # Uses pickle to serialize the model_data dictionary and save it to the file sto avoid repeatedly training the model everytime the app runs
    print("Classifier, vectorizer, and word features saved to sentiment_classifier.pkl")


if __name__ == '__main__':
    train_and_save_classifier()