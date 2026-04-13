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
    # Python
    ".py",
    # JavaScript / TypeScript
    ".js", ".ts", ".jsx", ".tsx", ".mjs",
    # Backend languages
    ".java", ".kt", ".go", ".rb", ".php", ".rs", ".cs", ".cpp", ".c", ".h",
    # Shell & config
    ".sh", ".bash",
    # Data / config formats (useful for understanding project structure)
    ".json", ".yaml", ".yml", ".toml", ".env.example",
    # Web
    ".html", ".css", ".scss",
    # Docs
    ".md",
    # SQL
    ".sql",
}
IGNORED_DIRS = {
    "node_modules", ".git", "dist", "build", "__pycache__",
    ".venv", "venv", "env", ".idea", ".vscode", "coverage",
    "*.egg-info", ".mypy_cache", ".pytest_cache",
}
MAX_FILE_SIZE_BYTES = 300 * 1024  # 300 KB
MAX_FILES = 200


# Patterns to extract root repo URL for each Git host
_GIT_HOST_PATTERNS = [
    # GitHub:    https://github.com/owner/repo(/tree/branch/...)
    (r"(https?://github\.com/[^/]+/[^/]+)", None),
    # GitLab:    https://gitlab.com/owner/repo(/-/tree/branch/...)
    (r"(https?://gitlab\.com/[^/]+/[^/]+)", r"/-/"),
    # Bitbucket: https://bitbucket.org/owner/repo(/src/branch/...)
    (r"(https?://bitbucket\.org/[^/]+/[^/]+)", None),
    # Azure DevOps: https://dev.azure.com/org/project/_git/repo
    (r"(https?://dev\.azure\.com/[^/]+/[^/]+/_git/[^/]+)", None),
]


def normalize_repo_url(url: str) -> str:
    """
    Strips subfolder/branch/blob paths from any supported Git host URL.
    Supports GitHub, GitLab, Bitbucket, Azure DevOps.
    """
    url = url.strip().rstrip("/")
    for pattern, _ in _GIT_HOST_PATTERNS:
        match = re.match(pattern, url)
        if match:
            return match.group(1)
    return url  # return as-is for self-hosted or git@ URLs


def clone_repo(repo_url: str) -> str:
    """
    Accepts:
      - Any Git remote URL (GitHub, GitLab, Bitbucket, Azure DevOps, self-hosted)
      - A local directory path (must be an existing folder)
    Returns the path to use for reading files.
    Raises ValueError for invalid input, RuntimeError for clone failures.
    """
    repo_url = repo_url.strip()

    # Local folder — no cloning needed, read directly
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
    """
    Walks the repo directory and reads source files matching allowed extensions.
    Returns a list of dicts: {path, content}
    Raises ValueError if no relevant files are found.
    """
    files = []

    for root, dirs, filenames in os.walk(repo_path):
        # Prune ignored directories in-place
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
    """Removes temp cloned repo. Skips cleanup if it's a local user directory."""
    if not repo_path or not repo_path.startswith("/tmp/codesage_"):
        return  # never delete a local folder the user pointed us to
    shutil.rmtree(repo_path, ignore_errors=True)
    print(f"[+] Cleaned up {repo_path}")
