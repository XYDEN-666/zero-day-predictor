🔮 Zero-Day Predictor: A Crystal Ball for Software Vulnerabilities
![alt text](https://img.shields.io/badge/License-MIT-yellow.svg)

![alt text](https://img.shields.io/badge/python-3.9+-blue.svg)

![alt text](https://img.shields.io/badge/status-in%20development-orange.svg)
Tired of reacting to vulnerabilities? What if you could predict them before they were discovered?
Zero-Day Predictor is a cutting-edge data science project that leverages machine learning to forecast which parts of a software project are most likely to harbor undiscovered, exploitable vulnerabilities. Instead of just patching the past, we're building a "weather forecast" for future security threats, allowing developers and security teams to proactively audit the riskiest code.
!
<p align="center">An example of our model explaining WHY a file is predicted to be high-risk.</p>
✨ The Core Idea
The traditional security model is reactive. A vulnerability is disclosed (a CVE is issued), and everyone scrambles to patch it. We aim to shift this paradigm from reactive to proactive risk prioritization.
This project does not find specific exploits. Instead, it ingests the entire history of a codebase—every commit, every change, every line of code—and combines it with historical vulnerability data to answer a critical question:
"Given the complexity, churn, and development history of this file, what is its statistical risk of containing a currently unknown vulnerability?"
The output is a ranked list of files, allowing security teams to focus their expensive manual audits, fuzzing, and static analysis efforts where they will have the most impact.
🚀 Features & Methodology
This project is a full-scale data science pipeline, built from the ground up:
Vast Data Collection:
Automatically downloads and parses the entire National Vulnerability Database (NVD) into a structured SQLite database.
Clones the complete git history of target open-source projects like Apache httpd, Redis, and Django.
Deep Feature Engineering: We don't just look at code; we look at its evolution.
Static Code Metrics: Cyclomatic complexity, lines of code (NLOC), and function counts calculated at specific snapshots in time using lizard.
Git History Metrics (Process Metrics): Code churn (lines added/deleted), commit frequency, number of unique authors, and file age, all calculated using GitPython.
"Time Machine" Labeling:
We create a time-aware dataset by taking snapshots of the code at regular intervals (e.g., every 90 days).
A snapshot is labeled as "vulnerable" (1) if a CVE was publicly disclosed for that project within the next 365 days. Otherwise, it's labeled 0. This simulates a true predictive scenario where the outcome is unknown at the time of prediction.
Intelligent Model Training:
Employs a powerful XGBoost Classifier, renowned for its performance on tabular data.
Crucially handles the severe class imbalance inherent in vulnerability data using scale_pos_weight.
Explainable AI (XAI):
A prediction is useless without an explanation. We use SHAP (SHapley Additive exPlanations) to break down every prediction, showing exactly which features (e.g., "high complexity," "recent churn") contributed to the file's risk score.
🛠️ Getting Started
Want to run the crystal ball yourself? Here's how.
Prerequisites
Python 3.9+
Git installed and available in your system's PATH.
A Python virtual environment is highly recommended.
1. Clone the Repository
Generated bash
git clone https://github.com/your-username/zero-day-predictor.git
cd zero-day-predictor
Use code with caution.
Bash
2. Set Up The Environment
Generated bash
# Create and activate a virtual environment
python -m venv venv
# On Windows
venv\Scripts\activate
# On macOS/Linux
source venv/bin/activate

# Install all project dependencies
pip install -r requirements.txt

# Make the src directory installable
pip install -e .
Use code with caution.
Bash
3. Run the Pipeline (The Fun Part!)
The pipeline is broken into distinct, sequential steps.
Step 1: Download Vulnerability & Code Data
(This only needs to be done once. Requires an internet connection.)
Generated bash
# Download NVD data (takes a few minutes)
python src/data_collection/get_nvd_data.py

# Parse NVD data into a database
python src/data_collection/parse_nvd_to_db.py

# Clone target repositories (can take several minutes)
python src/data_collection/clone_repos.py
Use code with caution.
Bash
Step 2: Generate the Training Dataset
(This is the most computationally intensive step. It can take many hours or even days depending on your machine. It is resumable, so you can stop and start it without losing progress.)
Generated bash
python src/create_dataset.py
Use code with caution.
Bash
Step 3: Train the Predictive Model
(This is fast and should only take a few minutes.)
Generated bash
python src/training/train_model.py
Use code with caution.
Bash
Step 4: Make Predictions and See Explanations!
(Run the model on sample data and generate SHAP plots.)
Generated bash
python src/prediction/predict_risk.py
Use code with caution.
Bash
Check the reports/figures/ directory for the beautiful explanation plots!
📈 Future Work
This project lays a powerful foundation. Future directions include:
Parallelizing Data Generation: Using multiprocessing to speed up the dataset creation phase.
Advanced NLP: Parsing CVE text to automatically pinpoint the exact vulnerable file, improving label accuracy.
Web Dashboard: Creating an interactive dashboard with Streamlit or FastAPI to explore predictions.
More Models: Experimenting with Graph Neural Networks (GNNs) on code dependency graphs.
Broader Scope: Adding more repositories (e.g., from npm, PyPI) to the analysis.
📜 License
This project is licensed under the MIT License. See the LICENSE file for details.
