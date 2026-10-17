#!/usr/bin/env python3
"""keyaudit: find AI/dev API keys sitting in plain text on your machine.

Never prints a secret. Output: key type, file, line, masked value (prefix + last 4).
Usage: python3 keyaudit.py [--json out.json] [extra_dir ...]
"""
import os, re, sys, json, stat, subprocess, hashlib
from pathlib import Path

HOME = Path.home()

PATTERNS = {
    "Anthropic":   r"sk-ant-(?:api|admin)\d{2}-[A-Za-z0-9_\-]{20,}",
    "OpenRouter":  r"sk-or-v1-[a-f0-9]{32,}",
    "OpenAI":      r"sk-(?:proj-|svcacct-|admin-)?[A-Za-z0-9_\-]{20,}T3BlbkFJ[A-Za-z0-9_\-]{20,}|sk-proj-[A-Za-z0-9_\-]{40,}",
    "Google AI":   r"AIza[0-9A-Za-z_\-]{35}",
    "Groq":        r"gsk_[A-Za-z0-9]{40,}",
    "HuggingFace": r"hf_[A-Za-z0-9]{30,}",
    "DeepSeek/generic sk-": r"(?<![A-Za-z0-9_\-])sk-[a-f0-9]{32}(?![A-Za-z0-9])",
    "GitHub":      r"gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{60,}",
    "GitLab":      r"glpat-[A-Za-z0-9_\-]{20}",
    "Slack":       r"xox[abpr]-[A-Za-z0-9\-]{10,}",
    "AWS":         r"(?:AKIA|ASIA)[0-9A-Z]{16}",
    "Stripe live": r"(?:sk|rk)_live_[A-Za-z0-9]{20,}",
    "npm":         r"npm_[A-Za-z0-9]{36}",
}
RX = [(k, re.compile(v)) for k, v in PATTERNS.items()]
# unknown vendors: a secret-sounding field name with a long random value
GENERIC = re.compile(r"""(?i)["']?[A-Za-z_\-]*(?:api[_\-]?key|token|secret|access[_\-]?key|auth)["']?\s*[:=]\s*["']([A-Za-z0-9_\-\.]{24,})["']""")

# Where AI tools and devs usually leave keys
TARGETS = [
    ".zshrc", ".zprofile", ".bashrc", ".bash_profile", ".profile", ".zshenv",
    ".zsh_history", ".bash_history", ".python_history", ".node_repl_history",
    ".claude.json", ".claude", ".codex", ".cursor", ".continue", ".aider.conf.yml", ".env",
    ".config/opencode", ".local/share/opencode", ".config/gh", ".config/github-copilot",
    ".gemini", ".npmrc", ".netrc", ".aws", ".docker/config.json", ".ollama",
    "Library/Application Support/Claude/claude_desktop_config.json",
    "Library/Application Support/Cursor/User/settings.json",
    "Library/Application Support/Cursor/User/globalStorage/storage.json",
    "Library/Application Support/Code/User/settings.json",
    "Library/Application Support/Code/User/mcp.json",
    "Library/Application Support/Windsurf/User/settings.json",
    "Library/Application Support/Zed/settings.json", ".config/zed",
    ".codeium", ".lmstudio",
]
TARGET_GLOBS = [".claude.json.*", ".env*", ".*rc.bak*"]
PROJECT_ROOTS = ["Projects", "Developer", "code", "dev", "src", "Desktop", "Documents", "work", "repos"]
SKIP_DIRS = {"node_modules", ".git", "venv", ".venv", "__pycache__", "dist", "build", ".next",
             "Library", ".Trash", "Pods", "DerivedData", ".cache", "target"}
MAX_SIZE = 2_000_000
CATEGORY = [  # how bad is the location
    ("history", "shell history"), ("rc", "shell startup file"), (".env", ".env file"),
    ("mcp", "MCP / editor config"), ("config", "tool config"),
]

def classify(p: str) -> str:
    n = p.lower()
    if "history" in n: return "shell history"
    if re.search(r"/\.(zsh|bash)(rc|_profile|env)$|/\.z?profile$", n): return "shell startup file"
    if "/.env" in n or n.endswith(".env"): return ".env file"
    if "mcp" in n or "claude_desktop_config" in n: return "MCP config"
    if any(t in n for t in ("cursor", "/code/", "windsurf", "zed", "continue")): return "editor config"
    return "tool config"

