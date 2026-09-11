"""
Baselines Module for SpotifyCares AI Support System.
Implements:
1. Trivial Baseline (Majority Class from training data)
2. Weakly Supervised ML Baseline (TF-IDF + Logistic Regression trained on 42k non-golden corpus)
"""

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from src.intent_taxonomy import classify_intent_rule_based

class MajorityClassBaseline:
    """Trivial Baseline: Predicts majority intent from weakly supervised training corpus."""
    def __init__(self):
        self.majority_class = "billing_subscription_dispute"

    def fit(self, X_train, y_train):
        classes, counts = np.unique(y_train, return_counts=True)
        self.majority_class = classes[np.argmax(counts)]

    def predict(self, X_test):
        return [self.majority_class] * len(X_test)

class LogisticRegressionBaseline:
    """
    Weakly Supervised ML Baseline:
    Trained strictly on non-golden historical corpus (42,440 items) using weakly supervised taxonomy labels.
    Evaluated strictly on independent golden_set_v2.json (200 items).
    """
    def __init__(self):
        self.vectorizer = TfidfVectorizer(ngram_range=(1, 2), max_features=5000, stop_words='english')
        self.model = LogisticRegression(max_iter=1000, random_state=42)

    def fit(self, X_train, y_train):
        print(f"Training LogisticRegressionBaseline on {len(X_train):,} weakly supervised historical samples...")
        X_vec = self.vectorizer.fit_transform(X_train)
        self.model.fit(X_vec, y_train)
        print("LogisticRegressionBaseline training complete.")

    def predict(self, X_test):
        X_vec = self.vectorizer.transform(X_test)
        return self.model.predict(X_vec)
