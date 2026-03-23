import pandas as pd
from dash import Dash, html, dcc
import plotly.express as px

# 1. THE CLEANING FUNCTION (From your notebook)
def clean_business(df):
    df = df.copy()
    # Basic cleaning you did in the notebook
    df.columns = [c.strip().lower() for c in df.columns]
    df = df.dropna(subset=['stars'])
    return df

# 2. LOADING THE DATA
# Make sure this .json file is in your cs163_demo folder!
try:
    # We load only 1000 rows so the demo is fast and doesn't crash
    raw_df = pd.read_json('yelp_academic_dataset_business.json', lines=True, nrows=1000)
    df = clean_business(raw_df)
    status_msg = f"Success! Loaded {len(df)} businesses from Yelp dataset."
except Exception as e:
    df = pd.DataFrame({'stars': [0], 'name': ['Data Not Found']})
    status_msg = "Error: Could not find the Yelp JSON file in this folder."

# 3. THE VISUAL (Interactive Histogram)
fig = px.histogram(df, x="stars", title="Yelp Star Ratings Distribution",
                   nbins=10, color_discrete_sequence=['#d32323']) # Yelp Red

# 4. THE LAYOUT
app = Dash(__name__)
server = app.server
app.layout = html.Div([
    html.H1("CS163: Yelp Data Analysis Demo"),
    html.P(status_msg),
    dcc.Graph(figure=fig)
])

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8050)