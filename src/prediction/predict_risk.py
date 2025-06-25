import os
import pandas as pd
import pickle
import shap
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split # We need this now

# --- Configuration ---
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MODEL_PATH = os.path.join(PROJECT_ROOT, 'models', 'vulnerability_predictor.pkl')
DATA_PATH = os.path.join(PROJECT_ROOT, 'data', '03_processed', 'training_dataset.csv')
REPORTS_DIR = os.path.join(PROJECT_ROOT, 'reports', 'figures')

def load_model_and_data():
    """Loads the model and splits data into the same train/test sets used for training."""
    print("Loading model and data...")
    
    try:
        with open(MODEL_PATH, 'rb') as f:
            model = pickle.load(f)
    except FileNotFoundError:
        print(f"ERROR: Model not found. Please run train_model.py first.")
        return None, None, None, None
        
    try:
        df = pd.read_csv(DATA_PATH)
    except FileNotFoundError:
        print(f"ERROR: Dataset not found. Please run create_dataset.py first.")
        return None, None, None, None

    # --- Re-create the exact same train/test split ---
    # This is crucial for finding representative samples.
    features_to_drop = ['label', 'file_path', 'commit_hash', 'snapshot_date', 'repo_name']
    X = df.drop(columns=features_to_drop)
    y = df['label']
    X.fillna(0, inplace=True)
    
    # Using the same random_state and stratify ensures the split is identical to training
    _, X_test, _, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    return model, X_test, y_test, df

def predict_and_explain(model, X_test_sample, sample_index, original_df):
    """Makes a prediction and explains it."""
    print(f"\n--- Analyzing Sample with Original Index: {sample_index} ---")
    
    # The sample to predict is a single row DataFrame
    sample_to_predict = X_test_sample.to_frame().T
    
    prediction = model.predict(sample_to_predict)[0]
    probability = model.predict_proba(sample_to_predict)[0][1]
    
    sample_context = original_df.loc[sample_index]
    
    print("Prediction Context:")
    print(f"  File: {sample_context['file_path']}")
    print(f"  Repo: {sample_context['repo_name']}")
    
    print("\nPrediction Result:")
    print(f"  Predicted Label: {'Vulnerable' if prediction == 1 else 'Not Vulnerable'}")
    print(f"  Vulnerability Probability (Risk Score): {probability:.4f}")
    
    print("\nGenerating SHAP explanation plot...")
    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(sample_to_predict)
    
    shap.force_plot(
        explainer.expected_value, shap_values[0], sample_to_predict.iloc[0],
        matplotlib=True, show=False
    )
    
    plt.title(f"SHAP Explanation for {sample_context['file_path']}")
    output_path = os.path.join(REPORTS_DIR, f"shap_force_plot_sample_{sample_index}.png")
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"SHAP plot saved to: {output_path}")

def main():
    """Main function to run prediction and explanation."""
    print("--- Starting Prediction and Explanation Pipeline ---")
    os.makedirs(REPORTS_DIR, exist_ok=True)
    
    model, X_test, y_test, original_df = load_model_and_data()
    
    if model is None:
        return
        
    # --- NEW: Find interesting samples within the TEST SET ---
    # 1. A sample that is ACTUALLY not vulnerable and the model correctly predicted as such.
    # We find the first instance in our test set where the true label is 0.
    low_risk_index = y_test[y_test == 0].index[0]
    predict_and_explain(model, X_test.loc[low_risk_index], low_risk_index, original_df)
    
    # 2. A sample that is ACTUALLY vulnerable.
    # We find the first instance in our test set where the true label is 1.
    # This is guaranteed to exist because we stratified the split.
    high_risk_index = y_test[y_test == 1].index[0]
    predict_and_explain(model, X_test.loc[high_risk_index], high_risk_index, original_df)

    print("\n--- Prediction Pipeline Complete! ---")

if __name__ == "__main__":
    main()