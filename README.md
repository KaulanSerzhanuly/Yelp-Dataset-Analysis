# Restaurant Operating Status Analysis (CS163 Project)

## 1. Repository Summary
This repository contains a data science project analyzing factors associated with whether restaurants are open or closed using the Yelp Open Dataset and UberEats data. The project combines exploratory data analysis, statistical testing, feature engineering, and machine learning to understand business success patterns. Results are presented through a web application hosted on Google Cloud App Engine. Plotly visualizations and machine learning model comparisons are included in the website.

---

## 2. Setup Instructions

### Requirements
- Python 3.11
- Google Cloud SDK (for deployment)
- Python packages listed in `website/requirements.txt`

### Install dependencies:
```
cd website
pip install -r requirements.txt
```

### Run Locally

```
python app.py
cd website
```

Open your browser and visit:

http://localhost:8080

### Deploy to Google App Engine
```
cd website
gcloud app deploy
```
---

## 3. End-to-End Pipeline

### Data Collection
#### Yelp Open Dataset 
- yelp_academic_dataset_business.json
- yelp_academic_dataset_review.json
  
#### Kaggle Uber Eats USA Restaurants and Menus Dataset
- restaurants.csv

### Data Processing
1. Filter Yelp businesses to restaurants.
2. Restrict analysis to restaurants with at least 50 reviews.
3. Process Yelp reviews in chunks to avoid memory issues.
4. Compute sentiment and complaint features.
5. Normalize restaurant names and ZIP codes.
6. Merge Yelp and UberEats datasets.

### Feature Engineering
| Feature             | Description                                        |
| ------------------- | -------------------------------------------------- |
| `log_reviews`       | `log(review_count)`                                |
| `avg_sentiment`     | Average TextBlob sentiment polarity per restaurant |
| `avg_complaints`    | Average complaint-related word count per review    |
| `delivery_presence` | 1 if restaurant matched to UberEats, 0 otherwise   |
| `ubereats_score`    | UberEats platform rating                           |
| `ubereats_ratings`  | Number of UberEats ratings                         |
| `price_level`       | Numeric encoding of `$`, `$$`, `$$$`, `$$$$`       |


### Analysis
- Exploratory Data Analysis (EDA)
- Statistical testing:
  - t-tests
  - chi-square tests
- Visualization of distributions and relationships

### Machine Learning
Multiple classification models were trained to predict `is_open`

#### Logistic Regression classifier
1. Review count only
2. Review count + stars
3. Yelp features (log_reviews, stars, avg_sentiment, avg_complaints)
4. Yelp + UberEats features

#### Evaluation Metrics
- Accuracy
- F1 Score
- ROC-AUC

### Deployment
- Flask web application
- Hosted on **Google App Engine**
- Gunicorn application server
- Interactive Plotly charts embedded through static HTML files
- FastAPI inference service deployed on Google Cloud Run
  
---

## 4. Repository Structure

```

├── inference_service/                         # FastAPI-based ML inference API deployed to Cloud Run
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                            # FastAPI application with / and /predict endpoints
│   │   └── model/
│   │       ├── __init__.py
│   │       ├── model.py                       # Loads the trained model and performs predictions
│   │       └── restaurant_model.pkl           # Trained Random Forest model artifact
│   ├── Dockerfile                             # Container definition for the inference service
│   ├── Dockerfile.txt                         # Backup/reference copy of Dockerfile
│   └── requirements.txt                       # Python dependencies for FastAPI and scikit-learn
│
├── project_notebooks/                         # Main data science notebooks
│   ├── analysis.ipynb                         # Statistical tests and hypothesis analysis
│   ├── eda.ipynb                              # Data cleaning, feature engineering, and visualizations
│   └── ml.ipynb                               # Model training, evaluation, and model export
│
├── website/                                   # Flask web application deployed to Google App Engine
│   ├── static/
│   │   └── interactive/                       # Standalone Plotly HTML files used by the website
│   │       ├── hyp1_plot1.html                # Hypothesis 1 interactive visualization
│   │       ├── hyp1_plot2.html
│   │       ├── hyp2_plot1.html                # Hypothesis 2 interactive visualization
│   │       ├── hyp2_plot2.html
│   │       ├── hyp4_plot1.html                # Hypothesis 4 interactive visualization
│   │       ├── hyp4_plot2.html
│   │       ├── hyp5_plot1.html                # Hypothesis 5 interactive visualization
│   │       ├── hyp5_plot2.html
│   │       └── model_comparison.html          # Interactive machine learning model comparison
│   ├── .gcloudignore                          # Files excluded during App Engine deployment
│   ├── Procfile                               # Gunicorn startup command
│   ├── app.py                                 # Main Flask application and website logic
│   ├── app.yaml                               # App Engine configuration and scaling settings
│   ├── cs163prject (1).ipynb                  # Notebook used to embed appendix figures
│   ├── index.html                             # Optional exported notebook HTML
│   ├── requirements.txt                       # Python dependencies for the website
│   └── runtime.txt                            # Python runtime version
│
├── .dockerignore                              # Files excluded from Docker builds
├── .gcloudignore                              # Root deployment ignore file
├── .gitattributes                             # Git file handling settings
├── .gitignore                                 # Files excluded from version control
└── README.md                                  # Project documentation
```