def mask(s: str) -> str:
    head = re.match(r"[a-zA-Z]+[_\-](?:[a-z]+[_\-])?(?:v1-|api\d\d-)?", s)
    h = head.group(0) if head else s[:4]
    return f"{h}…{s[-4:]}"

def git_tracked(path: Path) -> bool:
    try:
        r = subprocess.run(["git", "-C", str(path.parent), "ls-files", "--error-unmatch", path.name],
                           capture_output=True, timeout=5)
        return r.returncode == 0
    except Exception:
        return False

def iter_files():
    seen = set()
    for t in TARGETS:
        p = HOME / t
        if p.is_file(): yield p
        elif p.is_dir():
            for root, dirs, files in os.walk(p):
                dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
                for f in files: yield Path(root) / f
    for g in TARGET_GLOBS:
        for p in HOME.glob(g):
            if p.is_file(): yield p
    roots = [HOME / r for r in PROJECT_ROOTS] + [Path(a) for a in sys.argv[1:] if not a.startswith("--")]
    for r in roots:
        if not r.is_dir(): continue
        for root, dirs, files in os.walk(r):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".") or d in (".vscode", ".cursor", ".claude")]
            for f in files:
                if f.startswith(".env") or f in ("mcp.json", ".mcp.json", "settings.json", "settings.local.json",
                                                  "config.json", "config.toml", "config.yaml", "docker-compose.yml"):
                    yield Path(root) / f

def main():
    findings, scanned, seen_keys = [], 0, {}
    for p in iter_files():
        if p.suffix in (".md", ".txt", ".html") or (p.parent.name == "sessions" and p.suffix == ".key"):
            continue  # docs with sample tokens; local IPC session keys
        try:
            if p.stat().st_size > MAX_SIZE or p.is_symlink(): continue
            text = p.read_text(errors="ignore")
        except Exception:
            continue
        scanned += 1
        for ln, line in enumerate(text.splitlines(), 1):
            for kind, rx in RX:
                for m in rx.finditer(line):
                    key = m.group(0)
                    fp = hashlib.sha256(key.encode()).hexdigest()[:10]
                    mode = p.stat().st_mode
                    findings.append(dict(
                        type=kind, file=str(p).replace(str(HOME), "~"), line=ln, masked=mask(key),
                        where=classify(str(p)), fingerprint=fp,
                        git_tracked=git_tracked(p) if p.name.startswith(".env") else False,
                        world_readable=bool(mode & stat.S_IROTH)))
                    seen_keys.setdefault(fp, kind)
            if not any(rx.search(line) for _, rx in RX):
                for m in GENERIC.finditer(line):
                    key = m.group(1)
                    if len(set(key)) < 10 or re.fullmatch(r"[a-z_\-\.]+", key): continue  # not random enough
                    fp = hashlib.sha256(key.encode()).hexdigest()[:10]
                    findings.append(dict(type="unknown token", file=str(p).replace(str(HOME), "~"), line=ln,
                        masked=key[:3] + "…" + key[-4:], where=classify(str(p)), fingerprint=fp,
                        git_tracked=False, world_readable=bool(p.stat().st_mode & stat.S_IROTH)))
                    seen_keys.setdefault(fp, "unknown token")
    # report
    R, Y, G, D, B = "\033[31m", "\033[33m", "\033[32m", "\033[2m", "\033[1m"; X = "\033[0m"
    print(f"{B}keyaudit{X}  scanned {scanned} files\n")
    for f in sorted(findings, key=lambda f: (f["where"], f["file"])):
        flags = []
        if f["git_tracked"]: flags.append(f"{R}GIT-TRACKED{X}")
        if f["world_readable"]: flags.append(f"{Y}world-readable{X}")
        print(f"{R}●{X} {f['type']:<14} {f['masked']:<22} {D}{f['where']:<18}{X} {f['file']}:{f['line']} {' '.join(flags)}")
    by_where = {}
    for f in findings: by_where[f["where"]] = by_where.get(f["where"], 0) + 1
    print(f"\n{B}{len(findings)} plaintext hits · {len(seen_keys)} unique keys · {len(by_where)} kinds of places{X}")
    for w, c in sorted(by_where.items(), key=lambda x: -x[1]): print(f"  {w:<20} {c}")
    if not findings: print(f"{G}clean ✓{X}")
    if "--json" in sys.argv:
        out = sys.argv[sys.argv.index("--json") + 1]
        json.dump(dict(scanned=scanned, unique_keys=len(seen_keys), findings=findings), open(out, "w"), indent=1)

if __name__ == "__main__":
    main()
