#!/usr/bin/env python3
"""
Domain Classifier Training Script for Galatea

This script trains a simple but effective domain classifier using:
- Sentence Transformers for embeddings
- Logistic Regression for classification

The resulting model is small (~100MB) and fast enough to run alongside
the main LLM without noticeable latency.

Usage:
    python train_classifier.py

Requirements:
    pip install sentence-transformers scikit-learn numpy

Output:
    - domain_classifier.pkl (sklearn model)
    - domain_embedder/ (sentence transformer model, optional for optimization)
"""

import json
import pickle
from pathlib import Path
from typing import List, Tuple

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import classification_report, confusion_matrix
from sentence_transformers import SentenceTransformer

# Configuration
TRAINING_DATA = "domain_classifier_train.jsonl"
OUTPUT_MODEL = "domain_classifier.pkl"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"  # Small, fast, good quality
# Alternative: "all-mpnet-base-v2" for better accuracy but larger size

DOMAINS = ["general", "medical", "legal", "coding", "math", "finance"]


def load_training_data(filepath: str) -> Tuple[List[str], List[str]]:
    """Load training data from JSONL file"""
    texts = []
    labels = []
    
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                data = json.loads(line)
                texts.append(data['text'])
                labels.append(data['domain'])
    
    return texts, labels


def train_classifier():
    """Train the domain classifier"""
    print("=" * 60)
    print("Galatea Domain Classifier Training")
    print("=" * 60)
    
    # Load data
    print(f"\n1. Loading training data from {TRAINING_DATA}...")
    texts, labels = load_training_data(TRAINING_DATA)
    print(f"   Loaded {len(texts)} examples")
    
    # Show distribution
    from collections import Counter
    dist = Counter(labels)
    print("\n   Distribution:")
    for domain, count in sorted(dist.items()):
        print(f"   - {domain}: {count} examples")
    
    # Load embedding model
    print(f"\n2. Loading embedding model: {EMBEDDING_MODEL}...")
    print("   (This may take a moment on first run)")
    embedder = SentenceTransformer(EMBEDDING_MODEL)
    
    # Generate embeddings
    print("\n3. Generating embeddings...")
    embeddings = embedder.encode(texts, show_progress_bar=True)
    print(f"   Embedding shape: {embeddings.shape}")
    
    # Split data
    print("\n4. Splitting into train/test sets (80/20)...")
    X_train, X_test, y_train, y_test = train_test_split(
        embeddings, labels, test_size=0.2, random_state=42, stratify=labels
    )
    print(f"   Train: {len(X_train)}, Test: {len(X_test)}")
    
    # Train classifier
    print("\n5. Training Logistic Regression classifier...")
    classifier = LogisticRegression(
        max_iter=1000,
        multi_class='multinomial',
        solver='lbfgs',
        class_weight='balanced',  # Handle class imbalance
        random_state=42
    )
    classifier.fit(X_train, y_train)
    
    # Evaluate
    print("\n6. Evaluating on test set...")
    y_pred = classifier.predict(X_test)
    
    print("\n   Classification Report:")
    print(classification_report(y_test, y_pred))
    
    print("\n   Confusion Matrix:")
    print(confusion_matrix(y_test, y_pred))
    
    # Cross-validation
    print("\n7. Cross-validation (5-fold)...")
    cv_scores = cross_val_score(classifier, embeddings, labels, cv=5)
    print(f"   Accuracy: {cv_scores.mean():.3f} (+/- {cv_scores.std() * 2:.3f})")
    
    # Save model
    print(f"\n8. Saving model to {OUTPUT_MODEL}...")
    model_data = {
        'classifier': classifier,
        'embedding_model': EMBEDDING_MODEL,
        'domains': DOMAINS,
        'version': '1.0.0'
    }
    
    with open(OUTPUT_MODEL, 'wb') as f:
        pickle.dump(model_data, f)
    
    # Test inference
    print("\n9. Testing inference...")
    test_queries = [
        "What are the side effects of aspirin?",
        "How do I sue my employer?",
        "Can you debug this Python code?",
        "What is the derivative of x^2?",
        "Tell me a joke",
        "How do I invest in stocks?",
    ]
    
    test_embeddings = embedder.encode(test_queries)
    predictions = classifier.predict(test_embeddings)
    probabilities = classifier.predict_proba(test_embeddings)
    
    print("\n   Sample Predictions:")
    for query, pred, probs in zip(test_queries, predictions, probabilities):
        confidence = max(probs)
        print(f"   \"{query[:50]}...\"")
        print(f"      -> {pred} (confidence: {confidence:.2f})")
    
    print("\n" + "=" * 60)
    print("Training complete!")
    print(f"Model saved to: {OUTPUT_MODEL}")
    print("\nTo use in Galatea, copy the model to backend/app/services/")
    print("=" * 60)


class DomainClassifier:
    """
    Wrapper class for using the trained classifier in Galatea.
    
    Usage:
        classifier = DomainClassifier.load("domain_classifier.pkl")
        domain, confidence = classifier.predict("What causes high blood pressure?")
    """
    
    def __init__(self, classifier, embedder, domains):
        self.classifier = classifier
        self.embedder = embedder
        self.domains = domains
    
    @classmethod
    def load(cls, model_path: str):
        """Load a trained classifier from disk"""
        with open(model_path, 'rb') as f:
            model_data = pickle.load(f)
        
        embedder = SentenceTransformer(model_data['embedding_model'])
        
        return cls(
            classifier=model_data['classifier'],
            embedder=embedder,
            domains=model_data['domains']
        )
    
    def predict(self, text: str) -> Tuple[str, float]:
        """
        Predict the domain of a query.
        
        Returns:
            (domain, confidence)
        """
        embedding = self.embedder.encode([text])
        
        domain = self.classifier.predict(embedding)[0]
        probabilities = self.classifier.predict_proba(embedding)[0]
        confidence = max(probabilities)
        
        return domain, confidence
    
    def predict_batch(self, texts: List[str]) -> List[Tuple[str, float]]:
        """Predict domains for multiple queries"""
        embeddings = self.embedder.encode(texts)
        
        domains = self.classifier.predict(embeddings)
        probabilities = self.classifier.predict_proba(embeddings)
        
        results = []
        for domain, probs in zip(domains, probabilities):
            confidence = max(probs)
            results.append((domain, confidence))
        
        return results


if __name__ == "__main__":
    train_classifier()



