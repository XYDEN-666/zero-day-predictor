# %% [markdown]
# # Week 3: Static Code Analysis Exploration
#
# **Goal:** Test our `code_metrics` module by analyzing a real repository at a specific commit and viewing the results.

# %%
import os
import pandas as pd
import git
from IPython.display import display

# Because we did `pip install -e .`, Python now knows where to find our modules.
# The duplicate import line has been removed.
# ... other imports ...
from feature_extraction.code_metrics import analyze_repo_at_commit

# --- Configuration ---
# Define the path to the repository we want to analyze
REPO_NAME = 'redis'

# ---- NEW AND IMPROVED PATH LOGIC ----
# Find the project root directory (which contains the 'src', 'data', etc. folders)
# This is much more robust than using '..'
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
REPO_PATH = os.path.join(PROJECT_ROOT, 'data', '01_raw', 'repositories', REPO_NAME)
# ---- END OF NEW LOGIC ----

print(f"Project Root is: {PROJECT_ROOT}")
print(f"Using repository at: {REPO_PATH}")

# %% [markdown]
# ### Step 1: Select a Commit to Analyze
#
# Let's grab a commit to simulate looking at the code at a past point in time. We'll pick a relatively recent commit from the `unstable` branch of Redis as an example.

# %%
try:
    repo = git.Repo(REPO_PATH)
    # Get the latest commit from the 'unstable' branch as an example
    target_commit = repo.commit('unstable')
    commit_hash = target_commit.hexsha
    print(f"Selected repository: {REPO_NAME}")
    print(f"Target commit hash: {commit_hash}")
    print(f"Commit date: {target_commit.committed_datetime}")
    print(f"Commit message: {target_commit.message.strip()}")
except Exception as e:
    print(f"Error accessing repo at {REPO_PATH}: {e}")

# %% [markdown]
# ### Step 2: Run the Analysis
#
# Now we call our main function from `code_metrics.py`. This will check out the commit, walk through all files, analyze them with `lizard`, and then restore the repo to its original state.

# %%
# It's a good practice to check if a commit hash was found before proceeding
if 'commit_hash' in locals():
    file_metrics = analyze_repo_at_commit(REPO_PATH, commit_hash)

    # Convert the list of dictionaries to a pandas DataFrame for easy analysis
    df_metrics = pd.DataFrame(file_metrics)

    print(f"\nAnalysis complete. Found metrics for {len(df_metrics)} files.")
else:
    print("\nSkipping analysis because a target commit could not be found.")

# %% [markdown]
# ### Step 3: Explore the Results
#
# Let's look at the data we've generated. We can see basic stats and find the most complex files, which might be candidates for closer inspection.

# %%
# Display the first few rows of the DataFrame
# This will only run if the analysis was successful
if 'df_metrics' in locals() and not df_metrics.empty:
    display(df_metrics.head())


# %%
# Get a statistical summary of our metrics
if 'df_metrics' in locals() and not df_metrics.empty:
    display(df_metrics.describe())

# %%
# Find the top 10 most complex files in this commit
if 'df_metrics' in locals() and not df_metrics.empty:
    print("\n--- Top 10 Most Complex Files (by total cyclomatic complexity) ---")
    display(df_metrics.sort_values(by='complexity', ascending=False).head(10))


# %%
# Find the top 10 largest files by Non-Comment Lines of Code (NLOC)
if 'df_metrics' in locals() and not df_metrics.empty:
    print("\n--- Top 10 Largest Files (by NLOC) ---")
    display(df_metrics.sort_values(by='nloc', ascending=False).head(10))