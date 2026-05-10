import joblib
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
model_path = os.path.join(current_dir, "restaurant_model.pkl")

model = joblib.load(model_path)

def predict(features: list):
    prediction = model.predict([features])[0]
    probability_open = model.predict_proba([features])[0][1]
    return int(prediction), float(probability_open)
