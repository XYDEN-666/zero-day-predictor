import os
import subprocess

# --- Configuration ---
# List of well-known open-source projects with public CVE histories
# We choose a mix of languages (C, Python)
# Format: ('project_name', 'git_url')
TARGET_REPOS = [
    ('httpd', 'https://github.com/apache/httpd.git'),
    ('django', 'https://github.com/django/django.git'),
    ('redis', 'https://github.com/redis/redis.git'),
    # Add more repositories here if you wish
    # ('linux', 'https://github.com/torvalds/linux.git'), # Note: The Linux kernel is huge!
]

# Define the output directory for the cloned repositories
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'data', '01_raw', 'repositories')

def clone_repositories():
    """
    Clones the target repositories into the specified output directory.
    """
    # Ensure the output directory exists
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print(f"Starting repository cloning process. Repos will be saved in: {os.path.abspath(OUTPUT_DIR)}")

    for name, url in TARGET_REPOS:
        repo_path = os.path.join(OUTPUT_DIR, name)
        
        # Check if the repository directory already exists
        if os.path.exists(repo_path):
            print(f"\nRepository '{name}' already exists at {repo_path}. Skipping clone.")
            # Optional: You could add logic here to `git pull` for updates
            continue
            
        print(f"\nCloning '{name}' from {url}...")
        
        try:
            # We use subprocess to call the git command-line tool directly.
            # This is often more robust for large initial clones than library wrappers.
            # The command is: git clone [url] [destination_path]
            result = subprocess.run(
                ['git', 'clone', url, repo_path],
                check=True,        # Raises an exception if git returns a non-zero exit code
                capture_output=True, # Captures stdout and stderr
                text=True          # Decodes stdout/stderr as text
            )
            print(f"Successfully cloned '{name}'.")
            # print("Git output:\n", result.stdout) # Uncomment for verbose output
            
        except FileNotFoundError:
            print("ERROR: 'git' command not found. Please ensure Git is installed and in your system's PATH.")
            break
        except subprocess.CalledProcessError as e:
            print(f"ERROR: Failed to clone '{name}'.")
            print(f"Return code: {e.returncode}")
            print(f"Stderr:\n{e.stderr}")
            
    print("\nRepository cloning process completed.")


if __name__ == "__main__":
    clone_repositories()