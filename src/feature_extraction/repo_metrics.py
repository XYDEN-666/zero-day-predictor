import git
from datetime import datetime

def get_file_history_metrics(repo_path, file_path, end_commit_hash):
    """
    Analyzes the Git history of a specific file up to a given commit.

    Args:
        repo_path (str): The path to the local git repository.
        file_path (str): The relative path to the file within the repository.
        end_commit_hash (str): The hash of the commit to stop the analysis at.

    Returns:
        dict: A dictionary containing historical metrics for the file.
    """
    try:
        repo = git.Repo(repo_path)
        
        # Get all commits that affected this file, up to the end_commit
        # The '..' syntax means all commits reachable from end_commit_hash
        commits = list(repo.iter_commits(f"{end_commit_hash}", paths=file_path))

        if not commits:
            return {
                'commit_count': 0,
                'author_count': 0,
                'lines_added': 0,
                'lines_deleted': 0,
                'days_since_first_commit': 0,
                'days_since_last_commit': 0
            }
            
        # --- Calculate Metrics ---
        commit_count = len(commits)
        
        # Unique authors
        authors = {commit.author.email for commit in commits}
        author_count = len(authors)
        
        # Churn (lines added/deleted)
        total_added = 0
        total_deleted = 0
        for commit in commits:
            # We need to access the stats of the parent-to-commit diff
            # For the very first commit, it has no parents.
            if not commit.parents:
                # For the initial commit, stats are not available in the same way.
                # A simple heuristic is to count the lines in the blob.
                try:
                    total_added += len(commit.tree[file_path].data_stream.read().decode().splitlines())
                except (KeyError, UnicodeDecodeError):
                    # File might not exist in the tree or is binary
                    pass
                continue

            # Compare the commit with its first parent
            diff = commit.diff(commit.parents[0], paths=file_path, create_patch=True)
            for d in diff:
                # The patch format gives us lines starting with '+' or '-'
                for line in d.diff.decode(errors='ignore').splitlines():
                    if line.startswith('+') and not line.startswith('+++'):
                        total_added += 1
                    elif line.startswith('-') and not line.startswith('---'):
                        total_deleted += 1
                        
        # Age metrics
        first_commit_date = commits[-1].committed_datetime
        last_commit_date = commits[0].committed_datetime
        end_commit_date = repo.commit(end_commit_hash).committed_datetime

        days_since_first = (end_commit_date - first_commit_date).days
        days_since_last = (end_commit_date - last_commit_date).days

        return {
            'commit_count': commit_count,
            'author_count': author_count,
            'lines_added': total_added,
            'lines_deleted': total_deleted,
            'days_since_first_commit': days_since_first,
            'days_since_last_commit': days_since_last
        }
        
    except Exception as e:
        # print(f"Could not analyze history for {file_path}: {e}") # Uncomment for debugging
        return None