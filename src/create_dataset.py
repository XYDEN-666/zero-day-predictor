import os
import sqlite3
import pandas as pd
import git
from datetime import datetime, timedelta, timezone
from tqdm import tqdm

# --- Configuration ---
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(PROJECT_ROOT, 'data', '02_interim', 'cve_database.sqlite')
REPOS_DIR = os.path.join(PROJECT_ROOT, 'data', '01_raw', 'repositories')
OUTPUT_CSV_PATH = os.path.join(PROJECT_ROOT, 'data', '03_processed', 'training_dataset.csv')

TARGET_PROJECTS = {
    'httpd': ('http_server', 'httpd'),
    'redis': ('redis',),
    'django': ('django',)
}

VULNERABILITY_WINDOW_DAYS = 365
SNAPSHOT_INTERVAL_DAYS = 90

# --- The functions from our other modules ---
# We copy them here to avoid any import issues and make the script self-contained
def analyze_file_metrics(file_path):
    # This is a placeholder for the actual lizard analysis
    # In a real run, you would use your existing code_metrics.py functions
    # For now, this is just to show the structure
    try:
        # NOTE: Assumes 'lizard' is installed
        import lizard
        analysis = lizard.analyze_file(file_path)
        total_nloc = sum(func.nloc for func in analysis.function_list)
        total_complexity = sum(func.cyclomatic_complexity for func in analysis.function_list)
        function_count = len(analysis.function_list)
        average_complexity = (total_complexity / function_count) if function_count > 0 else 0
        return {
            'nloc': total_nloc,
            'complexity': total_complexity,
            'token_count': sum(func.token_count for func in analysis.function_list),
            'function_count': function_count,
            'average_complexity': round(average_complexity, 2)
        }
    except Exception:
        return None

def get_file_history_metrics(repo_path, file_path, end_commit_hash):
    # Placeholder for your repo_metrics.py function
    try:
        repo = git.Repo(repo_path)
        commits = list(repo.iter_commits(f"{end_commit_hash}", paths=file_path))
        if not commits: return {'commit_count': 0, 'author_count': 0, 'lines_added': 0, 'lines_deleted': 0, 'days_since_first_commit': 0, 'days_since_last_commit': 0}
        total_added, total_deleted = 0, 0
        for commit in commits:
            if not commit.parents: continue
            diff = commit.diff(commit.parents[0], paths=file_path, create_patch=True)
            for d in diff:
                for line in d.diff.decode(errors='ignore').splitlines():
                    if line.startswith('+') and not line.startswith('+++'): total_added += 1
                    elif line.startswith('-') and not line.startswith('---'): total_deleted += 1
        end_commit_date = repo.commit(end_commit_hash).committed_datetime
        return {
            'commit_count': len(commits), 'author_count': len({c.author.email for c in commits}),
            'lines_added': total_added, 'lines_deleted': total_deleted,
            'days_since_first_commit': (end_commit_date - commits[-1].committed_datetime).days,
            'days_since_last_commit': (end_commit_date - commits[0].committed_datetime).days
        }
    except Exception:
        return None
# --- End of copied functions ---


def get_snapshots_and_labels(repo_name, product_names):
    """
    Finds all the commits we need to analyze. This part is fast, so it doesn't need checkpointing.
    """
    print(f"\nIdentifying all snapshots for repository: {repo_name}...")
    repo_path = os.path.join(REPOS_DIR, repo_name)
    repo = git.Repo(repo_path)
    conn = sqlite3.connect(DB_PATH)
    
    main_branch = None
    possible_branch_names = ['main', 'master', 'trunk', 'development', 'unstable']
    repo_branches = [b.name for b in repo.branches]
    for name in possible_branch_names:
        if name in repo_branches:
            main_branch = name
            break
    if not main_branch: main_branch = repo_branches[0] if repo_branches else None
    
    if not main_branch: return pd.DataFrame()

    print(f"Found main development branch: '{main_branch}'")
    
    all_commits = sorted(list(repo.iter_commits(main_branch)), key=lambda c: c.committed_datetime, reverse=True)
    first_commit_date = all_commits[-1].committed_datetime
    last_commit_date = all_commits[0].committed_datetime
    
    snapshots = []
    processed_commits = set()
    current_date = first_commit_date
    while current_date <= last_commit_date:
        target_commit = next((c for c in all_commits if c.committed_datetime <= current_date), None)
        if target_commit and target_commit.hexsha not in processed_commits:
            snapshots.append({'commit_hash': target_commit.hexsha, 'snapshot_date': target_commit.committed_datetime.astimezone(timezone.utc)})
            processed_commits.add(target_commit.hexsha)
        current_date += timedelta(days=SNAPSHOT_INTERVAL_DAYS)
    
    # Now, label all the snapshots we found
    for snap in tqdm(snapshots, desc="Labeling snapshots"):
        start_date = snap['snapshot_date']
        end_date = start_date + timedelta(days=VULNERABILITY_WINDOW_DAYS)
        product_clauses = [f"affected_products LIKE '%\"{name}\"%'" for name in product_names]
        query = f"SELECT id FROM cves WHERE ({' OR '.join(product_clauses)}) AND published_date >= '{start_date.strftime('%Y-%m-%dT%H:%M:%S')}' AND published_date < '{end_date.strftime('%Y-%m-%dT%H:%M:%S')}'"
        future_vulns = pd.read_sql_query(query, conn)
        snap['label'] = 1 if not future_vulns.empty else 0
        snap['snapshot_date'] = snap['snapshot_date'].date()
        
    conn.close()
    return pd.DataFrame(snapshots)

