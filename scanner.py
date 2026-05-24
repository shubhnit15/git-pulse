import os
import git
from database import save_commit_and_stats, update_repo_last_scanned_commit

def is_valid_git_repo(path: str) -> bool:
    if not path or not os.path.exists(path):
        return False
    try:
        git.Repo(path)
        return True
    except (git.exc.InvalidGitRepositoryError, git.exc.NoSuchPathError):
        return False

def get_extension(filepath: str) -> str:
    name = os.path.basename(filepath)
    if '.' in name:
        ext = name.split('.')[-1].lower()
        if len(ext) <= 5 and ext.isalnum():
            return f".{ext}"
    return "other"

def scan_repository(repo_id: int, path: str, last_scanned_sha: str = None) -> int:
    """
    Scans a local repository incrementally, extracts commits metadata, saves to database.
    Returns the number of scanned commits.
    """
    if not is_valid_git_repo(path):
        raise ValueError("Invalid Git Repository path.")
        
    repo = git.Repo(path)
    
    # Check if repository has any commits
    try:
        head_commit = repo.head.commit
    except ValueError:
        # Repository is empty (no commits yet)
        return 0
        
    commits_to_scan = []
    
    if last_scanned_sha:
        try:
            # Check if last_scanned_sha is valid and exists in repo
            repo.commit(last_scanned_sha)
            
            # If the current HEAD is the same as last scanned, nothing to do
            if head_commit.hexsha == last_scanned_sha:
                return 0
                
            # Get commits from last_scanned_sha to HEAD
            # git log last_scanned_sha..HEAD
            commits_to_scan = list(repo.iter_commits(f"{last_scanned_sha}..HEAD"))
            # iter_commits returns newest first. Reverse to process chronologically (oldest first).
            commits_to_scan.reverse()
        except Exception:
            # If SHA not found, fallback to full scan
            last_scanned_sha = None
            
    if not last_scanned_sha:
        # Full scan: limit to last 1000 commits
        commits_to_scan = list(repo.iter_commits(max_count=1000))
        commits_to_scan.reverse()
        
    total_scanned = len(commits_to_scan)
    if total_scanned == 0:
        return 0
        
    for commit in commits_to_scan:
        sha = commit.hexsha
        author = commit.author.name or commit.author.email or "Unknown"
        timestamp = commit.committed_date
        # Commit message (cleaned)
        message = commit.message.strip() if commit.message else ""
        if len(message) > 200:
            message = message[:197] + "..."
            
        try:
            # Get commit stats (insertions and deletions)
            stats = commit.stats
            total = stats.total
            additions = total.get('insertions', 0)
            deletions = total.get('deletions', 0)
            
            # Group stats by file extensions
            ext_map = {}
            for file_path, fstat in stats.files.items():
                ext = get_extension(file_path)
                if ext not in ext_map:
                    ext_map[ext] = {"additions": 0, "deletions": 0}
                ext_map[ext]["additions"] += fstat.get('insertions', 0)
                ext_map[ext]["deletions"] += fstat.get('deletions', 0)
                
            file_stats_list = []
            for ext, counts in ext_map.items():
                file_stats_list.append({
                    "extension": ext,
                    "additions": counts["additions"],
                    "deletions": counts["deletions"]
                })
                
            save_commit_and_stats(
                repo_id=repo_id,
                sha=sha,
                author=author,
                timestamp=timestamp,
                message=message,
                additions=additions,
                deletions=deletions,
                file_stats_list=file_stats_list
            )
        except Exception as e:
            # In case stats extraction fails (e.g. binary files or empty commits), log and insert minimal commit stats
            print(f"Stats parse failed for commit {sha[:7]}: {e}")
            save_commit_and_stats(
                repo_id=repo_id,
                sha=sha,
                author=author,
                timestamp=timestamp,
                message=message,
                additions=0,
                deletions=0,
                file_stats_list=[]
            )
            
    # Update last scanned commit to the current HEAD
    update_repo_last_scanned_commit(repo_id, head_commit.hexsha)
    
    return total_scanned
