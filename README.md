# Restaurant Operating Status Analysis (CS163 Project)

## 1. Repository Summary
This repository contains a data science project analyzing factors associated with whether restaurants are open or closed using the Yelp Open Dataset and UberEats data. The project combines exploratory data analysis, statistical testing, feature engineering, and machine learning to understand business success patterns. Results are presented through a web application hosted on Google Cloud App Engine.

---

## 2. Setup Instructions

### Requirements
- Python 3.11
- Install dependencies:
  pip install -r requirements.txt
  
### Run Locally
  python app.py
  Then open:

http://localhost:8080


---

## 3. End-to-End Pipeline

### Data Collection
- Yelp Open Dataset (yelp_academic_dataset_business.json + yelp_academic_dataset_review.json)
- Kaggle: Uber Eats USA Restaurants and Menus (ubereats.csv) 

### Data Processing
- Filter restaurants (≥ 50 reviews)
- Clean names and features
- Merge Yelp and UberEats datasets

### Feature Engineering
- `log_reviews` (log of review count)
- `avg_sentiment` (TextBlob sentiment)
- `avg_complaints` (frequency of complaint words)
- `delivery_presence` (UberEats match)
- `ubereats_score`, `ubereats_ratings`, `price_level`

### Analysis
- Exploratory Data Analysis (EDA)
- Statistical testing:
  - t-tests
  - chi-square tests
- Visualization of distributions and relationships

### Machine Learning
- Logistic Regression classifier
- Compared multiple models:
  - Yelp features only
  - Yelp + sentiment
  - Yelp + sentiment + UberEats features

### Deployment
- Flask web app hosted on **Google App Engine**
- Notebook results rendered dynamically into HTML
- Uses Gunicorn for serving the application

---

## 4. Repository Structure


---

## 5. System Design & Scalability

The system is designed using a cloud-based architecture:

- **Frontend / Web App**
  - Hosted on Google App Engine
  - Serves visualizations and analysis results

- **Backend Processing**
  - Data processing and ML performed offline (notebooks)
  - Results rendered dynamically into the web app

- **Scalability**
  - App Engine automatically scales based on traffic
  - Stateless design ensures easy horizontal scaling

---

## 6. Inference Service

The current implementation embeds model results within the web application. A full inference service can be deployed using Cloud Run by containerizing the model and exposing an API endpoint.

Example future design:
- Input: restaurant features (reviews, stars, sentiment, etc.)
- Output: probability that the restaurant is open

---

## 7. Cloud Data Storage

- Data originates from the Yelp Open Dataset
- Due to dataset size, processing is done locally and/or in Google Colab
- A processed subset is used within the application
- Large raw datasets are not stored directly in the repository

---
## 8. Website Link

https://cs163project-491022.uc.r.appspot.com/

---

## Key Findings

- Review count is the strongest predictor of operating status
- Star ratings have moderate influence
- Sentiment and complaint frequency have weak but statistically significant effects
- UberEats features provide slight improvement in predictive performance

---

## Authors
- Angie Avalos Joel
- Kaulan Serzhanuly