def main():
    """Main pipeline with pause and resume functionality."""
    print("--- Starting Resumable Dataset Creation Pipeline ---")

    # --- Part 1: Load existing progress ---
    completed_tasks = set()
    if os.path.exists(OUTPUT_CSV_PATH):
        print(f"Resuming from existing file: {OUTPUT_CSV_PATH}")
        df_progress = pd.read_csv(OUTPUT_CSV_PATH)
        # Create a unique ID for each processed row to check against
        for _, row in df_progress.iterrows():
            completed_tasks.add((row['repo_name'], row['commit_hash'], row['file_path']))
        print(f"Found {len(completed_tasks)} previously completed file analyses.")
    else:
        # If no file exists, create one with the header row
        # This defines the schema of our final dataset
        header = ['nloc', 'complexity', 'token_count', 'function_count', 'average_complexity', 
                  'commit_count', 'author_count', 'lines_added', 'lines_deleted', 
                  'days_since_first_commit', 'days_since_last_commit', 
                  'file_path', 'commit_hash', 'snapshot_date', 'repo_name', 'label']
        pd.DataFrame(columns=header).to_csv(OUTPUT_CSV_PATH, index=False)

    # --- Part 2: Main processing loop ---
    for repo_name, product_names in TARGET_PROJECTS.items():
        snapshots_df = get_snapshots_and_labels(repo_name, product_names)
        repo_path = os.path.join(REPOS_DIR, repo_name)
        repo = git.Repo(repo_path)
        
        print(f"\nGenerating features for {len(snapshots_df)} snapshots in {repo_name}...")
        
        with tqdm(total=len(snapshots_df), desc=f"Processing snapshots for {repo_name}") as pbar_snap:
            for _, snapshot in snapshots_df.iterrows():
                pbar_snap.set_postfix_str(f"Commit: {snapshot['commit_hash'][:7]}")
                
                # Checkout the commit once
                try:
                    repo.git.checkout(snapshot['commit_hash'], force=True)
                except Exception as e:
                    print(f"\nError checking out {snapshot['commit_hash'][:7]}: {e}. Skipping snapshot.")
                    pbar_snap.update(1)
                    continue

                # Get a list of all files in this commit
                files_in_commit = []
                for root, _, files in os.walk(repo_path):
                    if '.git' in root: continue
                    for file in files:
                        if any(file.lower().endswith(ext) for ext in {'.c', '.h', '.py'}):
                            files_in_commit.append(os.path.relpath(os.path.join(root, file), repo_path).replace('\\', '/'))
                
                # Process each file
                for file_path in files_in_commit:
                    task_id = (repo_name, snapshot['commit_hash'], file_path)
                    
                    # --- THE RESUME LOGIC ---
                    if task_id in completed_tasks:
                        continue # Skip this file, it's already done
                    
                    # --- This is new work ---
                    # 1. Get static metrics
                    full_file_path = os.path.join(repo_path, file_path)
                    static_metrics = analyze_file_metrics(full_file_path)
                    if not static_metrics: continue

                    # 2. Get history metrics
                    history_metrics = get_file_history_metrics(repo_path, file_path, snapshot['commit_hash'])
                    if not history_metrics: continue
                    
                    # 3. Combine into a single row
                    row = {**static_metrics, **history_metrics}
                    row['file_path'] = file_path
                    row['commit_hash'] = snapshot['commit_hash']
                    row['snapshot_date'] = snapshot['snapshot_date']
                    row['repo_name'] = repo_name
                    row['label'] = snapshot['label']
                    
                    # 4. Append the new row to the CSV
                    pd.DataFrame([row]).to_csv(OUTPUT_CSV_PATH, mode='a', header=False, index=False)
                    
                    # 5. Update our in-memory set to avoid re-processing in this same run
                    completed_tasks.add(task_id)

                pbar_snap.update(1)

    print("\n--- Pipeline Complete! ---")
    final_dataset = pd.read_csv(OUTPUT_CSV_PATH)
    print(f"Dataset saved to: {OUTPUT_CSV_PATH}")
    print(f"Total rows (file snapshots): {len(final_dataset)}")
    if not final_dataset.empty:
        print(f"Label distribution:\n{final_dataset['label'].value_counts(normalize=True)}")

if __name__ == "__main__":
    # To make this self-contained, we're copying the functions here
    # This is not ideal for modularity but great for a single, robust script
    from feature_extraction.code_metrics import analyze_repo_at_commit
    from feature_extraction.repo_metrics import get_file_history_metrics
    main()