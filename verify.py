import os
import sys
# Include the api directory in sys.path to load moved modules
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "api"))

import shutil
import git
import database
import scanner
import charts

TEST_REPO_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_repo")

def setup_test_repo():
    print("--- Setting up test repository ---")
    if os.path.exists(TEST_REPO_PATH):
        shutil.rmtree(TEST_REPO_PATH)
    os.makedirs(TEST_REPO_PATH)
    
    # Initialize Git repository
    repo = git.Repo.init(TEST_REPO_PATH)
    
    # Configure user for commits
    repo.config_writer().set_value("user", "name", "Test Developer").release()
    repo.config_writer().set_value("user", "email", "test@gitpulse.local").release()
    
    # 1. Create first commit (init)
    file1 = os.path.join(TEST_REPO_PATH, "main.py")
    with open(file1, "w") as f:
        f.write("print('Hello Git-Pulse')\nprint('Line 2')\nprint('Line 3')\n")
    repo.index.add(["main.py"])
    repo.index.commit("Initial commit: setup main.py")
    print("Created commit 1: setup main.py")
    
    # 2. Create second commit (add files)
    file2 = os.path.join(TEST_REPO_PATH, "styles.css")
    with open(file2, "w") as f:
        f.write("body {\n  background: #000;\n  color: #fff;\n}\n")
    with open(file1, "a") as f:
        f.write("print('Line 4 added')\n")
    repo.index.add(["styles.css", "main.py"])
    repo.index.commit("Feature: Added styles.css and expanded main.py")
    print("Created commit 2: added styles.css")
    
    # 3. Create third commit (delete lines)
    with open(file1, "w") as f:
        f.write("print('Hello Git-Pulse')\nprint('Line 4 added')\n")
    repo.index.add(["main.py"])
    repo.index.commit("Fix: Cleaned up main.py")
    print("Created commit 3: cleaned main.py")
    
    return repo

def verify_git_pulse():
    # Delete existing database file for a clean slate
    db_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "git_pulse.db")
    if os.path.exists(db_file):
        os.remove(db_file)
        print("Cleared old database file.")
        
    # Setup test repository
    setup_test_repo()
    
    print("\n--- Initializing Git-Pulse DB & Scanning ---")
    database.init_db()
    
    # Register repo
    try:
        repo_id = database.add_repository("Test Repo", TEST_REPO_PATH)
        print(f"Registered repository in DB with ID: {repo_id}")
    except Exception as e:
        print(f"Error registering repo: {e}")
        return
        
    # Scan repository
    scanned_commits = scanner.scan_repository(repo_id, TEST_REPO_PATH)
    print(f"Scan complete. Number of scanned commits: {scanned_commits}")
    
    # Verify DB Summary Stats
    summary = database.get_dashboard_summary(repo_id)
    print("\n--- DB Summary Stats ---")
    print(f"Total Commits: {summary['total_commits']} (Expected: 3)")
    print(f"Total Contributors: {summary['total_authors']} (Expected: 1)")
    print(f"Total Additions: {summary['total_additions']} (Expected: 9)")
    print(f"Total Deletions: {summary['total_deletions']} (Expected: 2)")
    
    assert summary['total_commits'] == 3, "Commit count should be 3"
    assert summary['total_authors'] == 1, "Author count should be 1"
    
    # Verify File Type Distribution
    distribution = database.get_file_type_distribution(repo_id)
    print("\n--- File Type Distribution ---")
    for row in distribution:
        print(f"Extension: {row['extension']}, Additions: {row['total_additions']}, Deletions: {row['total_deletions']}")
        
    # Verify Recent Commits
    recent = database.get_recent_commits(repo_id)
    print("\n--- Recent Commits ---")
    for c in recent:
        print(f"[{c['sha'][:7]}] {c['author']}: {c['message']} (+{c['additions']}, -{c['deletions']})")
        
    # Verify Chart Generators
    print("\n--- Generating SVG Charts ---")
    velocity_data = database.get_commits_by_date(repo_id)
    heatmap_data = database.get_hourly_activity(repo_id)
    donut_data = database.get_file_type_distribution(repo_id)
    
    velocity_svg = charts.generate_velocity_chart(velocity_data)
    heatmap_svg = charts.generate_heatmap_chart(heatmap_data)
    donut_svg = charts.generate_donut_chart(donut_data)
    
    print(f"Velocity SVG size: {len(velocity_svg)} chars")
    print(f"Heatmap SVG size: {len(heatmap_svg)} chars")
    print(f"Donut SVG size: {len(donut_svg)} chars")
    
    assert "<svg" in velocity_svg, "Velocity chart should contain <svg>"
    assert "<svg" in heatmap_svg, "Heatmap should contain <svg>"
    assert "<svg" in donut_svg, "Donut chart should contain <svg>"
    
    print("\n--- INCREMENTAL SCANNING TEST ---")
    repo = git.Repo(TEST_REPO_PATH)
    file1 = os.path.join(TEST_REPO_PATH, "main.py")
    with open(file1, "a") as f:
        f.write("print('Incremental commit!')\n")
    repo.index.add(["main.py"])
    repo.index.commit("Chore: Added incremental test print statement")
    
    # Query database before rescanning
    active_repo = database.get_repository(repo_id)
    last_sha = active_repo["last_scanned_commit"]
    
    # Scan again
    newly_scanned = scanner.scan_repository(repo_id, TEST_REPO_PATH, last_sha)
    print(f"Newly scanned commits: {newly_scanned} (Expected: 1)")
    
    summary2 = database.get_dashboard_summary(repo_id)
    print(f"New Total Commits: {summary2['total_commits']} (Expected: 4)")
    assert newly_scanned == 1, "Incremental scan should only process 1 new commit"
    assert summary2['total_commits'] == 4, "Total commits should now be 4"
    
    print("\nALL VERIFICATIONS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    verify_git_pulse()
