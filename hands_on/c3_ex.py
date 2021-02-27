from sklearn.datasets import fetch_openml
from sklearn.model_selection import GridSearchCV
from sklearn.neighbors import KNeighborsClassifier
import pandas as pd
import numpy as np

def get_data():
    X, y = fetch_openml('mnist_784', version=1, return_X_y=True, as_frame=True)
    X.to_feather('datasets/mnist_784.feather')
    pd.DataFrame(y).to_feather('datasets/mnist_784_labels.feather')

def load_data():
    return pd.read_feather('datasets/mnist_784.feather'), pd.read_feather('datasets/mnist_784_labels.feather')

def prepare_mnist_dataset():
    X, y = load_data()

    train_set_size = 60000
    X_train, X_test, y_train, y_test = X[:train_set_size], X[train_set_size:], y[:train_set_size], y[train_set_size:]

    X_train = X_train.sample(frac=1, random_state=42).reset_index(drop=True)
    y_train = y_train.sample(frac=1, random_state=42).reset_index(drop=True)

    return X_train.to_numpy(), X_test.to_numpy(), y_train.values.ravel(), y_test.values.ravel()

def train_knn(X_train, y_train):
    knn_params = {
        'n_neighbors': [1, 3, 5, 10],
        'weights': ['uniform', 'distance'],
    }

    knn_gscv = GridSearchCV(KNeighborsClassifier(), knn_params, cv=3, scoring='accuracy', n_jobs=1, verbose=10)
    knn_gscv.fit(X_train, y_train)
    return knn_gscv

# best: {'n_neighbors': 3, 'weights': 'distance'}
