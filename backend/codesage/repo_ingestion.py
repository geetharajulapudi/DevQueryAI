import os, re, shutil, tempfile
from git import Repo
from git.exc import GitCommandError

ALLOWED_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".mjs",
    ".java", ".kt", ".go", ".rb", ".php", ".rs", ".cs", ".cpp", ".c", ".h",
    ".sh", ".bash", ".json", ".yaml", ".yml", ".toml",
    ".html", ".css", ".scss", ".md", ".sql",
}
IGNORED_DIRS = {"node_modules", ".git", "dist", "build", "__pycache__", ".venv", "venv", "env"}
MAX_FILE_SIZE_BYTES = 300 * 1024
MAX_FILES = 200

_GIT_HOST_PATTERNS = [
    r"(https?://github\.com/[^/]+/[^/]+)",
    r"(https?://gitlab\.com/[^/]+/[^/]+)",
    r"(https?://bitbucket\.org/[^/]+/[^/]+)",
    r"(https?://dev\.azure\.com/[^/]+/[^/]+/_git/[^/]+)",
]

def normalize_repo_url(url):
    url = url.strip().rstrip("/")
    for pattern in _GIT_HOST_PATTERNS:
        match = re.match(pattern, url)
        if match:
            return match.group(1)
    return url

def clone_repo(repo_url):
    repo_url = repo_url.strip()
    if os.path.isdir(repo_url):
        return repo_url
    if not repo_url.startswith(("https://", "http://", "git@")):
        raise ValueError(f"Invalid URL: {repo_url}")
    clean_url = normalize_repo_url(repo_url)
    tmp_dir = tempfile.mkdtemp(prefix="codesage_")
    try:
        print(f"[+] Cloning {clean_url} ...")
        Repo.clone_from(clean_url, tmp_dir, depth=1)
        return tmp_dir
    except GitCommandError as e:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise RuntimeError(f"Failed to clone repository: {e}") from e

def read_files(repo_path):
    files = []
    for root, dirs, filenames in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]
        for filename in filenames:
            if len(files) >= MAX_FILES:
                return files
            ext = os.path.splitext(filename)[1].lower()
            if ext not in ALLOWED_EXTENSIONS:
                continue
            filepath = os.path.join(root, filename)
            if os.path.getsize(filepath) > MAX_FILE_SIZE_BYTES:
                continue
            try:
                with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read().strip()
                if content:
                    files.append({"path": os.path.relpath(filepath, repo_path), "content": content})
            except OSError:
                pass
    if not files:
        raise ValueError("No relevant source files found in the repository.")
    print(f"[+] Read {len(files)} files.")
    return files

def cleanup_repo(repo_path):
    if repo_path and repo_path.startswith("/tmp/codesage_"):
        shutil.rmtree(repo_path, ignore_errors=True)
