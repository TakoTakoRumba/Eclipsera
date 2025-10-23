# scripts/backup.py
import os, zipfile, datetime, pathlib

EXCLUDES = {
    ".venv", "__pycache__", ".git", ".idea", ".vscode", "node_modules"
}
EXCLUDE_EXTS = {".zip", ".pyc"}

def should_skip(root, fname):
    p = pathlib.Path(root) / fname
    parts = set(p.parts)
    if parts & EXCLUDES:
        return True
    if p.suffix.lower() in EXCLUDE_EXTS:
        return True
    return False

def main():
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    out = f"backup_{ts}.zip"
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for root, dirs, files in os.walk("."):
            # prune excluded dirs
            dirs[:] = [d for d in dirs if d not in EXCLUDES]
            for f in files:
                if should_skip(root, f):
                    continue
                fp = os.path.join(root, f)
                z.write(fp)
    print(f"✅ Backup created: {out}")

if __name__ == "__main__":
    main()
