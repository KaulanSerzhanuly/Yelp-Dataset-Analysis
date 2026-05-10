from fastapi import FastAPI
from pydantic import BaseModel
from app.model.model import predict

app = FastAPI()

class RestaurantFeatures(BaseModel):
    log_reviews: float
    stars: float
    avg_sentiment: float
    avg_complaints: float
    delivery_presence: int
    ubereats_score: float
    ubereats_ratings: float
    price_level: float

class PredictionOut(BaseModel):
    prediction: int
    probability_open: float

@app.get("/")
def home():
    return {"health_check": "ok"}

@app.post("/predict", response_model=PredictionOut)
def predict_endpoint(payload: RestaurantFeatures):
    features = [
        payload.log_reviews,
        payload.stars,
        payload.avg_sentiment,
        payload.avg_complaints,
        payload.delivery_presence,
        payload.ubereats_score,
        payload.ubereats_ratings,
        payload.price_level
    ]

    prediction, probability_open = predict(features)

    return {
        "prediction": prediction,
        "probability_open": probability_open
    }
