# %% [markdown]
# # Week 4: Git History (Process Metrics) Exploration
#
# **Goal:** Test our `repo_metrics` module to extract historical data like churn, author count, and age for specific files.

# %%
import os
import git
import pandas as pd
from IPython.display import display

# Because we did `pip install -e .`, Python now knows where to find our modules.
from feature_extraction.repo_metrics import get_file_history_metrics

# --- Configuration ---
REPO_NAME = 'redis'

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
REPO_PATH = os.path.join(PROJECT_ROOT, 'data', '01_raw', 'repositories', REPO_NAME)
print(f"Using repository at: {REPO_PATH}")

# %% [markdown]
# ### Step 1: Select a Target File and Commit
#
# We'll pick an important, long-lived file from the Redis project, like `src/server.c`. We'll also pick the same commit hash we used last week to represent our "snapshot in time".

# %%
# The main server file, a core component of Redis
TARGET_FILE = 'src/server.c'

try:
    repo = git.Repo(REPO_PATH)
    # Use the same commit as last week for consistency
    target_commit = repo.commit('unstable')
    commit_hash = target_commit.hexsha
    print(f"Target file: {TARGET_FILE}")
    print(f"Analysis will run up to commit: {commit_hash[:10]}")
except Exception as e:
    print(f"Error accessing repo at {REPO_PATH}: {e}")

# %% [markdown]
# ### Step 2: Run the History Analysis
#
# Now we call our new function. It will traverse the Git history for `src/server.c`, calculate the metrics, and return them as a dictionary.

# %%
if 'commit_hash' in locals():
    history_metrics = get_file_history_metrics(REPO_PATH, TARGET_FILE, commit_hash)
    
    if history_metrics:
        print("\nSuccessfully calculated history metrics:")
        # Pretty print the dictionary
        for key, value in history_metrics.items():
            print(f"- {key}: {value}")
    else:
        print(f"\nCould not calculate metrics for {TARGET_FILE}. It might not exist at this commit or an error occurred.")

# %% [markdown]
# ### Step 3: Analyze Another File for Comparison
#
# Let's analyze a different file, maybe a less central one, to see how the metrics differ. `src/crc64.c` is a utility file for calculating checksums.

# %%
TARGET_FILE_2 = 'src/crc64.c'
print(f"\n--- Analyzing second file: {TARGET_FILE_2} ---")

if 'commit_hash' in locals():
    history_metrics_2 = get_file_history_metrics(REPO_PATH, TARGET_FILE_2, commit_hash)

    if history_metrics_2:
        print("\nSuccessfully calculated history metrics:")
        for key, value in history_metrics_2.items():
            print(f"- {key}: {value}")
    else:
        print(f"\nCould not calculate metrics for {TARGET_FILE_2}.")

# %% [markdown]
# ### Conclusion
#
# Comparing the two files, you will likely see that `src/server.c` has a much higher `commit_count`, `author_count`, and `lines_added`/`deleted` than `src/crc64.c`. This indicates it is a more central, "hot" part of the codebase. Our hypothesis is that such files are more likely to contain vulnerabilities. We have now successfully extracted these signals.