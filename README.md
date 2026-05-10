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

---

## 4. Repository Structure

```
.
├── inference_service/                 # Dockerized model inference service for Cloud Run
│   ├── Dockerfile                     # Container definition for the API service
│   └── Dockerfile.txt                 # Backup/reference copy of Dockerfile
│
├── project_notebooks/                 # Main data science notebooks
│   ├── analysis.ipynb                 # Statistical tests and hypothesis analysis
│   ├── eda.ipynb                      # Data cleaning, feature engineering, and visualizations
│   └── ml.ipynb                       # Model training and evaluation
│
├── static/
│   └── interactive/                   # Standalone Plotly HTML files used by the website
│       ├── hyp1_plot1.html            # Hypothesis 1 interactive visualization
│       ├── hyp1_plot2.html
│       ├── hyp2_plot1.html            # Hypothesis 2 interactive visualization
│       ├── hyp2_plot2.html
│       ├── hyp4_plot1.html            # Hypothesis 4 interactive visualization
│       ├── hyp4_plot2.html
│       ├── hyp5_plot1.html            # Hypothesis 5 interactive visualization
│       ├── hyp5_plot2.html
│       └── model_comparison.html      # Interactive ML model comparison chart
│
├── website/                           # Flask web application deployed to App Engine
│   ├── .gcloudignore                  # Files excluded during deployment
│   ├── Procfile                       # Gunicorn startup command
│   ├── app.py                         # Main Flask application
│   ├── app.yaml                       # Google App Engine configuration
│   ├── cs163prject (1).ipynb          # Notebook used to embed appendix figures
│   ├── index.html                     # Optional exported notebook HTML
│   ├── requirements.txt               # Python dependencies for the web app
│   └── runtime.txt                    # Python runtime version
│
├── .dockerignore                      # Files excluded from Docker builds
├── .gcloudignore                      # Root deployment ignore file
├── .gitattributes                     # Git LFS and file handling settings
├── .gitignore                         # Files excluded from version control
└── README.md                          # Project documentation
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

Contains Docker-related files for a future Cloud Run API that can serve model predictions in real time.

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
   Processed Features + Plotly HTML Files
                │
                ├──────────────► static/interactive/
                │
                ▼
      Flask Website (website/app.py)
                │
                ▼
     Google App Engine (Auto Scaling)
                │
                ▼
            End Users
                │
                ▼
   Cloud Run Inference Service
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

Docker configuration: inference_service/Dockerfile
Model training code: project_notebooks/ml.ipynb

#### Purpose

The inference service is designed to provide real-time predictions for whether a restaurant is likely to be open.

Input

Restaurant features such as:

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