`project_notebooks/`

Contains all data science work:

- Data cleaning and preprocessing
- Sentiment and complaint feature engineering
- Statistical hypothesis testing
- Machine learning model training and evaluation
  
`static/interactive/`

Contains Plotly interactive visualizations saved as standalone HTML files. These are loaded directly into the website using an iframe.

`website/`

Contains the Flask application and deployment configuration used to host the final project website on Google App Engine.

`inference_service/`

Contains the FastAPI-based machine learning inference service deployed on Google Cloud Run. The service loads the trained Random Forest model and exposes a `/predict` endpoint that returns the predicted probability that a restaurant is open.

---

## 5. System Design & Scalability
```
Yelp Open Dataset + UberEats Data
                │
                ▼
      Google Colab / Jupyter Notebooks
     (EDA, Feature Engineering, ML)
                │
                ▼
   Trained Random Forest Model (.pkl)
                │
                ▼
 Cloud Run Inference Service (FastAPI)
                ▲
                │
      Flask Website (website/app.py)
                │
                ▼
     Google App Engine (Auto Scaling)
                │
                ▼
            End Users
```
### Scalability Discussion
#### Google App Engine Scaling
The website uses App Engine Standard Environment with automatic scaling.

Current configuration:

- instance_class: F1
- max_instances: 20
This allows Google Cloud to automatically create additional instances when traffic increases and shut them down when traffic decreases.

---

## 6. Inference Service

#### Location of Code

- Docker configuration: `inference_service/Dockerfile`
- API entry point: `inference_service/app/main.py`
- Model loading logic: `inference_service/app/model/model.py`
- Trained model: `inference_service/app/model/restaurant_model.pkl`
- Model training notebook: `project_notebooks/ml.ipynb`

#### Purpose

The inference service provides real-time predictions for whether a restaurant is likely to be open.

### API Endpoints

- `GET /` — Health check
- `POST /predict` — Returns a prediction and probability

### Input Features

The service accepts the following features:

- `log_reviews`
- `stars`
- `avg_sentiment`
- `avg_complaints`
- `delivery_presence`
- `ubereats_score`
- `ubereats_ratings`
- `price_level`

### Output

Example response:

```
{
  "prediction": 1,
  "probability_open": 0.82
}
```
---

## 7. Cloud Data Storage

The raw Yelp and UberEats datasets are processed in Google Colab and are not stored directly in the GitHub repository due to their size.

The following derived assets are stored in Google Cloud services:

- The App Engine website stores static figures and interactive Plotly HTML files.
- The Cloud Run inference service stores the trained Random Forest model (`restaurant_model.pkl`) inside the deployed container image.
- Processed restaurant-level features are used to generate visualizations and train the model.

The website consumes:
1. Static and interactive visualization files generated from the processed dataset.
2. Real-time predictions returned by the Cloud Run inference service.

---
## 8. Website Link

https://cs163project-491022.uc.r.appspot.com/

---

## Authors
- Angie Avalos Joel
- Kaulan Serzhanuly
