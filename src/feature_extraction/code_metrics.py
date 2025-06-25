import os
import lizard
import git
from tqdm import tqdm

# --- Configuration ---
# Define the file extensions we want to analyze.
# This helps us avoid analyzing binary files, documentation, etc.
SUPPORTED_EXTENSIONS = {
    '.c', '.h', '.cpp', '.hpp', # C/C++
    '.py',                      # Python
    # Add other language extensions as needed
}

def analyze_file_metrics(file_path):
    """
    Analyzes a single source file using the lizard library.

    Args:
        file_path (str): The full path to the file to analyze.

    Returns:
        dict: A dictionary containing aggregated metrics for the file,
              or None if the file cannot be analyzed.
    """
    try:
        # Use lizard to analyze the file
        analysis = lizard.analyze_file(file_path)
        
        # Aggregate metrics from all functions in the file
        total_nloc = sum(func.nloc for func in analysis.function_list)
        total_complexity = sum(func.cyclomatic_complexity for func in analysis.function_list)
        function_count = len(analysis.function_list)
        
        # Calculate average complexity, avoiding division by zero
        average_complexity = (total_complexity / function_count) if function_count > 0 else 0
        
        return {
            'nloc': total_nloc,
            'complexity': total_complexity,
            'token_count': sum(func.token_count for func in analysis.function_list),
            'function_count': function_count,
            'average_complexity': round(average_complexity, 2)
        }
    except Exception as e:
        # print(f"Could not analyze file {file_path}: {e}") # Uncomment for debugging
        return None


def analyze_repo_at_commit(repo_path, commit_hash):
    """
    Checks out a specific commit in a repository and analyzes all supported files.

    Args:
        repo_path (str): The path to the local git repository.
        commit_hash (str): The hash of the commit to analyze.

    Returns:
        list: A list of dictionaries, where each dictionary contains the
              path and static metrics for one analyzed file.
    """
    all_file_metrics = []
    repo = None # Initialize repo to None
    original_head = None # Initialize original_head to None
    
    try:
        repo = git.Repo(repo_path)
        
        # Store the current branch/commit to return to it later
        original_head = repo.head.commit
        
        print(f"\nChecking out commit {commit_hash[:7]}...")
        # Check out the specific commit
        repo.git.checkout(commit_hash, force=True)

        print(f"Analyzing files in commit {commit_hash[:7]}...")
        # Walk through all files in the repository at this commit
        # We create a list first to use tqdm for a progress bar
        files_to_analyze = []
        for root, _, files in os.walk(repo_path):
            if '.git' in root: # Skip the .git directory
                continue
            for file in files:
                # Check if the file has a supported extension
                if any(file.endswith(ext) for ext in SUPPORTED_EXTENSIONS):
                    files_to_analyze.append(os.path.join(root, file))

        for file_path in tqdm(files_to_analyze, desc="Analyzing files", unit="file"):
            metrics = analyze_file_metrics(file_path)
            if metrics:
                # We want the relative path within the repo, not the absolute path
                relative_path = os.path.relpath(file_path, repo_path)
                metrics['file_path'] = relative_path.replace('\\', '/') # Normalize path for consistency
                all_file_metrics.append(metrics)
                
    except git.exc.GitCommandError as e:
        print(f"Error checking out commit {commit_hash}: {e}")
        return []
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return []
    finally:
        # --- IMPORTANT ---
        # Ensure we always return the repository to its original state
        if repo and original_head:
            print(f"\nReturning repo to original state ({original_head.hexsha[:7]})...")
            repo.git.checkout(original_head, force=True)
            print("Repo state restored.")
            
    return all_file_metrics