import joblib
import numpy as np
import os
from sklearn.linear_model import LinearRegression

MODEL_DIR = 'dummy_sklearn_model'
os.makedirs(MODEL_DIR, exist_ok=True)

X_train = np.random.rand(100, 2) * 10
y_train = 2 * X_train[:, 0] + 5 * X_train[:, 1] + np.random.randn(100)

model = LinearRegression()
model.fit(X_train, y_train)

model_filename = 'model.joblib'
model_path = os.path.join(MODEL_DIR, model_filename)

joblib.dump(model, model_path)