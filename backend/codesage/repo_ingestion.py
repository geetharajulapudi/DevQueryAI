"""
repo_ingestion.py
Clones a GitHub repo and reads relevant source code files.
"""

import os
import re
import shutil
import tempfile
from git import Repo
from git.exc import GitCommandError

ALLOWED_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".mjs",
    ".java", ".kt", ".go", ".rb", ".php", ".rs", ".cs", ".cpp", ".c", ".h",
    ".sh", ".bash",
    ".json", ".yaml", ".yml", ".toml", ".env.example",
    ".html", ".css", ".scss",
    ".md", ".sql",
}
IGNORED_DIRS = {
    "node_modules", ".git", "dist", "build", "__pycache__",
    ".venv", "venv", "env", ".idea", ".vscode", "coverage",
    ".mypy_cache", ".pytest_cache",
}
MAX_FILE_SIZE_BYTES = 300 * 1024
MAX_FILES = 200

_GIT_HOST_PATTERNS = [
    (r"(https?://github\.com/[^/]+/[^/]+)", None),
    (r"(https?://gitlab\.com/[^/]+/[^/]+)", None),
    (r"(https?://bitbucket\.org/[^/]+/[^/]+)", None),
    (r"(https?://dev\.azure\.com/[^/]+/[^/]+/_git/[^/]+)", None),
]


def normalize_repo_url(url: str) -> str:
    url = url.strip().rstrip("/")
    for pattern, _ in _GIT_HOST_PATTERNS:
        match = re.match(pattern, url)
        if match:
            return match.group(1)
    return url


def clone_repo(repo_url: str) -> str:
    repo_url = repo_url.strip()

    if os.path.isdir(repo_url):
        print(f"[+] Using local directory: {repo_url}")
        return repo_url

    if not repo_url.startswith(("https://", "http://", "git@")):
        raise ValueError(f"Invalid input: not a valid URL or existing local path: {repo_url}")

    clean_url = normalize_repo_url(repo_url)
    if clean_url != repo_url:
        print(f"[!] URL normalized: {repo_url} → {clean_url}")

    tmp_dir = tempfile.mkdtemp(prefix="codesage_")
    try:
        print(f"[+] Cloning {clean_url} ...")
        Repo.clone_from(clean_url, tmp_dir, depth=1)
        print(f"[+] Cloned to {tmp_dir}")
        return tmp_dir
    except GitCommandError as e:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise RuntimeError(f"Failed to clone repository: {e}") from e


def read_files(repo_path: str) -> list[dict]:
    files = []
    for root, dirs, filenames in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]
        for filename in filenames:
            if len(files) >= MAX_FILES:
                print(f"[!] Reached {MAX_FILES} file limit, stopping early.")
                return files
            ext = os.path.splitext(filename)[1].lower()
            if ext not in ALLOWED_EXTENSIONS:
                continue
            filepath = os.path.join(root, filename)
            if os.path.getsize(filepath) > MAX_FILE_SIZE_BYTES:
                print(f"[!] Skipping large file: {filepath}")
                continue
            try:
                with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read().strip()
                if content:
                    rel_path = os.path.relpath(filepath, repo_path)
                    files.append({"path": rel_path, "content": content})
            except OSError as e:
                print(f"[!] Could not read {filepath}: {e}")

    if not files:
        raise ValueError("No relevant source files found in the repository.")
    print(f"[+] Read {len(files)} source files.")
    return files


def cleanup_repo(repo_path: str) -> None:
    if not repo_path or not repo_path.startswith("/tmp/codesage_"):
        return
    shutil.rmtree(repo_path, ignore_errors=True)
    print(f"[+] Cleaned up {repo_path}")
