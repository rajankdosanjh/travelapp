import unittest
import pickle
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
from nltk.tokenize import word_tokenize
from review_classifier import document_features

class TestSentimentClassifier(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """Load the trained model and data once for all tests."""
        print("--- Loading Saved Classifier and Test Data ---")
        try:
            with open('sentiment_classifier.pkl', 'rb') as f:
                cls.model_data = pickle.load(f)
        except FileNotFoundError:
            raise unittest.SkipTest("sentiment_classifier.pkl not found. Run review_classifier.py to create it.")

        cls.classifier = cls.model_data['classifier']
        cls.vectorizer = cls.model_data['vectorizer']
        cls.word_features = cls.model_data['word_features']

        # Load and prepare the dataset for performance testing
        df = pd.read_csv('app/data/tweets.csv')
        df.dropna(subset=['tweet_text', 'sentiment'], inplace=True)
        df = df[df['sentiment'] != 'neutral']

        cls.documents = []
        for index, row in df.iterrows():
            words = word_tokenize(row['tweet_text'])
            cleaned_words = [w.lower() for w in words if w.isalpha()]
            cls.documents.append((cleaned_words, row['sentiment']))


    def test_single_positive_prediction(self):
        """Test the classifier on a sample positive review."""
        text = "This place is absolutely amazing and wonderful, I loved it."
        words = [w.lower() for w in word_tokenize(text) if w.isalpha()]
        features = document_features(words, self.word_features)
        vectorized_features = self.vectorizer.transform([features])
        prediction = self.classifier.predict(vectorized_features)
        self.assertEqual(prediction[0], 'positive')
        print(f"Positive prediction test passed for: '{text}'")

    def test_single_negative_prediction(self):
        """Test the classifier on a sample negative review."""
        text = "It was a terrible and dreadful experience, I hated everything."
        words = [w.lower() for w in word_tokenize(text) if w.isalpha()]
        features = document_features(words, self.word_features)
        vectorized_features = self.vectorizer.transform([features])
        prediction = self.classifier.predict(vectorized_features)
        self.assertEqual(prediction[0], 'negative')
        print(f"Negative prediction test passed for: '{text}'")

    def test_classifier_performance_on_dataset(self):
        """Evaluate the classifier's performance on the full dataset."""
        feature_dicts = [document_features(d, self.word_features) for (d, c) in self.documents]
        labels = [c for (d, c) in self.documents]

        X = self.vectorizer.transform(feature_dicts)
        y = labels

        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

        predictions = self.classifier.predict(X_test)

        print("\n--- Classifier Performance Report ---")
        report = classification_report(y_test, predictions, output_dict=True)
        print(classification_report(y_test, predictions))
        print("-------------------------------------\n")

        # Check if the F1-score for both classes is above a reasonable threshold (e.g., 0.7)
        self.assertGreater(report['positive']['f1-score'], 0.7)
        self.assertGreater(report['negative']['f1-score'], 0.7)

if __name__ == '__main__':
    unittest.main()