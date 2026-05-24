import os
from fastapi import FastAPI, Request, Form, HTTPException, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import database
import scanner
import charts

app = FastAPI(title="Git-Pulse Dashboard")

# Initialize SQLite database schema
database.init_db()

# Setup templates (looking one level up since main.py is now inside api/)
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATES_DIR = os.path.join(parent_dir, "templates")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request, active_id: int = None):
    repos = database.get_repositories()
    active_repo = None
    
    if active_id:
        active_repo = database.get_repository(active_id)
    elif repos:
        active_repo = repos[0]
        
    return templates.TemplateResponse(
        request,
        "index.html", 
        {
            "repos": repos, 
            "active_repo": active_repo
        }
    )

@app.post("/repo", response_class=HTMLResponse)
async def add_repo(request: Request, path: str = Form(...)):
    path = path.strip()
    
    # 1. Validation
    if not path:
        return "<span class='text-rose-400 text-sm'>Path cannot be empty.</span>"
        
    if not os.path.exists(path):
        return f"<span class='text-rose-400 text-sm'>Folder does not exist.</span>"
        
    if not scanner.is_valid_git_repo(path):
        return f"<span class='text-rose-400 text-sm'>Not a valid Git repository (no .git folder).</span>"
        
    # 2. Add to database
    repo_name = os.path.basename(os.path.normpath(path))
    if not repo_name:
        repo_name = "Root Repository"
        
    try:
        repo_id = database.add_repository(repo_name, path)
        # Trigger initial scan
        scanner.scan_repository(repo_id, path)
    except Exception as e:
        return f"<span class='text-rose-400 text-sm'>Error scanning: {str(e)}</span>"
        
    # 3. Return HTMX redirect to refresh the main page with the active repository
    response = Response()
    response.headers["HX-Redirect"] = f"/?active_id={repo_id}"
    return response

@app.delete("/repo/{repo_id}", response_class=HTMLResponse)
async def delete_repo(repo_id: int):
    database.delete_repository(repo_id)
    
    # Send HTMX redirect to root to refresh lists
    response = Response()
    response.headers["HX-Redirect"] = "/"
    return response

@app.get("/repo/{repo_id}/dashboard", response_class=HTMLResponse)
async def get_dashboard(request: Request, repo_id: int):
    repo = database.get_repository(repo_id)
    if not repo:
        return "<div class='text-center p-8 text-rose-400 font-semibold'>Repository not found in Git-Pulse database.</div>"
        
    # 1. Trigger smart (incremental) scan on every 30s HTMX poll
    error_msg = None
    try:
        scanner.scan_repository(repo_id, repo["path"], repo["last_scanned_commit"])
        # Fetch updated repo record (updates last_scanned_commit SHA)
        repo = database.get_repository(repo_id)
    except ValueError:
        error_msg = "Repository path is no longer valid. Has it been moved or deleted?"
    except Exception as e:
        error_msg = f"Scan error: {str(e)}"
        
    # 2. Fetch all analytics
    summary = database.get_dashboard_summary(repo_id)
    velocity_data = database.get_commits_by_date(repo_id, days_limit=14)
    heatmap_data = database.get_hourly_activity(repo_id)
    donut_data = database.get_file_type_distribution(repo_id, limit=5)
    recent_commits = database.get_recent_commits(repo_id, limit=8)
    
    from datetime import datetime
    for c in recent_commits:
        c["formatted_date"] = datetime.fromtimestamp(c["timestamp"]).strftime("%b %d, %H:%M")
    
    # 3. Generate native SVGs
    velocity_svg = charts.generate_velocity_chart(velocity_data)
    heatmap_svg = charts.generate_heatmap_chart(heatmap_data)
    donut_svg = charts.generate_donut_chart(donut_data)
    
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "repo": repo,
            "summary": summary,
            "velocity_svg": velocity_svg,
            "heatmap_svg": heatmap_svg,
            "donut_svg": donut_svg,
            "recent_commits": recent_commits,
            "error_msg": error_msg
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8080, reload=True)
