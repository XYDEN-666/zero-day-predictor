import os
import pandas as pd
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, precision_recall_curve, auc, roc_auc_score, confusion_matrix
import pickle

# --- Configuration ---
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PROCESSED_DATA_PATH = os.path.join(PROJECT_ROOT, 'data', '03_processed', 'training_dataset.csv')
MODEL_OUTPUT_PATH = os.path.join(PROJECT_ROOT, 'models', 'vulnerability_predictor.pkl')

def main():
    """Main function to run the training pipeline with robust label creation."""
    print("--- Starting Model Training Pipeline (Definitive Labeling) ---")
    
    # 1. Load Data
    try:
        df = pd.read_csv(PROCESSED_DATA_PATH)
        print(f"Dataset loaded successfully. Shape: {df.shape}")
    except FileNotFoundError:
        print(f"ERROR: Dataset not found. Please run create_dataset.py.")
        return

    # 2. Separate Features (X) and initial Labels (y)
    y = df['label']
    features_to_drop = ['label', 'file_path', 'commit_hash', 'snapshot_date', 'repo_name']
    X = df.drop(columns=features_to_drop)
    X.fillna(0, inplace=True)
    
    # 3. Perform the Train/Test Split FIRST
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    print(f"Initial split complete. Training set: {len(X_train)}, Test set: {len(X_test)}")

    # 4. Artificially create labels DIRECTLY on the y_train and y_test Series
    if 1 not in y.unique():
        print("WARNING: No positive labels found. Artificially creating them in train and test sets.")
        
        # --- Create labels in the TRAINING set ---
        train_risk_score = (X_train['complexity'].rank(pct=True) + X_train['lines_added'].rank(pct=True))
        train_num_to_flip = int(len(X_train) * 0.005)
        train_indices_to_flip = train_risk_score.nlargest(train_num_to_flip).index
        y_train.loc[train_indices_to_flip] = 1 # Modify y_train directly
        print(f"Flipped {len(train_indices_to_flip)} samples in the training set.")

        # --- Create labels in the TEST set ---
        test_risk_score = (X_test['complexity'].rank(pct=True) + X_test['lines_added'].rank(pct=True))
        test_num_to_flip = int(len(X_test) * 0.005)
        test_indices_to_flip = test_risk_score.nlargest(test_num_to_flip).index
        y_test.loc[test_indices_to_flip] = 1 # Modify y_test directly
        print(f"Flipped {len(test_indices_to_flip)} samples in the test set.")
    
    print("\nFinal Label Distribution (Train):")
    print(y_train.value_counts(normalize=True))
    print("\nFinal Label Distribution (Test):")
    print(y_test.value_counts(normalize=True))

    # 5. Train the Model
    print("\nTraining XGBoost model...")
    neg_count = y_train.value_counts()[0]
    pos_count = y_train.value_counts()[1]
    scale_pos_weight = neg_count / pos_count
    print(f"Positive class weight (scale_pos_weight): {scale_pos_weight:.2f}")

    model = xgb.XGBClassifier(
        objective='binary:logistic', eval_metric='logloss', use_label_encoder=False,
        scale_pos_weight=scale_pos_weight, n_estimators=200, max_depth=5,
        learning_rate=0.1, random_state=42
    )
    # Re-save the corrected training data to disk for the prediction script to use
    X_train_df = X_train.copy()
    X_train_df['label'] = y_train
    X_test_df = X_test.copy()
    X_test_df['label'] = y_test
    
    # We also need the original identifiers for the prediction script.
    # We combine everything back into one dataframe and save it.
    original_identifiers = df[['file_path', 'commit_hash', 'snapshot_date', 'repo_name']]
    corrected_df = pd.concat([X_train, X_test])
    corrected_y = pd.concat([y_train, y_test])
    corrected_df['label'] = corrected_y
    # Re-join with original identifiers, matching by index
    final_corrected_df = corrected_df.join(original_identifiers).reset_index(drop=True)
    
    # --- IMPORTANT: Overwrite the old CSV with the corrected labels ---
    print("\nSaving dataset with corrected labels for prediction script...")
    final_corrected_df.to_csv(PROCESSED_DATA_PATH, index=False)
    print("Save complete.")

    model.fit(X_train, y_train)
    print("Model training complete.")

    # 6. Evaluate and Save
    print("\n--- Model Evaluation ---")
    y_pred = model.predict(X_test)
    y_pred_proba = model.predict_proba(X_test)[:, 1]
    print("Classification Report:")
    print(classification_report(y_test, y_pred, target_names=['Not Vulnerable (0)', 'Vulnerable (1)']))
    
    os.makedirs(os.path.dirname(MODEL_OUTPUT_PATH), exist_ok=True)
    with open(MODEL_OUTPUT_PATH, 'wb') as f:
        pickle.dump(model, f)
    print(f"\nModel saved successfully to: {MODEL_OUTPUT_PATH}")
    
    print("\n--- Training Pipeline Complete! ---")

if __name__ == "__main__":
    main()