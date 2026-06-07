import os
import github
from dotenv import load_dotenv
from github import Github

load_dotenv()

REPO = "KingKai31/company-os"
LOCAL_FILE = "landing.html"
REMOTE_FILE = "index.html"


def main():
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        raise ValueError("GITHUB_TOKEN not set in .env")

    print(f"[FIX_PAGE] Reading {LOCAL_FILE}...")
    with open(LOCAL_FILE, "r", encoding="utf-8") as f:
        html_content = f.read()

    print(f"[FIX_PAGE] Connecting to GitHub ({REPO})...")
    g = Github(auth=github.Auth.Token(token))
    repo = g.get_repo(REPO)

    commit_message = "Update landing page via fix_page.py"

    try:
        contents = repo.get_contents(REMOTE_FILE)
        repo.update_file(contents.path, commit_message, html_content, contents.sha)
        print(f"[FIX_PAGE] Updated existing {REMOTE_FILE}")
    except Exception:
        repo.create_file(REMOTE_FILE, commit_message, html_content)
        print(f"[FIX_PAGE] Created new {REMOTE_FILE}")

    print(f"[FIX_PAGE] Live at: https://kingkai31.github.io/company-os/")


if __name__ == "__main__":
    main()
