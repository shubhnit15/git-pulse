import sqlite3
import os
from datetime import datetime

if os.environ.get("VERCEL"):
    DB_PATH = "/tmp/git_pulse.db"
else:
    DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "git_pulse.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create repositories table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS repositories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        path TEXT UNIQUE NOT NULL,
        last_scanned_commit TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """)
    
    # Create commits table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS commits (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        repo_id INTEGER NOT NULL,
        sha TEXT NOT NULL,
        author TEXT NOT NULL,
        timestamp INTEGER NOT NULL,
        message TEXT,
        additions INTEGER DEFAULT 0,
        deletions INTEGER DEFAULT 0,
        FOREIGN KEY (repo_id) REFERENCES repositories(id) ON DELETE CASCADE,
        UNIQUE (repo_id, sha)
    );
    """)
    
    # Create file_stats table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS file_stats (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        commit_id INTEGER NOT NULL,
        extension TEXT NOT NULL,
        additions INTEGER DEFAULT 0,
        deletions INTEGER DEFAULT 0,
        FOREIGN KEY (commit_id) REFERENCES commits(id) ON DELETE CASCADE
    );
    """)
    
    # Create index for faster querying
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_commits_repo_timestamp ON commits(repo_id, timestamp);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_file_stats_commit ON file_stats(commit_id);")
    
    conn.commit()
    conn.close()

def add_repository(name: str, path: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO repositories (name, path) VALUES (?, ?);",
            (name, path)
        )
        conn.commit()
        repo_id = cursor.lastrowid
        return repo_id
    except sqlite3.IntegrityError:
        # Repository already exists
        cursor.execute("SELECT id FROM repositories WHERE path = ?;", (path,))
        row = cursor.fetchone()
        if row:
            return row["id"]
        raise
    finally:
        conn.close()

def get_repositories():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM repositories ORDER BY created_at DESC;")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_repository(repo_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM repositories WHERE id = ?;", (repo_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def delete_repository(repo_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM repositories WHERE id = ?;", (repo_id,))
    conn.commit()
    conn.close()

def update_repo_last_scanned_commit(repo_id: int, commit_sha: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE repositories SET last_scanned_commit = ? WHERE id = ?;",
        (commit_sha, repo_id)
    )
    conn.commit()
    conn.close()

def save_commit_and_stats(repo_id: int, sha: str, author: str, timestamp: int, message: str, additions: int, deletions: int, file_stats_list: list):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Insert commit
        cursor.execute(
            """
            INSERT OR IGNORE INTO commits (repo_id, sha, author, timestamp, message, additions, deletions)
            VALUES (?, ?, ?, ?, ?, ?, ?);
            """,
            (repo_id, sha, author, timestamp, message, additions, deletions)
        )
        # Get the commit_id (either newly inserted or existing)
        cursor.execute("SELECT id FROM commits WHERE repo_id = ? AND sha = ?;", (repo_id, sha))
        commit_id = cursor.fetchone()["id"]
        
        # Insert file stats if we inserted a new commit
        # To avoid duplicates if we ignored, let's delete existing file stats first
        cursor.execute("DELETE FROM file_stats WHERE commit_id = ?;", (commit_id,))
        
        for stat in file_stats_list:
            cursor.execute(
                """
                INSERT INTO file_stats (commit_id, extension, additions, deletions)
                VALUES (?, ?, ?, ?);
                """,
                (commit_id, stat["extension"], stat["additions"], stat["deletions"])
            )
        conn.commit()
        return commit_id
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def get_dashboard_summary(repo_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Total Commits
    cursor.execute("SELECT COUNT(*) as count FROM commits WHERE repo_id = ?;", (repo_id,))
    total_commits = cursor.fetchone()["count"]
    
    # 2. Total Authors
    cursor.execute("SELECT COUNT(DISTINCT author) as count FROM commits WHERE repo_id = ?;", (repo_id,))
    total_authors = cursor.fetchone()["count"]
    
    # 3. Total Lines Added / Deleted
    cursor.execute(
        "SELECT SUM(additions) as total_add, SUM(deletions) as total_del FROM commits WHERE repo_id = ?;",
        (repo_id,)
    )
    res = cursor.fetchone()
    total_additions = res["total_add"] or 0
    total_deletions = res["total_del"] or 0
    
    conn.close()
    
    return {
        "total_commits": total_commits,
        "total_authors": total_authors,
        "total_additions": total_additions,
        "total_deletions": total_deletions
    }

def get_recent_commits(repo_id: int, limit: int = 5):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM commits WHERE repo_id = ? ORDER BY timestamp DESC LIMIT ?;",
        (repo_id, limit)
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_commits_by_date(repo_id: int, days_limit: int = 14):
    """
    Returns dates and sum of additions, deletions, commits count, aggregated daily.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # We aggregate by date (YYYY-MM-DD). We use SQLite's date function with epoch time.
    cursor.execute(
        """
        SELECT 
            date(timestamp, 'unixepoch') as commit_date,
            COUNT(*) as commit_count,
            SUM(additions) as total_additions,
            SUM(deletions) as total_deletions
        FROM commits
        WHERE repo_id = ?
        GROUP BY commit_date
        ORDER BY commit_date ASC
        LIMIT ?;
        """,
        (repo_id, days_limit)
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_hourly_activity(repo_id: int):
    """
    Returns commit counts grouped by day of week (0=Sunday, 6=Saturday) and hour of day (0-23).
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # strftime('%w', ...) returns day of week (0-6, where 0 is Sunday)
    # strftime('%H', ...) returns hour (00-23)
    cursor.execute(
        """
        SELECT 
            CAST(strftime('%w', timestamp, 'unixepoch') AS INTEGER) as day_of_week,
            CAST(strftime('%H', timestamp, 'unixepoch') AS INTEGER) as hour_of_day,
            COUNT(*) as commit_count
        FROM commits
        WHERE repo_id = ?
        GROUP BY day_of_week, hour_of_day;
        """,
        (repo_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_file_type_distribution(repo_id: int, limit: int = 5):
    """
    Returns sum of additions and deletions per file extension.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        """
        SELECT 
            fs.extension,
            SUM(fs.additions) as total_additions,
            SUM(fs.deletions) as total_deletions,
            COUNT(DISTINCT fs.commit_id) as commit_count
        FROM file_stats fs
        JOIN commits c ON fs.commit_id = c.id
        WHERE c.repo_id = ?
        GROUP BY fs.extension
        ORDER BY (total_additions + total_deletions) DESC
        LIMIT ?;
        """,
        (repo_id, limit)
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully at", DB_PATH)
