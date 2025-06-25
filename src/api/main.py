import os
import pickle
from fastapi import FastAPI
from pydantic import BaseModel
import pandas as pd

# --- Configuration & Model Loading ---
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
MODEL_PATH = os.path.join(PROJECT_ROOT, 'models', 'vulnerability_predictor.pkl')

app = FastAPI(title="Zero-Day Vulnerability Predictor API")

# Load the model once when the API starts up
try:
    with open(MODEL_PATH, 'rb') as f:
        model = pickle.load(f)
    print("Model loaded successfully.")
except FileNotFoundError:
    print(f"FATAL ERROR: Model not found at {MODEL_PATH}. The API will not work.")
    model = None

# Define the structure of the input data we expect
class FileMetrics(BaseModel):
    nloc: int
    complexity: int
    token_count: int
    function_count: int
    average_complexity: float
    commit_count: int
    author_count: int
    lines_added: int
    lines_deleted: int
    days_since_first_commit: int
    days_since_last_commit: int

@app.get("/")
def read_root():
    return {"message": "Welcome to the Zero-Day Predictor API. Use the /predict endpoint to get a risk score."}

@app.post("/predict/")
def predict_risk(metrics: FileMetrics):
    """
    Accepts a JSON object with file metrics and returns a vulnerability risk score.
    """
    if model is None:
        return {"error": "Model is not loaded. Cannot make predictions."}
    
    # Convert the input data into a pandas DataFrame (model expects this format)
    input_df = pd.DataFrame([metrics.dict()])
    
    # The model was trained on these specific feature names in this order
    feature_order = [
        'nloc', 'complexity', 'token_count', 'function_count', 'average_complexity', 
        'commit_count', 'author_count', 'lines_added', 'lines_deleted', 
        'days_since_first_commit', 'days_since_last_commit'
    ]
    input_df = input_df[feature_order]

    # Get the probability of being vulnerable (class 1)
    risk_score = model.predict_proba(input_df)[0][1]
    
    return {"filename_metrics": metrics.dict(), "vulnerability_risk_score": float(risk_score)}