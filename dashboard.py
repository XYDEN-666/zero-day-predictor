import streamlit as st
import pandas as pd
import pickle
import shap
import matplotlib.pyplot as plt
import os

# --- Page Configuration ---
st.set_page_config(
    page_title="Zero-Day Vulnerability Dashboard",
    page_icon="🛡️",
    layout="wide"
)

# --- Caching Functions ---
@st.cache_resource
def load_model():
    path = os.path.join('models', 'vulnerability_predictor.pkl')
    try:
        with open(path, 'rb') as f:
            return pickle.load(f)
    except FileNotFoundError:
        return None

@st.cache_data
def load_data():
    path = os.path.join('data', '03_processed', 'training_dataset.csv')
    try:
        df = pd.read_csv(path)
        _model = load_model()
        if _model is not None:
            features_to_drop = ['label', 'file_path', 'commit_hash', 'snapshot_date', 'repo_name']
            features = df.drop(columns=features_to_drop, errors='ignore')
            features.fillna(0, inplace=True)
            train_cols = _model.get_booster().feature_names
            features = features[train_cols]
            df['risk_score'] = _model.predict_proba(features)[:, 1]
        return df
    except FileNotFoundError:
        return pd.DataFrame()

# --- Main App ---
st.title("🛡️ Zero-Day Exploit Prediction Dashboard")
st.markdown("This dashboard analyzes software components to predict which are most likely to contain vulnerabilities.")

model = load_model()
df = load_data()

st.sidebar.header("Filter Options")
if st.sidebar.button("Clear Cache and Rerun"):
    st.cache_data.clear()
    st.cache_resource.clear()
    st.rerun()

if not df.empty and model:
    repo_list = ['All'] + sorted(df['repo_name'].unique().tolist())
    selected_repo = st.sidebar.selectbox("Select Repository", repo_list)
    
    risk_threshold = st.sidebar.slider("Minimum Risk Score", 0.0, 1.0, 0.5, 0.01)

    filtered_df = df[df['risk_score'] >= risk_threshold]
    if selected_repo != 'All':
        filtered_df = filtered_df[filtered_df['repo_name'] == selected_repo]
        
    st.header("Potentially Vulnerable Components")
    st.markdown(f"Displaying **{len(filtered_df)}** files matching the criteria.")
    
    display_cols = ['repo_name', 'file_path', 'risk_score', 'complexity', 'commit_count', 'lines_added']
    st.dataframe(
        filtered_df[display_cols].sort_values(by='risk_score', ascending=False),
        use_container_width=True
    )

    # --- Explainability Section ---
    st.header("Explain a Prediction")
    st.markdown("Select a file from the filtered list above to understand why the model assigned it a specific risk score.")
    
    if not filtered_df.empty:
        filtered_df_display = filtered_df.sort_values(by='risk_score', ascending=False)
        file_to_explain_options = [
            f"{idx}: {row['repo_name']}/{row['file_path']} (Risk: {row['risk_score']:.2f})" 
            for idx, row in filtered_df_display.iterrows()
        ]
        selected_file_str = st.selectbox("Select a file to explain:", file_to_explain_options)
        
        if selected_file_str:
            selected_index = int(selected_file_str.split(':')[0])
            sample = df.loc[[selected_index]]
            
            st.write(f"**Explanation for:** `{sample.iloc[0]['file_path']}`")
            
            features_to_drop = ['label', 'file_path', 'commit_hash', 'snapshot_date', 'repo_name', 'risk_score']
            features = sample.drop(columns=features_to_drop, errors='ignore')
            features.fillna(0, inplace=True)
            train_cols = model.get_booster().feature_names
            features = features[train_cols]
            
            explainer = shap.TreeExplainer(model)
            shap_values = explainer(features) # Use the explainer as a function

            # --- THE FINAL, ROBUST PLOTTING FIX ---
            # Instead of the experimental force_plot, we use the stable waterfall_plot.
            # It shows the same information in a clearer, vertical format.
            fig, ax = plt.subplots()
            st.markdown("#### Feature Contribution Waterfall")
            st.write("This plot shows how each feature pushed the prediction away from the average (base value). Red features increase risk, blue features decrease it.")
            
            # The waterfall_plot is designed for a single instance, so we use shap_values[0]
            shap.waterfall_plot(shap_values[0], max_display=10, show=False)
            st.pyplot(fig, bbox_inches='tight')
            # --- END OF FIX ---
            
    else:
        st.warning("No files match the current filter settings. Try lowering the risk score threshold.")
else:
    st.error("Could not load model or data. Please ensure the pipeline has been run successfully.")